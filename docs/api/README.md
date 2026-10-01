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
GET /scalability
GET /api/experiments/scalability
POST /api/experiments/scalability
GET /api/experiments/scalability/{id}
DELETE /api/experiments/scalability/{id}
POST /api/experiments/scalability/{id}/cancel
GET /api/experiments/scalability/{id}/export?format=csv|json
GET /api/analysis/strategies
GET /api/analysis/capabilities
GET /api/analysis/channel-plan
POST /api/analysis/graph-metrics
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
GET /experiments/scalability
POST /experiments/scalability
GET /experiments/scalability/{id}
DELETE /experiments/scalability/{id}
POST /experiments/scalability/{id}/cancel
GET /experiments/scalability/{id}/export?format=csv|json
```

`POST /access_points/generate` takes `node_count` (2 to 1000), `min_degree` (1 to `node_count` − 1; the former name, `clique_factor`, is still accepted) and, optionally, `seed` (integer from 0 to 4294967295), and returns in `payload` the APs, the links and `metadata`, with the seed used in `metadata.seed`. The same seed and parameters generate the same topology; without `seed`, one is drawn.

`POST /experiments/scalability` starts the scalability test in the background and answers HTTP 202 with the created run. It takes `max_nodes` (2 to 1000), `step`, `min_degree`, `seed` (optional), `strategies` (implemented strategies; default: all), `time_limit_seconds` (greater than 0 and up to 3600), `thread_count` and `objective` (optimization criterion, with the same values as the analysis routes; default: `default`); invalid parameters return HTTP 400, and another run in progress, HTTP 409. `GET /experiments/scalability/{id}` returns the run, with `status` (`running`, `completed`, `cancelled`, `failed` or `interrupted`), `progress`, `version` (`commit`, `branch` and `tag`, read from the git repository mounted at `/repo-git`), `parameters`, `strategies` (with `exact`), `breaks` (the break size of each strategy) and `points` (one point per size and strategy). The listing omits `points`, and the export returns the CSV or the JSON as a file; the CSV reports the objective used in its last column, `objective` (runs made before it appear as `default`). The service calls analysis_service through `ANALYSIS_SERVICE_URL`.

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
POST /graph-metrics
```

Besides the `strategies` map (name and description), `GET /strategies` returns the `strategy_details` list with the parameters accepted by each strategy, whether it is an exact method (`exact`) and its family (`family`: `exact`, `constructive` or `metaheuristic`), which the interface uses to group the strategies. In each parameter, `advanced` tells whether the interface shows it under the advanced parameters:

```json
{
  "name": "backtracking",
  "implemented": true,
  "exact": true,
  "family": "exact",
  "parameters": [
    {"name": "thread_count", "label": "Threads", "type": "integer", "default": 1, "min": 1, "max": 256, "unit": null, "zero_disables": false, "advanced": true, "optional": false},
    {"name": "time_limit_seconds", "label": "Limite de tempo", "type": "number", "default": 60, "min": 0, "max": 3600, "unit": "s", "zero_disables": true, "advanced": false, "optional": false}
  ]
}
```

An optional parameter (`optional: true`) has no default (`default` is null), and `optional_label` tells what happens without a value: the metaheuristics' seed is drawn (`Sorteada`), and Simulated Annealing's initial temperature is estimated (`Estimada`). A choice parameter (`type: "choice"`) lists its options in `options`, with `value` and `label`, and the default option in `default`, without `min` and `max`:

```json
{"name": "initial_solution", "label": "Solução inicial", "type": "choice", "default": "greedy", "options": [{"value": "greedy", "label": "Guloso"}, {"value": "random", "label": "Aleatória"}], "unit": null, "zero_disables": false, "advanced": true, "optional": false}
```

In the same response, `objectives` lists the accepted optimization criteria, and `default_objective`, the default:

```json
{"name": "energy_tiebreak", "label": "Energia no desempate", "description": "...", "order": ["conflicts", "interference", "power"]}
```

The analysis routes receive the criterion in the `objective` field (`default`, `energy_tiebreak` or `energy_first`; without the field, `default`) and report it in `execution.objective`. An unknown objective returns HTTP 400.

The analysis routes receive these values in `parameters`. Values outside the declared type or range, and options outside the list, return HTTP 400 with the message in `error`. The details are in [services/analysis_service/README.md](../../services/analysis_service/README.md).

In the metaheuristics (`metaheuristic` family: `local_search`, `simulated_annealing`, `tabu_search` and `genetic`), the response also reports:

- `execution.seed`: the seed used, given in `parameters.seed` or drawn; repeating the request with it reproduces the result (except when the search stops at the time limit);
- `execution.search.iterations` and, in each band, `search.iterations`: the iterations run;
- `stop_reason`: besides `completed`, `time_limit` and `cancelled`, the reasons `iteration_limit` (iteration limit), `no_improvement` (iterations without improvement) and `min_temperature` (Simulated Annealing's minimum temperature);
- in Simulated Annealing, each band reports in `search` the initial and final temperatures, whether the initial one was estimated, the levels visited and the worsenings accepted, and, in Tabu Search, the moves evaluated, forbidden, accepted by aspiration and worsening, and, in the Genetic Algorithm, the population, the evaluations and the generations in which the best got worse (in the GA, each iteration is a generation);
- `execution.bands[].convergence`: the band's convergence curve, with the best solution at the initial solution, at each improvement and at the end:

```json
[{"iteration": 0, "time_ms": 0.2, "conflicts": 10, "interference": 241.4, "bandwidth": 240, "power_w": 111.0}, {"iteration": 11, "time_ms": 0.3, "conflicts": 9, "interference": 230.9, "bandwidth": 240, "power_w": 111.0}]
```

On the *streaming* route, the metaheuristics' progress includes `iteration`.

`POST /graph-metrics` takes `aps`, like the analysis routes, and returns the metrics of the graph the analysis would build (`nodes`, `edges`, `density`, `average_degree` and `max_degree`), in total and in `bands`, without running a strategy. APs without `raio` use the band's default radius: 20 m in 2.4 GHz, 15 m in 5 GHz and 12 m in 6 GHz.

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
