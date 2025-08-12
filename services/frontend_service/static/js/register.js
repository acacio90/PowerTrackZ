document.addEventListener('DOMContentLoaded', function() {
    // Elementos do DOM
    const modal = document.getElementById('modal-add-point');
    const btnAddPoint = document.getElementById('btn-add-point');
    const btnAnalyze = document.getElementById('btn-analyze');
    const closeModal = document.getElementById('close-modal');
    const formModal = document.getElementById('form-add-point');
    const btnCancel = document.getElementById('cancel-modal');

    // Funções da modal
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

    function closeModalHandler() {
        if (modal) modal.style.display = 'none';
    }

    // Event listeners
    if (btnAddPoint) btnAddPoint.addEventListener('click', openModal);
    if (btnAnalyze) btnAnalyze.addEventListener('click', () => window.location.href = '/analysis');
    if (closeModal) closeModal.addEventListener('click', closeModalHandler);
    if (btnCancel) btnCancel.addEventListener('click', closeModalHandler);

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
        const validations = {
            latitude: (num) => num >= -90 && num <= 90,
            longitude: (num) => num >= -180 && num <= 180,
            frequency: (num) => !isNaN(num) && num > 0 && num <= 6,
            bandwidth: (num) => !isNaN(num) && num > 0 && num <= 160,
            channel: (num) => !isNaN(num) && num > 0 && num <= 165
        };

        const errorMessages = {
            'modal-latitude': 'Latitude deve estar entre -90 e 90',
            'modal-longitude': 'Longitude deve estar entre -180 e 180',
            'modal-frequency': 'Frequência inválida (0-6 GHz)',
            'modal-bandwidth': 'Largura de banda inválida (0-160 MHz)',
            'modal-channel': 'Canal inválido (1-165)'
        };

        // Validação em tempo real
        inputs.forEach(input => {
            if (input.readOnly) return;

            input.addEventListener('input', function() {
                const value = parseFloat(input.value);
                const type = input.id.split('-')[1];
                const isValid = validations[type]?.(value) ?? false;

                input.classList.toggle('is-invalid', !isValid);
                input.classList.toggle('is-valid', isValid);

                if (!isValid) {
                    let feedback = input.nextElementSibling;
                    if (!feedback?.classList.contains('invalid-feedback')) {
                        feedback = document.createElement('div');
                        feedback.className = 'invalid-feedback';
                        input.parentNode.insertBefore(feedback, input.nextSibling);
                    }
                    feedback.textContent = errorMessages[input.id];
                }
            });
        });

        // Validação no envio
        formModal.addEventListener('submit', function(event) {
            const isValid = Array.from(inputs).every(input => input.value.trim());
            if (!isValid) {
                event.preventDefault();
                alert('Preencha todos os campos obrigatórios.');
            }
        });
    }
});

// Atualiza coordenadas nos formulários
function updateCoordinates(lat, lng) {
    const forms = [
        {
            modal: document.getElementById('modal-add-point'),
            latInput: document.getElementById('modal-latitude'),
            lngInput: document.getElementById('modal-longitude')
        },
        {
            modal: document.getElementById('modal-edit-point'),
            latInput: document.getElementById('edit-latitude'),
            lngInput: document.getElementById('edit-longitude')
        }
    ];

    forms.forEach(form => {
        if (form.latInput && form.lngInput && form.modal?.style.display !== 'none') {
            form.latInput.value = lat.toFixed(6);
            form.lngInput.value = lng.toFixed(6);
        }
    });
}

window.updateCoordinates = updateCoordinates;