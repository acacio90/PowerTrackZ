# Scripts de Gerenciamento - PowerTrackZ

[English](SCRIPTS.md) | **Português**

Este documento descreve os scripts disponíveis para gerenciar o projeto PowerTrackZ.

## Scripts Disponíveis

### 1. `start.sh` - Iniciar o Projeto

Script principal para construir e iniciar todos os serviços do PowerTrackZ.

**Uso:**
```bash
./start.sh [OPÇÕES]
```

**Opções:**
- `--restart` - Reinicia os serviços sem rebuild
- `--clean` - Limpa as imagens antigas antes do build
- `-h, --help` - Mostra a ajuda

**Exemplos:**
```bash
./start.sh              # Build e start normal
./start.sh --restart    # Reinicia os serviços (sem rebuild)
./start.sh --clean      # Build limpo (remove as imagens antigas)
./start.sh --clean --restart  # Reinicia com build limpo
```

**O que faz:**
1. Verifica se o Docker e o Docker Compose estão instalados
2. Para os contêineres existentes (se --restart for usado)
3. Limpa as imagens antigas (se --clean for usado)
4. Constrói as imagens Docker (pula se --restart for usado)
5. Inicia todos os serviços
6. Verifica a saúde dos serviços
7. Mostra as informações de acesso

### 2. `stop.sh` - Parar o Projeto

Script para parar todos os serviços do PowerTrackZ.

**Uso:**
```bash
./stop.sh [OPÇÕES]
```

**Opções:**
- `--clean` - Remove os contêineres e volumes
- `--clean-all` - Remove os contêineres, volumes e imagens
- `-h, --help` - Mostra a ajuda

**Exemplos:**
```bash
./stop.sh              # Para os serviços normalmente
./stop.sh --clean      # Para e remove contêineres/volumes
./stop.sh --clean-all  # Para e remove tudo (contêineres, volumes, imagens)
```

### 3. `start-local.ps1` - Executar sem Docker Compose (Windows)

Inicia os serviços Python em um ambiente virtual local e o `analysis_service` em um contêiner Docker avulso, cada um em sua própria janela do PowerShell.

**Uso:**
```powershell
.\scripts\management\start-local.ps1 [-SkipInstall] [-VenvPath <caminho>]
```

**Opções:**
- `-SkipInstall`: não reinstala as dependências do ambiente virtual
- `-VenvPath`: caminho do ambiente virtual (padrão: `.venv-local`)

Sem o Docker no `PATH`, o `analysis_service` não é iniciado. Para encerrar, use `Ctrl+C` em cada janela.

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

# Para ver os logs
docker compose logs -f

# Para ver o status
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
| Frontend Service | 3000 | Interface web principal |
| Analysis Service | 5002 | Análise de dados e algoritmos |
| Access Point Service | 5004 | Gerenciamento de APs |

## Comandos Docker Úteis

```bash
# Ver os logs de todos os serviços
docker compose logs -f

# Ver os logs de um serviço específico
docker compose logs -f frontend_service
docker compose logs -f analysis_service

# Ver o status dos contêineres
docker compose ps

# Executar um comando em um contêiner
docker compose exec frontend_service bash

# Ver o uso de recursos
docker stats

# Verificar a conectividade dos serviços
./scripts/monitor.sh
```

## Troubleshooting

### Problemas Comuns

1. **Porta já em uso:**
   ```bash
   # Verificar o que está usando a porta
   sudo lsof -i :3000

   # Parar o processo
   sudo kill -9 <PID>
   ```

2. **Erro de permissão:**
   ```bash
   # Tornar os scripts executáveis
   chmod +x scripts/management/*.sh
   ```

3. **Docker não encontrado:**
   ```bash
   # Instalar o Docker
   sudo apt-get update
   sudo apt-get install docker.io docker-compose
   sudo systemctl start docker
   sudo systemctl enable docker
   sudo usermod -aG docker $USER
   ```

4. **Erro de build das imagens:**
   ```bash
   # Limpar o cache do Docker
   docker builder prune -f

   # Rebuild limpo
   ./scripts/management/start.sh --clean
   ```

5. **Limpeza completa:**
   ```bash
   # Parar e remover tudo
   ./scripts/management/stop.sh --clean-all

   # Remover as imagens não utilizadas
   docker system prune -a
   ```

6. **Problemas de conectividade:**
   ```bash
   # Verificar o status dos serviços
   ./scripts/monitor.sh

   # Verificar os logs de erro
   docker compose logs --tail=50 | grep ERROR
   ```

## Requisitos

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **curl** (para as verificações de saúde)
- **bash** (shell padrão)
- **git** (para clonar o repositório)

## Estrutura dos Scripts

Todos os scripts seguem o mesmo padrão:
- **Cores na saída** (verde, vermelho, amarelo, azul)
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
# Iniciar o ambiente de desenvolvimento
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

# Verificar a conectividade
curl -f http://localhost:3000/health
curl -f http://localhost:5002/health
curl -f http://localhost:5004/health

# Verificar os recursos
docker stats --no-stream
```
