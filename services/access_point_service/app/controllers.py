from flask import jsonify, render_template
from models import db, AccessPoint
import logging
import re
from datetime import datetime
import os
from zabbix_integration import get_saved_zabbix_client

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

def create_tables():
    db.create_all()
    add_missing_columns()


# Colunas acrescentadas a tabelas que ja existem: o create_all so cria tabelas novas.
MISSING_COLUMNS = {
    "scalability_runs": {"proposals": "TEXT NOT NULL DEFAULT '{}'"},
}


def add_missing_columns():
    with db.engine.begin() as connection:
        for table, columns in MISSING_COLUMNS.items():
            existing = {row[1] for row in connection.exec_driver_sql(f"PRAGMA table_info({table})")}
            for name, definition in columns.items():
                if name not in existing:
                    connection.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

def extract_ap_info(item):
    """Extrai informações do AP do item do Zabbix"""
    try:
        key = item.get('key_', '')
        lastvalue = item.get('lastvalue')
        name = item.get('name', '')
        ap_name = name.split(' - ')[0]

        match = re.search(r'ap\.(channel|frequency|bandwidth)\[(.*?)\]', key)
        if match:
            metric_type = match.group(1)
            snmpindex = match.group(2)
            return snmpindex, ap_name, metric_type, lastvalue
        return None, None, None, None

    except Exception as e:
        logger.error(f"Erro ao extrair informações do AP: {str(e)}")
        return None, None, None, None

def process_zabbix_data(data):
    """Processa dados do Zabbix e atualiza banco"""
    try:
        if not data or 'result' not in data or not data['result']:
            logger.warning("Dados inválidos do Zabbix")
            return []
            
        if not isinstance(data['result'], list) or not data['result'] or 'items' not in data['result'][0]:
             logger.error("Estrutura inválida nos dados do Zabbix")
             return []

        ap_data = {}

        for item in data['result'][0]['items']:
            snmpindex, ap_name, metric_type, value = extract_ap_info(item)
            
            if not snmpindex:
                continue

            if snmpindex not in ap_data:
                ap_data[snmpindex] = {
                    'id': snmpindex,
                    'name': ap_name,
                    'channel': None,
                    'frequency': None,
                    'bandwidth': None,
                    'last_update': datetime.utcnow()
                }
            
            if metric_type and value is not None:
                 ap_data[snmpindex][metric_type] = value

        processed_aps = []
        for ap_info in ap_data.values():
            ap = AccessPoint.query.get(ap_info['id'])
            if not ap:
                ap = AccessPoint(
                    id=ap_info['id'],
                    name=ap_info['name'],
                    channel=ap_info['channel'],
                    frequency=ap_info['frequency'],
                    bandwidth=ap_info['bandwidth'],
                    last_update=ap_info['last_update']
                )
                db.session.add(ap)
                logger.info(f"Novo AP adicionado: {ap.name} ({ap.id})")
            else:
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
                    logger.info(f"AP atualizado: {ap.name} ({ap.id})")
                
            processed_aps.append(ap)

        db.session.commit()
        return processed_aps
        
    except Exception as e:
        logger.error(f"Erro ao processar dados do Zabbix: {str(e)}")
        db.session.rollback()
        raise

class AccessPointController:
    def list_hosts(self):
        """Lista todos os pontos de acesso"""
        try:
            access_points = AccessPoint.query.all()
            for ap in access_points:
                ap.display_name = f"{ap.name}.{ap.id}"
            return render_template('hosts.html', access_points=access_points)
        
        except Exception as e:
            logger.error(f"Erro ao listar hosts: {str(e)}")
            return jsonify({"error": f"Não foi possível listar os APs: {str(e)}"}), 500

    def get_host_details(self, host_id):
        """Obtém detalhes de um ponto de acesso"""
        try:
            ap = AccessPoint.query.get(host_id)
            if ap:
                return jsonify(ap.to_dict())
            return jsonify({"error": "AP não encontrado. Recarregue a página para atualizar a lista."}), 404
                
        except Exception as e:
            logger.error(f"Erro ao buscar host {host_id}: {str(e)}")
            return jsonify({"error": f"Não foi possível buscar os detalhes do AP: {str(e)}"}), 500

    def sync_zabbix_data(self):
        try:
            zabbix_hosts = get_saved_zabbix_client().get_hosts()
            processed_aps = []

            for host in zabbix_hosts:
                raw_id = str(host.get("index") or host.get("id") or "").strip()
                if not raw_id:
                    continue

                suffix = raw_id.split(".")[-1] if "." in raw_id else raw_id
                raw_name = (host.get("name") or host.get("host") or raw_id).split(" - ")[0]

                ap = AccessPoint.query.get(raw_id)
                if not ap:
                    ap = AccessPoint(id=raw_id, name=f"{raw_name}.{suffix}".rstrip("."))
                    db.session.add(ap)

                ap.frequency = host.get("frequency")
                ap.bandwidth = host.get("bandwidth")
                ap.channel = host.get("channel")
                ap.last_update = datetime.utcnow()
                processed_aps.append(ap)

            db.session.commit()
            return jsonify({
                "message": f"{len(processed_aps)} APs sincronizados.",
                "access_points": [ap.to_dict() for ap in processed_aps]
            })
        except Exception as e:
            db.session.rollback()
            logger.error(f"Não foi possível sincronizar com o Zabbix: {str(e)}")
            return jsonify({"error": f"Não foi possível sincronizar com o Zabbix: {str(e)}"}), 500