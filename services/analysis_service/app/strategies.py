from abc import ABC, abstractmethod
import networkx as nx
import math
from typing import Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)

class GraphAnalysisStrategy(ABC):
    """Classe abstrata para estratégias de análise de grafos"""
    
    @abstractmethod
    def analyze(self, graph: nx.Graph, **kwargs) -> Dict[str, Any]:
        """Método abstrato para análise do grafo"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Retorna o nome da estratégia"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Retorna a descrição da estratégia"""
        pass

class BacktrackingStrategy(GraphAnalysisStrategy):
    """Estratégia usando backtracking para encontrar cliques máximos"""
    
    def get_name(self) -> str:
        return "backtracking"
    
    def get_description(self) -> str:
        return "Algoritmo de backtracking para encontrar cliques máximos no grafo de colisões"
    
    def analyze(self, graph: nx.Graph, **kwargs) -> Dict[str, Any]:
        """Implementa análise usando backtracking"""
        logger.info("Executando análise com estratégia Backtracking")
        
        # Encontra cliques máximos usando backtracking
        cliques = list(nx.find_cliques(graph))
        max_clique = max(cliques, key=len) if cliques else []
        
        # Calcula métricas
        analysis = {
            "strategy": self.get_name(),
            "description": self.get_description(),
            "total_cliques": len(cliques),
            "max_clique_size": len(max_clique),
            "max_clique_nodes": max_clique,
            "clique_distribution": self._analyze_clique_distribution(cliques),
            "graph_metrics": self._calculate_graph_metrics(graph),
            "recommendations": self._generate_recommendations(graph, max_clique)
        }
        
        return analysis
    
    def _analyze_clique_distribution(self, cliques: List[List]) -> Dict[str, Any]:
        """Analisa a distribuição de tamanhos de cliques"""
        sizes = [len(clique) for clique in cliques]
        return {
            "size_distribution": {size: sizes.count(size) for size in set(sizes)},
            "average_size": sum(sizes) / len(sizes) if sizes else 0,
            "max_size": max(sizes) if sizes else 0,
            "min_size": min(sizes) if sizes else 0
        }
    
    def _calculate_graph_metrics(self, graph: nx.Graph) -> Dict[str, Any]:
        """Calcula métricas básicas do grafo"""
        return {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "density": nx.density(graph),
            "average_degree": sum(dict(graph.degree()).values()) / graph.number_of_nodes() if graph.number_of_nodes() > 0 else 0,
            "connected_components": nx.number_connected_components(graph),
            "is_connected": nx.is_connected(graph) if graph.number_of_nodes() > 0 else True
        }
    
    def _generate_recommendations(self, graph: nx.Graph, max_clique: List) -> List[str]:
        """Gera recomendações baseadas na análise"""
        recommendations = []
        
        if len(max_clique) > 3:
            recommendations.append(f"Alerta: Clique máximo com {len(max_clique)} pontos - alta interferência detectada")
        
        if graph.number_of_edges() > graph.number_of_nodes() * 2:
            recommendations.append("Rede densa detectada - considere redistribuir pontos de acesso")
        
        if nx.density(graph) > 0.7:
            recommendations.append("Densidade muito alta - risco de interferência significativa")
        
        return recommendations

