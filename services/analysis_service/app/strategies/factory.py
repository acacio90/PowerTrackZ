from typing import Dict, Type

from .backtracking import BacktrackingStrategy
from .base import GraphAnalysisStrategy
from .genetic import GeneticStrategy
from .greedy import GreedyStrategy


class StrategyFactory:
    """Factory para criar estrategias de analise."""

    _strategies: Dict[str, Type[GraphAnalysisStrategy]] = {
        "backtracking": BacktrackingStrategy,
        "greedy": GreedyStrategy,
        "genetic": GeneticStrategy,
    }

    @classmethod
    def get_strategy(cls, strategy_name: str) -> GraphAnalysisStrategy:
        if strategy_name not in cls._strategies:
            raise ValueError(
                f"Estrategia '{strategy_name}' nao encontrada. "
                f"Estrategias disponiveis: {list(cls._strategies.keys())}"
            )

        return cls._strategies[strategy_name]()

    @classmethod
    def get_available_strategies(cls) -> Dict[str, str]:
        return {
            name: strategy_class().get_description()
            for name, strategy_class in cls._strategies.items()
        }
