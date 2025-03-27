from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class ZabbixConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255), nullable=False)
    user = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)