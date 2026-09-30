# PowerTrackZ Architecture

**English** | [Português](README.pt-BR.md)

## Overview

PowerTrackZ is a lean distributed system for monitoring and analyzing access points. The web interface is the main entry point of the application; it renders the map in the frontend itself and talks directly to the internal services, which are configured through environment variables.

## Main Components

### Frontend Service
- Main web interface
- Page rendering
- Interactive map with Leaflet
- `/api/*` routes used by the interface JavaScript
- Direct forwarding to the Analysis and Access Point services

### Access Point Service
- Access point management
- Data import, generation and synchronization
- Configuration, testing and querying of the external Zabbix
- Persistence of registered APs
- Source of the data shown on the map
- Execution and history of the scalability test, which calls the Analysis Service

### Analysis Service
- Collision analysis and optimization
- Execution of the analysis algorithms
- Progress streaming to the interface
- Queries the Access Point Service when it needs to load the registered access points

## Data Flow

1. The user opens the Frontend Service at `http://localhost:3000`.
2. The frontend renders the pages, including the interactive map.
3. The frontend's internal routes call the responsible microservice directly.
4. The Access Point Service handles CRUD, import, generation and the Zabbix integration.
5. The Analysis Service queries the Access Point Service when it needs to load the registered access points.
6. In the scalability test, the Access Point Service generates the instances and calls the Analysis Service to analyze them, storing the results in its own database.

## Architecture Diagram

```text
[Client]
   |
   v
[Frontend Service]
   |                 |
   v                 v
[Access Point]  [Analysis]
      |
      v
[Database]
      |
      v
[External Zabbix]
```

## Notes

- The services remain isolated in containers.
- The frontend holds the interface responsibilities, including the map.
- The Access Point Service owns everything that creates, imports or synchronizes APs.
- The internal URLs are configured through `.env` and `docker-compose.yml`.
