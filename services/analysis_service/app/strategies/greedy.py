from typing import Any, Dict, List
import logging

import networkx as nx

from .base import GraphAnalysisStrategy
from .common import apply_configurations_to_graph, assign_configurations, calculate_basic_graph_metrics

logger = logging.getLogger(__name__)


class GreedyStrategy(GraphAnalysisStrategy):
    """Estrategia usando algoritmo guloso para otimizacao."""

    def get_name(self) -> str:
        return "greedy"

    def get_description(self) -> str:
        return "Algoritmo guloso para otimizacao de cobertura e minimizacao de interferencia"

    def analyze(self, graph: nx.Graph, **kwargs) -> Dict[str, Any]:
        logger.info("Executando analise com estrategia Greedy")

        selected_nodes = self._greedy_node_selection(graph)
        coverage_analysis = self._analyze_coverage(graph, selected_nodes)
        ordered_nodes = selected_nodes + [node for node in graph.nodes() if node not in selected_nodes]
        proposed_configurations = assign_configurations(graph, ordered_nodes)
        apply_configurations_to_graph(graph, proposed_configurations)

        analysis = {
            "strategy": self.get_name(),
            "description": self.get_description(),
            "selected_nodes": selected_nodes,
            "proposed_configurations": proposed_configurations,
            "coverage_analysis": coverage_analysis,
            "graph_metrics": self._calculate_graph_metrics(graph),
            "optimization_score": self._calculate_optimization_score(graph, selected_nodes),
            "recommendations": self._generate_recommendations(graph, selected_nodes),
        }

        return analysis

    def _greedy_node_selection(self, graph: nx.Graph) -> List[str]:
        nodes = list(graph.nodes())
        selected = []
        remaining = set(nodes)

        while remaining:
            best_node = max(remaining, key=lambda node: self._weighted_degree(graph, node))
            selected.append(best_node)

            neighbors = set(graph.neighbors(best_node))
            remaining -= {best_node}
            remaining -= neighbors

        return selected

    def _weighted_degree(self, graph: nx.Graph, node: str) -> float:
        total_weight = 0
        for neighbor in graph.neighbors(node):
            total_weight += graph[node][neighbor].get("peso", 1)
        return total_weight

    def _analyze_coverage(self, graph: nx.Graph, selected_nodes: List[str]) -> Dict[str, Any]:
        all_nodes = set(graph.nodes())
        covered_nodes = set(selected_nodes)

        for node in selected_nodes:
            covered_nodes.update(graph.neighbors(node))

        coverage_percentage = len(covered_nodes) / len(all_nodes) * 100 if all_nodes else 0

        return {
            "total_nodes": len(all_nodes),
            "covered_nodes": len(covered_nodes),
            "coverage_percentage": coverage_percentage,
            "uncovered_nodes": list(all_nodes - covered_nodes),
        }

    def _calculate_optimization_score(self, graph: nx.Graph, selected_nodes: List[str]) -> float:
        if not selected_nodes:
            return 0.0

        coverage = len(selected_nodes) / graph.number_of_nodes() if graph.number_of_nodes() > 0 else 0

        interference_penalty = 0
        for index, node1 in enumerate(selected_nodes):
            for node2 in selected_nodes[index + 1:]:
                if graph.has_edge(node1, node2):
                    interference_penalty += graph[node1][node2].get("peso", 0)

        return coverage - (interference_penalty / 100)

    def _calculate_graph_metrics(self, graph: nx.Graph) -> Dict[str, Any]:
        return calculate_basic_graph_metrics(graph)

    def _generate_recommendations(self, graph: nx.Graph, selected_nodes: List[str]) -> List[str]:
        recommendations = []

        coverage = len(selected_nodes) / graph.number_of_nodes() if graph.number_of_nodes() > 0 else 0

        if coverage < 0.5:
            recommendations.append("Cobertura baixa - considere adicionar mais pontos de acesso")

        if len(selected_nodes) > graph.number_of_nodes() * 0.7:
            recommendations.append("Muitos pontos selecionados - otimize a distribuicao")

        return recommendations
