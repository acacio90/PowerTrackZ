document.addEventListener('DOMContentLoaded', function() {
    console.log("Página de registro carregada. Inicializando...");
    
    // Elementos globais
    const modal = document.getElementById('modal-add-point');
    const btnAddPoint = document.getElementById('btn-add-point');
    const closeModal = document.getElementById('close-modal');
    const latitudeInput = document.getElementById('modal-latitude');
    const longitudeInput = document.getElementById('modal-longitude');
    const formModal = document.getElementById('form-add-point');
    
    // Verificar se os elementos existem
    if (!modal) console.error("Modal não encontrada!");
    if (!btnAddPoint) console.error("Botão de adicionar ponto não encontrado!");
    if (!latitudeInput) console.error("Input de latitude não encontrado!");
    if (!longitudeInput) console.error("Input de longitude não encontrado!");
    
    // Função para abrir a modal
    function openModal() {
        console.log("Abrindo modal...");
        if (modal) {
            modal.style.display = 'flex';
            
            // Verificar se há coordenadas selecionadas no mapa
            if (window.lastSelectedCoordinates) {
                updateCoordinates(
                    window.lastSelectedCoordinates.lat, 
                    window.lastSelectedCoordinates.lng
                );
            }
        }
    }
    
    // Função para fechar a modal
    function closeModalHandler() {
        console.log("Fechando modal...");
        if (modal) {
            modal.style.display = 'none';
        }
    }
    
    // Adicionar eventos aos botões
    if (btnAddPoint) {
        btnAddPoint.addEventListener('click', openModal);
    }
    
    if (closeModal) {
        closeModal.addEventListener('click', closeModalHandler);
    }
    
    // Fechar a modal ao clicar fora dela
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            closeModalHandler();
        }
    });
    
    // Fechar a modal ao pressionar ESC
    window.addEventListener('keydown', function(event) {
        if (event.key === 'Escape' && modal && (modal.style.display === 'flex' || modal.style.display === 'block')) {
            closeModalHandler();
        }
    });
    
    // Validação do formulário
    if (formModal) {
        const inputs = formModal.querySelectorAll('input[required]');
        
        // Função para validar coordenadas
        function isValidCoordinate(value, type) {
            const num = parseFloat(value);
            if (isNaN(num)) return false;
            
            if (type === 'latitude') {
                return num >= -90 && num <= 90;
            } else if (type === 'longitude') {
                return num >= -180 && num <= 180;
            }
            return false;
        }
        
        // Função para validar frequência
        function isValidFrequency(value) {
            const num = parseFloat(value);
            return !isNaN(num) && num > 0 && num <= 6; // Frequência em GHz
        }
        
        // Função para validar largura de banda
        function isValidBandwidth(value) {
            const num = parseFloat(value);
            return !isNaN(num) && num > 0 && num <= 160; // Largura de banda em MHz
        }
        
        // Função para validar canal
        function isValidChannel(value) {
            const num = parseInt(value);
            return !isNaN(num) && num > 0 && num <= 165; // Canais WiFi
        }
        
        // Adiciona validação em tempo real
        inputs.forEach(input => {
            if (input.readOnly) return; // Pular campos readonly (lat/long)
            
            input.addEventListener('input', function() {
                let isValid = true;
                let errorMessage = '';
                
                switch(input.id) {
                    case 'modal-latitude':
                        if (!isValidCoordinate(input.value, 'latitude')) {
                            isValid = false;
                            errorMessage = 'Latitude deve estar entre -90 e 90';
                        }
                        break;
                    case 'modal-longitude':
                        if (!isValidCoordinate(input.value, 'longitude')) {
                            isValid = false;
                            errorMessage = 'Longitude deve estar entre -180 e 180';
                        }
                        break;
                    case 'modal-frequency':
                        if (!isValidFrequency(input.value)) {
                            isValid = false;
                            errorMessage = 'Frequência inválida (deve ser entre 0 e 6 GHz)';
                        }
                        break;
                    case 'modal-bandwidth':
                        if (!isValidBandwidth(input.value)) {
                            isValid = false;
                            errorMessage = 'Largura de banda inválida (deve ser entre 0 e 160 MHz)';
                        }
                        break;
                    case 'modal-channel':
                        if (!isValidChannel(input.value)) {
                            isValid = false;
                            errorMessage = 'Canal inválido (deve ser entre 1 e 165)';
                        }
                        break;
                }
                
                // Atualiza o feedback visual
                if (!isValid) {
                    input.classList.add('is-invalid');
                    let feedback = input.nextElementSibling;
                    if (!feedback || !feedback.classList.contains('invalid-feedback')) {
                        feedback = document.createElement('div');
                        feedback.className = 'invalid-feedback';
                        input.parentNode.insertBefore(feedback, input.nextSibling);
                    }
                    feedback.textContent = errorMessage;
                } else {
                    input.classList.remove('is-invalid');
                    input.classList.add('is-valid');
                    let feedback = input.nextElementSibling;
                    if (feedback && feedback.classList.contains('invalid-feedback')) {
                        feedback.remove();
                    }
                }
            });
        });
        
        // Validação no envio do formulário
        formModal.addEventListener('submit', function(event) {
            console.log("Formulário submetido, validando...");
            let isValid = true;
            
            inputs.forEach(input => {
                // Pular campos readonly (lat/long) na validação de preenchimento
                if (input.readOnly) {
                    if (!input.value.trim()) {
                        isValid = false;
                        console.error(`Campo ${input.id} está vazio`);
                    }
                    return;
                }
                
                if (!input.value.trim()) {
                    isValid = false;
                    input.classList.add('is-invalid');
                    console.error(`Campo ${input.id} está vazio`);
                }
            });
            
            if (!isValid) {
                event.preventDefault();
                alert('Por favor, preencha todos os campos obrigatórios.');
            } else {
                console.log("Formulário válido, enviando...");
            }
        });
    }
});

// Função global para atualizar as coordenadas no formulário
function updateCoordinates(lat, lng) {
    console.log(`Atualizando coordenadas: ${lat.toFixed(6)}, ${lng.toFixed(6)}`);
    
    const latitudeInput = document.getElementById('modal-latitude');
    const longitudeInput = document.getElementById('modal-longitude');
    
    if (latitudeInput && longitudeInput) {
        latitudeInput.value = lat.toFixed(6);
        longitudeInput.value = lng.toFixed(6);
        console.log("Coordenadas atualizadas com sucesso!");
    } else {
        console.error("Campos de latitude/longitude não encontrados!");
    }
}

// Evento personalizado para quando o mapa for carregado
document.addEventListener('mapReady', function(e) {
    console.log("Evento 'mapReady' recebido. Mapa pronto para seleção de coordenadas.");
});

// Expor função para ser usada pelo mapa.js
window.updateCoordinates = updateCoordinates; 