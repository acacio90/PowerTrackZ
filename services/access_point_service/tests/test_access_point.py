import os
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1] / "app"
TEST_DB_PATH = Path(__file__).resolve().with_name("test_access_point.sqlite")

os.environ.setdefault("ACCESS_POINT_DATABASE_URI", f"sqlite:///{TEST_DB_PATH.as_posix()}")
os.environ.setdefault("ZABBIX_SERVICE_URL", "http://zabbix:5005")
os.environ.setdefault("ACCESS_POINT_HTTP_TIMEOUT", "30")

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from main import app  # noqa: E402
from models import AccessPoint, db  # noqa: E402


class AccessPointRoutesTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

        with app.app_context():
            db.drop_all()
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()

    def test_create_access_point_rejects_missing_required_fields(self):
        response = self.client.post("/access_points", json={"id": "ap-1"})

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertEqual(payload["error"], "Dados invalidos")
        self.assertIn("campo obrigatório 'name' não informado", payload["details"])

    def test_bulk_import_creates_updates_and_rejects_invalid_items(self):
        with app.app_context():
            db.session.add(AccessPoint(
                id="ap-existing",
                name="Original",
                channel="1",
                frequency="2.4 GHz",
                bandwidth="20 MHz",
                latitude=-23.0,
                longitude=-46.0,
            ))
            db.session.commit()

        response = self.client.post("/access_points/import", json=[
            {
                "id": "ap-existing",
                "name": "Atualizado",
                "channel": "36",
                "frequency": "5 GHz",
                "bandwidth": "80 MHz",
                "latitude": -23.55,
                "longitude": -46.63,
                "last_update": "2000-01-01T00:00:00",
            },
            {
                "id": "ap-new",
                "name": "Novo AP",
                "channel": "6",
                "frequency": "2.4 GHz",
                "bandwidth": "20 MHz",
                "latitude": "-23.56",
                "longitude": "-46.64",
            },
            {
                "id": "ap-invalid",
                "channel": "11",
            },
            {
                "id": "ap-new",
                "name": "Duplicado",
            },
        ])

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["summary"]["processed"], 4)
        self.assertEqual(payload["summary"]["created"], 1)
        self.assertEqual(payload["summary"]["updated"], 1)
        self.assertEqual(payload["summary"]["rejected"], 2)
        self.assertEqual(len(payload["summary"]["errors"]), 2)

        with app.app_context():
            existing = AccessPoint.query.get("ap-existing")
            created = AccessPoint.query.get("ap-new")

            self.assertEqual(existing.name, "Atualizado")
            self.assertEqual(existing.channel, "36")
            self.assertIsNotNone(existing.last_update)
            self.assertEqual(created.name, "Novo AP")
            self.assertEqual(created.latitude, -23.56)
            self.assertEqual(created.longitude, -46.64)
            self.assertEqual(AccessPoint.query.count(), 2)

    def test_bulk_import_requires_json_list(self):
        response = self.client.post("/access_points/import", json={"id": "ap-1", "name": "AP 1"})

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIn("lista JSON", payload["error"])


if __name__ == "__main__":
    unittest.main()
