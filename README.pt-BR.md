# PowerTrackZ

[English](README.md) | **Português**

O PowerTrackZ é um sistema de monitoramento e análise de pontos de acesso Wi-Fi, com foco na detecção de interferência e na otimização de configurações.

## Funcionalidades

- Cadastro, importação e geração de pontos de acesso
- Integração com um Zabbix externo para carregar os APs monitorados
- Mapa interativo no frontend com Leaflet
- Análise de colisão e otimização por algoritmos em C
- Teste de escalabilidade das estratégias, com gráficos e histórico por versão
- Execução via Docker Compose

## Arquitetura

```text
PowerTrackZ/
├── services/
│   ├── frontend_service/       # Interface web e mapa
│   ├── access_point_service/   # CRUD, importação, geração e Zabbix
│   └── analysis_service/       # Algoritmos de análise
├── scripts/                    # Automação e manutenção
├── docs/                       # Documentação
└── docker-compose.yml
```

## Serviços

### Frontend Service (porta 3000)
- Entrada principal em `http://localhost:3000`
- Páginas web, assets e mapa interativo
- Rotas `/api/*` usadas pela interface

### Access Point Service (porta 5004)
- CRUD de pontos de acesso
- Importação e geração de APs
- Configuração, teste e sincronização com o Zabbix externo
- Persistência dos APs cadastrados

### Analysis Service (porta 5002)
- Análise de colisão entre pontos de acesso
- Estratégias de otimização
- Respostas em streaming para a interface

## Instalar e Rodar

Copie o arquivo de variáveis de ambiente antes da primeira execução; sem ele, os serviços não recebem os endereços uns dos outros.

```bash
cp .env.example .env
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

## Documentação

- Arquitetura: [docs/architecture/README.pt-BR.md](docs/architecture/README.pt-BR.md)
- API: [docs/api/README.pt-BR.md](docs/api/README.pt-BR.md)
- Instalação: [docs/guides/installation.pt-BR.md](docs/guides/installation.pt-BR.md)
- Uso: [docs/guides/usage.pt-BR.md](docs/guides/usage.pt-BR.md)
- Design tokens: [docs/design/README.pt-BR.md](docs/design/README.pt-BR.md)
- Energia do processamento das estratégias: [docs/energy/README.pt-BR.md](docs/energy/README.pt-BR.md)
- Contribuição: [CONTRIBUTING.pt-BR.md](CONTRIBUTING.pt-BR.md)
