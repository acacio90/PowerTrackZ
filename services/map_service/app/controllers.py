from flask import jsonify, send_file
import folium
import requests
import os
import logging
from app.config import Config

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format=Config.LOG_FORMAT
)
logger = logging.getLogger(__name__)

def get_map():
    m = folium.Map(location=[-24.061258, -52.386096], zoom_start=19)
    
    try:
        logger.info(f"Buscando pontos de acesso em {Config.ACCESS_POINT_SERVICE_URL}")
        response = requests.get(
            f"{Config.ACCESS_POINT_SERVICE_URL}/access_points",
            timeout=30
        )
        response.raise_for_status()
        access_points = response.json()
        logger.info(f"Pontos de acesso recebidos com sucesso: {len(access_points)}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao buscar pontos de acesso: {str(e)}")
        return jsonify({
            "message": "Erro ao buscar pontos de acesso",
            "error": str(e)
        }), 500
    
    if not access_points:
        logger.info("Nenhum ponto de acesso encontrado.")
    else:
        logger.info("Pontos de acesso encontrados:")
        for ap in access_points:
            logger.info(f"ID: {ap['id']}, Descrição: {ap['description']}, Latitude: {ap['latitude']}, Longitude: {ap['longitude']}, Frequência: {ap['frequency']}, Banda: {ap['bandwidth']}, Canal: {ap['channel']}")
            folium.Marker(
                location=[ap['latitude'], ap['longitude']],
                popup=f"{ap['description']}<br>Frequência: {ap['frequency']}<br>Banda: {ap['bandwidth']}<br>Canal: {ap['channel']}",
                icon=folium.Icon(icon="info-sign")
            ).add_to(m)
    
    map_path = os.path.join(os.getcwd(), "map.html")
    m.save(map_path)
    return send_file(map_path)