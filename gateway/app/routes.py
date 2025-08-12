from flask import Blueprint, request, jsonify, redirect
import requests
from .config import Config
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração da sessão HTTP
session = requests.Session()
session.timeout = 30
session.verify = False  # Desabilita verificação SSL para certificados auto-assinados

routes = Blueprint('routes', __name__)

def handle_error(error, service_name):
    """Função para tratar erros de forma consistente"""
    logger.error(f"Erro no {service_name}: {str(error)}")
    if isinstance(error, requests.exceptions.ConnectionError):
        return {"message": f"Serviço {service_name} não está disponível"}, 503
    elif isinstance(error, requests.exceptions.Timeout):
        return {"message": f"Timeout ao conectar com {service_name}"}, 504
    else:
        return {"message": f"Erro interno no {service_name}", "error": str(error)}, 500

# ===== HEALTH CHECK =====
@routes.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "service": "gateway",
        "port": 80
    })

# ===== ZABBIX SERVICE ROUTES =====
@routes.route('/api/zabbix/test-connection', methods=['POST'])
@routes.route('/zabbix/test-connection', methods=['POST'])
def test_zabbix_connection():
    try:
        response = session.post(f"{Config.ZABBIX_SERVICE_URL}/test-connection", json=request.get_json())
        return response.json(), response.status_code
    except Exception as e:
        error_response, status_code = handle_error(e, "Zabbix")
        return jsonify(error_response), status_code

@routes.route('/api/zabbix/hosts', methods=['GET', 'POST'])
@routes.route('/zabbix/hosts', methods=['GET', 'POST'])
def zabbix_hosts():
    try:
        if request.method == 'GET':
            response = session.get(f"{Config.ZABBIX_SERVICE_URL}/hosts")
        else:
        response = session.post(f"{Config.ZABBIX_SERVICE_URL}/hosts", json=request.get_json() or {})
        return response.json(), response.status_code
    except Exception as e:
        error_response, status_code = handle_error(e, "Zabbix")
        return jsonify(error_response), status_code

@routes.route('/api/zabbix/save-config', methods=['POST'])
@routes.route('/zabbix/save-config', methods=['POST'])
def save_zabbix_config():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Dados obrigatórios"}), 400
        response = session.post(f"{Config.ZABBIX_SERVICE_URL}/save-config", json=data)
        return response.json(), response.status_code
    except Exception as e:
        error_response, status_code = handle_error(e, "Zabbix")
        return jsonify(error_response), status_code

# ===== MAP SERVICE ROUTES =====
@routes.route('/api/map', methods=['GET'])
def get_map():
    try:
        response = session.get(f"{Config.MAP_SERVICE_URL}/map")
        return response.content, response.status_code, {'Content-Type': 'text/html'}
    except Exception as e:
        error_response, status_code = handle_error(e, "map_service")
        return jsonify(error_response), status_code

@routes.route('/api/map/points', methods=['GET'])
def get_map_points():
    try:
        response = session.get(f"{Config.MAP_SERVICE_URL}/points")
        return response.json(), response.status_code
    except Exception as e:
        error_response, status_code = handle_error(e, "map_service")
        return jsonify(error_response), status_code

# ===== ANALYSIS SERVICE ROUTES =====
@routes.route('/api/analysis/analyze', methods=['GET'])
def analyze():
    try:
        response = session.get(f"{Config.ANALYSIS_SERVICE_URL}/analyze")
        return response.json(), response.status_code
    except Exception as e:
        error_response, status_code = handle_error(e, "analysis_service")
        return jsonify(error_response), status_code

@routes.route('/api/analysis/strategies', methods=['GET'])
def get_analysis_strategies():
    """Retorna as estratégias de análise disponíveis"""
    try:
        response = session.get(f"{Config.ANALYSIS_SERVICE_URL}/strategies")
        return response.json(), response.status_code
    except Exception as e:
        error_response, status_code = handle_error(e, "analysis_service")
        return jsonify(error_response), status_code

@routes.route('/api/analysis/analyze-graph', methods=['POST'])
def analyze_graph():
    """Análise de grafos com estratégias configuráveis"""
    try:
        response = session.post(f"{Config.ANALYSIS_SERVICE_URL}/analyze-graph", json=request.get_json())
        return response.json(), response.status_code
        except Exception as e:
        error_response, status_code = handle_error(e, "analysis_service")
            return jsonify(error_response), status_code

@routes.route('/api/analysis/compare-strategies', methods=['POST'])
def compare_strategies():
    """Compara diferentes estratégias de análise"""
    try:
        response = session.post(f"{Config.ANALYSIS_SERVICE_URL}/compare-strategies", json=request.get_json())
        return response.json(), response.status_code
    except Exception as e:
        error_response, status_code = handle_error(e, "analysis_service")
        return jsonify(error_response), status_code

@routes.route('/api/analysis/collision-graph', methods=['POST'])
def collision_graph():
    try:
        response = session.post(f"{Config.ANALYSIS_SERVICE_URL}/collision-graph", json=request.get_json())
        return response.json(), response.status_code
    except Exception as e:
        error_response, status_code = handle_error(e, "analysis_service")
        return jsonify(error_response), status_code

# ===== ACCESS POINT SERVICE ROUTES =====
@routes.route('/api/access_points', methods=['GET', 'POST'])
def access_points():
    try:
        if request.method == 'GET':
        response = session.get(f"{Config.ACCESS_POINT_SERVICE_URL}/access_points")
        else:
            response = session.post(f"{Config.ACCESS_POINT_SERVICE_URL}/access_points", json=request.get_json())
        return response.json(), response.status_code
    except Exception as e:
        error_response, status_code = handle_error(e, "access_point_service")
        return jsonify(error_response), status_code

