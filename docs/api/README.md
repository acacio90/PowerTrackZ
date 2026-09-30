# API Documentation

**English** | [Português](README.pt-BR.md)

## Main Entry Point

The frontend runs at `http://localhost:3000` and exposes the web pages and the `/api/*` routes used by the interface. Internally, it forwards the calls to `access_point_service` and `analysis_service`.

## Frontend Service (Port 3000)

```http
GET /health
GET /
GET /infrastructure
GET /hosts (redirects to /infrastructure)
GET /register (redirects to /infrastructure)
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
GET /api/analysis/channel-plan
POST /api/analysis/analyze-graph
POST /api/analysis/backtracking
POST /api/analysis/analyze-graph-stream
POST /api/analysis/backtracking-stream
POST /api/analysis/cancel-analysis
POST /api/analysis/collision-graph
```

## Access Point Service (Port 5004)

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

`GET /access_points/{id}` returns the AP with the same fields as the listing (`id`, `name`, `channel`, `frequency`, `bandwidth`, `latitude`, `longitude` and `last_update`), or HTTP 404 when the identifier does not exist. The frontend route `GET /api/access_points/{id}` passes through the same response.

## Analysis Service (Port 5002)

```http
GET /health
GET /analyze
GET /strategies
GET /capabilities
GET /channel-plan
POST /analyze-graph
POST /backtracking
POST /analyze-graph-stream
POST /backtracking-stream
POST /cancel-analysis
POST /compare-strategies
POST /collision-graph
```

Besides the `strategies` map (name and description), `GET /strategies` returns the `strategy_details` list with the parameters accepted by each strategy:

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

The analysis routes receive these values in `parameters`. Values outside the declared type or range return HTTP 400 with the message in `error`. The details are in [services/analysis_service/README.md](../../services/analysis_service/README.md).

`GET /channel-plan` returns the channels that the interface offers when editing a configuration, grouped by frequency and bandwidth:

```json
{
  "success": true,
  "valid": {"2.4 GHz": {"20 MHz": ["1", "2", "..."], "40 MHz": ["1", "..."]}, "5 GHz": {"...": []}, "6 GHz": {"...": []}},
  "profiles": {"2.4 GHz": {"40 MHz": ["1", "11"], "20 MHz": ["1", "6", "11"]}, "5 GHz": {"...": []}}
}
```

`valid` lists every channel allowed in Brazil and is used when registering and editing APs. `profiles` lists the default profiles the strategies can propose, and `options`, one option per distinct channel block at each width, used to choose the search profiles.

The analysis routes accept the `channels` field, in the `profiles` format, with the channels the strategies may use in each band; bands that are not given use the default. Each band is solved in its own graph, and the response reports the per-band results in `execution.bands`. The details are in [services/analysis_service/README.md](../../services/analysis_service/README.md).
