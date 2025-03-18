from flask import jsonify, send_file
import folium
import requests
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_map():
    m = folium.Map(location=[-24.061258, -52.386096], zoom_start=19)
    
    # Solicitar pontos de acesso do access_point_service
    try:
        response = requests.get('http://access_point_service:5000/access_points')
        response.raise_for_status()
        access_points = response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error retrieving access points: {e}")
        return jsonify({"message": "Error retrieving access points"}), 500
    
    # Adicionar pontos de acesso ao mapa
    if not access_points:
        logger.info("No access points found.")
    else:
        logger.info("Access points found:")
        for ap in access_points:
            logger.info(f"ID: {ap['id']}, Description: {ap['description']}, Latitude: {ap['latitude']}, Longitude: {ap['longitude']}, Frequency: {ap['frequency']}, Bandwidth: {ap['bandwidth']}, Channel: {ap['channel']}")
            folium.Marker(
                location=[ap['latitude'], ap['longitude']],
                popup=f"{ap['description']}<br>Frequency: {ap['frequency']}<br>Bandwidth: {ap['bandwidth']}<br>Channel: {ap['channel']}",
                icon=folium.Icon(icon="info-sign")
            ).add_to(m)
    
    map_path = os.path.join(os.getcwd(), "map.html")
    m.save(map_path)
    return send_file(map_path)