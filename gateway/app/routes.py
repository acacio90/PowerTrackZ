from flask import Blueprint, request, jsonify, render_template, redirect, url_for
import logging
import requests
from .config import Config

logger = logging.getLogger(__name__)
routes = Blueprint('routes', __name__)

session = requests.Session()
session.verify = False  # Ignora o SSL

def handle_error(e, service_name):
    error_msg = str(e)
    if isinstance(e, requests.exceptions.ConnectionError):
        logger.error(f"❌ Erro de conexão com {service_name}: {error_msg}")
        return {
            "message": f"Erro de conexão com o serviço {service_name}",
            "error": error_msg,
            "type": "connection_error"
        }, 503
    elif isinstance(e, requests.exceptions.Timeout):
        logger.error(f"⏰ Timeout ao conectar com {service_name}: {error_msg}")
        return {
            "message": f"Timeout ao conectar com o serviço {service_name}",
            "error": error_msg,
            "type": "timeout_error"
        }, 504
    else:
        logger.error(f"❌ Erro ao conectar com {service_name}: {error_msg}")
        return {
            "message": f"Erro ao conectar com o serviço {service_name}",
            "error": error_msg,
            "type": "request_error"
        }, 500

# Rota principal
@routes.route('/')
def index():
    """Página inicial"""
    logger.debug("📌 Acessando a página inicial")
    return render_template('pages/index.html')

# Rota de hosts do Zabbix
@routes.route('/hosts', methods=['GET'])
def hosts():
    """Lista os hosts do Zabbix"""
    try:
        logger.debug("📌 Buscando hosts do Zabbix")
        
        # Fazer requisição para o serviço Zabbix
        response = session.get(f"{Config.ZABBIX_SERVICE_URL}/hosts")
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                hosts = result.get("data", [])
                logger.debug(f"✅ Hosts recebidos com sucesso: {hosts}")
                return render_template('pages/hosts.html', hosts=hosts)
            else:
                logger.warning(f"⚠️ Erro ao buscar hosts: {result}")
                return render_template('pages/hosts.html', hosts=[], error=result)
        else:
            logger.warning(f"⚠️ Erro ao buscar hosts: {response.json()}")
            return render_template('pages/hosts.html', hosts=[], error=response.json())
    except Exception as e:
        error_response, status_code = handle_error(e, "Zabbix")
        logger.error(f"❌ Erro ao buscar hosts: {e}")
        return render_template('pages/hosts.html', hosts=[], error=error_response)

