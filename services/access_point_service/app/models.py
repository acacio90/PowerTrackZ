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


class ZabbixConfig(db.Model):
    """Configuracao de conexao com o Zabbix externo."""
    __tablename__ = 'zabbix_config'

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255), nullable=False)
    user = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
