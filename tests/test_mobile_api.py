"""Regression coverage for persistent Android API authentication and aliases."""

from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from werkzeug.security import generate_password_hash


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app as tour_app  # noqa: E402


class MobileApiTest(unittest.TestCase):
    USERNAME = "android.user"
    PASSWORD = "senha-segura-123"

    def setUp(self) -> None:
        self.database = tour_app.initial_database()
        self.database.update({
            "users": [{
                "id": "user_android",
                "username": self.USERNAME,
                "name": "Usuário Android",
                "role": tour_app.ROLE_HOSTESS,
                "permissions": tour_app.default_permissions_for_role(tour_app.ROLE_HOSTESS),
                "active": True,
                "passwordHash": generate_password_hash(self.PASSWORD),
                "checkInLocation": "Prestige Praia do Forte",
                "createdAt": "2026-09-08T10:00:00+00:00",
            }],
            "mobileApiSessions": {},
            "attendance": [],
            "activities": [],
        })
        self.patchers = [
            patch.object(tour_app, "POSTGRES_URL", ""),
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
        self.client = tour_app.app.test_client()

    def login(self, device_id: str = "install-android-01"):
        return self.client.post(
            "/api/mobile/v1/auth/login",
            json={
                "username": self.USERNAME,
                "password": self.PASSWORD,
                "deviceId": device_id,
                "deviceName": "Pixel de teste",
            },
        )

    @staticmethod
    def authorization(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def test_persistent_mobile_token_authenticates_every_versioned_route(self) -> None:
        response = self.login()
        self.assertEqual(response.status_code, 200, response.get_json())
        payload = response.get_json()
        token = payload["token"]
        self.assertTrue(token.startswith(tour_app.MOBILE_API_TOKEN_PREFIX))
        self.assertEqual(payload["tokenType"], "Bearer")
        self.assertEqual(payload["apiVersion"], "v1")
        self.assertEqual(payload["basePath"], "/api/mobile/v1")
        self.assertEqual(payload["deviceId"], "install-android-01")
        self.assertGreater(
            datetime.fromisoformat(payload["expiresAt"]),
            datetime.now(timezone.utc) + timedelta(days=29),
        )

        encoded_database = json.dumps(self.database)
        self.assertNotIn(token, encoded_database)
        token_hash = tour_app.mobile_api_token_digest(token)
        self.assertIn(token_hash, self.database["mobileApiSessions"])

        # The token does not rely on the browser's process-memory sessions.
        tour_app.SESSIONS.clear()
        me = self.client.get("/api/mobile/v1/auth/me", headers=self.authorization(token))
        bootstrap = self.client.get("/api/mobile/v1/bootstrap", headers=self.authorization(token))
        check_in = self.client.post("/api/mobile/v1/attendance/check-in", headers=self.authorization(token))
        self.assertEqual(me.status_code, 200, me.get_json())
        self.assertEqual(me.get_json()["user"]["id"], "user_android")
        self.assertEqual(bootstrap.status_code, 200, bootstrap.get_json())
        self.assertEqual(bootstrap.get_json()["user"]["id"], "user_android")
        self.assertEqual(check_in.status_code, 201, check_in.get_json())
        self.assertEqual(check_in.headers.get("X-API-Version"), "v1")
        self.assertEqual(check_in.headers.get("Cache-Control"), "private, no-store")

    def test_same_device_rotates_token_and_logout_revokes_it(self) -> None:
        first = self.login().get_json()["token"]
        second_response = self.login()
        self.assertEqual(second_response.status_code, 200, second_response.get_json())
        second = second_response.get_json()["token"]
        self.assertNotEqual(first, second)
        self.assertEqual(len(self.database["mobileApiSessions"]), 1)

        old_token = self.client.get("/api/mobile/v1/bootstrap", headers=self.authorization(first))
        self.assertEqual(old_token.status_code, 401, old_token.get_json())
        active_token = self.client.get("/api/mobile/v1/bootstrap", headers=self.authorization(second))
        self.assertEqual(active_token.status_code, 200, active_token.get_json())

        logout = self.client.post("/api/mobile/v1/auth/logout", headers=self.authorization(second))
        self.assertEqual(logout.status_code, 200, logout.get_json())
        self.assertEqual(self.database["mobileApiSessions"], {})
        revoked = self.client.get("/api/mobile/v1/auth/me", headers=self.authorization(second))
        self.assertEqual(revoked.status_code, 401, revoked.get_json())

    def test_health_and_contract_are_public_but_bad_credentials_are_rejected(self) -> None:
        health = self.client.get("/api/mobile/v1/health")
        contract = self.client.get("/api/mobile/v1/openapi.yaml")
        public_status = self.client.get("/api/mobile/v1/public/driver-status")
        self.assertEqual(health.status_code, 200, health.get_json())
        self.assertEqual(health.get_json()["apiVersion"], "v1")
        self.assertEqual(contract.status_code, 200)
        self.assertIn(b"openapi: 3.1.0", contract.data)
        contract.close()
        self.assertEqual(public_status.status_code, 200, public_status.get_json())

        bad_login = self.client.post(
            "/api/mobile/v1/auth/login",
            json={"username": self.USERNAME, "password": "incorreta"},
        )
        self.assertEqual(bad_login.status_code, 401, bad_login.get_json())
        self.assertEqual(self.database["mobileApiSessions"], {})

    def test_expired_mobile_token_is_not_accepted(self) -> None:
        token = f"{tour_app.MOBILE_API_TOKEN_PREFIX}expired-token"
        token_hash = tour_app.mobile_api_token_digest(token)
        self.database["mobileApiSessions"][token_hash] = {
            "tokenHash": token_hash,
            "userId": "user_android",
            "deviceId": "expired-device",
            "deviceName": "Aparelho antigo",
            "createdAt": (datetime.now(timezone.utc) - timedelta(days=31)).isoformat(),
            "expiresAt": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
        }
        response = self.client.get("/api/mobile/v1/bootstrap", headers=self.authorization(token))
        self.assertEqual(response.status_code, 401, response.get_json())


if __name__ == "__main__":
    unittest.main()
