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

    def spectral_factor(self, left, right):
        # Dois APs no mesmo ponto: a sobreposicao espacial w e 100%, e o peso de interferencia e 100 * s.
        aps = [
            {
                "id": ap_id,
                "label": ap_id,
                "x": -23.5505,
                "y": -46.6333,
                "raio": 30,
                "channel": channel,
                "bandwidth": bandwidth,
                "frequency": frequency,
                "locked": False,
            }
            for ap_id, (channel, bandwidth, frequency) in (("left", left), ("right", right))
        ]
        links = self.post_json("/collision-graph", {"aps": aps})["links"]
        self.assertEqual(len(links), 1)
        self.assertAlmostEqual(links[0]["collision_peso"], 100.0)
        return links[0]["interference_peso"] / 100.0

    def test_spectral_overlap_uses_the_center_of_bonded_channels(self):
        cases = [
            # 36 a 80 MHz ocupa 36-48 (centro 5210 MHz) e cobre o canal 48.
            (("36", "80 MHz", "5 GHz"), ("48", "20 MHz", "5 GHz"), 1.0),
            # 44 a 40 MHz ocupa 44-48 (centro 5230 MHz) e cobre o canal 48.
            (("44", "40 MHz", "5 GHz"), ("48", "20 MHz", "5 GHz"), 1.0),
            # 149 a 80 MHz ocupa 149-161 (centro 5775 MHz) e cobre o canal 161.
            (("149", "80 MHz", "5 GHz"), ("161", "20 MHz", "5 GHz"), 1.0),
            # 36 a 40 MHz (36-40) e 44 a 20 MHz so se tocam na borda.
            (("36", "40 MHz", "5 GHz"), ("44", "20 MHz", "5 GHz"), 0.0),
            # 1 a 40 MHz usa o secundario acima (centro no canal 3) e cobre 15 dos 20 MHz do canal 6.
            (("1", "40 MHz", "2.4 GHz"), ("6", "20 MHz", "2.4 GHz"), 0.75),
            # 11 a 40 MHz usa o secundario abaixo (centro no canal 9) e cobre 15 dos 20 MHz do canal 6.
            (("11", "40 MHz", "2.4 GHz"), ("6", "20 MHz", "2.4 GHz"), 0.75),
            # A 20 MHz o centro continua sendo o do proprio canal.
            (("1", "20 MHz", "2.4 GHz"), ("6", "20 MHz", "2.4 GHz"), 0.0),
            (("1", "20 MHz", "2.4 GHz"), ("3", "20 MHz", "2.4 GHz"), 0.5),
            (("36", "20 MHz", "5 GHz"), ("36", "20 MHz", "5 GHz"), 1.0),
        ]
        for left, right, expected in cases:
            with self.subTest(left=left, right=right):
                self.assertAlmostEqual(self.spectral_factor(left, right), expected)

    def ap_at(self, ap_id, frequency, channel, bandwidth="20 MHz", offset=0.0):
        return {
            "id": ap_id,
            "label": ap_id,
            "x": -23.5505 + offset,
            "y": -46.6333,
            "raio": 30,
            "channel": channel,
            "bandwidth": bandwidth,
            "frequency": frequency,
            "locked": False,
        }

    def test_reports_power_of_each_access_point_by_the_consumption_model(self):
        # Mesmos valores do modelo (Dembele et al., 2023) antes calculado no frontend; 160 MHz e 6 GHz ficam fora.
        cases = [
            ("2.4 GHz", "20 MHz", "1", 14.5),
            ("2.4 GHz", "40 MHz", "1", 13.8),
            ("5 GHz", "20 MHz", "36", 11.1),
            ("5 GHz", "40 MHz", "36", 10.3),
            ("5 GHz", "80 MHz", "36", 9.9),
            ("5 GHz", "160 MHz", "36", None),
            ("6 GHz", "20 MHz", "1", None),
        ]
        aps = [
            self.ap_at(f"ap{index}", frequency, channel, bandwidth, offset=index * 0.01)
            for index, (frequency, bandwidth, channel, _) in enumerate(cases)
        ]
        graph = self.post_json("/collision-graph", {"aps": aps})
        nodes = {node["id"]: node for node in graph["nodes"]}

        for index, (frequency, bandwidth, _, watts) in enumerate(cases):
            with self.subTest(frequency=frequency, bandwidth=bandwidth):
                self.assertEqual(nodes[f"ap{index}"]["power_w"], watts)
                self.assertEqual(nodes[f"ap{index}"]["proposed_power_w"], watts)
        self.assertAlmostEqual(graph["power_w"], 14.5 + 13.8 + 11.1 + 10.3 + 9.9)
        self.assertEqual(graph["power_unmodeled_nodes"], 2)

    def test_analysis_reports_power_before_and_after(self):
        aps = [
            self.ap_at("a24-1", "2.4 GHz", "1", "20 MHz"),
            self.ap_at("a24-2", "2.4 GHz", "1", "20 MHz", offset=0.00001),
            self.ap_at("a5-1", "5 GHz", "36", "20 MHz"),
        ]
        result = self.post_json(
            "/analyze-graph",
            {"aps": aps, "strategy": "backtracking", "parameters": {"time_limit_seconds": 0}},
        )
        comparison = result["execution"]["comparison"]
        nodes = result["graph_data"]["nodes"]

        self.assertAlmostEqual(comparison["power_before_w"], 14.5 + 14.5 + 11.1)
        self.assertAlmostEqual(comparison["power_after_w"], sum(node["proposed_power_w"] for node in nodes))
        self.assertAlmostEqual(result["graph_data"]["power_w"], comparison["power_after_w"])
        self.assertEqual(
            sum(band["comparison"]["power_after_w"] for band in result["execution"]["bands"]),
            comparison["power_after_w"],
        )

    def test_comparison_counts_conflicts_and_not_every_overlap(self):
        # Tres APs sobrepostos (3 arestas), mas so o par no canal 1 esta em conflito antes da otimizacao.
        aps = [
            self.ap_at("a", "2.4 GHz", "1"),
            self.ap_at("b", "2.4 GHz", "1", offset=0.00001),
            self.ap_at("c", "2.4 GHz", "11", offset=0.00002),
        ]
        result = self.post_json(
            "/analyze-graph",
            {"aps": aps, "strategy": "backtracking", "parameters": {"time_limit_seconds": 0},
             "channels": {"2.4 GHz": {"20 MHz": ["1", "6", "11"]}}},
        )
        execution = result["execution"]
        comparison = execution["comparison"]

        self.assertEqual(execution["graph_snapshot"]["edges"], 3)
        self.assertEqual(comparison["conflicts_before"], 1)
        self.assertEqual(comparison["conflicts_after"], 0)
        self.assertEqual(comparison["conflicts_after"], execution["search"]["conflicts"])
        self.assertAlmostEqual(comparison["conflict_density_before"], 1 / 3)
        self.assertEqual(comparison["conflict_density_after"], 0)
        self.assertEqual(execution["bands"][0]["comparison"]["conflicts_before"], 1)
        for field in ("edges_before", "edges_after", "density_before", "density_after"):
            self.assertNotIn(field, comparison)

    def test_comparison_reports_interference_and_changed_access_points(self):
        aps = [
            self.ap_at("a", "2.4 GHz", "1"),
            self.ap_at("b", "2.4 GHz", "1", offset=0.00001),
            self.ap_at("c", "2.4GHz", "11", offset=0.00002),
        ]
        before = self.post_json("/collision-graph", {"aps": aps})
        result = self.post_json(
            "/analyze-graph",
            {"aps": aps, "strategy": "backtracking", "parameters": {"time_limit_seconds": 0},
             "channels": {"2.4 GHz": {"20 MHz": ["1", "6", "11"]}}},
        )
        comparison = result["execution"]["comparison"]
        nodes = result["graph_data"]["nodes"]

        self.assertAlmostEqual(comparison["interference_before"], sum(link["interference_peso"] for link in before["links"]))
        self.assertAlmostEqual(comparison["interference_after"], sum(link["interference_peso"] for link in result["graph_data"]["links"]))
        self.assertAlmostEqual(comparison["interference_after"], result["execution"]["search"]["interference_score"])
        # "2.4GHz" com o mesmo canal e largura nao conta como mudanca.
        changed = [
            node for node in nodes
            if (node["channel"], float(node["bandwidth"].split()[0]), float(node["frequency"].rstrip("GHz ")))
            != (node["proposed_channel"], float(node["proposed_bandwidth"].split()[0]), float(node["proposed_frequency"].rstrip("GHz ")))
        ]
        self.assertEqual(comparison["changed_nodes"], len(changed))
        self.assertGreater(comparison["changed_nodes"], 0)

    def test_aps_in_different_bands_are_not_linked(self):
        aps = [self.ap_at("a24", "2.4 GHz", "1"), self.ap_at("a5", "5 GHz", "36")]
        self.assertEqual(self.post_json("/collision-graph", {"aps": aps})["links"], [])

    def test_analysis_reports_results_per_band(self):
        aps = [
            self.ap_at("a24-1", "2.4 GHz", "1"),
            self.ap_at("a24-2", "2.4 GHz", "1", offset=0.00001),
            self.ap_at("a24-3", "2.4 GHz", "1", offset=0.00002),
            self.ap_at("a5-1", "5 GHz", "36"),
            self.ap_at("a5-2", "5 GHz", "36", offset=0.00001),
        ]
        result = self.post_json("/analyze-graph", {"aps": aps, "strategy": "greedy"})
        execution = result["execution"]
        bands = {band["frequency"]: band for band in execution["bands"]}

        self.assertEqual(list(bands), ["2.4 GHz", "5 GHz"])
        self.assertEqual(bands["2.4 GHz"]["nodes"], 3)
        self.assertEqual(bands["2.4 GHz"]["edges"], 3)
        self.assertEqual(bands["5 GHz"]["nodes"], 2)
        self.assertEqual(bands["5 GHz"]["edges"], 1)
        self.assertEqual(execution["graph_snapshot"]["edges"], 4)
        for field in ("conflicts", "greedy_conflicts", "nodes_explored"):
            self.assertEqual(
                execution["search"][field],
                sum(band["search"][field] for band in execution["bands"]),
            )
        for node in result["graph_data"]["nodes"]:
            self.assertEqual(node["proposed_frequency"], node["frequency"])

    def test_uses_only_the_requested_channels_of_each_band(self):
        aps = [
            self.ap_at("a24-1", "2.4 GHz", "6"),
            self.ap_at("a24-2", "2.4 GHz", "6", offset=0.00001),
            self.ap_at("a5-1", "5 GHz", "149"),
        ]
        cases = [
            ({"2.4 GHz": {"20 MHz": ["1"]}}, {"1"}, 1),
            ({"2.4 GHz": {"20 MHz": ["1", "6"]}}, {"1", "6"}, 0),
        ]
        for channels, expected_channels, expected_conflicts in cases:
            with self.subTest(channels=channels):
                result = self.post_json(
                    "/analyze-graph",
                    {"aps": aps, "strategy": "backtracking", "channels": channels, "parameters": {"time_limit_seconds": 0}},
                )
                nodes = {node["id"]: node for node in result["graph_data"]["nodes"]}
                bands = {band["frequency"]: band for band in result["execution"]["bands"]}

                self.assertEqual({nodes[ap_id]["proposed_channel"] for ap_id in ("a24-1", "a24-2")}, expected_channels)
                self.assertEqual({nodes[ap_id]["proposed_bandwidth"] for ap_id in ("a24-1", "a24-2")}, {"20 MHz"})
                self.assertEqual(bands["2.4 GHz"]["search"]["conflicts"], expected_conflicts)
                self.assertEqual(bands["2.4 GHz"]["profile_count"], len(expected_channels))
                # A faixa nao informada usa os perfis padrao (10 em 5 GHz).
                self.assertEqual(bands["5 GHz"]["profile_count"], 10)

    def test_rejects_invalid_channel_selections(self):
        aps = [self.ap_at("a24-1", "2.4 GHz", "1")]
        invalid_cases = [
            ({"2.4 GHz": {"60 MHz": ["1"]}}, "Largura de banda invalida"),
            ({"2.4 GHz": {"20 MHz": ["14"]}}, "Canal invalido"),
            ({"5 GHz": {"40 MHz": ["165"]}}, "Canal invalido"),
            ({"3 GHz": {"20 MHz": ["1"]}}, "Faixa invalida"),
            ({"2.4 GHz": {"20 MHz": []}}, "ao menos um canal"),
            (["1", "6"], "Campo channels"),
        ]
        for channels, message in invalid_cases:
            with self.subTest(channels=channels):
                with self.assertRaises(urllib.error.HTTPError) as context:
                    self.post_json("/analyze-graph", {"aps": aps, "strategy": "greedy", "channels": channels})
                with context.exception as error:
                    self.assertEqual(error.code, 400)
                    body = json.loads(error.read().decode("utf-8"))
                self.assertIn(message, body["error"])

    def test_channel_plan_lists_valid_channels_per_band_and_bandwidth(self):
        valid = self.get_json("/channel-plan")["valid"]

        self.assertEqual(set(valid), {"2.4 GHz", "5 GHz", "6 GHz"})
        self.assertEqual(set(valid["2.4 GHz"]), {"20 MHz", "40 MHz"})
        self.assertEqual(valid["2.4 GHz"]["20 MHz"], [str(channel) for channel in range(1, 14)])
        self.assertEqual(valid["2.4 GHz"]["40 MHz"], [str(channel) for channel in range(1, 14)])

        five = valid["5 GHz"]
        self.assertEqual(len(five["20 MHz"]), 25)
        self.assertNotIn("165", five["40 MHz"])
        self.assertIn("161", five["40 MHz"])
        self.assertEqual(five["80 MHz"][:4], ["36", "40", "44", "48"])
        self.assertNotIn("165", five["80 MHz"])
        self.assertEqual(len(five["160 MHz"]), 16)
        self.assertNotIn("149", five["160 MHz"])

        six = valid["6 GHz"]
        self.assertEqual(len(six["20 MHz"]), 59)
        self.assertNotIn("233", six["40 MHz"])
        self.assertEqual(len(six["160 MHz"]), 56)

    def test_channel_plan_options_list_each_distinct_block_once(self):
        plan = self.get_json("/channel-plan")
        options = plan["options"]

        def blocks(frequency, bandwidth):
            return [option["channels"] for option in options[frequency][bandwidth]]

        self.assertEqual(len(blocks("2.4 GHz", "20 MHz")), 13)
        self.assertEqual(blocks("2.4 GHz", "40 MHz"), [[str(p), str(p + 4)] for p in range(1, 10)])
        self.assertEqual(len(blocks("5 GHz", "20 MHz")), 25)
        self.assertEqual(len(blocks("5 GHz", "40 MHz")), 12)
        self.assertEqual(
            blocks("5 GHz", "80 MHz"),
            [["36", "40", "44", "48"], ["52", "56", "60", "64"], ["100", "104", "108", "112"],
             ["116", "120", "124", "128"], ["132", "136", "140", "144"], ["149", "153", "157", "161"]],
        )
        self.assertEqual(len(blocks("5 GHz", "160 MHz")), 2)
        self.assertEqual(
            [len(blocks("6 GHz", width)) for width in ("20 MHz", "40 MHz", "80 MHz", "160 MHz")],
            [59, 29, 14, 7],
        )

        for frequency, bandwidths in options.items():
            for bandwidth, entries in bandwidths.items():
                for option in entries:
                    with self.subTest(frequency=frequency, bandwidth=bandwidth, option=option):
                        self.assertIn(option["channel"], option["channels"])
                        self.assertIn(option["channel"], plan["valid"][frequency][bandwidth])

        # Cada perfil padrao e o primario da opcao que cobre o seu bloco (11 a 40 MHz e o par 7+11).
        for frequency, bandwidths in plan["profiles"].items():
            for bandwidth, channels in bandwidths.items():
                primaries = [option["channel"] for option in options[frequency][bandwidth]]
                for channel in channels:
                    with self.subTest(frequency=frequency, bandwidth=bandwidth, channel=channel):
                        self.assertIn(channel, primaries)

    def test_channel_plan_options_report_the_occupied_spectrum(self):
        options = self.get_json("/channel-plan")["options"]

        def bounds(frequency, bandwidth, channel):
            option = next(item for item in options[frequency][bandwidth] if item["channel"] == channel)
            return option["lower_mhz"], option["upper_mhz"]

        self.assertEqual(bounds("2.4 GHz", "20 MHz", "1"), (2402, 2422))
        self.assertEqual(bounds("2.4 GHz", "40 MHz", "1"), (2402, 2442))
        self.assertEqual(bounds("2.4 GHz", "40 MHz", "11"), (2432, 2472))
        self.assertEqual(bounds("5 GHz", "80 MHz", "36"), (5170, 5250))
        self.assertEqual(bounds("5 GHz", "160 MHz", "100"), (5490, 5650))
        self.assertEqual(bounds("6 GHz", "20 MHz", "1"), (5945, 5965))
        for frequency, bandwidths in options.items():
            for bandwidth, entries in bandwidths.items():
                width = float(bandwidth.split()[0])
                for option in entries:
                    with self.subTest(frequency=frequency, bandwidth=bandwidth, channel=option["channel"]):
                        self.assertAlmostEqual(option["upper_mhz"] - option["lower_mhz"], width)

    def test_channel_plan_profiles_are_valid_combinations(self):
        plan = self.get_json("/channel-plan")
        profiles = plan["profiles"]

        self.assertEqual(set(profiles), {"2.4 GHz", "5 GHz"})
        for frequency, bandwidths in profiles.items():
            for bandwidth, channels in bandwidths.items():
                with self.subTest(frequency=frequency, bandwidth=bandwidth):
                    self.assertIn(bandwidth, plan["valid"][frequency])
                    self.assertTrue(set(channels) <= set(plan["valid"][frequency][bandwidth]))

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