@routes.route('/api/access_points/<id>', methods=['GET', 'PUT', 'DELETE'])
def access_point_by_id(id):
    try:
        if request.method == 'GET':
            response = session.get(f"{Config.ACCESS_POINT_SERVICE_URL}/access_points/{id}")
        elif request.method == 'PUT':
            response = session.put(f"{Config.ACCESS_POINT_SERVICE_URL}/access_points/{id}", json=request.get_json())
        else:  # DELETE
            response = session.delete(f"{Config.ACCESS_POINT_SERVICE_URL}/access_points/{id}")
        return response.json(), response.status_code
    except Exception as e:
        error_response, status_code = handle_error(e, "access_point_service")
        return jsonify(error_response), status_code

@routes.route('/api/access_points/sync/zabbix', methods=['POST'])
def sync_zabbix_access_points():
    try:
        response = session.post(f"{Config.ACCESS_POINT_SERVICE_URL}/sync/zabbix", json=request.get_json() or {})
        return response.json(), response.status_code
    except Exception as e:
        error_response, status_code = handle_error(e, "access_point_service")
        return jsonify(error_response), status_code

# ===== FRONTEND SERVICE ROUTES =====
# Rota específica para assets estáticos
@routes.route('/static/css/<path:filename>')
def static_css_files(filename):
    """Redireciona CSS para o frontend service"""
    logger.info(f"Tentando acessar CSS: {filename}")
    try:
        frontend_url = f"{Config.FRONTEND_SERVICE_URL}/static/css/{filename}"
        logger.info(f"Redirecionando para: {frontend_url}")
        response = session.get(frontend_url)
        logger.info(f"Resposta do frontend: {response.status_code}")
        return response.content, response.status_code, {'Content-Type': 'text/css'}
    except Exception as e:
        logger.error(f"Erro ao redirecionar CSS {filename}: {str(e)}")
        return jsonify({"message": "Erro ao acessar CSS"}), 500

@routes.route('/static/js/<path:filename>')
def static_js_files(filename):
    """Redireciona JavaScript para o frontend service"""
    logger.info(f"Tentando acessar JS: {filename}")
    try:
        frontend_url = f"{Config.FRONTEND_SERVICE_URL}/static/js/{filename}"
        logger.info(f"Redirecionando para: {frontend_url}")
        response = session.get(frontend_url)
        logger.info(f"Resposta do frontend: {response.status_code}")
        return response.content, response.status_code, {'Content-Type': 'application/javascript'}
    except Exception as e:
        logger.error(f"Erro ao redirecionar JS {filename}: {str(e)}")
        return jsonify({"message": "Erro ao acessar JavaScript"}), 500

@routes.route('/static/<path:filename>')
def static_files(filename):
    """Redireciona outros assets estáticos para o frontend service"""
    try:
        frontend_url = f"{Config.FRONTEND_SERVICE_URL}/static/{filename}"
        response = session.get(frontend_url)
        
        # Determina o tipo MIME baseado na extensão do arquivo
        content_type = 'text/plain'  # padrão
        if filename.endswith('.png'):
            content_type = 'image/png'
        elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
            content_type = 'image/jpeg'
        elif filename.endswith('.gif'):
            content_type = 'image/gif'
        elif filename.endswith('.svg'):
            content_type = 'image/svg+xml'
        elif filename.endswith('.ico'):
            content_type = 'image/x-icon'
        elif filename.endswith('.woff'):
            content_type = 'font/woff'
        elif filename.endswith('.woff2'):
            content_type = 'font/woff2'
        elif filename.endswith('.ttf'):
            content_type = 'font/ttf'
        elif filename.endswith('.eot'):
            content_type = 'application/vnd.ms-fontobject'
        
        return response.content, response.status_code, {'Content-Type': content_type}
    except Exception as e:
        logger.error(f"Erro ao redirecionar asset estático {filename}: {str(e)}")
        return jsonify({"message": "Erro ao acessar asset estático"}), 500

# O gateway agora redireciona para o frontend service
@routes.route('/', defaults={'path': ''})
@routes.route('/<path:path>')
def frontend_proxy(path):
    """Redireciona todas as requisições frontend para o frontend service"""
    try:
        # Se for uma requisição para API, não redireciona
        if path.startswith('api/'):
            return jsonify({"message": "Endpoint não encontrado"}), 404
        
        # Redireciona para o frontend service
        frontend_url = f"{Config.FRONTEND_SERVICE_URL}/{path}"
        response = session.get(frontend_url)
        
        # Determina o tipo MIME baseado na extensão do arquivo
        content_type = 'text/html'  # padrão
        if path.endswith('.css'):
            content_type = 'text/css'
        elif path.endswith('.js'):
            content_type = 'application/javascript'
        elif path.endswith('.png'):
            content_type = 'image/png'
        elif path.endswith('.jpg') or path.endswith('.jpeg'):
            content_type = 'image/jpeg'
        elif path.endswith('.gif'):
            content_type = 'image/gif'
        elif path.endswith('.svg'):
            content_type = 'image/svg+xml'
        elif path.endswith('.ico'):
            content_type = 'image/x-icon'
        elif path.endswith('.woff'):
            content_type = 'font/woff'
        elif path.endswith('.woff2'):
            content_type = 'font/woff2'
        elif path.endswith('.ttf'):
            content_type = 'font/ttf'
        elif path.endswith('.eot'):
            content_type = 'application/vnd.ms-fontobject'
        
        return response.content, response.status_code, {'Content-Type': content_type}
    except Exception as e:
        logger.error(f"Erro ao redirecionar para frontend: {str(e)}")
        return jsonify({"message": "Erro ao acessar frontend"}), 500