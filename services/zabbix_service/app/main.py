from flask import request, jsonify
import logging
import os
import sys
from pathlib import Path
from controllers import test_zabbix_connection, save_zabbix_config, get_all_hosts
from app import app, db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.before_request
def before_request():
    logger.info(f"Requisição recebida: {request.method} {request.url}")
    logger.info(f"Headers: {dict(request.headers)}")
    if request.is_json:
        logger.info(f"Body: {request.get_json()}")

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "zabbix_service",
        "port": int(os.environ.get('PORT', 5003))
    })

@app.route('/test-connection', methods=['POST'])
def test_connection():
    return test_zabbix_connection()

@app.route('/hosts', methods=['POST'])
def hosts():
    return get_all_hosts()

@app.route('/save-config', methods=['POST'])
def save_config():
    return save_zabbix_config()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5003))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Iniciando servidor na porta {port} com host {host}")
    
    ssl_dir = Path(__file__).parent.parent / 'ssl'
    ssl_dir.mkdir(exist_ok=True)
    
    cert_path = ssl_dir / 'cert.pem'
    key_path = ssl_dir / 'key.pem'
    
    if not (cert_path.exists() and key_path.exists()):
        logger.info("Gerando certificados SSL auto-assinados...")
        os.system(f'openssl req -x509 -newkey rsa:4096 -nodes -out {cert_path} -keyout {key_path} -days 365 -subj "/CN=localhost"')
    
    with app.app_context():
        db.create_all()
    
    app.run(
        host=host,
        port=port,
        debug=debug,
        ssl_context=(str(cert_path), str(key_path))
    )