"""Testes da interface no Chrome headless, com os servicos do docker compose no ar.

Abrem as paginas pelo protocolo DevTools e conferem erros de JavaScript, os fluxos principais, o contraste AA do
texto visivel e a rolagem horizontal. As requisicoes que gravariam dados sao bloqueadas no navegador. Sao pulados,
com aviso, quando o Chrome, o websocket-client ou os servicos nao estao disponiveis. Ver o CONTRIBUTING.
"""
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
import warnings

try:
    import websocket
except ImportError:  # dependencia de desenvolvimento (requirements-dev.txt)
    websocket = None

FRONTEND_URL = os.environ.get("PTZ_FRONTEND_URL", "http://localhost:3000").rstrip("/")
PAGES = ["/", "/infrastructure", "/analysis", "/scalability"]
WIDTHS = (1280, 600)

# Rotas que podem receber POST sem gravar dados: as analises e a geracao de topologia (que so devolve os APs).
WRITE_ALLOWED_PREFIXES = ("/api/analysis/", "/api/access_points/generate")

CONTRAST_SCRIPT = r"""
(() => {
  const parse = c => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; };
  const lum = ([r, g, b]) => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const blend = (top, bottom) => { const a = top[3]; return [top[0] * a + bottom[0] * (1 - a), top[1] * a + bottom[1] * (1 - a), top[2] * a + bottom[2] * (1 - a), 1]; };
  const background = el => {
    const layers = [];
    for (let e = el; e; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.backgroundImage !== 'none' && !cs.backgroundImage.startsWith('url')) return null;
      const c = parse(cs.backgroundColor);
      if (c && c[3] > 0) { layers.push(c); if (c[3] >= 1) break; }
    }
    let base = [255, 255, 255, 1];
    for (let i = layers.length - 1; i >= 0; i--) base = blend(layers[i], base);
    return base;
  };
  const visible = el => {
    for (let e = el; e; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) return false;
    }
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const failures = [];
  const seen = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const el = n.parentElement;
    if (!el || seen.has(el) || !n.textContent.trim()) continue;
    seen.add(el);
    // Mapa (Leaflet), elementos desabilitados e opcoes de listas ficam fora (o WCAG isenta componentes inativos).
    if (el.closest('.leaflet-container, script, style, option, :disabled, [aria-disabled="true"]') || !visible(el)) continue;
    const cs = getComputedStyle(el);
    const fg = parse(el instanceof SVGElement ? cs.fill : cs.color);
    const bg = background(el);
    if (!fg || !bg) continue;
    const color = fg[3] < 1 ? blend(fg, bg) : fg;
    const [a, b] = [lum(color) + 0.05, lum(bg) + 0.05];
    const ratio = Math.max(a, b) / Math.min(a, b);
    const size = parseFloat(cs.fontSize);
    const need = (size >= 24 || (+cs.fontWeight >= 700 && size >= 18.66)) ? 3 : 4.5;
    if (ratio < need) failures.push(`${n.textContent.trim().slice(0, 40)} (${ratio.toFixed(2)} < ${need})`);
  }
  return failures;
})()
"""


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def find_chrome():
    candidates = [
        os.environ.get("CHROME_PATH"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ] + [shutil.which(name) for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")]
    return next((path for path in candidates if path and os.path.exists(path)), None)


def services_unavailable_reason():
    for path in ("/health", "/api/analysis/strategies", "/api/access_points"):
        try:
            with urllib.request.urlopen(FRONTEND_URL + path, timeout=5) as response:
                if response.status != 200:
                    return f"{path} respondeu {response.status}"
        except (urllib.error.URLError, OSError) as error:
            return f"{FRONTEND_URL}{path} indisponível ({error})"
    return None


class Browser:
    """Cliente minimo do protocolo DevTools: comandos, erros de JavaScript e bloqueio das gravacoes."""

    def __init__(self, chrome_path):
        self.port = free_port()
        self.profile = tempfile.mkdtemp(prefix="ptz-browser-tests-")
        self.process = subprocess.Popen(
            [chrome_path, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
             f"--remote-debugging-port={self.port}", f"--user-data-dir={self.profile}", "--force-prefers-reduced-motion",
             "about:blank"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        page = None
        for _ in range(100):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json", timeout=2) as response:
                    page = next(target for target in json.load(response) if target["type"] == "page")
                break
            except (urllib.error.URLError, OSError, StopIteration):
                time.sleep(0.2)
        if not page:
            self.close()
            raise RuntimeError("O Chrome não abriu a porta de depuração.")
        self.socket = websocket.create_connection(page["webSocketDebuggerUrl"], suppress_origin=True, timeout=120)
        self.next_id = 0
        self.errors = []
        self.blocked = []
        self.call("Runtime.enable")
        self.call("Network.setCacheDisabled", cacheDisabled=True)
        self.call("Fetch.enable", patterns=[{"urlPattern": "*", "requestStage": "Request"}])

    def _handle_event(self, message):
        method = message.get("method")
        params = message.get("params", {})
        if method == "Runtime.exceptionThrown":
            details = params["exceptionDetails"]
            self.errors.append((details.get("exception") or {}).get("description") or details.get("text"))
        elif method == "Runtime.consoleAPICalled" and params.get("type") == "error":
            self.errors.append(" ".join(str(arg.get("value", arg.get("description", ""))) for arg in params.get("args", [])))
        elif method == "Fetch.requestPaused":
            request = params["request"]
            path = urllib.parse.urlparse(request["url"]).path
            writes = request["method"] in ("POST", "PUT", "PATCH", "DELETE")
            if writes and not path.startswith(WRITE_ALLOWED_PREFIXES):
                self.blocked.append(f"{request['method']} {path}")
                self._send("Fetch.failRequest", requestId=params["requestId"], errorReason="BlockedByClient")
            else:
                self._send("Fetch.continueRequest", requestId=params["requestId"])

    def _send(self, method, **params):
        self.next_id += 1
        self.socket.send(json.dumps({"id": self.next_id, "method": method, "params": params}))
        return self.next_id

    def call(self, method, **params):
        request_id = self._send(method, **params)
        while True:
            message = json.loads(self.socket.recv())
            if message.get("id") == request_id:
                if "error" in message:
                    raise RuntimeError(f"{method}: {message['error']}")
                return message.get("result", {})
            self._handle_event(message)

    def evaluate(self, expression):
        result = self.call("Runtime.evaluate", expression=expression, returnByValue=True, awaitPromise=True)
        return result.get("result", {}).get("value")

    def wait_for(self, expression, timeout=60):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.evaluate(expression):
                return True
            time.sleep(0.25)
        return False

    def open(self, path, width=1280):
        self.call("Emulation.setDeviceMetricsOverride", width=width, height=900, deviceScaleFactor=1, mobile=False)
        self.call("Page.enable")
        self.call("Page.navigate", url=FRONTEND_URL + path)
        self.wait_for("document.readyState === 'complete'", timeout=30)
        # Deixa os scripts da pagina carregarem os dados dos servicos.
        time.sleep(2)
        self.evaluate("document.getAnimations().forEach(a => { try { a.finish(); } catch (e) {} })")

    def close(self):
        try:
            self.socket.close()
        except Exception:
            pass
        self.process.terminate()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
        shutil.rmtree(self.profile, ignore_errors=True)


class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reason = None
        chrome = find_chrome()
        if websocket is None:
            reason = "websocket-client não instalado (pip install -r services/frontend_service/requirements-dev.txt)"
        elif not chrome:
            reason = "Chrome não encontrado (informe o caminho em CHROME_PATH)"
        else:
            reason = services_unavailable_reason()
        if reason:
            warnings.warn(f"Testes da interface pulados: {reason}")
            raise unittest.SkipTest(reason)
        cls.browser = Browser(chrome)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()

    def setUp(self):
        self.browser.errors.clear()
        self.browser.blocked.clear()

    def assert_no_javascript_errors(self, context):
        self.assertEqual(self.browser.errors, [], f"erros de JavaScript em {context}")

    def test_pages_load_without_javascript_errors(self):
        for path in PAGES + ["/?open_config=1"]:
            with self.subTest(path=path):
                self.browser.errors.clear()
                self.browser.open(path)
                self.assert_no_javascript_errors(path)

    def test_infrastructure_modals_open_and_close(self):
        browser = self.browser
        browser.open("/infrastructure")
        for button, modal, close in (
            ("btn-add-point", "modal-add-point", "close-modal"),
            ("btn-load-points", "modal-load-points", "close-load-modal"),
        ):
            with self.subTest(modal=modal):
                browser.evaluate(f"document.getElementById('{button}').click()")
                self.assertTrue(browser.wait_for(f"getComputedStyle(document.getElementById('{modal}')).display !== 'none'", 5))
                browser.evaluate(f"document.getElementById('{close}').click()")
                self.assertTrue(browser.wait_for(f"getComputedStyle(document.getElementById('{modal}')).display === 'none'", 5))
        self.assert_no_javascript_errors("modais da infraestrutura")

    def test_generates_a_topology_until_the_review_without_saving(self):
        browser = self.browser
        browser.open("/infrastructure")
        browser.evaluate("document.getElementById('btn-load-points').click()")
        browser.evaluate("document.getElementById('btn-load-generate').click()")
        browser.evaluate(
            "document.getElementById('generate-node-count').value = '30';"
            "document.getElementById('generate-min-degree').value = '3';"
            "document.getElementById('generate-seed').value = '2026';"
            "document.getElementById('submit-load-generate').click()"
        )
        self.assertTrue(browser.wait_for("!document.getElementById('load-review').hidden", 30))
        self.assertTrue(browser.wait_for("!document.getElementById('load-review-metrics').hidden", 30))
        self.assertEqual(browser.evaluate("document.querySelectorAll('#load-review-body tr').length"), 30)
        browser.evaluate("document.getElementById('close-load-modal').click()")
        self.assertEqual(browser.blocked, [])
        self.assert_no_javascript_errors("geração de topologia")

    def test_runs_a_strategy_until_the_summary(self):
        browser = self.browser
        browser.open("/analysis")
        self.assertTrue(browser.wait_for("!!document.querySelector('[data-strategy=\"greedy\"]')", 20))
        browser.evaluate("document.querySelector('[data-strategy=\"greedy\"]').click()")
        browser.evaluate("document.getElementById('analysis-run-button').click()")
        self.assertTrue(browser.wait_for("!document.getElementById('analysis-summary').hidden", 120))
        self.assertEqual(browser.evaluate("document.querySelector('.analysis-tab.is-active').dataset.tab"), "resumo")
        self.assertIn("Guloso", browser.evaluate("document.querySelector('#analysis-summary .analysis-summary-run').textContent"))
        self.assertEqual(browser.blocked, [])
        self.assert_no_javascript_errors("execução da análise")

    def test_scalability_page_lists_the_strategies(self):
        browser = self.browser
        browser.open("/scalability")
        self.assertTrue(browser.wait_for("document.querySelectorAll('input[name=\"strategy\"]').length > 0", 20))
        self.assert_no_javascript_errors("teste de escalabilidade")

    def test_visible_text_meets_contrast_aa(self):
        for width in WIDTHS:
            for path in PAGES:
                with self.subTest(width=width, path=path):
                    self.browser.open(path, width)
                    self.assertEqual(self.browser.evaluate(CONTRAST_SCRIPT), [])

    def test_requests_that_write_data_are_blocked(self):
        self.browser.open("/")
        status = self.browser.evaluate(
            "fetch('/api/access_points', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'})"
            ".then(() => 'enviada', () => 'bloqueada')"
        )
        self.assertEqual(status, "bloqueada")
        self.assertEqual(self.browser.blocked, ["POST /api/access_points"])
        self.browser.errors.clear()

    def test_contrast_check_detects_low_contrast_text(self):
        self.browser.open("/")
        self.browser.evaluate(
            "const probe = document.createElement('p'); probe.textContent = 'Texto claro demais';"
            "probe.style.cssText = 'color: #c8c8c8; background: #ffffff; font-size: 14px'; document.body.prepend(probe);"
        )
        failures = self.browser.evaluate(CONTRAST_SCRIPT)
        self.assertEqual(len(failures), 1)
        self.assertIn("Texto claro demais", failures[0])

    def test_no_horizontal_scroll_at_600_px(self):
        for path in PAGES:
            with self.subTest(path=path):
                self.browser.open(path, 600)
                overflow = self.browser.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                self.assertLessEqual(overflow, 0)


if __name__ == "__main__":
    unittest.main()
