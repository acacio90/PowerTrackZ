from flask import Flask, jsonify, request
from models import db, AccessPoint
from controllers import AccessPointController, create_tables
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///access_points.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.before_first_request
def init_db():
    create_tables()

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "access_point_service",
        "port": int(os.environ.get('PORT', 5004))
    })

@app.route('/hosts', methods=['GET'])
def list_hosts():
    try:
        controller = AccessPointController()
        return controller.list_hosts()
    except Exception as e:
        logger.error(f"Erro ao listar hosts: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/hosts/<host_id>', methods=['GET'])
def get_host_details(host_id):
    try:
        controller = AccessPointController()
        return controller.get_host_details(host_id)
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes do host: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/sync/zabbix', methods=['POST'])
def sync_zabbix():
    try:
        controller = AccessPointController()
        return controller.sync_zabbix_data()
    except Exception as e:
        logger.error(f"Erro na sincronização: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/access_points', methods=['POST'])
def create_access_point():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dados obrigatórios não enviados"}), 400

        ap = AccessPoint.query.get(data.get('id'))
        if ap:
            ap.name = data.get('name')
            ap.channel = data.get('channel')
            ap.frequency = data.get('frequency')
            ap.bandwidth = data.get('bandwidth')
            ap.latitude = data.get('latitude')
            ap.longitude = data.get('longitude')
            ap.last_update = datetime.utcnow()
        else:
            ap = AccessPoint(
                id=data.get('id'),
                name=data.get('name'),
                channel=data.get('channel'),
                frequency=data.get('frequency'),
                bandwidth=data.get('bandwidth'),
                latitude=data.get('latitude'),
                longitude=data.get('longitude'),
                last_update=datetime.utcnow()
            )
            db.session.add(ap)
        db.session.commit()
        return jsonify({"success": True, "message": "Ponto de acesso salvo/atualizado com sucesso!"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/access_points', methods=['GET'])
def get_access_points():
    try:
        aps = AccessPoint.query.all()
        return jsonify([{
            'id': ap.id,
            'name': ap.name,
            'channel': ap.channel,
            'frequency': ap.frequency,
            'bandwidth': ap.bandwidth,
            'latitude': ap.latitude,
            'longitude': ap.longitude,
            'last_update': ap.last_update.isoformat() if ap.last_update else None
        } for ap in aps])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/access_points/<id>', methods=['PUT'])
def update_access_point(id):
    try:
        data = request.get_json()
        ap = AccessPoint.query.get(id)
        if not ap:
            return jsonify({"error": "Ponto de acesso não encontrado"}), 404
            
        ap.name = data.get('name', ap.name)
        ap.channel = data.get('channel', ap.channel)
        ap.frequency = data.get('frequency', ap.frequency)
        ap.bandwidth = data.get('bandwidth', ap.bandwidth)
        ap.latitude = data.get('latitude', ap.latitude)
        ap.longitude = data.get('longitude', ap.longitude)
        ap.last_update = datetime.utcnow()
        
        db.session.commit()
        return jsonify({"success": True, "message": "Ponto de acesso atualizado com sucesso!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5004))
    app.run(host='0.0.0.0', port=port, debug=True)