from typing import Any, Dict

import networkx as nx


def calculate_basic_graph_metrics(graph: nx.Graph) -> Dict[str, Any]:
    node_count = graph.number_of_nodes()
    return {
        "nodes": node_count,
        "edges": graph.number_of_edges(),
        "density": nx.density(graph),
        "average_degree": sum(dict(graph.degree()).values()) / node_count if node_count > 0 else 0,
    }
