import math
import random
from datetime import datetime


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


def build_generated_access_points(node_count):
    aps = []

    for index in range(node_count):
        profile = random.choice(FREQUENCY_PROFILES)
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


def build_generated_links(node_count, clique_factor):
    links = []
    adjacency = [set() for _ in range(node_count)]
    minimum_connections = max(1, min(clique_factor, node_count - 1))

    for index in range(node_count - 1):
        adjacency[index].add(index + 1)
        adjacency[index + 1].add(index)

    for index in range(node_count):
        while len(adjacency[index]) < minimum_connections:
            candidate = random.randrange(node_count)
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


def assign_coordinates_for_topology(aps, links):
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
        random.shuffle(neighbors)

        for neighbor_id in neighbors:
            if neighbor_id in visited:
                continue

            neighbor = by_id[neighbor_id]
            desired_distance = max(
                6,
                min(
                    34,
                    (current["radius"] + neighbor["radius"]) * random.uniform(0.42, 0.95),
                ),
            )
            angle = random.uniform(0, math.pi * 2)
            local_jitter = random.uniform(-5.5, 5.5)
            lat_offset = meters_to_latitude_degrees((desired_distance + local_jitter) * math.cos(angle))
            lng_offset = meters_to_longitude_degrees((desired_distance - local_jitter) * math.sin(angle), current["latitude"])

            neighbor_lat = current["latitude"] + lat_offset
            neighbor_lng = current["longitude"] + lng_offset

            # Introduz deslocamentos irregulares para evitar topologia "arrumada".
            neighbor_lat += meters_to_latitude_degrees(random.uniform(-3.5, 3.5))
            neighbor_lng += meters_to_longitude_degrees(random.uniform(-3.5, 3.5), current["latitude"])

            neighbor["latitude"] = round(neighbor_lat, 6)
            neighbor["longitude"] = round(neighbor_lng, 6)
            visited.add(neighbor_id)
            queue.append(neighbor_id)

    for ap in aps:
        if ap["latitude"] is not None and ap["longitude"] is not None:
            continue

        fallback_distance = random.uniform(8, 42)
        fallback_angle = random.uniform(0, math.pi * 2)
        ap["latitude"] = round(origin_lat + meters_to_latitude_degrees(fallback_distance * math.cos(fallback_angle)), 6)
        ap["longitude"] = round(origin_lng + meters_to_longitude_degrees(fallback_distance * math.sin(fallback_angle), origin_lat), 6)

    return [
        {key: value for key, value in ap.items() if key != "radius"}
        for ap in aps
    ]


def generate_access_point_infrastructure(node_count, clique_factor):
    if node_count < 2:
        raise ValueError("node_count deve ser maior ou igual a 2")
    if clique_factor < 1:
        raise ValueError("clique_factor deve ser maior ou igual a 1")
    if clique_factor >= node_count:
        raise ValueError("clique_factor deve ser menor que node_count")

    aps = build_generated_access_points(node_count)
    links = build_generated_links(node_count, clique_factor)
    positioned_aps = assign_coordinates_for_topology(aps, links)

    return {
        "metadata": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "node_count": node_count,
            "clique_factor": clique_factor,
        },
        "aps": positioned_aps,
        "links": links,
    }
