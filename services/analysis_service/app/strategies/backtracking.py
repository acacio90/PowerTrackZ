from typing import Any, Dict, List, Set
import logging

import networkx as nx

from .base import GraphAnalysisStrategy
from .common import apply_configurations_to_graph, assign_configurations, calculate_basic_graph_metrics

logger = logging.getLogger(__name__)


class BacktrackingStrategy(GraphAnalysisStrategy):
    """Estrategia usando backtracking para encontrar cliques maximos."""

    def get_name(self) -> str:
        return "backtracking"

    def get_description(self) -> str:
        return "Algoritmo de backtracking para encontrar cliques maximos no grafo de colisoes"

    def analyze(self, graph: nx.Graph, **kwargs) -> Dict[str, Any]:
        logger.info("Executando analise com estrategia Backtracking")

        cliques = self._find_maximal_cliques(graph)
        max_clique = max(cliques, key=lambda clique: (len(clique), sorted(str(node) for node in clique))) if cliques else []
        ordered_nodes = max_clique + [node for node in graph.nodes() if node not in max_clique]
        proposed_configurations = assign_configurations(graph, ordered_nodes)
        apply_configurations_to_graph(graph, proposed_configurations)

        analysis = {
            "strategy": self.get_name(),
            "description": self.get_description(),
            "total_cliques": len(cliques),
            "max_clique_size": len(max_clique),
            "max_clique_nodes": max_clique,
            "clique_distribution": self._analyze_clique_distribution(cliques),
            "proposed_configurations": proposed_configurations,
            "graph_metrics": self._calculate_graph_metrics(graph),
            "recommendations": self._generate_recommendations(graph, max_clique),
        }

        return analysis

    def _find_maximal_cliques(self, graph: nx.Graph) -> List[List[Any]]:
        """Encontra cliques maximais usando backtracking recursivo."""
        cliques: List[List[Any]] = []
        nodes = set(graph.nodes())
        self._backtrack_cliques(graph, [], nodes, set(), cliques)
        return cliques

    def _backtrack_cliques(
        self,
        graph: nx.Graph,
        current_clique: List[Any],
        candidates: Set[Any],
        excluded: Set[Any],
        cliques: List[List[Any]],
    ) -> None:
        """Explora combinacoes validas de nos para formar cliques maximais."""
        if not candidates and not excluded:
            cliques.append(current_clique.copy())
            return

        for node in list(candidates):
            neighbors = set(graph.neighbors(node))
            current_clique.append(node)
            self._backtrack_cliques(
                graph,
                current_clique,
                candidates.intersection(neighbors),
                excluded.intersection(neighbors),
                cliques,
            )
            current_clique.pop()
            candidates.remove(node)
            excluded.add(node)

    def _analyze_clique_distribution(self, cliques: List[List[Any]]) -> Dict[str, Any]:
        sizes = [len(clique) for clique in cliques]
        return {
            "size_distribution": {size: sizes.count(size) for size in set(sizes)},
            "average_size": sum(sizes) / len(sizes) if sizes else 0,
            "max_size": max(sizes) if sizes else 0,
            "min_size": min(sizes) if sizes else 0,
        }

    def _calculate_graph_metrics(self, graph: nx.Graph) -> Dict[str, Any]:
        metrics = calculate_basic_graph_metrics(graph)
        metrics.update({
            "connected_components": nx.number_connected_components(graph),
            "is_connected": nx.is_connected(graph) if graph.number_of_nodes() > 0 else True,
        })
        return metrics

    def _generate_recommendations(self, graph: nx.Graph, max_clique: List[Any]) -> List[str]:
        recommendations = []

        if len(max_clique) > 3:
            recommendations.append(
                f"Alerta: Clique maximo com {len(max_clique)} pontos - alta interferencia detectada"
            )

        if graph.number_of_edges() > graph.number_of_nodes() * 2:
            recommendations.append("Rede densa detectada - considere redistribuir pontos de acesso")

        if nx.density(graph) > 0.7:
            recommendations.append("Densidade muito alta - risco de interferencia significativa")

        return recommendations
