"""Regression coverage for generic driver operational support.

Run with:
    python -m unittest tests.test_driver_support
"""

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


class DriverSupportApiTest(unittest.TestCase):
    """An operational support reserves the driver until it is explicitly closed."""

    def setUp(self) -> None:
        self.database = self._database()
        self.patchers = [
            patch.object(tour_app, "operational_database", return_value=self.database),
            patch.object(tour_app, "save_database", return_value=None),
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
            "token-admin": {"userId": "user_admin", "expiresAt": expiry},
            "token-one": {"userId": "user_one", "expiresAt": expiry},
            "token-two": {"userId": "user_two", "expiresAt": expiry},
        })
        self.client = tour_app.app.test_client()

    @staticmethod
    def _account(user_id: str, name: str, role: str, permissions: list[str], driver_id: str | None = None) -> dict:
        account = {
            "id": user_id,
            "name": name,
            "username": user_id,
            "role": role,
            "permissions": permissions,
            "active": True,
            "passwordHash": "unused-in-session-tests",
            "createdAt": "2026-09-03T12:00:00+00:00",
        }
        if driver_id:
            account["driverId"] = driver_id
        return account

    @staticmethod
    def _driver(driver_id: str, name: str, status: str = tour_app.DRIVER_AVAILABLE) -> dict:
        return {
            "id": driver_id,
            "name": name,
            "active": True,
            "status": status,
            "toursStarted": 0,
            "homePickups": 0,
            "hostessAvailable": False,
            "hostessRequestId": None,
            "driverSupportId": None,
            "supportLocation": None,
            "lastActivity": "2026-09-03T12:00:00+00:00",
        }

    @classmethod
    def _database(cls) -> dict:
        db = tour_app.initial_database()
        today = tour_app.operation_date()
        db.update({
            "operationDate": today,
            "users": [
                cls._account(
                    "user_admin",
                    "Coordenador",
                    tour_app.ROLE_ADMIN,
                    tour_app.default_permissions_for_role(tour_app.ROLE_ADMIN),
                ),
                cls._account(
                    "user_one",
                    "Motorista Um",
                    tour_app.ROLE_DRIVER,
                    tour_app.default_permissions_for_role(tour_app.ROLE_DRIVER),
                    "drv_one",
                ),
                cls._account(
                    "user_two",
                    "Motorista Dois",
                    tour_app.ROLE_DRIVER,
                    tour_app.default_permissions_for_role(tour_app.ROLE_DRIVER),
                    "drv_two",
                ),
            ],
            "drivers": [
                cls._driver("drv_one", "Motorista Um"),
                cls._driver("drv_two", "Motorista Dois"),
                cls._driver("drv_without_checkin", "Sem Check-in"),
            ],
            "carts": [
                {"id": "cart_one", "name": "Carrinho 01", "capacity": 5, "guestCapacity": 4, "status": "DISPONIVEL"},
            ],
            "attendance": [
                {"id": "checkin_one", "userId": "user_one", "operationDate": today, "status": "TRABALHANDO"},
                {"id": "checkin_two", "userId": "user_two", "operationDate": today, "status": "TRABALHANDO"},
            ],
            "driverSupports": [],
            "activities": [],
        })
        return db

    def _request(self, token: str, method: str, path: str, **kwargs):
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = f"Bearer {token}"
        return self.client.open(path, method=method, headers=headers, **kwargs)

    def _start_own_support(self):
        response = self._request(
            "token-one",
            "POST",
            "/api/driver-supports",
            json={"location": "Casa 305", "note": "Apoio para bagagens"},
        )
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()["support"]

    def test_driver_starts_and_closes_own_support_with_audit_and_public_location(self) -> None:
        support = self._start_own_support()
        driver = self.database["drivers"][0]
        self.assertEqual(support["status"], tour_app.DRIVER_SUPPORT_OPEN)
        self.assertEqual(support["driverId"], "drv_one")
        self.assertEqual(support["driverName"], "Motorista Um")
        self.assertEqual(driver["status"], tour_app.DRIVER_SUPPORT)
        self.assertEqual(driver["driverSupportId"], support["id"])
        self.assertEqual(driver["supportLocation"], "Casa 305")

        # Repeating check-in is harmless and must never release an active
        # support reservation back to the available driver pool.
        repeated_checkin = self._request("token-one", "POST", "/api/attendance/check-in")
        self.assertEqual(repeated_checkin.status_code, 200, repeated_checkin.get_json())
        self.assertTrue(repeated_checkin.get_json()["alreadyCheckedIn"])
        self.assertEqual(driver["status"], tour_app.DRIVER_SUPPORT)
        self.assertEqual(driver["driverSupportId"], support["id"])

        started_audit = self.database["activities"][0]
        self.assertEqual(started_audit["actorUserId"], "user_one")
        self.assertEqual(started_audit["audit"]["type"], "DRIVER_SUPPORT")
        self.assertEqual(started_audit["audit"]["action"], "START")

        bootstrap = self._request("token-one", "GET", "/api/bootstrap")
        self.assertEqual(bootstrap.status_code, 200, bootstrap.get_json())
        payload = bootstrap.get_json()
        self.assertEqual(payload["driverStates"]["APOIO"], tour_app.DRIVER_SUPPORT)
        self.assertEqual(payload["data"]["driverSupports"][0]["id"], support["id"])

        public_board = self.client.get("/api/public/driver-status")
        self.assertEqual(public_board.status_code, 200, public_board.get_json())
        public_driver = next(item for item in public_board.get_json()["drivers"] if item["name"] == "Motorista Um")
        self.assertEqual(public_driver["status"], tour_app.DRIVER_SUPPORT)
        self.assertEqual(public_driver["locationLabel"], "Em apoio · Casa 305")

        closed = self._request("token-one", "POST", f"/api/driver-supports/{support['id']}/close")
        self.assertEqual(closed.status_code, 200, closed.get_json())
        self.assertEqual(closed.get_json()["support"]["status"], tour_app.DRIVER_SUPPORT_CLOSED)
        self.assertEqual(closed.get_json()["driver"]["status"], tour_app.DRIVER_AVAILABLE)
        self.assertIsNone(closed.get_json()["driver"]["driverSupportId"])
        closed_audit = self.database["activities"][0]
        self.assertEqual(closed_audit["actorUserId"], "user_one")
        self.assertEqual(closed_audit["audit"]["action"], "CLOSE")

    def test_only_the_driver_or_settings_coordinator_can_manage_a_support(self) -> None:
        # Settings access is intentionally enough for a coordinator to
        # supervise this board, even if the optional support grant was removed
        # from a customized administrator account.
        admin = next(item for item in self.database["users"] if item["id"] == "user_admin")
        admin["permissions"] = [tour_app.PERMISSION_MANAGE_SETTINGS]
        forbidden_start = self._request(
            "token-one",
            "POST",
            "/api/driver-supports",
            json={"driverId": "drv_two", "location": "Galeria"},
        )
        self.assertEqual(forbidden_start.status_code, 403, forbidden_start.get_json())

        coordinated = self._request(
            "token-admin",
            "POST",
            "/api/driver-supports",
            json={"driverId": "drv_two", "location": "Lobby Selection"},
        )
        self.assertEqual(coordinated.status_code, 201, coordinated.get_json())
        support = coordinated.get_json()["support"]
        self.assertEqual(support["startedByName"], "Coordenador")

        coordinator_bootstrap = self._request("token-admin", "GET", "/api/bootstrap")
        self.assertEqual(coordinator_bootstrap.status_code, 200, coordinator_bootstrap.get_json())
        coordinator_data = coordinator_bootstrap.get_json()["data"]
        self.assertTrue(any(item["id"] == "drv_two" for item in coordinator_data["drivers"]))
        self.assertEqual(coordinator_data["driverSupports"][0]["id"], support["id"])

        forbidden_close = self._request("token-one", "POST", f"/api/driver-supports/{support['id']}/close")
        self.assertEqual(forbidden_close.status_code, 403, forbidden_close.get_json())
        coordinator_close = self._request("token-admin", "POST", f"/api/driver-supports/{support['id']}/close")
        self.assertEqual(coordinator_close.status_code, 200, coordinator_close.get_json())
        self.assertEqual(coordinator_close.get_json()["driver"]["status"], tour_app.DRIVER_AVAILABLE)

    def test_support_only_grant_receives_driver_and_support_data_in_bootstrap(self) -> None:
        account = next(item for item in self.database["users"] if item["id"] == "user_one")
        account["permissions"] = [
            tour_app.PERMISSION_MANAGE_DRIVER_SUPPORT,
            tour_app.PERMISSION_CHECK_IN,
        ]
        support = self._start_own_support()

        bootstrap = self._request("token-one", "GET", "/api/bootstrap")
        self.assertEqual(bootstrap.status_code, 200, bootstrap.get_json())
        data = bootstrap.get_json()["data"]
        self.assertTrue(any(item["id"] == "drv_one" for item in data["drivers"]))
        self.assertEqual(data["driverSupports"][0]["id"], support["id"])

    def test_support_rejects_missing_checkin_tour_and_hostess_conflicts(self) -> None:
        missing_checkin = self._request(
            "token-admin",
            "POST",
            "/api/driver-supports",
            json={"driverId": "drv_without_checkin", "location": "Lobby"},
        )
        self.assertEqual(missing_checkin.status_code, 409, missing_checkin.get_json())

        driver = self.database["drivers"][0]
        driver.update({"status": tour_app.DRIVER_HOSTESS_SUPPORT, "hostessAvailable": True})
        hostess_conflict = self._request(
            "token-one",
            "POST",
            "/api/driver-supports",
            json={"location": "Casa"},
        )
        self.assertEqual(hostess_conflict.status_code, 409, hostess_conflict.get_json())

        driver.update({"status": tour_app.DRIVER_IN_TOUR, "hostessAvailable": False})
        self.database["tours"] = [{
            "id": "tour_active",
            "groupName": "Tour em andamento",
            "status": tour_app.STATE_IN_TOUR,
            "allocations": [{"driverId": "drv_one", "cartId": "cart_one"}],
        }]
        tour_conflict = self._request(
            "token-one",
            "POST",
            "/api/driver-supports",
            json={"location": "Casa"},
        )
        self.assertEqual(tour_conflict.status_code, 409, tour_conflict.get_json())

    def test_open_support_blocks_tour_hostess_and_driver_record_changes(self) -> None:
        support = self._start_own_support()

        with self.assertRaises(tour_app.APIError):
            tour_app.normalized_allocations(self.database, [{"driverId": "drv_one", "cartId": "cart_one"}])

        hostess_response = self._request(
            "token-one",
            "POST",
            "/api/drivers/hostess-availability",
            json={"available": True},
        )
        self.assertEqual(hostess_response.status_code, 409, hostess_response.get_json())
        update_response = self._request(
            "token-admin",
            "PUT",
            "/api/drivers/drv_one",
            json={"name": "Nome não deve mudar"},
        )
        self.assertEqual(update_response.status_code, 409, update_response.get_json())
        delete_response = self._request("token-admin", "DELETE", "/api/drivers/drv_one")
        self.assertEqual(delete_response.status_code, 409, delete_response.get_json())
        self.assertEqual(self.database["driverSupports"][0]["id"], support["id"])

    def test_close_without_current_checkin_returns_driver_to_folga_and_reset_clears_supports(self) -> None:
        support = self._start_own_support()
        # The normal flow cannot lose a check-in mid-shift, but if an account
        # is removed from attendance the release must still avoid advertising
        # the driver as available.
        self.database["attendance"] = []
        closed = self._request("token-one", "POST", f"/api/driver-supports/{support['id']}/close")
        self.assertEqual(closed.status_code, 200, closed.get_json())
        self.assertEqual(closed.get_json()["driver"]["status"], tour_app.DRIVER_LEAVE)

        # Resetting the operational day removes historical open/closed support
        # records from the active board and clears any reservation pointers.
        self.database["driverSupports"] = [{
            "id": "support_open_after_close",
            "status": tour_app.DRIVER_SUPPORT_OPEN,
            "driverId": "drv_one",
            "location": "Casa",
        }]
        driver = self.database["drivers"][0]
        driver.update({
            "status": tour_app.DRIVER_SUPPORT,
            "driverSupportId": "support_open_after_close",
            "supportLocation": "Casa",
        })
        tour_app.reset_operational_data(self.database, "Operação de teste reiniciada.")
        self.assertEqual(self.database["driverSupports"], [])
        self.assertEqual(driver["status"], tour_app.DRIVER_LEAVE)
        self.assertIsNone(driver["driverSupportId"])
        self.assertIsNone(driver["supportLocation"])


