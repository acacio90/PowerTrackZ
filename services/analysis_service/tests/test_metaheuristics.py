import http.client
import json
import subprocess
import time
import unittest
import urllib.error

from service_case import REPO_ROOT, SERVICE_DIR, AnalysisServiceTestCase


class AnalysisServiceMetaheuristicTests(AnalysisServiceTestCase):
    """Base comum das metaheuristicas, exercitada pela busca local (local_search)."""

    def dense_aps(self, count, seed):
        # Metade em 2,4 GHz e metade em 5 GHz, proximos o bastante para haver muitos conflitos.
        aps = self.random_aps(count, seed=seed, spread=0.0015)
        for index, ap in enumerate(aps):
            ap["raio"] = 25
            if index % 2:
                ap.update({"frequency": "5 GHz", "channel": "36", "bandwidth": "20 MHz", "raio": 20})
        return aps

    def local_search(self, aps, timeout=60, **parameters):
        return self.post_json(
            "/analyze-graph",
            {"aps": aps, "strategy": "local_search", "parameters": parameters},
            timeout=timeout,
        )

    def assert_rejected(self, payload, expected_text):
        with self.assertRaises(urllib.error.HTTPError) as context:
            self.post_json("/analyze-graph", payload)
        with context.exception as error:
            self.assertEqual(error.code, 400)
            body = json.loads(error.read().decode("utf-8"))
        self.assertIn(expected_text, body["error"])

    def test_c_unit_tests_of_the_common_base_pass(self):
        # Custo incremental x recalculo completo, vizinhanca, APs travados e gerador (tests/c).
        result = subprocess.run(
            ["docker", "build", "--target", "test", SERVICE_DIR],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-3000:])

    def test_local_search_is_declared_as_a_metaheuristic_with_the_common_parameters(self):
        details = {item["name"]: item for item in self.get_json("/strategies")["strategy_details"]}
        local_search = details["local_search"]
        parameters = {parameter["name"]: parameter for parameter in local_search["parameters"]}

        self.assertEqual(local_search["family"], "metaheuristic")
        self.assertFalse(local_search["exact"])
        self.assertTrue(local_search["implemented"])
        self.assertEqual(
            list(parameters),
            ["seed", "time_limit_seconds", "max_iterations", "max_iterations_without_improvement", "initial_solution"],
        )
        self.assertTrue(parameters["seed"]["optional"])
        self.assertIsNone(parameters["seed"]["default"])
        self.assertEqual(parameters["seed"]["max"], 4294967295)
        self.assertEqual(parameters["initial_solution"]["type"], "choice")
        self.assertEqual(parameters["initial_solution"]["default"], "greedy")
        self.assertEqual([option["value"] for option in parameters["initial_solution"]["options"]], ["greedy", "random"])
        self.assertFalse(parameters["time_limit_seconds"]["optional"])

    def test_same_seed_and_parameters_give_the_same_result(self):
        aps = self.dense_aps(60, seed=21)
        parameters = {"seed": 123, "time_limit_seconds": 0, "max_iterations": 20000, "initial_solution": "random"}
        first = self.local_search(aps, **parameters)
        second = self.local_search(aps, **parameters)

        self.assertEqual(first["execution"]["seed"], 123)
        self.assertEqual(first["execution"]["parameters"]["seed"], 123)
        self.assertEqual(self.proposals(first), self.proposals(second))
        strip_time = lambda result: [
            [{key: value for key, value in point.items() if key != "time_ms"} for point in band["convergence"]]
            for band in result["execution"]["bands"]
        ]
        self.assertEqual(strip_time(first), strip_time(second))

    def test_seed_is_drawn_and_returned_when_not_given(self):
        aps = self.dense_aps(40, seed=22)
        drawn = self.local_search(aps, time_limit_seconds=0, max_iterations=5000, initial_solution="random")
        seed = drawn["execution"]["seed"]

        self.assertIsInstance(seed, int)
        self.assertTrue(0 <= seed <= 4294967295)
        self.assertEqual(drawn["execution"]["parameters"]["seed"], seed)
        repeated = self.local_search(aps, seed=seed, time_limit_seconds=0, max_iterations=5000, initial_solution="random")
        self.assertEqual(self.proposals(repeated), self.proposals(drawn))

    def test_different_seeds_explore_differently(self):
        aps = self.dense_aps(60, seed=23)
        curves = {
            json.dumps([band["search"]["conflicts"] for band in result["execution"]["bands"]])
            + json.dumps(self.proposals(result))
            for result in (
                self.local_search(aps, seed=seed, time_limit_seconds=0, max_iterations=3000, initial_solution="random")
                for seed in (1, 2, 3)
            )
        }
        self.assertGreater(len(curves), 1)

    def test_stops_at_the_iteration_limit(self):
        aps = self.dense_aps(40, seed=24)
        result = self.local_search(aps, time_limit_seconds=0, max_iterations=300, max_iterations_without_improvement=0)
        execution = result["execution"]

        self.assertEqual(execution["search"]["stop_reason"], "iteration_limit")
        self.assertFalse(execution["search"]["optimal"])
        for band in execution["bands"]:
            self.assertEqual(band["search"]["stop_reason"], "iteration_limit")
            self.assertEqual(band["search"]["iterations"], 300)
        self.assertEqual(execution["search"]["iterations"], 300 * len(execution["bands"]))

    def test_stops_after_iterations_without_improvement(self):
        aps = self.dense_aps(40, seed=25)
        result = self.local_search(aps, time_limit_seconds=0, max_iterations=0, max_iterations_without_improvement=200)

        for band in result["execution"]["bands"]:
            curve = band["convergence"]
            last_improvement = max(point["iteration"] for point in curve[:-1]) if len(curve) > 1 else 0
            self.assertEqual(band["search"]["stop_reason"], "no_improvement")
            self.assertEqual(band["search"]["iterations"] - last_improvement, 200)

    def test_stops_at_the_time_limit(self):
        aps = self.dense_aps(300, seed=26)
        started = time.time()
        result = self.local_search(aps, timeout=60, time_limit_seconds=1, max_iterations=0, max_iterations_without_improvement=0)
        elapsed = time.time() - started
        execution = result["execution"]

        self.assertEqual(execution["search"]["stop_reason"], "time_limit")
        self.assertLess(elapsed, len(execution["bands"]) * 1 + 5)
        for band in execution["bands"]:
            self.assertEqual(band["search"]["stop_reason"], "time_limit")
            self.assertGreater(band["search"]["iterations"], 0)

    def test_rejects_invalid_parameters(self):
        aps = self.dense_aps(4, seed=27)
        cases = [
            ({"time_limit_seconds": 0, "max_iterations": 0, "max_iterations_without_improvement": 0}, "critérios de parada"),
            ({"initial_solution": "best"}, "initial_solution"),
            ({"seed": -1}, "seed"),
            ({"seed": 4294967296}, "seed"),
            ({"seed": 1.5}, "seed"),
        ]
        for parameters, expected in cases:
            with self.subTest(parameters=parameters):
                self.assert_rejected({"aps": aps, "strategy": "local_search", "parameters": parameters}, expected)

    def test_convergence_curve_tracks_the_best_cost(self):
        aps = self.dense_aps(60, seed=28)
        result = self.local_search(aps, seed=5, time_limit_seconds=0, max_iterations=20000, initial_solution="random")

        for band in result["execution"]["bands"]:
            curve = band["convergence"]
            search = band["search"]
            self.assertEqual(curve[0]["iteration"], 0)
            self.assertEqual(curve[0]["conflicts"], search["greedy_conflicts"])
            self.assertEqual(curve[-1]["iteration"], search["iterations"])
            self.assertEqual(curve[-1]["conflicts"], search["conflicts"])
            self.assertAlmostEqual(curve[-1]["interference"], search["interference_score"], places=6)
            # Objetivo padrao: (conflitos, interferencia, -banda) nunca piora ao longo da curva.
            keys = [(point["conflicts"], round(point["interference"], 6), -point["bandwidth"]) for point in curve]
            self.assertEqual(keys, sorted(keys, reverse=True))
            self.assertEqual([point["iteration"] for point in curve], sorted(point["iteration"] for point in curve))

    def test_reported_cost_matches_the_independent_comparison(self):
        aps = self.dense_aps(80, seed=29)
        result = self.local_search(aps, seed=9, time_limit_seconds=0, max_iterations=30000, initial_solution="random")
        execution = result["execution"]

        self.assertEqual(execution["search"]["conflicts"], execution["comparison"]["conflicts_after"])
        self.assertAlmostEqual(execution["search"]["interference_score"], execution["comparison"]["interference_after"], places=6)

    def test_starting_from_greedy_is_never_worse_than_greedy(self):
        aps = self.dense_aps(60, seed=30)
        for objective in ("default", "energy_first"):
            with self.subTest(objective=objective):
                greedy = self.post_json("/analyze-graph", {"aps": aps, "strategy": "greedy", "objective": objective})
                local = self.post_json(
                    "/analyze-graph",
                    {
                        "aps": aps,
                        "strategy": "local_search",
                        "objective": objective,
                        "parameters": {"seed": 1, "time_limit_seconds": 0, "max_iterations": 10000},
                    },
                )
                greedy_search = greedy["execution"]["search"]
                local_search = local["execution"]["search"]
                self.assertEqual(local_search["greedy_conflicts"], greedy_search["conflicts"])
                if objective == "default":
                    self.assertLessEqual(local_search["conflicts"], greedy_search["conflicts"])
                else:
                    self.assertLessEqual(local_search["power_score_w"], greedy_search["power_score_w"])

    def test_respects_locked_access_points(self):
        aps = self.dense_aps(30, seed=31)
        locked = {ap["id"]: ap for ap in aps[::5]}
        for ap in locked.values():
            ap["locked"] = True
            ap.update({"channel": "6", "bandwidth": "20 MHz"} if ap["frequency"] == "2.4 GHz" else {"channel": "44", "bandwidth": "20 MHz"})
        result = self.local_search(aps, seed=3, time_limit_seconds=0, max_iterations=20000, initial_solution="random")

        for ap_id, ap in locked.items():
            node = self.get_node_by_id(result, ap_id)
            self.assertEqual(
                (node["proposed_channel"], node["proposed_bandwidth"], node["proposed_frequency"]),
                (ap["channel"], ap["bandwidth"], ap["frequency"]),
            )

    def test_streams_progress_and_can_be_cancelled(self):
        aps = self.dense_aps(200, seed=32)
        payload = {
            "aps": aps,
            "strategy": "local_search",
            "parameters": {"time_limit_seconds": 60, "max_iterations": 0, "max_iterations_without_improvement": 0},
        }
        connection = http.client.HTTPConnection("127.0.0.1", self.host_port, timeout=30)
        connection.request("POST", "/analyze-graph-stream", body=json.dumps(payload), headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        started = time.time()
        events = []
        cancelled_at = None
        try:
            while True:
                line = response.readline()
                if not line:
                    break
                event = json.loads(line.decode("utf-8"))
                events.append(event["type"])
                if event["type"] == "started":
                    job_id = event["payload"]["job_id"]
                elif event["type"] == "progress" and cancelled_at is None and events.count("progress") >= 2:
                    self.assertIn("iteration", event["payload"])
                    self.post_json("/cancel-analysis", {"job_id": job_id})
                    cancelled_at = time.time()
                elif event["type"] in ("cancelled", "result", "error"):
                    break
        finally:
            connection.close()

        self.assertIsNotNone(cancelled_at)
        self.assertEqual(events[-1], "cancelled")
        self.assertLess(time.time() - started, 15)



class SimulatedAnnealingTests(AnalysisServiceTestCase):
    """Simulated Annealing (#82) sobre a base comum."""

    def annealing(self, aps, **parameters):
        return self.post_json(
            "/analyze-graph",
            {"aps": aps, "strategy": "simulated_annealing", "parameters": parameters},
            timeout=60,
        )

    def dense_aps(self, count, seed):
        return AnalysisServiceMetaheuristicTests.dense_aps(self, count, seed)

    def test_is_declared_with_its_parameters(self):
        details = {item["name"]: item for item in self.get_json("/strategies")["strategy_details"]}
        annealing = details["simulated_annealing"]
        parameters = {parameter["name"]: parameter for parameter in annealing["parameters"]}

        self.assertEqual(annealing["family"], "metaheuristic")
        self.assertFalse(annealing["exact"])
        self.assertTrue(annealing["implemented"])
        self.assertTrue(
            {"seed", "time_limit_seconds", "initial_temperature", "cooling_schedule", "cooling_rate",
             "iterations_per_temperature", "min_temperature", "max_iterations",
             "max_iterations_without_improvement", "initial_solution"} <= set(parameters)
        )
        self.assertTrue(parameters["initial_temperature"]["optional"])
        self.assertEqual(parameters["initial_temperature"]["optional_label"], "Estimada")
        self.assertEqual(parameters["seed"]["optional_label"], "Sorteada")
        self.assertEqual([option["value"] for option in parameters["cooling_schedule"]["options"]], ["geometric", "linear"])

    def test_same_seed_gives_the_same_result(self):
        aps = self.dense_aps(60, seed=40)
        parameters = {"seed": 77, "time_limit_seconds": 0, "max_iterations": 20000, "min_temperature": 0}
        first = self.annealing(aps, **parameters)
        second = self.annealing(aps, **parameters)

        self.assertEqual(self.proposals(first), self.proposals(second))
        self.assertEqual(
            [band["search"]["accepted_worse"] for band in first["execution"]["bands"]],
            [band["search"]["accepted_worse"] for band in second["execution"]["bands"]],
        )

    def test_accepts_worse_solutions_at_high_temperature_and_returns_the_best(self):
        aps = self.dense_aps(60, seed=41)
        common = {"seed": 3, "time_limit_seconds": 0, "max_iterations": 5000, "max_iterations_without_improvement": 0, "min_temperature": 0}
        hot = self.annealing(aps, initial_temperature=100000, **common)
        cold = self.annealing(aps, initial_temperature=0.0001, **common)

        hot_worse = sum(band["search"]["accepted_worse"] for band in hot["execution"]["bands"])
        cold_worse = sum(band["search"]["accepted_worse"] for band in cold["execution"]["bands"])
        self.assertGreater(hot_worse, 1000)
        self.assertLess(cold_worse, hot_worse / 10)
        # A solucao corrente anda por pioras, mas a devolvida e a melhor: nunca pior que a inicial (o guloso).
        for band in hot["execution"]["bands"]:
            self.assertLessEqual(band["search"]["conflicts"], band["search"]["greedy_conflicts"])
        self.assertEqual(hot["execution"]["search"]["conflicts"], hot["execution"]["comparison"]["conflicts_after"])

    def test_estimates_the_initial_temperature_when_not_given(self):
        result = self.annealing(self.dense_aps(40, seed=42), seed=1, time_limit_seconds=0, max_iterations=2000)
        for band in result["execution"]["bands"]:
            self.assertTrue(band["search"]["initial_temperature_estimated"])
            self.assertGreater(band["search"]["initial_temperature"], 0)

    def test_cooling_schedules_stop_at_the_minimum_temperature(self):
        aps = self.dense_aps(40, seed=43)
        cases = (
            # Geometrico: 1 -> 0,5 -> 0,25 (< 0,5) para no segundo patamar.
            ({"cooling_schedule": "geometric", "cooling_rate": 0.5, "min_temperature": 0.5}, 20),
            # Linear: 1 -> 0,75 -> 0,5 -> 0,25 -> 0 para no quarto patamar.
            ({"cooling_schedule": "linear", "cooling_rate": 0.75, "min_temperature": 0}, 40),
        )
        for parameters, iterations in cases:
            with self.subTest(parameters=parameters):
                result = self.annealing(
                    aps, seed=1, time_limit_seconds=0, initial_temperature=1, iterations_per_temperature=10, **parameters
                )
                self.assertEqual(result["execution"]["search"]["stop_reason"], "min_temperature")
                for band in result["execution"]["bands"]:
                    self.assertEqual(band["search"]["stop_reason"], "min_temperature")
                    self.assertEqual(band["search"]["iterations"], iterations)

    def test_rejects_a_minimum_temperature_above_the_initial(self):
        with self.assertRaises(urllib.error.HTTPError) as context:
            self.annealing(self.dense_aps(4, seed=44), initial_temperature=0.01, min_temperature=0.5)
        with context.exception as error:
            self.assertEqual(error.code, 400)
            self.assertIn("temperatura mínima", json.loads(error.read().decode("utf-8"))["error"])



class TabuSearchTests(AnalysisServiceTestCase):
    """Busca Tabu (#83) sobre a base comum. A lista tabu e a aspiracao tem testes em C (tests/c)."""

    def tabu(self, aps, **parameters):
        return self.post_json("/analyze-graph", {"aps": aps, "strategy": "tabu_search", "parameters": parameters}, timeout=60)

    def dense_aps(self, count, seed):
        return AnalysisServiceMetaheuristicTests.dense_aps(self, count, seed)

    def test_is_declared_with_its_parameters(self):
        details = {item["name"]: item for item in self.get_json("/strategies")["strategy_details"]}
        tabu = details["tabu_search"]
        parameters = {parameter["name"]: parameter for parameter in tabu["parameters"]}

        self.assertEqual(tabu["family"], "metaheuristic")
        self.assertFalse(tabu["exact"])
        self.assertTrue({"seed", "time_limit_seconds", "tabu_tenure", "candidate_nodes", "max_iterations",
                         "max_iterations_without_improvement", "initial_solution"} <= set(parameters))
        self.assertEqual(parameters["tabu_tenure"]["default"], 10)

    def test_same_seed_gives_the_same_result(self):
        aps = self.dense_aps(60, seed=50)
        parameters = {"seed": 11, "time_limit_seconds": 0, "max_iterations": 2000, "initial_solution": "random"}
        first = self.tabu(aps, **parameters)
        second = self.tabu(aps, **parameters)

        self.assertEqual(self.proposals(first), self.proposals(second))
        self.assertEqual(
            [band["search"]["tabu_rejections"] for band in first["execution"]["bands"]],
            [band["search"]["tabu_rejections"] for band in second["execution"]["bands"]],
        )

    def test_moves_to_worse_neighbors_but_returns_the_best(self):
        aps = self.dense_aps(60, seed=51)
        result = self.tabu(aps, seed=2, time_limit_seconds=0, max_iterations=3000, max_iterations_without_improvement=0)

        bands = result["execution"]["bands"]
        self.assertGreater(sum(band["search"]["worsening_moves"] for band in bands), 0)
        self.assertGreater(sum(band["search"]["tabu_rejections"] for band in bands), 0)
        for band in bands:
            self.assertLessEqual(band["search"]["conflicts"], band["search"]["greedy_conflicts"])
            self.assertEqual(band["search"]["iterations"], 3000)
        self.assertEqual(result["execution"]["search"]["conflicts"], result["execution"]["comparison"]["conflicts_after"])

    def test_a_longer_tenure_forbids_more_moves(self):
        aps = self.dense_aps(60, seed=52)
        common = {"seed": 4, "time_limit_seconds": 0, "max_iterations": 2000, "max_iterations_without_improvement": 0}
        short = self.tabu(aps, tabu_tenure=1, **common)
        long = self.tabu(aps, tabu_tenure=500, **common)

        rejections = lambda result: sum(band["search"]["tabu_rejections"] for band in result["execution"]["bands"])
        self.assertGreater(rejections(long), rejections(short))



class GeneticAlgorithmTests(AnalysisServiceTestCase):
    """Algoritmo Genetico (#84). Os operadores tem testes em C (tests/c)."""

    def genetic(self, aps, **parameters):
        return self.post_json("/analyze-graph", {"aps": aps, "strategy": "genetic", "parameters": parameters}, timeout=60)

    def dense_aps(self, count, seed):
        return AnalysisServiceMetaheuristicTests.dense_aps(self, count, seed)

    def test_is_implemented_with_its_parameters(self):
        details = {item["name"]: item for item in self.get_json("/strategies")["strategy_details"]}
        genetic = details["genetic"]
        parameters = {parameter["name"]: parameter for parameter in genetic["parameters"]}

        self.assertTrue(genetic["implemented"])
        self.assertEqual(genetic["family"], "metaheuristic")
        self.assertTrue({"seed", "time_limit_seconds", "population_size", "generations", "max_iterations_without_improvement",
                         "greedy_fraction", "crossover", "crossover_rate", "mutation_rate", "tournament_size", "elitism"} <= set(parameters))
        self.assertEqual([option["value"] for option in parameters["crossover"]["options"]], ["uniform", "one_point"])

    def test_same_seed_gives_the_same_result(self):
        aps = self.dense_aps(60, seed=60)
        parameters = {"seed": 21, "time_limit_seconds": 0, "generations": 60, "population_size": 30}
        first = self.genetic(aps, **parameters)
        second = self.genetic(aps, **parameters)

        self.assertEqual(self.proposals(first), self.proposals(second))
        for band in first["execution"]["bands"]:
            self.assertEqual(band["search"]["iterations"], 60)
            self.assertEqual(band["search"]["evaluations"], 30 + 60 * (30 - 2))

    def test_elitism_never_lets_the_best_of_a_generation_get_worse(self):
        aps = self.dense_aps(60, seed=61)
        common = {"seed": 6, "time_limit_seconds": 0, "generations": 80, "population_size": 20,
                  "mutation_rate": 0.3, "max_iterations_without_improvement": 0}
        with_elite = self.genetic(aps, elitism=1, **common)
        without_elite = self.genetic(aps, elitism=0, **common)

        for band in with_elite["execution"]["bands"]:
            self.assertEqual(band["search"]["generation_best_worsened"], 0)
        # Sem elite e com mutacao alta, a melhor de uma geracao chega a piorar; a devolvida continua sendo a melhor.
        self.assertGreater(sum(band["search"]["generation_best_worsened"] for band in without_elite["execution"]["bands"]), 0)
        for band in without_elite["execution"]["bands"]:
            self.assertLessEqual(band["search"]["conflicts"], band["search"]["greedy_conflicts"])

    def test_preserves_locked_access_points(self):
        aps = self.dense_aps(30, seed=62)
        locked = {ap["id"]: ap for ap in aps[::4]}
        for ap in locked.values():
            ap["locked"] = True
            ap.update({"channel": "6", "bandwidth": "20 MHz"} if ap["frequency"] == "2.4 GHz" else {"channel": "44", "bandwidth": "20 MHz"})
        result = self.genetic(aps, seed=8, time_limit_seconds=0, generations=50, greedy_fraction=0, mutation_rate=0.5)

        for ap_id, ap in locked.items():
            node = self.get_node_by_id(result, ap_id)
            self.assertEqual(
                (node["proposed_channel"], node["proposed_bandwidth"], node["proposed_frequency"]),
                (ap["channel"], ap["bandwidth"], ap["frequency"]),
            )

    def test_rejects_inconsistent_parameters(self):
        aps = self.dense_aps(4, seed=63)
        cases = [
            ({"population_size": 10, "elitism": 10}, "elite"),
            ({"population_size": 10, "tournament_size": 11}, "torneio"),
            ({"time_limit_seconds": 0, "generations": 0, "max_iterations_without_improvement": 0}, "critérios de parada"),
            ({"crossover": "two_points"}, "crossover"),
        ]
        for parameters, expected in cases:
            with self.subTest(parameters=parameters):
                with self.assertRaises(urllib.error.HTTPError) as context:
                    self.genetic(aps, **parameters)
                with context.exception as error:
                    self.assertEqual(error.code, 400)
                    self.assertIn(expected, json.loads(error.read().decode("utf-8"))["error"])



class HybridGeneticTests(AnalysisServiceTestCase):
    """AG hibrido (#85): o AG com a busca local da base comum. A descida tem teste em C (tests/c)."""

    def hybrid(self, aps, timeout=60, **parameters):
        return self.post_json("/analyze-graph", {"aps": aps, "strategy": "hybrid_genetic", "parameters": parameters}, timeout=timeout)

    def dense_aps(self, count, seed):
        return AnalysisServiceMetaheuristicTests.dense_aps(self, count, seed)

    def test_is_declared_with_the_genetic_and_local_search_parameters(self):
        details = {item["name"]: item for item in self.get_json("/strategies")["strategy_details"]}
        hybrid = {parameter["name"]: parameter for parameter in details["hybrid_genetic"]["parameters"]}
        genetic = {parameter["name"] for parameter in details["genetic"]["parameters"]}

        self.assertEqual(details["hybrid_genetic"]["family"], "metaheuristic")
        self.assertTrue(genetic <= set(hybrid))
        self.assertTrue({"local_search_target", "local_search_count", "local_search_frequency", "local_search_depth"} <= set(hybrid))
        self.assertEqual([option["value"] for option in hybrid["local_search_target"]["options"]], ["children", "best"])

    def test_same_seed_gives_the_same_result(self):
        aps = self.dense_aps(60, seed=70)
        parameters = {"seed": 31, "time_limit_seconds": 0, "generations": 30, "population_size": 20}
        first = self.hybrid(aps, **parameters)
        second = self.hybrid(aps, **parameters)

        self.assertEqual(self.proposals(first), self.proposals(second))
        self.assertEqual(
            [band["search"]["local_search_moves"] for band in first["execution"]["bands"]],
            [band["search"]["local_search_moves"] for band in second["execution"]["bands"]],
        )

    def test_local_search_never_worsens_the_refined_individuals(self):
        aps = self.dense_aps(60, seed=71)
        for target in ("children", "best"):
            with self.subTest(target=target):
                result = self.hybrid(
                    aps, seed=2, time_limit_seconds=0, generations=20, population_size=20,
                    local_search_target=target, local_search_count=4, local_search_frequency=2, local_search_depth=100,
                )
                for band in result["execution"]["bands"]:
                    search = band["search"]
                    # Busca local nas geracoes 2, 4, ..., 20: 10 geracoes x 4 individuos.
                    self.assertEqual(search["local_search_applied"], 40)
                    self.assertEqual(search["local_search_worsened"], 0)
                    self.assertGreater(search["local_search_improved"], 0)
                    self.assertLessEqual(search["conflicts"], search["greedy_conflicts"])

    def test_local_search_time_counts_for_the_time_limit(self):
        aps = self.dense_aps(300, seed=72)
        started = time.time()
        result = self.hybrid(
            aps, timeout=60, seed=3, time_limit_seconds=1, generations=0, max_iterations_without_improvement=0,
            local_search_count=50, local_search_depth=10000000,
        )
        elapsed = time.time() - started

        self.assertEqual(result["execution"]["search"]["stop_reason"], "time_limit")
        self.assertLess(elapsed, len(result["execution"]["bands"]) * 1 + 5)


if __name__ == "__main__":
    unittest.main()
