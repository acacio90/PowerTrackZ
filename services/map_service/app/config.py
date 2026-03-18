import os

class Config:
    DEBUG = os.environ.get('FLASK_ENV', 'development') == 'development'
    PORT = int(os.environ.get('PORT', 5001))
    HOST = os.environ.get('HOST', '0.0.0.0')

    ACCESS_POINT_SERVICE_URL = os.environ["ACCESS_POINT_SERVICE_URL"]

    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.environ.get('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
