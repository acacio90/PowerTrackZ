from flask import Blueprint, jsonify, request
import logging
import math
import os

import networkx as nx
from networkx.readwrite import json_graph
import requests

from strategies import StrategyFactory
from strategies.common import build_color_from_key, build_configuration_key


routes = Blueprint("routes", __name__)

logger = logging.getLogger(__name__)

GATEWAY_URL = os.environ.get("GATEWAY_URL")


def haversine(lat1, lon1, lat2, lon2):
    """Calcula a distancia em metros entre duas coordenadas geograficas."""
    radius = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def calculate_intersection_area(r1, r2, distance):
    """Calcula a area de interseccao entre dois circulos."""
    if distance >= r1 + r2:
        return 0
    if distance <= abs(r1 - r2):
        return math.pi * min(r1, r2) ** 2

    term1 = r1 ** 2 * math.acos((distance ** 2 + r1 ** 2 - r2 ** 2) / (2 * distance * r1))
    term2 = r2 ** 2 * math.acos((distance ** 2 + r2 ** 2 - r1 ** 2) / (2 * distance * r2))
    term3 = 0.5 * math.sqrt(
        (-distance + r1 + r2)
        * (distance + r1 - r2)
        * (distance - r1 + r2)
        * (distance + r1 + r2)
    )

    return term1 + term2 - term3


def build_collision_graph(access_points):
    """Constroi o grafo de colisoes com base na sobreposicao entre os pontos de acesso."""

    def colidem(ap1, ap2):
        """Verifica se dois pontos de acesso colidem e calcula o peso da sobreposicao."""
        distancia = haversine(ap1["x"], ap1["y"], ap2["x"], ap2["y"])
        if distancia >= (ap1["raio"] + ap2["raio"]):
            return False, 0

        area_intersecao = calculate_intersection_area(ap1["raio"], ap2["raio"], distancia)
        smaller_area = math.pi * min(ap1["raio"], ap2["raio"]) ** 2
        porcentagem = (area_intersecao / smaller_area) * 100
        return True, porcentagem

    graph = nx.Graph()
    for ap in access_points:
        channel_value = ap.get("canal") if ap.get("canal") is not None else ap.get("channel")
        canal = str(channel_value).strip() if channel_value else None
        graph.add_node(
            ap["id"],
            x=ap["x"],
            y=ap["y"],
            raio=ap["raio"],
            label=ap.get("label"),
            canal=canal,
            channel=canal,
            bandwidth=ap.get("bandwidth"),
            frequency=ap.get("frequency"),
            locked=ap.get("locked", False),
            cor=build_color_from_key(
                build_configuration_key(
                    canal,
                    ap.get("bandwidth"),
                    ap.get("frequency"),
                )
            ),
        )

    for index in range(len(access_points)):
        for other_index in range(index + 1, len(access_points)):
            colide, peso = colidem(access_points[index], access_points[other_index])
            if colide:
                graph.add_edge(access_points[index]["id"], access_points[other_index]["id"], peso=peso)

    return graph


def error_response(message, status_code=400, **extra):
    """Monta uma resposta de erro padronizada da API."""
    payload = {"success": False, "error": message}
    payload.update(extra)
    return jsonify(payload), status_code


def build_graph_from_request_payload(payload):
    """Valida o payload da requisicao e gera o grafo de colisoes."""
    access_points = payload.get("aps", [])
    if not access_points:
        return None, error_response("Lista de pontos de acesso vazia", 400)

    graph = build_collision_graph(access_points)
    if graph.number_of_nodes() == 0:
        return None, error_response("Grafo vazio - nenhum ponto de acesso valido", 400)

    return graph, None


def summarize_graph(graph):
    """Resume as principais metricas estruturais do grafo."""
    return {
        "total_nodes": graph.number_of_nodes(),
        "total_edges": graph.number_of_edges(),
        "density": nx.density(graph),
        "connected_components": nx.number_connected_components(graph),
    }


def run_strategy_analysis(strategy_name, graph, strategy_params):
    """Executa a estrategia solicitada a partir do nome informado."""
    strategy = StrategyFactory.get_strategy(strategy_name)
    return strategy.analyze(graph, **strategy_params)


def load_access_points():
    """Busca os pontos de acesso por meio do gateway da API."""
    if not GATEWAY_URL:
        raise RuntimeError("Variavel de ambiente GATEWAY_URL nao configurada")

    response = requests.get(
        f"{GATEWAY_URL}/api/access_points",
        timeout=int(os.environ["ANALYSIS_HTTP_TIMEOUT"]),
    )
    if response.status_code != 200:
        raise RuntimeError("Erro ao buscar pontos de acesso")
    return response.json()


@routes.route("/health")
def health_check():
    """Retorna o estado de saude do servico de analise."""
    return jsonify({
        "status": "healthy",
        "service": "analysis_service",
        "port": int(os.environ.get("PORT", 5002)),
    })


