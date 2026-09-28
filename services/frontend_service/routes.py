from flask import Blueprint, Response, jsonify, redirect, render_template, request, stream_with_context, url_for
import logging
import os
import requests

routes = Blueprint('routes', __name__)

logger = logging.getLogger(__name__)

SERVICE_URLS = {
    "analysis": os.environ["ANALYSIS_SERVICE_URL"],
    "access_points": os.environ["ACCESS_POINT_SERVICE_URL"],
}
HTTP_TIMEOUT = int(os.environ.get("FRONTEND_HTTP_TIMEOUT", "120"))
HTTP_VERIFY_SSL = os.environ.get("FRONTEND_HTTP_VERIFY_SSL", "false").lower() == "true"


def resolve_service_url(endpoint):
    routes = {
        "/zabbix": ("access_points", ""),
        "/analysis": ("analysis", "/analysis"),
        "/access_points": ("access_points", ""),
    }

    for prefix, (service_name, strip_prefix) in routes.items():
        if endpoint == prefix or endpoint.startswith(f"{prefix}/"):
            service_path = endpoint[len(strip_prefix):] if strip_prefix else endpoint
            return f"{SERVICE_URLS[service_name]}{service_path}"

    raise ValueError(f"Endpoint sem servico configurado: {endpoint}")


def make_api_request(endpoint, method='GET', data=None):
    """Faz requisicao direta ao microservico responsavel."""
    try:
        url = resolve_service_url(endpoint)
        if method == 'GET':
            response = requests.get(url, timeout=HTTP_TIMEOUT, verify=HTTP_VERIFY_SSL)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=HTTP_TIMEOUT, verify=HTTP_VERIFY_SSL)
        elif method == 'PUT':
            response = requests.put(url, json=data, timeout=HTTP_TIMEOUT, verify=HTTP_VERIFY_SSL)
        elif method == 'DELETE':
            response = requests.delete(url, timeout=HTTP_TIMEOUT, verify=HTTP_VERIFY_SSL)
        else:
            raise ValueError(f"Metodo HTTP nao suportado: {method}")

        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            return response.json(), response.status_code
        return response.text, response.status_code
    except Exception as e:
        logger.error(f"Erro na requisicao para {endpoint}: {str(e)}")
        return {"error": str(e)}, 500


@routes.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "frontend_service",
        "port": int(os.environ.get("PORT", 3000))
    })


@routes.route('/')
def index():
    return render_template('pages/index.html')


@routes.route('/infrastructure')
def infrastructure():
    try:
        points_data, _ = make_api_request('/access_points')
        points = points_data if isinstance(points_data, list) else []
    except Exception:
        points = []

    return render_template('pages/infrastructure.html', points=points)


@routes.route('/hosts')
@routes.route('/register')
def legacy_infrastructure():
    # Pontos e Registrar foram unificadas em Sua infraestrutura; os enderecos antigos continuam validos.
    return redirect(url_for('routes.infrastructure'))


@routes.route('/analysis')
def analysis():
    try:
        points_data, _ = make_api_request('/access_points')
        points = points_data if isinstance(points_data, list) else []
    except Exception:
        points = []
    return render_template('pages/analysis.html', points=points)


@routes.route('/settings')
def settings():
    # As configuracoes sao um modal do layout base; o endereco antigo abre o modal na tela inicial.
    return redirect(url_for('routes.index', open_config=1))


@routes.route('/zabbix/hosts', methods=['GET'])
def zabbix_hosts():
    response_data, status_code = make_api_request('/zabbix/hosts')
    return jsonify(response_data), status_code


@routes.route('/zabbix/save-config', methods=['POST'])
def save_zabbix_config():
    data = request.get_json(silent=True) or {}
    response_data, status_code = make_api_request('/zabbix/save-config', 'POST', data)
    return jsonify(response_data), status_code


@routes.route('/zabbix/test-connection', methods=['POST'])
def test_zabbix_connection():
    data = request.get_json(silent=True) or {}
    response_data, status_code = make_api_request('/zabbix/test-connection', 'POST', data)
    return jsonify(response_data), status_code


