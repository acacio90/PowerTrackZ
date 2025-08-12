from flask import Flask, jsonify, request
import os
import networkx as nx
import math
import json
import requests
from flask_cors import CORS
from strategies import StrategyFactory
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calcular_area_intersecao(r1, r2, d):
    """
    Calcula a área de interseção entre dois círculos
    r1, r2: raios dos círculos em metros
    d: distância entre os centros em metros
    retorna: área de interseção em metros quadrados
    """
    if d >= r1 + r2:
        return 0
    if d <= abs(r1 - r2):
        return math.pi * min(r1, r2)**2
    
    termo1 = r1**2 * math.acos((d**2 + r1**2 - r2**2)/(2*d*r1))
    termo2 = r2**2 * math.acos((d**2 + r2**2 - r1**2)/(2*d*r2))
    termo3 = 0.5 * math.sqrt((-d + r1 + r2)*(d + r1 - r2)*(d - r1 + r2)*(d + r1 + r2))
    
    return termo1 + termo2 - termo3

def build_collision_graph(aps):
    """Constrói o grafo de colisões a partir dos pontos de acesso"""
    def colidem(ap1, ap2):
        distancia = haversine(ap1['x'], ap1['y'], ap2['x'], ap2['y'])
        if distancia >= (ap1['raio'] + ap2['raio']):
            return False, 0

        area_intersecao = calcular_area_intersecao(ap1['raio'], ap2['raio'], distancia)
        area_total = math.pi * (ap1['raio']**2 + ap2['raio']**2)
        porcentagem = (area_intersecao / area_total) * 100
        
        return True, porcentagem

    G = nx.Graph()
    for ap in aps:
        canal = str(ap.get('canal', '')).strip() if ap.get('canal') else None
        G.add_node(ap['id'], 
                  x=ap['x'], 
                  y=ap['y'], 
                  raio=ap['raio'], 
                  label=ap.get('label'), 
                  canal=canal)
    
    for i in range(len(aps)):
        for j in range(i+1, len(aps)):
            colide, peso = colidem(aps[i], aps[j])
            if colide:
                G.add_edge(aps[i]['id'], aps[j]['id'], peso=peso)
    
    return G

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "analysis_service",
        "port": int(os.environ.get('PORT', 5002))
    })

@app.route('/strategies', methods=['GET'])
def get_available_strategies():
    """Retorna as estratégias de análise disponíveis"""
    try:
        strategies = StrategyFactory.get_available_strategies()
        return jsonify({
            "success": True,
            "strategies": strategies,
            "message": "Estratégias disponíveis para análise de grafos"
        })
    except Exception as e:
        logger.error(f"Erro ao obter estratégias: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/collision-graph', methods=['POST'])
def collision_graph():
    """Endpoint original para compatibilidade - usa estratégia backtracking por padrão"""
    data = request.get_json()
    aps = data.get('aps', [])
    
    G = build_collision_graph(aps)
    
    from networkx.readwrite import json_graph
    data = json_graph.node_link_data(G)
    return jsonify(data)

@app.route('/analyze-graph', methods=['POST'])
def analyze_graph():
    """Novo endpoint para análise de grafos com estratégias configuráveis"""
    try:
        data = request.get_json()
        aps = data.get('aps', [])
        strategy_name = data.get('strategy', 'backtracking')
        strategy_params = data.get('parameters', {})
        
        if not aps:
            return jsonify({
                "success": False,
                "error": "Lista de pontos de acesso vazia"
            }), 400
        
        # Constrói o grafo de colisões
        G = build_collision_graph(aps)
        
        if G.number_of_nodes() == 0:
            return jsonify({
                "success": False,
                "error": "Grafo vazio - nenhum ponto de acesso válido"
            }), 400
        
        # Obtém a estratégia solicitada
        try:
            strategy = StrategyFactory.get_strategy(strategy_name)
        except ValueError as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 400
        
        # Executa a análise
        analysis_result = strategy.analyze(G, **strategy_params)
        
        # Adiciona informações do grafo
        from networkx.readwrite import json_graph
        graph_data = json_graph.node_link_data(G)
        
        result = {
            "success": True,
            "strategy_used": strategy_name,
            "analysis": analysis_result,
            "graph_data": graph_data,
            "summary": {
                "total_nodes": G.number_of_nodes(),
                "total_edges": G.number_of_edges(),
                "density": nx.density(G),
                "connected_components": nx.number_connected_components(G)
            }
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro na análise do grafo: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }), 500

