from flask import request, jsonify
from models import db, AccessPoint
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tables():
    db.create_all()

def register():
    try:
        data = request.get_json()
        new_ap = AccessPoint(**data)
        db.session.add(new_ap)
        db.session.commit()
        logger.info(f"Registered new access point: {new_ap.description} at ({new_ap.latitude}, {new_ap.longitude})")
        return jsonify({"message": "Access point registered successfully"}), 201
    except Exception as e:
        logger.error(f"Error registering access point: {e}")
        return jsonify({"message": "Error registering access point"}), 500
    
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
        logger.error(f"Error retrieving access points: {e}")
        return jsonify({"message": "Error retrieving access points"}), 500