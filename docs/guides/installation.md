# Guia de Instalação

## Pré-requisitos

- Docker
- Docker Compose
- Python 3.9+
- Git

## Instalação

### 1. Clone o Repositório

```bash
git clone https://github.com/acacio90/PowerTrackZ.git
cd PowerTrackZ
```

### 2. Configuração do Ambiente

1. Copie o arquivo de exemplo de variáveis de ambiente:
```bash
cp .env.example .env
```

2. Edite o arquivo `.env` com suas configurações:
```bash
# Edite as variáveis conforme necessário
nano .env
```

### 3. Construção dos Containers

```bash
docker-compose build
```

### 4. Iniciar os Serviços

```bash
docker-compose up -d
```

### 5. Verificar a Instalação

Acesse:
- API Gateway: http://localhost:80
- Swagger UI: http://localhost:80/docs

## Configuração do Zabbix

1. Acesse o painel do Zabbix
2. Configure as credenciais no arquivo `.env`
3. Teste a conexão:
```bash
curl http://localhost:5003/api/zabbix/test-connection
```

## Configuração do Banco de Dados

1. O banco de dados será criado automaticamente
2. As migrações serão executadas na primeira inicialização
3. Verifique os logs para confirmar:
```bash
docker-compose logs db
```

## Troubleshooting

### Problemas Comuns

1. **Portas em uso**
   - Verifique se as portas necessárias estão disponíveis
   - Altere as portas no arquivo `.env` se necessário

2. **Erro de conexão com Zabbix**
   - Verifique as credenciais
   - Confirme se o servidor Zabbix está acessível

3. **Erro de banco de dados**
   - Verifique os logs do container do banco
   - Confirme as credenciais no arquivo `.env`

### Logs

Para verificar os logs de todos os serviços:
```bash
docker-compose logs -f
```

Para logs de um serviço específico:
```bash
docker-compose logs -f [nome-do-serviço]
```

## Atualização

Para atualizar o sistema:

1. Pare os containers:
```bash
docker-compose down
```

2. Atualize o código:
```bash
git pull
```

3. Reconstrua e inicie:
```bash
docker-compose up -d --build
```

## Backup

### Backup do Banco de Dados

```bash
docker-compose exec db pg_dump -U postgres powertrackz > backup.sql
```

### Restauração

```bash
cat backup.sql | docker-compose exec -T db psql -U postgres powertrackz
``` 