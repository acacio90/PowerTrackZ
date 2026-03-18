import os
from pathlib import Path

class Config:
    DEBUG = os.environ.get('FLASK_ENV', 'development') == 'development'
    PORT = int(os.environ.get('PORT', 5003))
    HOST = os.environ.get('HOST', '0.0.0.0')

    SQLALCHEMY_DATABASE_URI = os.environ["ZABBIX_DATABASE_URI"]
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SSL_DIR = Path(os.environ.get("ZABBIX_SSL_DIR", Path(__file__).parent.parent / 'ssl'))
    SSL_CERT_PATH = Path(os.environ.get("ZABBIX_SSL_CERT_PATH", SSL_DIR / 'cert.pem'))
    SSL_KEY_PATH = Path(os.environ.get("ZABBIX_SSL_KEY_PATH", SSL_DIR / 'key.pem'))

    CORS_ORIGINS = [
        origin.strip()
        for origin in os.environ["ZABBIX_CORS_ORIGINS"].split(",")
        if origin.strip()
    ]

    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.environ.get('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
