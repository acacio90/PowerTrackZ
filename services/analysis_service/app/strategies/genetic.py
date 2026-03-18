from typing import Any, Dict, List
import logging
import random

import networkx as nx

from .base import GraphAnalysisStrategy
from .common import calculate_basic_graph_metrics

logger = logging.getLogger(__name__)


class GeneticStrategy(GraphAnalysisStrategy):
    """Estrategia usando algoritmo genetico para otimizacao."""

    def get_name(self) -> str:
        return "genetic"

    def get_description(self) -> str:
        return "Algoritmo genetico para otimizacao multi-objetivo de cobertura e interferencia"

    def analyze(self, graph: nx.Graph, **kwargs) -> Dict[str, Any]:
        logger.info("Executando analise com estrategia Genetic")

        population_size = kwargs.get("population_size", 50)
        generations = kwargs.get("generations", 100)

        best_solution = self._genetic_algorithm(graph, population_size, generations)

        analysis = {
            "strategy": self.get_name(),
            "description": self.get_description(),
            "best_solution": best_solution,
            "genetic_metrics": {
                "population_size": population_size,
                "generations": generations,
                "fitness_score": best_solution.get("fitness", 0),
            },
            "graph_metrics": self._calculate_graph_metrics(graph),
            "recommendations": self._generate_recommendations(graph, best_solution),
        }

        return analysis

    def _genetic_algorithm(self, graph: nx.Graph, population_size: int, generations: int) -> Dict[str, Any]:
        nodes = list(graph.nodes())
        population = self._generate_initial_population(nodes, population_size)

        best_solution = None
        best_fitness = -float("inf")

        for _ in range(generations):
            for solution in population:
                fitness = self._calculate_fitness(graph, solution)
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_solution = solution.copy()

            population = self._evolve_population(population, graph, nodes)

        return {
            "selected_nodes": best_solution if best_solution else [],
            "fitness": best_fitness,
            "generation": generations,
        }

    def _generate_initial_population(self, nodes: List[str], size: int) -> List[List[str]]:
        population = []
        for _ in range(size):
            num_selected = random.randint(len(nodes) // 3, len(nodes) // 2) if nodes else 0
            solution = random.sample(nodes, num_selected) if num_selected else []
            population.append(solution)
        return population

    def _calculate_fitness(self, graph: nx.Graph, solution: List[str]) -> float:
        if not solution:
            return 0.0

        coverage = len(solution) / graph.number_of_nodes() if graph.number_of_nodes() > 0 else 0

        interference = 0
        for index, node1 in enumerate(solution):
            for node2 in solution[index + 1:]:
                if graph.has_edge(node1, node2):
                    interference += graph[node1][node2].get("peso", 0)

        return coverage - (interference / 100)

    def _evolve_population(
        self, population: List[List[str]], graph: nx.Graph, all_nodes: List[str]
    ) -> List[List[str]]:
        new_population = []

        elite_size = max(1, len(population) // 10)
        elite = sorted(
            population,
            key=lambda solution: self._calculate_fitness(graph, solution),
            reverse=True,
        )[:elite_size]
        new_population.extend(elite)

        while len(new_population) < len(population):
            parent1 = self._tournament_selection(population, graph)
            parent2 = self._tournament_selection(population, graph)

            child = self._crossover(parent1, parent2)

            if random.random() < 0.1:
                child = self._mutate(child, all_nodes)

            new_population.append(child)

        return new_population[: len(population)]

    def _tournament_selection(self, population: List[List[str]], graph: nx.Graph) -> List[str]:
        tournament = random.sample(population, 3)
        return max(tournament, key=lambda solution: self._calculate_fitness(graph, solution))

    def _crossover(self, parent1: List[str], parent2: List[str]) -> List[str]:
        mid = len(parent1) // 2
        child = parent1[:mid] + parent2[mid:]
        return list(set(child))

    def _mutate(self, solution: List[str], all_nodes: List[str]) -> List[str]:
        mutated = solution.copy()
        if random.random() < 0.5:
            available_nodes = [node for node in all_nodes if node not in mutated]
            if available_nodes:
                mutated.append(random.choice(available_nodes))
        elif mutated:
            mutated.pop(random.randint(0, len(mutated) - 1))
        return mutated

    def _calculate_graph_metrics(self, graph: nx.Graph) -> Dict[str, Any]:
        return calculate_basic_graph_metrics(graph)

    def _generate_recommendations(self, graph: nx.Graph, solution: Dict[str, Any]) -> List[str]:
        recommendations = []

        selected_nodes = solution.get("selected_nodes", [])
        fitness = solution.get("fitness", 0)

        if fitness < 0.3:
            recommendations.append("Fitness baixo - considere ajustar parametros do algoritmo")

        if len(selected_nodes) < graph.number_of_nodes() * 0.2:
            recommendations.append("Poucos nos selecionados - pode haver problemas de cobertura")

        return recommendations
