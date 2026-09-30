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

    def test_strategies_describe_their_parameters(self):
        details = {item["name"]: item for item in self.get_json("/strategies")["strategy_details"]}

        backtracking = {parameter["name"]: parameter for parameter in details["backtracking"]["parameters"]}
        self.assertEqual(backtracking["thread_count"]["type"], "integer")
        self.assertEqual(backtracking["thread_count"]["min"], 1)
        self.assertEqual(backtracking["time_limit_seconds"]["default"], 60)
        self.assertTrue(backtracking["time_limit_seconds"]["zero_disables"])
        self.assertEqual(details["greedy"]["parameters"], [])
        self.assertFalse(details["genetic"]["implemented"])

    def test_rejects_parameters_outside_the_declared_range(self):
        aps = self.random_aps(4, seed=1)
        invalid_cases = [
            {"time_limit_seconds": 5000},
            {"thread_count": 0},
            {"thread_count": 1.5},
            {"time_limit_seconds": "60"},
        ]
        for parameters in invalid_cases:
            with self.subTest(parameters=parameters):
                with self.assertRaises(urllib.error.HTTPError) as context:
                    self.post_json("/analyze-graph", {"aps": aps, "strategy": "backtracking", "parameters": parameters})
                with context.exception as error:
                    self.assertEqual(error.code, 400)
                    body = json.loads(error.read().decode("utf-8"))
                self.assertIn(next(iter(parameters)), body["error"])

    def test_execution_reports_only_the_parameters_of_the_strategy(self):
        aps = self.random_aps(4, seed=2)
        greedy = self.post_json("/analyze-graph", {"aps": aps, "strategy": "greedy", "parameters": {"thread_count": 4}})
        exact = self.post_json(
            "/analyze-graph",
            {"aps": aps, "strategy": "backtracking", "parameters": {"thread_count": 2, "time_limit_seconds": 0}},
        )

        self.assertEqual(greedy["execution"]["parameters"], {})
        self.assertEqual(exact["execution"]["parameters"], {"thread_count": 2, "time_limit_seconds": 0})
        self.assertTrue(exact["execution"]["search"]["optimal"])

    def test_result_is_the_same_for_any_thread_count(self):
        aps = self.random_aps(9, seed=11)
        results = [
            self.post_json("/backtracking", {"aps": aps, "parameters": {"thread_count": threads, "time_limit_seconds": 0}})
            for threads in (1, 2, 4, 8)
        ]

        for result in results:
            self.assertTrue(result["execution"]["search"]["optimal"])
            self.assertEqual(self.proposals(result), self.proposals(results[0]))

    def test_exact_search_is_never_worse_than_greedy(self):
        aps = self.random_aps(9, seed=5)
        greedy = self.post_json("/analyze-graph", {"aps": aps, "strategy": "greedy"})
        exact = self.post_json("/backtracking", {"aps": aps, "parameters": {"thread_count": 4, "time_limit_seconds": 0}})

        self.assertEqual(greedy["strategy_used"], "greedy")
        self.assertFalse(greedy["execution"]["search"]["optimal"])
        self.assertTrue(exact["execution"]["search"]["optimal"])
        self.assertLessEqual(
            exact["execution"]["search"]["conflicts"],
            greedy["execution"]["search"]["conflicts"],
        )
        self.assertEqual(
            exact["execution"]["search"]["greedy_conflicts"],
            greedy["execution"]["search"]["conflicts"],
        )

    def test_time_limit_stops_search_with_best_solution_found(self):
        aps = self.random_aps(150, seed=7, spread=0.002)
        started = time.time()
        result = self.post_json(
            "/backtracking",
            {"aps": aps, "parameters": {"thread_count": 2, "time_limit_seconds": 1}},
            timeout=60,
        )
        elapsed = time.time() - started
        search = result["execution"]["search"]

        self.assertLess(elapsed, 10)
        self.assertEqual(search["stop_reason"], "time_limit")
        self.assertFalse(search["optimal"])
        self.assertLessEqual(search["conflicts"], search["greedy_conflicts"])
        self.assertEqual(result["execution"]["parameters"]["time_limit_seconds"], 1)

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
        self.assertEqual(node["proposed_bandwidth"], "40 MHz")
        self.assertEqual(node["proposed_channel"], "1")

    def test_proposes_only_bandwidths_valid_for_the_band(self):
        valid_bandwidths = {
            "2.4 GHz": {"20 MHz", "40 MHz"},
            "5 GHz": {"20 MHz", "40 MHz", "80 MHz"},
        }
        for seed in (3, 13, 23):
            aps = self.random_aps(8, seed=seed)
            for index, ap in enumerate(aps[::2]):
                ap.update({"frequency": "5 GHz", "channel": ("36", "44", "149", "157")[index % 4]})
            for strategy in ("greedy", "backtracking"):
                with self.subTest(seed=seed, strategy=strategy):
                    result = self.post_json(
                        "/analyze-graph",
                        {"aps": aps, "strategy": strategy, "parameters": {"time_limit_seconds": 0}},
                    )
                    for node in result["graph_data"]["nodes"]:
                        self.assertIn(node["proposed_bandwidth"], valid_bandwidths[node["proposed_frequency"]])

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
                    "id": "near-heavy-1",
                    "label": "Near Heavy 1",
                    "x": -23.5505,
                    "y": -46.63331,
                    "raio": 100,
                    "channel": "1",
                    "bandwidth": "20 MHz",
                    "frequency": "2.4 GHz",
                    "locked": True,
                },
                {
                    "id": "near-heavy-6",
                    "label": "Near Heavy 6",
                    "x": -23.5505,
                    "y": -46.63331,
                    "raio": 100,
                    "channel": "6",
                    "bandwidth": "20 MHz",
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
