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
}

# Função para aviso
warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] AVISO: $1${NC}"
}

# Diretório do projeto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$PROJECT_DIR/logs/monitor.log"

# Cria diretório de logs se não existir
mkdir -p "$(dirname "$LOG_FILE")"

# Função para verificar serviço
check_service() {
    local service=$1
    local url=$2
    local response
    
    response=$(curl -s -w "\n%{http_code}" "$url")
    local status_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')
    
    if [ "$status_code" -eq 200 ]; then
        log "Serviço $service está respondendo normalmente"
        echo "$(date +'%Y-%m-%d %H:%M:%S') - $service: OK" >> "$LOG_FILE"
    else
        error "Serviço $service retornou status $status_code"
        echo "$(date +'%Y-%m-%d %H:%M:%S') - $service: ERRO ($status_code)" >> "$LOG_FILE"
    fi
}

# Função para verificar uso de recursos
check_resources() {
    # CPU
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2 + $4}')
    if (( $(echo "$cpu_usage > 80" | bc -l) )); then
        warn "Uso de CPU alto: $cpu_usage%"
        echo "$(date +'%Y-%m-%d %H:%M:%S') - CPU: $cpu_usage%" >> "$LOG_FILE"
    fi
    
    # Memória
    local mem_usage=$(free | awk '/Mem:/ {print $3/$2 * 100.0}' | cut -d. -f1)
    if [ "$mem_usage" -gt 80 ]; then
        warn "Uso de memória alto: $mem_usage%"
        echo "$(date +'%Y-%m-%d %H:%M:%S') - Memória: $mem_usage%" >> "$LOG_FILE"
    fi
    
    # Disco
    local disk_usage=$(df -h "$PROJECT_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 80 ]; then
        warn "Uso de disco alto: $disk_usage%"
        echo "$(date +'%Y-%m-%d %H:%M:%S') - Disco: $disk_usage%" >> "$LOG_FILE"
    fi
}

# Função para verificar logs de erro
check_error_logs() {
    local error_count=$(docker-compose logs --tail=1000 | grep -i "error\|exception\|fail" | wc -l)
    if [ "$error_count" -gt 0 ]; then
        warn "Encontrados $error_count erros nos logs"
        echo "$(date +'%Y-%m-%d %H:%M:%S') - Erros nos logs: $error_count" >> "$LOG_FILE"
    fi
}

# Função para verificar conectividade do banco de dados
check_database() {
    if docker-compose exec -T db pg_isready -U postgres > /dev/null 2>&1; then
        log "Banco de dados está respondendo"
        echo "$(date +'%Y-%m-%d %H:%M:%S') - Banco de dados: OK" >> "$LOG_FILE"
    else
        warn "Banco de dados não está respondendo"
        echo "$(date +'%Y-%m-%d %H:%M:%S') - Banco de dados: ERRO" >> "$LOG_FILE"
    fi
}

# Função para verificar certificados SSL
check_ssl() {
    local domains=("api.powertrackz.com" "gateway.powertrackz.com")
    
    for domain in "${domains[@]}"; do
        local expiry_date=$(openssl s_client -connect "$domain:443" -servername "$domain" </dev/null 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2)
        local days_left=$(( ($(date -d "$expiry_date" +%s) - $(date +%s)) / 86400 ))
        
        if [ "$days_left" -lt 30 ]; then
            warn "Certificado SSL para $domain expira em $days_left dias"
            echo "$(date +'%Y-%m-%d %H:%M:%S') - SSL $domain: $days_left dias" >> "$LOG_FILE"
        fi
    done
}

# Função principal
main() {
    log "Iniciando monitoramento..."
    
    # Verifica serviços
    check_service "Gateway" "http://localhost:80/health"
    check_service "Zabbix Service" "http://localhost:5003/health"
    check_service "Map Service" "http://localhost:5001/health"
    check_service "Analysis Service" "http://localhost:5002/health"
    check_service "Access Point Service" "http://localhost:5004/health"
    
    # Verifica recursos
    check_resources
    
    # Verifica logs
    check_error_logs
    
    # Verifica banco de dados
    check_database
    
    # Verifica SSL
    check_ssl
    
    log "Monitoramento concluído"
}

# Executa o script
main 