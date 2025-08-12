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

# Banner do projeto
show_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                        PowerTrackZ                           ║"
    echo "║              Sistema de Monitoramento de APs                 ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Para os serviços
stop_services() {
    log "Parando serviços do PowerTrackZ..."
    docker compose down --remove-orphans
    
    if [ $? -eq 0 ]; then
        log "Serviços parados com sucesso ✓"
    else
        error "Falha ao parar serviços"
    fi
}

# Remove containers e volumes (opcional)
cleanup_containers() {
    if [ "$1" = "--clean" ]; then
        warn "Removendo containers e volumes..."
        docker compose down -v --remove-orphans
        log "Containers e volumes removidos ✓"
    fi
}

# Remove imagens (opcional)
cleanup_images() {
    if [ "$1" = "--clean-all" ]; then
        warn "Removendo imagens do PowerTrackZ..."
        docker rmi $(docker images | grep powertrackz | awk '{print $3}') 2>/dev/null || true
        log "Imagens removidas ✓"
    fi
}

# Mostra status dos containers
show_status() {
    echo -e "\n${BLUE}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}Status dos containers:${NC}"
    docker compose ps
    echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}\n"
}

# Função principal
main() {
    show_banner
    
    # Verifica argumentos
    CLEAN_CONTAINERS=false
    CLEAN_IMAGES=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --clean)
                CLEAN_CONTAINERS=true
                shift
                ;;
            --clean-all)
                CLEAN_CONTAINERS=true
                CLEAN_IMAGES=true
                shift
                ;;
            -h|--help)
                echo "Uso: $0 [OPÇÕES]"
                echo ""
                echo "Opções:"
                echo "  --clean      Remove containers e volumes"
                echo "  --clean-all  Remove containers, volumes e imagens"
                echo "  -h, --help   Mostra esta ajuda"
                echo ""
                echo "Exemplos:"
                echo "  $0              # Para serviços normalmente"
                echo "  $0 --clean      # Para e remove containers/volumes"
                echo "  $0 --clean-all  # Para e remove tudo (containers, volumes, imagens)"
                exit 0
                ;;
            *)
                error "Opção desconhecida: $1"
                ;;
        esac
    done
    
    # Executa os passos
    stop_services
    cleanup_containers $CLEAN_CONTAINERS
    cleanup_images $CLEAN_IMAGES
    show_status
    
    log "PowerTrackZ parado com sucesso! 🛑"
}

# Executa o script
main "$@" 