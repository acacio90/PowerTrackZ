# Importações necessárias
from flask import request, jsonify, render_template
from models import db, AccessPoint
import logging
import sys
import os
import requests
import re
from datetime import datetime

# Adiciona o diretório src ao path do Python
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from rules.snmp_index_rule import SNMPIndexRule

# Configuração básica de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URL do serviço Zabbix
ZABBIX_SERVICE_URL = os.getenv('ZABBIX_SERVICE_URL', 'http://zabbix_service:5000')

# Cria as tabelas no banco
def create_tables():
    db.create_all()

def extract_ap_info(item):
    """
    Extrai informações do AP a partir do item do Zabbix
    
    Args:
        item (dict): Item do Zabbix
        
    Returns:
        tuple: (snmpindex, ap_name, metric_type, value)
    """
    try:
        key = item.get('key_', '')
        lastvalue = item.get('lastvalue')
        name = item.get('name', '')
        ap_name = name.split(' - ')[0].replace('AP ', '') # Extrai o nome do AP do nome do item

        # Regex para extrair o snmpindex e o tipo de métrica
        # Busca por chaves como ap.channel[INDEX], ap.frequency[INDEX], ap.bandwidth[INDEX]
        match = re.search(r'ap\.(channel|frequency|bandwidth)\[(.*?)\]', key)

        if match:
            metric_type = match.group(1) # 'channel', 'frequency' ou 'bandwidth'
            snmpindex = match.group(2) # O INDEX
            return snmpindex, ap_name, metric_type, lastvalue
        else:
            return None, None, None, None

    except Exception as e:
        logger.error(f"Erro ao extrair informações do AP: {str(e)}")
        return None, None, None, None

def process_zabbix_data(data):
    """
    Processa os dados do Zabbix, agrupa por AP e salva no banco
    
    Args:
        data (dict): Dados do Zabbix
        
    Returns:
        list: Lista de APs processados
    """
    try:
        if not data or 'result' not in data or not data['result']:
            logger.warning("Dados inválidos ou vazios do Zabbix recebidos.")
            return []
            
        # Assumindo que os dados relevantes estão em data['result'][0]['items']
        if not isinstance(data['result'], list) or not data['result'] or 'items' not in data['result'][0]:
             logger.error("Estrutura inesperada nos dados do Zabbix.")
             return []

        ap_data = {}

        # Coletar e agrupar todos os dados dos APs por snmpindex
        for item in data['result'][0]['items']:
            snmpindex, ap_name, metric_type, value = extract_ap_info(item)
            
            if not snmpindex:
                continue # Ignora itens que não são métricas de AP (canal, freq, bw)

            if snmpindex not in ap_data:
                ap_data[snmpindex] = {
                    'id': snmpindex,
                    'name': ap_name,
                    'channel': None,
                    'frequency': None,
                    'bandwidth': None,
                    'last_update': datetime.utcnow()
                }
            
            # Atualiza o valor da métrica correspondente
            if metric_type and value is not None:
                 ap_data[snmpindex][metric_type] = value

        processed_aps = []
        # Salvar ou atualizar no banco de dados
        for ap_info in ap_data.values():
            ap = AccessPoint.query.get(ap_info['id'])
            if not ap:
                # Cria novo AP se não existir
                ap = AccessPoint(
                    id=ap_info['id'],
                    name=ap_info['name'],
                    channel=ap_info['channel'],
                    frequency=ap_info['frequency'],
                    bandwidth=ap_info['bandwidth'],
                    last_update=ap_info['last_update']
                )
                db.session.add(ap)
                logger.info(f"Adicionado novo AP ao banco: {ap.name} ({ap.id})")
            else:
                # Atualiza dados do AP existente
                updated = False
                if ap.channel != ap_info['channel'] and ap_info['channel'] is not None:
                    ap.channel = ap_info['channel']
                    updated = True
                if ap.frequency != ap_info['frequency'] and ap_info['frequency'] is not None:
                    ap.frequency = ap_info['frequency']
                    updated = True
                if ap.bandwidth != ap_info['bandwidth'] and ap_info['bandwidth'] is not None:
                    ap.bandwidth = ap_info['bandwidth']
                    updated = True
                
                if updated:
                    ap.last_update = datetime.utcnow()
                    logger.info(f"Atualizado AP existente no banco: {ap.name} ({ap.id})")
                
            processed_aps.append(ap)

        db.session.commit()
        return processed_aps
        
    except Exception as e:
        logger.error(f"Erro ao processar dados do Zabbix: {str(e)}")
        db.session.rollback()
        # Re-raise a exceção para que a rota que chamou saiba que houve um erro
        raise

