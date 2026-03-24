import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import networkx as nx


APP_DIR = Path(__file__).resolve().parents[1] / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import routes  # noqa: E402
from main import app  # noqa: E402
from routes import build_collision_graph, calculate_intersection_area, load_access_points, summarize_graph  # noqa: E402
from strategies import (  # noqa: E402
    BacktrackingStrategy,
    GeneticStrategy,
    GreedyStrategy,
    StrategyFactory,
)


def sample_access_points():
    return [
        {"id": "ap-1", "x": -23.55052, "y": -46.633308, "raio": 100, "label": "AP 1", "canal": "1"},
        {"id": "ap-2", "x": -23.55062, "y": -46.633208, "raio": 100, "label": "AP 2", "canal": "6"},
        {"id": "ap-3", "x": -23.56052, "y": -46.643308, "raio": 50, "label": "AP 3", "canal": "11"},
    ]


class StrategyFactoryTests(unittest.TestCase):
    def test_get_strategy_returns_expected_instance(self):
        self.assertIsInstance(StrategyFactory.get_strategy("backtracking"), BacktrackingStrategy)
        self.assertIsInstance(StrategyFactory.get_strategy("greedy"), GreedyStrategy)
        self.assertIsInstance(StrategyFactory.get_strategy("genetic"), GeneticStrategy)

    def test_get_strategy_raises_for_unknown_strategy(self):
        with self.assertRaises(ValueError):
            StrategyFactory.get_strategy("unknown")

    def test_get_available_strategies_lists_all_expected_strategies(self):
        strategies = StrategyFactory.get_available_strategies()
        self.assertIn("backtracking", strategies)
        self.assertIn("greedy", strategies)
        self.assertIn("genetic", strategies)

    def test_backtracking_strategy_finds_maximum_clique_with_manual_backtracking(self):
        graph = nx.Graph()
        graph.add_edges_from([
            ("ap-1", "ap-2"),
            ("ap-1", "ap-3"),
            ("ap-2", "ap-3"),
            ("ap-3", "ap-4"),
        ])

        analysis = StrategyFactory.get_strategy("backtracking").analyze(graph)

        self.assertEqual(analysis["max_clique_size"], 3)
        self.assertEqual(set(analysis["max_clique_nodes"]), {"ap-1", "ap-2", "ap-3"})
        self.assertGreaterEqual(analysis["total_cliques"], 2)
        self.assertIn("ap-1", analysis["proposed_configurations"])
        self.assertIn("color", analysis["proposed_configurations"]["ap-1"])
        self.assertIn("proposed_channel", graph.nodes["ap-1"])


class GraphHelperTests(unittest.TestCase):
    def test_calculate_intersection_area_returns_zero_when_circles_do_not_overlap(self):
        area = calculate_intersection_area(100, 50, 200)

        self.assertEqual(area, 0)

    def test_calculate_intersection_area_returns_smaller_circle_area_when_fully_contained(self):
        area = calculate_intersection_area(100, 50, 20)

        self.assertAlmostEqual(area, 3.141592653589793 * 50 ** 2)

    def test_build_collision_graph_creates_nodes_and_edges(self):
        graph = build_collision_graph(sample_access_points())

        self.assertEqual(graph.number_of_nodes(), 3)
        self.assertGreaterEqual(graph.number_of_edges(), 1)
        self.assertIn("ap-1", graph.nodes)
        self.assertIn("ap-2", graph.nodes)

    def test_build_collision_graph_uses_100_percent_weight_when_smaller_ap_is_fully_contained(self):
        graph = build_collision_graph([
            {"id": "ap-1", "x": -23.55052, "y": -46.633308, "raio": 100, "label": "AP 1", "canal": "1"},
            {"id": "ap-2", "x": -23.55052, "y": -46.633308, "raio": 50, "label": "AP 2", "canal": "36"},
        ])

        self.assertEqual(graph.number_of_edges(), 1)
        self.assertAlmostEqual(graph["ap-1"]["ap-2"]["peso"], 100.0)

    def test_summarize_graph_returns_expected_metrics(self):
        graph = build_collision_graph(sample_access_points())
        summary = summarize_graph(graph)

        self.assertEqual(summary["total_nodes"], 3)
        self.assertEqual(summary["total_edges"], graph.number_of_edges())
        self.assertIn("density", summary)
        self.assertIn("connected_components", summary)


