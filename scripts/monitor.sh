#!/bin/bash

# Função para verificar certificados SSL
check_ssl() {
    local domains=("powertrackz.com" "api.powertrackz.com")
    
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
    check_service "Frontend" "http://localhost:3000/health"
    check_service "Analysis Service" "http://localhost:5002/health"
    check_service "Access Point Service" "http://localhost:5004/health"
    
    # Verifica recursos
    check_resources
    
    # Verifica logs
    check_error_logs
    # Verifica SSL
    check_ssl
    
    log "Monitoramento concluído"
}

# Executa o script
main 