from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import math
import os

import networkx as nx
from networkx.readwrite import json_graph
import requests

from strategies import StrategyFactory


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ACCESS_POINT_SERVICE_URL = "http://access_point_service:5004"

app = Flask(__name__)
CORS(app)


def haversine(lat1, lon1, lat2, lon2):
    radius = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def calcular_area_intersecao(r1, r2, distancia):
    """Calcula a area de interseccao entre dois circulos."""
    if distancia >= r1 + r2:
        return 0
    if distancia <= abs(r1 - r2):
        return math.pi * min(r1, r2) ** 2

    termo1 = r1 ** 2 * math.acos((distancia ** 2 + r1 ** 2 - r2 ** 2) / (2 * distancia * r1))
    termo2 = r2 ** 2 * math.acos((distancia ** 2 + r2 ** 2 - r1 ** 2) / (2 * distancia * r2))
    termo3 = 0.5 * math.sqrt(
        (-distancia + r1 + r2)
        * (distancia + r1 - r2)
        * (distancia - r1 + r2)
        * (distancia + r1 + r2)
    )

    return termo1 + termo2 - termo3


def build_collision_graph(access_points):
    """Constroi o grafo de colisoes a partir dos pontos de acesso."""

    def colidem(ap1, ap2):
        distancia = haversine(ap1["x"], ap1["y"], ap2["x"], ap2["y"])
        if distancia >= (ap1["raio"] + ap2["raio"]):
            return False, 0

        area_intersecao = calcular_area_intersecao(ap1["raio"], ap2["raio"], distancia)
        area_total = math.pi * (ap1["raio"] ** 2 + ap2["raio"] ** 2)
        porcentagem = (area_intersecao / area_total) * 100
        return True, porcentagem

    graph = nx.Graph()
    for ap in access_points:
        canal = str(ap.get("canal", "")).strip() if ap.get("canal") else None
        graph.add_node(
            ap["id"],
            x=ap["x"],
            y=ap["y"],
            raio=ap["raio"],
            label=ap.get("label"),
            canal=canal,
        )

    for index in range(len(access_points)):
        for other_index in range(index + 1, len(access_points)):
            colide, peso = colidem(access_points[index], access_points[other_index])
            if colide:
                graph.add_edge(access_points[index]["id"], access_points[other_index]["id"], peso=peso)

    return graph


def error_response(message, status_code=400, **extra):
    payload = {"success": False, "error": message}
    payload.update(extra)
    return jsonify(payload), status_code


def build_graph_from_request_payload(payload):
    access_points = payload.get("aps", [])
    if not access_points:
        return None, error_response("Lista de pontos de acesso vazia", 400)

    graph = build_collision_graph(access_points)
    if graph.number_of_nodes() == 0:
        return None, error_response("Grafo vazio - nenhum ponto de acesso valido", 400)

    return graph, None


def summarize_graph(graph):
    return {
        "total_nodes": graph.number_of_nodes(),
        "total_edges": graph.number_of_edges(),
        "density": nx.density(graph),
        "connected_components": nx.number_connected_components(graph),
    }


def load_access_points():
    response = requests.get(f"{ACCESS_POINT_SERVICE_URL}/access_points")
    if response.status_code != 200:
        raise RuntimeError("Erro ao buscar pontos de acesso")
    return response.json()


@app.route("/health")
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "analysis_service",
        "port": int(os.environ.get("PORT", 5002)),
    })


@app.route("/strategies", methods=["GET"])
def get_available_strategies():
    try:
        return jsonify({
            "success": True,
            "strategies": StrategyFactory.get_available_strategies(),
            "message": "Estrategias disponiveis para analise de grafos",
        })
    except Exception as exc:
        logger.error(f"Erro ao obter estrategias: {str(exc)}")
        return error_response(str(exc), 500)


@app.route("/collision-graph", methods=["POST"])
def collision_graph():
    data = request.get_json() or {}
    graph = build_collision_graph(data.get("aps", []))
    return jsonify(json_graph.node_link_data(graph))


@app.route("/analyze-graph", methods=["POST"])
def analyze_graph():
    try:
        data = request.get_json() or {}
        strategy_name = data.get("strategy", "backtracking")
        strategy_params = data.get("parameters", {})

        graph, graph_error = build_graph_from_request_payload(data)
        if graph_error:
            return graph_error

        try:
            strategy = StrategyFactory.get_strategy(strategy_name)
        except ValueError as exc:
            return error_response(str(exc), 400)

        return jsonify({
            "success": True,
            "strategy_used": strategy_name,
            "analysis": strategy.analyze(graph, **strategy_params),
            "graph_data": json_graph.node_link_data(graph),
            "summary": summarize_graph(graph),
        })
    except Exception as exc:
        logger.error(f"Erro na analise do grafo: {str(exc)}")
        return error_response(f"Erro interno: {str(exc)}", 500)


@app.route("/compare-strategies", methods=["POST"])
def compare_strategies():
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
                strategy = StrategyFactory.get_strategy(strategy_name)
                comparison_results[strategy_name] = strategy.analyze(
                    graph, **strategy_params.get(strategy_name, {})
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


@app.route("/analyze", methods=["GET"])
def analyze():
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port, debug=True)
