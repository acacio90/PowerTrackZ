from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class AccessPoint(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    description = db.Column(db.String(100))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    frequency = db.Column(db.String(50))
    bandwidth = db.Column(db.String(50))
    channel = db.Column(db.Integer)