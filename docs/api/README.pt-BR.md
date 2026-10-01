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
GET /experiments/scalability
POST /experiments/scalability
GET /experiments/scalability/{id}
DELETE /experiments/scalability/{id}
POST /experiments/scalability/{id}/cancel
GET /experiments/scalability/{id}/export?format=csv|json
```

`POST /access_points/generate` recebe `node_count` (2 a 1000), `min_degree` (1 a `node_count` − 1; o nome anterior, `clique_factor`, continua aceito) e, opcionalmente, `seed` (inteiro de 0 a 4294967295), e devolve em `payload` os APs, as ligações e `metadata`, com a semente usada em `metadata.seed`. A mesma semente e os mesmos parâmetros geram a mesma topologia; sem `seed`, uma é sorteada.

`POST /experiments/scalability` inicia o teste de escalabilidade em segundo plano e responde HTTP 202 com a execução criada. Recebe `max_nodes` (2 a 1000), `step`, `min_degree`, `seed` (opcional), `strategies` (estratégias implementadas; padrão: todas), `time_limit_seconds` (maior que 0 e até 3600), `thread_count` e `objective` (critério de otimização, com os mesmos valores das rotas de análise; padrão: `default`); parâmetros inválidos retornam HTTP 400, e outra execução em andamento, HTTP 409. `GET /experiments/scalability/{id}` devolve a execução, com `status` (`running`, `completed`, `cancelled`, `failed` ou `interrupted`), `progress`, `version` (`commit`, `branch` e `tag`, lidos do repositório git montado em `/repo-git`), `parameters`, `strategies` (com `exact`), `breaks` (o tamanho de quebra de cada estratégia) e `points` (um ponto por tamanho e estratégia). A listagem omite `points`, e a exportação devolve o CSV ou o JSON como arquivo; o CSV traz o objetivo usado na última coluna, `objective` (execuções anteriores a ele aparecem como `default`). O serviço chama o analysis_service pela `ANALYSIS_SERVICE_URL`.

`GET /access_points/{id}` devolve o AP com os mesmos campos da listagem (`id`, `name`, `channel`, `frequency`, `bandwidth`, `latitude`, `longitude` e `last_update`) ou HTTP 404 quando o identificador não existe. A rota `GET /api/access_points/{id}` do frontend repassa a mesma resposta.

## Analysis Service (Porta 5002)

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

`GET /strategies` devolve, além do mapa `strategies` (nome e descrição), a lista `strategy_details` com os parâmetros aceitos por cada estratégia, se ela é um método exato (`exact`) e a sua família (`family`: `exact`, `constructive` ou `metaheuristic`), que a interface usa para agrupar as estratégias. Em cada parâmetro, `advanced` indica se a interface o mostra entre os parâmetros avançados:

```json
{
  "name": "backtracking",
  "implemented": true,
  "exact": true,
  "family": "exact",
  "parameters": [
    {"name": "thread_count", "label": "Threads", "type": "integer", "default": 1, "min": 1, "max": 256, "unit": null, "zero_disables": false, "advanced": true},
    {"name": "time_limit_seconds", "label": "Limite de tempo", "type": "number", "default": 60, "min": 0, "max": 3600, "unit": "s", "zero_disables": true, "advanced": false}
  ]
}
```

Na mesma resposta, `objectives` lista os critérios de otimização aceitos, e `default_objective`, o padrão:

```json
{"name": "energy_tiebreak", "label": "Energia no desempate", "description": "...", "order": ["conflicts", "interference", "power"]}
```

As rotas de análise recebem o critério no campo `objective` (`default`, `energy_tiebreak` ou `energy_first`; sem o campo, `default`) e o informam em `execution.objective`. Um objetivo desconhecido retorna HTTP 400.

As rotas de análise recebem esses valores em `parameters`. Valores fora do tipo ou do intervalo declarado retornam HTTP 400 com a mensagem em `error`. Os detalhes estão em [services/analysis_service/README.pt-BR.md](../../services/analysis_service/README.pt-BR.md).

`POST /graph-metrics` recebe `aps`, como as rotas de análise, e devolve as métricas do grafo que a análise montaria (`nodes`, `edges`, `density`, `average_degree` e `max_degree`), no total e em `bands`, sem executar estratégia. APs sem `raio` usam o raio padrão da faixa: 20 m em 2,4 GHz, 15 m em 5 GHz e 12 m em 6 GHz.

`GET /channel-plan` devolve os canais que a interface oferece na edição de uma configuração, agrupados por frequência e largura de banda:

```json
{
  "success": true,
  "valid": {"2.4 GHz": {"20 MHz": ["1", "2", "..."], "40 MHz": ["1", "..."]}, "5 GHz": {"...": []}, "6 GHz": {"...": []}},
  "profiles": {"2.4 GHz": {"40 MHz": ["1", "11"], "20 MHz": ["1", "6", "11"]}, "5 GHz": {"...": []}}
}
```

`valid` lista todos os canais permitidos no Brasil e é usado no cadastro e na edição de APs. `profiles` lista os perfis padrão que as estratégias podem propor, e `options`, uma opção por bloco de canais distinto em cada largura, usada para escolher os perfis de busca.

As rotas de análise aceitam o campo `channels`, no formato de `profiles`, com os canais que as estratégias podem usar em cada faixa; as faixas não informadas usam o padrão. Cada faixa é resolvida num grafo próprio, e a resposta traz os resultados por faixa em `execution.bands`. Os detalhes estão em [services/analysis_service/README.pt-BR.md](../../services/analysis_service/README.pt-BR.md).
