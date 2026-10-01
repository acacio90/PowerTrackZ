import json
import logging
import os
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

import requests

SERVICE_DIR = Path(__file__).resolve().parents[1]
ANALYSIS_URL = "http://analysis.test:5002"
ACCESS_POINT_URL = "http://access-points.test:5004"

os.environ.setdefault("ANALYSIS_SERVICE_URL", ANALYSIS_URL)
os.environ.setdefault("ACCESS_POINT_SERVICE_URL", ACCESS_POINT_URL)
os.environ.setdefault("FRONTEND_SECRET_KEY", "test")

if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

import routes  # noqa: E402
from app import create_app  # noqa: E402

# Os erros de conexao simulados sao esperados; o registro deles so poluiria a saida dos testes.
logging.getLogger("routes").setLevel(logging.CRITICAL)

BASE_STYLES = ["css/base/tokens.css", "css/base/elements.css", "css/base/components.css"]
PAGE_STYLES = {
    "/": "css/pages/home.css",
    "/infrastructure": "css/pages/infrastructure.css",
    "/analysis": "css/pages/analysis.css",
    "/scalability": "css/pages/scalability.css",
    "/experiments": "css/pages/scalability.css",
}
CONNECTION_ERROR = "Não foi possível contatar o serviço. Confira se os serviços estão no ar e tente de novo."


