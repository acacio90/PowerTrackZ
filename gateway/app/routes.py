from flask import Blueprint, jsonify, request
import logging

import requests

from .config import Config


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

session = Config.get_http_session()

routes = Blueprint("routes", __name__)


def handle_error(error, service_name):
    logger.error(f"Erro no {service_name}: {str(error)}")
    if isinstance(error, requests.exceptions.ConnectionError):
        return {"message": f"Servico {service_name} nao esta disponivel"}, 503
    if isinstance(error, requests.exceptions.Timeout):
        return {"message": f"Timeout ao conectar com {service_name}"}, 504
    return {"message": f"Erro interno no {service_name}", "error": str(error)}, 500


@routes.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": "gateway",
        "port": Config.PORT,
    })


@routes.route("/api/zabbix/test-connection", methods=["POST"])
@routes.route("/zabbix/test-connection", methods=["POST"])
def test_zabbix_connection():
    try:
        response = session.post(
            f"{Config.ZABBIX_SERVICE_URL}/test-connection",
            json=request.get_json(),
            timeout=Config.HTTP_TIMEOUT,
        )
        return response.json(), response.status_code
    except Exception as exc:
        error_response, status_code = handle_error(exc, "Zabbix")
        return jsonify(error_response), status_code


@routes.route("/api/zabbix/hosts", methods=["GET", "POST"])
@routes.route("/zabbix/hosts", methods=["GET", "POST"])
def zabbix_hosts():
    try:
        if request.method == "GET":
            response = session.get(f"{Config.ZABBIX_SERVICE_URL}/hosts", timeout=Config.HTTP_TIMEOUT)
        else:
            response = session.post(
                f"{Config.ZABBIX_SERVICE_URL}/hosts",
                json=request.get_json() or {},
                timeout=Config.HTTP_TIMEOUT,
            )
        return response.json(), response.status_code
    except Exception as exc:
        error_response, status_code = handle_error(exc, "Zabbix")
        return jsonify(error_response), status_code


@routes.route("/api/zabbix/save-config", methods=["POST"])
@routes.route("/zabbix/save-config", methods=["POST"])
def save_zabbix_config():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Dados obrigatorios"}), 400
        response = session.post(
            f"{Config.ZABBIX_SERVICE_URL}/save-config",
            json=data,
            timeout=Config.HTTP_TIMEOUT,
        )
        return response.json(), response.status_code
    except Exception as exc:
        error_response, status_code = handle_error(exc, "Zabbix")
        return jsonify(error_response), status_code


@routes.route("/api/map", methods=["GET"])
def get_map():
    try:
        response = session.get(f"{Config.MAP_SERVICE_URL}/map", timeout=Config.HTTP_TIMEOUT)
        return response.content, response.status_code, {"Content-Type": "text/html"}
    except Exception as exc:
        error_response, status_code = handle_error(exc, "map_service")
        return jsonify(error_response), status_code


@routes.route("/api/map/points", methods=["GET"])
def get_map_points():
    try:
        response = session.get(f"{Config.MAP_SERVICE_URL}/points", timeout=Config.HTTP_TIMEOUT)
        return response.json(), response.status_code
    except Exception as exc:
        error_response, status_code = handle_error(exc, "map_service")
        return jsonify(error_response), status_code


@routes.route("/api/analysis/analyze", methods=["GET"])
def analyze():
    try:
        response = session.get(f"{Config.ANALYSIS_SERVICE_URL}/analyze", timeout=Config.HTTP_TIMEOUT)
        return response.json(), response.status_code
    except Exception as exc:
        error_response, status_code = handle_error(exc, "analysis_service")
        return jsonify(error_response), status_code


@routes.route("/api/analysis/strategies", methods=["GET"])
def get_analysis_strategies():
    try:
        response = session.get(f"{Config.ANALYSIS_SERVICE_URL}/strategies", timeout=Config.HTTP_TIMEOUT)
        return response.json(), response.status_code
    except Exception as exc:
        error_response, status_code = handle_error(exc, "analysis_service")
        return jsonify(error_response), status_code


