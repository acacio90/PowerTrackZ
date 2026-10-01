# PowerTrackZ

**English** | [Português](README.pt-BR.md)

PowerTrackZ is a system for monitoring and analyzing Wi-Fi access points, focused on detecting interference and optimizing their configurations.

## Features

- Registration, import and generation of access points
- Integration with an external Zabbix to load monitored APs
- Interactive map in the frontend with Leaflet
- Collision analysis and optimization by algorithms written in C
- Scalability test of the strategies, with charts and a per-version history
- Runs with Docker Compose

## Architecture

```text
PowerTrackZ/
├── services/
│   ├── frontend_service/       # Web interface and map
│   ├── access_point_service/   # CRUD, import, generation and Zabbix
│   └── analysis_service/       # Analysis algorithms
├── scripts/                    # Automation and maintenance
├── docs/                       # Documentation
└── docker-compose.yml
```

## Services

### Frontend Service (port 3000)
- Main entry point at `http://localhost:3000`
- Web pages, assets and interactive map
- `/api/*` routes used by the interface

### Access Point Service (port 5004)
- Access point CRUD
- AP import and generation
- Configuration, testing and synchronization with the external Zabbix
- Persistence of registered APs

### Analysis Service (port 5002)
- Collision analysis between access points
- Optimization strategies
- Streaming responses to the interface

## Install and Run

Copy the environment variables file before the first run; without it, the services do not receive each other's addresses.

```bash
cp .env.example .env
docker compose build
docker compose up -d --remove-orphans
```

Open:

```text
http://localhost:3000
```

## Scripts

```bash
./scripts/management/start.sh
./scripts/management/stop.sh
./scripts/monitor.sh
```

## Documentation

- Architecture: [docs/architecture/README.md](docs/architecture/README.md)
- API: [docs/api/README.md](docs/api/README.md)
- Installation: [docs/guides/installation.md](docs/guides/installation.md)
- Usage: [docs/guides/usage.md](docs/guides/usage.md)
- Design tokens: [docs/design/README.md](docs/design/README.md)
- Processing energy of the strategies: [docs/energy/README.md](docs/energy/README.md)
- Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)
