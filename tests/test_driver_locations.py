"""Regression coverage for private, on-duty driver locations.

Run with:
    python -m unittest tests.test_driver_locations
"""

from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app as tour_app  # noqa: E402


class DriverLocationApiTest(unittest.TestCase):
    """A precise point exists only inside an authorized sharing session."""

    OPERATION_DAY = "2026-09-05"
    SALVADOR_TZ = ZoneInfo("America/Bahia")

    def setUp(self) -> None:
        self.operation_date_patcher = patch.object(tour_app, "operation_date", return_value=self.OPERATION_DAY)
        self.operation_date_patcher.start()
        self.addCleanup(self.operation_date_patcher.stop)

        self.database = self._database()
        self.patchers = [
            patch.object(tour_app, "POSTGRES_URL", ""),
            patch.object(tour_app, "operational_database", return_value=self.database),
            patch.object(tour_app, "save_database", return_value=None),
            patch.object(
                tour_app,
                "driver_location_now",
                return_value=datetime(2026, 9, 5, 14, 0, tzinfo=self.SALVADOR_TZ),
                create=True,
            ),
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
            "token-driver": {"userId": "user_driver", "expiresAt": expiry},
            "token-no-share": {"userId": "user_no_share", "expiresAt": expiry},
            "token-unlinked": {"userId": "user_unlinked", "expiresAt": expiry},
            "token-hostess": {"userId": "user_hostess", "expiresAt": expiry},
            "token-viewer": {"userId": "user_viewer", "expiresAt": expiry},
        })
        self.client = tour_app.app.test_client()

    @staticmethod
    def _account(
        user_id: str,
        name: str,
        role: str,
        permissions: list[str],
        driver_id: str | None = None,
    ) -> dict:
        account = {
            "id": user_id,
            "name": name,
            "username": user_id,
            "role": role,
            "permissions": permissions,
            "active": True,
            "passwordHash": "unused-in-session-tests",
            "createdAt": "2026-09-05T10:00:00+00:00",
        }
        if driver_id:
            account["driverId"] = driver_id
        return account

    @staticmethod
    def _driver(driver_id: str, name: str) -> dict:
        return {
            "id": driver_id,
            "name": name,
            "active": True,
            "status": tour_app.DRIVER_AVAILABLE,
            "toursStarted": 2,
            "homePickups": 1,
            "hostessAvailable": False,
            "hostessRequestId": None,
            "driverSupportId": None,
            "supportLocation": None,
            "lastActivity": "2026-09-05T10:00:00+00:00",
        }

    @classmethod
    def _database(cls) -> dict:
        db = tour_app.initial_database()
        db.update({
            "operationDate": cls.OPERATION_DAY,
            "users": [
                cls._account(
                    "user_admin",
                    "Administrador",
                    tour_app.ROLE_ADMIN,
                    tour_app.default_permissions_for_role(tour_app.ROLE_ADMIN),
                ),
                cls._account(
                    "user_driver",
                    "Motorista Localizado",
                    tour_app.ROLE_DRIVER,
                    tour_app.default_permissions_for_role(tour_app.ROLE_DRIVER),
                    "drv_one",
                ),
                cls._account(
                    "user_no_share",
                    "Motorista Sem Permissão",
                    tour_app.ROLE_DRIVER,
                    [tour_app.PERMISSION_CHECK_IN],
                    "drv_no_share",
                ),
                cls._account(
                    "user_unlinked",
                    "Motorista Sem Vínculo",
                    tour_app.ROLE_DRIVER,
                    [tour_app.PERMISSION_SHARE_OWN_LOCATION],
                ),
                # Even an explicitly granted non-driver cannot publish a point.
                cls._account(
                    "user_hostess",
                    "Hostess Mapa",
                    tour_app.ROLE_HOSTESS,
                    [
                        tour_app.PERMISSION_VIEW_DRIVER_LOCATIONS,
                        tour_app.PERMISSION_REQUEST_HOSTESS_CAR,
                        tour_app.PERMISSION_CHECK_IN,
                    ],
                ),
                cls._account(
                    "user_viewer",
                    "Painel Somente Leitura",
                    tour_app.ROLE_VIEWER,
                    [tour_app.PERMISSION_VIEW_DASHBOARD],
                ),
            ],
            "drivers": [
                cls._driver("drv_one", "Motorista Localizado"),
                cls._driver("drv_no_share", "Motorista Sem Permissão"),
            ],
            "consultants": [
                {"id": "con_one", "name": "Consultora Um", "active": True},
                {"id": "con_two", "name": "Consultor Dois", "active": True},
                {"id": "con_inactive", "name": "Consultora Inativa", "active": False},
            ],
            "attendance": [
                {
                    "id": "checkin_one",
                    "userId": "user_driver",
                    "userName": "Motorista Localizado",
                    "role": tour_app.ROLE_DRIVER,
                    "status": "TRABALHANDO",
                    "operationDate": cls.OPERATION_DAY,
                    "checkInAt": "2026-09-05T10:00:00+00:00",
                },
                {
                    "id": "checkin_no_share",
                    "userId": "user_no_share",
                    "status": "TRABALHANDO",
                    "operationDate": cls.OPERATION_DAY,
                },
                {
                    "id": "checkin_hostess",
                    "userId": "user_hostess",
                    "userName": "Hostess Mapa",
                    "role": tour_app.ROLE_HOSTESS,
                    "status": "TRABALHANDO",
                    "operationDate": cls.OPERATION_DAY,
                    "checkInAt": "2026-09-05T10:00:00+00:00",
                },
            ],
            "driverLocations": {},
            "activities": [],
        })
        return db

    def _request(self, token: str | None, method: str, path: str, **kwargs):
        headers = dict(kwargs.pop("headers", {}))
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return self.client.open(path, method=method, headers=headers, **kwargs)

    def _start(self, attendance_id: str = "checkin_one") -> dict:
        response = self._request(
            "token-driver",
            "POST",
            "/api/drivers/me/location-sharing",
            json={"attendanceId": attendance_id},
        )
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()

    def _update(self, sharing_id: str, **changes):
        payload = {
            "attendanceId": "checkin_one",
            "sharingId": sharing_id,
            "latitude": -12.57123456,
            "longitude": -38.00567891,
            "accuracy": 12.34,
            **changes,
        }
        return self._request(
            "token-driver",
            "PUT",
            "/api/drivers/me/location",
            json=payload,
        )

    def _create_public_support_request(self, consultant_id: str = "con_one") -> tuple[dict, str]:
        response = self._request(
            None,
            "POST",
            "/api/public/consultant-support-requests",
            json={"consultantId": consultant_id, "note": "Apoio na saída do tour"},
        )
        self.assertEqual(response.status_code, 201, response.get_json())
        payload = response.get_json()
        self.assertIsInstance(payload.get("request"), dict)
        self.assertTrue(payload.get("accessToken"))
        return payload["request"], payload["accessToken"]

    def _public_support_status(self, request_id: str, access_token: str | None):
        headers = {"X-Support-Access-Token": access_token} if access_token else {}
        return self._request(
            None,
            "GET",
            f"/api/public/consultant-support-requests/{request_id}",
            headers=headers,
        )

    def _set_location_test_mode(
        self,
        active: bool,
        token: str = "token-admin",
        driver_id: str | None = "drv_one",
    ):
        payload = {"active": active}
        if active and driver_id is not None:
            payload["driverId"] = driver_id
        return self._request(
            token,
            "POST",
            "/api/operation/driver-location-test",
            json=payload,
        )

    @staticmethod
    def _at_salvador_time(hour: int, minute: int = 0, second: int = 0):
        """Freeze the location policy at a wall time in Salvador."""
        local_time = datetime(2026, 9, 5, hour, minute, second, tzinfo=ZoneInfo("America/Bahia"))
        return patch.object(tour_app, "driver_location_now", return_value=local_time, create=True)

    @staticmethod
    def _assert_no_precise_location_keys(test_case: unittest.TestCase, payload: object) -> None:
        encoded = json.dumps(payload, ensure_ascii=False)
        for key in ("driverLocations", "latitude", "longitude", "accuracy", "attendanceId", "sharingId"):
            test_case.assertNotIn(f'"{key}"', encoded)

    def test_authorization_and_on_duty_rules_are_enforced(self) -> None:
        unauthenticated = self._request(
            None,
            "POST",
            "/api/drivers/me/location-sharing",
            json={"attendanceId": "checkin_one"},
        )
        self.assertEqual(unauthenticated.status_code, 401, unauthenticated.get_json())

        no_permission = self._request(
            "token-no-share",
            "POST",
            "/api/drivers/me/location-sharing",
            json={"attendanceId": "checkin_no_share"},
        )
        self.assertEqual(no_permission.status_code, 403, no_permission.get_json())

        wrong_role = self._request(
            "token-hostess",
            "POST",
            "/api/drivers/me/location-sharing",
            json={"attendanceId": "any"},
        )
        self.assertEqual(wrong_role.status_code, 403, wrong_role.get_json())

        unlinked = self._request(
            "token-unlinked",
            "POST",
            "/api/drivers/me/location-sharing",
            json={"attendanceId": "any"},
        )
        self.assertEqual(unlinked.status_code, 409, unlinked.get_json())

        wrong_checkin = self._request(
            "token-driver",
            "POST",
            "/api/drivers/me/location-sharing",
            json={"attendanceId": "checkin_from_another_shift"},
        )
        self.assertEqual(wrong_checkin.status_code, 409, wrong_checkin.get_json())

        attendance = self.database["attendance"].pop(0)
        without_checkin = self._request(
            "token-driver",
            "POST",
            "/api/drivers/me/location-sharing",
            json={"attendanceId": "checkin_one"},
        )
        self.assertEqual(without_checkin.status_code, 409, without_checkin.get_json())
        self.database["attendance"].insert(0, attendance)

        self.database["drivers"][0]["status"] = tour_app.DRIVER_LEAVE
        off_duty = self._request(
            "token-driver",
            "POST",
            "/api/drivers/me/location-sharing",
            json={"attendanceId": "checkin_one"},
        )
        self.assertEqual(off_duty.status_code, 409, off_duty.get_json())
        self.assertEqual(self.database["driverLocations"], {})

        forbidden_read = self._request("token-viewer", "GET", "/api/driver-locations")
        self.assertEqual(forbidden_read.status_code, 403, forbidden_read.get_json())

    def test_only_hostess_role_can_receive_the_internal_location_map(self) -> None:
        session = self._start()
        updated = self._update(session["sharingId"])
        self.assertEqual(updated.status_code, 200, updated.get_json())

        hostess = self._request("token-hostess", "GET", "/api/driver-locations")
        self.assertEqual(hostess.status_code, 200, hostess.get_json())
        self.assertEqual(len(hostess.get_json()["locations"]), 1)

        # A stale or manually edited permission list must not bypass the
        # role-level policy or make the frontend render the map.
        for user_id, token in (("user_admin", "token-admin"), ("user_driver", "token-driver")):
            account = next(item for item in self.database["users"] if item["id"] == user_id)
            account["permissions"] = list({
                *account.get("permissions", []),
                tour_app.PERMISSION_VIEW_DRIVER_LOCATIONS,
            })
            with self.subTest(role=account["role"], surface="endpoint"):
                denied = self._request(token, "GET", "/api/driver-locations")
                self.assertEqual(denied.status_code, 403, denied.get_json())
            with self.subTest(role=account["role"], surface="bootstrap"):
                bootstrap = self._request(token, "GET", "/api/bootstrap")
                self.assertEqual(bootstrap.status_code, 200, bootstrap.get_json())
                self.assertNotIn(
                    tour_app.PERMISSION_VIEW_DRIVER_LOCATIONS,
                    bootstrap.get_json()["user"]["permissions"],
                )

        self.assertIn(
            tour_app.PERMISSION_VIEW_DRIVER_LOCATIONS,
            tour_app.default_permissions_for_role(tour_app.ROLE_HOSTESS),
        )
        self.assertNotIn(
            tour_app.PERMISSION_VIEW_DRIVER_LOCATIONS,
            tour_app.default_permissions_for_role(tour_app.ROLE_DRIVER),
        )
        self.assertNotIn(
            tour_app.PERMISSION_VIEW_DRIVER_LOCATIONS,
            tour_app.default_permissions_for_role(tour_app.ROLE_ADMIN),
        )

    def test_session_rotation_update_and_explicit_stop(self) -> None:
        driver = self.database["drivers"][0]
        last_operational_activity = driver["lastActivity"]
        first_session = self._start()
        second_session = self._start()
        self.assertNotEqual(first_session["sharingId"], second_session["sharingId"])

        superseded = self._update(first_session["sharingId"])
        self.assertEqual(superseded.status_code, 409, superseded.get_json())

        updated = self._update(second_session["sharingId"])
        self.assertEqual(updated.status_code, 200, updated.get_json())
        record = self.database["driverLocations"]["drv_one"]
        self.assertEqual(record["attendanceId"], "checkin_one")
        self.assertEqual(record["sharingId"], second_session["sharingId"])
        self.assertEqual(record["latitude"], -12.571235)
        self.assertEqual(record["longitude"], -38.005679)
        self.assertEqual(record["accuracy"], 12.3)
        self.assertEqual(driver["lastActivity"], last_operational_activity)

        visible = self._request("token-hostess", "GET", "/api/driver-locations")
        self.assertEqual(visible.status_code, 200, visible.get_json())
        self.assertEqual(visible.headers.get("Cache-Control"), "private, no-store")
        self.assertEqual(len(visible.get_json()["locations"]), 1)
        self.assertNotIn("attendanceId", visible.get_json()["locations"][0])
        self.assertNotIn("sharingId", visible.get_json()["locations"][0])

        stopped = self._request("token-driver", "DELETE", "/api/drivers/me/location-sharing")
        self.assertEqual(stopped.status_code, 200, stopped.get_json())
        self.assertTrue(stopped.get_json()["removed"])
        self.assertEqual(self.database["driverLocations"], {})

        delayed_callback = self._update(second_session["sharingId"])
        self.assertEqual(delayed_callback.status_code, 409, delayed_callback.get_json())
        stopped_again = self._request("token-driver", "DELETE", "/api/drivers/me/location-sharing")
        self.assertEqual(stopped_again.status_code, 200, stopped_again.get_json())
        self.assertFalse(stopped_again.get_json()["removed"])

    def test_salvador_cutoff_blocks_post_put_and_get_at_exactly_15h(self) -> None:
        # Render commonly runs in UTC. Freezing 17:59:59 UTC proves the rule is
        # evaluated as 14:59:59 in Salvador rather than against the host clock.
        with self._at_salvador_time(14, 59, 59):
            session = self._start()
            before_cutoff = self._update(session["sharingId"])
            self.assertEqual(before_cutoff.status_code, 200, before_cutoff.get_json())
            visible = self._request("token-hostess", "GET", "/api/driver-locations")
            self.assertEqual(visible.status_code, 200, visible.get_json())
            visible_payload = visible.get_json()
            self.assertEqual(len(visible_payload["locations"]), 1)
            self.assertTrue(visible_payload["sharingWindowOpen"])
            self.assertEqual(visible_payload["sharingEndsAt"], "15:00")

        with self._at_salvador_time(15, 0, 0):
            delayed_callback = self._update(session["sharingId"])
            self.assertEqual(delayed_callback.status_code, 409, delayed_callback.get_json())

            hidden = self._request("token-hostess", "GET", "/api/driver-locations")
            self.assertEqual(hidden.status_code, 200, hidden.get_json())
            hidden_payload = hidden.get_json()
            self.assertEqual(hidden_payload["locations"], [])
            self.assertFalse(hidden_payload["sharingWindowOpen"])
            self.assertEqual(hidden_payload["sharingEndsAt"], "15:00")
            self.assertEqual(self.database["driverLocations"], {})

            # POST needs its own guard; an empty store must not allow a fresh
            # sharing session to be created after the deadline.
            self.database["driverLocations"] = {}
            late_start = self._request(
                "token-driver",
                "POST",
                "/api/drivers/me/location-sharing",
                json={"attendanceId": "checkin_one"},
            )
            self.assertEqual(late_start.status_code, 409, late_start.get_json())
            self.assertEqual(self.database["driverLocations"], {})

    def test_test_mode_deadline_is_fail_closed_when_absent_or_malformed(self) -> None:
        self.assertNotIn("driverLocationTestUntil", tour_app.initial_database())
        self.assertNotIn("driverLocationTestDriverId", tour_app.initial_database())
        self.assertEqual(
            tour_app.parse_driver_location_test_until("2026-09-05T16:30:00-03:00"),
            datetime(2026, 9, 5, 19, 30, tzinfo=timezone.utc),
        )

        invalid_values = (
            None,
            "",
            "not-an-iso-timestamp",
            "2026-09-05T16:30:00",  # Never inherit the host timezone.
            ["2026-09-05T19:30:00Z"],
            "x" * 129,
        )
        with self._at_salvador_time(15, 1, 0):
            for value in invalid_values:
                with self.subTest(value=value):
                    if value is None:
                        self.database.pop("driverLocationTestUntil", None)
                    else:
                        self.database["driverLocationTestUntil"] = value

                    window = tour_app.driver_location_window_payload(db=self.database)
                    self.assertFalse(window["sharingWindowOpen"])
                    self.assertFalse(window["locationTestModeActive"])
                    self.assertIsNone(window["locationTestModeEndsAt"])
                    self.assertEqual(window["sharingEndsAt"], "15:00")

                    late_start = self._request(
                        "token-driver",
                        "POST",
                        "/api/drivers/me/location-sharing",
                        json={"attendanceId": "checkin_one"},
                    )
                    self.assertEqual(late_start.status_code, 409, late_start.get_json())
                    self.assertEqual(self.database["driverLocations"], {})

    def test_admin_test_mode_extends_only_the_time_window_for_thirty_minutes(self) -> None:
        with self._at_salvador_time(15, 10, 0):
            unauthenticated = self._set_location_test_mode(True, token="")
            denied = self._set_location_test_mode(True, token="token-hostess")
            invalid = self._request(
                "token-admin",
                "POST",
                "/api/operation/driver-location-test",
                json={"active": "true"},
            )
            missing_driver = self._set_location_test_mode(True, driver_id=None)
            unknown_driver = self._set_location_test_mode(True, driver_id="drv_missing")
            ineligible_driver = self._set_location_test_mode(True, driver_id="drv_no_share")
            self.assertEqual(unauthenticated.status_code, 401, unauthenticated.get_json())
            self.assertEqual(denied.status_code, 403, denied.get_json())
            self.assertEqual(invalid.status_code, 400, invalid.get_json())
            self.assertEqual(missing_driver.status_code, 400, missing_driver.get_json())
            self.assertEqual(unknown_driver.status_code, 404, unknown_driver.get_json())
            self.assertEqual(ineligible_driver.status_code, 409, ineligible_driver.get_json())

            enabled = self._set_location_test_mode(True)
            self.assertEqual(enabled.status_code, 200, enabled.get_json())
            expected_until = "2026-09-05T18:40:00+00:00"
            self.assertEqual(self.database["driverLocationTestUntil"], expected_until)
            self.assertEqual(self.database["driverLocationTestDriverId"], "drv_one")
            settings = enabled.get_json()["operationSettings"]
            self.assertTrue(settings["locationTestModeActive"])
            self.assertEqual(settings["locationTestModeEndsAt"], expected_until)
            self.assertEqual(settings["locationTestDriverId"], "drv_one")
            self.assertEqual(settings["locationTestDriverName"], "Motorista Localizado")

            for token in ("token-admin", "token-hostess", "token-driver"):
                bootstrap = self._request(token, "GET", "/api/bootstrap")
                self.assertEqual(bootstrap.status_code, 200, bootstrap.get_json())
                visible_settings = bootstrap.get_json()["data"]["operationSettings"]
                self.assertTrue(visible_settings["locationTestModeActive"])
                self.assertEqual(visible_settings["locationTestDriverId"], "drv_one")
                if token in {"token-admin", "token-driver"}:
                    test_activity = bootstrap.get_json()["data"]["activities"][0]
                    self.assertEqual(test_activity["audit"]["driverId"], "drv_one")
                    self.assertIn("Motorista Localizado", test_activity["message"])
            for token in ("token-viewer", "token-no-share"):
                bootstrap = self._request(token, "GET", "/api/bootstrap")
                self.assertEqual(bootstrap.status_code, 200, bootstrap.get_json())
                hidden_settings = bootstrap.get_json()["data"]["operationSettings"]
                self.assertFalse(hidden_settings["locationTestModeActive"])
                self.assertIsNone(hidden_settings["locationTestModeEndsAt"])
                self.assertIsNone(hidden_settings["locationTestDriverId"])
                self.assertIsNone(hidden_settings["locationTestDriverName"])
            hidden_activity = self._request(
                "token-viewer", "GET", "/api/bootstrap"
            ).get_json()["data"]["activities"][0]
            encoded_hidden_activity = json.dumps(hidden_activity, ensure_ascii=False)
            self.assertNotIn("drv_one", encoded_hidden_activity)
            self.assertNotIn("Motorista Localizado", encoded_hidden_activity)
            self.assertEqual(
                hidden_activity["audit"]["action"],
                "DRIVER_LOCATION_TEST_ENABLED",
            )

            # The override suspends only the time cutoff. Role, grant and
            # active-attendance checks remain mandatory.
            no_permission = self._request(
                "token-no-share",
                "POST",
                "/api/drivers/me/location-sharing",
                json={"attendanceId": "checkin_no_share"},
            )
            wrong_role = self._request(
                "token-hostess",
                "POST",
                "/api/drivers/me/location-sharing",
                json={"attendanceId": "checkin_one"},
            )
            self.assertEqual(no_permission.status_code, 403, no_permission.get_json())
            self.assertEqual(wrong_role.status_code, 403, wrong_role.get_json())

            no_share_account = next(
                item for item in self.database["users"] if item["id"] == "user_no_share"
            )
            no_share_account["permissions"].append(tour_app.PERMISSION_SHARE_OWN_LOCATION)
            not_selected = self._request(
                "token-no-share",
                "POST",
                "/api/drivers/me/location-sharing",
                json={"attendanceId": "checkin_no_share"},
            )
            self.assertEqual(not_selected.status_code, 409, not_selected.get_json())

            attendance = self.database["attendance"].pop(0)
            without_checkin = self._request(
                "token-driver",
                "POST",
                "/api/drivers/me/location-sharing",
                json={"attendanceId": "checkin_one"},
            )
            self.assertEqual(without_checkin.status_code, 409, without_checkin.get_json())
            self.database["attendance"].insert(0, attendance)

            session = self._start()
            self.assertTrue(session["locationTestModeActive"])
            self.assertEqual(session["locationTestModeEndsAt"], expected_until)
            self.assertEqual(session["locationTestDriverId"], "drv_one")
            self.assertEqual(session["locationTestDriverName"], "Motorista Localizado")
            self.assertEqual(session["sharingEndsAt"], "2026-09-05T15:40:00-03:00")
            updated = self._update(session["sharingId"])
            self.assertEqual(updated.status_code, 200, updated.get_json())
            self.assertTrue(updated.get_json()["locationTestModeActive"])

            hostess = self._request("token-hostess", "GET", "/api/driver-locations")
            self.assertEqual(hostess.status_code, 200, hostess.get_json())
            self.assertEqual(len(hostess.get_json()["locations"]), 1)
            self.assertTrue(hostess.get_json()["locationTestModeActive"])
            self.assertEqual(hostess.get_json()["locationTestDriverId"], "drv_one")
            self.assertEqual(hostess.get_json()["locationTestDriverName"], "Motorista Localizado")
            for token in ("token-driver", "token-admin"):
                forbidden = self._request(token, "GET", "/api/driver-locations")
                self.assertEqual(forbidden.status_code, 403, forbidden.get_json())

            support_request, access_token = self._create_public_support_request()
            accepted = self._request(
                "token-driver",
                "POST",
                "/api/drivers/hostess-availability",
                json={"available": True, "requestId": support_request["id"]},
            )
            self.assertEqual(accepted.status_code, 200, accepted.get_json())
            for missing_or_wrong_token in (None, "wrong-capability"):
                hidden = self._public_support_status(
                    support_request["id"],
                    missing_or_wrong_token,
                )
                self.assertEqual(hidden.status_code, 404, hidden.get_json())
            tracked = self._public_support_status(support_request["id"], access_token)
            self.assertEqual(tracked.status_code, 200, tracked.get_json())
            self.assertIsNotNone(tracked.get_json()["location"])
            self.assertTrue(tracked.get_json()["locationTestModeActive"])
            self.assertIsNone(tracked.get_json()["locationTestDriverId"])
            self.assertIsNone(tracked.get_json()["locationTestDriverName"])

            forbidden_stop = self._set_location_test_mode(False, token="token-hostess")
            self.assertEqual(forbidden_stop.status_code, 403, forbidden_stop.get_json())
            self.assertEqual(self.database["driverLocationTestUntil"], expected_until)
            self.assertIn("drv_one", self.database["driverLocations"])

            disabled = self._set_location_test_mode(False)
            self.assertEqual(disabled.status_code, 200, disabled.get_json())
            self.assertNotIn("driverLocationTestUntil", self.database)
            self.assertNotIn("driverLocationTestDriverId", self.database)
            self.assertEqual(self.database["driverLocations"], {})
            self.assertFalse(disabled.get_json()["operationSettings"]["locationTestModeActive"])
            self.assertIsNone(disabled.get_json()["operationSettings"]["locationTestModeEndsAt"])
            self.assertIsNone(disabled.get_json()["operationSettings"]["locationTestDriverId"])
            self.assertIsNone(disabled.get_json()["operationSettings"]["locationTestDriverName"])
            delayed_callback = self._update(session["sharingId"])
            self.assertEqual(delayed_callback.status_code, 409, delayed_callback.get_json())

    def test_test_mode_expiry_blocks_writes_and_purges_at_the_exact_deadline(self) -> None:
        with self._at_salvador_time(15, 20, 0):
            enabled = self._set_location_test_mode(True)
            self.assertEqual(enabled.status_code, 200, enabled.get_json())
            session = self._start()
            updated = self._update(session["sharingId"])
            self.assertEqual(updated.status_code, 200, updated.get_json())
            support_request, access_token = self._create_public_support_request()
            accepted = self._request(
                "token-driver",
                "POST",
                "/api/drivers/hostess-availability",
                json={"available": True, "requestId": support_request["id"]},
            )
            self.assertEqual(accepted.status_code, 200, accepted.get_json())
            self.assertIsNotNone(
                self._public_support_status(support_request["id"], access_token).get_json()["location"]
            )
            stored_point = dict(self.database["driverLocations"]["drv_one"])

        # The deadline is exclusive: exactly 30 minutes later the callback is
        # rejected and its previously accepted precise point is erased.
        with self._at_salvador_time(15, 50, 0):
            expired_callback = self._update(session["sharingId"])
            self.assertEqual(expired_callback.status_code, 409, expired_callback.get_json())
            self.assertEqual(self.database["driverLocations"], {})
            self.assertNotIn("driverLocationTestUntil", self.database)
            self.assertNotIn("driverLocationTestDriverId", self.database)

            # Starting a new session has the same centralized purge behavior.
            self.database["driverLocations"]["drv_one"] = stored_point
            expired_start = self._request(
                "token-driver",
                "POST",
                "/api/drivers/me/location-sharing",
                json={"attendanceId": "checkin_one"},
            )
            self.assertEqual(expired_start.status_code, 409, expired_start.get_json())
            self.assertEqual(self.database["driverLocations"], {})

            hostess = self._request("token-hostess", "GET", "/api/driver-locations")
            self.assertEqual(hostess.status_code, 200, hostess.get_json())
            payload = hostess.get_json()
            self.assertEqual(payload["locations"], [])
            self.assertFalse(payload["sharingWindowOpen"])
            self.assertFalse(payload["locationTestModeActive"])
            self.assertIsNone(payload["locationTestModeEndsAt"])
            self.assertEqual(payload["sharingEndsAt"], "15:00")

            public = self._public_support_status(support_request["id"], access_token)
            self.assertEqual(public.status_code, 200, public.get_json())
            self.assertIsNone(public.get_json()["location"])
            self.assertFalse(public.get_json()["sharingWindowOpen"])
            self.assertFalse(public.get_json()["locationTestModeActive"])
            wrong_capability = self._public_support_status(
                support_request["id"],
                "wrong-capability",
            )
            self.assertEqual(wrong_capability.status_code, 404, wrong_capability.get_json())

    def test_test_selection_scopes_after_hours_but_not_the_regular_window(self) -> None:
        second_account = next(
            item for item in self.database["users"] if item["id"] == "user_no_share"
        )
        second_account["permissions"] = tour_app.default_permissions_for_role(
            tour_app.ROLE_DRIVER
        )

        # Before 15:00 the test selection does not restrict ordinary sharing.
        with self._at_salvador_time(14, 30, 0):
            enabled = self._set_location_test_mode(True, driver_id="drv_one")
            self.assertEqual(enabled.status_code, 200, enabled.get_json())
            second_start = self._request(
                "token-no-share",
                "POST",
                "/api/drivers/me/location-sharing",
                json={"attendanceId": "checkin_no_share"},
            )
            self.assertEqual(second_start.status_code, 201, second_start.get_json())

        # A fresh after-hours activation for A invalidates prior ordinary
        # sessions. Only A may create a new one.
        with self._at_salvador_time(15, 10, 0):
            enabled = self._set_location_test_mode(True, driver_id="drv_one")
            self.assertEqual(enabled.status_code, 200, enabled.get_json())
            self.assertEqual(self.database["driverLocations"], {})
            blocked_second = self._request(
                "token-no-share",
                "POST",
                "/api/drivers/me/location-sharing",
                json={"attendanceId": "checkin_no_share"},
            )
            self.assertEqual(blocked_second.status_code, 409, blocked_second.get_json())

            first_session = self._start()
            first_update = self._update(first_session["sharingId"])
            self.assertEqual(first_update.status_code, 200, first_update.get_json())

            # A consultant assigned to B cannot infer A's test selection or
            # receive either driver's precise point.
            support_request, access_token = self._create_public_support_request()
            accepted = self._request(
                "token-no-share",
                "POST",
                "/api/drivers/hostess-availability",
                json={"available": True, "requestId": support_request["id"]},
            )
            self.assertEqual(accepted.status_code, 200, accepted.get_json())
            point_time = tour_app.driver_location_now().astimezone(timezone.utc).isoformat()
            self.database["driverLocations"]["drv_no_share"] = {
                "driverId": "drv_no_share",
                "attendanceId": "checkin_no_share",
                "sharingId": "location_not_selected",
                "operationDate": self.OPERATION_DAY,
                "latitude": -12.5,
                "longitude": -38.1,
                "accuracy": 9.0,
                "startedAt": point_time,
                "updatedAt": point_time,
            }
            public = self._public_support_status(support_request["id"], access_token)
            self.assertEqual(public.status_code, 200, public.get_json())
            public_payload = public.get_json()
            self.assertIsNone(public_payload["location"])
            self.assertFalse(public_payload["sharingWindowOpen"])
            self.assertFalse(public_payload["locationTestModeActive"])
            self.assertIsNone(public_payload["locationTestDriverId"])
            self.assertIsNone(public_payload["locationTestDriverName"])
            self.assertEqual(set(self.database["driverLocations"]), {"drv_one"})

            # Switching A -> B after cutoff removes A's point/session and B
            # must explicitly start sharing. Renewing B keeps that new session.
            switched = self._set_location_test_mode(True, driver_id="drv_no_share")
            self.assertEqual(switched.status_code, 200, switched.get_json())
            switched_settings = switched.get_json()["operationSettings"]
            self.assertEqual(switched_settings["locationTestDriverId"], "drv_no_share")
            self.assertEqual(switched_settings["locationTestDriverName"], "Motorista Sem Permissão")
            self.assertEqual(self.database["driverLocations"], {})
            rejected_old_session = self._update(first_session["sharingId"])
            self.assertEqual(rejected_old_session.status_code, 409, rejected_old_session.get_json())

            second_start = self._request(
                "token-no-share",
                "POST",
                "/api/drivers/me/location-sharing",
                json={"attendanceId": "checkin_no_share"},
            )
            self.assertEqual(second_start.status_code, 201, second_start.get_json())
            second_update = self._request(
                "token-no-share",
                "PUT",
                "/api/drivers/me/location",
                json={
                    "attendanceId": "checkin_no_share",
                    "sharingId": second_start.get_json()["sharingId"],
                    "latitude": -12.55,
                    "longitude": -38.05,
                    "accuracy": 8,
                },
            )
            self.assertEqual(second_update.status_code, 200, second_update.get_json())
            renewed = self._set_location_test_mode(True, driver_id="drv_no_share")
            self.assertEqual(renewed.status_code, 200, renewed.get_json())
            self.assertIn("drv_no_share", self.database["driverLocations"])

            hostess = self._request("token-hostess", "GET", "/api/driver-locations")
            self.assertEqual(hostess.status_code, 200, hostess.get_json())
            self.assertEqual(
                [item["driverId"] for item in hostess.get_json()["locations"]],
                ["drv_no_share"],
            )

            audit = self.database["activities"][0]["audit"]
            self.assertEqual(audit["action"], "DRIVER_LOCATION_TEST_ENABLED")
            self.assertEqual(audit["driverId"], "drv_no_share")
            self.assertEqual(audit["previousDriverId"], "drv_no_share")

    def test_test_target_must_remain_active_and_linked(self) -> None:
        driver = next(item for item in self.database["drivers"] if item["id"] == "drv_one")
        account = next(item for item in self.database["users"] if item["id"] == "user_driver")

        with self._at_salvador_time(15, 5, 0):
            driver["active"] = False
            inactive = self._set_location_test_mode(True, driver_id="drv_one")
            self.assertEqual(inactive.status_code, 409, inactive.get_json())
            driver["active"] = True

            account["role"] = tour_app.ROLE_VIEWER
            unlinked_role = self._set_location_test_mode(True, driver_id="drv_one")
            self.assertEqual(unlinked_role.status_code, 409, unlinked_role.get_json())
            account["role"] = tour_app.ROLE_DRIVER

            enabled = self._set_location_test_mode(True, driver_id="drv_one")
            self.assertEqual(enabled.status_code, 200, enabled.get_json())
            session = self._start()
            self.assertEqual(self._update(session["sharingId"]).status_code, 200)

            # Deactivating the linked account invalidates the persisted target.
            # The next protected read clears both metadata and precise points.
            account["active"] = False
            hostess = self._request("token-hostess", "GET", "/api/driver-locations")
            self.assertEqual(hostess.status_code, 200, hostess.get_json())
            payload = hostess.get_json()
            self.assertEqual(payload["locations"], [])
            self.assertFalse(payload["locationTestModeActive"])
            self.assertIsNone(payload["locationTestDriverId"])
            self.assertNotIn("driverLocationTestUntil", self.database)
            self.assertNotIn("driverLocationTestDriverId", self.database)
            self.assertEqual(self.database["driverLocations"], {})

    def test_checkin_after_15h_does_not_open_a_location_window(self) -> None:
        self.database["attendance"] = [
            record for record in self.database["attendance"]
            if record.get("userId") != "user_driver"
        ]
        self.database["driverLocations"] = {}

        with self._at_salvador_time(15, 1, 0):
            checkin = self._request("token-driver", "POST", "/api/attendance/check-in")
            self.assertEqual(checkin.status_code, 201, checkin.get_json())
            attendance_id = checkin.get_json()["attendance"]["id"]
            self.assertIsNotNone(tour_app.attendance_for(self.database, "user_driver"))

            late_start = self._request(
                "token-driver",
                "POST",
                "/api/drivers/me/location-sharing",
                json={"attendanceId": attendance_id},
            )
            self.assertEqual(late_start.status_code, 409, late_start.get_json())
            self.assertEqual(self.database["driverLocations"], {})

            # A forged fresh record cannot bypass the read-side time guard.
            now = datetime(2026, 9, 5, 18, 1, tzinfo=timezone.utc).isoformat()
            self.database["driverLocations"]["drv_one"] = {
                "driverId": "drv_one",
                "attendanceId": attendance_id,
                "sharingId": "location_forged_after_cutoff",
                "operationDate": self.OPERATION_DAY,
                "latitude": -12.57,
                "longitude": -38.0,
                "accuracy": 10.0,
                "startedAt": now,
                "updatedAt": now,
            }
            hidden = self._request("token-hostess", "GET", "/api/driver-locations")
            self.assertEqual(hidden.status_code, 200, hidden.get_json())
            hidden_payload = hidden.get_json()
            self.assertEqual(hidden_payload["locations"], [])
            self.assertFalse(hidden_payload["sharingWindowOpen"])
            self.assertEqual(hidden_payload["sharingEndsAt"], "15:00")
            self.assertEqual(self.database["driverLocations"], {})

    def test_logout_removes_the_precise_point_immediately(self) -> None:
        session = self._start()
        updated = self._update(session["sharingId"])
        self.assertEqual(updated.status_code, 200, updated.get_json())
        self.assertIn("drv_one", self.database["driverLocations"])

        logged_out = self._request("token-driver", "POST", "/api/auth/logout")
        self.assertEqual(logged_out.status_code, 200, logged_out.get_json())
        self.assertNotIn("token-driver", tour_app.SESSIONS)
        self.assertEqual(self.database["driverLocations"], {})

    def test_closed_attendance_cannot_publish_or_expose_a_point(self) -> None:
        attendance = self.database["attendance"][0]
        attendance.update({"status": "ENCERRADO", "checkOutAt": datetime.now(timezone.utc).isoformat()})
        blocked = self._request(
            "token-driver",
            "POST",
            "/api/drivers/me/location-sharing",
            json={"attendanceId": attendance["id"]},
        )
        self.assertEqual(blocked.status_code, 409, blocked.get_json())

        now = datetime.now(timezone.utc).isoformat()
        self.database["driverLocations"]["drv_one"] = {
            "driverId": "drv_one",
            "attendanceId": attendance["id"],
            "sharingId": "location_closed_shift",
            "operationDate": self.OPERATION_DAY,
            "latitude": -12.57,
            "longitude": -38.0,
            "accuracy": 10.0,
            "startedAt": now,
            "updatedAt": now,
        }
        visible = self._request("token-hostess", "GET", "/api/driver-locations")
        self.assertEqual(visible.status_code, 200, visible.get_json())
        self.assertEqual(visible.get_json()["locations"], [])

    def test_postgres_state_payload_never_contains_precise_points(self) -> None:
        source = {
            "operationDate": self.OPERATION_DAY,
            "driverLocationTestUntil": "2026-09-05T18:40:00+00:00",
            "driverLocationTestDriverId": "drv_one",
            "driverLocations": {"drv_one": {"latitude": -12.57, "longitude": -38.0}},
            "hostessRequestLocations": {"hostreq_one": {"latitude": -12.58, "longitude": -38.01}},
            "mobileApiSessions": {"token_hash": {"userId": "user_driver"}},
        }
        sanitized = tour_app.postgres_state_payload(source)
        self.assertEqual(sanitized["driverLocations"], {})
        self.assertEqual(sanitized["hostessRequestLocations"], {})
        self.assertEqual(sanitized["mobileApiSessions"], {})
        self.assertEqual(
            sanitized["driverLocationTestUntil"],
            "2026-09-05T18:40:00+00:00",
        )
        self.assertEqual(sanitized["driverLocationTestDriverId"], "drv_one")
        self.assertIn("drv_one", source["driverLocations"])
        self.assertIn("hostreq_one", source["hostessRequestLocations"])
        self.assertIn("token_hash", source["mobileApiSessions"])

    def test_coordinate_validation_is_atomic(self) -> None:
        malformed_start = self._request(
            "token-driver",
            "POST",
            "/api/drivers/me/location-sharing",
            json=["checkin_one"],
        )
        self.assertEqual(malformed_start.status_code, 400, malformed_start.get_json())

        session = self._start()
        initial_record = dict(self.database["driverLocations"]["drv_one"])
        valid_prefix = {"attendanceId": "checkin_one", "sharingId": session["sharingId"]}
        invalid_payloads = [
            ["not-an-object"],
            {**valid_prefix, "longitude": -38.0},
            {**valid_prefix, "latitude": True, "longitude": -38.0},
            {**valid_prefix, "latitude": "nan", "longitude": -38.0},
            {**valid_prefix, "latitude": 90.000001, "longitude": -38.0},
            {**valid_prefix, "latitude": -12.5, "longitude": -180.000001},
            {**valid_prefix, "latitude": -12.5, "longitude": -38.0, "accuracy": -0.1},
            {**valid_prefix, "latitude": -12.5, "longitude": -38.0, "accuracy": 10000.1},
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self._request(
                    "token-driver",
                    "PUT",
                    "/api/drivers/me/location",
                    json=payload,
                )
                self.assertEqual(response.status_code, 400, response.get_json())
                self.assertEqual(self.database["driverLocations"]["drv_one"], initial_record)

    def test_ttl_marks_stale_and_hides_expired_points(self) -> None:
        now = tour_app.driver_location_now().astimezone(timezone.utc)
        self.database["driverLocations"]["drv_one"] = {
            "driverId": "drv_one",
            "attendanceId": "checkin_one",
            "sharingId": "location_ttl",
            "operationDate": self.OPERATION_DAY,
            "latitude": -12.57,
            "longitude": -38.00,
            "accuracy": 18.0,
            "startedAt": now.isoformat(),
            "updatedAt": now.isoformat(),
        }

        fresh = self._request("token-hostess", "GET", "/api/driver-locations")
        self.assertEqual(fresh.status_code, 200, fresh.get_json())
        self.assertEqual(fresh.get_json()["staleAfterSeconds"], tour_app.DRIVER_LOCATION_STALE_SECONDS)
        self.assertEqual(fresh.get_json()["expiresAfterSeconds"], tour_app.DRIVER_LOCATION_EXPIRES_SECONDS)
        self.assertFalse(fresh.get_json()["locations"][0]["stale"])

        stale_at = now - timedelta(seconds=tour_app.DRIVER_LOCATION_STALE_SECONDS + 10)
        self.database["driverLocations"]["drv_one"]["updatedAt"] = stale_at.isoformat()
        stale = self._request("token-hostess", "GET", "/api/driver-locations")
        self.assertEqual(stale.status_code, 200, stale.get_json())
        self.assertTrue(stale.get_json()["locations"][0]["stale"])

        expired_at = now - timedelta(seconds=tour_app.DRIVER_LOCATION_EXPIRES_SECONDS + 10)
        self.database["driverLocations"]["drv_one"]["updatedAt"] = expired_at.isoformat()
        expired = self._request("token-hostess", "GET", "/api/driver-locations")
        self.assertEqual(expired.status_code, 200, expired.get_json())
        self.assertEqual(expired.get_json()["locations"], [])

    def test_operation_reset_clears_location_and_invalidates_old_session(self) -> None:
        session = self._start()
        updated = self._update(session["sharingId"])
        self.assertEqual(updated.status_code, 200, updated.get_json())
        self.assertIn("drv_one", self.database["driverLocations"])
        self.database["driverLocationTestUntil"] = "2026-09-05T23:59:00+00:00"
        self.database["driverLocationTestDriverId"] = "drv_one"

        reset = self._request("token-admin", "POST", "/api/operation/reset")
        self.assertEqual(reset.status_code, 200, reset.get_json())
        self.assertEqual(self.database["driverLocations"], {})
        self.assertNotIn("driverLocationTestUntil", self.database)
        self.assertNotIn("driverLocationTestDriverId", self.database)
        self.assertEqual(self.database["attendance"], [])
        self.assertTrue(all(driver["status"] == tour_app.DRIVER_LEAVE for driver in self.database["drivers"]))

        delayed_callback = self._update(session["sharingId"])
        self.assertEqual(delayed_callback.status_code, 409, delayed_callback.get_json())
        locations = self._request("token-hostess", "GET", "/api/driver-locations")
        self.assertEqual(locations.status_code, 200, locations.get_json())
        self.assertEqual(locations.get_json()["locations"], [])

    def test_public_consultant_tracking_requires_its_own_capability_and_assignment(self) -> None:
        session = self._start()
        updated = self._update(session["sharingId"])
        self.assertEqual(updated.status_code, 200, updated.get_json())

        public_board = self._request(None, "GET", "/api/public/driver-status")
        self.assertEqual(public_board.status_code, 200, public_board.get_json())
        self._assert_no_precise_location_keys(self, public_board.get_json())

        options = self._request(None, "GET", "/api/public/consultant-support/options")
        self.assertEqual(options.status_code, 200, options.get_json())
        self._assert_no_precise_location_keys(self, options.get_json())

        own_request, own_token = self._create_public_support_request("con_one")
        other_request, other_token = self._create_public_support_request("con_two")
        self.assertNotEqual(own_token, other_token)

        hostess_bootstrap = self._request("token-hostess", "GET", "/api/bootstrap")
        self.assertEqual(hostess_bootstrap.status_code, 200, hostess_bootstrap.get_json())
        hostess_request_ids = {
            item["id"] for item in hostess_bootstrap.get_json()["data"]["hostessRequests"]
        }
        self.assertNotIn(own_request["id"], hostess_request_ids)
        self.assertNotIn(other_request["id"], hostess_request_ids)
        for token in ("token-hostess", "token-driver", "token-admin"):
            bootstrap = self._request(token, "GET", "/api/bootstrap")
            self.assertEqual(bootstrap.status_code, 200, bootstrap.get_json())
            encoded_bootstrap = json.dumps(bootstrap.get_json())
            self.assertNotIn(own_token, encoded_bootstrap)
            self.assertNotIn(other_token, encoded_bootstrap)
            self.assertNotIn("publicAccessTokenHash", encoded_bootstrap)
        for path in ("/api/public/driver-status", "/api/public/consultant-support/options"):
            public_payload = self._request(None, "GET", path)
            self.assertEqual(public_payload.status_code, 200, public_payload.get_json())
            encoded_public_payload = json.dumps(public_payload.get_json())
            self.assertNotIn(own_token, encoded_public_payload)
            self.assertNotIn(other_token, encoded_public_payload)
            self.assertNotIn("publicAccessTokenHash", encoded_public_payload)

        # Creating a request is not enough: no driver has accepted it yet.
        waiting = self._public_support_status(own_request["id"], own_token)
        self.assertEqual(waiting.status_code, 200, waiting.get_json())
        self.assertEqual(waiting.headers.get("Cache-Control"), "private, no-store")
        self.assertEqual(waiting.get_json()["staleAfterSeconds"], tour_app.DRIVER_LOCATION_STALE_SECONDS)
        self.assertEqual(waiting.get_json()["expiresAfterSeconds"], tour_app.DRIVER_LOCATION_EXPIRES_SECONDS)
        self.assertIsNone(waiting.get_json()["location"])

        missing_token = self._public_support_status(own_request["id"], None)
        wrong_token = self._public_support_status(own_request["id"], other_token)
        unknown_token = self._public_support_status(own_request["id"], "not-a-real-capability")
        query_string_token = self._request(
            None,
            "GET",
            f"/api/public/consultant-support-requests/{own_request['id']}?accessToken={own_token}",
        )
        for response in (missing_token, wrong_token, unknown_token, query_string_token):
            self.assertEqual(response.status_code, 404, response.get_json())
        self.assertEqual(wrong_token.get_json(), unknown_token.get_json())

        accepted = self._request(
            "token-driver",
            "POST",
            "/api/drivers/hostess-availability",
            json={"available": True, "requestId": own_request["id"]},
        )
        self.assertEqual(accepted.status_code, 200, accepted.get_json())

        tracked = self._public_support_status(own_request["id"], own_token)
        self.assertEqual(tracked.status_code, 200, tracked.get_json())
        tracked_payload = tracked.get_json()
        self.assertEqual(tracked_payload["request"]["id"], own_request["id"])
        self.assertEqual(tracked_payload["request"]["consultantName"], "Consultora Um")
        self.assertEqual(tracked_payload["location"]["driverName"], "Motorista Localizado")
        self.assertEqual(tracked_payload["location"]["latitude"], -12.571235)
        self.assertEqual(tracked_payload["location"]["longitude"], -38.005679)
        self.assertNotIn("driverId", tracked_payload["location"])
        self.assertNotIn("attendanceId", tracked_payload["location"])
        self.assertNotIn("sharingId", tracked_payload["location"])
        self.assertNotIn("accessToken", tracked_payload)
        self.assertNotIn("publicAccessTokenHash", json.dumps(tracked_payload))
        for internal_key in ("consultantId", "requestedById", "assignedDriverId"):
            self.assertNotIn(internal_key, tracked_payload["request"])

        second_driver_account = next(
            item for item in self.database["users"]
            if item["id"] == "user_no_share"
        )
        second_driver_account["permissions"] = [
            tour_app.PERMISSION_CHECK_IN,
            tour_app.PERMISSION_SHARE_OWN_LOCATION,
            tour_app.PERMISSION_MANAGE_HOSTESS_SUPPORT,
        ]
        second_session = self._request(
            "token-no-share",
            "POST",
            "/api/drivers/me/location-sharing",
            json={"attendanceId": "checkin_no_share"},
        )
        self.assertEqual(second_session.status_code, 201, second_session.get_json())
        second_update = self._request(
            "token-no-share",
            "PUT",
            "/api/drivers/me/location",
            json={
                "attendanceId": "checkin_no_share",
                "sharingId": second_session.get_json()["sharingId"],
                "latitude": -12.58,
                "longitude": -38.02,
                "accuracy": 9,
            },
        )
        self.assertEqual(second_update.status_code, 200, second_update.get_json())
        second_accepted = self._request(
            "token-no-share",
            "POST",
            "/api/drivers/hostess-availability",
            json={"available": True, "requestId": other_request["id"]},
        )
        self.assertEqual(second_accepted.status_code, 200, second_accepted.get_json())

        # Each consultant receives only the driver assigned to that exact
        # request, even while two live points and two accepted calls coexist.
        other_status = self._public_support_status(other_request["id"], other_token)
        self.assertEqual(other_status.status_code, 200, other_status.get_json())
        other_location = other_status.get_json()["location"]
        self.assertEqual(other_location["driverName"], "Motorista Sem Permissão")
        self.assertEqual(other_location["latitude"], -12.58)
        self.assertEqual(other_location["longitude"], -38.02)
        self.assertNotEqual(other_location["latitude"], tracked_payload["location"]["latitude"])
        crossed = self._public_support_status(own_request["id"], other_token)
        self.assertEqual(crossed.status_code, 404, crossed.get_json())

        stored_request = next(
            item for item in self.database["hostessRequests"]
            if item["id"] == own_request["id"]
        )
        self.assertNotIn(own_token, json.dumps(stored_request))
        stored_request.pop("publicAccessTokenHash", None)
        for missing_hash_response in (
            self._public_support_status(own_request["id"], None),
            self._public_support_status(own_request["id"], own_token),
        ):
            self.assertEqual(
                missing_hash_response.status_code,
                404,
                missing_hash_response.get_json(),
            )

    def test_public_consultant_tracking_hides_absent_closed_and_after_hours_location(self) -> None:
        support_request, access_token = self._create_public_support_request("con_one")
        accepted = self._request(
            "token-driver",
            "POST",
            "/api/drivers/hostess-availability",
            json={"available": True, "requestId": support_request["id"]},
        )
        self.assertEqual(accepted.status_code, 200, accepted.get_json())

        without_point = self._public_support_status(support_request["id"], access_token)
        self.assertEqual(without_point.status_code, 200, without_point.get_json())
        self.assertIsNone(without_point.get_json()["location"])

        session = self._start()
        updated = self._update(session["sharingId"])
        self.assertEqual(updated.status_code, 200, updated.get_json())
        with_point = self._public_support_status(support_request["id"], access_token)
        self.assertEqual(with_point.status_code, 200, with_point.get_json())
        self.assertIsNotNone(with_point.get_json()["location"])

        with self._at_salvador_time(15, 0, 0):
            after_hours = self._public_support_status(support_request["id"], access_token)
            self.assertEqual(after_hours.status_code, 200, after_hours.get_json())
            self.assertIsNone(after_hours.get_json()["location"])
            self.assertFalse(after_hours.get_json()["sharingWindowOpen"])
            self.assertEqual(after_hours.get_json()["sharingEndsAt"], "15:00")
            self.assertEqual(self.database["driverLocations"], {})

        stored_request = next(
            item for item in self.database["hostessRequests"]
            if item["id"] == support_request["id"]
        )
        stored_request["status"] = tour_app.HOSTESS_REQUEST_CLOSED
        closed = self._public_support_status(support_request["id"], access_token)
        self.assertIn(closed.status_code, {200, 404}, closed.get_json())
        if closed.status_code == 200:
            self.assertIsNone(closed.get_json()["location"])

        invalid_consultant = self._request(
            None,
            "POST",
            "/api/public/consultant-support-requests",
            json={"consultantId": "con_missing"},
        )
        inactive_consultant = self._request(
            None,
            "POST",
            "/api/public/consultant-support-requests",
            json={"consultantId": "con_inactive"},
        )
        self.assertIn(invalid_consultant.status_code, {400, 404})
        self.assertIn(inactive_consultant.status_code, {400, 404, 409})

    def test_precise_coordinates_never_leak_to_bootstrap_or_public_board(self) -> None:
        session = self._start()
        updated = self._update(session["sharingId"])
        self.assertEqual(updated.status_code, 200, updated.get_json())

        for token in ("token-admin", "token-driver", "token-hostess", "token-viewer"):
            with self.subTest(token=token):
                bootstrap = self._request(token, "GET", "/api/bootstrap")
                self.assertEqual(bootstrap.status_code, 200, bootstrap.get_json())
                self.assertNotIn("driverLocations", bootstrap.get_json()["data"])
                self._assert_no_precise_location_keys(self, bootstrap.get_json())

        public = self._request(None, "GET", "/api/public/driver-status")
        self.assertEqual(public.status_code, 200, public.get_json())
        self._assert_no_precise_location_keys(self, public.get_json())
        public_driver = next(item for item in public.get_json()["drivers"] if item["name"] == "Motorista Localizado")
        self.assertEqual(
            set(public_driver),
            {"name", "status", "active", "lastActivity"},
        )

    def test_hostess_and_assigned_driver_privately_track_their_approach(self) -> None:
        created = self._request(
            "token-hostess",
            "POST",
            "/api/hostess-requests",
            json={"latitude": -12.5701, "longitude": -38.0012, "accuracy": 11},
        )
        self.assertEqual(created.status_code, 201, created.get_json())
        car_request = created.get_json()["request"]
        self._assert_no_precise_location_keys(self, created.get_json())

        waiting = self._request(
            "token-hostess",
            "GET",
            f"/api/hostess-requests/{car_request['id']}/approach",
        )
        self.assertEqual(waiting.status_code, 200, waiting.get_json())
        self.assertEqual(waiting.headers.get("Cache-Control"), "private, no-store")
        self.assertEqual(waiting.get_json()["hostessLocation"]["latitude"], -12.5701)
        self.assertIsNone(waiting.get_json()["driverLocation"])

        # Precise Hostess coordinates never enter generic/bootstrap data.
        for token in ("token-hostess", "token-driver", "token-admin", "token-viewer"):
            bootstrap = self._request(token, "GET", "/api/bootstrap")
            self.assertEqual(bootstrap.status_code, 200, bootstrap.get_json())
            self._assert_no_precise_location_keys(self, bootstrap.get_json())

        driver_session = self._start()
        driver_update = self._update(driver_session["sharingId"])
        self.assertEqual(driver_update.status_code, 200, driver_update.get_json())
        accepted = self._request(
            "token-driver",
            "POST",
            "/api/drivers/hostess-availability",
            json={"available": True, "requestId": car_request["id"]},
        )
        self.assertEqual(accepted.status_code, 200, accepted.get_json())

        assigned_driver = self._request(
            "token-driver",
            "GET",
            f"/api/hostess-requests/{car_request['id']}/approach",
        )
        self.assertEqual(assigned_driver.status_code, 200, assigned_driver.get_json())
        pair = assigned_driver.get_json()
        self.assertEqual(pair["request"]["assignedDriverName"], "Motorista Localizado")
        self.assertEqual(pair["hostessLocation"]["hostessName"], "Hostess Mapa")
        self.assertEqual(pair["driverLocation"]["driverName"], "Motorista Localizado")
        self.assertNotIn("driverId", pair["driverLocation"])
        self.assertNotIn("requestedById", pair["request"])
        self.assertNotIn("assignedDriverId", pair["request"])

        # No coordinator or unassigned driver can open the paired map.
        for token in ("token-admin", "token-no-share", "token-viewer"):
            denied = self._request(
                token,
                "GET",
                f"/api/hostess-requests/{car_request['id']}/approach",
            )
            self.assertEqual(denied.status_code, 404, denied.get_json())

        refreshed = self._request(
            "token-hostess",
            "PUT",
            f"/api/hostess-requests/{car_request['id']}/location",
            json={"latitude": -12.5698, "longitude": -38.0009, "accuracy": 7},
        )
        self.assertEqual(refreshed.status_code, 200, refreshed.get_json())
        self._assert_no_precise_location_keys(self, refreshed.get_json())

        closed = self._request(
            "token-hostess",
            "POST",
            f"/api/hostess-requests/{car_request['id']}/close",
        )
        self.assertEqual(closed.status_code, 200, closed.get_json())
        self.assertNotIn(car_request["id"], self.database["hostessRequestLocations"])
        unavailable = self._request(
            "token-driver",
            "GET",
            f"/api/hostess-requests/{car_request['id']}/approach",
        )
        self.assertEqual(unavailable.status_code, 404, unavailable.get_json())


class DriverLocationTimeZonePolicyTest(unittest.TestCase):
    """The cutoff follows Salvador time, independently of the server timezone."""

    def test_utc_instants_are_normalized_to_salvador_before_cutoff(self) -> None:
        before_cutoff_utc = datetime(2026, 9, 5, 17, 59, 59, tzinfo=timezone.utc)
        at_cutoff_utc = datetime(2026, 9, 5, 18, 0, 0, tzinfo=timezone.utc)

        self.assertEqual(tour_app.DRIVER_LOCATION_TZ.key, "America/Bahia")
        self.assertEqual(
            tour_app.driver_location_now(at_cutoff_utc).isoformat(),
            "2026-09-05T15:00:00-03:00",
        )
        self.assertTrue(tour_app.driver_location_window_is_open(before_cutoff_utc))
        self.assertFalse(tour_app.driver_location_window_is_open(at_cutoff_utc))


if __name__ == "__main__":
    unittest.main()
