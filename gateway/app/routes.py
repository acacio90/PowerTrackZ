from flask import Blueprint, request, jsonify, render_template, redirect, url_for
import logging
import requests
from .config import Config

logger = logging.getLogger(__name__)
routes = Blueprint('routes', __name__)
session = requests.Session()
session.verify = False

def handle_error(e, service_name):
    error_msg = str(e)
    if isinstance(e, requests.exceptions.ConnectionError):
        return {"message": f"Erro de conexão com {service_name}", "error": error_msg}, 503
    elif isinstance(e, requests.exceptions.Timeout):
        return {"message": f"Timeout ao conectar com {service_name}", "error": error_msg}, 504
    else:
        return {"message": f"Erro ao conectar com {service_name}", "error": error_msg}, 500

@routes.route('/')
def index():
    return render_template('pages/index.html')

@routes.route('/hosts', methods=['GET'])
def hosts():
    try:
        response = session.get(f"{Config.ZABBIX_SERVICE_URL}/hosts")
        if response.status_code == 200:
            result = response.json()
            hosts = result.get("data", []) if result.get("success") else []
            return render_template('pages/hosts.html', hosts=hosts)
        return render_template('pages/hosts.html', hosts=[], error=response.json())
    except Exception as e:
        error_response, _ = handle_error(e, "Zabbix")
        return render_template('pages/hosts.html', hosts=[], error=error_response)

@routes.route('/zabbix/test-connection', methods=['POST'])
def test_zabbix_connection():
    try:
        response = session.post(f"{Config.ZABBIX_SERVICE_URL}/test-connection", json=request.get_json() or {})
        return response.json()
    except Exception as e:
        error_response, status_code = handle_error(e, "Zabbix")
        return jsonify(error_response), status_code

@routes.route('/zabbix/hosts', methods=['POST'])
def get_hosts():
    try:
        response = session.post(f"{Config.ZABBIX_SERVICE_URL}/hosts", json=request.get_json() or {})
        return response.json()
    except Exception as e:
        error_response, status_code = handle_error(e, "Zabbix")
        return jsonify(error_response), status_code

@routes.route('/zabbix/save-config', methods=['POST'])
def save_config():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Dados obrigatórios"}), 400
        response = session.post(f"{Config.ZABBIX_SERVICE_URL}/save-config", json=data)
        return response.json()
    except Exception as e:
        error_response, status_code = handle_error(e, "Zabbix")
        return jsonify(error_response), status_code

@routes.route('/map', methods=['GET'])
def get_map():
    try:
        response = session.get(f"{Config.MAP_SERVICE_URL}/map")
        return response.content, response.status_code, {'Content-Type': 'text/html'}
    except Exception as e:
        error_response, status_code = handle_error(e, "map_service")
        return jsonify(error_response), status_code

@routes.route('/analyze', methods=['GET'])
def analyze():
    try:
        response = session.get(f"{Config.ANALYSIS_SERVICE_URL}/analyze")
        return jsonify(response.json()), response.status_code
    except Exception as e:
        error_response, status_code = handle_error(e, "analysis_service")
        return jsonify(error_response), status_code

@routes.route('/access_points', methods=['GET'])
def get_access_points():
    try:
        response = session.get(f"{Config.ACCESS_POINT_SERVICE_URL}/access_points")
        return jsonify(response.json()), response.status_code
    except Exception as e:
        error_response, status_code = handle_error(e, "access_point_service")
        return jsonify(error_response), status_code

@routes.route('/register', methods=['GET', 'POST'])
def register():
    print('>>> Entrou na rota /register, método:', request.method)
    if request.method == 'POST':
        try:
            if request.is_json:
                data = request.get_json()
            else:
                data = {
                    "id": request.form.get('id', request.form['description']),
                    "name": request.form['description'],
                    "channel": request.form['channel'],
                    "frequency": request.form['frequency'],
                    "bandwidth": request.form['bandwidth'],
                    "latitude": request.form['latitude'],
                    "longitude": request.form['longitude'],
                    "coordenadas": f"{request.form['latitude']},{request.form['longitude']}"
                }
            print('Enviando para access_point_service:', data)
            response = session.post(f"{Config.ACCESS_POINT_SERVICE_URL}/access_points", json=data)
            print('Resposta do access_point_service:', response.status_code, response.text)
            if response.status_code == 201:
                if request.is_json:
                    return jsonify({"success": True, "message": "Ponto cadastrado com sucesso!"}), 201
                return redirect(url_for('routes.register'))
            else:
                return jsonify(response.json()), response.status_code
        except Exception as e:
            error_response, status_code = handle_error(e, "access_point_service")
            return jsonify(error_response), status_code

    try:
        points = session.get(f"{Config.ACCESS_POINT_SERVICE_URL}/access_points").json()
    except Exception:
        points = []

    try:
        map_html = session.get(f"{Config.MAP_SERVICE_URL}/map").text
    except Exception:
        map_html = "<p>Error loading map</p>"

    return render_template('pages/register.html', points=points, map_html=map_html)

@routes.route('/analysis', methods=['GET'])
def analysis():
    try:
        response = session.get(f"{Config.ACCESS_POINT_SERVICE_URL}/access_points")
        points = response.json() if response.status_code == 200 else []
    except Exception:
        points = []
    return render_template('pages/analysis.html', points=points)

@routes.route('/api/access_points', methods=['POST'])
def save_access_point():
    try:
        response = session.post(f"{Config.ACCESS_POINT_SERVICE_URL}/access_points", json=request.get_json())
        return jsonify(response.json()), response.status_code
    except Exception as e:
        error_response, status_code = handle_error(e, "access_point_service")
        return jsonify(error_response), status_code

@routes.route('/api/access_points/<id>', methods=['PUT'])
def update_access_point(id):
    try:
        response = session.put(f"{Config.ACCESS_POINT_SERVICE_URL}/access_points/{id}", json=request.get_json())
        return jsonify(response.json()), response.status_code
    except Exception as e:
        error_response, status_code = handle_error(e, "access_point_service")
        return jsonify(error_response), status_code