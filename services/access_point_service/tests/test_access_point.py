import os
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1] / "app"
TEST_DB_PATH = Path(__file__).resolve().with_name("test_access_point.sqlite")

os.environ.setdefault("ACCESS_POINT_DATABASE_URI", f"sqlite:///{TEST_DB_PATH.as_posix()}")
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
            # Fecha as conexoes do pool; no Windows o arquivo aberto nao pode ser removido.
            db.engine.dispose()

        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()

    def test_create_access_point_rejects_missing_required_fields(self):
        response = self.client.post("/access_points", json={"id": "ap-1"})

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertEqual(payload["error"], "Dados inválidos. Corrija os campos indicados e envie de novo.")
        self.assertTrue(any("name" in detail for detail in payload["details"]))

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

    def test_generate_accepts_min_degree_and_the_former_clique_factor_name(self):
        by_new_name = self.client.post("/access_points/generate", json={"node_count": 20, "min_degree": 3, "seed": 9})
        by_old_name = self.client.post("/access_points/generate", json={"node_count": 20, "clique_factor": 3, "seed": 9})

        self.assertEqual(by_new_name.status_code, 200)
        new_payload = by_new_name.get_json()["payload"]
        old_payload = by_old_name.get_json()["payload"]
        self.assertEqual(new_payload["aps"], old_payload["aps"])
        self.assertEqual(new_payload["metadata"]["min_degree"], 3)
        self.assertEqual(new_payload["metadata"]["clique_factor"], 3)

        degrees = {ap["id"]: 0 for ap in new_payload["aps"]}
        for link in new_payload["links"]:
            degrees[link["source"]] += 1
            degrees[link["target"]] += 1
        self.assertGreaterEqual(min(degrees.values()), 3)

    def test_generate_rejects_min_degree_not_smaller_than_node_count(self):
        response = self.client.post("/access_points/generate", json={"node_count": 5, "min_degree": 5})

        self.assertEqual(response.status_code, 400)
        self.assertIn("min_degree", response.get_json()["error"])

    def test_generate_access_points_uses_frequency_profiles_with_fixed_settings(self):
        response = self.client.post("/access_points/generate", json={
            "node_count": 12,
            "clique_factor": 2,
        })

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])

        aps = payload["payload"]["aps"]
        self.assertEqual(len(aps), 12)

        for ap in aps:
            self.assertIsNotNone(ap["latitude"])
            self.assertIsNotNone(ap["longitude"])

            if ap["frequency"] == "2.4 GHz":
                self.assertEqual(ap["channel"], "1")
                self.assertEqual(ap["bandwidth"], "20 MHz")
            elif ap["frequency"] == "5 GHz":
                self.assertEqual(ap["channel"], "36")
                self.assertEqual(ap["bandwidth"], "80 MHz")
            else:
                self.fail(f"Frequencia inesperada gerada: {ap['frequency']}")

    def test_delete_access_point_removes_existing_record(self):
        with app.app_context():
            db.session.add(AccessPoint(id="ap-1", name="AP 1"))
            db.session.commit()

        response = self.client.delete("/access_points/ap-1")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])

        with app.app_context():
            self.assertIsNone(AccessPoint.query.get("ap-1"))

    def test_get_access_point_returns_existing_record(self):
        with app.app_context():
            db.session.add(AccessPoint(
                id="ap-1",
                name="AP 1",
                channel="6",
                frequency="2.4 GHz",
                bandwidth="20 MHz",
                latitude=-23.5,
                longitude=-46.6,
            ))
            db.session.commit()

        response = self.client.get("/access_points/ap-1")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["id"], "ap-1")
        self.assertEqual(payload["name"], "AP 1")
        self.assertEqual(payload["channel"], "6")
        self.assertEqual(payload["latitude"], -23.5)
        self.assertIn("last_update", payload)

    def test_get_access_point_returns_404_when_missing(self):
        response = self.client.get("/access_points/ap-inexistente")

        self.assertEqual(response.status_code, 404)
        payload = response.get_json()
        self.assertIn("não encontrado", payload["error"])

    def test_delete_access_point_returns_404_when_missing(self):
        response = self.client.delete("/access_points/ap-inexistente")

        self.assertEqual(response.status_code, 404)
        payload = response.get_json()
        self.assertIn("não encontrado", payload["error"])


if __name__ == "__main__":
    unittest.main()
