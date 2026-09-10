"""Regression coverage for Hostess quantity-slot corrections."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app as tour_app  # noqa: E402


class HostessTourCorrectionsApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.database = tour_app.initial_database()
        self.database.update({
            "users": [
                self._account("user_hostess", [tour_app.PERMISSION_MANAGE_TOUR_QUANTITIES]),
                self._account("user_viewer", [tour_app.PERMISSION_VIEW_DASHBOARD]),
            ],
            "tours": [
                self._tour("tour_1", "Tour 1"),
                self._tour("tour_2", "Tour 2", self_guide=True),
                self._tour("tour_started", "Tour iniciado", requires_details=False, status=tour_app.STATE_IN_TOUR),
            ],
            "activities": [],
        })
        self.patchers = [
            patch.object(tour_app, "operational_database", return_value=self.database),
            patch.object(tour_app, "save_database", return_value=None),
            patch.object(tour_app, "notify_operation_update", return_value={"sent": 0}),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

        self.previous_testing = tour_app.app.config.get("TESTING")
        tour_app.app.config["TESTING"] = True
        self.addCleanup(tour_app.app.config.__setitem__, "TESTING", self.previous_testing)
        tour_app.SESSIONS.clear()
        self.addCleanup(tour_app.SESSIONS.clear)
        expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        tour_app.SESSIONS.update({
            "token-hostess": {"userId": "user_hostess", "expiresAt": expiry},
            "token-viewer": {"userId": "user_viewer", "expiresAt": expiry},
        })
        self.client = tour_app.app.test_client()

    @staticmethod
    def _account(user_id: str, permissions: list[str]) -> dict:
        return {
            "id": user_id,
            "name": "Hostess Teste",
            "username": user_id,
            "role": tour_app.ROLE_HOSTESS,
            "permissions": permissions,
            "active": True,
            "passwordHash": "unused-in-session-tests",
            "createdAt": "2026-09-05T12:00:00+00:00",
        }

    @staticmethod
    def _tour(
        tour_id: str,
        label: str,
        *,
        self_guide: bool = False,
        requires_details: bool = True,
        status: str = tour_app.STATE_AVAILABLE,
    ) -> dict:
        return {
            "id": tour_id,
            "groupName": label,
            "slotLabel": label,
            "people": 0,
            "selfGuide": self_guide,
            "consultantId": None,
            "wave": "WAVE_1",
            "scheduledTime": "09:00",
            "status": status,
            "phase": "Prestige Praia do Forte",
            "requiresDetails": requires_details,
            "registeredBy": tour_app.ROLE_HOSTESS,
            "createdAt": "2026-09-05T12:00:00+00:00",
            "updatedAt": "2026-09-05T12:00:00+00:00",
            "allocations": [],
        }

    def _request(self, token: str, method: str, **kwargs):
        return self.client.open(
            "/api/tours/hostess/selection",
            method=method,
            headers={"Authorization": f"Bearer {token}"},
            **kwargs,
        )

    def test_hostess_moves_selected_slots_to_another_wave(self) -> None:
        response = self._request(
            "token-hostess",
            "PATCH",
            json={"tourIds": ["tour_1", "tour_2"], "wave": "WAVE_2"},
        )

        self.assertEqual(response.status_code, 200, response.get_json())
        for tour_id in ("tour_1", "tour_2"):
            tour = next(item for item in self.database["tours"] if item["id"] == tour_id)
            self.assertEqual(tour["wave"], "WAVE_2")
            self.assertEqual(tour["scheduledTime"], "11:00")
        self.assertEqual(next(item for item in self.database["tours"] if item["id"] == "tour_1")["slotLabel"], "Tour 1")
        self.assertEqual(next(item for item in self.database["tours"] if item["id"] == "tour_2")["slotLabel"], "Self Gen 1")
        self.assertIn("2 lançamentos", self.database["activities"][0]["message"])
        self.assertIn("2ª Ola", self.database["activities"][0]["message"])

    def test_second_wave_restarts_tour_and_self_gen_numbering(self) -> None:
        first = self.client.post(
            "/api/tours/hostess",
            headers={"Authorization": "Bearer token-hostess"},
            json={"quantity": 2, "selfGeanQuantity": 1, "wave": "WAVE_2"},
        )
        second = self.client.post(
            "/api/tours/hostess",
            headers={"Authorization": "Bearer token-hostess"},
            json={"quantity": 1, "selfGeanQuantity": 1, "wave": "WAVE_2"},
        )

        self.assertEqual(first.status_code, 201, first.get_json())
        self.assertEqual(
            [item["slotLabel"] for item in first.get_json()["tours"]],
            ["Tour 1", "Tour 2", "Self Gen 1"],
        )
        self.assertEqual(second.status_code, 201, second.get_json())
        self.assertEqual(
            [item["slotLabel"] for item in second.get_json()["tours"]],
            ["Tour 3", "Self Gen 2"],
        )

    def test_selection_is_atomic_when_a_tour_has_already_started(self) -> None:
        response = self._request(
            "token-hostess",
            "PATCH",
            json={"tourIds": ["tour_1", "tour_started"], "wave": "WAVE_2"},
        )

        self.assertEqual(response.status_code, 409, response.get_json())
        tour = next(item for item in self.database["tours"] if item["id"] == "tour_1")
        self.assertEqual(tour["wave"], "WAVE_1")
        self.assertEqual(tour["scheduledTime"], "09:00")

    def test_hostess_deletes_only_the_selected_unstarted_slots(self) -> None:
        response = self._request(
            "token-hostess",
            "DELETE",
            json={"tourIds": ["tour_1", "tour_2"]},
        )

        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(set(response.get_json()["deletedTourIds"]), {"tour_1", "tour_2"})
        self.assertEqual([item["id"] for item in self.database["tours"]], ["tour_started"])
        self.assertIn("1 tour e 1 Self Gen", self.database["activities"][0]["message"])

    def test_dashboard_only_hostess_cannot_change_or_delete_slots(self) -> None:
        change = self._request("token-viewer", "PATCH", json={"tourIds": ["tour_1"], "wave": "WAVE_2"})
        delete = self._request("token-viewer", "DELETE", json={"tourIds": ["tour_1"]})

        self.assertEqual(change.status_code, 403, change.get_json())
        self.assertEqual(delete.status_code, 403, delete.get_json())
        self.assertTrue(any(item["id"] == "tour_1" for item in self.database["tours"]))


if __name__ == "__main__":
    unittest.main()
