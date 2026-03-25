import json
import os
import socket
import subprocess
import time
import unittest
import urllib.error
import urllib.request


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SERVICE_DIR = os.path.join(REPO_ROOT, "services", "analysis_service")
TEST_IMAGE = "powertrackz-analysis-service-test"


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class AnalysisServiceBacktrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            subprocess.run(["docker", "--version"], check=True, capture_output=True, text=True)
        except Exception as exc:
            raise unittest.SkipTest(f"Docker indisponivel: {exc}")

        subprocess.run(
            ["docker", "build", "-t", TEST_IMAGE, SERVICE_DIR],
            check=True,
            cwd=REPO_ROOT,
        )

        cls.host_port = find_free_port()
        cls.container_name = f"powertrackz-analysis-test-{os.getpid()}"
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--rm",
                "--name",
                cls.container_name,
                "-e",
                "HOST=0.0.0.0",
                "-e",
                "PORT=5002",
                "-e",
                "ANALYSIS_LOG_LEVEL=ERROR",
                "-p",
                f"{cls.host_port}:5002",
                TEST_IMAGE,
            ],
            check=True,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        deadline = time.time() + 30
        last_error = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{cls.host_port}/health", timeout=2) as response:
                    if response.status == 200:
                        return
            except Exception as exc:
                last_error = exc
                time.sleep(0.5)

        cls.tearDownClass()
        raise RuntimeError(f"analysis_service nao ficou saudavel: {last_error}")

    @classmethod
    def tearDownClass(cls):
        container_name = getattr(cls, "container_name", None)
        if container_name:
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

    def post_json(self, path, payload):
        request = urllib.request.Request(
            url=f"http://127.0.0.1:{self.host_port}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_node_by_id(self, response_json, node_id):
        nodes = response_json["graph_data"]["nodes"]
        return next(node for node in nodes if node["id"] == node_id)

    def test_preserves_frequency_and_prefers_highest_clean_bandwidth(self):
        payload = {
            "aps": [
                {
                    "id": "ap-1",
                    "label": "AP 1",
                    "x": -23.5505,
                    "y": -46.6333,
                    "raio": 20,
                    "channel": "6",
                    "bandwidth": "20 MHz",
                    "frequency": "2.4 GHz",
                    "locked": False,
                }
            ],
            "strategy": "backtracking",
            "parameters": {"thread_count": 2},
        }

        result = self.post_json("/backtracking", payload)
        node = self.get_node_by_id(result, "ap-1")

        self.assertEqual(node["proposed_frequency"], "2.4 GHz")
        self.assertEqual(node["proposed_bandwidth"], "60 MHz")
        self.assertEqual(node["proposed_channel"], "1")

    def test_respects_locked_access_points(self):
        payload = {
            "aps": [
                {
                    "id": "locked-ap",
                    "label": "Locked AP",
                    "x": -23.5505,
                    "y": -46.6333,
                    "raio": 20,
                    "channel": "44",
                    "bandwidth": "20 MHz",
                    "frequency": "5 GHz",
                    "locked": True,
                },
                {
                    "id": "free-ap",
                    "label": "Free AP",
                    "x": -23.55051,
                    "y": -46.63331,
                    "raio": 20,
                    "channel": "36",
                    "bandwidth": "20 MHz",
                    "frequency": "5 GHz",
                    "locked": False,
                },
            ],
            "strategy": "backtracking",
            "parameters": {"thread_count": 2},
        }

        result = self.post_json("/backtracking", payload)
        node = self.get_node_by_id(result, "locked-ap")

        self.assertEqual(node["proposed_frequency"], "5 GHz")
        self.assertEqual(node["proposed_channel"], "44")
        self.assertEqual(node["proposed_bandwidth"], "20 MHz")

    def test_when_repeat_is_required_prefers_lower_interference_side(self):
        payload = {
            "aps": [
                {
                    "id": "target",
                    "label": "Target",
                    "x": -23.5505,
                    "y": -46.6333,
                    "raio": 100,
                    "channel": "6",
                    "bandwidth": "20 MHz",
                    "frequency": "2.4 GHz",
                    "locked": False,
                },
                {
                    "id": "near-heavy",
                    "label": "Near Heavy",
                    "x": -23.5505,
                    "y": -46.63331,
                    "raio": 100,
                    "channel": "1",
                    "bandwidth": "60 MHz",
                    "frequency": "2.4 GHz",
                    "locked": True,
                },
                {
                    "id": "far-light",
                    "label": "Far Light",
                    "x": -23.5505,
                    "y": -46.6341,
                    "raio": 100,
                    "channel": "11",
                    "bandwidth": "20 MHz",
                    "frequency": "2.4 GHz",
                    "locked": True,
                },
            ],
            "strategy": "backtracking",
            "parameters": {"thread_count": 2},
        }

        result = self.post_json("/backtracking", payload)
        node = self.get_node_by_id(result, "target")

        self.assertEqual(node["proposed_frequency"], "2.4 GHz")
        self.assertEqual(node["proposed_channel"], "11")
        self.assertIn(node["proposed_bandwidth"], {"20 MHz", "40 MHz"})


if __name__ == "__main__":
    unittest.main()
