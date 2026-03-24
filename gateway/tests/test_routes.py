import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


GATEWAY_DIR = Path(__file__).resolve().parents[1]

os.environ.setdefault("ZABBIX_SERVICE_URL", "http://zabbix:5005")
os.environ.setdefault("MAP_SERVICE_URL", "http://map_service:5001")
os.environ.setdefault("ANALYSIS_SERVICE_URL", "http://analysis_service:5002")
os.environ.setdefault("ACCESS_POINT_SERVICE_URL", "http://access_point_service:5004")
os.environ.setdefault("FRONTEND_SERVICE_URL", "http://frontend_service:3000")
os.environ.setdefault("GATEWAY_SECRET_KEY", "test-secret")
os.environ.setdefault("GATEWAY_HTTP_TIMEOUT", "30")
os.environ.setdefault("GATEWAY_HTTP_RETRIES", "1")
os.environ.setdefault("GATEWAY_HTTP_BACKOFF_FACTOR", "0.1")
os.environ.setdefault("GATEWAY_HTTP_VERIFY_SSL", "false")

if str(GATEWAY_DIR) not in sys.path:
    sys.path.insert(0, str(GATEWAY_DIR))

from app.main import app  # noqa: E402


class GatewayAccessPointImportTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    @patch("app.routes.session.post")
    def test_access_point_import_route_forwards_payload(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "summary": {
                "processed": 1,
                "created": 1,
                "updated": 0,
                "rejected": 0,
                "errors": [],
            },
        }
        mock_post.return_value = mock_response

        payload = [{"id": "ap-1", "name": "AP 1"}]
        response = self.client.post("/api/access_points/import", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["summary"]["created"], 1)
        mock_post.assert_called_once_with(
            "http://access_point_service:5004/access_points/import",
            json=payload,
            timeout=30,
        )


if __name__ == "__main__":
    unittest.main()