class GreedyStrategy(GraphAnalysisStrategy):
    """Estratégia usando algoritmo guloso para otimização"""
    
    def get_name(self) -> str:
        return "greedy"
    
    def get_description(self) -> str:
        return "Algoritmo guloso para otimização de cobertura e minimização de interferência"
    
    def analyze(self, graph: nx.Graph, **kwargs) -> Dict[str, Any]:
        """Implementa análise usando algoritmo guloso"""
        logger.info("Executando análise com estratégia Greedy")
        
        # Algoritmo guloso para seleção de nós
        selected_nodes = self._greedy_node_selection(graph)
        
        # Calcula cobertura
        coverage_analysis = self._analyze_coverage(graph, selected_nodes)
        
        analysis = {
            "strategy": self.get_name(),
            "description": self.get_description(),
            "selected_nodes": selected_nodes,
            "coverage_analysis": coverage_analysis,
            "graph_metrics": self._calculate_graph_metrics(graph),
            "optimization_score": self._calculate_optimization_score(graph, selected_nodes),
            "recommendations": self._generate_recommendations(graph, selected_nodes)
        }
        
        return analysis
    
    def _greedy_node_selection(self, graph: nx.Graph) -> List[str]:
        """Seleção gulosa de nós baseada em grau e peso das arestas"""
        nodes = list(graph.nodes())
        selected = []
        remaining = set(nodes)
        
        while remaining:
            # Seleciona o nó com maior grau ponderado
            best_node = max(remaining, key=lambda n: self._weighted_degree(graph, n))
            selected.append(best_node)
            
            # Remove o nó selecionado e seus vizinhos
            neighbors = set(graph.neighbors(best_node))
            remaining -= {best_node}
            remaining -= neighbors
        
        return selected
    
    def _weighted_degree(self, graph: nx.Graph, node: str) -> float:
        """Calcula o grau ponderado de um nó"""
        total_weight = 0
        for neighbor in graph.neighbors(node):
            weight = graph[node][neighbor].get('peso', 1)
            total_weight += weight
        return total_weight
    
    def _analyze_coverage(self, graph: nx.Graph, selected_nodes: List[str]) -> Dict[str, Any]:
        """Analisa a cobertura dos nós selecionados"""
        all_nodes = set(graph.nodes())
        covered_nodes = set(selected_nodes)
        
        # Adiciona vizinhos dos nós selecionados
        for node in selected_nodes:
            covered_nodes.update(graph.neighbors(node))
        
        coverage_percentage = len(covered_nodes) / len(all_nodes) * 100 if all_nodes else 0
        
        return {
            "total_nodes": len(all_nodes),
            "covered_nodes": len(covered_nodes),
            "coverage_percentage": coverage_percentage,
            "uncovered_nodes": list(all_nodes - covered_nodes)
        }
    
    def _calculate_optimization_score(self, graph: nx.Graph, selected_nodes: List[str]) -> float:
        """Calcula score de otimização"""
        if not selected_nodes:
            return 0.0
        
        # Score baseado na cobertura e minimização de interferência
        coverage = len(selected_nodes) / graph.number_of_nodes() if graph.number_of_nodes() > 0 else 0
        
        # Penalidade por interferência entre nós selecionados
        interference_penalty = 0
        for i, node1 in enumerate(selected_nodes):
            for node2 in selected_nodes[i+1:]:
                if graph.has_edge(node1, node2):
                    weight = graph[node1][node2].get('peso', 0)
                    interference_penalty += weight
        
        return coverage - (interference_penalty / 100)  # Normaliza a penalidade
    
    def _calculate_graph_metrics(self, graph: nx.Graph) -> Dict[str, Any]:
        """Calcula métricas básicas do grafo"""
        return {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "density": nx.density(graph),
            "average_degree": sum(dict(graph.degree()).values()) / graph.number_of_nodes() if graph.number_of_nodes() > 0 else 0
        }
    
    def _generate_recommendations(self, graph: nx.Graph, selected_nodes: List[str]) -> List[str]:
        """Gera recomendações baseadas na análise gulosa"""
        recommendations = []
        
        coverage = len(selected_nodes) / graph.number_of_nodes() if graph.number_of_nodes() > 0 else 0
        
        if coverage < 0.5:
            recommendations.append("Cobertura baixa - considere adicionar mais pontos de acesso")
        
        if len(selected_nodes) > graph.number_of_nodes() * 0.7:
            recommendations.append("Muitos pontos selecionados - otimize a distribuição")
        
        return recommendations

