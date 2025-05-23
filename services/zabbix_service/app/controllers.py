import json
import logging
from pyzabbix import ZabbixAPI
from werkzeug.security import generate_password_hash
from flask import request, jsonify, current_app
import urllib3
import ssl
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from .models import db, ZabbixConfig

# Desabilita avisos SSL
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_url(url):
    """Valida URL"""
    if not url:
        return False
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None

def sanitize_input(text):
    """Limpa caracteres especiais"""
    if not text:
        return ""
    return ''.join(char for char in text if char.isprintable() and ord(char) < 128)

class ZabbixService:
    def __init__(self, url, user, password):
        if not url.startswith('https://'):
            url = 'https://' + url.lstrip('http://')
        
        self.url = url
        self.user = user
        self.password = password
        self.zapi = None
        self.logger = logging.getLogger(__name__)

    def authenticate(self):
        if self.zapi:
            return

        try:
            self.logger.info(f"📡 Conectando ao Zabbix: {self.url}")
            self.zapi = ZabbixAPI(self.url)
            self.zapi.session.verify = False
            self.zapi.login(self.user, self.password)
            self.logger.info("✅ Autenticado")
            version = self.zapi.api_version()
            self.logger.info(f"Versão API: {version}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro auth: {str(e)}")
            raise ValueError(f"Falha conexão: {str(e)}")

    def get_hosts(self):
        if not self.zapi:
            self.authenticate()
        return self.zapi.host.get(
            output=['hostid', 'host'],
            selectInterfaces=['interfaceid', 'ip']
        )

    def get_items(self, hostids):
        if not self.zapi:
            self.authenticate()
        return self.zapi.item.get(hostids=hostids, output='extend')

def test_zabbix_connection():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "JSON inválido"}), 400

        url = data.get('url')
        user = data.get('user')
        password = data.get('password')

        if not all([url, user, password]):
            logger.error(f"Dados: {data}")
            return jsonify({"success": False, "error": "Campos obrigatórios faltando"}), 400

        zabbix_service = ZabbixService(url.strip(), user.strip(), password.strip())
        zabbix_service.authenticate()
        
        return jsonify({
            "success": True,
            "message": "Conectado",
            "url": url
        })
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "details": "Verifique URL e acesso"
        }), 500

def get_all_hosts():
    try:
        config = ZabbixConfig.query.first()
        if not config:
            return jsonify({
                "success": False,
                "error": "Config não encontrada"
            }), 404

        zabbix_service = ZabbixService(config.url, config.user, config.password)
        hosts = zabbix_service.get_hosts()
        
        return jsonify({
            "success": True,
            "data": hosts
        })
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "details": "Verifique URL e acesso"
        }), 500

def save_zabbix_config():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "JSON inválido"}), 400

        url = data.get('url')
        user = data.get('user')
        password = data.get('password')

        if not all([url, user, password]):
            return jsonify({"success": False, "error": "Campos obrigatórios faltando"}), 400

        ZabbixConfig.query.delete()
        config = ZabbixConfig(
            url=url.strip(), 
            user=user.strip(), 
            password=generate_password_hash(password.strip())
        )
        db.session.add(config)
        db.session.commit()

        zabbix_service = ZabbixService(url.strip(), user.strip(), password.strip())
        zabbix_service.authenticate()
        
        return jsonify({
            "success": True,
            "message": "Configuração salva",
            "url": url
        })
    except Exception as e:
        if 'db' in locals():
            db.session.rollback()
        logger.error(f"❌ Erro: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "details": "Verifique URL e acesso"
        }), 500

def get_zabbix_config():
    try:
        config = ZabbixConfig.query.first()
        if not config:
            return jsonify({
                "success": False,
                "error": "Config não encontrada"
            }), 404

        return jsonify({
            "success": True,
            "data": {
                "url": config.url,
                "user": config.user
            }
        })
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
