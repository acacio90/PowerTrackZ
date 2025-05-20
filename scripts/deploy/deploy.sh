#!/bin/bash

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Função para log
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# Função para erro
error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERRO: $1${NC}"
    exit 1
}

# Função para aviso
warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] AVISO: $1${NC}"
}

# Verifica se o Docker está instalado
if ! command -v docker &> /dev/null; then
    error "Docker não está instalado. Por favor, instale o Docker primeiro."
fi

# Verifica se o Docker Compose está instalado
if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose não está instalado. Por favor, instale o Docker Compose primeiro."
fi

# Diretório do projeto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Backup do banco de dados
backup_db() {
    log "Iniciando backup do banco de dados..."
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_DIR="$PROJECT_DIR/backups"
    mkdir -p "$BACKUP_DIR"
    
    docker-compose exec -T db pg_dump -U postgres powertrackz > "$BACKUP_DIR/backup_$TIMESTAMP.sql"
    
    if [ $? -eq 0 ]; then
        log "Backup concluído: backup_$TIMESTAMP.sql"
    else
        error "Falha ao realizar backup do banco de dados"
    fi
}

# Atualiza o código
update_code() {
    log "Atualizando código do repositório..."
    git pull origin main || error "Falha ao atualizar código"
}

# Reconstrui as imagens
rebuild_images() {
    log "Reconstruindo imagens Docker..."
    docker-compose build --no-cache || error "Falha ao reconstruir imagens"
}

# Atualiza os containers
update_containers() {
    log "Atualizando containers..."
    docker-compose down || error "Falha ao parar containers"
    docker-compose up -d || error "Falha ao iniciar containers"
}

# Executa migrações
run_migrations() {
    log "Executando migrações do banco de dados..."
    docker-compose exec -T gateway flask db upgrade || error "Falha ao executar migrações"
}

# Verifica saúde dos serviços
check_health() {
    log "Verificando saúde dos serviços..."
    
    # Verifica Gateway
    if curl -s http://localhost:5000/health | grep -q "ok"; then
        log "Gateway está saudável"
    else
        error "Gateway não está respondendo corretamente"
    fi
    
    # Verifica API
    if curl -s http://localhost:5001/health | grep -q "ok"; then
        log "API está saudável"
    else
        error "API não está respondendo corretamente"
    fi
}

# Limpa recursos não utilizados
cleanup() {
    log "Limpando recursos Docker não utilizados..."
    docker system prune -f || warn "Falha ao limpar recursos Docker"
}

# Função principal
main() {
    log "Iniciando processo de deploy..."
    
    # Backup
    backup_db
    
    # Atualização
    update_code
    rebuild_images
    update_containers
    
    # Migrações
    run_migrations
    
    # Verificações
    check_health
    
    # Limpeza
    cleanup
    
    log "Deploy concluído com sucesso!"
}

# Executa o script
main 