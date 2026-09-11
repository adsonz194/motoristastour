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
        self.database["users"].append({
            "id": "user_consultant",
            "username": "dimitri",
            "name": "Dimitri",
            "role": tour_app.ROLE_CONSULTANT,
            "permissions": [],
            "consultantId": "con_dimitri",
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
            "token-consultant": {"userId": "user_consultant", "expiresAt": expiry},
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

    def test_operator_selects_driver_before_starting_request(self) -> None:
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
        drivers = {item["id"]: item for item in self.database["drivers"]}
        self.assertEqual(drivers["drv_one"]["status"], tour_app.DRIVER_AVAILABLE)
        self.assertEqual(drivers["drv_two"]["status"], tour_app.DRIVER_IN_TOUR)
        self.assertEqual(drivers["drv_one"]["toursStarted"], 0)
        self.assertEqual(drivers["drv_two"]["toursStarted"], 1)

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

    def test_house_request_accepts_legacy_tour_linked_only_by_consultant_name(self) -> None:
        tour = self._tour("tour_house", "Tour 03", status=tour_app.STATE_WAITING_HOME)
        tour.update({
            "requiresDetails": False,
            "consultantName": "  DIMITRI ",
            "phase": "Casa",
        })
        self.database["tours"] = [tour]

        options = self.client.get("/api/public/consultant-support/options")
        self.assertEqual(options.status_code, 200, options.get_json())
        option = options.get_json()["tours"][0]
        self.assertIsNone(option["consultantId"])
        self.assertEqual(option["consultantName"], "  DIMITRI ")

        created = self.client.post("/api/public/consultant-support-requests", json={
            "identityType": "CONSULTANT",
            "consultantId": "con_dimitri",
            "tourId": "tour_house",
            "routeStage": "CASA",
            "guestLocation": "SELECTION",
        })
        self.assertEqual(created.status_code, 201, created.get_json())
        self.assertEqual(tour["consultantId"], "con_dimitri")
        self.assertEqual(tour["consultantName"], "Dimitri")

        started = self.client.post(
            f"/api/consultant-tour-requests/{created.get_json()['request']['id']}/start",
            headers=self.auth("token-driver"),
        )
        self.assertEqual(started.status_code, 200, started.get_json())
        self.assertEqual(started.get_json()["action"], "pickup-home")
        self.assertEqual(tour["status"], tour_app.STATE_IN_TOUR)

    def test_gallery_request_accepts_legacy_tour_linked_only_by_consultant_name(self) -> None:
        tour = self._tour("tour_gallery_legacy", "Tour 04", status=tour_app.STATE_WAITING_DESTINATION)
        tour.update({
            "requiresDetails": False,
            "consultantName": "Dimitri",
            "phase": "Galeria",
        })
        self.database["tours"] = [tour]
        destination_id = self.database["destinations"][0]["id"]

        created = self.client.post("/api/public/consultant-support-requests", json={
            "identityType": "CONSULTANT",
            "consultantId": "con_dimitri",
            "tourId": "tour_gallery_legacy",
            "routeStage": "GALERIA_EXIT",
            "destinationId": destination_id,
        })
        self.assertEqual(created.status_code, 201, created.get_json())
        self.assertEqual(tour["consultantId"], "con_dimitri")

    def test_later_stage_does_not_accept_tour_linked_to_another_name(self) -> None:
        tour = self._tour("tour_other", "Tour 05", status=tour_app.STATE_WAITING_HOME)
        tour.update({"consultantName": "Outra Pessoa", "phase": "Casa"})
        self.database["tours"] = [tour]

        created = self.client.post("/api/public/consultant-support-requests", json={
            "identityType": "CONSULTANT",
            "consultantId": "con_dimitri",
            "tourId": "tour_other",
            "routeStage": "CASA",
            "guestLocation": "WAVES",
        })
        self.assertEqual(created.status_code, 409, created.get_json())
        self.assertIn("outro nome", created.get_json()["error"])

    def test_consultant_login_is_scoped_and_each_completed_segment_releases_next_request(self) -> None:
        headers = self.auth("token-consultant")
        options = self.client.get("/api/consultant/support/options", headers=headers)
        self.assertEqual(options.status_code, 200, options.get_json())
        self.assertTrue(options.get_json()["consultantMode"])
        self.assertEqual(options.get_json()["consultants"], [{"id": "con_dimitri", "name": "Dimitri"}])
        self.assertEqual(options.get_json()["selfGens"], [])
        mobile_options = self.client.get("/api/mobile/v1/consultant/support/options", headers=headers)
        self.assertEqual(mobile_options.status_code, 200, mobile_options.get_json())
        self.assertTrue(mobile_options.get_json()["consultantMode"])

        prestige = self.client.post("/api/consultant/support-requests", headers=headers, json={
            "tourId": "tour_01",
            "routeStage": "PRESTIGE",
            "guestLocation": "WAVES",
        })
        self.assertEqual(prestige.status_code, 201, prestige.get_json())
        prestige_request_id = prestige.get_json()["request"]["id"]
        self.assertEqual(self.database["hostessRequests"][0]["requestedById"], "user_consultant")

        started = self.client.post(
            f"/api/consultant-tour-requests/{prestige_request_id}/start",
            headers=self.auth("token-driver"),
        )
        self.assertEqual(started.status_code, 200, started.get_json())
        arrived = self.client.post("/api/tours/tour_01/action", headers=self.auth("token-driver"), json={
            "action": "arrived-home",
            "driverId": "drv_one",
            "homeDecision": "DEIXOU_NA_CASA",
        })
        self.assertEqual(arrived.status_code, 200, arrived.get_json())
        self.assertEqual(self.database["hostessRequests"][0]["status"], tour_app.HOSTESS_REQUEST_CLOSED)
        self.assertEqual(self.database["tours"][0]["status"], tour_app.STATE_WAITING_HOME)

        house_options = self.client.get("/api/consultant/support/options", headers=headers).get_json()
        self.assertIsNone(house_options["activeRequest"])
        self.assertEqual([item["id"] for item in house_options["tours"]], ["tour_01"])
        house = self.client.post("/api/consultant/support-requests", headers=headers, json={
            "tourId": "tour_01",
            "routeStage": "CASA",
            "guestLocation": "SELECTION",
        })
        self.assertEqual(house.status_code, 201, house.get_json())
        house_request_id = house.get_json()["request"]["id"]
        self.assertEqual(
            self.client.post(f"/api/consultant-tour-requests/{house_request_id}/start", headers=self.auth("token-driver")).status_code,
            200,
        )
        gallery_arrival = self.client.post("/api/tours/tour_01/action", headers=self.auth("token-driver"), json={
            "action": "deliver-gallery",
        })
        self.assertEqual(gallery_arrival.status_code, 200, gallery_arrival.get_json())
        house_record = next(item for item in self.database["hostessRequests"] if item["id"] == house_request_id)
        self.assertEqual(house_record["status"], tour_app.HOSTESS_REQUEST_CLOSED)

        gallery_options = self.client.get("/api/consultant/support/options", headers=headers).get_json()
        self.assertIsNone(gallery_options["activeRequest"])
        self.assertEqual(
            {item["name"] for item in gallery_options["destinations"]},
            {"Prestige Waves", "Prestige Selection", "Lobby Waves", "Lobby Selection"},
        )
        destination_id = next(item["id"] for item in gallery_options["destinations"] if item["name"] == "Prestige Waves")
        gallery = self.client.post("/api/consultant/support-requests", headers=headers, json={
            "tourId": "tour_01",
            "routeStage": "GALERIA_EXIT",
            "destinationId": destination_id,
        })
        self.assertEqual(gallery.status_code, 201, gallery.get_json())
        gallery_request_id = gallery.get_json()["request"]["id"]
        self.assertEqual(
            self.client.post(f"/api/consultant-tour-requests/{gallery_request_id}/start", headers=self.auth("token-driver")).status_code,
            200,
        )
        completed = self.client.post("/api/tours/tour_01/action", headers=self.auth("token-driver"), json={
            "action": "complete-destination",
        })
        self.assertEqual(completed.status_code, 200, completed.get_json())
        gallery_record = next(item for item in self.database["hostessRequests"] if item["id"] == gallery_request_id)
        self.assertEqual(gallery_record["status"], tour_app.HOSTESS_REQUEST_CLOSED)

    def test_admin_can_create_consultant_login_linked_to_existing_consultant(self) -> None:
        created = self.client.post("/api/users", headers=self.auth("token-admin"), json={
            "name": "Nome será substituído",
            "username": "bruna",
            "password": "senha-segura",
            "role": "CONSULTOR",
            "consultantId": "con_dimitri",
            "permissions": ["VIEW_DASHBOARD"],
        })
        self.assertEqual(created.status_code, 409, created.get_json())
        self.assertIn("já está vinculado", created.get_json()["error"])

        self.database["users"] = [item for item in self.database["users"] if item["id"] != "user_consultant"]
        created = self.client.post("/api/users", headers=self.auth("token-admin"), json={
            "name": "Nome será substituído",
            "username": "bruna",
            "password": "senha-segura",
            "role": "CONSULTOR",
            "consultantId": "con_dimitri",
            "permissions": ["VIEW_DASHBOARD"],
        })
        self.assertEqual(created.status_code, 201, created.get_json())
        account = created.get_json()["user"]
        self.assertEqual(account["name"], "Dimitri")
        self.assertEqual(account["consultantId"], "con_dimitri")
        self.assertEqual(account["permissions"], [])

        login = self.client.post("/api/auth/login", json={
            "username": "bruna",
            "password": "senha-segura",
        })
        self.assertEqual(login.status_code, 200, login.get_json())
        self.assertEqual(login.get_json()["user"]["role"], tour_app.ROLE_CONSULTANT)
        consultant_headers = self.auth(login.get_json()["token"])
        scoped_options = self.client.get("/api/consultant/support/options", headers=consultant_headers)
        self.assertEqual(scoped_options.status_code, 200, scoped_options.get_json())
        self.assertEqual(scoped_options.get_json()["consultants"], [{"id": "con_dimitri", "name": "Dimitri"}])
        bootstrap = self.client.get("/api/bootstrap", headers=consultant_headers)
        self.assertEqual(bootstrap.status_code, 200, bootstrap.get_json())
        self.assertEqual(bootstrap.get_json()["data"]["tours"], [])

    def test_numbered_tours_are_returned_from_smallest_to_largest(self) -> None:
        self.database["tours"] = [
            self._tour("tour_a", "Tour 11"),
            self._tour("tour_z", "Tour 2"),
            self._tour("tour_y", "Tour 1"),
        ]

        consultant_options = self.client.get(
            "/api/consultant/support/options",
            headers=self.auth("token-consultant"),
        )
        self.assertEqual(consultant_options.status_code, 200, consultant_options.get_json())
        self.assertEqual(
            [item["label"] for item in consultant_options.get_json()["tours"]],
            ["Tour 1", "Tour 2", "Tour 11"],
        )

        driver_bootstrap = self.client.get("/api/bootstrap", headers=self.auth("token-driver"))
        self.assertEqual(driver_bootstrap.status_code, 200, driver_bootstrap.get_json())
        self.assertEqual(
            [item["slotLabel"] for item in driver_bootstrap.get_json()["data"]["tours"]],
            ["Tour 1", "Tour 2", "Tour 11"],
        )


if __name__ == "__main__":
    unittest.main()
