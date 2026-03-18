import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class Config:
    DEBUG = os.environ.get("FLASK_ENV", "development") == "development"
    PORT = int(os.environ.get("PORT", 80))
    HOST = os.environ.get("HOST", "0.0.0.0")

    ZABBIX_SERVICE_URL = os.environ["ZABBIX_SERVICE_URL"]
    MAP_SERVICE_URL = os.environ["MAP_SERVICE_URL"]
    ANALYSIS_SERVICE_URL = os.environ["ANALYSIS_SERVICE_URL"]
    ACCESS_POINT_SERVICE_URL = os.environ["ACCESS_POINT_SERVICE_URL"]
    FRONTEND_SERVICE_URL = os.environ["FRONTEND_SERVICE_URL"]

    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.environ.get(
        "LOG_FORMAT",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    SECRET_KEY = os.environ["GATEWAY_SECRET_KEY"]

    HTTP_TIMEOUT = int(os.environ["GATEWAY_HTTP_TIMEOUT"])
    HTTP_RETRIES = int(os.environ["GATEWAY_HTTP_RETRIES"])
    HTTP_BACKOFF_FACTOR = float(os.environ["GATEWAY_HTTP_BACKOFF_FACTOR"])
    HTTP_VERIFY_SSL = os.environ["GATEWAY_HTTP_VERIFY_SSL"].lower() == "true"
    HTTP_STATUS_FORCELIST = [
        500,
        502,
        503,
        504,
        408,
        429,
        104,
        111,
        110,
        113,
        99,
        100,
        101,
        102,
        103,
    ]

    @classmethod
    def get_http_session(cls):
        session = requests.Session()
        retry = Retry(
            total=cls.HTTP_RETRIES,
            backoff_factor=cls.HTTP_BACKOFF_FACTOR,
            status_forcelist=cls.HTTP_STATUS_FORCELIST,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.verify = cls.HTTP_VERIFY_SSL
        return session
