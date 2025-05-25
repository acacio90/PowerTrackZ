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
        return distancia < (ap1['raio'] + ap2['raio']), distancia

    G = nx.Graph()
    for ap in aps:
        G.add_node(ap['id'], x=ap['x'], y=ap['y'], raio=ap['raio'], label=ap.get('label'), canal=ap.get('canal'))
    for i in range(len(aps)):
        for j in range(i+1, len(aps)):
            colide, distancia = colidem(aps[i], aps[j])
            if colide:
                G.add_edge(aps[i]['id'], aps[j]['id'], peso=distancia)
    from networkx.readwrite import json_graph
    data = json_graph.node_link_data(G)
    return jsonify(data)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=True)