# Scripts de Gerenciamento - PowerTrackZ

Este documento descreve os scripts disponíveis para gerenciar o projeto PowerTrackZ.

## Scripts Disponíveis

### 1. `start.sh` - Iniciar o Projeto

Script principal para construir e iniciar todos os serviços do PowerTrackZ.

**Uso:**
```bash
./start.sh [OPÇÕES]
```

**Opções:**
- `--restart` - Reinicia serviços sem rebuild
- `--clean` - Limpa imagens antigas antes do build
- `-h, --help` - Mostra esta ajuda

**Exemplos:**
```bash
./start.sh              # Build e start normal
./start.sh --restart    # Reinicia serviços (sem rebuild)
./start.sh --clean      # Build limpo (remove imagens antigas)
./start.sh --clean --restart  # Reinicia com build limpo
```

**O que faz:**
1. Verifica se Docker e Docker Compose estão instalados
2. Para containers existentes (se --restart for usado)
3. Limpa imagens antigas (se --clean for usado)
4. Constrói as imagens Docker (pula se --restart for usado)
5. Inicia todos os serviços
6. Verifica a saúde dos serviços
7. Mostra informações de acesso

### 2. `stop.sh` - Parar o Projeto

Script para parar todos os serviços do PowerTrackZ.

**Uso:**
```bash
./stop.sh [OPÇÕES]
```

**Opções:**
- `--clean` - Remove containers e volumes
- `--clean-all` - Remove containers, volumes e imagens
- `-h, --help` - Mostra esta ajuda

**Exemplos:**
```bash
./stop.sh              # Para serviços normalmente
./stop.sh --clean      # Para e remove containers/volumes
./stop.sh --clean-all  # Para e remove tudo (containers, volumes, imagens)
```

## Fluxo de Trabalho Típico

### Primeira Execução
```bash
# 1. Clone o repositório
git clone https://github.com/acacio90/PowerTrackZ.git
cd PowerTrackZ

# 2. Torne os scripts executáveis
chmod +x scripts/management/*.sh

# 3. Inicie o projeto
./scripts/management/start.sh
```

### Desenvolvimento Diário
```bash
# Para parar os serviços
./scripts/management/stop.sh

# Para reiniciar os serviços (sem rebuild)
./scripts/management/start.sh --restart

# Para reiniciar com rebuild
./scripts/management/start.sh --clean

# Para ver logs
docker compose logs -f

# Para ver status
docker compose ps
```

### Limpeza Completa
```bash
# Para parar e remover tudo
./scripts/management/stop.sh --clean-all

# Para iniciar com build limpo
./scripts/management/start.sh --clean
```

## Serviços Disponíveis

Após executar `./start.sh`, os seguintes serviços estarão disponíveis:

| Serviço | Porta | Descrição |
|---------|-------|-----------|
| Gateway | 80 | API Gateway e proxy reverso |
| Frontend Service | 3000 | Interface web principal |
| Zabbix Service | 5003 | Integração com Zabbix |
| Map Service | 5001 | Visualização de mapas |
| Analysis Service | 5002 | Análise de dados e algoritmos |
| Access Point Service | 5004 | Gerenciamento de APs |

## Comandos Docker Úteis

```bash
# Ver logs de todos os serviços
docker compose logs -f

# Ver logs de um serviço específico
docker compose logs -f gateway
docker compose logs -f frontend_service
docker compose logs -f analysis_service

# Ver status dos containers
docker compose ps

# Executar comando em um container
docker compose exec gateway bash
docker compose exec frontend_service bash

# Ver uso de recursos
docker stats

# Verificar conectividade dos serviços
./scripts/monitor.sh
```

## Troubleshooting

### Problemas Comuns

1. **Porta já em uso:**
   ```bash
   # Verificar o que está usando a porta
   sudo lsof -i :80
   sudo lsof -i :3000
   
   # Parar o processo
   sudo kill -9 <PID>
   ```

2. **Erro de permissão:**
   ```bash
   # Tornar scripts executáveis
   chmod +x scripts/management/*.sh
   ```

3. **Docker não encontrado:**
   ```bash
   # Instalar Docker
   sudo apt-get update
   sudo apt-get install docker.io docker-compose
   sudo systemctl start docker
   sudo systemctl enable docker
   sudo usermod -aG docker $USER
   ```

4. **Erro de build das imagens:**
   ```bash
   # Limpar cache do Docker
   docker builder prune -f
   
   # Rebuild limpo
   ./scripts/management/start.sh --clean
   ```

5. **Limpeza completa:**
   ```bash
   # Parar e remover tudo
   ./scripts/management/stop.sh --clean-all
   
   # Remover imagens não utilizadas
   docker system prune -a
   ```

6. **Problemas de conectividade:**
   ```bash
   # Verificar status dos serviços
   ./scripts/monitor.sh
   
   # Verificar logs de erro
   docker compose logs --tail=50 | grep ERROR
   ```

## Requisitos

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **curl** (para verificações de saúde)
- **bash** (shell padrão)
- **git** (para clonagem do repositório)

## Estrutura dos Scripts

Todos os scripts seguem o mesmo padrão:
- **Cores para output colorido** (verde, vermelho, amarelo, azul)
- **Funções de log** (success, error, warn, info)
- **Verificação de dependências** (Docker, Docker Compose)
- **Tratamento de argumentos** (--help, --restart, --clean)
- **Banner do projeto** com informações
- **Verificação de saúde** dos serviços
- **Tratamento de erros** robusto

## Integração com Outros Scripts

Os scripts de gerenciamento trabalham em conjunto com:

- **`scripts/monitor.sh`** - Monitoramento em tempo real
- **`scripts/maintenance/maintenance.sh`** - Manutenção e deploy
- **`scripts/maintenance/maintenance.sh --update`** - Deploy completo

## Exemplos de Uso Avançado

### Desenvolvimento
```bash
# Iniciar ambiente de desenvolvimento
./scripts/management/start.sh

# Monitorar em tempo real
./scripts/monitor.sh

# Reiniciar após mudanças
./scripts/management/start.sh --restart
```

### Produção
```bash
# Deploy completo
./scripts/maintenance/maintenance.sh --update

# Monitoramento contínuo
./scripts/monitor.sh

# Manutenção periódica
./scripts/maintenance/maintenance.sh
```

### Debug
```bash
# Ver logs detalhados
docker compose logs -f --tail=100

# Verificar conectividade
curl -f http://localhost/api/health

# Verificar recursos
docker stats --no-stream
``` 