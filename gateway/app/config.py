import os

class Config:
    # Configurações
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    PORT = int(os.environ.get('PORT', 80))
    HOST = os.environ.get('HOST', '0.0.0.0')
    
    # URLs
    ZABBIX_SERVICE_URL = "https://zabbix_service:5003"
    MAP_SERVICE_URL = "http://map_service:5001"
    ANALYSIS_SERVICE_URL = "http://analysis_service:5002"
    ACCESS_POINT_SERVICE_URL = "http://access_point_service:5004"
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Flask
    SECRET_KEY = "zabbixtrack"
    DEBUG = True

    # Configurações do HTTP
    HTTP_TIMEOUT = 120
    HTTP_RETRIES = 10
    HTTP_BACKOFF_FACTOR = 2.0
    HTTP_STATUS_FORCELIST = [
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
        408,  # Request Timeout
        429,  # Too Many Requests
        104,  # Connection Reset
        111,  # Connection Refused
        110,  # Connection Timed Out
        113,  # No Route to Host
        99,   # Connection Reset by Peer
        100,  # Connection Reset by Host
        101,  # Connection Reset by Network
        102,  # Connection Reset by Service
        103   # Connection Reset by Gateway
    ]

    @classmethod
    def get_http_session(cls):
        session = requests.Session()
        retry = Retry(
            total=cls.HTTP_RETRIES,
            backoff_factor=cls.HTTP_BACKOFF_FACTOR,
            status_forcelist=cls.HTTP_STATUS_FORCELIST
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session 