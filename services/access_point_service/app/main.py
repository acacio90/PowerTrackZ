# Importações necessárias
from flask import Flask, jsonify, request
from models import db
from controllers import AccessPointController, create_tables
import os
import logging

# Configuração básica de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializa app Flask e configura banco
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///access_points.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Cria tabelas antes da primeira requisição
@app.before_first_request
def init_db():
    create_tables()

# Rota de healthcheck
@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "access_point_service",
        "port": int(os.environ.get('PORT', 5004))
    })

# Rota para listar hosts (pontos de acesso)
@app.route('/hosts', methods=['GET'])
def list_hosts():
    try:
        controller = AccessPointController()
        return controller.list_hosts()
    except Exception as e:
        logger.error(f"Erro ao listar hosts: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Rota para detalhes de um host (ponto de acesso)
@app.route('/hosts/<host_id>', methods=['GET'])
def get_host_details(host_id):
    try:
        controller = AccessPointController()
        return controller.get_host_details(host_id)
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes do host: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Rota para sincronização com Zabbix
@app.route('/sync/zabbix', methods=['POST'])
def sync_zabbix():
    try:
        controller = AccessPointController()
        return controller.sync_zabbix_data()
    except Exception as e:
        logger.error(f"Erro na sincronização: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Inicia a aplicação
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5004))
    app.run(host='0.0.0.0', port=port, debug=True)