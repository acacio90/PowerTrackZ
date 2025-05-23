# Importações necessárias
from flask import request, jsonify
from models import db, AccessPoint
import logging

# Configuração básica de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cria as tabelas no banco
def create_tables():
    db.create_all()

# Registra um novo ponto de acesso
def register():
    try:
        data = request.get_json()
        new_ap = AccessPoint(**data)
        db.session.add(new_ap)
        db.session.commit()
        logger.info(f"Novo AP registrado: {new_ap.description}")
        return jsonify({"message": "Access point registered successfully"}), 201
    except Exception as e:
        logger.error(f"Erro ao registrar AP: {e}")
        return jsonify({"message": "Error registering access point"}), 500
    
# Retorna lista de pontos de acesso
def get_access_points():
    try:
        access_points = AccessPoint.query.all()
        return jsonify([{
            "id": ap.id,
            "description": ap.description, 
            "latitude": ap.latitude,
            "longitude": ap.longitude,
            "frequency": ap.frequency,
            "bandwidth": ap.bandwidth,
            "channel": ap.channel
        } for ap in access_points]), 200
    except Exception as e:
        logger.error(f"Erro ao buscar APs: {e}")
        return jsonify({"message": "Error retrieving access points"}), 500