import logging
import re

import requests
import urllib3
from flask import jsonify, request
from pyzabbix import ZabbixAPI
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from models import ZabbixConfig, db


requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


def validate_url(url):
    if not url:
        return False

    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$',
        re.IGNORECASE,
    )
    return url_pattern.match(url) is not None


class ZabbixClient:
    def __init__(self, url, user, password):
        if not url or not validate_url(url):
            raise ValueError("URL invalida")

        if not url.startswith("https://"):
            url = "https://" + url.lstrip("http://")

        self.url = url
        self.user = user
        self.password = password
        self.zapi = None

    def authenticate(self):
        if self.zapi:
            return True

        try:
            self.zapi = ZabbixAPI(self.url)
            self.zapi.session.verify = False
            self.zapi.login(self.user, self.password)
            logger.info("Conectado ao Zabbix API v%s", self.zapi.api_version())
            return True
        except Exception as exc:
            logger.error("Erro ao autenticar no Zabbix: %s", exc)
            if "Login name or password is incorrect" in str(exc):
                raise ValueError("Credenciais invalidas") from exc
            if "Connection refused" in str(exc):
                raise ValueError("Servidor Zabbix indisponivel") from exc
            raise ValueError(f"Erro na autenticacao: {exc}") from exc

    def get_hosts(self):
        if not self.zapi:
            self.authenticate()

        hosts = self.zapi.host.get(
            output=["hostid", "host", "name"],
            selectInterfaces=["interfaceid", "ip"],
            selectItems=["snmpindex", "itemid", "name", "key_", "lastvalue"],
            groupids=["28"],
        )

        if not hosts:
            return []

        controladora = hosts[0]
        grouped_items = {}

        for item in controladora.get("items", []):
            key = item.get("key_", "")
            lastvalue = item.get("lastvalue", "N/A")
            item_name = item.get("name", "N/A")
            match = re.search(r"\[(.*?)\]", key)

            if not match:
                continue

            index = match.group(1)
            if index not in grouped_items:
                grouped_items[index] = {
                    "hostid": controladora.get("hostid"),
                    "host": controladora.get("name"),
                    "name": item_name,
                    "index": index,
                    "frequency": "N/A",
                    "bandwidth": "N/A",
                    "channel": "N/A",
                }

            if "freq" in key:
                freq_mapping = {
                    "1": "2.4 GHz",
                    "2": "5 GHz",
                    "3": "6 GHz",
                }
                grouped_items[index]["frequency"] = freq_mapping.get(lastvalue, f"{lastvalue} MHz")
            elif "width" in key:
                grouped_items[index]["bandwidth"] = f"{lastvalue} MHz"
            elif "channel" in key:
                grouped_items[index]["channel"] = lastvalue

        return list(grouped_items.values())

    def get_groups(self):
        if not self.zapi:
            self.authenticate()

        return self.zapi.hostgroup.get(output=["groupid", "name"], sortfield="name")


def get_saved_zabbix_client():
    config = ZabbixConfig.query.first()
    if not config:
        raise ValueError("Config nao encontrada")
    return ZabbixClient(config.url, config.user, config.password)


def test_zabbix_connection():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "JSON invalido"}), 400

        url = data.get("url")
        user = data.get("user")
        password = data.get("password")

        if not all([url, user, password]):
            return jsonify({"success": False, "error": "Campos obrigatorios faltando"}), 400

        client = ZabbixClient(url.strip(), user.strip(), password.strip())
        client.authenticate()
        return jsonify({"success": True, "message": "Conectado", "url": url})
    except Exception as exc:
        logger.error("Erro ao testar Zabbix: %s", exc)
        return jsonify({
            "success": False,
            "error": str(exc),
            "details": "Verifique URL e acesso",
        }), 500


def save_zabbix_config():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "JSON invalido"}), 400

        url = data.get("url")
        user = data.get("user")
        password = data.get("password")

        if not all([url, user, password]):
            return jsonify({"success": False, "error": "Campos obrigatorios faltando"}), 400

        client = ZabbixClient(url.strip(), user.strip(), password.strip())
        client.authenticate()

        ZabbixConfig.query.delete()
        db.session.add(ZabbixConfig(url=url.strip(), user=user.strip(), password=password.strip()))
        db.session.commit()

        return jsonify({"success": True, "message": "Configuracao salva", "url": url})
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        logger.error("Erro ao salvar configuracao Zabbix: %s", exc)
        return jsonify({
            "success": False,
            "error": str(exc),
            "details": "Verifique URL e acesso",
        }), 500


def get_zabbix_config():
    try:
        config = ZabbixConfig.query.first()
        if not config:
            return jsonify({"success": False, "error": "Config nao encontrada"}), 404

        return jsonify({
            "success": True,
            "data": {
                "url": config.url,
                "user": config.user,
            },
        })
    except Exception as exc:
        logger.error("Erro ao buscar configuracao Zabbix: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


def get_zabbix_hosts():
    try:
        client = get_saved_zabbix_client()
        hosts = client.get_hosts()
        return jsonify({"success": True, "data": hosts})
    except Exception as exc:
        logger.error("Erro ao buscar hosts Zabbix: %s", exc)
        return jsonify({
            "success": False,
            "error": str(exc),
            "details": "Verifique URL e acesso",
        }), 500


def get_zabbix_groups():
    try:
        client = get_saved_zabbix_client()
        groups = client.get_groups()
        return jsonify({"success": True, "data": groups})
    except Exception as exc:
        logger.error("Erro ao buscar grupos Zabbix: %s", exc)
        return jsonify({
            "success": False,
            "error": str(exc),
            "details": "Verifique URL e acesso",
        }), 500