@app.route('/compare-strategies', methods=['POST'])
def compare_strategies():
    """Compara diferentes estratégias de análise"""
    try:
        data = request.get_json()
        aps = data.get('aps', [])
        strategies = data.get('strategies', ['backtracking', 'greedy', 'genetic'])
        strategy_params = data.get('parameters', {})
        
        if not aps:
            return jsonify({
                "success": False,
                "error": "Lista de pontos de acesso vazia"
            }), 400
        
        # Constrói o grafo de colisões
        G = build_collision_graph(aps)
        
        if G.number_of_nodes() == 0:
            return jsonify({
                "success": False,
                "error": "Grafo vazio - nenhum ponto de acesso válido"
            }), 400
        
        comparison_results = {}
        
        for strategy_name in strategies:
            try:
                strategy = StrategyFactory.get_strategy(strategy_name)
                analysis_result = strategy.analyze(G, **strategy_params.get(strategy_name, {}))
                comparison_results[strategy_name] = analysis_result
            except Exception as e:
                logger.error(f"Erro na estratégia {strategy_name}: {str(e)}")
                comparison_results[strategy_name] = {
                    "error": str(e),
                    "success": False
                }
        
        # Análise comparativa
        comparison_summary = {
            "strategies_tested": list(comparison_results.keys()),
            "best_strategy": None,
            "performance_metrics": {}
        }
        
        # Determina a melhor estratégia (exemplo simples)
        valid_results = {k: v for k, v in comparison_results.items() if v.get('success', True)}
        if valid_results:
            # Compara baseado em diferentes métricas
            comparison_summary["best_strategy"] = max(valid_results.keys(), 
                key=lambda s: valid_results[s].get('graph_metrics', {}).get('density', 0))
        
        result = {
            "success": True,
            "comparison_results": comparison_results,
            "comparison_summary": comparison_summary,
            "graph_info": {
                "nodes": G.number_of_nodes(),
                "edges": G.number_of_edges(),
                "density": nx.density(G)
            }
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro na comparação de estratégias: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }), 500

@app.route('/analyze', methods=['GET'])
def analyze():
    """Análise básica dos pontos de acesso"""
    try:
        # Busca pontos de acesso do access_point_service
        access_point_url = "http://access_point_service:5004"
        response = requests.get(f"{access_point_url}/access_points")
        if response.status_code != 200:
            return jsonify({"error": "Erro ao buscar pontos de acesso"}), 500
        
        access_points = response.json()
        
        # Análise estatística
        analysis = {
            "total_points": len(access_points),
            "with_coordinates": len([ap for ap in access_points if ap.get('latitude') and ap.get('longitude')]),
            "without_coordinates": len([ap for ap in access_points if not (ap.get('latitude') and ap.get('longitude'))]),
            "frequency_distribution": {},
            "channel_distribution": {},
            "bandwidth_distribution": {},
            "available_strategies": StrategyFactory.get_available_strategies()
        }
        
        # Distribuição de frequências
        for ap in access_points:
            freq = ap.get('frequency', 'Unknown')
            analysis['frequency_distribution'][freq] = analysis['frequency_distribution'].get(freq, 0) + 1
            
            channel = ap.get('channel', 'Unknown')
            analysis['channel_distribution'][channel] = analysis['channel_distribution'].get(channel, 0) + 1
            
            bandwidth = ap.get('bandwidth', 'Unknown')
            analysis['bandwidth_distribution'][bandwidth] = analysis['bandwidth_distribution'].get(bandwidth, 0) + 1
        
        return jsonify(analysis)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=True)