import logging
import re
from pyzabbix import ZabbixAPI
from flask import request, jsonify
import urllib3
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from .models import db, ZabbixConfig

# Desabilita avisos SSL
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_url(url):
    """Valida formato da URL"""
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

class ZabbixService:
    def __init__(self, url, user, password):
        if not url or not validate_url(url):
            raise ValueError("URL inválida")
            
        if not url.startswith('https://'):
            url = 'https://' + url.lstrip('http://')
        
        self.url = url
        self.user = user
        self.password = password
        self.zapi = None
        self.logger = logging.getLogger(__name__)

    def authenticate(self):
        """Autentica no Zabbix"""
        if self.zapi:
            return True

        try:
            self.logger.info(f"Conectando ao Zabbix: {self.url}")
            self.zapi = ZabbixAPI(self.url)
            self.zapi.session.verify = False
            self.zapi.login(self.user, self.password)
            self.logger.info(f"Conectado - API v{self.zapi.api_version()}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro auth: {str(e)}")
            if "Login name or password is incorrect" in str(e):
                raise ValueError("Credenciais inválidas")
            elif "Connection refused" in str(e):
                raise ValueError("Servidor Zabbix indisponível")
            else:
                raise ValueError(f"Erro na autenticação: {str(e)}")

    def get_hosts(self):
        """Busca hosts e seus itens"""
        if not self.zapi:
            self.authenticate()
        
        try:
            hosts = self.zapi.host.get(
                output=['hostid', 'host', 'name'],
                selectInterfaces=['interfaceid', 'ip'],
                selectItems=['snmpindex', 'itemid', 'name', 'key_', 'lastvalue'],
                groupids=["28"]
            )
            
            if not hosts:
                return []
                
            controladora = hosts[0]
            items_agrupados = {}
            
            for item in controladora.get('items', []):
                try:
                    key = item.get('key_', '')
                    lastvalue = item.get('lastvalue', 'N/A')
                    item_name = item.get('name', 'N/A')
                    
                    match = re.search(r'\[(.*?)\]', key)
                    if match:
                        index = match.group(1)
                        
                        if index not in items_agrupados:
                            items_agrupados[index] = {
                                'hostid': controladora.get('hostid'),
                                'host': controladora.get('name'),
                                'name': item_name,
                                'index': index,
                                'frequency': 'N/A',
                                'bandwidth': 'N/A',
                                'channel': 'N/A'
                            }
                        
                        if 'freq' in key:
                            freq_mapping = {
                                "1": "2.4 GHz",
                                "2": "5 GHz", 
                                "3": "6 GHz"
                            }
                            items_agrupados[index]['frequency'] = freq_mapping.get(lastvalue, f"{lastvalue} MHz")
                        elif 'width' in key:
                            items_agrupados[index]['bandwidth'] = f"{lastvalue} MHz"
                        elif 'channel' in key:
                            items_agrupados[index]['channel'] = lastvalue
                            
                except Exception as e:
                    self.logger.error(f"Erro ao processar item: {str(e)}")
                    continue
            
            return list(items_agrupados.values())
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar hosts: {str(e)}")
            raise ValueError(f"Erro ao buscar hosts: {str(e)}")

    def get_groups(self):
        """Obtém grupos de hosts"""
        if not self.zapi:
            self.authenticate()
        
        try:
            return self.zapi.hostgroup.get(
                output=['groupid', 'name'],
                sortfield='name'
            )
        except Exception as e:
            self.logger.error(f"Erro ao buscar grupos: {str(e)}")
            raise ValueError(f"Erro ao buscar grupos: {str(e)}")

    def get_items(self, hostids):
        """Obtém itens dos hosts"""
        if not self.zapi:
            self.authenticate()
        return self.zapi.item.get(hostids=hostids, output='extend')

def test_zabbix_connection():
    """Testa conexão com Zabbix"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "JSON inválido"}), 400

        url = data.get('url')
        user = data.get('user')
        password = data.get('password')

        if not all([url, user, password]):
            return jsonify({"success": False, "error": "Campos obrigatórios faltando"}), 400

        zabbix_service = ZabbixService(url.strip(), user.strip(), password.strip())
        zabbix_service.authenticate()
        
        return jsonify({
            "success": True,
            "message": "Conectado",
            "url": url
        })
    except Exception as e:
        logger.error(f"Erro: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "details": "Verifique URL e acesso"
        }), 500

def get_all_hosts():
    """Lista todos os hosts"""
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
        logger.error(f"Erro: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "details": "Verifique URL e acesso"
        }), 500

def get_all_groups():
    """Lista todos os grupos"""
    try:
        config = ZabbixConfig.query.first()
        if not config:
            return jsonify({
                "success": False,
                "error": "Config não encontrada"
            }), 404

        zabbix_service = ZabbixService(config.url, config.user, config.password)
        groups = zabbix_service.get_groups()
        
        return jsonify({
            "success": True,
            "data": groups
        })
    except Exception as e:
        logger.error(f"Erro: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "details": "Verifique URL e acesso"
        }), 500

def save_zabbix_config():
    """Salva configuração do Zabbix"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "JSON inválido"}), 400

        url = data.get('url')
        user = data.get('user')
        password = data.get('password')

        if not all([url, user, password]):
            return jsonify({"success": False, "error": "Campos obrigatórios faltando"}), 400

        zabbix_service = ZabbixService(url.strip(), user.strip(), password.strip())
        zabbix_service.authenticate()

        ZabbixConfig.query.delete()
        config = ZabbixConfig(
            url=url.strip(), 
            user=user.strip(), 
            password=password.strip()
        )
        db.session.add(config)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Configuração salva",
            "url": url
        })
    except ValueError as e:
        db.session.rollback()
        logger.error(f"Erro de validação: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "details": "Verifique URL e acesso"
        }), 500

def get_zabbix_config():
    """Obtém configuração do Zabbix"""
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
        logger.error(f"Erro: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
