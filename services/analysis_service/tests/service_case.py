import json
import os
import random
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


class AnalysisServiceTestCase(unittest.TestCase):
    """Sobe o analysis_service num conteiner (imagem montada a partir do Dockerfile) para os testes por HTTP."""

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
        cls.container_name = f"powertrackz-analysis-test-{cls.__name__.lower()}-{os.getpid()}"
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

    def post_json(self, path, payload, timeout=20):
        request = urllib.request.Request(
            url=f"http://127.0.0.1:{self.host_port}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_node_by_id(self, response_json, node_id):
        nodes = response_json["graph_data"]["nodes"]
        return next(node for node in nodes if node["id"] == node_id)

    def random_aps(self, count, seed, spread=0.0012):
        rnd = random.Random(seed)
        return [
            {
                "id": f"ap-{index}",
                "label": f"AP {index}",
                "x": -23.5505 + rnd.uniform(0, spread),
                "y": -46.6333 + rnd.uniform(0, spread),
                "raio": 60,
                "channel": rnd.choice(["1", "6", "11"]),
                "bandwidth": "20 MHz",
                "frequency": "2.4 GHz",
                "locked": False,
            }
            for index in range(count)
        ]

    def proposals(self, response_json):
        return sorted(
            (node["id"], node["proposed_channel"], node["proposed_bandwidth"])
            for node in response_json["graph_data"]["nodes"]
        )

    def get_json(self, path):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.host_port}{path}", timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
