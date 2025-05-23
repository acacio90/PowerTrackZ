// Inicializa quando o DOM carregar
document.addEventListener('DOMContentLoaded', function() {
    // Elementos principais
    const modal = document.getElementById('modal-add-point');
    const btnAddPoint = document.getElementById('btn-add-point');
    const closeModal = document.getElementById('close-modal');
    const latitudeInput = document.getElementById('modal-latitude');
    const longitudeInput = document.getElementById('modal-longitude');
    const formModal = document.getElementById('form-add-point');
    const btnCancel = document.getElementById('cancel-modal');

    // Abre a modal e atualiza coordenadas
    function openModal() {
        if (modal) {
            modal.style.display = 'flex';
            if (window.lastSelectedCoordinates) {
                updateCoordinates(
                    window.lastSelectedCoordinates.lat,
                    window.lastSelectedCoordinates.lng
                );
            }
        }
    }

    // Fecha a modal
    function closeModalHandler() {
        if (modal) modal.style.display = 'none';
    }

    // Eventos dos botões
    if (btnAddPoint) btnAddPoint.addEventListener('click', openModal);
    if (closeModal) closeModal.addEventListener('click', closeModalHandler);
    if (btnCancel) btnCancel.addEventListener('click', closeModalHandler);

    // Fecha modal ao clicar fora ou pressionar ESC
    window.addEventListener('click', e => {
        if (e.target === modal) closeModalHandler();
    });

    window.addEventListener('keydown', e => {
        if (e.key === 'Escape' && modal) closeModalHandler();
    });

    // Validação do formulário
    if (formModal) {
        const inputs = formModal.querySelectorAll('input[required]');

        // Funções de validação
        function isValidCoordinate(value, type) {
            const num = parseFloat(value);
            return type === 'latitude' ? (num >= -90 && num <= 90) : (num >= -180 && num <= 180);
        }

        function isValidFrequency(value) {
            const num = parseFloat(value);
            return !isNaN(num) && num > 0 && num <= 6;
        }

        function isValidBandwidth(value) {
            const num = parseFloat(value);
            return !isNaN(num) && num > 0 && num <= 160;
        }

        function isValidChannel(value) {
            const num = parseInt(value);
            return !isNaN(num) && num > 0 && num <= 165;
        }

        // Validação em tempo real
        inputs.forEach(input => {
            if (input.readOnly) return;

            input.addEventListener('input', function() {
                let isValid = true;
                let errorMessage = '';

                // Valida cada campo
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
                            errorMessage = 'Frequência inválida (0-6 GHz)';
                        }
                        break;
                    case 'modal-bandwidth':
                        if (!isValidBandwidth(input.value)) {
                            isValid = false;
                            errorMessage = 'Largura de banda inválida (0-160 MHz)';
                        }
                        break;
                    case 'modal-channel':
                        if (!isValidChannel(input.value)) {
                            isValid = false;
                            errorMessage = 'Canal inválido (1-165)';
                        }
                        break;
                }

                // Atualiza feedback visual
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
                }
            });
        });

        // Validação no envio
        formModal.addEventListener('submit', function(event) {
            let isValid = true;
            inputs.forEach(input => {
                if (!input.value.trim()) {
                    isValid = false;
                    input.classList.add('is-invalid');
                }
            });

            if (!isValid) {
                event.preventDefault();
                alert('Preencha todos os campos obrigatórios.');
            }
        });
    }
});

// Atualiza coordenadas no formulário
function updateCoordinates(lat, lng) {
    const latitudeInput = document.getElementById('modal-latitude');
    const longitudeInput = document.getElementById('modal-longitude');
    
    if (latitudeInput && longitudeInput) {
        latitudeInput.value = lat.toFixed(6);
        longitudeInput.value = lng.toFixed(6);
    }
}

// Expõe função globalmente
window.updateCoordinates = updateCoordinates;