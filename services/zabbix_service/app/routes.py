from flask import Blueprint, request, jsonify
import logging
from .controllers import test_zabbix_connection, save_zabbix_config, get_all_hosts, get_zabbix_config, get_all_groups

logger = logging.getLogger(__name__)

routes = Blueprint('routes', __name__)

@routes.before_request
def before_request():
    logger.info(f"Requisição recebida: {request.method} {request.url}")
    logger.info(f"Headers: {dict(request.headers)}")
    if request.is_json:
        logger.info(f"Body: {request.get_json()}")

@routes.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "zabbix_service",
        "port": 5003
    })

@routes.route('/test-connection', methods=['POST'])
def test_connection():
    return test_zabbix_connection()

@routes.route('/hosts', methods=['GET'])
def hosts():
    return get_all_hosts()

@routes.route('/save-config', methods=['POST'])
def save_config():
    return save_zabbix_config()

@routes.route('/config', methods=['GET'])
def config():
    return get_zabbix_config()

@routes.route('/groups', methods=['GET'])
def groups():
    return get_all_groups() 