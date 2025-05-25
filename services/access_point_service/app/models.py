from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class AccessPoint(db.Model):
    __tablename__ = 'access_points'

    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    channel = db.Column(db.String(10))
    frequency = db.Column(db.String(20))
    bandwidth = db.Column(db.String(20))
    last_update = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<AccessPoint {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'channel': self.channel,
            'frequency': self.frequency,
            'bandwidth': self.bandwidth,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }