from flask import jsonify, send_file
import folium
import requests
import os
import logging
import tempfile
from app.config import Config

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format=Config.LOG_FORMAT
)
logger = logging.getLogger(__name__)

def get_map():
    # Criar mapa com folium
    m = folium.Map(
        location=[-24.061258, -52.386096],
        zoom_start=4,
        control_scale=True,
        prefer_canvas=True,
        height='100%',
        width='100%'
    )
    
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
        logger.info("Adicionando pontos de acesso ao mapa:")
        for ap in access_points:
            try:
                lat = float(ap['latitude'])
                lng = float(ap['longitude'])
                logger.info(f"Ponto: {ap['description']} em ({lat}, {lng})")
                folium.Marker(
                    location=[lat, lng],
                    popup=f"{ap['description']}<br>Frequência: {ap['frequency']} GHz<br>Banda: {ap['bandwidth']} MHz<br>Canal: {ap['channel']}",
                    icon=folium.Icon(icon="info-sign")
                ).add_to(m)
            except Exception as e:
                logger.error(f"Erro ao adicionar ponto {ap.get('id')}: {str(e)}")
    
    # Criar arquivo temporário para o mapa
    with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp:
        # Salvar o mapa no arquivo temporário
        m.save(tmp.name)
        tmp_path = tmp.name
    
    # Adicionar CSS personalizado para melhorar a aparência do mapa
    with open(tmp_path, 'r') as f:
        content = f.read()
    
    # Inserir CSS para garantir que o mapa ocupe todo o espaço disponível
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
    
    # Salvar o conteúdo modificado
    with open(tmp_path, 'w') as f:
        f.write(content)
    
    # Enviar o arquivo como resposta e depois removê-lo
    try:
        response = send_file(
            tmp_path,
            mimetype='text/html'
        )
        return response
    finally:
        # Remover o arquivo temporário após o envio
        try:
            os.unlink(tmp_path)
        except:
            pass