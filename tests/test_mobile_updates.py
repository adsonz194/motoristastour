import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app
import mobile_updates


class MobileUpdateTest(unittest.TestCase):
    def setUp(self):
        self.policy = dict(versionCode=13, versionName="2.5.0", sha256="a" * 64,
            apkUrl="https://github.com/adsonz194/motoristastourapk/releases/download/v2.5.0/app-release.apk")
        self.client = app.app.test_client()

    def policy_patch(self, policy=None):
        return patch.object(Path, "read_text", return_value=json.dumps(self.policy if policy is None else policy))

    def test_numeric_version_comparison(self):
        with self.policy_patch():
            value = mobile_updates.update_policy()
        for installed in (None, "", "12", "garbage", "-1"):
            self.assertTrue(mobile_updates.requires_update(value, installed))
        self.assertFalse(mobile_updates.requires_update(value, "13"))
        self.assertFalse(mobile_updates.requires_update(value, "100"))

    def test_old_login_and_logged_in_routes_block_before_database_access(self):
        with self.policy_patch(), patch.object(app, "operational_database", side_effect=AssertionError("must not access data")):
            for method, path in (("post", "/api/mobile/v1/auth/login"), ("get", "/api/mobile/v1/bootstrap"), ("post", "/api/mobile/v1/tours")):
                for headers in ({}, {"X-App-Version-Code": "12"}):
                    response = getattr(self.client, method)(path, headers=headers)
                    self.assertEqual(response.status_code, 426)
                    self.assertEqual(response.json["code"], "APP_UPDATE_REQUIRED")
                    self.assertEqual(response.json["update"]["minVersionCode"], 13)
            alias = self.client.get("/api/bootstrap", headers={"Authorization": "Bearer mta_old"})
            self.assertEqual(alias.status_code, 426)

    def test_current_version_passes_to_normal_auth(self):
        with self.policy_patch(), patch.object(app, "operational_database", return_value={}):
            response = self.client.get("/api/mobile/v1/bootstrap", headers={"X-App-Version-Code": "13"})
            self.assertEqual(response.status_code, 401)
            web = self.client.get("/api/bootstrap")
            self.assertEqual(web.status_code, 401)

    def test_update_endpoint_is_public_uncached_and_not_blocked(self):
        with self.policy_patch():
            response = self.client.get("/api/mobile/v1/app-update")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["versionCode"], 13)
            self.assertIn("no-store", response.headers["Cache-Control"])

    def test_disabled_policy_keeps_legacy_versions_working(self):
        with self.policy_patch({"versionCode": 0}), patch.object(app, "operational_database", return_value={}):
            self.assertEqual(self.client.get("/api/mobile/v1/bootstrap").status_code, 401)

    def test_bad_manifest_fails_closed_without_breaking_web(self):
        for field, value in (("versionCode", True), ("versionCode", -1), ("sha256", "wrong"),
                             ("apkUrl", "http://github.com/invalid.apk"), ("apkUrl", self.policy["apkUrl"] + "?token=secret"),
                             ("apkUrl", self.policy["apkUrl"].replace("adsonz194", "other"))):
            with self.policy_patch({**self.policy, field: value}):
                self.assertEqual(self.client.get("/api/mobile/v1/app-update").status_code, 503)
                self.assertEqual(self.client.get("/api/mobile/v1/bootstrap").status_code, 503)


if __name__ == "__main__":
    unittest.main()
