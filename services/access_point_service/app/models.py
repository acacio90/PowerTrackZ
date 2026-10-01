from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class AccessPoint(db.Model):
    """Modelo para pontos de acesso"""
    __tablename__ = 'access_points'

    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    channel = db.Column(db.String(10))
    frequency = db.Column(db.String(20)) 
    bandwidth = db.Column(db.String(20))
    last_update = db.Column(db.DateTime, default=datetime.utcnow)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    def to_dict(self):
        """Converte o modelo para dicionário"""
        return {
            'id': self.id,
            'name': self.name, 
            'channel': self.channel,
            'frequency': self.frequency,
            'bandwidth': self.bandwidth,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }


class ScalabilityRun(db.Model):
    """Execucao do teste de escalabilidade: parametros, versao do PowerTrackZ, pontos medidos e pontos de quebra."""
    __tablename__ = 'scalability_runs'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    finished_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), nullable=False, default='running')
    progress = db.Column(db.Float, nullable=False, default=0.0)
    current_step = db.Column(db.String(200))
    version = db.Column(db.Text, nullable=False, default='{}')
    parameters = db.Column(db.Text, nullable=False, default='{}')
    strategies = db.Column(db.Text, nullable=False, default='[]')
    points = db.Column(db.Text, nullable=False, default='[]')
    breaks = db.Column(db.Text, nullable=False, default='{}')
    error = db.Column(db.Text)
    # Modo Comparacao (#90): por estrategia, a execucao e a configuracao proposta da melhor repeticao.
    proposals = db.Column(db.Text, nullable=False, default='{}')


class ZabbixConfig(db.Model):
    """Configuracao de conexao com o Zabbix externo."""
    __tablename__ = 'zabbix_config'

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255), nullable=False)
    user = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
