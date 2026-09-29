from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app as tour_app  # noqa: E402


class TrainingSiteAccessTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = tour_app.app.test_client()
        self.token_patcher = patch.object(tour_app, "TRAINING_ACCESS_TOKEN", "training-capability-test")
        self.token_patcher.start()
        self.addCleanup(self.token_patcher.stop)

    def test_training_requires_its_capability_link(self) -> None:
        for path in ("/treinamento", "/treinamento?convite=errado"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404)

        authorized = self.client.get("/treinamento?convite=training-capability-test")
        self.assertEqual(authorized.status_code, 200)
        self.assertIn(b'id="root"', authorized.data)
        self.assertIn(b"/assets/training-", authorized.data)
        self.assertEqual(authorized.headers.get("Cache-Control"), "private, no-store")
        self.assertEqual(authorized.headers.get("Referrer-Policy"), "no-referrer")
        self.assertIn("noindex", authorized.headers.get("X-Robots-Tag", ""))
        authorized.close()

    def test_training_stays_closed_when_render_secret_is_missing(self) -> None:
        with patch.object(tour_app, "TRAINING_ACCESS_TOKEN", ""):
            response = self.client.get("/treinamento?convite=training-capability-test")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
