import json
import os
import sys
import tempfile
import unittest
import zlib
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1] / "app"
TEST_DB_PATH = Path(__file__).resolve().with_name("test_access_point.sqlite")

os.environ.setdefault("ACCESS_POINT_DATABASE_URI", f"sqlite:///{TEST_DB_PATH.as_posix()}")

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import main  # noqa: E402
from models import AccessPoint, ScalabilityRun, db  # noqa: E402
from scalability import (  # noqa: E402
    ScalabilityRunner,
    instance_sizes,
    mark_interrupted_runs,
    repetition_seed,
    stochastic_broke,
    strategy_broke,
    summarize_points,
    validate_parameters,
)
from version import read_version  # noqa: E402

OBJECTIVES = ["default", "energy_tiebreak", "energy_first"]

STRATEGIES = [
    {"name": "backtracking", "implemented": True, "exact": True},
    {"name": "greedy", "implemented": True, "exact": False},
    {"name": "local_search", "implemented": True, "exact": False, "family": "metaheuristic",
     "parameters": [{"name": "seed"}, {"name": "time_limit_seconds"}, {"name": "max_iterations"}]},
    {"name": "genetic", "implemented": False, "exact": False, "family": "metaheuristic"},
]


class FakeAnalysisClient:
    """Backtracking comprova o otimo ate 30 APs; o guloso leva 10 ms por AP e fica 2 conflitos acima do otimo.
    A busca local (estocastica) da conflitos que dependem da semente e para pelo limite de tempo a partir de
    time_limit_from APs nas sementes em time_limited_seeds (todas, se for None)."""

    def __init__(self, cancel_at=None, time_limit_from=50, time_limited_seeds=None):
        self.calls = []
        self.requests = []
        self.objectives_used = set()
        self.cancel_at = cancel_at
        self.runner = None
        self.time_limit_from = time_limit_from
        self.time_limited_seeds = time_limited_seeds

    def strategies(self):
        return STRATEGIES

    def objectives(self):
        return OBJECTIVES

    def graph_metrics(self, aps):
        return {"edges": len(aps) - 1, "density": 0.1, "average_degree": 2.0}

    def analyze(self, aps, strategy, parameters, time_limit_seconds, objective="default", channels=None):
        self.calls.append((strategy, [ap["id"] for ap in aps]))
        self.requests.append({"strategy": strategy, "size": len(aps), "parameters": dict(parameters), "channels": channels})
        self.objectives_used.add(objective)
        size = len(aps)
        if self.cancel_at == size and self.runner:
            self.runner.cancel(self.runner._active_run)
        if strategy == "backtracking":
            optimal = size <= 30
            search = {"optimal": optimal, "stop_reason": "completed" if optimal else "time_limit", "nodes_explored": size * 100}
            conflicts, duration_ms = 0, 5
        elif strategy == "local_search":
            seed = parameters["seed"]
            limited = size >= self.time_limit_from and (self.time_limited_seeds is None or seed in self.time_limited_seeds)
            search = {"optimal": False, "stop_reason": "time_limit" if limited else "no_improvement", "nodes_explored": size}
            conflicts, duration_ms = 1 + seed % 4, 20
        else:
            search = {"optimal": False, "stop_reason": "completed", "nodes_explored": size}
            conflicts, duration_ms = 2, size * 10
        return {
            "success": True,
            # Proposta: todos os APs no canal 6, para a comparacao guardar a configuracao da melhor repeticao.
            "graph_data": {"nodes": [{"id": ap["id"], "proposed_channel": "6", "proposed_bandwidth": "20 MHz",
                                      "proposed_frequency": ap.get("frequency")} for ap in aps]},
            "execution": {
                "duration_ms": duration_ms,
                "search": search,
                "comparison": {
                    "changed_nodes": size // 2,
                    "conflicts_before": 5, "conflicts_after": conflicts,
                    "interference_before": 500.0, "interference_after": conflicts * 50.0,
                    "power_after_w": size * 12.0,
                },
                "processing": {"cpu_seconds": duration_ms / 1000.0, "energy_j": duration_ms / 1000.0 * 3.25,
                               "max_energy_j": duration_ms / 1000.0 * 10.95},
            },
        }