# As funções register() e get_access_points() existentes (que não usam dados do Zabbix) podem ser removidas se não forem mais usadas
# Exemplo de como removê-las se não forem necessárias:
# def register():
#     ... (manter ou remover) ...
# def get_access_points():
#     ... (manter ou remover) ...


class AccessPointController:
    def __init__(self):
        # A regra SNMPIndexRule pode não ser mais necessária aqui se os dados já vêm processados do Zabbix e salvos no banco
        # Mantenho por enquanto caso haja outro uso
        self.snmp_rule = SNMPIndexRule()

    def list_hosts(self):
        """
        Lista todos os pontos de acesso do banco de dados local
        
        Returns:
            str: Template renderizado com os dados dos pontos de acesso
        """
        try:
            # Busca todos os APs do banco de dados
            access_points = AccessPoint.query.all()
            
            # Renderiza o template com os dados encontrados
            return render_template('hosts.html', access_points=access_points)
            
        except Exception as e:
            logger.error(f"Erro ao listar hosts do banco: {str(e)}")
            return jsonify({"error": f"Erro ao listar pontos de acesso: {str(e)}"}), 500

    def get_host_details(self, host_id):
        """
        Obtém detalhes de um ponto de acesso específico do banco de dados local
        
        Args:
            host_id (str): ID (SNMPINDEX) do ponto de acesso
            
        Returns:
            dict: Detalhes do ponto de acesso ou erro
        """
        try:
            # Busca o AP específico no banco de dados
            ap = AccessPoint.query.get(host_id)
            
            if ap:
                # Retorna os dados do AP em formato dicionário
                return jsonify(ap.to_dict())
            else:
                return jsonify({"error": "Ponto de acesso não encontrado"}), 404
                
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes do host {host_id} no banco: {str(e)}")
            return jsonify({"error": f"Erro ao buscar detalhes do ponto de acesso: {str(e)}"}), 500

    def sync_zabbix_data(self):
        """
        Busca dados de hosts e itens do Zabbix e sincroniza com o banco local.
        
        Returns:
            dict: Resultado da sincronização
        """
        try:
            # Chama o endpoint do serviço Zabbix para obter dados
            # Assumindo que este endpoint retorna uma estrutura com 'result' e 'items' conforme o JSON de exemplo
            response = requests.get(f"{ZABBIX_SERVICE_URL}/hosts_with_items") # Nome de endpoint mais descritivo
            
            if response.status_code == 200:
                data = response.json()
                processed_aps = process_zabbix_data(data)
                
                return jsonify({
                    "message": f"Dados sincronizados com sucesso. {len(processed_aps)} APs processados.",
                    "access_points": [ap.to_dict() for ap in processed_aps]
                })
            else:
                logger.error(f"Erro ao buscar dados do Zabbix. Status: {response.status_code}")
                return jsonify({"error": "Erro ao buscar dados do Zabbix"}), response.status_code
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de conexão ao serviço Zabbix: {str(e)}")
            return jsonify({"error": f"Erro de conexão ao serviço Zabbix: {str(e)}"}), 500
        except Exception as e:
            logger.error(f"Erro geral na sincronização: {str(e)}")
            return jsonify({"error": f"Erro na sincronização: {str(e)}"}), 500