class GeneticStrategy(GraphAnalysisStrategy):
    """Estratégia usando algoritmo genético para otimização"""
    
    def get_name(self) -> str:
        return "genetic"
    
    def get_description(self) -> str:
        return "Algoritmo genético para otimização multi-objetivo de cobertura e interferência"
    
    def analyze(self, graph: nx.Graph, **kwargs) -> Dict[str, Any]:
        """Implementa análise usando algoritmo genético"""
        logger.info("Executando análise com estratégia Genetic")
        
        # Parâmetros do algoritmo genético
        population_size = kwargs.get('population_size', 50)
        generations = kwargs.get('generations', 100)
        
        # Executa algoritmo genético
        best_solution = self._genetic_algorithm(graph, population_size, generations)
        
        analysis = {
            "strategy": self.get_name(),
            "description": self.get_description(),
            "best_solution": best_solution,
            "genetic_metrics": {
                "population_size": population_size,
                "generations": generations,
                "fitness_score": best_solution.get('fitness', 0)
            },
            "graph_metrics": self._calculate_graph_metrics(graph),
            "recommendations": self._generate_recommendations(graph, best_solution)
        }
        
        return analysis
    
    def _genetic_algorithm(self, graph: nx.Graph, population_size: int, generations: int) -> Dict[str, Any]:
        """Implementação simplificada de algoritmo genético"""
        # Esta é uma implementação básica - pode ser expandida
        nodes = list(graph.nodes())
        
        # Gera população inicial
        population = self._generate_initial_population(nodes, population_size)
        
        best_solution = None
        best_fitness = -float('inf')
        
        for generation in range(generations):
            # Avalia fitness da população
            for solution in population:
                fitness = self._calculate_fitness(graph, solution)
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_solution = solution.copy()
            
            # Seleção, crossover e mutação
            population = self._evolve_population(population, graph)
        
        return {
            "selected_nodes": best_solution if best_solution else [],
            "fitness": best_fitness,
            "generation": generations
        }
    
    def _generate_initial_population(self, nodes: List[str], size: int) -> List[List[str]]:
        """Gera população inicial aleatória"""
        import random
        population = []
        for _ in range(size):
            # Seleciona aleatoriamente 30-70% dos nós
            num_selected = random.randint(len(nodes) // 3, len(nodes) // 2)
            solution = random.sample(nodes, num_selected)
            population.append(solution)
        return population
    
    def _calculate_fitness(self, graph: nx.Graph, solution: List[str]) -> float:
        """Calcula fitness de uma solução"""
        if not solution:
            return 0.0
        
        # Fitness baseado em cobertura e interferência
        coverage = len(solution) / graph.number_of_nodes() if graph.number_of_nodes() > 0 else 0
        
        # Penalidade por interferência
        interference = 0
        for i, node1 in enumerate(solution):
            for node2 in solution[i+1:]:
                if graph.has_edge(node1, node2):
                    weight = graph[node1][node2].get('peso', 0)
                    interference += weight
        
        return coverage - (interference / 100)
    
    def _evolve_population(self, population: List[List[str]], graph: nx.Graph) -> List[List[str]]:
        """Evolui a população usando seleção, crossover e mutação"""
        import random
        
        new_population = []
        
        # Elitismo: mantém os melhores 10%
        elite_size = max(1, len(population) // 10)
        elite = sorted(population, key=lambda x: self._calculate_fitness(graph, x), reverse=True)[:elite_size]
        new_population.extend(elite)
        
        # Gera resto da população
        while len(new_population) < len(population):
            # Seleção por torneio
            parent1 = self._tournament_selection(population, graph)
            parent2 = self._tournament_selection(population, graph)
            
            # Crossover
            child = self._crossover(parent1, parent2)
            
            # Mutação
            if random.random() < 0.1:  # 10% de chance de mutação
                child = self._mutate(child)
            
            new_population.append(child)
        
        return new_population[:len(population)]
    
    def _tournament_selection(self, population: List[List[str]], graph: nx.Graph) -> List[str]:
        """Seleção por torneio"""
        import random
        tournament_size = 3
        tournament = random.sample(population, tournament_size)
        return max(tournament, key=lambda x: self._calculate_fitness(graph, x))
    
    def _crossover(self, parent1: List[str], parent2: List[str]) -> List[str]:
        """Crossover entre dois pais"""
        import random
        # Crossover simples: pega metade de cada pai
        mid = len(parent1) // 2
        child = parent1[:mid] + parent2[mid:]
        return list(set(child))  # Remove duplicatas
    
    def _mutate(self, solution: List[str]) -> List[str]:
        """Mutação de uma solução"""
        import random
        if random.random() < 0.5:
            # Adiciona um nó aleatório
            all_nodes = list(set(solution) | set(['node1', 'node2', 'node3']))  # Exemplo
            if all_nodes:
                solution.append(random.choice(all_nodes))
        else:
            # Remove um nó aleatório
            if solution:
                solution.pop(random.randint(0, len(solution) - 1))
        return solution
    
    def _calculate_graph_metrics(self, graph: nx.Graph) -> Dict[str, Any]:
        """Calcula métricas básicas do grafo"""
        return {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "density": nx.density(graph),
            "average_degree": sum(dict(graph.degree()).values()) / graph.number_of_nodes() if graph.number_of_nodes() > 0 else 0
        }
    
    def _generate_recommendations(self, graph: nx.Graph, solution: Dict[str, Any]) -> List[str]:
        """Gera recomendações baseadas na análise genética"""
        recommendations = []
        
        selected_nodes = solution.get('selected_nodes', [])
        fitness = solution.get('fitness', 0)
        
        if fitness < 0.3:
            recommendations.append("Fitness baixo - considere ajustar parâmetros do algoritmo")
        
        if len(selected_nodes) < graph.number_of_nodes() * 0.2:
            recommendations.append("Poucos nós selecionados - pode haver problemas de cobertura")
        
        return recommendations

class StrategyFactory:
    """Factory para criar estratégias de análise"""
    
    _strategies = {
        "backtracking": BacktrackingStrategy,
        "greedy": GreedyStrategy,
        "genetic": GeneticStrategy
    }
    
    @classmethod
    def get_strategy(cls, strategy_name: str) -> GraphAnalysisStrategy:
        """Retorna uma instância da estratégia solicitada"""
        if strategy_name not in cls._strategies:
            raise ValueError(f"Estratégia '{strategy_name}' não encontrada. Estratégias disponíveis: {list(cls._strategies.keys())}")
        
        return cls._strategies[strategy_name]()
    
    @classmethod
    def get_available_strategies(cls) -> Dict[str, str]:
        """Retorna lista de estratégias disponíveis com suas descrições"""
        return {
            name: strategy().get_description() 
            for name, strategy in cls._strategies.items()
        } 