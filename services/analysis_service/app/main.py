from flask import Flask, jsonify, request
import os
import networkx as nx
import math
import json
from flask_cors import CORS

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

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "analysis_service",
        "port": int(os.environ.get('PORT', 5002))
    })

@app.route('/collision-graph', methods=['POST'])
def collision_graph():
    data = request.get_json()
    aps = data.get('aps', [])

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
    
    from networkx.readwrite import json_graph
    data = json_graph.node_link_data(G)
    return jsonify(data)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=True)