@routes.route('/api/access_points', methods=['GET', 'POST'])
def access_points_api():
    data = request.get_json(silent=True) if request.method in ['POST'] else None
    response_data, status_code = make_api_request('/access_points', request.method, data)
    return jsonify(response_data), status_code


@routes.route('/api/access_points/import', methods=['POST'])
def access_points_import_api():
    data = request.get_json(silent=True)
    response_data, status_code = make_api_request('/access_points/import', 'POST', data)
    return jsonify(response_data), status_code


@routes.route('/api/access_points/generate', methods=['POST'])
def access_points_generate_api():
    data = request.get_json(silent=True) or {}
    response_data, status_code = make_api_request('/access_points/generate', 'POST', data)
    return jsonify(response_data), status_code


@routes.route('/api/access_points/<point_id>', methods=['GET', 'PUT', 'DELETE'])
def access_point_detail_api(point_id):
    data = request.get_json(silent=True) if request.method == 'PUT' else None
    response_data, status_code = make_api_request(f'/access_points/{point_id}', request.method, data)
    return jsonify(response_data), status_code


@routes.route('/api/analysis/strategies', methods=['GET'])
def analysis_strategies_api():
    response_data, status_code = make_api_request('/analysis/strategies', 'GET')
    return jsonify(response_data), status_code


@routes.route('/api/analysis/capabilities', methods=['GET'])
def analysis_capabilities_api():
    response_data, status_code = make_api_request('/analysis/capabilities', 'GET')
    return jsonify(response_data), status_code


@routes.route('/api/analysis/analyze-graph', methods=['POST'])
def analysis_analyze_graph_api():
    data = request.get_json(silent=True) or {}
    response_data, status_code = make_api_request('/analysis/analyze-graph', 'POST', data)
    return jsonify(response_data), status_code


@routes.route('/api/analysis/backtracking', methods=['POST'])
def analysis_backtracking_api():
    data = request.get_json(silent=True) or {}
    response_data, status_code = make_api_request('/analysis/backtracking', 'POST', data)
    return jsonify(response_data), status_code


@routes.route('/api/analysis/analyze-graph-stream', methods=['POST'])
def analysis_analyze_graph_stream_api():
    data = request.get_json(silent=True) or {}
    try:
        response = requests.post(
            resolve_service_url('/analysis/analyze-graph-stream'),
            json=data,
            stream=True,
            timeout=None,
            verify=HTTP_VERIFY_SSL,
        )

        def generate():
            try:
                for chunk in response.iter_content(chunk_size=1):
                    if chunk:
                        yield chunk
            finally:
                response.close()

        return Response(
            stream_with_context(generate()),
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'application/x-ndjson'),
        )
    except Exception as e:
        logger.error(f"Erro na requisicao stream para /analysis/analyze-graph-stream: {str(e)}")
        return jsonify({"error": str(e)}), 500


@routes.route('/api/analysis/backtracking-stream', methods=['POST'])
def analysis_backtracking_stream_api():
    data = request.get_json(silent=True) or {}
    try:
        response = requests.post(
            resolve_service_url('/analysis/backtracking-stream'),
            json=data,
            stream=True,
            timeout=None,
            verify=HTTP_VERIFY_SSL,
        )

        def generate():
            try:
                for chunk in response.iter_content(chunk_size=1):
                    if chunk:
                        yield chunk
            finally:
                response.close()

        return Response(
            stream_with_context(generate()),
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'application/x-ndjson'),
        )
    except Exception as e:
        logger.error(f"Erro na requisicao stream para /analysis/backtracking-stream: {str(e)}")
        return jsonify({"error": str(e)}), 500


@routes.route('/api/analysis/cancel-analysis', methods=['POST'])
def analysis_cancel_api():
    data = request.get_json(silent=True) or {}
    response_data, status_code = make_api_request('/analysis/cancel-analysis', 'POST', data)
    return jsonify(response_data), status_code


@routes.route('/api/analysis/collision-graph', methods=['POST'])
def analysis_collision_graph_api():
    data = request.get_json(silent=True) or {}
    response_data, status_code = make_api_request('/analysis/collision-graph', 'POST', data)
    return jsonify(response_data), status_code

