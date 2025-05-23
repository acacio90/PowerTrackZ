from flask import Blueprint, request, jsonify, render_template, redirect, url_for
import logging
import requests
from .config import Config

# Configuração inicial
logger = logging.getLogger(__name__)
routes = Blueprint('routes', __name__)
session = requests.Session()
session.verify = False

# Função para tratamento de erros
def handle_error(e, service_name):
    error_msg = str(e)
    if isinstance(e, requests.exceptions.ConnectionError):
        return {"message": f"Erro de conexão com {service_name}", "error": error_msg}, 503
    elif isinstance(e, requests.exceptions.Timeout):
        return {"message": f"Timeout ao conectar com {service_name}", "error": error_msg}, 504
    else:
        return {"message": f"Erro ao conectar com {service_name}", "error": error_msg}, 500

# Rota principal
@routes.route('/')
def index():
    return render_template('pages/index.html')

# Rota para listar hosts do Zabbix
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

# Rotas da API do Zabbix
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

# Rota do mapa
@routes.route('/map', methods=['GET'])
def get_map():
    try:
        response = session.get(f"{Config.MAP_SERVICE_URL}/map")
        return response.content, response.status_code, {'Content-Type': 'text/html'}
    except Exception as e:
        error_response, status_code = handle_error(e, "map_service")
        return jsonify(error_response), status_code

# Rota de análise
@routes.route('/analyze', methods=['GET'])
def analyze():
    try:
        response = session.get(f"{Config.ANALYSIS_SERVICE_URL}/analyze")
        return jsonify(response.json()), response.status_code
    except Exception as e:
        error_response, status_code = handle_error(e, "analysis_service")
        return jsonify(error_response), status_code

# Rotas de pontos de acesso
@routes.route('/access_points', methods=['GET'])
def get_access_points():
    try:
        response = session.get(f"{Config.ACCESS_POINT_SERVICE_URL}/access_points")
        return jsonify(response.json()), response.status_code
    except Exception as e:
        error_response, status_code = handle_error(e, "access_point_service")
        return jsonify(error_response), status_code

# Rota de registro de pontos de acesso
@routes.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            data = {
                "description": request.form['description'],
                "latitude": request.form['latitude'],
                "longitude": request.form['longitude'],
                "frequency": request.form['frequency'],
                "bandwidth": request.form['bandwidth'],
                "channel": request.form['channel']
            }
            response = session.post(f"{Config.ACCESS_POINT_SERVICE_URL}/register", json=data)
            return redirect(url_for('routes.register')) if response.status_code == 201 else jsonify(response.json())
        except Exception as e:
            error_response, status_code = handle_error(e, "access_point_service")
            return jsonify(error_response), status_code

    # Carrega dados para o formulário GET
    try:
        points = session.get(f"{Config.ACCESS_POINT_SERVICE_URL}/access_points").json()
    except Exception:
        points = []

    try:
        map_html = session.get(f"{Config.MAP_SERVICE_URL}/map").text
    except Exception:
        map_html = "<p>Error loading map</p>"

    return render_template('pages/register.html', points=points, map_html=map_html)