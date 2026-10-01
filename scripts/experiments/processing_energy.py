"""Protótipo da medição de energia do processamento das estratégias (#87).

Mede o tempo de CPU que o contêiner do analysis_service gasta em cada análise, pela contabilidade do cgroup
(cpu.stat, usage_usec), e o converte em energia por uma potência por núcleo: E = tempo de CPU x potência por núcleo.
O RAPL não está acessível no Docker com WSL2 (ver docs/energy), então este é o método comum a todas as
estratégias. As análises são feitas uma por vez, com o serviço ocioso, e o custo da própria leitura do cgroup
(o "docker exec" roda dentro do contêiner) é medido e descontado.

Uso, com os serviços do docker compose no ar:
    python scripts/experiments/processing_energy.py --nodes 100 --repetitions 3
"""
import argparse
import json
import statistics
import subprocess
import time
import urllib.request

# Intel Core i7-14700: potência base (PBP) de 65 W e potência turbo máxima (MTP) de 219 W, em 20 núcleos.
DEFAULT_CORE_POWER_W = 65 / 20
DEFAULT_MAX_CORE_POWER_W = 219 / 20

STRATEGIES = [
    ("greedy", {}),
    ("backtracking", {"thread_count": 1, "time_limit_seconds": 10}),
    ("backtracking", {"thread_count": 4, "time_limit_seconds": 10}),
    ("local_search", {"seed": 1, "time_limit_seconds": 0, "max_iterations": 200000}),
    ("simulated_annealing", {"seed": 1, "time_limit_seconds": 0, "max_iterations": 200000}),
]


def post(url, payload, timeout=600):
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def cpu_usage_seconds(container):
    """Tempo de CPU acumulado pelo cgroup do contêiner (cgroup v2), em segundos."""
    output = subprocess.run(
        ["docker", "exec", container, "cat", "/sys/fs/cgroup/cpu.stat"],
        check=True, capture_output=True, text=True,
    ).stdout
    usage = next(line for line in output.splitlines() if line.startswith("usage_usec"))
    return int(usage.split()[1]) / 1_000_000


def reading_overhead(container, samples=10):
    """CPU gasta pela própria leitura (o "cat" do docker exec roda no cgroup do contêiner)."""
    deltas = []
    for _ in range(samples):
        before = cpu_usage_seconds(container)
        after = cpu_usage_seconds(container)
        deltas.append(after - before)
    return statistics.median(deltas)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--frontend", default="http://localhost:3000")
    parser.add_argument("--analysis", default="http://localhost:5002")
    parser.add_argument("--container", default="powertrackz-analysis_service-1")
    parser.add_argument("--nodes", type=int, default=100)
    parser.add_argument("--min-degree", type=int, default=3)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--core-power", type=float, default=DEFAULT_CORE_POWER_W, help="W por núcleo (padrão: PBP/núcleos)")
    parser.add_argument("--max-core-power", type=float, default=DEFAULT_MAX_CORE_POWER_W, help="W por núcleo no turbo máximo")
    args = parser.parse_args()

    generated = post(f"{args.frontend}/api/access_points/generate",
                     {"node_count": args.nodes, "min_degree": args.min_degree, "seed": args.seed})["payload"]["aps"]
    aps = [{"id": ap["id"], "label": ap["name"], "x": ap["latitude"], "y": ap["longitude"], "channel": ap["channel"],
            "bandwidth": ap["bandwidth"], "frequency": ap["frequency"]} for ap in generated]
    overhead = reading_overhead(args.container)
    print(f"Instância: {args.nodes} APs, semente {args.seed}, grau mínimo {args.min_degree}. "
          f"Custo da leitura do cgroup: {overhead * 1000:.1f} ms de CPU (descontado).")
    print(f"Potência por núcleo: {args.core_power:.2f} W (base) a {args.max_core_power:.2f} W (turbo máximo).\n")
    header = f"{'estratégia':<32}{'tempo (s)':>11}{'CPU (s)':>11}{'núcleos':>9}{'energia (J)':>22}{'conflitos':>11}"
    print(header)
    print("-" * len(header))
    for strategy, parameters in STRATEGIES:
        walls, cpus, conflicts = [], [], None
        for _ in range(args.repetitions):
            before = cpu_usage_seconds(args.container)
            started = time.perf_counter()
            result = post(f"{args.analysis}/analyze-graph", {"aps": aps, "strategy": strategy, "parameters": parameters})
            wall = time.perf_counter() - started
            cpu = cpu_usage_seconds(args.container) - before - overhead
            walls.append(wall)
            cpus.append(max(cpu, 0.0))
            conflicts = result["execution"]["comparison"]["conflicts_after"]
        wall, cpu = statistics.mean(walls), statistics.mean(cpus)
        spread = statistics.stdev(cpus) if len(cpus) > 1 else 0.0
        label = strategy + (f" ({parameters['thread_count']} threads)" if "thread_count" in parameters else "")
        energy = f"{cpu * args.core_power:.2f} a {cpu * args.max_core_power:.2f}"
        print(f"{label:<32}{wall:>11.3f}{cpu:>8.3f}±{spread:<.3f}{cpu / wall if wall else 0:>7.2f}{energy:>22}{conflicts:>11}")


if __name__ == "__main__":
    main()