@routes.route("/api/analysis/analyze-graph", methods=["POST"])
def analyze_graph():
    try:
        response = session.post(
            f"{Config.ANALYSIS_SERVICE_URL}/analyze-graph",
            json=request.get_json(),
            timeout=Config.HTTP_TIMEOUT,
        )
        return response.json(), response.status_code
    except Exception as exc:
        error_response, status_code = handle_error(exc, "analysis_service")
        return jsonify(error_response), status_code


@routes.route("/api/analysis/compare-strategies", methods=["POST"])
def compare_strategies():
    try:
        response = session.post(
            f"{Config.ANALYSIS_SERVICE_URL}/compare-strategies",
            json=request.get_json(),
            timeout=Config.HTTP_TIMEOUT,
        )
        return response.json(), response.status_code
    except Exception as exc:
        error_response, status_code = handle_error(exc, "analysis_service")
        return jsonify(error_response), status_code


@routes.route("/api/analysis/collision-graph", methods=["POST"])
def collision_graph():
    try:
        response = session.post(
            f"{Config.ANALYSIS_SERVICE_URL}/collision-graph",
            json=request.get_json(),
            timeout=Config.HTTP_TIMEOUT,
        )
        return response.json(), response.status_code
    except Exception as exc:
        error_response, status_code = handle_error(exc, "analysis_service")
        return jsonify(error_response), status_code


@routes.route("/api/access_points", methods=["GET", "POST"])
def access_points():
    try:
        if request.method == "GET":
            response = session.get(
                f"{Config.ACCESS_POINT_SERVICE_URL}/access_points",
                timeout=Config.HTTP_TIMEOUT,
            )
        else:
            response = session.post(
                f"{Config.ACCESS_POINT_SERVICE_URL}/access_points",
                json=request.get_json(),
                timeout=Config.HTTP_TIMEOUT,
            )
        return response.json(), response.status_code
    except Exception as exc:
        error_response, status_code = handle_error(exc, "access_point_service")
        return jsonify(error_response), status_code


@routes.route("/api/access_points/import", methods=["POST"])
def import_access_points():
    try:
        response = session.post(
            f"{Config.ACCESS_POINT_SERVICE_URL}/access_points/import",
            json=request.get_json(),
            timeout=Config.HTTP_TIMEOUT,
        )
        return response.json(), response.status_code
    except Exception as exc:
        error_response, status_code = handle_error(exc, "access_point_service")
        return jsonify(error_response), status_code


@routes.route("/api/access_points/<id>", methods=["GET", "PUT", "DELETE"])
def access_point_by_id(id):
    try:
        if request.method == "GET":
            response = session.get(
                f"{Config.ACCESS_POINT_SERVICE_URL}/access_points/{id}",
                timeout=Config.HTTP_TIMEOUT,
            )
        elif request.method == "PUT":
            response = session.put(
                f"{Config.ACCESS_POINT_SERVICE_URL}/access_points/{id}",
                json=request.get_json(),
                timeout=Config.HTTP_TIMEOUT,
            )
        else:
            response = session.delete(
                f"{Config.ACCESS_POINT_SERVICE_URL}/access_points/{id}",
                timeout=Config.HTTP_TIMEOUT,
            )
        return response.json(), response.status_code
    except Exception as exc:
        error_response, status_code = handle_error(exc, "access_point_service")
        return jsonify(error_response), status_code


@routes.route("/api/access_points/sync/zabbix", methods=["POST"])
def sync_zabbix_access_points():
    try:
        response = session.post(
            f"{Config.ACCESS_POINT_SERVICE_URL}/sync/zabbix",
            json=request.get_json() or {},
            timeout=Config.HTTP_TIMEOUT,
        )
        return response.json(), response.status_code
    except Exception as exc:
        error_response, status_code = handle_error(exc, "access_point_service")
        return jsonify(error_response), status_code


