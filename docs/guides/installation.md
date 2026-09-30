# Installation Guide

**English** | [Português](installation.pt-BR.md)

## Prerequisites

- Docker
- Docker Compose
- Git

## Install

```bash
git clone https://github.com/acacio90/PowerTrackZ.git
cd PowerTrackZ
cp .env.example .env
docker compose build
docker compose up -d --remove-orphans
```

Open `http://localhost:3000`.

## Zabbix

The connection to the external Zabbix is configured through the web interface, on the settings screen. The credentials are stored in the SQLite database of `access_point_service`.

## Logs

```bash
docker compose logs -f
```

Logs of a specific service:

```bash
docker compose logs -f frontend_service
docker compose logs -f access_point_service
docker compose logs -f analysis_service
```

## Update

```bash
docker compose down
git pull
docker compose up -d --build --remove-orphans
```

## Next Step

Using the interface, from loading the APs to reading the analysis results, is described in [usage.md](usage.md).
