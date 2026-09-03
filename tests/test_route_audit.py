"""Regression coverage for route ownership and audit attribution.

Run with:
    python -m unittest tests.test_route_audit
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


class RouteAuditApiTest(unittest.TestCase):
    """A driver may change only a tour to which they are assigned."""

    def setUp(self) -> None:
        self.database = self._database_at_home()
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
            "token-natan": {"userId": "user_natan", "expiresAt": expiry},
            "token-outsider": {"userId": "user_outsider", "expiresAt": expiry},
        })
        self.client = tour_app.app.test_client()

    @staticmethod
    def _driver(driver_id: str, name: str, status: str) -> dict:
        return {
            "id": driver_id,
            "name": name,
            "active": True,
            "status": status,
            "toursStarted": 0,
            "homePickups": 0,
            "hostessAvailable": False,
            "hostessRequestId": None,
            "lastActivity": "2026-09-03T12:00:00+00:00",
        }

    @classmethod
    def _database_at_home(cls) -> dict:
        db = tour_app.initial_database()
        db.update({
            "consultants": [{"id": "con_libni", "name": "Libni", "active": True}],
            "drivers": [
                cls._driver("drv_natan", "Natan", tour_app.DRIVER_HOME),
                cls._driver("drv_wagner", "Wagner", tour_app.DRIVER_HOME),
                cls._driver("drv_outsider", "Outro Motorista", tour_app.DRIVER_AVAILABLE),
            ],
            "users": [
                {
                    "id": "user_natan",
                    "username": "natan.operador",
                    "name": "Natan Operador",
                    "role": tour_app.ROLE_DRIVER,
                    "active": True,
                    "driverId": "drv_natan",
                },
                {
                    "id": "user_outsider",
                    "username": "outro.motorista",
                    "name": "Outro Motorista",
                    "role": tour_app.ROLE_DRIVER,
                    "active": True,
                    "driverId": "drv_outsider",
                },
            ],
            "carts": [
                {"id": "cart_natan", "name": "Carrinho Natan", "status": "EM_USO"},
                {"id": "cart_wagner", "name": "Carrinho Wagner", "status": "EM_USO"},
                {"id": "cart_outsider", "name": "Carrinho Extra", "status": "DISPONIVEL"},
            ],
            "activities": [],
            "tours": [{
                "id": "tour_8",
                "groupName": "Tour 8",
                "consultantId": "con_libni",
                "consultantName": "Libni",
                "people": 8,
                "wave": "WAVE_1",
                "scheduledTime": "09:00",
                "status": tour_app.STATE_HOME,
                "phase": "Casa",
                "requiredCartCount": 2,
                "createdAt": "2026-09-03T10:00:00+00:00",
                "updatedAt": "2026-09-03T12:00:00+00:00",
                "allocations": [
                    {
                        "driverId": "drv_natan",
                        "cartId": "cart_natan",
                        "guests": 4,
                        "homeDecision": "AGUARDOU_NA_CASA",
                        "arrived": True,
                    },
                    {
                        "driverId": "drv_wagner",
                        "cartId": "cart_wagner",
                        "guests": 4,
                        "homeDecision": "AGUARDOU_NA_CASA",
                        "arrived": True,
                    },
                ],
            }],
        })
        return db

    def _post_action(self, token: str, action: str):
        return self.client.post(
            "/api/tours/tour_8/action",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": action},
        )

    def test_only_assigned_driver_can_change_home_route_and_change_is_audited(self) -> None:
        # A different driver must neither move the couple nor produce an audit entry.
        forbidden = self._post_action("token-outsider", "depart-home")
        self.assertEqual(forbidden.status_code, 403, forbidden.get_json())
        tour = self.database["tours"][0]
        self.assertEqual(tour["status"], tour_app.STATE_HOME)
        self.assertEqual(tour["phase"], "Casa")
        self.assertFalse(self.database["activities"])

        # Natan is assigned to the tour and can advance it. The record must name
        # the account, previous/new route, consultant, and every affected driver.
        allowed = self._post_action("token-natan", "depart-home")
        self.assertEqual(allowed.status_code, 200, allowed.get_json())
        self.assertEqual(tour["status"], tour_app.STATE_IN_TOUR)
        self.assertEqual(tour["phase"], "Casa → Galeria")

        audits = [
            activity for activity in self.database["activities"]
            if activity.get("audit", {}).get("type") == "ROUTE_CHANGE"
        ]
        self.assertEqual(len(audits), 1)
        audit_activity = audits[0]
        self.assertEqual(audit_activity["actorUserId"], "user_natan")
        self.assertEqual(audit_activity["actorName"], "Natan Operador")
        self.assertEqual(audit_activity["actorUsername"], "natan.operador")
        self.assertEqual(audit_activity["actorRole"], tour_app.ROLE_DRIVER)
        self.assertEqual(audit_activity["audit"]["action"], "depart-home")
        self.assertEqual(audit_activity["audit"]["tourName"], "Tour 8")
        self.assertEqual(audit_activity["audit"]["consultantName"], "Libni")
        self.assertEqual(audit_activity["audit"]["from"], "Casa")
        self.assertEqual(audit_activity["audit"]["to"], "Casa → Galeria")
        self.assertEqual(set(audit_activity["audit"]["driverNames"]), {"Natan", "Wagner"})


if __name__ == "__main__":
    unittest.main()
