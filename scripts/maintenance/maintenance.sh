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

# Diretório do projeto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Backup do banco de dados
backup_database() {
    log "Iniciando backup do banco de dados..."
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_DIR="$PROJECT_DIR/backups"
    mkdir -p "$BACKUP_DIR"
    
    docker-compose exec -T db pg_dump -U postgres powertrackz > "$BACKUP_DIR/backup_$TIMESTAMP.sql"
    
    if [ $? -eq 0 ]; then
        log "Backup concluído: backup_$TIMESTAMP.sql"
        
        # Mantém apenas os últimos 7 backups
        ls -t "$BACKUP_DIR"/backup_*.sql | tail -n +8 | xargs -r rm
    else
        error "Falha ao realizar backup do banco de dados"
    fi
}

# Limpeza de logs
cleanup_logs() {
    log "Limpando logs antigos..."
    LOG_DIR="$PROJECT_DIR/logs"
    
    # Remove logs mais antigos que 30 dias
    find "$LOG_DIR" -type f -name "*.log" -mtime +30 -delete
    
    # Compacta logs mais antigos que 7 dias
    find "$LOG_DIR" -type f -name "*.log" -mtime +7 -exec gzip {} \;
}

# Verificação de espaço em disco
check_disk_space() {
    log "Verificando espaço em disco..."
    DISK_USAGE=$(df -h "$PROJECT_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$DISK_USAGE" -gt 90 ]; then
        warn "Espaço em disco crítico: $DISK_USAGE% utilizado"
    else
        log "Espaço em disco OK: $DISK_USAGE% utilizado"
    fi
}

# Verificação de memória
check_memory() {
    log "Verificando uso de memória..."
    MEM_USAGE=$(free | awk '/Mem:/ {print $3/$2 * 100.0}' | cut -d. -f1)
    
    if [ "$MEM_USAGE" -gt 90 ]; then
        warn "Uso de memória crítico: $MEM_USAGE%"
    else
        log "Uso de memória OK: $MEM_USAGE%"
    fi
}

# Verificação de containers
check_containers() {
    log "Verificando status dos containers..."
    
    # Verifica se todos os containers estão rodando
    if docker-compose ps | grep -q "Exit"; then
        error "Alguns containers estão parados"
    fi
    
    # Verifica uso de recursos dos containers
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
}

# Rotação de logs do Docker
rotate_docker_logs() {
    log "Configurando rotação de logs do Docker..."
    
    # Cria diretório de configuração se não existir
    sudo mkdir -p /etc/docker
    
    # Configura rotação de logs
    cat << EOF | sudo tee /etc/docker/daemon.json
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    }
}
EOF
    
    # Reinicia o Docker para aplicar as configurações
    sudo systemctl restart docker
}

# Verificação de segurança
security_check() {
    log "Realizando verificação de segurança..."
    
    # Verifica atualizações de segurança do sistema
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get upgrade -s | grep -i security
    fi
    
    # Verifica permissões de arquivos sensíveis
    find "$PROJECT_DIR" -type f -name "*.env" -o -name "*.pem" | while read -r file; do
        if [ "$(stat -c %a "$file")" != "600" ]; then
            warn "Permissões incorretas em $file"
            chmod 600 "$file"
        fi
    done
}

# Atualiza o código
update_code() {
    log "Atualizando código do repositório..."
    git pull origin main || warn "Falha ao atualizar código"
}

# Reconstrui as imagens
rebuild_images() {
    log "Reconstruindo imagens Docker..."
    docker-compose build --no-cache || warn "Falha ao reconstruir imagens"
}

# Atualiza os containers
update_containers() {
    log "Atualizando containers..."
    docker-compose down || warn "Falha ao parar containers"
    docker-compose up -d || warn "Falha ao iniciar containers"
}

# Verifica saúde dos serviços
check_health() {
    log "Verificando saúde dos serviços..."
    
    services=(
        "gateway:80"
        "zabbix_service:5003"
        "map_service:5001"
        "analysis_service:5002"
        "access_point_service:5004"
    )
    
    for service in "${services[@]}"; do
        IFS=':' read -r name port <<< "$service"
        
        if curl -s -f "http://localhost:$port/health" >/dev/null 2>&1 || \
           curl -s -f "https://localhost:$port/health" >/dev/null 2>&1; then
            log "$name está saudável ✓"
        else
            warn "$name pode não estar respondendo corretamente"
        fi
    done
}

# Função principal
main() {
    log "Iniciando tarefas de manutenção..."
    
    # Backup
    backup_database
    
    # Limpeza
    cleanup_logs
    
    # Verificações
    check_disk_space
    check_memory
    check_containers
    
    # Configurações
    rotate_docker_logs
    
    # Segurança
    security_check
    
    # Atualização (opcional)
    if [ "$1" = "--update" ]; then
        log "Executando atualização completa..."
        update_code
        rebuild_images
        update_containers
        check_health
    fi
    
    log "Tarefas de manutenção concluídas!"
}

# Executa o script
main 