"""Regression coverage for Consultant/Self Gen requests tied to numbered Tours."""

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


class ConsultantTourRequestApiTest(unittest.TestCase):
    OPERATION_DAY = "2026-09-11"

    def setUp(self) -> None:
        self.database = tour_app.initial_database()
        self.database.update({
            "operationDate": self.OPERATION_DAY,
            "consultants": [{"id": "con_dimitri", "name": "Dimitri", "active": True}],
            "selfGens": [
                {"id": "self_ana", "name": "Ana", "active": True},
                {"id": "self_inactive", "name": "Inativo", "active": False},
            ],
            "drivers": [
                {
                    "id": "drv_one",
                    "name": "Motorista Um",
                    "active": True,
                    "status": tour_app.DRIVER_AVAILABLE,
                    "toursStarted": 0,
                    "homePickups": 0,
                    "hostessAvailable": False,
                    "hostessRequestId": None,
                    "lastActivity": "2026-09-11T10:00:00+00:00",
                },
                {
                    "id": "drv_two",
                    "name": "Motorista Dois",
                    "active": True,
                    "status": tour_app.DRIVER_AVAILABLE,
                    "toursStarted": 0,
                    "homePickups": 0,
                    "hostessAvailable": False,
                    "hostessRequestId": None,
                    "lastActivity": "2026-09-11T10:00:00+00:00",
                },
            ],
            "tours": [self._tour("tour_01", "Tour 01")],
            "attendance": [{
                "id": "attendance_one",
                "userId": "user_driver",
                "operationDate": self.OPERATION_DAY,
                "status": "TRABALHANDO",
                "checkInAt": "2026-09-11T10:00:00+00:00",
            }, {
                "id": "attendance_two",
                "userId": "user_driver_two",
                "operationDate": self.OPERATION_DAY,
                "status": "TRABALHANDO",
                "checkInAt": "2026-09-11T10:00:00+00:00",
            }],
            "hostessRequests": [],
            "activities": [],
        })
        self.database["users"].append({
            "id": "user_driver",
            "username": "driver",
            "name": "Motorista Um",
            "role": tour_app.ROLE_DRIVER,
            "permissions": tour_app.default_permissions_for_role(tour_app.ROLE_DRIVER),
            "driverId": "drv_one",
            "active": True,
            "passwordHash": "unused",
            "createdAt": "2026-09-11T10:00:00+00:00",
        })
        self.database["users"].append({
            "id": "user_driver_two",
            "username": "driver2",
            "name": "Motorista Dois",
            "role": tour_app.ROLE_DRIVER,
            "permissions": tour_app.default_permissions_for_role(tour_app.ROLE_DRIVER),
            "driverId": "drv_two",
            "active": True,
            "passwordHash": "unused",
            "createdAt": "2026-09-11T10:00:00+00:00",
        })

        self.patchers = [
            patch.object(tour_app, "POSTGRES_URL", ""),
            patch.object(tour_app, "operation_date", return_value=self.OPERATION_DAY),
            patch.object(tour_app, "operational_database", return_value=self.database),
            patch.object(tour_app, "save_database", return_value=None),
            patch.object(tour_app, "notify_operation_update", return_value=None),
            patch.object(tour_app, "notify_hostess_car_update", return_value=None),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

        expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        tour_app.SESSIONS.clear()
        tour_app.SESSIONS.update({
            "token-admin": {"userId": "user_admin", "expiresAt": expiry},
            "token-driver": {"userId": "user_driver", "expiresAt": expiry},
            "token-driver-two": {"userId": "user_driver_two", "expiresAt": expiry},
        })
        self.addCleanup(tour_app.SESSIONS.clear)
        tour_app.app.config["TESTING"] = True
        self.client = tour_app.app.test_client()

    @staticmethod
    def _tour(tour_id: str, label: str, *, self_guide: bool = False, status: str | None = None) -> dict:
        return {
            "id": tour_id,
            "groupName": label,
            "slotLabel": label,
            "people": None,
            "selfGuide": self_guide,
            "consultantId": None,
            "consultantName": None,
            "selfGenId": None,
            "selfGenName": None,
            "wave": "WAVE_1",
            "scheduledTime": "09:00",
            "status": status or tour_app.STATE_AVAILABLE,
            "phase": "Prestige Waves",
            "requiredCartCount": 1,
            "requiresDetails": True,
            "allocations": [],
            "createdAt": "2026-09-11T10:00:00+00:00",
            "updatedAt": "2026-09-11T10:00:00+00:00",
        }

    def auth(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def test_prestige_request_binds_identity_and_driver_starts_with_one_tap(self) -> None:
        created = self.client.post("/api/public/consultant-support-requests", json={
            "identityType": "CONSULTANT",
            "consultantId": "con_dimitri",
            "tourId": "tour_01",
            "routeStage": "PRESTIGE",
            "guestLocation": "WAVES",
        })
        self.assertEqual(created.status_code, 201, created.get_json())
        request_payload = created.get_json()["request"]
        tour = self.database["tours"][0]
        self.assertEqual(tour["consultantName"], "Dimitri")
        self.assertEqual(tour["pendingConsultantRequestId"], request_payload["id"])
        self.assertEqual(request_payload["tourLabel"], "Tour 01")
        self.assertEqual(request_payload["guestLocationLabel"], "Prestige Waves")

        bypass = self.client.post(
            "/api/tours/tour_01/action",
            headers=self.auth("token-driver"),
            json={"action": "start", "allocations": [{"driverId": "drv_one"}]},
        )
        self.assertEqual(bypass.status_code, 409, bypass.get_json())

        started = self.client.post(
            f"/api/consultant-tour-requests/{request_payload['id']}/start",
            headers=self.auth("token-driver"),
        )
        self.assertEqual(started.status_code, 200, started.get_json())
        self.assertEqual(started.get_json()["action"], "start")
        self.assertEqual(tour["status"], tour_app.STATE_IN_TOUR)
        self.assertNotIn("pendingConsultantRequestId", tour)
        self.assertEqual(started.get_json()["request"]["status"], tour_app.HOSTESS_REQUEST_IN_PROGRESS)
        self.assertEqual(started.get_json()["request"]["assignedDriverName"], "Motorista Um")

    def test_self_gen_crud_and_only_active_names_in_public_options(self) -> None:
        created = self.client.post(
            "/api/self-gens",
            headers=self.auth("token-admin"),
            json={"name": "Bruno", "active": True},
        )
        self.assertEqual(created.status_code, 201, created.get_json())
        self_gen_id = created.get_json()["selfGen"]["id"]

        updated = self.client.put(
            f"/api/self-gens/{self_gen_id}",
            headers=self.auth("token-admin"),
            json={"name": "Bruno SG", "active": True},
        )
        self.assertEqual(updated.status_code, 200, updated.get_json())

        options = self.client.get("/api/public/consultant-support/options")
        self.assertEqual(options.status_code, 200, options.get_json())
        names = {item["name"] for item in options.get_json()["selfGens"]}
        self.assertEqual(names, {"Ana", "Bruno SG"})

        deleted = self.client.delete(f"/api/self-gens/{self_gen_id}", headers=self.auth("token-admin"))
        self.assertEqual(deleted.status_code, 200, deleted.get_json())

    def test_operator_selects_driver_then_colleague_corrects_assignment(self) -> None:
        created = self.client.post("/api/public/consultant-support-requests", json={
            "identityType": "CONSULTANT",
            "consultantId": "con_dimitri",
            "tourId": "tour_01",
            "routeStage": "PRESTIGE",
            "guestLocation": "SELECTION",
        })
        request_id = created.get_json()["request"]["id"]

        started = self.client.post(
            f"/api/consultant-tour-requests/{request_id}/start",
            headers=self.auth("token-driver"),
            json={"driverId": "drv_two"},
        )
        self.assertEqual(started.status_code, 200, started.get_json())
        self.assertEqual(started.get_json()["request"]["assignedDriverId"], "drv_two")
        self.assertEqual(self.database["tours"][0]["allocations"][0]["driverId"], "drv_two")

        corrected = self.client.patch(
            f"/api/consultant-tour-requests/{request_id}/driver",
            headers=self.auth("token-driver-two"),
            json={"driverId": "drv_one"},
        )
        self.assertEqual(corrected.status_code, 200, corrected.get_json())
        self.assertEqual(corrected.get_json()["request"]["assignedDriverId"], "drv_one")
        self.assertEqual(self.database["tours"][0]["allocations"][0]["driverId"], "drv_one")
        drivers = {item["id"]: item for item in self.database["drivers"]}
        self.assertEqual(drivers["drv_one"]["status"], tour_app.DRIVER_IN_TOUR)
        self.assertEqual(drivers["drv_two"]["status"], tour_app.DRIVER_AVAILABLE)
        self.assertEqual(drivers["drv_one"]["toursStarted"], 1)
        self.assertEqual(drivers["drv_two"]["toursStarted"], 0)

    def test_driver_can_cancel_mistaken_start_and_request_returns_to_queue(self) -> None:
        created = self.client.post("/api/public/consultant-support-requests", json={
            "identityType": "CONSULTANT",
            "consultantId": "con_dimitri",
            "tourId": "tour_01",
            "routeStage": "PRESTIGE",
            "guestLocation": "WAVES",
        })
        request_id = created.get_json()["request"]["id"]
        started = self.client.post(
            f"/api/consultant-tour-requests/{request_id}/start",
            headers=self.auth("token-driver"),
            json={"driverId": "drv_one"},
        )
        self.assertEqual(started.status_code, 200, started.get_json())
        cart_id = self.database["tours"][0]["allocations"][0]["cartId"]

        cancelled = self.client.post(
            f"/api/consultant-tour-requests/{request_id}/cancel",
            headers=self.auth("token-driver-two"),
        )
        self.assertEqual(cancelled.status_code, 200, cancelled.get_json())
        tour = self.database["tours"][0]
        self.assertEqual(tour["status"], tour_app.STATE_AVAILABLE)
        self.assertEqual(tour["pendingConsultantRequestId"], request_id)
        self.assertEqual(tour["allocations"], [])
        self.assertEqual(cancelled.get_json()["request"]["status"], tour_app.HOSTESS_REQUEST_OPEN)
        self.assertIsNone(cancelled.get_json()["request"]["assignedDriverId"])
        driver = next(item for item in self.database["drivers"] if item["id"] == "drv_one")
        cart = next(item for item in self.database["carts"] if item["id"] == cart_id)
        self.assertEqual(driver["status"], tour_app.DRIVER_AVAILABLE)
        self.assertEqual(driver["toursStarted"], 0)
        self.assertEqual(cart["status"], "DISPONIVEL")

    def test_gallery_exit_request_requires_and_applies_selected_destination(self) -> None:
        tour = self._tour("tour_gallery", "Tour 02", status=tour_app.STATE_WAITING_DESTINATION)
        tour.update({
            "requiresDetails": False,
            "consultantId": "con_dimitri",
            "consultantName": "Dimitri",
            "phase": "Galeria",
        })
        self.database["tours"] = [tour]
        destination_id = self.database["destinations"][0]["id"]

        created = self.client.post("/api/public/consultant-support-requests", json={
            "identityType": "CONSULTANT",
            "consultantId": "con_dimitri",
            "tourId": "tour_gallery",
            "routeStage": "GALERIA_EXIT",
            "destinationId": destination_id,
        })
        self.assertEqual(created.status_code, 201, created.get_json())
        request_id = created.get_json()["request"]["id"]

        started = self.client.post(
            f"/api/consultant-tour-requests/{request_id}/start",
            headers=self.auth("token-driver"),
        )
        self.assertEqual(started.status_code, 200, started.get_json())
        self.assertEqual(started.get_json()["action"], "assign-destination")
        self.assertEqual(tour["status"], tour_app.STATE_FINAL_DESTINATION)
        self.assertEqual(tour["destinationId"], destination_id)


if __name__ == "__main__":
    unittest.main()
