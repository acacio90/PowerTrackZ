"""Teste de escalabilidade incremental das estrategias de analise.

Uma unica topologia e gerada pela semente com o tamanho maximo, e as instancias sao os seus prefixos (os primeiros
n APs), de modo que cada instancia contem a anterior. Para cada tamanho, as estrategias sao executadas pelo
analysis_service, primeiro as exatas, que servem de referencia de otimo para as demais. Uma estrategia quebra no
primeiro tamanho em que deixa de resolver o problema: um metodo exato, quando para pelo limite de tempo sem
comprovar o otimo; um metodo deterministico sem garantia de otimo, quando excede o limite de tempo; uma estrategia
estocastica (que declara semente), quando a maioria das repeticoes para pelo limite de tempo antes dos proprios
criterios de parada. Depois de quebrar, ela deixa de ser executada nos tamanhos seguintes.

As estrategias estocasticas sao repetidas por tamanho, com sementes derivadas da semente do teste (as mesmas em
todas as estrategias e tamanhos), e cada repeticao vira um ponto; as estatisticas por tamanho saem dos pontos.

No modo Comparacao (#90), a instancia e uma copia dos APs cadastrados, tirada no inicio, e as estrategias sao
executadas sobre ela com o mesmo criterio, os mesmos canais e as mesmas sementes; da melhor repeticao de cada uma,
guarda-se a execucao e a configuracao proposta, para abri-la na pagina de Analise.
"""
import csv
import hashlib
import io
import json
import statistics
import logging
import os
import threading
import time
from datetime import datetime

import requests

from access_point_generator import MAX_NODE_COUNT, generate_access_point_infrastructure, resolve_seed
from models import AccessPoint, ScalabilityRun, db
from version import read_version

logger = logging.getLogger(__name__)

DEFAULT_PARAMETERS = {
    "max_nodes": 200,
    "step": 10,
    "min_degree": 3,
    "time_limit_seconds": 10,
    "thread_count": 1,
    "objective": "default",
    "repetitions": 1,
}
MAX_REPETITIONS = 100

POINT_FIELDS = [
    "nodes", "edges", "density", "average_degree", "strategy", "exact", "duration_seconds", "wall_seconds",
    "conflicts_before", "conflicts", "interference_before", "interference", "power_w", "nodes_explored",
    "optimal", "stop_reason", "broke", "gap_conflicts", "gap_interference",
]
# Colunas acrescentadas depois de "objective" no CSV (#124): tempo de CPU e energia estimada do processamento.
PROCESSING_FIELDS = ["cpu_seconds", "processing_energy_j", "processing_max_energy_j"]
# Colunas acrescentadas depois delas (#86): repeticao e semente de cada ponto; e (#90) os APs alterados.
REPETITION_FIELDS = ["repetition", "seed", "changed_nodes"]
# Metricas resumidas por tamanho e estrategia (media, desvio-padrao, melhor e pior).
SUMMARY_FIELDS = ["duration_seconds", "conflicts", "interference", "power_w", "processing_energy_j", "changed_nodes"]
MODES = ("scalability", "comparison")
# Parametros que o teste define para todas as estrategias, e nao por estrategia.
SHARED_PARAMETERS = {"seed", "time_limit_seconds"}


class ScalabilityConflict(Exception):
    """Ja existe uma execucao em andamento."""


class AnalysisClient:
    """Chamadas ao analysis_service usadas pelo teste."""

    def __init__(self, base_url=None, timeout=None):
        self.base_url = (base_url or os.environ.get("ANALYSIS_SERVICE_URL", "http://analysis_service:5002")).rstrip("/")
        self.timeout = timeout or float(os.environ.get("ACCESS_POINT_HTTP_TIMEOUT", "120"))

    def _post(self, path, payload, timeout):
        response = requests.post(f"{self.base_url}{path}", json=payload, timeout=timeout)
        body = response.json()
        if not response.ok or body.get("success") is False:
            raise RuntimeError(body.get("error") or f"analysis_service respondeu {response.status_code} em {path}")
        return body

    def _catalog(self):
        response = requests.get(f"{self.base_url}/strategies", timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def strategies(self):
        return self._catalog().get("strategy_details", [])

    def objectives(self):
        """Nomes dos criterios de otimizacao aceitos pelo analysis_service."""
        return [objective["name"] for objective in self._catalog().get("objectives", [])] or ["default"]

    def graph_metrics(self, aps):
        return self._post("/graph-metrics", {"aps": aps}, self.timeout)

    def analyze(self, aps, strategy, parameters, time_limit_seconds, objective="default", channels=None):
        # Cada faixa tem o proprio limite de tempo; a margem cobre a montagem e a serializacao da resposta.
        timeout = max(self.timeout, time_limit_seconds * 4 + 60)
        payload = {"aps": aps, "strategy": strategy, "parameters": parameters, "objective": objective}
        if isinstance(channels, dict):
            payload["channels"] = channels
        return self._post("/analyze-graph", payload, timeout)


def _integer(data, name, minimum, maximum):
    value = data.get(name, DEFAULT_PARAMETERS.get(name))
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{name} deve ser um inteiro entre {minimum} e {maximum}")
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} deve ser um inteiro entre {minimum} e {maximum}") from None
    if number != float(value) or number < minimum or number > maximum:
        raise ValueError(f"{name} deve ser um inteiro entre {minimum} e {maximum}")
    return number


def validate_parameters(data, strategy_details, objectives=("default",)):
    """Valida os parametros do teste e devolve-os completos, com a semente resolvida."""
    data = data or {}
    implemented = [detail["name"] for detail in strategy_details if detail.get("implemented")]
    mode = data.get("mode") or "scalability"
    if mode not in MODES:
        raise ValueError("mode deve ser scalability ou comparison")
    if mode == "comparison":
        # A instancia e a infraestrutura cadastrada: nao ha tamanhos nem topologia gerada.
        max_nodes = step = min_degree = None
    else:
        max_nodes = _integer(data, "max_nodes", 2, MAX_NODE_COUNT)
        step = _integer(data, "step", 1, max_nodes)
        min_degree = _integer(data, "min_degree", 1, max_nodes - 1)
    thread_count = _integer(data, "thread_count", 1, 256)

    time_limit = data.get("time_limit_seconds", DEFAULT_PARAMETERS["time_limit_seconds"])
    if isinstance(time_limit, bool) or not isinstance(time_limit, (int, float)) or not 0 < time_limit <= 3600:
        raise ValueError("time_limit_seconds deve ser um número maior que 0 e até 3600")

    strategies = data.get("strategies") or implemented
    if not isinstance(strategies, list) or not strategies:
        raise ValueError("strategies deve ser uma lista de estratégias implementadas")
    unknown = [name for name in strategies if name not in implemented]
    if unknown:
        raise ValueError(f"Estratégias inválidas ou não implementadas: {', '.join(map(str, unknown))}")

    objective = data.get("objective") or DEFAULT_PARAMETERS["objective"]
    if objective not in objectives:
        raise ValueError(f"objective deve ser um dos objetivos do analysis_service: {', '.join(objectives)}")

    repetitions = _integer(data, "repetitions", 1, MAX_REPETITIONS)
    strategy_parameters = validate_strategy_parameters(data.get("strategy_parameters"), strategies)

    # Canais escolhidos no mapa do espectro, no formato de "profiles" do /channel-plan; o analysis_service os valida.
    channels = data.get("channels")
    if channels in (None, "padrao", {}):
        channels = "padrao"
    elif not isinstance(channels, dict):
        raise ValueError("channels deve ser um objeto por faixa e largura, como profiles em /channel-plan, ou ficar vazio")

    return {
        "mode": mode,
        "max_nodes": max_nodes,
        "step": step,
        "min_degree": min_degree,
        "seed": resolve_seed(data.get("seed")),
        "strategies": list(dict.fromkeys(strategies)),
        "time_limit_seconds": time_limit,
        "thread_count": thread_count,
        "objective": objective,
        "channels": channels,
        "repetitions": repetitions,
        "strategy_parameters": strategy_parameters,
    }


def validate_strategy_parameters(value, strategies):
    """Parametros proprios de cada estrategia: {estrategia: {parametro: valor}}. A semente e o limite de tempo sao do
    teste, e os valores sao validados pelo analysis_service ao executar."""
    if value in (None, {}):
        return {}
    if not isinstance(value, dict):
        raise ValueError("strategy_parameters deve ser um objeto com os parâmetros de cada estratégia")
    result = {}
    for name, parameters in value.items():
        if name not in strategies:
            raise ValueError(f"strategy_parameters traz a estratégia {name}, que não foi escolhida no teste")
        if not isinstance(parameters, dict):
            raise ValueError(f"Os parâmetros de {name} devem ser um objeto")
        for key, item in parameters.items():
            if isinstance(item, bool) or not isinstance(item, (int, float, str)):
                raise ValueError(f"O parâmetro {key} de {name} deve ser um número ou uma opção")
        result[name] = {key: item for key, item in parameters.items() if key not in SHARED_PARAMETERS}
    return result


def repetition_seed(test_seed, repetition):
    """Semente da repeticao (a partir de 0), derivada da semente do teste: a mesma em todas as estrategias e tamanhos."""
    digest = hashlib.sha256(f"powertrackz:{test_seed}:{repetition}".encode()).hexdigest()
    return int(digest[:8], 16)


def instance_sizes(max_nodes, step):
    """Tamanhos testados: multiplos do passo a partir de 2 APs, sempre incluindo o tamanho maximo."""
    sizes = [size for size in range(step, max_nodes + 1, step) if size >= 2]
    if not sizes or sizes[-1] != max_nodes:
        sizes.append(max_nodes)
    return sizes


def registered_aps():
    """APs cadastrados com coordenadas, no formato do gerador (os que a pagina de Analise analisa)."""
    points = AccessPoint.query.filter(AccessPoint.latitude.isnot(None), AccessPoint.longitude.isnot(None)).order_by(AccessPoint.id).all()
    return [point.to_dict() for point in points]


def proposal_key(objective, point):
    """Ordem da melhor repeticao, pelo criterio de otimizacao: conflitos e interferencia, ou a potencia primeiro."""
    conflicts = point.get("conflicts") if point.get("conflicts") is not None else float("inf")
    interference = point.get("interference") if point.get("interference") is not None else float("inf")
    power = point.get("power_w") if point.get("power_w") is not None else float("inf")
    if objective == "energy_first":
        return (power, conflicts, interference)
    if objective == "energy_tiebreak":
        return (conflicts, interference, power)
    return (conflicts, interference)


def compact_proposal(result):
    """Configuracao proposta de cada AP, a partir do graph_data da resposta."""
    nodes = (result.get("graph_data") or {}).get("nodes") or []
    return [
        {"id": node.get("id"), "channel": node.get("proposed_channel"), "bandwidth": node.get("proposed_bandwidth"),
         "frequency": node.get("proposed_frequency")}
        for node in nodes
    ]


def to_analysis_aps(aps):
    """APs do gerador no formato das rotas de analise; sem raio, o analysis_service usa o padrao da faixa."""
    return [
        {
            "id": ap["id"],
            "label": ap["name"],
            "x": ap["latitude"],
            "y": ap["longitude"],
            "channel": ap["channel"],
            "bandwidth": ap["bandwidth"],
            "frequency": ap["frequency"],
        }
        for ap in aps
    ]


def strategy_broke(exact, stop_reason, duration_seconds, time_limit_seconds):
    """Metodo exato: quebra ao parar pelo limite sem comprovar o otimo. Sem garantia de otimo: ao exceder o limite."""
    if exact:
        return stop_reason == "time_limit"
    return duration_seconds > time_limit_seconds


def stochastic_broke(stop_reasons):
    """Estrategia estocastica: quebra quando a maioria das repeticoes para pelo limite de tempo, antes dos proprios
    criterios de parada (iteracoes, iteracoes sem melhora ou temperatura minima)."""
    return sum(reason == "time_limit" for reason in stop_reasons) * 2 > len(stop_reasons)


def summarize_points(points):
    """Estatisticas por tamanho e estrategia: repeticoes, e media, desvio-padrao, melhor e pior de cada metrica."""
    groups = {}
    for point in points:
        groups.setdefault((point["nodes"], point["strategy"]), []).append(point)
    summaries = []
    for (nodes, strategy), group in groups.items():
        summary = {"nodes": nodes, "strategy": strategy, "repetitions": len(group), "broke": any(p.get("broke") for p in group)}
        for field in SUMMARY_FIELDS:
            values = [p[field] for p in group if p.get(field) is not None]
            summary[field] = {
                "mean": statistics.fmean(values) if values else None,
                "std": statistics.stdev(values) if len(values) > 1 else (0.0 if values else None),
                "min": min(values) if values else None,
                "max": max(values) if values else None,
            }
        summaries.append(summary)
    return summaries


def build_point(size, metrics, strategy, exact, result, wall_seconds, time_limit_seconds):
    execution = result.get("execution") or {}
    search = execution.get("search") or {}
    comparison = execution.get("comparison") or {}
    processing = execution.get("processing") or {}
    duration_seconds = (execution.get("duration_ms") or 0) / 1000.0
    stop_reason = search.get("stop_reason", "completed")
    return {
        "nodes": size,
        "edges": metrics.get("edges"),
        "density": metrics.get("density"),
        "average_degree": metrics.get("average_degree"),
        "strategy": strategy,
        "exact": exact,
        "duration_seconds": duration_seconds,
        "wall_seconds": wall_seconds,
        "conflicts_before": comparison.get("conflicts_before"),
        "conflicts": comparison.get("conflicts_after"),
        "interference_before": comparison.get("interference_before"),
        "interference": comparison.get("interference_after"),
        "power_w": comparison.get("power_after_w"),
        "nodes_explored": search.get("nodes_explored"),
        "optimal": bool(exact and search.get("optimal")),
        "stop_reason": stop_reason,
        "broke": strategy_broke(exact, stop_reason, duration_seconds, time_limit_seconds),
        "gap_conflicts": None,
        "gap_interference": None,
        "changed_nodes": comparison.get("changed_nodes"),
        "cpu_seconds": processing.get("cpu_seconds"),
        "processing_energy_j": processing.get("energy_j"),
        "processing_max_energy_j": processing.get("max_energy_j"),
    }


def fill_optimality_gaps(points_of_size):
    """Distancia das estrategias ate o otimo, quando algum metodo exato o comprovou naquele tamanho."""
    reference = next((point for point in points_of_size if point["exact"] and point["optimal"]), None)
    if not reference:
        return
    for point in points_of_size:
        if point["conflicts"] is not None:
            point["gap_conflicts"] = point["conflicts"] - reference["conflicts"]
        if point["interference"] is not None and reference["interference"] is not None:
            point["gap_interference"] = point["interference"] - reference["interference"]


def run_to_dict(run, include_points=True):
    parameters = json.loads(run.parameters or "{}")
    instance = parameters.pop("instance", None)
    proposals = json.loads(getattr(run, "proposals", None) or "{}")
    data = {
        "id": run.id,
        "created_at": run.created_at.isoformat() + "Z" if run.created_at else None,
        "finished_at": run.finished_at.isoformat() + "Z" if run.finished_at else None,
        "status": run.status,
        "progress": run.progress,
        "current_step": run.current_step,
        "version": json.loads(run.version or "{}"),
        "mode": parameters.get("mode", "scalability"),
        "parameters": parameters,
        # Comparacao: numero de APs da instancia e estrategias com a proposta guardada (a lista de APs fica fora).
        "instance_size": len(instance) if instance is not None else None,
        "proposals": {name: {"repetition": item.get("repetition"), "seed": item.get("seed")} for name, item in proposals.items()},
        "strategies": json.loads(run.strategies or "[]"),
        "breaks": json.loads(run.breaks or "{}"),
        "error": run.error,
    }
    if include_points:
        data["points"] = json.loads(run.points or "[]")
        data["summaries"] = summarize_points(data["points"])
    return data


def run_to_csv(run):
    data = run_to_dict(run)
    version = data["version"]
    parameters = data["parameters"]
    # Colunas novas entram no fim, para nao deslocar as existentes (leitura por posicao continua valida).
    header = (["run_id", "commit", "tag", "seed", "min_degree", "time_limit_seconds", "thread_count"] + POINT_FIELDS
              + ["objective"] + PROCESSING_FIELDS + REPETITION_FIELDS)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(header)
    for point in data["points"]:
        writer.writerow([
            data["id"], version.get("commit"), version.get("tag"), parameters.get("seed"), parameters.get("min_degree"),
            parameters.get("time_limit_seconds"), parameters.get("thread_count"),
        ] + [point.get(field) for field in POINT_FIELDS] + [
            # Execucoes anteriores ao criterio configuravel usaram o objetivo padrao.
            parameters.get("objective", "default"),
        ] + [point.get(field) for field in PROCESSING_FIELDS + REPETITION_FIELDS])
    return output.getvalue()


def mark_interrupted_runs():
    """Execucoes que estavam em andamento quando o servico parou nao serao retomadas."""
    for run in ScalabilityRun.query.filter_by(status="running").all():
        run.status = "interrupted"
        run.finished_at = datetime.utcnow()
        run.error = "Execução interrompida pela reinicialização do serviço. Execute o teste de novo."
    db.session.commit()


class ScalabilityRunner:
    """Executa um teste por vez, em segundo plano, para que execucoes simultaneas nao distorcam os tempos."""

    def __init__(self, app, client=None, clock=time.perf_counter, background=True):
        self.app = app
        self.client = client or AnalysisClient()
        self.clock = clock
        self.background = background
        self._lock = threading.Lock()
        self._active_run = None
        self._cancel = threading.Event()

    def start(self, data):
        details = self.client.strategies()
        parameters = validate_parameters(data, details, self.client.objectives())
        if parameters["mode"] == "comparison":
            instance = registered_aps()
            if not instance:
                raise ValueError("Nenhum AP cadastrado com coordenadas. Cadastre ou carregue os APs na página Sua infraestrutura.")
            # Copia da infraestrutura no inicio: a comparacao continua reprodutivel mesmo que os APs mudem depois.
            parameters["instance"] = instance
        with self._lock:
            if self._active_run is not None:
                raise ScalabilityConflict("Já existe um teste de escalabilidade em andamento. Aguarde o fim dele ou cancele-o.")
            strategies = [
                {
                    "name": detail["name"],
                    "exact": bool(detail.get("exact")),
                    "description": detail.get("description"),
                    # Estocastica: declara semente; e repetida com as sementes derivadas da semente do teste.
                    "stochastic": any(parameter.get("name") == "seed" for parameter in detail.get("parameters") or []),
                }
                for detail in details if detail["name"] in parameters["strategies"]
            ]
            run = ScalabilityRun(
                status="running",
                version=json.dumps(read_version()),
                parameters=json.dumps(parameters),
                strategies=json.dumps(strategies),
            )
            db.session.add(run)
            db.session.commit()
            self._active_run = run.id
            self._cancel.clear()

        if self.background:
            threading.Thread(target=self._execute, args=(run.id,), daemon=True).start()
        else:
            self._execute(run.id)
        return run

    def cancel(self, run_id):
        with self._lock:
            if self._active_run != run_id:
                return False
            self._cancel.set()
            return True

    def is_active(self, run_id):
        return self._active_run == run_id

    def _save(self, run_id, **fields):
        run = db.session.get(ScalabilityRun, run_id)
        for name, value in fields.items():
            setattr(run, name, value)
        db.session.commit()

    def _execute(self, run_id):
        with self.app.app_context():
            try:
                self._run(run_id)
            except Exception as error:  # noqa: BLE001 - o erro fica registrado na execucao
                logger.exception("Falha no teste de escalabilidade %s", run_id)
                self._save(run_id, status="failed", error=str(error), finished_at=datetime.utcnow(), current_step=None)
            finally:
                with self._lock:
                    self._active_run = None

    def _run(self, run_id):
        run = db.session.get(ScalabilityRun, run_id)
        parameters = json.loads(run.parameters)
        if parameters.get("mode") == "comparison":
            self._run_comparison(run_id, parameters, json.loads(run.strategies))
            return
        strategies = json.loads(run.strategies)
        # Exatas primeiro: quando comprovam o otimo, servem de referencia para as demais no mesmo tamanho.
        ordered = sorted(strategies, key=lambda strategy: not strategy["exact"])
        time_limit = parameters["time_limit_seconds"]
        objective = parameters.get("objective", "default")
        channels = parameters.get("channels")
        repetitions = parameters.get("repetitions", 1)
        own_parameters = parameters.get("strategy_parameters") or {}
        seeds = [repetition_seed(parameters["seed"], index) for index in range(repetitions)]

        topology = generate_access_point_infrastructure(parameters["max_nodes"], parameters["min_degree"], parameters["seed"])
        all_aps = to_analysis_aps(topology["aps"])
        sizes = instance_sizes(parameters["max_nodes"], parameters["step"])
        total_steps = len(sizes) * sum(repetitions if strategy.get("stochastic") else 1 for strategy in ordered)
        done_steps = 0
        points, breaks = [], {}

        for size in sizes:
            if self._cancel.is_set():
                break
            aps = all_aps[:size]
            metrics = self.client.graph_metrics(aps)
            points_of_size = []
            for strategy in ordered:
                name = strategy["name"]
                stochastic = strategy.get("stochastic", False)
                runs = seeds if stochastic else [None]
                if name in breaks or self._cancel.is_set():
                    done_steps += len(runs)
                    continue
                points_of_strategy = []
                for index, seed in enumerate(runs):
                    if self._cancel.is_set():
                        break
                    step = f"{size} APs: {name}" + (f" (repetição {index + 1} de {len(runs)})" if stochastic else "")
                    self._save(run_id, current_step=step)
                    analysis_parameters = {"thread_count": parameters["thread_count"], "time_limit_seconds": time_limit,
                                           **own_parameters.get(name, {})}
                    if seed is not None:
                        analysis_parameters["seed"] = seed
                    started = self.clock()
                    result = self.client.analyze(aps, name, analysis_parameters, time_limit, objective, channels)
                    point = build_point(size, metrics, name, strategy["exact"], result, self.clock() - started, time_limit)
                    point["repetition"] = index + 1
                    point["seed"] = seed
                    points_of_strategy.append(point)
                    done_steps += 1
                    self._save(run_id, progress=done_steps / total_steps)
                if stochastic and points_of_strategy:
                    broke = stochastic_broke([point["stop_reason"] for point in points_of_strategy])
                    for point in points_of_strategy:
                        point["broke"] = broke
                points_of_size.extend(points_of_strategy)
                if any(point["broke"] for point in points_of_strategy):
                    breaks[name] = size
            fill_optimality_gaps(points_of_size)
            points.extend(points_of_size)
            self._save(run_id, points=json.dumps(points), breaks=json.dumps(breaks))
            if len(breaks) == len(ordered):
                break

        cancelled = self._cancel.is_set()
        self._save(
            run_id,
            status="cancelled" if cancelled else "completed",
            progress=1.0 if not cancelled else done_steps / total_steps,
            current_step=None,
            finished_at=datetime.utcnow(),
            points=json.dumps(points),
            breaks=json.dumps(breaks),
        )

    def _run_comparison(self, run_id, parameters, strategies):
        """Executa as estrategias sobre a copia da infraestrutura cadastrada; guarda a melhor repeticao de cada uma."""
        ordered = sorted(strategies, key=lambda strategy: not strategy["exact"])
        time_limit = parameters["time_limit_seconds"]
        objective = parameters.get("objective", "default")
        channels = parameters.get("channels")
        own_parameters = parameters.get("strategy_parameters") or {}
        seeds = [repetition_seed(parameters["seed"], index) for index in range(parameters.get("repetitions", 1))]
        aps = to_analysis_aps(parameters["instance"])
        size = len(aps)
        metrics = self.client.graph_metrics(aps)
        total_steps = sum(len(seeds) if strategy.get("stochastic") else 1 for strategy in ordered)
        done_steps = 0
        points, proposals = [], {}

        for strategy in ordered:
            name = strategy["name"]
            stochastic = strategy.get("stochastic", False)
            runs = seeds if stochastic else [None]
            best = None
            for index, seed in enumerate(runs):
                if self._cancel.is_set():
                    break
                step = name + (f" (repetição {index + 1} de {len(runs)})" if stochastic else "")
                self._save(run_id, current_step=step)
                analysis_parameters = {"thread_count": parameters["thread_count"], "time_limit_seconds": time_limit,
                                       **own_parameters.get(name, {})}
                if seed is not None:
                    analysis_parameters["seed"] = seed
                started = self.clock()
                result = self.client.analyze(aps, name, analysis_parameters, time_limit, objective, channels)
                point = build_point(size, metrics, name, strategy["exact"], result, self.clock() - started, time_limit)
                # A comparacao nao tem ponto de quebra: o limite de tempo so encerra a busca.
                point["broke"] = False
                point["repetition"] = index + 1
                point["seed"] = seed
                points.append(point)
                if best is None or proposal_key(objective, point) < proposal_key(objective, best[0]):
                    best = (point, result)
                done_steps += 1
                self._save(run_id, progress=done_steps / total_steps)
            if best is not None:
                point, result = best
                execution = result.get("execution") or {}
                proposals[name] = {
                    "repetition": point["repetition"],
                    "seed": point["seed"],
                    "execution": execution,
                    "proposal": compact_proposal(result),
                }
            fill_optimality_gaps(points)
            self._save(run_id, points=json.dumps(points), proposals=json.dumps(proposals))
            if self._cancel.is_set():
                break

        cancelled = self._cancel.is_set()
        self._save(
            run_id,
            status="cancelled" if cancelled else "completed",
            progress=1.0 if not cancelled else done_steps / total_steps,
            current_step=None,
            finished_at=datetime.utcnow(),
            points=json.dumps(points),
            breaks=json.dumps({}),
            proposals=json.dumps(proposals),
        )


def run_proposal(run, strategy):
    """Proposta guardada da melhor repeticao de uma estrategia comparada, com a instancia e a execucao."""
    parameters = json.loads(run.parameters or "{}")
    proposals = json.loads(run.proposals or "{}")
    item = proposals.get(strategy)
    if parameters.get("mode") != "comparison" or not item:
        return None
    return {
        "run_id": run.id,
        "strategy": strategy,
        "repetition": item.get("repetition"),
        "seed": item.get("seed"),
        "objective": parameters.get("objective", "default"),
        "channels": parameters.get("channels"),
        "instance": parameters.get("instance") or [],
        "execution": item.get("execution") or {},
        "proposal": item.get("proposal") or [],
    }