@routes.route("/static/css/<path:filename>")
def static_css_files(filename):
    logger.info(f"Tentando acessar CSS: {filename}")
    try:
        frontend_url = f"{Config.FRONTEND_SERVICE_URL}/static/css/{filename}"
        response = session.get(frontend_url, timeout=Config.HTTP_TIMEOUT)
        return response.content, response.status_code, {"Content-Type": "text/css"}
    except Exception as exc:
        logger.error(f"Erro ao redirecionar CSS {filename}: {str(exc)}")
        return jsonify({"message": "Erro ao acessar CSS"}), 500


@routes.route("/static/js/<path:filename>")
def static_js_files(filename):
    logger.info(f"Tentando acessar JS: {filename}")
    try:
        frontend_url = f"{Config.FRONTEND_SERVICE_URL}/static/js/{filename}"
        response = session.get(frontend_url, timeout=Config.HTTP_TIMEOUT)
        return response.content, response.status_code, {"Content-Type": "application/javascript"}
    except Exception as exc:
        logger.error(f"Erro ao redirecionar JS {filename}: {str(exc)}")
        return jsonify({"message": "Erro ao acessar JavaScript"}), 500


@routes.route("/static/<path:filename>")
def static_files(filename):
    try:
        frontend_url = f"{Config.FRONTEND_SERVICE_URL}/static/{filename}"
        response = session.get(frontend_url, timeout=Config.HTTP_TIMEOUT)

        content_type = "text/plain"
        if filename.endswith(".png"):
            content_type = "image/png"
        elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
            content_type = "image/jpeg"
        elif filename.endswith(".gif"):
            content_type = "image/gif"
        elif filename.endswith(".svg"):
            content_type = "image/svg+xml"
        elif filename.endswith(".ico"):
            content_type = "image/x-icon"
        elif filename.endswith(".woff"):
            content_type = "font/woff"
        elif filename.endswith(".woff2"):
            content_type = "font/woff2"
        elif filename.endswith(".ttf"):
            content_type = "font/ttf"
        elif filename.endswith(".eot"):
            content_type = "application/vnd.ms-fontobject"

        return response.content, response.status_code, {"Content-Type": content_type}
    except Exception as exc:
        logger.error(f"Erro ao redirecionar asset estatico {filename}: {str(exc)}")
        return jsonify({"message": "Erro ao acessar asset estatico"}), 500


@routes.route("/", defaults={"path": ""})
@routes.route("/<path:path>")
def frontend_proxy(path):
    try:
        if path.startswith("api/"):
            return jsonify({"message": "Endpoint nao encontrado"}), 404

        frontend_url = f"{Config.FRONTEND_SERVICE_URL}/{path}"
        response = session.get(frontend_url, timeout=Config.HTTP_TIMEOUT)

        content_type = "text/html"
        if path.endswith(".css"):
            content_type = "text/css"
        elif path.endswith(".js"):
            content_type = "application/javascript"
        elif path.endswith(".png"):
            content_type = "image/png"
        elif path.endswith(".jpg") or path.endswith(".jpeg"):
            content_type = "image/jpeg"
        elif path.endswith(".gif"):
            content_type = "image/gif"
        elif path.endswith(".svg"):
            content_type = "image/svg+xml"
        elif path.endswith(".ico"):
            content_type = "image/x-icon"
        elif path.endswith(".woff"):
            content_type = "font/woff"
        elif path.endswith(".woff2"):
            content_type = "font/woff2"
        elif path.endswith(".ttf"):
            content_type = "font/ttf"
        elif path.endswith(".eot"):
            content_type = "application/vnd.ms-fontobject"

        return response.content, response.status_code, {"Content-Type": content_type}
    except Exception as exc:
        logger.error(f"Erro ao redirecionar para frontend: {str(exc)}")
        return jsonify({"message": "Erro ao acessar frontend"}), 500
