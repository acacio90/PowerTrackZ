# Guia de Instalacao

## Pre-requisitos

- Docker
- Docker Compose
- Git

## Instalar

```bash
git clone https://github.com/acacio90/PowerTrackZ.git
cd PowerTrackZ
cp .env.example .env
docker compose build
docker compose up -d --remove-orphans
```

Acesse `http://localhost:3000`.

## Zabbix

A conexao com o Zabbix externo e configurada pela interface web, na tela de configuracoes. As credenciais ficam armazenadas no banco SQLite do `access_point_service`.

## Logs

```bash
docker compose logs -f
```

Logs de um servico especifico:

```bash
docker compose logs -f frontend_service
docker compose logs -f access_point_service
docker compose logs -f analysis_service
```

## Atualizar

```bash
docker compose down
git pull
docker compose up -d --build --remove-orphans
```