class DriverSupportPermissionMigrationTest(unittest.TestCase):
    """Only untouched Admin/Driver role templates receive the new grant."""

    def test_migration_upgrades_complete_old_templates_but_keeps_custom_access(self) -> None:
        db = tour_app.initial_database()
        old_admin_permissions = tour_app.ordered_permissions(tour_app.PRE_DRIVER_SUPPORT_DEFAULT_PERMISSIONS[tour_app.ROLE_ADMIN])
        old_driver_permissions = tour_app.ordered_permissions(tour_app.PRE_DRIVER_SUPPORT_DEFAULT_PERMISSIONS[tour_app.ROLE_DRIVER])
        custom_driver_permissions = [item for item in old_driver_permissions if item != tour_app.PERMISSION_CHECK_IN]
        db.update({
            "operationDate": tour_app.operation_date(),
            "users": [
                {
                    "id": "admin_old_default",
                    "name": "Admin padrão antigo",
                    "username": "admin.antigo",
                    "role": tour_app.ROLE_ADMIN,
                    "permissions": old_admin_permissions,
                    "active": True,
                    "passwordHash": "unused",
                },
                {
                    "id": "driver_old_default",
                    "name": "Motorista padrão antigo",
                    "username": "motorista.antigo",
                    "role": tour_app.ROLE_DRIVER,
                    "driverId": "drv_old_default",
                    "permissions": old_driver_permissions,
                    "active": True,
                    "passwordHash": "unused",
                },
                {
                    "id": "driver_custom",
                    "name": "Motorista personalizado",
                    "username": "motorista.personalizado",
                    "role": tour_app.ROLE_DRIVER,
                    "driverId": "drv_custom",
                    "permissions": custom_driver_permissions,
                    "active": True,
                    "passwordHash": "unused",
                },
            ],
            "drivers": [
                DriverSupportApiTest._driver("drv_old_default", "Motorista padrão antigo", tour_app.DRIVER_LEAVE),
                DriverSupportApiTest._driver("drv_custom", "Motorista personalizado", tour_app.DRIVER_LEAVE),
            ],
        })
        db.pop("driverSupports", None)

        with patch.object(tour_app, "load_database", return_value=db), patch.object(tour_app, "save_database"):
            migrated = tour_app.operational_database()

        accounts = {item["id"]: item for item in migrated["users"]}
        self.assertIn(tour_app.PERMISSION_MANAGE_DRIVER_SUPPORT, accounts["admin_old_default"]["permissions"])
        self.assertIn(tour_app.PERMISSION_MANAGE_DRIVER_SUPPORT, accounts["driver_old_default"]["permissions"])
        self.assertNotIn(tour_app.PERMISSION_MANAGE_DRIVER_SUPPORT, accounts["driver_custom"]["permissions"])
        self.assertEqual(accounts["driver_custom"]["permissions"], custom_driver_permissions)
        self.assertEqual(migrated["driverSupports"], [])

    def test_reconciliation_restores_open_support_status_and_releases_orphaned_marker(self) -> None:
        db = tour_app.initial_database()
        today = tour_app.operation_date()
        db.update({
            "operationDate": today,
            "users": [{
                "id": "user_driver",
                "name": "Motorista em apoio",
                "username": "motorista.apoio",
                "role": tour_app.ROLE_DRIVER,
                "driverId": "drv_reconcile",
                "permissions": tour_app.default_permissions_for_role(tour_app.ROLE_DRIVER),
                "active": True,
                "passwordHash": "unused",
            }],
            "drivers": [DriverSupportApiTest._driver("drv_reconcile", "Motorista em apoio")],
            "attendance": [{"id": "checkin", "userId": "user_driver", "operationDate": today, "status": "TRABALHANDO"}],
            "driverSupports": [{
                "id": "support_reconcile",
                "status": tour_app.DRIVER_SUPPORT_OPEN,
                "driverId": "drv_reconcile",
                "driverName": "Motorista em apoio",
                "location": "Galeria",
                "note": "",
                "operationDate": today,
                "startedAt": "2026-09-03T12:00:00+00:00",
                "createdAt": "2026-09-03T12:00:00+00:00",
                "updatedAt": "2026-09-03T12:00:00+00:00",
            }],
        })

        with patch.object(tour_app, "load_database", return_value=db), patch.object(tour_app, "save_database"):
            migrated = tour_app.operational_database()

        driver = migrated["drivers"][0]
        self.assertEqual(driver["status"], tour_app.DRIVER_SUPPORT)
        self.assertEqual(driver["driverSupportId"], "support_reconcile")
        self.assertEqual(driver["supportLocation"], "Galeria")

        migrated["driverSupports"] = []
        self.assertTrue(tour_app.reconcile_driver_supports(migrated))
        self.assertEqual(driver["status"], tour_app.DRIVER_AVAILABLE)
        self.assertIsNone(driver["driverSupportId"])


if __name__ == "__main__":
    unittest.main()