class FakeResponse:
    """Resposta simulada de um servico, com o necessario para make_api_request e as rotas de arquivo e stream."""

    def __init__(self, body=None, status_code=200, content_type="application/json", headers=None, content=None):
        self.status_code = status_code
        self._body = body
        self.headers = {"Content-Type": content_type, **(headers or {})}
        self.content = content if content is not None else (json.dumps(body).encode() if body is not None else b"")
        self.text = self.content.decode("utf-8", errors="replace")
        self.closed = False

    def json(self):
        return self._body

    def iter_content(self, chunk_size=1):
        # chunk_size=None entrega os dados como chegam; aqui, em dois pedacos, para exercitar a juncao.
        size = chunk_size or max(1, len(self.content) // 2)
        for index in range(0, len(self.content), size):
            yield self.content[index:index + size]

    def close(self):
        self.closed = True


class FrontendRoutesTests(unittest.TestCase):
    """Rotas do frontend_service com os outros servicos simulados (sem Docker, rede nem navegador)."""

    def setUp(self):
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()
        self.patches = {method: mock.patch.object(routes.requests, method) for method in ("get", "post", "put", "delete")}
        self.http = {method: patch.start() for method, patch in self.patches.items()}
        for patch in self.patches.values():
            self.addCleanup(patch.stop)
        # Por padrao, os servicos respondem com uma lista vazia de APs.
        self.http["get"].return_value = FakeResponse([])

    def stylesheets(self, html):
        return re.findall(r'href="/static/(css/[^"]+)"', html)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["service"], "frontend_service")

    def test_pages_load_the_base_styles_and_only_their_own_page_styles(self):
        for path, page_style in PAGE_STYLES.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                styles = self.stylesheets(response.get_data(as_text=True))
                self.assertEqual(styles, BASE_STYLES + [page_style])

    def test_pages_render_even_when_the_access_point_service_is_down(self):
        self.http["get"].side_effect = requests.ConnectionError("recusada")
        for path in ("/infrastructure", "/analysis"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_legacy_addresses_redirect(self):
        cases = {"/hosts": "/infrastructure", "/register": "/infrastructure", "/settings": "/?open_config=1"}
        for path, target in cases.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.headers["Location"], target)

    def test_resolve_service_url_for_each_prefix(self):
        cases = {
            "/analysis/strategies": f"{ANALYSIS_URL}/strategies",
            "/analysis": ANALYSIS_URL,
            "/access_points/7": f"{ACCESS_POINT_URL}/access_points/7",
            "/access_points": f"{ACCESS_POINT_URL}/access_points",
            "/experiments/scalability/3": f"{ACCESS_POINT_URL}/experiments/scalability/3",
            "/zabbix/hosts": f"{ACCESS_POINT_URL}/zabbix/hosts",
        }
        for endpoint, url in cases.items():
            with self.subTest(endpoint=endpoint):
                self.assertEqual(routes.resolve_service_url(endpoint), url)

    def test_resolve_service_url_rejects_an_endpoint_without_service(self):
        for endpoint in ("/unknown", "/analysisx", "/access_pointsx/1"):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(ValueError):
                    routes.resolve_service_url(endpoint)

    def test_api_routes_forward_method_body_and_status(self):
        body = {"strategy": "greedy", "aps": [{"id": "a"}]}
        cases = [
            ("get", "/api/access_points", None, f"{ACCESS_POINT_URL}/access_points"),
            ("post", "/api/access_points", {"id": "a"}, f"{ACCESS_POINT_URL}/access_points"),
            ("put", "/api/access_points/a", {"channel": "6"}, f"{ACCESS_POINT_URL}/access_points/a"),
            ("delete", "/api/access_points/a", None, f"{ACCESS_POINT_URL}/access_points/a"),
            ("post", "/api/access_points/generate", {"count": 10}, f"{ACCESS_POINT_URL}/access_points/generate"),
            ("get", "/api/analysis/strategies", None, f"{ANALYSIS_URL}/strategies"),
            ("post", "/api/analysis/analyze-graph", body, f"{ANALYSIS_URL}/analyze-graph"),
            ("post", "/api/analysis/graph-metrics", body, f"{ANALYSIS_URL}/graph-metrics"),
            ("post", "/api/analysis/cancel-analysis", {"job_id": "job-1"}, f"{ANALYSIS_URL}/cancel-analysis"),
            ("post", "/api/experiments/scalability", {"max_nodes": 20}, f"{ACCESS_POINT_URL}/experiments/scalability"),
            ("delete", "/api/experiments/scalability/3", None, f"{ACCESS_POINT_URL}/experiments/scalability/3"),
            ("get", "/api/experiments/scalability/3/proposal?strategy=local_search", None,
             f"{ACCESS_POINT_URL}/experiments/scalability/3/proposal?strategy=local_search"),
        ]
        for method, path, payload, url in cases:
            with self.subTest(method=method, path=path):
                self.http[method].reset_mock()
                self.http[method].return_value = FakeResponse({"ok": path}, status_code=207)
                response = getattr(self.client, method)(path, json=payload) if payload is not None else getattr(self.client, method)(path)

                self.assertEqual(response.status_code, 207)
                self.assertEqual(response.get_json(), {"ok": path})
                args, kwargs = self.http[method].call_args
                self.assertEqual(args[0], url)
                if payload is not None:
                    self.assertEqual(kwargs["json"], payload)

    def test_service_errors_keep_their_status_and_message(self):
        self.http["post"].return_value = FakeResponse({"success": False, "error": "Estratégia não encontrada."}, status_code=400)
        response = self.client.post("/api/analysis/analyze-graph", json={"strategy": "x"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Estratégia não encontrada.")

    def test_connection_errors_become_error_responses(self):
        for method in ("get", "post", "put", "delete"):
            self.http[method].side_effect = requests.ConnectionError("recusada")
        cases = [
            ("get", "/api/access_points"),
            ("post", "/api/analysis/analyze-graph"),
            ("put", "/api/access_points/a"),
            ("delete", "/api/experiments/scalability/1"),
            ("post", "/api/analysis/analyze-graph-stream"),
            ("get", "/api/experiments/scalability/1/export?format=csv"),
        ]
        for method, path in cases:
            with self.subTest(path=path):
                response = getattr(self.client, method)(path, json={}) if method in ("post", "put") else getattr(self.client, method)(path)
                self.assertEqual(response.status_code, 500)
                self.assertEqual(response.get_json()["error"], CONNECTION_ERROR)

    def test_scalability_export_keeps_the_content_type_and_file_name(self):
        csv = b"nodes,strategy\n10,greedy\n"
        disposition = 'attachment; filename="escalabilidade-3.csv"'
        self.http["get"].return_value = FakeResponse(
            content=csv, content_type="text/csv; charset=utf-8", headers={"Content-Disposition": disposition}
        )
        response = self.client.get("/api/experiments/scalability/3/export?format=csv")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, csv)
        self.assertEqual(response.headers["Content-Type"], "text/csv; charset=utf-8")
        self.assertEqual(response.headers["Content-Disposition"], disposition)
        args, kwargs = self.http["get"].call_args
        self.assertEqual(args[0], f"{ACCESS_POINT_URL}/experiments/scalability/3/export")
        self.assertEqual(kwargs["params"], {"format": "csv"})

    def test_analysis_stream_forwards_the_events(self):
        events = b'{"type": "started"}\n{"type": "result"}\n'
        upstream = FakeResponse(content=events, content_type="application/x-ndjson")
        self.http["post"].return_value = upstream
        response = self.client.post("/api/analysis/analyze-graph-stream", json={"strategy": "greedy"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/x-ndjson")
        self.assertEqual(response.get_data(), events)
        self.assertEqual(self.http["post"].call_args.args[0], f"{ANALYSIS_URL}/analyze-graph-stream")
        self.assertTrue(upstream.closed)

    def test_experiments_page_opens_in_the_requested_mode(self):
        for path, mode in (("/experiments", "scalability"), ("/experiments?mode=comparison", "comparison"), ("/scalability", "scalability")):
            with self.subTest(path=path):
                html = self.client.get(path).get_data(as_text=True)
                self.assertIn(f'window.EXPERIMENT_MODE = "{mode}"', html)

    def test_non_json_responses_are_forwarded_as_text(self):
        self.http["get"].return_value = FakeResponse(content=b"pong", content_type="text/plain")
        response = self.client.get("/zabbix/hosts")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), "pong")


if __name__ == "__main__":
    unittest.main()
