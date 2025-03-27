import os
from pathlib import Path

class Config:
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    PORT = int(os.environ.get('PORT', 5003))
    HOST = os.environ.get('HOST', '0.0.0.0')
    
    SQLALCHEMY_DATABASE_URI = 'sqlite:///zabbix_config.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    SSL_DIR = Path(__file__).parent.parent / 'ssl'
    SSL_CERT_PATH = SSL_DIR / 'cert.pem'
    SSL_KEY_PATH = SSL_DIR / 'key.pem'
    
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s' 