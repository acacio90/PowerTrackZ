import math
import random
import secrets
from datetime import datetime


MAX_NODE_COUNT = 1000
MAX_SEED = 2**32 - 1


FREQUENCY_PROFILES = [
    {
        "frequency": "2.4 GHz",
        "channel": "1",
        "bandwidth": "20 MHz",
    },
    {
        "frequency": "5 GHz",
        "channel": "36",
        "bandwidth": "80 MHz",
    },
]


def get_signal_radius(frequency):
    if not frequency:
        return 10

    normalized = str(frequency).replace(",", ".")
    if normalized.startswith("2.4"):
        return 20
    if normalized.startswith("5"):
        return 15
    if normalized.startswith("6"):
        return 12
    return 10


def meters_to_latitude_degrees(meters):
    return meters / 111320


def meters_to_longitude_degrees(meters, latitude):
    latitude_radians = latitude * (math.pi / 180)
    meters_per_degree = 111320 * math.cos(latitude_radians)
    return 0 if meters_per_degree == 0 else meters / meters_per_degree


def build_generated_access_points(node_count, rnd):
    aps = []

    for index in range(node_count):
        profile = rnd.choice(FREQUENCY_PROFILES)
        frequency = profile["frequency"]
        bandwidth = profile["bandwidth"]
        channel = profile["channel"]

        aps.append({
            "id": f"generated-ap-{index + 1:03d}",
            "name": f"AP Gerado {index + 1}",
            "channel": channel,
            "frequency": frequency,
            "bandwidth": bandwidth,
            "radius": get_signal_radius(frequency),
            "latitude": None,
            "longitude": None,
        })

    return aps


# Ligacoes usadas so para posicionar os APs: cada AP recebe ao menos min_degree vizinhos, perto dos quais e
# colocado. A analise monta o proprio grafo pela sobreposicao das coberturas, em geral bem mais denso.
def build_generated_links(node_count, min_degree, rnd):
    links = []
    adjacency = [set() for _ in range(node_count)]
    minimum_connections = max(1, min(min_degree, node_count - 1))

    for index in range(node_count - 1):
        adjacency[index].add(index + 1)
        adjacency[index + 1].add(index)

    for index in range(node_count):
        while len(adjacency[index]) < minimum_connections:
            candidate = rnd.randrange(node_count)
            if candidate == index or candidate in adjacency[index]:
                continue

            adjacency[index].add(candidate)
            adjacency[candidate].add(index)

    for source_index, neighbors in enumerate(adjacency):
        for target_index in neighbors:
            if source_index < target_index:
                links.append({
                    "source": f"generated-ap-{source_index + 1:03d}",
                    "target": f"generated-ap-{target_index + 1:03d}",
                })

    return links


def assign_coordinates_for_topology(aps, links, rnd):
    if not aps:
        return aps

    by_id = {ap["id"]: ap for ap in aps}
    adjacency = {ap["id"]: set() for ap in aps}

    for link in links:
        adjacency[link["source"]].add(link["target"])
        adjacency[link["target"]].add(link["source"])

    origin_lat = -23.55052
    origin_lng = -46.633308
    visited = set()
    queue = []
    root = aps[0]

    root["latitude"] = origin_lat
    root["longitude"] = origin_lng
    visited.add(root["id"])
    queue.append(root["id"])

    while queue:
        current_id = queue.pop(0)
        current = by_id[current_id]
        neighbors = list(adjacency[current_id])
        # A ordem dos vizinhos no conjunto nao e estavel entre execucoes; ordenar antes de embaralhar
        # torna o resultado dependente so da semente.
        neighbors.sort()
        rnd.shuffle(neighbors)

        for neighbor_id in neighbors:
            if neighbor_id in visited:
                continue

            neighbor = by_id[neighbor_id]
            desired_distance = max(
                6,
                min(
                    34,
                    (current["radius"] + neighbor["radius"]) * rnd.uniform(0.42, 0.95),
                ),
            )
            angle = rnd.uniform(0, math.pi * 2)
            local_jitter = rnd.uniform(-5.5, 5.5)
            lat_offset = meters_to_latitude_degrees((desired_distance + local_jitter) * math.cos(angle))
            lng_offset = meters_to_longitude_degrees((desired_distance - local_jitter) * math.sin(angle), current["latitude"])

            neighbor_lat = current["latitude"] + lat_offset
            neighbor_lng = current["longitude"] + lng_offset

            # Introduz deslocamentos irregulares para evitar topologia "arrumada".
            neighbor_lat += meters_to_latitude_degrees(rnd.uniform(-3.5, 3.5))
            neighbor_lng += meters_to_longitude_degrees(rnd.uniform(-3.5, 3.5), current["latitude"])

            neighbor["latitude"] = round(neighbor_lat, 6)
            neighbor["longitude"] = round(neighbor_lng, 6)
            visited.add(neighbor_id)
            queue.append(neighbor_id)

    for ap in aps:
        if ap["latitude"] is not None and ap["longitude"] is not None:
            continue

        fallback_distance = rnd.uniform(8, 42)
        fallback_angle = rnd.uniform(0, math.pi * 2)
        ap["latitude"] = round(origin_lat + meters_to_latitude_degrees(fallback_distance * math.cos(fallback_angle)), 6)
        ap["longitude"] = round(origin_lng + meters_to_longitude_degrees(fallback_distance * math.sin(fallback_angle), origin_lat), 6)

    return [
        {key: value for key, value in ap.items() if key != "radius"}
        for ap in aps
    ]


def resolve_seed(seed):
    """Valida a semente informada ou sorteia uma, para que toda topologia possa ser recriada."""
    if seed is None or seed == "":
        return secrets.randbelow(MAX_SEED + 1)
    if isinstance(seed, bool):
        raise ValueError("seed deve ser um inteiro entre 0 e 4294967295")
    try:
        value = int(seed)
    except (TypeError, ValueError):
        raise ValueError("seed deve ser um inteiro entre 0 e 4294967295") from None
    if isinstance(seed, float) and value != seed:
        raise ValueError("seed deve ser um inteiro entre 0 e 4294967295")
    if value < 0 or value > MAX_SEED:
        raise ValueError("seed deve ser um inteiro entre 0 e 4294967295")
    return value


def generate_access_point_infrastructure(node_count, min_degree, seed=None):
    """Gera APs posicionados em uma topologia. A mesma semente, com os mesmos parametros e a mesma versao do
    gerador, produz a mesma topologia; sem semente, uma e sorteada e devolvida em metadata.seed."""
    if node_count < 2:
        raise ValueError("node_count deve ser maior ou igual a 2")
    if node_count > MAX_NODE_COUNT:
        raise ValueError(f"node_count deve ser menor ou igual a {MAX_NODE_COUNT}")
    if min_degree < 1:
        raise ValueError("min_degree deve ser maior ou igual a 1")
    if min_degree >= node_count:
        raise ValueError("min_degree deve ser menor que node_count")

    resolved_seed = resolve_seed(seed)
    # Gerador proprio: sorteios de outras partes do servico nao alteram a sequencia desta topologia.
    rnd = random.Random(resolved_seed)
    aps = build_generated_access_points(node_count, rnd)
    links = build_generated_links(node_count, min_degree, rnd)
    positioned_aps = assign_coordinates_for_topology(aps, links, rnd)

    return {
        "metadata": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "node_count": node_count,
            "min_degree": min_degree,
            # Nome anterior do parametro, mantido para quem le arquivos gerados antes.
            "clique_factor": min_degree,
            "seed": resolved_seed,
        },
        "aps": positioned_aps,
        "links": links,
    }
