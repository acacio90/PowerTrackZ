# Guia de Instalação

[English](installation.md) | **Português**

## Pré-requisitos

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

A conexão com o Zabbix externo é configurada pela interface web, na tela de configurações. As credenciais ficam armazenadas no banco SQLite do `access_point_service`.

## Logs

```bash
docker compose logs -f
```

Logs de um serviço específico:

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

## Próximo Passo

O uso da interface, do carregamento dos APs à leitura dos resultados da análise, está descrito em [usage.pt-BR.md](usage.pt-BR.md).
