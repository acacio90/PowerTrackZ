from abc import ABC, abstractmethod
from typing import Any, Dict

import networkx as nx


class GraphAnalysisStrategy(ABC):
    """Contrato base para estrategias de analise de grafos."""

    @abstractmethod
    def analyze(self, graph: nx.Graph, **kwargs) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def get_description(self) -> str:
        pass
