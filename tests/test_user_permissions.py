"""Regression coverage for per-account permissions.

Run with:
    python -m unittest tests.test_user_permissions
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


class UserPermissionsApiTest(unittest.TestCase):
    """A dashboard-only account must never inherit its role's write access."""

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
            "token-viewer": {"userId": "user_viewer", "expiresAt": expiry},
            "token-manager": {"userId": "user_manager", "expiresAt": expiry},
        })
        self.client = tour_app.app.test_client()

    @staticmethod
    def _account(
        user_id: str,
        name: str,
        username: str,
        role: str,
        permissions: list[str],
    ) -> dict:
        return {
            "id": user_id,
            "name": name,
            "username": username,
            "role": role,
            "permissions": permissions,
            "active": True,
            "passwordHash": "unused-in-session-tests",
            "createdAt": "2026-09-03T12:00:00+00:00",
        }

    @classmethod
    def _database(cls) -> dict:
        db = tour_app.initial_database()
        db.update({
            "users": [
                cls._account(
                    "user_admin",
                    "Administrador",
                    "admin",
                    tour_app.ROLE_ADMIN,
                    [tour_app.PERMISSION_MANAGE_USERS],
                ),
                # Hostess is deliberately used here because it historically
                # had write endpoints.  Its explicit grant must override any
                # role default and retain read-only dashboard access only.
                cls._account(
                    "user_viewer",
                    "Painel Somente Leitura",
                    "painel.leitura",
                    tour_app.ROLE_HOSTESS,
                    [tour_app.PERMISSION_VIEW_DASHBOARD],
                ),
                cls._account(
                    "user_manager",
                    "Gestor Delegado",
                    "gestor.delegado",
                    tour_app.ROLE_HOSTESS,
                    [tour_app.PERMISSION_VIEW_DASHBOARD, tour_app.PERMISSION_MANAGE_USERS],
                ),
            ],
            "drivers": [{
                "id": "drv_1",
                "name": "Motorista Teste",
                "active": True,
                "status": tour_app.DRIVER_AVAILABLE,
                "toursStarted": 0,
                "homePickups": 0,
                "hostessAvailable": False,
                "hostessRequestId": None,
                "lastActivity": "2026-09-03T12:00:00+00:00",
            }],
            "tours": [{
                "id": "tour_1",
                "groupName": "Tour 1",
                "people": 2,
                "selfGuide": False,
                "consultantId": None,
                "consultantName": None,
                "wave": "WAVE_1",
                "scheduledTime": "09:00",
                "status": tour_app.STATE_AVAILABLE,
                "phase": "Prestige Praia do Forte",
                "createdAt": "2026-09-03T12:00:00+00:00",
                "updatedAt": "2026-09-03T12:00:00+00:00",
                "allocations": [],
            }],
            "activities": [],
        })
        return db

    def _request(self, token: str, method: str, path: str, **kwargs):
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = f"Bearer {token}"
        return self.client.open(path, method=method, headers=headers, **kwargs)

    def test_dashboard_only_permission_allows_bootstrap_but_blocks_writes(self) -> None:
        bootstrap = self._request("token-viewer", "GET", "/api/bootstrap")
        self.assertEqual(bootstrap.status_code, 200, bootstrap.get_json())
        payload = bootstrap.get_json()
        self.assertEqual(payload["user"]["permissions"], [tour_app.PERMISSION_VIEW_DASHBOARD])
        self.assertIn("tours", payload["data"])
        self.assertIn("drivers", payload["data"])
        catalog_keys = {item["key"] for item in payload["permissionsCatalog"]}
        self.assertIn(tour_app.PERMISSION_VIEW_DASHBOARD, catalog_keys)

        # These previously depended on the Hostess role.  A viewer must not
        # gain either daily-total registration or a route transition.
        create_tours = self._request(
            "token-viewer",
            "POST",
            "/api/tours",
            json={"quantity": 1, "selfGeanQuantity": 0, "wave": "WAVE_1"},
        )
        self.assertEqual(create_tours.status_code, 403, create_tours.get_json())
        route_change = self._request(
            "token-viewer",
            "POST",
            "/api/tours/tour_1/action",
            json={"action": "withdraw"},
        )
        self.assertEqual(route_change.status_code, 403, route_change.get_json())
        check_in = self._request("token-viewer", "POST", "/api/attendance/check-in")
        self.assertEqual(check_in.status_code, 403, check_in.get_json())
        self.assertEqual(self.database["tours"][0]["status"], tour_app.STATE_AVAILABLE)

    def test_admin_can_create_and_update_explicit_permission_grants(self) -> None:
        created = self._request(
            "token-admin",
            "POST",
            "/api/users",
            json={
                "name": "Consulta Operacional",
                "username": "consulta.operacional",
                "password": "senha-segura",
                "role": tour_app.ROLE_HOSTESS,
                "permissions": [tour_app.PERMISSION_VIEW_DASHBOARD],
            },
        )
        self.assertEqual(created.status_code, 201, created.get_json())
        account = created.get_json()["user"]
        self.assertEqual(account["permissions"], [tour_app.PERMISSION_VIEW_DASHBOARD])

        updated_permissions = [
            tour_app.PERMISSION_VIEW_DASHBOARD,
            tour_app.PERMISSION_VIEW_DRIVERS,
        ]
        updated = self._request(
            "token-admin",
            "PUT",
            f"/api/users/{account['id']}",
            json={"permissions": updated_permissions},
        )
        self.assertEqual(updated.status_code, 200, updated.get_json())
        self.assertEqual(updated.get_json()["user"]["permissions"], updated_permissions)
        saved = next(item for item in self.database["users"] if item["id"] == account["id"])
        self.assertEqual(saved["permissions"], updated_permissions)

    def test_delegated_user_manager_cannot_escalate_permissions(self) -> None:
        promoted = self._request(
            "token-manager",
            "POST",
            "/api/users",
            json={
                "name": "Administrador Indevido",
                "username": "administrador.indevido",
                "password": "senha-segura",
                "role": tour_app.ROLE_ADMIN,
                "permissions": [tour_app.PERMISSION_MANAGE_USERS],
            },
        )
        self.assertEqual(promoted.status_code, 403, promoted.get_json())

        extra_access = self._request(
            "token-manager",
            "POST",
            "/api/users",
            json={
                "name": "Acesso Indevido",
                "username": "acesso.indevido",
                "password": "senha-segura",
                "role": tour_app.ROLE_HOSTESS,
                "permissions": [tour_app.PERMISSION_MANAGE_SETTINGS],
            },
        )
        self.assertEqual(extra_access.status_code, 403, extra_access.get_json())


if __name__ == "__main__":
    unittest.main()
