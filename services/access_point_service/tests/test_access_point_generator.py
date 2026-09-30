import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1] / "app"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from access_point_generator import MAX_NODE_COUNT, generate_access_point_infrastructure  # noqa: E402


def generate_in_subprocess(node_count, clique_factor, seed, hash_seed):
    # Processo separado com outro PYTHONHASHSEED: a ordem de iteracao de conjuntos de textos muda entre processos,
    # e a topologia nao pode depender dela.
    script = (
        "import json, sys; sys.path.insert(0, sys.argv[1]);"
        "from access_point_generator import generate_access_point_infrastructure as g;"
        "p = g(int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]));"
        "print(json.dumps({'aps': p['aps'], 'links': p['links']}))"
    )
    environment = {**os.environ, "PYTHONHASHSEED": str(hash_seed)}
    output = subprocess.run(
        [sys.executable, "-c", script, str(APP_DIR), str(node_count), str(clique_factor), str(seed)],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    ).stdout
    return json.loads(output)


class AccessPointGeneratorTests(unittest.TestCase):
    def topology(self, payload):
        return {"aps": payload["aps"], "links": payload["links"]}

    def test_same_seed_generates_the_same_topology(self):
        first = generate_access_point_infrastructure(40, 3, seed=123)
        second = generate_access_point_infrastructure(40, 3, seed=123)

        self.assertEqual(self.topology(first), self.topology(second))
        self.assertEqual(first["metadata"]["seed"], 123)

    def test_same_seed_generates_the_same_topology_in_other_processes(self):
        results = [generate_in_subprocess(30, 3, 7, hash_seed) for hash_seed in (1, 2, 3)]

        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0], results[2])
        self.assertEqual(results[0], self.topology(generate_access_point_infrastructure(30, 3, seed=7)))

    def test_different_seeds_generate_different_topologies(self):
        first = generate_access_point_infrastructure(40, 3, seed=1)
        second = generate_access_point_infrastructure(40, 3, seed=2)

        self.assertNotEqual(self.topology(first), self.topology(second))

    def test_without_seed_a_seed_is_drawn_and_reproduces_the_topology(self):
        generated = generate_access_point_infrastructure(25, 2)
        seed = generated["metadata"]["seed"]

        self.assertIsInstance(seed, int)
        self.assertEqual(
            self.topology(generate_access_point_infrastructure(25, 2, seed=seed)),
            self.topology(generated),
        )

    def test_accepts_seed_as_text_and_rejects_invalid_seeds(self):
        self.assertEqual(generate_access_point_infrastructure(5, 1, seed="42")["metadata"]["seed"], 42)
        for seed in (-1, 2**32, "abc", 1.5, True):
            with self.subTest(seed=seed):
                with self.assertRaises(ValueError):
                    generate_access_point_infrastructure(5, 1, seed=seed)

    def test_generates_up_to_the_maximum_number_of_access_points(self):
        generated = generate_access_point_infrastructure(MAX_NODE_COUNT, 3, seed=5)
        ids = {ap["id"] for ap in generated["aps"]}

        self.assertEqual(MAX_NODE_COUNT, 1000)
        self.assertEqual(len(ids), MAX_NODE_COUNT)
        self.assertTrue(all(ap["latitude"] is not None and ap["longitude"] is not None for ap in generated["aps"]))
        with self.assertRaises(ValueError):
            generate_access_point_infrastructure(MAX_NODE_COUNT + 1, 3, seed=5)


if __name__ == "__main__":
    unittest.main()