# Rotas do Zabbix
@routes.route('/zabbix/test-connection', methods=['POST'])
def test_zabbix_connection():
    """Testa a conexão com o serviço Zabbix"""
    try:
        logger.info("Testando conexão com o serviço Zabbix...")
        data = request.get_json() or {}
        response = session.post(
            f"{Config.ZABBIX_SERVICE_URL}/test-connection",
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        error_response, status_code = handle_error(e, "Zabbix")
        return jsonify(error_response), status_code

@routes.route('/zabbix/hosts', methods=['POST'])
def get_hosts():
    """Lista hosts do Zabbix"""
    try:
        logger.info("Buscando hosts do serviço Zabbix...")
        data = request.get_json() or {}
        response = session.post(
            f"{Config.ZABBIX_SERVICE_URL}/hosts",
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        error_response, status_code = handle_error(e, "Zabbix")
        return jsonify(error_response), status_code

@routes.route('/zabbix/save-config', methods=['POST'])
def save_config():
    """Salva a configuração do Zabbix"""
    try:
        logger.info("Salvando configuração do serviço Zabbix...")
        data = request.get_json()
        if not data:
            return jsonify({
                "message": "Dados de configuração são obrigatórios",
                "type": "validation_error"
            }), 400
        response = session.post(
            f"{Config.ZABBIX_SERVICE_URL}/save-config",
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        error_response, status_code = handle_error(e, "Zabbix")
        return jsonify(error_response), status_code

# Rotas do Mapa
@routes.route('/map', methods=['GET'])
def get_map():
    """Obtém o mapa com os pontos de acesso"""
    try:
        logger.debug("📌 Buscando mapa")
        response = session.get(f"{Config.MAP_SERVICE_URL}/map")
        if response.status_code == 200:
            logger.debug("✅ Mapa recebido com sucesso")
            return response.content, response.status_code, {'Content-Type': 'text/html'}
        else:
            logger.warning(f"⚠️ Erro ao carregar mapa: {response.json()}")
            return jsonify(response.json()), response.status_code
    except Exception as e:
        error_response, status_code = handle_error(e, "map_service")
        return jsonify(error_response), status_code

# Rotas de Análise
@routes.route('/analyze', methods=['GET'])
def analyze():
    """Análise dos dados"""
    try:
        logger.debug("📌 Solicitando análise ao serviço")
        response = session.get(f"{Config.ANALYSIS_SERVICE_URL}/analyze")
        logger.debug(f"✅ Resposta recebida: {response.status_code} - {response.json()}")
        return jsonify(response.json()), response.status_code
    except Exception as e:
        error_response, status_code = handle_error(e, "analysis_service")
        return jsonify(error_response), status_code

# Rotas de Pontos de Acesso
@routes.route('/access_points', methods=['GET'])
def get_access_points():
    """Obtém a lista de pontos de acesso"""
    try:
        logger.debug("🔍 Buscando pontos de acesso")
        response = session.get(f"{Config.ACCESS_POINT_SERVICE_URL}/access_points")
        logger.debug(f"✅ Resposta recebida: {response.status_code} - {response.json()}")
        return jsonify(response.json()), response.status_code
    except Exception as e:
        error_response, status_code = handle_error(e, "access_point_service")
        return jsonify(error_response), status_code

@routes.route('/register', methods=['GET', 'POST'])
def register():
    """Registra um novo ponto de acesso"""
    if request.method == 'POST':
        try:
            logger.debug("📌 Recebida solicitação POST para registrar ponto de acesso")
            data = {
                "description": request.form['description'],
                "latitude": request.form['latitude'],
                "longitude": request.form['longitude'],
                "frequency": request.form['frequency'],
                "bandwidth": request.form['bandwidth'],
                "channel": request.form['channel']
            }
            logger.debug(f"📡 Enviando dados para registro: {data}")
            response = session.post(
                f"{Config.ACCESS_POINT_SERVICE_URL}/register",
                json=data
            )
            logger.debug(f"✅ Resposta recebida: {response.status_code} - {response.json()}")

            if response.status_code == 201:
                logger.info("🎉 Ponto de acesso registrado com sucesso!")
                return redirect(url_for('routes.register'))
            else:
                logger.warning(f"⚠️ Erro ao registrar ponto de acesso: {response.json()}")
                return jsonify(response.json()), response.status_code
        except Exception as e:
            error_response, status_code = handle_error(e, "access_point_service")
            return jsonify(error_response), status_code

    # GET request - renderiza o formulário
    try:
        logger.debug("📌 Carregando a página de registro")
        response = session.get(f"{Config.ACCESS_POINT_SERVICE_URL}/access_points")
        access_points = response.json()
        logger.debug(f"✅ Pontos de acesso recebidos: {access_points}")
    except Exception as e:
        logger.error(f"❌ Erro ao buscar pontos de acesso: {e}")
        access_points = []

    try:
        map_response = session.get(f"{Config.MAP_SERVICE_URL}/map")
        if map_response.status_code == 200:
            map_html = map_response.text
            logger.debug("✅ Mapa carregado com sucesso")
        else:
            map_html = "<p>Error loading map</p>"
            logger.warning("⚠️ Erro ao carregar o mapa")
    except Exception as e:
        logger.error(f"❌ Erro ao conectar ao serviço de mapas: {e}")
        map_html = "<p>Error connecting to map service</p>"

    return render_template('pages/register.html', access_points=access_points, map_html=map_html) 