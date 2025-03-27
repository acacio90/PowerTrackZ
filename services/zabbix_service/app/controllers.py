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

# Desabilitar avisos de SSL
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_url(url):
    """Valida se a URL está em um formato correto"""
    if not url:
        return False
    url_pattern = re.compile(
        r'^https?://'  # http:// ou https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domínio
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # porta opcional
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None

def sanitize_input(text):
    """Remove caracteres especiais"""
    if not text:
        return ""
    # Remove caracteres e mantém apenas caracteres ASCII
    return ''.join(char for char in text if char.isprintable() and ord(char) < 128)

class ZabbixService:
    def __init__(self, url, user, password):
        # Garantir que a URL começa com https://
        if not url.startswith('https://'):
            url = 'https://' + url.lstrip('http://')
        
        self.url = url
        self.user = user
        self.password = password
        self.zapi = None
        self.logger = logging.getLogger(__name__)

    def authenticate(self):
        if self.zapi:
            return  # Evita múltiplas autenticações

        try:
            self.logger.info(f"📡 Tentando conectar ao Zabbix em: {self.url}")

            self.zapi = ZabbixAPI(self.url)
            
            self.zapi.session.verify = False
            
            # Tentar autenticação
            self.zapi.login(self.user, self.password)
            self.logger.info("✅ Autenticação realizada com sucesso")
            
            # Testar a conexão obtendo a versão da API
            version = self.zapi.api_version()
            self.logger.info(f"Versão da API do Zabbix: {version}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao fazer autenticação: {str(e)}")
            raise ValueError(f"Falha ao conectar à API do Zabbix: {str(e)}")

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

# Função para testar a conexão com o Zabbix
def test_zabbix_connection():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Dados JSON inválidos ou ausentes"}), 400

        url = data.get('url')
        user = data.get('user')
        password = data.get('password')

        if not all([url, user, password]):
            logger.error(f"Dados recebidos: {data}")
            return jsonify({"success": False, "error": "Campos obrigatórios ausentes"}), 400

        url = url.strip()
        user = user.strip()
        password = password.strip()

        logger.info(f"Tentando conectar com URL: {url}")
        zabbix_service = ZabbixService(url, user, password)
        zabbix_service.authenticate()
        
        return jsonify({
            "success": True,
            "message": "Conexão estabelecida com sucesso",
            "url": url
        })
    except json.JSONDecodeError:
        return jsonify({"success": False, "error": "JSON inválido"}), 400
    except Exception as e:
        logger.error(f"❌ Erro ao testar conexão: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "details": "Verifique se a URL do Zabbix está correta e se o servidor está acessível"
        }), 500

# Função para obter todos os hosts
def get_all_hosts():
    try:
        # Buscar configuração do banco
        config = ZabbixConfig.query.first()
        if not config:
            return jsonify({
                "success": False,
                "error": "Configuração do Zabbix não encontrada"
            }), 404

        url = config.url
        user = config.user
        password = config.password

        logger.info(f"Tentando obter hosts de: {url}")
        zabbix_service = ZabbixService(url, user, password)
        hosts = zabbix_service.get_hosts()
        
        return jsonify({
            "success": True,
            "data": hosts
        })
    except Exception as e:
        logger.error(f"❌ Erro ao obter hosts: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "details": "Verifique se a URL do Zabbix está correta e se o servidor está acessível"
        }), 500

# Função para salvar a configuração do Zabbix
def save_zabbix_config():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Dados JSON inválidos ou ausentes"}), 400

        url = data.get('url')
        user = data.get('user')
        password = data.get('password')

        if not all([url, user, password]):
            return jsonify({"success": False, "error": "Campos obrigatórios ausentes"}), 400

        url = url.strip()
        user = user.strip()
        password = password.strip()

        logger.info(f"Tentando conectar com URL: {url}")

        ZabbixConfig.query.delete()
        
        config = ZabbixConfig(url=url, user=user, password=password)
        db.session.add(config)
        db.session.commit()

        zabbix_service = ZabbixService(url, user, password)
        zabbix_service.authenticate()
        
        return jsonify({
            "success": True,
            "message": "Configuração salva e conexão estabelecida com sucesso",
            "url": url
        })
    except json.JSONDecodeError:
        return jsonify({"success": False, "error": "JSON inválido"}), 400
    except Exception as e:
        if 'db' in locals():
            db.session.rollback()
        logger.error(f"❌ Erro ao salvar configuração: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "details": "Verifique se a URL do Zabbix está correta e se o servidor está acessível"
        }), 500

def get_zabbix_config():
    try:
        config = ZabbixConfig.query.first()
        if not config:
            return jsonify({
                "success": False,
                "error": "Configuração do Zabbix não encontrada"
            }), 404

        return jsonify({
            "success": True,
            "data": {
                "url": config.url,
                "user": config.user
            }
        })
    except Exception as e:
        logger.error(f"❌ Erro ao obter configuração: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
