document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('modal-add-point');
    const btnAddPoint = document.getElementById('btn-add-point');
    const btnAnalyze = document.getElementById('btn-analyze');
    const closeModal = document.getElementById('close-modal');
    const formModal = document.getElementById('form-add-point');
    const btnCancel = document.getElementById('cancel-modal');
    const importButton = document.getElementById('btn-import-json');
    const importInput = document.getElementById('input-import-json');
    const importFeedback = document.getElementById('import-feedback');

    function openModal() {
        if (!modal) return;

        modal.style.display = 'flex';
        if (window.lastSelectedCoordinates) {
            updateCoordinates(
                window.lastSelectedCoordinates.lat,
                window.lastSelectedCoordinates.lng
            );
        }
    }

    function closeModalHandler() {
        if (modal) {
            modal.style.display = 'none';
        }
    }

    function showImportFeedback(type, title, details) {
        if (!importFeedback) return;

        const safeDetails = Array.isArray(details) ? details.filter(Boolean) : [];
        importFeedback.hidden = false;
        importFeedback.className = `import-feedback import-feedback-${type}`;
        importFeedback.innerHTML = `
            <div class="import-feedback-title">${title}</div>
            ${safeDetails.length ? `
                <ul class="import-feedback-list">
                    ${safeDetails.map(item => `<li>${item}</li>`).join('')}
                </ul>
            ` : ''}
        `;
    }

    function formatImportError(error) {
        const itemIndex = typeof error.index === 'number' ? error.index + 1 : '?';
        const itemLabel = error.id ? `Item ${itemIndex} (${error.id})` : `Item ${itemIndex}`;
        const reasons = Array.isArray(error.reasons) ? error.reasons.join('; ') : 'erro de validacao';
        return `${itemLabel}: ${reasons}`;
    }

    function buildSummaryLines(summary) {
        const lines = [
            `Processados: ${summary.processed || 0}`,
            `Criados: ${summary.created || 0}`,
            `Atualizados: ${summary.updated || 0}`,
            `Rejeitados: ${summary.rejected || 0}`
        ];

        if (Array.isArray(summary.errors)) {
            summary.errors.forEach(error => lines.push(formatImportError(error)));
        }

        return lines;
    }

    async function handleImportSelection(event) {
        const file = event.target.files && event.target.files[0];
        if (!file) return;

        if (!file.name.toLowerCase().endsWith('.json')) {
            showImportFeedback('error', 'Selecione um arquivo .json valido.', []);
            event.target.value = '';
            return;
        }

        if (importButton) {
            importButton.disabled = true;
            importButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Importando...';
        }

        try {
            const fileContent = await file.text();
            let payload;

            try {
                payload = JSON.parse(fileContent);
            } catch (parseError) {
                showImportFeedback('error', 'Nao foi possivel ler o arquivo JSON.', [parseError.message]);
                return;
            }

            if (!Array.isArray(payload)) {
                showImportFeedback('error', 'O arquivo deve conter uma lista JSON de APs.', []);
                return;
            }

            const response = await fetch('/api/access_points/import', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json().catch(() => ({}));
            if (!response.ok) {
                const details = [];
                if (result.error) details.push(result.error);
                if (Array.isArray(result.details)) details.push(...result.details);
                if (result.summary && Array.isArray(result.summary.errors)) {
                    result.summary.errors.forEach(error => details.push(formatImportError(error)));
                }
                showImportFeedback('error', 'Falha ao importar APs.', details);
                return;
            }

            const summary = result.summary || {};
            const feedbackType = summary.rejected > 0 ? 'warning' : 'success';
            const title = summary.rejected > 0
                ? 'Importacao concluida com itens rejeitados.'
                : 'Importacao concluida com sucesso.';

            showImportFeedback(feedbackType, title, buildSummaryLines(summary));

            if ((summary.created || 0) > 0 || (summary.updated || 0) > 0) {
                window.setTimeout(() => window.location.reload(), 1800);
            }
        } catch (error) {
            showImportFeedback('error', 'Erro ao enviar o arquivo para importacao.', [error.message]);
        } finally {
            if (importButton) {
                importButton.disabled = false;
                importButton.innerHTML = '<i class="fas fa-file-import"></i> Importar JSON';
            }
            event.target.value = '';
        }
    }

    if (btnAddPoint) btnAddPoint.addEventListener('click', openModal);
    if (btnAnalyze) btnAnalyze.addEventListener('click', () => {
        window.location.href = '/analysis';
    });
    if (closeModal) closeModal.addEventListener('click', closeModalHandler);
    if (btnCancel) btnCancel.addEventListener('click', closeModalHandler);
    if (importButton && importInput) {
        importButton.addEventListener('click', () => importInput.click());
        importInput.addEventListener('change', handleImportSelection);
    }

    window.addEventListener('click', event => {
        if (event.target === modal) {
            closeModalHandler();
        }
    });

    window.addEventListener('keydown', event => {
        if (event.key === 'Escape' && modal) {
            closeModalHandler();
        }
    });

    if (formModal) {
        const inputs = formModal.querySelectorAll('input[required]');
        const validations = {
            latitude: num => num >= -90 && num <= 90,
            longitude: num => num >= -180 && num <= 180,
            frequency: num => !isNaN(num) && num > 0 && num <= 6,
            bandwidth: num => !isNaN(num) && num > 0 && num <= 160,
            channel: num => !isNaN(num) && num > 0 && num <= 165
        };
        const errorMessages = {
            'modal-latitude': 'Latitude deve estar entre -90 e 90',
            'modal-longitude': 'Longitude deve estar entre -180 e 180',
            'modal-frequency': 'Frequencia invalida (0-6 GHz)',
            'modal-bandwidth': 'Largura de banda invalida (0-160 MHz)',
            'modal-channel': 'Canal invalido (1-165)'
        };

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

        formModal.addEventListener('submit', function(event) {
            const isValid = Array.from(inputs).every(input => input.value.trim());
            if (!isValid) {
                event.preventDefault();
                alert('Preencha todos os campos obrigatorios.');
            }
        });
    }
});

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