class ScalabilityTests(unittest.TestCase):
    def setUp(self):
        main.app.config["TESTING"] = True
        self.client = main.app.test_client()
        with main.app.app_context():
            db.drop_all()
            db.create_all()
        self.fake = FakeAnalysisClient()
        self.runner = ScalabilityRunner(main.app, client=self.fake, background=False)
        self.fake.runner = self.runner
        main.scalability_runner = self.runner

    def tearDown(self):
        with main.app.app_context():
            db.session.remove()
            db.drop_all()
            # Fecha as conexoes do pool; no Windows o arquivo aberto nao pode ser removido.
            db.engine.dispose()

        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()

    def start(self, **parameters):
        body = {"max_nodes": 100, "step": 10, "min_degree": 2, "seed": 7, "time_limit_seconds": 0.5,
                "strategies": ["backtracking", "greedy"], **parameters}
        response = self.client.post("/experiments/scalability", json=body)
        self.assertEqual(response.status_code, 202, response.get_json())
        run_id = response.get_json()["run"]["id"]
        return self.client.get(f"/experiments/scalability/{run_id}").get_json()["run"]

    def test_instances_are_nested_prefixes_of_one_topology(self):
        self.start()
        instances = [ids for strategy, ids in self.fake.calls if strategy == "greedy"]

        self.assertEqual([len(ids) for ids in instances], [10, 20, 30, 40, 50, 60])
        for smaller, larger in zip(instances, instances[1:]):
            self.assertEqual(larger[:len(smaller)], smaller)

    def test_break_points_follow_the_criterion_of_each_kind_of_method(self):
        run = self.start()

        # Exato: 40 APs e o primeiro tamanho sem otimo comprovado. Guloso: 60 APs levam 0,6 s, acima do limite de 0,5 s.
        self.assertEqual(run["breaks"], {"backtracking": 40, "greedy": 60})
        self.assertEqual(run["status"], "completed")
        backtracking_sizes = [len(ids) for strategy, ids in self.fake.calls if strategy == "backtracking"]
        self.assertEqual(backtracking_sizes, [10, 20, 30, 40])
        self.assertEqual(max(point["nodes"] for point in run["points"]), 60)

    def test_records_the_distance_to_the_optimum_while_it_is_proven(self):
        run = self.start()
        greedy = {point["nodes"]: point for point in run["points"] if point["strategy"] == "greedy"}

        self.assertEqual(greedy[30]["gap_conflicts"], 2)
        self.assertEqual(greedy[30]["gap_interference"], 100.0)
        self.assertIsNone(greedy[40]["gap_conflicts"])

    def test_saves_version_parameters_and_points(self):
        run = self.start()

        self.assertEqual(set(run["version"]), {"commit", "branch", "tag"})
        self.assertEqual(run["parameters"]["seed"], 7)
        self.assertEqual(run["parameters"]["strategies"], ["backtracking", "greedy"])
        self.assertEqual(run["parameters"]["objective"], "default")
        self.assertEqual([strategy["exact"] for strategy in run["strategies"]], [True, False])
        self.assertEqual(len(run["points"]), 10)
        self.assertEqual(run["progress"], 1.0)
        listed = self.client.get("/experiments/scalability").get_json()["runs"]
        self.assertEqual(listed[0]["id"], run["id"])
        self.assertNotIn("points", listed[0])

    def test_exports_csv_and_json(self):
        run = self.start()
        csv_response = self.client.get(f"/experiments/scalability/{run['id']}/export?format=csv")
        json_response = self.client.get(f"/experiments/scalability/{run['id']}/export?format=json")

        lines = csv_response.get_data(as_text=True).strip().splitlines()
        self.assertEqual(csv_response.mimetype, "text/csv")
        self.assertIn("attachment", csv_response.headers["Content-Disposition"])
        self.assertTrue(lines[0].startswith("run_id,commit,tag,seed,min_degree,time_limit_seconds,thread_count,nodes,"))
        self.assertTrue(lines[0].endswith(",objective,cpu_seconds,processing_energy_j,processing_max_energy_j,repetition,seed,changed_nodes"))
        self.assertIn(",default,", lines[1])
        point = run["points"][0]
        self.assertAlmostEqual(point["processing_energy_j"], point["cpu_seconds"] * 3.25)
        self.assertTrue(lines[1].endswith(f",{point['cpu_seconds']},{point['processing_energy_j']},{point['processing_max_energy_j']},1,,{point['changed_nodes']}"))
        self.assertEqual(len(lines), 1 + len(run["points"]))
        self.assertEqual(json.loads(json_response.get_data())["id"], run["id"])

    def test_uses_and_records_the_chosen_objective(self):
        run = self.start(objective="energy_first")

        self.assertEqual(run["parameters"]["objective"], "energy_first")
        self.assertEqual(self.fake.objectives_used, {"energy_first"})
        csv_text = self.client.get(f"/experiments/scalability/{run['id']}/export?format=csv").get_data(as_text=True)
        header, first = (line.split(",") for line in csv_text.splitlines()[:2])
        self.assertEqual(first[header.index("objective")], "energy_first")

    def test_cancelling_stops_before_the_next_size(self):
        self.fake.cancel_at = 20
        run = self.start()

        self.assertEqual(run["status"], "cancelled")
        self.assertEqual(max(point["nodes"] for point in run["points"]), 20)

    def test_rejects_invalid_parameters_and_concurrent_runs(self):
        invalid = (
            {"max_nodes": 1001}, {"step": 0}, {"time_limit_seconds": 0}, {"strategies": ["genetic"]}, {"seed": -1},
            {"objective": "energia"},
        )
        for body in invalid:
            with self.subTest(body=body):
                response = self.client.post("/experiments/scalability", json=body)
                self.assertEqual(response.status_code, 400)
        self.runner._active_run = 999
        response = self.client.post("/experiments/scalability", json={})
        self.assertEqual(response.status_code, 409)

    def test_stochastic_strategies_repeat_with_the_same_seeds_in_every_size(self):
        run = self.start(strategies=["greedy", "local_search"], repetitions=3, max_nodes=30)
        seeds = [repetition_seed(7, index) for index in range(3)]
        local = [request for request in self.fake.requests if request["strategy"] == "local_search"]
        greedy = [request for request in self.fake.requests if request["strategy"] == "greedy"]

        self.assertEqual(len(greedy), 3)
        self.assertEqual([request["parameters"]["seed"] for request in local], seeds * 3)
        points = [point for point in run["points"] if point["strategy"] == "local_search"]
        self.assertEqual([(point["nodes"], point["repetition"], point["seed"]) for point in points[:3]],
                         [(10, 1, seeds[0]), (10, 2, seeds[1]), (10, 3, seeds[2])])
        summary = next(item for item in run["summaries"] if item["strategy"] == "local_search" and item["nodes"] == 10)
        conflicts = [1 + seed % 4 for seed in seeds]
        self.assertEqual(summary["repetitions"], 3)
        self.assertEqual(summary["conflicts"]["min"], min(conflicts))
        self.assertEqual(summary["conflicts"]["max"], max(conflicts))
        self.assertAlmostEqual(summary["conflicts"]["mean"], sum(conflicts) / 3)
        self.assertEqual(run["strategies"][1]["stochastic"], True)
        self.assertEqual(run["progress"], 1.0)

    def test_stochastic_strategy_breaks_when_most_repetitions_stop_at_the_time_limit(self):
        run = self.start(strategies=["local_search"], repetitions=3)
        self.assertEqual(run["breaks"], {"local_search": 50})
        self.assertEqual(max(point["nodes"] for point in run["points"]), 50)

    def test_stochastic_strategy_does_not_break_with_a_minority_of_time_limit_stops(self):
        self.fake.time_limited_seeds = {repetition_seed(7, 0)}
        run = self.start(strategies=["local_search"], repetitions=3)
        self.assertEqual(run["breaks"], {})
        self.assertEqual(max(point["nodes"] for point in run["points"]), 100)

    def test_forwards_the_strategy_parameters_and_the_channels(self):
        channels = {"2.4 GHz": {"20 MHz": ["1", "6", "11"]}}
        self.start(
            strategies=["greedy", "local_search"], repetitions=2, max_nodes=10, channels=channels,
            strategy_parameters={"local_search": {"max_iterations": 500, "seed": 9, "time_limit_seconds": 99}},
        )
        local = [request for request in self.fake.requests if request["strategy"] == "local_search"]
        greedy = next(request for request in self.fake.requests if request["strategy"] == "greedy")

        # A semente e o limite de tempo sao do teste; os demais parametros sao os da estrategia.
        self.assertEqual(local[0]["parameters"]["max_iterations"], 500)
        self.assertEqual(local[0]["parameters"]["time_limit_seconds"], 0.5)
        self.assertEqual([request["parameters"]["seed"] for request in local], [repetition_seed(7, 0), repetition_seed(7, 1)])
        self.assertNotIn("max_iterations", greedy["parameters"])
        self.assertTrue(all(request["channels"] == channels for request in self.fake.requests))

    def test_rejects_invalid_repetitions_parameters_and_channels(self):
        invalid = (
            {"repetitions": 0}, {"repetitions": 101}, {"channels": "todos"},
            {"strategy_parameters": {"tabu_search": {"tabu_tenure": 5}}},
            {"strategy_parameters": {"greedy": {"x": [1]}}},
        )
        for body in invalid:
            with self.subTest(body=body):
                response = self.client.post("/experiments/scalability", json={"strategies": ["greedy"], **body})
                self.assertEqual(response.status_code, 400)

    def register_aps(self, count, without_coordinates=1):
        with main.app.app_context():
            for index in range(count):
                db.session.add(AccessPoint(id=f"ap-{index:02d}", name=f"AP {index}", channel="1", frequency="2.4 GHz",
                                           bandwidth="20 MHz", latitude=-23.55 + index * 1e-4, longitude=-46.63))
            for index in range(without_coordinates):
                db.session.add(AccessPoint(id=f"sem-{index}", name="Sem coordenadas", channel="1", frequency="2.4 GHz", bandwidth="20 MHz"))
            db.session.commit()

    def test_comparison_runs_every_strategy_on_the_registered_aps_with_the_same_conditions(self):
        self.register_aps(12)
        channels = {"2.4 GHz": {"20 MHz": ["1", "6", "11"]}}
        run = self.start(mode="comparison", strategies=["backtracking", "greedy", "local_search"], repetitions=3,
                         objective="energy_tiebreak", channels=channels)

        self.assertEqual(run["mode"], "comparison")
        self.assertEqual(run["instance_size"], 12)
        self.assertNotIn("instance", run["parameters"])
        self.assertEqual(run["breaks"], {})
        self.assertEqual(run["status"], "completed")
        expected_ids = [f"ap-{index:02d}" for index in range(12)]
        self.assertTrue(all(ids == expected_ids for _, ids in self.fake.calls))
        self.assertEqual(self.fake.objectives_used, {"energy_tiebreak"})
        self.assertTrue(all(request["channels"] == channels for request in self.fake.requests))
        local = [request["parameters"]["seed"] for request in self.fake.requests if request["strategy"] == "local_search"]
        self.assertEqual(local, [repetition_seed(7, index) for index in range(3)])
        self.assertEqual([point["strategy"] for point in run["points"]], ["backtracking", "greedy"] + ["local_search"] * 3)
        self.assertTrue(all(point["changed_nodes"] == 6 for point in run["points"]))
        self.assertEqual(set(run["proposals"]), {"backtracking", "greedy", "local_search"})

    def test_comparison_keeps_the_proposal_of_the_best_repetition(self):
        self.register_aps(8)
        run = self.start(mode="comparison", strategies=["greedy", "local_search"], repetitions=4)
        seeds = [repetition_seed(7, index) for index in range(4)]
        best = min(range(4), key=lambda index: (1 + seeds[index] % 4, (1 + seeds[index] % 4) * 50.0))

        response = self.client.get(f"/experiments/scalability/{run['id']}/proposal?strategy=local_search")
        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual((body["repetition"], body["seed"]), (best + 1, seeds[best]))
        self.assertEqual(len(body["instance"]), 8)
        self.assertEqual({item["channel"] for item in body["proposal"]}, {"6"})
        self.assertEqual(body["execution"]["comparison"]["conflicts_after"], 1 + seeds[best] % 4)
        self.assertEqual(self.client.get(f"/experiments/scalability/{run['id']}/proposal?strategy=tabu_search").status_code, 404)

    def test_scalability_runs_have_no_stored_proposal(self):
        run = self.start(max_nodes=20)
        self.assertEqual(run["mode"], "scalability")
        self.assertEqual(self.client.get(f"/experiments/scalability/{run['id']}/proposal?strategy=greedy").status_code, 404)

    def test_comparison_needs_registered_aps_with_coordinates(self):
        self.register_aps(0, without_coordinates=2)
        response = self.client.post("/experiments/scalability", json={"mode": "comparison", "strategies": ["greedy"]})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Nenhum AP", response.get_json()["error"])
        self.assertEqual(self.client.post("/experiments/scalability", json={"mode": "outro"}).status_code, 400)

    def test_marks_runs_left_running_as_interrupted(self):
        with main.app.app_context():
            db.session.add(ScalabilityRun(status="running"))
            db.session.commit()
            mark_interrupted_runs()
            self.assertEqual(ScalabilityRun.query.one().status, "interrupted")

    def test_helpers(self):
        self.assertEqual(instance_sizes(25, 10), [10, 20, 25])
        self.assertEqual(instance_sizes(5, 1), [2, 3, 4, 5])
        self.assertTrue(strategy_broke(True, "time_limit", 1.0, 10))
        self.assertFalse(strategy_broke(True, "completed", 99.0, 10))
        self.assertTrue(strategy_broke(False, "completed", 10.5, 10))
        self.assertFalse(strategy_broke(False, "completed", 9.9, 10))
        parameters = validate_parameters({}, STRATEGIES)
        self.assertEqual(parameters["strategies"], ["backtracking", "greedy", "local_search"])
        self.assertIsInstance(parameters["seed"], int)
        self.assertEqual((parameters["repetitions"], parameters["channels"], parameters["strategy_parameters"]), (1, "padrao", {}))

    def test_repetition_seeds_are_derived_from_the_test_seed(self):
        seeds = [repetition_seed(7, index) for index in range(5)]
        self.assertEqual(seeds, [repetition_seed(7, index) for index in range(5)])
        self.assertEqual(len(set(seeds)), 5)
        self.assertNotEqual(seeds, [repetition_seed(8, index) for index in range(5)])
        self.assertTrue(all(0 <= seed <= 2**32 - 1 for seed in seeds))

    def test_stochastic_break_needs_a_majority_of_time_limit_stops(self):
        self.assertTrue(stochastic_broke(["time_limit", "time_limit", "no_improvement"]))
        self.assertFalse(stochastic_broke(["time_limit", "no_improvement", "no_improvement"]))
        self.assertFalse(stochastic_broke(["time_limit", "iteration_limit"]))
        self.assertTrue(stochastic_broke(["time_limit"]))

    def test_summaries_report_mean_spread_best_and_worst(self):
        points = [{"nodes": 10, "strategy": "local_search", "conflicts": value, "duration_seconds": 1.0, "broke": False}
                  for value in (2, 4, 6)]
        summary = summarize_points(points)[0]
        self.assertEqual(summary["repetitions"], 3)
        self.assertEqual(summary["conflicts"], {"mean": 4, "std": 2.0, "min": 2, "max": 6})
        self.assertEqual(summary["duration_seconds"]["std"], 0.0)
        self.assertIsNone(summary["power_w"]["mean"])


