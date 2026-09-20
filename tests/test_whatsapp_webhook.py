"""Regression coverage for the Meta WhatsApp webhook and Tour workflow."""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app as tour_app  # noqa: E402


class WhatsAppWebhookTest(unittest.TestCase):
    OPERATION_DAY = "2026-09-20"
    APP_SECRET = "unit-test-app-secret"
    VERIFY_TOKEN = "unit-test-verify-token"
    CONSULTANT_NUMBER = "5571999999999"

    def setUp(self) -> None:
        self.database = tour_app.initial_database()
        self.database.update({
            "operationDate": self.OPERATION_DAY,
            "consultants": [{
                "id": "con_yasmin",
                "name": "Yasmin",
                "active": True,
                "whatsappNumber": self.CONSULTANT_NUMBER,
            }],
            "tours": [{
                "id": "tour_02",
                "groupName": "Tour 2",
                "slotLabel": "Tour 2",
                "people": 2,
                "selfGuide": False,
                "consultantId": None,
                "consultantName": None,
                "selfGenId": None,
                "selfGenName": None,
                "wave": "WAVE_1",
                "scheduledTime": "09:00",
                "status": tour_app.STATE_AVAILABLE,
                "phase": "Prestige Waves",
                "requiredCartCount": 1,
                "requiresDetails": True,
                "allocations": [],
                "createdAt": "2026-09-20T10:00:00+00:00",
                "updatedAt": "2026-09-20T10:00:00+00:00",
            }],
            "hostessRequests": [],
            "activities": [],
            "whatsappProcessedMessages": [],
        })
        self.sent_messages: list[list[tuple[str, dict]]] = []
        self.patchers = [
            patch.object(tour_app, "POSTGRES_URL", ""),
            patch.object(tour_app, "operation_date", return_value=self.OPERATION_DAY),
            patch.object(tour_app, "operational_database", return_value=self.database),
            patch.object(tour_app, "save_database", return_value=None),
            patch.object(tour_app, "notify_hostess_car_update", return_value=None),
            patch.object(tour_app, "send_whatsapp_messages", side_effect=self._record_sent_messages),
            patch.object(tour_app, "WHATSAPP_ACCESS_TOKEN", "test-access-token"),
            patch.object(tour_app, "WHATSAPP_PHONE_NUMBER_ID", "123456"),
            patch.object(tour_app, "WHATSAPP_WEBHOOK_VERIFY_TOKEN", self.VERIFY_TOKEN),
            patch.object(tour_app, "WHATSAPP_APP_SECRET", self.APP_SECRET),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.previous_testing = tour_app.app.config.get("TESTING")
        tour_app.app.config["TESTING"] = True
        self.addCleanup(tour_app.app.config.__setitem__, "TESTING", self.previous_testing)
        self.client = tour_app.app.test_client()

    def _record_sent_messages(self, messages):
        self.sent_messages.append(messages)
        return {"attempted": len(messages), "delivered": len(messages), "disabled": False}

    def _webhook_payload(self, message: dict) -> dict:
        return {
            "object": "whatsapp_business_account",
            "entry": [{"changes": [{"field": "messages", "value": {"messages": [message]}}]}],
        }

    def _post_webhook(self, message: dict):
        body = json.dumps(self._webhook_payload(message), separators=(",", ":")).encode("utf-8")
        signature = hmac.new(self.APP_SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return self.client.post(
            "/whatsapp/webhook",
            data=body,
            content_type="application/json",
            headers={"X-Hub-Signature-256": f"sha256={signature}"},
        )

    def test_meta_verification_requires_the_configured_token(self) -> None:
        verified = self.client.get(
            "/whatsapp/webhook",
            query_string={
                "hub.mode": "subscribe",
                "hub.verify_token": self.VERIFY_TOKEN,
                "hub.challenge": "challenge-from-meta",
            },
        )
        self.assertEqual(verified.status_code, 200)
        self.assertEqual(verified.get_data(as_text=True), "challenge-from-meta")

        rejected = self.client.get(
            "/whatsapp/webhook",
            query_string={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "x"},
        )
        self.assertEqual(rejected.status_code, 403)

    def test_webhook_selects_a_tour_then_creates_one_idempotent_request(self) -> None:
        selection = self._post_webhook({
            "id": "wamid-select",
            "from": self.CONSULTANT_NUMBER,
            "type": "interactive",
            "interactive": {"type": "list_reply", "list_reply": {"id": "select-tour:tour_02"}},
        })
        self.assertEqual(selection.status_code, 200)
        selection_payload = self.sent_messages[-1][0][1]
        self.assertEqual(selection_payload["type"], "interactive")
        self.assertEqual(
            selection_payload["interactive"]["action"]["buttons"][0]["reply"]["id"],
            "request:tour_02:PRESTIGE",
        )

        requested = self._post_webhook({
            "id": "wamid-request",
            "from": self.CONSULTANT_NUMBER,
            "type": "interactive",
            "interactive": {"type": "button_reply", "button_reply": {"id": "request:tour_02:PRESTIGE"}},
        })
        self.assertEqual(requested.status_code, 200)
        self.assertEqual(len(self.database["hostessRequests"]), 1)
        car_request = self.database["hostessRequests"][0]
        self.assertEqual(car_request["consultantId"], "con_yasmin")
        self.assertEqual(car_request["routeStage"], "PRESTIGE")
        self.assertEqual(self.database["tours"][0]["pendingConsultantRequestId"], car_request["id"])
        self.assertEqual(self.database["tours"][0]["consultantName"], "Yasmin")

        duplicate = self._post_webhook({
            "id": "wamid-request",
            "from": self.CONSULTANT_NUMBER,
            "type": "interactive",
            "interactive": {"type": "button_reply", "button_reply": {"id": "request:tour_02:PRESTIGE"}},
        })
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(len(self.database["hostessRequests"]), 1)

    def test_invalid_signature_cannot_open_a_request(self) -> None:
        payload = self._webhook_payload({
            "id": "wamid-invalid",
            "from": self.CONSULTANT_NUMBER,
            "type": "text",
            "text": {"body": "MENU"},
        })
        rejected = self.client.post(
            "/whatsapp/webhook",
            data=json.dumps(payload),
            content_type="application/json",
            headers={"X-Hub-Signature-256": "sha256=wrong"},
        )
        self.assertEqual(rejected.status_code, 401)
        self.assertEqual(self.database["hostessRequests"], [])

    def test_home_and_gallery_events_offer_only_the_next_valid_action(self) -> None:
        tour = self.database["tours"][0]
        tour.update({
            "consultantId": "con_yasmin",
            "consultantName": "Yasmin",
            "status": tour_app.STATE_WAITING_HOME,
        })

        tour_app.notify_whatsapp_consultant_for_route_event(
            self.database, tour, "WAITING_HOME",
        )
        home_message = self.sent_messages[-1][0][1]
        self.assertEqual(home_message["interactive"]["type"], "button")
        self.assertEqual(
            home_message["interactive"]["action"]["buttons"][0]["reply"]["id"],
            "request:tour_02:CASA",
        )

        self.database["destinations"] = [
            {"id": "lobby-selection", "name": "Lobby Selection", "active": True},
            {"id": "lobby-waves", "name": "Lobby Waves", "active": True},
            {"id": "prestige-selection", "name": "Prestige Selection", "active": True},
            {"id": "prestige-waves", "name": "Prestige Waves", "active": True},
        ]
        tour["status"] = tour_app.STATE_WAITING_DESTINATION
        tour_app.notify_whatsapp_consultant_for_route_event(
            self.database, tour, "GALLERY",
        )
        gallery_message = self.sent_messages[-1][0][1]
        rows = gallery_message["interactive"]["action"]["sections"][0]["rows"]
        self.assertEqual([row["id"] for row in rows], [
            "destination:tour_02:lobby-selection",
            "destination:tour_02:lobby-waves",
            "destination:tour_02:prestige-selection",
            "destination:tour_02:prestige-waves",
        ])


if __name__ == "__main__":
    unittest.main()
