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
    # Cria mapa base com folium
    m = folium.Map(
        location=[-24.061258, -52.386096],
        zoom_start=4,
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
                lat, lng = float(ap['latitude']), float(ap['longitude'])
                folium.Marker(
                    location=[lat, lng],
                    popup=f"{ap['description']}<br>Frequência: {ap['frequency']} GHz<br>Banda: {ap['bandwidth']} MHz<br>Canal: {ap['channel']}",
                    icon=folium.Icon(icon="info-sign")
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