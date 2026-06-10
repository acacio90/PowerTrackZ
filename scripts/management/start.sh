#!/bin/bash

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Função para info
info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Banner do projeto
show_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                        PowerTrackZ                           ║"
    echo "║              Sistema de Monitoramento de APs                 ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Verifica se o Docker está instalado
check_docker() {
    log "Verificando dependências..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker não está instalado. Por favor, instale o Docker primeiro."
    fi
    
    if ! command -v docker compose &> /dev/null; then
        error "Docker Compose não está instalado. Por favor, instale o Docker Compose primeiro."
    fi
    
    log "Docker e Docker Compose encontrados ✓"
}

# Para containers existentes
stop_containers() {
    log "Parando containers existentes..."
    docker compose down --remove-orphans 2>/dev/null || true
}

# Limpa imagens antigas (opcional)
cleanup_images() {
    if [ "$1" = "--clean" ]; then
        warn "Limpando imagens antigas..."
        docker system prune -f
    fi
}

# Constrói as imagens
build_images() {
    log "Construindo imagens Docker..."
    docker compose build
    
    if [ $? -eq 0 ]; then
        log "Build concluído com sucesso ✓"
    else
        error "Falha no build das imagens"
    fi
}

# Inicia os serviços
start_services() {
    log "Iniciando serviços..."
    docker compose up -d
    
    if [ $? -eq 0 ]; then
        log "Serviços iniciados com sucesso ✓"
    else
        error "Falha ao iniciar serviços"
    fi
}

# Verifica saúde dos serviços
check_health() {
    log "Verificando saúde dos serviços..."
    
    # Aguarda um pouco para os serviços inicializarem
    sleep 10
    
    # Verifica cada serviço
    services=(
        "frontend_service:3000"
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

# Mostra informações dos serviços
show_services_info() {
    echo -e "\n${BLUE}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}🎉 PowerTrackZ está rodando!${NC}"
    echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}Serviços disponíveis:${NC}"
    echo -e "  🌐 Frontend: ${GREEN}http://localhost:3000${NC}"
    echo -e "  📈 Analysis Service: ${GREEN}http://localhost:5002${NC}"
    echo -e "  📡 Access Point Service: ${GREEN}http://localhost:5004${NC}"
    echo -e "\n${YELLOW}Comandos úteis:${NC}"
    echo -e "  📋 Ver logs: ${GREEN}docker compose logs -f${NC}"
    echo -e "  🛑 Parar serviços: ${GREEN}docker compose down${NC}"
    echo -e "  🔄 Reiniciar: ${GREEN}docker compose restart${NC}"
    echo -e "  📊 Status: ${GREEN}docker compose ps${NC}"
    echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}\n"
}

# Função principal
main() {
    show_banner
    
    # Verifica argumentos
    CLEAN_BUILD=false
    RESTART_MODE=false
    while [[ $# -gt 0 ]]; do
        case $1 in
            --clean)
                CLEAN_BUILD=true
                shift
                ;;
            --restart)
                RESTART_MODE=true
                shift
                ;;
            -h|--help)
                echo "Uso: $0 [OPÇÕES]"
                echo ""
                echo "Opções:"
                echo "  --clean    Limpa imagens antigas antes do build"
                echo "  --restart  Reinicia os serviços (para e inicia)"
                echo "  -h, --help Mostra esta ajuda"
                echo ""
                echo "Exemplos:"
                echo "  $0              # Build e start normal"
                echo "  $0 --clean      # Build limpo (remove imagens antigas)"
                echo "  $0 --restart    # Reinicia os serviços"
                exit 0
                ;;
            *)
                error "Opção desconhecida: $1"
                ;;
        esac
    done
    
    # Executa os passos
    check_docker
    stop_containers
    
    if [ "$RESTART_MODE" = true ]; then
        log "Modo restart ativado - pulando build..."
    else
    cleanup_images $CLEAN_BUILD
    build_images
    fi
    
    start_services
    check_health
    show_services_info
    
    if [ "$RESTART_MODE" = true ]; then
        log "PowerTrackZ reiniciado com sucesso! 🔄"
    else
    log "PowerTrackZ iniciado com sucesso! 🚀"
    fi
}

# Executa o script
main "$@" 