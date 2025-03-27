from flask_sqlalchemy import SQLAlchemy
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = SQLAlchemy()

class ZabbixConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255), nullable=False)
    user = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