class LoadAccessPointsTests(unittest.TestCase):
    @patch("routes.requests.get")
    def test_load_access_points_fetches_data_from_gateway(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": "ap-1"}]
        mock_get.return_value = mock_response

        with patch.dict(os.environ, {"ANALYSIS_HTTP_TIMEOUT": "120"}, clear=False):
            with patch.object(routes, "GATEWAY_URL", "http://gateway:80"):
                access_points = load_access_points()

        self.assertEqual(access_points, [{"id": "ap-1"}])
        mock_get.assert_called_once_with(
            "http://gateway:80/api/access_points",
            timeout=120,
        )

    def test_load_access_points_raises_when_gateway_url_is_missing(self):
        with patch.object(routes, "GATEWAY_URL", None):
            with self.assertRaisesRegex(RuntimeError, "GATEWAY_URL"):
                load_access_points()

    @patch("routes.requests.get")
    def test_load_access_points_raises_when_gateway_returns_error(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 503
        mock_get.return_value = mock_response

        with patch.dict(os.environ, {"ANALYSIS_HTTP_TIMEOUT": "120"}, clear=False):
            with patch.object(routes, "GATEWAY_URL", "http://gateway:80"):
                with self.assertRaisesRegex(RuntimeError, "Erro ao buscar pontos de acesso"):
                    load_access_points()


class AnalysisRoutesTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_health_endpoint_returns_healthy_status(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "healthy")
        self.assertEqual(payload["service"], "analysis_service")

    def test_strategies_endpoint_returns_available_strategies(self):
        response = self.client.get("/strategies")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertIn("backtracking", payload["strategies"])

    def test_analyze_graph_returns_400_for_empty_payload(self):
        response = self.client.post("/analyze-graph", json={"aps": []})

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["success"])

    def test_analyze_graph_returns_400_for_invalid_strategy(self):
        response = self.client.post(
            "/analyze-graph",
            json={"aps": sample_access_points(), "strategy": "invalid"},
        )

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["success"])
        self.assertIn("invalid", payload["error"])

    def test_analyze_graph_returns_analysis_for_valid_strategy(self):
        response = self.client.post(
            "/analyze-graph",
            json={"aps": sample_access_points(), "strategy": "backtracking"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["strategy_used"], "backtracking")
        self.assertIn("analysis", payload)
        self.assertIn("execution", payload)
        self.assertEqual(payload["execution"]["strategy"], "backtracking")
        self.assertIn("duration_ms", payload["execution"])
        self.assertIn("parameters", payload["execution"])
        self.assertIn("graph_snapshot", payload["execution"])
        self.assertIn("graph_data", payload)
        self.assertIn("summary", payload)

    def test_compare_strategies_returns_results_for_requested_strategies(self):
        response = self.client.post(
            "/compare-strategies",
            json={
                "aps": sample_access_points(),
                "strategies": ["backtracking", "greedy"],
                "parameters": {},
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertIn("backtracking", payload["comparison_results"])
        self.assertIn("greedy", payload["comparison_results"])
        self.assertIn("execution", payload["comparison_results"]["backtracking"])
        self.assertIn("duration_ms", payload["comparison_results"]["backtracking"]["execution"])
        self.assertIn("execution", payload["comparison_results"]["greedy"])

    @patch("routes.load_access_points")
    def test_analyze_endpoint_returns_summary_from_access_points(self, mock_load_access_points):
        mock_load_access_points.return_value = [
            {
                "id": "ap-1",
                "latitude": -23.55,
                "longitude": -46.63,
                "frequency": "2.4 GHz",
                "channel": "1",
                "bandwidth": "20 MHz",
            },
            {
                "id": "ap-2",
                "latitude": None,
                "longitude": None,
                "frequency": "5 GHz",
                "channel": "36",
                "bandwidth": "80 MHz",
            },
        ]

        response = self.client.get("/analyze")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total_points"], 2)
        self.assertEqual(payload["with_coordinates"], 1)
        self.assertEqual(payload["without_coordinates"], 1)
        self.assertIn("available_strategies", payload)


if __name__ == "__main__":
    unittest.main()
