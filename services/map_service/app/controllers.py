from flask import jsonify, send_file
import folium
import requests
import os
import logging
import tempfile
from app.config import Config

# Configuração básica de logging
logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL), format=Config.LOG_FORMAT)
logger = logging.getLogger(__name__)

def get_map():
    """Retorna o mapa HTML completo"""
    return create_map_html()

def get_map_points():
    """Retorna apenas os pontos de acesso em formato JSON"""
    try:
        response = requests.get(f"{Config.ACCESS_POINT_SERVICE_URL}/access_points", timeout=30)
        response.raise_for_status()
        access_points = response.json()
        return jsonify(access_points)
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao buscar pontos de acesso: {str(e)}")
        return jsonify({"message": "Erro ao buscar pontos de acesso", "error": str(e)}), 500

def create_map_html(center_lat=-24.061258, center_lng=-52.386096, zoom=4):
    """Cria mapa HTML com pontos de acesso"""
    # Cria mapa base com folium
    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=zoom,
        control_scale=True,
        prefer_canvas=True,
        height='100%',
        width='100%'
    )
    
    # Busca pontos de acesso da API
    try:
        response = requests.get(f"{Config.ACCESS_POINT_SERVICE_URL}/access_points", timeout=30)
        response.raise_for_status()
        access_points = response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao buscar pontos de acesso: {str(e)}")
        return jsonify({"message": "Erro ao buscar pontos de acesso", "error": str(e)}), 500
    
    # Adiciona marcadores para cada ponto de acesso
    if access_points:
        for ap in access_points:
            try:
                if ap.get('latitude') and ap.get('longitude'):
                lat, lng = float(ap['latitude']), float(ap['longitude'])
                    
                    # Cria popup com informações do ponto
                    popup_content = f"""
                    <div style="min-width: 200px;">
                        <h4>{ap.get('name', 'Ponto de Acesso')}</h4>
                        <p><strong>Frequência:</strong> {ap.get('frequency', 'N/A')} GHz</p>
                        <p><strong>Banda:</strong> {ap.get('bandwidth', 'N/A')} MHz</p>
                        <p><strong>Canal:</strong> {ap.get('channel', 'N/A')}</p>
                        <p><strong>Coordenadas:</strong> {lat}, {lng}</p>
                    </div>
                    """
                    
                folium.Marker(
                    location=[lat, lng],
                        popup=folium.Popup(popup_content, max_width=300),
                        icon=folium.Icon(icon="wifi", color="blue")
                ).add_to(m)
            except Exception as e:
                logger.error(f"Erro ao adicionar ponto {ap.get('id')}: {str(e)}")
    
    # Salva mapa em arquivo temporário
    with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp:
        m.save(tmp.name)
        tmp_path = tmp.name
    
    # Adiciona CSS para ocupar tela inteira
    with open(tmp_path, 'r') as f:
        content = f.read()
    
    custom_css = """
    <style>
        html, body {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
        }
        .folium-map {
            width: 100%;
            height: 100%;
            z-index: 1;
        }
        .leaflet-container {
            width: 100% !important;
            height: 100% !important;
        }
        .leaflet-popup-content {
            font-family: Arial, sans-serif;
        }
    </style>
    """
    content = content.replace('</head>', f'{custom_css}</head>')
    
    with open(tmp_path, 'w') as f:
        f.write(content)
    
    # Retorna arquivo HTML e remove temporário
    try:
        response = send_file(tmp_path, mimetype='text/html')
        return response
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass