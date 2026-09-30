# Documentação da API

[English](README.md) | **Português**

## Entrada Principal

O frontend roda em `http://localhost:3000` e expõe as páginas web e as rotas `/api/*` usadas pela interface. Internamente, ele encaminha as chamadas para o `access_point_service` e o `analysis_service`.

## Frontend Service (Porta 3000)

```http
GET /health
GET /
GET /infrastructure
GET /hosts (redireciona para /infrastructure)
GET /register (redireciona para /infrastructure)
GET /analysis
GET /settings
GET /zabbix/hosts
POST /zabbix/save-config
POST /zabbix/test-connection
GET /api/access_points
POST /api/access_points
POST /api/access_points/import
POST /api/access_points/generate
GET /api/access_points/{id}
PUT /api/access_points/{id}
DELETE /api/access_points/{id}
GET /api/analysis/strategies
GET /api/analysis/capabilities
POST /api/analysis/analyze-graph
POST /api/analysis/backtracking
POST /api/analysis/analyze-graph-stream
POST /api/analysis/backtracking-stream
POST /api/analysis/cancel-analysis
POST /api/analysis/collision-graph
```

## Access Point Service (Porta 5004)

```http
GET /health
GET /hosts
GET /hosts/{host_id}
GET /access_points
POST /access_points
POST /access_points/import
POST /access_points/generate
GET /access_points/{id}
PUT /access_points/{id}
DELETE /access_points/{id}
POST /sync/zabbix
GET /zabbix/hosts
GET /zabbix/groups
GET /zabbix/config
POST /zabbix/save-config
POST /zabbix/test-connection
```

`GET /access_points/{id}` devolve o AP com os mesmos campos da listagem (`id`, `name`, `channel`, `frequency`, `bandwidth`, `latitude`, `longitude` e `last_update`) ou HTTP 404 quando o identificador não existe. A rota `GET /api/access_points/{id}` do frontend repassa a mesma resposta.

## Analysis Service (Porta 5002)

```http
GET /health
GET /analyze
GET /strategies
GET /capabilities
POST /analyze-graph
POST /backtracking
POST /analyze-graph-stream
POST /backtracking-stream
POST /cancel-analysis
POST /compare-strategies
POST /collision-graph
```

`GET /strategies` devolve, além do mapa `strategies` (nome e descrição), a lista `strategy_details` com os parâmetros aceitos por cada estratégia:

```json
{
  "name": "backtracking",
  "implemented": true,
  "parameters": [
    {"name": "thread_count", "label": "Threads", "type": "integer", "default": 1, "min": 1, "max": 256, "unit": null, "zero_disables": false},
    {"name": "time_limit_seconds", "label": "Limite de tempo", "type": "number", "default": 60, "min": 0, "max": 3600, "unit": "s", "zero_disables": true}
  ]
}
```

As rotas de análise recebem esses valores em `parameters`. Valores fora do tipo ou do intervalo declarado retornam HTTP 400 com a mensagem em `error`. Os detalhes estão em [services/analysis_service/README.pt-BR.md](../../services/analysis_service/README.pt-BR.md).
