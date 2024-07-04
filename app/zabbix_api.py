import configparser
from pyzabbix import ZabbixAPI

class ZabbixConnector:
    def __init__(self, config_path='config.ini'):
        config = configparser.ConfigParser()
        config.read(config_path)
        
        username = config.get('zabbix', 'username')
        password = config.get('zabbix', 'password')
        url = config.get('zabbix', 'url')

        self.zapi = ZabbixAPI(url)

        try:
            self.zapi.login(username, password)
            print("Conexão bem-sucedida!")
        except Exception as e:
            print(f"Erro ao conectar: {e}")

    def get_hostgroups(self):
        # Exemplo de como obter dados de host groups
        hostgroups = self.zapi.hostgroup.get()
        return hostgroups
