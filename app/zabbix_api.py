# app/zabbix_api.py
import configparser
from pyzabbix import ZabbixAPI
import certifi

class ZabbixConnector:
    def __init__(self, config_path='config.ini', verify=True):
        config = configparser.ConfigParser()
        config.read(config_path)
        
        username = config.get('zabbix', 'username')
        password = config.get('zabbix', 'password')
        url = config.get('zabbix', 'url')

        # Verificação do certificado SSL
        self.zapi = ZabbixAPI(url)
        if not verify:
            # Desativa a verificação SSL
            self.zapi.session.verify = False
        else:
            # Usar o certificado confiável
            self.zapi.session.verify = certifi.where()

        try:
            self.zapi.login(username, password)
            print("Conexão bem-sucedida!")
        except Exception as e:
            print(f"Erro ao conectar: {e}")

    def get_hostgroups(self):
        hostgroups = self.zapi.hostgroup.get()
        return hostgroups
