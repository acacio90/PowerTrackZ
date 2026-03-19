from hashlib import md5
from typing import Any, Dict, Iterable, List, Optional, Set

import networkx as nx


def calculate_basic_graph_metrics(graph: nx.Graph) -> Dict[str, Any]:
    node_count = graph.number_of_nodes()
    return {
        "nodes": node_count,
        "edges": graph.number_of_edges(),
        "density": nx.density(graph),
        "average_degree": sum(dict(graph.degree()).values()) / node_count if node_count > 0 else 0,
    }


def build_configuration_key(channel: Optional[str], bandwidth: Optional[str], frequency: Optional[str]) -> str:
    return f"{channel or 'N/A'}-{bandwidth or 'N/A'}-{frequency or 'N/A'}"


def build_color_from_key(config_key: str) -> str:
    digest = md5(config_key.encode("utf-8")).hexdigest()
    return f"#{digest[:6]}"


def generate_possible_configurations(graph: nx.Graph) -> List[str]:
    bandas_por_freq = {
        "2.4": ["40", "20"],
        "5": ["80", "40", "20"],
        "6": ["80", "40", "20"],
    }
    configs: Set[str] = set()

    for _, data in graph.nodes(data=True):
        channel = data.get("channel") or data.get("canal")
        bandwidth = data.get("bandwidth")
        frequency = data.get("frequency")
        freq = str(frequency or "").replace(",", ".")
        freq_base = "2.4" if freq.startswith("2.4") else "5" if freq.startswith("5") else "6" if freq.startswith("6") else None

        if freq_base and channel:
            for bw in bandas_por_freq[freq_base]:
                configs.add(build_configuration_key(str(channel), bw, str(frequency)))
        else:
            configs.add(build_configuration_key(
                str(channel) if channel is not None else None,
                str(bandwidth) if bandwidth is not None else None,
                str(frequency) if frequency is not None else None,
            ))

    return sorted(configs)


def assign_configurations(
    graph: nx.Graph,
    node_order: Iterable[Any],
) -> Dict[Any, Dict[str, Any]]:
    configs_disponiveis = generate_possible_configurations(graph)
    ordered_links = sorted(
        (
            {"source": source, "target": target, "peso": data.get("peso", 1)}
            for source, target, data in graph.edges(data=True)
        ),
        key=lambda edge: edge["peso"],
        reverse=True,
    )

    configuracoes: Dict[Any, Optional[str]] = {}
    for node in graph.nodes():
        data = graph.nodes[node]
        if data.get("locked"):
            configuracoes[node] = build_configuration_key(
                data.get("channel") or data.get("canal"),
                data.get("bandwidth"),
                data.get("frequency"),
            )
        else:
            configuracoes[node] = None

    for node in node_order:
        node_data = graph.nodes[node]
        if node_data.get("locked"):
            continue

        frequency = str(node_data.get("frequency") or "").replace(",", ".")
        valid_configs = configs_disponiveis
        if frequency:
            valid_configs = [
                config for config in configs_disponiveis
                if (config.split("-")[2] or "").strip().replace(",", ".") == frequency
            ]

        valid_configs = sorted(
            valid_configs,
            key=lambda config: int((config.split("-")[1] or "0").replace(" MHz", "").strip() or 0),
            reverse=True,
        )
        best_config = valid_configs[0] if valid_configs else build_configuration_key(
            node_data.get("channel") or node_data.get("canal"),
            node_data.get("bandwidth"),
            node_data.get("frequency"),
        )
        lowest_conflict = float("inf")

        for config in valid_configs or [best_config]:
            conflict = 0
            for neighbor in graph.neighbors(node):
                if configuracoes.get(neighbor) != config:
                    continue

                edge = next(
                    (
                        item for item in ordered_links
                        if (item["source"] == node and item["target"] == neighbor)
                        or (item["source"] == neighbor and item["target"] == node)
                    ),
                    None,
                )
                conflict += edge["peso"] if edge else 1

            if conflict < lowest_conflict:
                lowest_conflict = conflict
                best_config = config

        configuracoes[node] = best_config

    result: Dict[Any, Dict[str, Any]] = {}
    for node, config in configuracoes.items():
        channel, bandwidth, frequency = config.split("-", 2)
        result[node] = {
            "channel": None if channel == "N/A" else channel,
            "bandwidth": None if bandwidth == "N/A" else bandwidth,
            "frequency": None if frequency == "N/A" else frequency,
            "color": build_color_from_key(config),
            "config_key": config,
        }

    return result


def apply_configurations_to_graph(graph: nx.Graph, configurations: Dict[Any, Dict[str, Any]]) -> nx.Graph:
    for node, config in configurations.items():
        graph.nodes[node]["proposed_channel"] = config["channel"]
        graph.nodes[node]["proposed_bandwidth"] = config["bandwidth"]
        graph.nodes[node]["proposed_frequency"] = config["frequency"]
        graph.nodes[node]["cor"] = config["color"]
        graph.nodes[node]["config_key"] = config["config_key"]
    return graph
