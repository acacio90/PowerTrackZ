document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    const inputs = form.querySelectorAll('input[required]');

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
        return !isNaN(num) && num > 0 && num <= 6000; // Frequência em MHz
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
        input.addEventListener('input', function() {
            let isValid = true;
            let errorMessage = '';

            switch(input.id) {
                case 'latitude':
                    if (!isValidCoordinate(input.value, 'latitude')) {
                        isValid = false;
                        errorMessage = 'Latitude deve estar entre -90 e 90';
                    }
                    break;
                case 'longitude':
                    if (!isValidCoordinate(input.value, 'longitude')) {
                        isValid = false;
                        errorMessage = 'Longitude deve estar entre -180 e 180';
                    }
                    break;
                case 'frequency':
                    if (!isValidFrequency(input.value)) {
                        isValid = false;
                        errorMessage = 'Frequência inválida (deve ser entre 0 e 6000 MHz)';
                    }
                    break;
                case 'bandwidth':
                    if (!isValidBandwidth(input.value)) {
                        isValid = false;
                        errorMessage = 'Largura de banda inválida (deve ser entre 0 e 160 MHz)';
                    }
                    break;
                case 'channel':
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
            }
        });
    });

    // Validação no envio do formulário
    form.addEventListener('submit', function(event) {
        let isValid = true;

        inputs.forEach(input => {
            if (!input.value.trim()) {
                isValid = false;
                input.classList.add('is-invalid');
            }
        });

        if (!isValid) {
            event.preventDefault();
            showAlert('Por favor, preencha todos os campos obrigatórios.', 'danger');
        }
    });
}); 