@routes.route("/strategies", methods=["GET"])
def get_available_strategies():
    """Lista as estrategias de analise de grafo disponiveis."""
    try:
        return jsonify({
            "success": True,
            "strategies": StrategyFactory.get_available_strategies(),
            "message": "Estrategias disponiveis para analise de grafos",
        })
    except Exception as exc:
        logger.error(f"Erro ao obter estrategias: {str(exc)}")
        return error_response(str(exc), 500)


@routes.route("/collision-graph", methods=["POST"])
def collision_graph():
    """Gera e retorna o grafo de colisoes a partir do payload recebido."""
    data = request.get_json() or {}
    graph = build_collision_graph(data.get("aps", []))
    return jsonify(json_graph.node_link_data(graph))


@routes.route("/analyze-graph", methods=["POST"])
def analyze_graph():
    """Executa a estrategia solicitada sobre o grafo gerado no payload."""
    try:
        data = request.get_json() or {}
        strategy_name = data.get("strategy", "backtracking")
        strategy_params = data.get("parameters", {})

        graph, graph_error = build_graph_from_request_payload(data)
        if graph_error:
            return graph_error

        try:
            analysis = run_strategy_analysis(strategy_name, graph, strategy_params)
        except ValueError as exc:
            return error_response(str(exc), 400)

        return jsonify({
            "success": True,
            "strategy_used": strategy_name,
            "analysis": analysis,
            "graph_data": json_graph.node_link_data(graph),
            "summary": summarize_graph(graph),
        })
    except Exception as exc:
        logger.error(f"Erro na analise do grafo: {str(exc)}")
        return error_response(f"Erro interno: {str(exc)}", 500)


@routes.route("/compare-strategies", methods=["POST"])
def compare_strategies():
    """Compara multiplas estrategias de analise sobre o mesmo grafo."""
    try:
        data = request.get_json() or {}
        strategy_names = data.get("strategies", ["backtracking", "greedy", "genetic"])
        strategy_params = data.get("parameters", {})

        graph, graph_error = build_graph_from_request_payload(data)
        if graph_error:
            return graph_error

        comparison_results = {}
        for strategy_name in strategy_names:
            try:
                comparison_results[strategy_name] = run_strategy_analysis(
                    strategy_name,
                    graph,
                    strategy_params.get(strategy_name, {}),
                )
            except Exception as exc:
                logger.error(f"Erro na estrategia {strategy_name}: {str(exc)}")
                comparison_results[strategy_name] = {
                    "error": str(exc),
                    "success": False,
                }

        comparison_summary = {
            "strategies_tested": list(comparison_results.keys()),
            "best_strategy": None,
            "performance_metrics": {},
        }

        valid_results = {
            name: result for name, result in comparison_results.items() if result.get("success", True)
        }
        if valid_results:
            comparison_summary["best_strategy"] = max(
                valid_results.keys(),
                key=lambda name: valid_results[name].get("graph_metrics", {}).get("density", 0),
            )

        return jsonify({
            "success": True,
            "comparison_results": comparison_results,
            "comparison_summary": comparison_summary,
            "graph_info": {
                "nodes": graph.number_of_nodes(),
                "edges": graph.number_of_edges(),
                "density": nx.density(graph),
            },
        })
    except Exception as exc:
        logger.error(f"Erro na comparacao de estrategias: {str(exc)}")
        return error_response(f"Erro interno: {str(exc)}", 500)


@routes.route("/analyze", methods=["GET"])
def analyze():
    """Consolida estatisticas gerais dos pontos de acesso cadastrados."""
    try:
        access_points = load_access_points()
        analysis = {
            "total_points": len(access_points),
            "with_coordinates": len(
                [ap for ap in access_points if ap.get("latitude") and ap.get("longitude")]
            ),
            "without_coordinates": len(
                [ap for ap in access_points if not (ap.get("latitude") and ap.get("longitude"))]
            ),
            "frequency_distribution": {},
            "channel_distribution": {},
            "bandwidth_distribution": {},
            "available_strategies": StrategyFactory.get_available_strategies(),
        }

        for ap in access_points:
            frequency = ap.get("frequency", "Unknown")
            channel = ap.get("channel", "Unknown")
            bandwidth = ap.get("bandwidth", "Unknown")

            analysis["frequency_distribution"][frequency] = (
                analysis["frequency_distribution"].get(frequency, 0) + 1
            )
            analysis["channel_distribution"][channel] = (
                analysis["channel_distribution"].get(channel, 0) + 1
            )
            analysis["bandwidth_distribution"][bandwidth] = (
                analysis["bandwidth_distribution"].get(bandwidth, 0) + 1
            )

        return jsonify(analysis)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
