# Documentação da API

## Endpoints

### Gateway (Porta 80)

#### Autenticação
```
POST /api/auth/login
POST /api/auth/refresh
POST /api/auth/logout
```

#### Pontos de Acesso
```
GET /api/access-points
POST /api/access-points
GET /api/access-points/{id}
PUT /api/access-points/{id}
DELETE /api/access-points/{id}
```

#### Mapas
```
GET /api/maps
POST /api/maps
GET /api/maps/{id}
PUT /api/maps/{id}
DELETE /api/maps/{id}
```

#### Análise
```
GET /api/analysis/performance
GET /api/analysis/reports
POST /api/analysis/generate-report
```

### Zabbix Service (Porta 5003)

```
GET /api/zabbix/items
GET /api/zabbix/triggers
POST /api/zabbix/events
```

### Map Service (Porta 5001)

```
GET /api/map/points
POST /api/map/points
GET /api/map/heatmap
```

### Analysis Service (Porta 5002)

```
GET /api/analysis/metrics
POST /api/analysis/calculate
GET /api/analysis/history
```

### Access Point Service (Porta 5004)

```
GET /api/access-points/status
POST /api/access-points/configure
GET /api/access-points/history
```

## Formatos de Resposta

### Sucesso
```json
{
    "status": "success",
    "data": {
        // Dados da resposta
    }
}
```

### Erro
```json
{
    "status": "error",
    "error": {
        "code": "ERROR_CODE",
        "message": "Descrição do erro"
    }
}
```

## Autenticação

Todas as requisições devem incluir um token JWT no header:
```
Authorization: Bearer <token>
```

## Rate Limiting

- 100 requisições por minuto por IP
- 1000 requisições por hora por usuário

## Códigos de Status

- 200: Sucesso
- 201: Criado
- 400: Requisição inválida
- 401: Não autorizado
- 403: Proibido
- 404: Não encontrado
- 429: Muitas requisições
- 500: Erro interno do servidor 