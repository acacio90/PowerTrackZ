from flask import Blueprint, jsonify, redirect, render_template, request, url_for
import logging
import os
import requests

routes = Blueprint('routes', __name__)

logger = logging.getLogger(__name__)

GATEWAY_URL = os.environ["GATEWAY_URL"]


def make_api_request(endpoint, method='GET', data=None):
    """Faz requisicao para a API via gateway."""
    try:
        url = f"{GATEWAY_URL}/api{endpoint}"
        if method == 'GET':
            response = requests.get(url)
        elif method == 'POST':
            response = requests.post(url, json=data)
        elif method == 'PUT':
            response = requests.put(url, json=data)
        elif method == 'DELETE':
            response = requests.delete(url)
        else:
            raise ValueError(f"Metodo HTTP nao suportado: {method}")

        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            return response.json(), response.status_code
        return response.text, response.status_code
    except Exception as e:
        logger.error(f"Erro na requisicao para {endpoint}: {str(e)}")
        return {"error": str(e)}, 500


@routes.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "frontend_service",
        "port": int(os.environ.get("PORT", 3000))
    })


@routes.route('/')
def index():
    return render_template('pages/index.html')


@routes.route('/hosts')
def hosts():
    try:
        hosts_data, status_code = make_api_request('/zabbix/hosts')
        if status_code == 200:
            hosts = hosts_data.get("data", []) if hosts_data.get("success") else []
            return render_template('pages/hosts.html', hosts=hosts)
        return render_template('pages/hosts.html', hosts=[], error=hosts_data)
    except Exception as e:
        return render_template('pages/hosts.html', hosts=[], error={"error": str(e)})


@routes.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            data = {
                "id": request.form.get('id', request.form['description']),
                "name": request.form['description'],
                "channel": request.form['channel'],
                "frequency": request.form['frequency'],
                "bandwidth": request.form['bandwidth'],
                "latitude": request.form['latitude'],
                "longitude": request.form['longitude']
            }

            result, status_code = make_api_request('/access_points', 'POST', data)

            if status_code == 201:
                return redirect(url_for('routes.register'))
            return render_template('pages/register.html', error=result)
        except Exception as e:
            return render_template('pages/register.html', error={"error": str(e)})

    try:
        points_data, _ = make_api_request('/access_points')
        points = points_data if isinstance(points_data, list) else []
    except Exception:
        points = []

    try:
        map_data, _ = make_api_request('/map')
        map_html = map_data if isinstance(map_data, str) else "<p>Error loading map</p>"
    except Exception:
        map_html = "<p>Error loading map</p>"

    return render_template('pages/register.html', points=points, map_html=map_html)


@routes.route('/analysis')
def analysis():
    try:
        points_data, _ = make_api_request('/access_points')
        points = points_data if isinstance(points_data, list) else []
    except Exception:
        points = []
    return render_template('pages/analysis.html', points=points)


@routes.route('/settings')
def settings():
    return render_template('pages/settings.html')


@routes.route('/zabbix/save-config', methods=['POST'])
def save_zabbix_config():
    data = request.get_json(silent=True) or {}
    response_data, status_code = make_api_request('/zabbix/save-config', 'POST', data)
    return jsonify(response_data), status_code


@routes.route('/zabbix/test-connection', methods=['POST'])
def test_zabbix_connection():
    data = request.get_json(silent=True) or {}
    response_data, status_code = make_api_request('/zabbix/test-connection', 'POST', data)
    return jsonify(response_data), status_code


@routes.route('/api/access_points', methods=['GET', 'POST'])
def access_points_api():
    data = request.get_json(silent=True) if request.method in ['POST'] else None
    response_data, status_code = make_api_request('/access_points', request.method, data)
    return jsonify(response_data), status_code


@routes.route('/api/access_points/<point_id>', methods=['GET', 'PUT', 'DELETE'])
def access_point_detail_api(point_id):
    data = request.get_json(silent=True) if request.method == 'PUT' else None
    response_data, status_code = make_api_request(f'/access_points/{point_id}', request.method, data)
    return jsonify(response_data), status_code


@routes.route('/api/analysis/strategies', methods=['GET'])
def analysis_strategies_api():
    response_data, status_code = make_api_request('/analysis/strategies', 'GET')
    return jsonify(response_data), status_code


@routes.route('/api/analysis/analyze-graph', methods=['POST'])
def analysis_analyze_graph_api():
    data = request.get_json(silent=True) or {}
    response_data, status_code = make_api_request('/analysis/analyze-graph', 'POST', data)
    return jsonify(response_data), status_code


@routes.route('/api/analysis/collision-graph', methods=['POST'])
def analysis_collision_graph_api():
    data = request.get_json(silent=True) or {}
    response_data, status_code = make_api_request('/analysis/collision-graph', 'POST', data)
    return jsonify(response_data), status_code
