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
from models import ScalabilityRun, db  # noqa: E402
from scalability import (  # noqa: E402
    ScalabilityRunner,
    instance_sizes,
    mark_interrupted_runs,
    strategy_broke,
    validate_parameters,
)
from version import read_version  # noqa: E402

OBJECTIVES = ["default", "energy_tiebreak", "energy_first"]

STRATEGIES = [
    {"name": "backtracking", "implemented": True, "exact": True},
    {"name": "greedy", "implemented": True, "exact": False},
    {"name": "local_search", "implemented": True, "exact": False, "family": "metaheuristic"},
    {"name": "genetic", "implemented": False, "exact": False, "family": "metaheuristic"},
]


class FakeAnalysisClient:
    """Backtracking comprova o otimo ate 30 APs; o guloso leva 10 ms por AP e fica 2 conflitos acima do otimo."""

    def __init__(self, cancel_at=None):
        self.calls = []
        self.objectives_used = set()
        self.cancel_at = cancel_at
        self.runner = None

    def strategies(self):
        return STRATEGIES

    def objectives(self):
        return OBJECTIVES

    def graph_metrics(self, aps):
        return {"edges": len(aps) - 1, "density": 0.1, "average_degree": 2.0}

    def analyze(self, aps, strategy, parameters, time_limit_seconds, objective="default"):
        self.calls.append((strategy, [ap["id"] for ap in aps]))
        self.objectives_used.add(objective)
        size = len(aps)
        if self.cancel_at == size and self.runner:
            self.runner.cancel(self.runner._active_run)
        if strategy == "backtracking":
            optimal = size <= 30
            search = {"optimal": optimal, "stop_reason": "completed" if optimal else "time_limit", "nodes_explored": size * 100}
            conflicts, duration_ms = 0, 5
        else:
            search = {"optimal": False, "stop_reason": "completed", "nodes_explored": size}
            conflicts, duration_ms = 2, size * 10
        return {
            "success": True,
            "execution": {
                "duration_ms": duration_ms,
                "search": search,
                "comparison": {
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
        body = {"max_nodes": 100, "step": 10, "min_degree": 2, "seed": 7, "time_limit_seconds": 0.5, **parameters}
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
        self.assertTrue(lines[0].endswith(",objective,cpu_seconds,processing_energy_j,processing_max_energy_j"))
        self.assertIn(",default,", lines[1])
        point = run["points"][0]
        self.assertAlmostEqual(point["processing_energy_j"], point["cpu_seconds"] * 3.25)
        self.assertTrue(lines[1].endswith(f",{point['cpu_seconds']},{point['processing_energy_j']},{point['processing_max_energy_j']}"))
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
            {"max_nodes": 1001}, {"step": 0}, {"time_limit_seconds": 0}, {"strategies": ["genetic"]}, {"strategies": ["local_search"]}, {"seed": -1},
            {"objective": "energia"},
        )
        for body in invalid:
            with self.subTest(body=body):
                response = self.client.post("/experiments/scalability", json=body)
                self.assertEqual(response.status_code, 400)
        self.runner._active_run = 999
        response = self.client.post("/experiments/scalability", json={})
        self.assertEqual(response.status_code, 409)

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
        self.assertEqual(parameters["strategies"], ["backtracking", "greedy"])
        self.assertIsInstance(parameters["seed"], int)


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
