# Documentacao da API

## Entrada Principal

O frontend roda em `http://localhost:3000` e expoe as paginas web e rotas `/api/*` usadas pela interface. Internamente, ele encaminha chamadas para `access_point_service` e `analysis_service`.

## Frontend Service (Porta 3000)

```http
GET /health
GET /
GET /hosts
GET /register
POST /register
GET /analysis
GET /settings
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
PUT /access_points/{id}
DELETE /access_points/{id}
POST /sync/zabbix
GET /zabbix/hosts
GET /zabbix/groups
GET /zabbix/config
POST /zabbix/save-config
POST /zabbix/test-connection
```

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

`GET /strategies` devolve, alem do mapa `strategies` (nome e descricao), a lista `strategy_details` com os parametros aceitos por cada estrategia:

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

As rotas de analise recebem esses valores em `parameters`. Valores fora do tipo ou do intervalo declarado retornam HTTP 400 com a mensagem em `error`. Os detalhes estao em `services/analysis_service/README.md`.