class VersionTests(unittest.TestCase):
    def test_reads_commit_branch_and_annotated_tag(self):
        commit = "a" * 40
        tag_object = "b" * 40
        with tempfile.TemporaryDirectory() as directory:
            git_dir = Path(directory)
            (git_dir / "refs" / "heads").mkdir(parents=True)
            (git_dir / "refs" / "tags").mkdir(parents=True)
            (git_dir / "HEAD").write_text("ref: refs/heads/develop\n")
            (git_dir / "refs" / "heads" / "develop").write_text(commit + "\n")
            (git_dir / "refs" / "tags" / "v9.9.9").write_text(tag_object + "\n")
            body = f"object {commit}\ntype commit\ntag v9.9.9\n\nversao".encode()
            (git_dir / "objects" / tag_object[:2]).mkdir(parents=True)
            (git_dir / "objects" / tag_object[:2] / tag_object[2:]).write_bytes(
                zlib.compress(b"tag %d\0" % len(body) + body)
            )

            self.assertEqual(read_version(git_dir), {"commit": commit, "branch": "develop", "tag": "v9.9.9"})

    def test_reads_packed_refs_and_detached_head(self):
        commit = "c" * 40
        with tempfile.TemporaryDirectory() as directory:
            git_dir = Path(directory)
            (git_dir / "HEAD").write_text(commit + "\n")
            (git_dir / "packed-refs").write_text(f"# pack-refs\n{'d' * 40} refs/tags/v1.0.0\n^{commit}\n")

            self.assertEqual(read_version(git_dir), {"commit": commit, "branch": None, "tag": "v1.0.0"})

    def test_without_repository_fields_are_null(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(read_version(directory), {"commit": None, "branch": None, "tag": None})


if __name__ == "__main__":
    unittest.main()
