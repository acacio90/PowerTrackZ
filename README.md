# PowerTrackZ

PowerTrackZ e um sistema de monitoramento e analise de pontos de acesso WiFi, com foco em deteccao de interferencia e otimizacao de configuracoes.

## Funcionalidades

- Cadastro, importacao e geracao de pontos de acesso
- Integracao com Zabbix externo para carregar APs monitorados
- Mapa interativo no frontend com Leaflet
- Analise de colisao e otimizacao por algoritmos em C
- Execucao via Docker Compose

## Arquitetura

```text
PowerTrackZ/
├── services/
│   ├── frontend_service/       # Interface web e mapa
│   ├── access_point_service/   # CRUD, importacao, geracao e Zabbix
│   └── analysis_service/       # Algoritmos de analise
├── scripts/                    # Automacao e manutencao
├── docs/                       # Documentacao
└── docker-compose.yml
```

## Servicos

### Frontend Service (porta 3000)
- Entrada principal em `http://localhost:3000`
- Paginas web, assets e mapa interativo
- Rotas `/api/*` usadas pela interface

### Access Point Service (porta 5004)
- CRUD de pontos de acesso
- Importacao e geracao de APs
- Configuracao, teste e sincronizacao com Zabbix externo
- Persistencia dos APs cadastrados

### Analysis Service (porta 5002)
- Analise de colisao entre pontos de acesso
- Estrategias de otimizacao
- Respostas em streaming para a interface

## Instalar e Rodar

```bash
docker compose build
docker compose up -d --remove-orphans
```

Acesse:

```text
http://localhost:3000
```

## Scripts

```bash
./scripts/management/start.sh
./scripts/management/stop.sh
./scripts/monitor.sh
```

## Documentacao

- Arquitetura: `docs/architecture/README.md`
- API: `docs/api/README.md`
- Instalacao: `docs/guides/installation.md`
