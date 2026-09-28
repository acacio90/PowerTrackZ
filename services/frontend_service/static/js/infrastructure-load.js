// Carregamento de APs na pagina Sua infraestrutura: Zabbix, JSON importado ou topologia gerada.
// Os APs ficam em revisao no modal e so vao para o banco ao clicar em Salvar.
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('modal-load-points');
    if (!modal) return;

    const openButton = document.getElementById('btn-load-points');
    const closeButton = document.getElementById('close-load-modal');
    const cancelButton = document.getElementById('cancel-load-modal');
    const zabbixButton = document.getElementById('btn-load-zabbix');
    const jsonButton = document.getElementById('btn-load-json');
    const jsonInput = document.getElementById('input-load-json');
    const generateButton = document.getElementById('btn-load-generate');
    const generateForm = document.getElementById('form-load-generate');
    const generateSubmit = document.getElementById('submit-load-generate');
    const nodeCountInput = document.getElementById('generate-node-count');
    const cliqueFactorInput = document.getElementById('generate-clique-factor');
    const feedback = document.getElementById('load-feedback');
    const review = document.getElementById('load-review');
    const reviewBody = document.getElementById('load-review-body');
    const reviewSummary = document.getElementById('load-review-summary');
    const reviewSource = document.getElementById('load-review-source');
    const downloadButton = document.getElementById('btn-load-download');
    const saveButton = document.getElementById('btn-load-save');

    const SOURCE_LABELS = {
        zabbix: 'Zabbix',
        import: 'JSON importado',
        generate: 'Topologia gerada'
    };

    let stagedPoints = [];
    let stagedSource = null;
    let stagedPayload = null;

    function escapeHtml(value) {
        return String(value ?? '').replace(/[&<>"']/g, char => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        }[char]));
    }

    function hasCoordinates(point) {
        return point.latitude !== null && point.latitude !== undefined && point.latitude !== ''
            && point.longitude !== null && point.longitude !== undefined && point.longitude !== '';
    }

    function showFeedback(type, title, details = []) {
        feedback.hidden = false;
        feedback.className = `import-feedback import-feedback-${type}`;
        feedback.innerHTML = `
            <div class="import-feedback-title">${escapeHtml(title)}</div>
            ${details.length ? `<ul class="import-feedback-list">${details.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>` : ''}
        `;
    }

    function clearFeedback() {
        feedback.hidden = true;
        feedback.innerHTML = '';
    }

    function setBusy(button, busy, label) {
        if (!button) return;
        if (busy) {
            button.dataset.label = button.innerHTML;
            button.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${label}`;
        } else if (button.dataset.label) {
            button.innerHTML = button.dataset.label;
        }
        button.disabled = busy;
    }

    // O Zabbix nao informa coordenadas; APs ja salvos mantem as coordenadas do inventario.
    function keepSavedCoordinates(points) {
        const saved = new Map((window.savedAccessPoints || []).map(point => [String(point.id), point]));
        return points.map(point => {
            const current = saved.get(point.id);
            if (hasCoordinates(point) || !current || !hasCoordinates(current)) {
                return point;
            }
            return { ...point, latitude: current.latitude, longitude: current.longitude };
        });
    }

    function normalizeZabbixHosts(items) {
        if (!Array.isArray(items)) return [];

        return items.map(item => {
            const rawId = item.index || item.id || '';
            const suffix = typeof rawId === 'string' && rawId.includes('.') ? rawId.split('.').pop() : rawId;
            const rawName = item.name ? item.name.split(' - ')[0] : (item.host || rawId);

            return {
                id: String(rawId || '').trim(),
                name: `${rawName}.${suffix}`.replace(/\.$/, ''),
                frequency: item.frequency || '',
                bandwidth: item.bandwidth || '',
                channel: item.channel || '',
                latitude: item.latitude ?? null,
                longitude: item.longitude ?? null
            };
        }).filter(item => item.id && item.name);
    }

    function normalizeImportedPoints(content) {
        const items = Array.isArray(content)
            ? content
            : Array.isArray(content?.aps)
                ? content.aps
                : null;

        if (!items) {
            throw new Error('O arquivo deve conter uma lista JSON de APs ou um objeto com a chave "aps".');
        }

        return items.map((item, index) => {
            if (!item || typeof item !== 'object' || Array.isArray(item)) {
                throw new Error(`Item ${index + 1}: formato inválido.`);
            }
            if (!item.id || !String(item.id).trim()) {
                throw new Error(`Item ${index + 1}: campo "id" obrigatório.`);
            }
            if (!item.name || !String(item.name).trim()) {
                throw new Error(`Item ${index + 1}: campo "name" obrigatório.`);
            }

            return {
                id: String(item.id).trim(),
                name: String(item.name).trim(),
                frequency: item.frequency || '',
                bandwidth: item.bandwidth || '',
                channel: item.channel || '',
                latitude: item.latitude ?? null,
                longitude: item.longitude ?? null
            };
        });
    }

    function stage(points, source, payload = null) {
        stagedPoints = points;
        stagedSource = source;
        stagedPayload = payload;
        renderReview();
    }

    function renderReview() {
        const count = stagedPoints.length;
        review.hidden = count === 0;
        downloadButton.hidden = count === 0;
        saveButton.disabled = count === 0;
        saveButton.innerHTML = `<i class="fas fa-floppy-disk"></i> Salvar${count ? ` ${count} AP(s)` : ''}`;
        if (!count) {
            reviewBody.innerHTML = '';
            return;
        }

        const withoutCoordinates = stagedPoints.filter(point => !hasCoordinates(point)).length;
        reviewSummary.textContent = withoutCoordinates
            ? `${count} AP(s) carregados, ${withoutCoordinates} sem coordenadas (não participam da análise até serem posicionados no mapa).`
            : `${count} AP(s) carregados.`;
        reviewSource.textContent = SOURCE_LABELS[stagedSource] || '';

        reviewBody.innerHTML = stagedPoints.map(point => `
            <tr class="${hasCoordinates(point) ? '' : 'row-missing-coords'}">
                <td>${escapeHtml(point.name)}</td>
                <td>${escapeHtml(point.id)}</td>
                <td>${escapeHtml(point.frequency || '-')}</td>
                <td>${escapeHtml(point.bandwidth || '-')}</td>
                <td>${escapeHtml(point.channel || '-')}</td>
                <td><span class="coords">${hasCoordinates(point) ? `${escapeHtml(point.latitude)}, ${escapeHtml(point.longitude)}` : '-'}</span></td>
            </tr>
        `).join('');
    }

    function openModal() {
        modal.style.display = 'flex';
    }

    function closeModal() {
        modal.style.display = 'none';
        generateForm.hidden = true;
        clearFeedback();
        stage([], null);
    }

    async function loadFromZabbix() {
        generateForm.hidden = true;
        clearFeedback();
        setBusy(zabbixButton, true, 'Consultando...');

        try {
            const response = await fetch('/zabbix/hosts');
            const result = await response.json().catch(() => ({}));
            if (!response.ok || !result.success) {
                throw new Error(result.error || 'Falha ao consultar o Zabbix.');
            }

            const points = keepSavedCoordinates(normalizeZabbixHosts(result.data));
            stage(points, 'zabbix');
            if (!points.length) {
                showFeedback('warning', 'O Zabbix não retornou APs.');
            }
        } catch (error) {
            stage([], null);
            showFeedback('error', 'Não foi possível carregar os APs do Zabbix.', [
                error.message,
                'Confira a conexão nas configurações (ícone de engrenagem).'
            ]);
        } finally {
            setBusy(zabbixButton, false);
        }
    }

    async function loadFromJson(event) {
        const file = event.target.files && event.target.files[0];
        if (!file) return;

        generateForm.hidden = true;
        clearFeedback();

        try {
            const content = JSON.parse(await file.text());
            stage(normalizeImportedPoints(content), 'import', content);
        } catch (error) {
            stage([], null);
            showFeedback('error', 'Falha ao ler o arquivo JSON.', [error.message]);
        } finally {
            event.target.value = '';
        }
    }

    async function loadFromGenerator(event) {
        event.preventDefault();
        clearFeedback();

        const nodeCount = Number.parseInt(nodeCountInput.value, 10);
        const cliqueFactor = Number.parseInt(cliqueFactorInput.value, 10);
        if (!Number.isInteger(nodeCount) || nodeCount < 2) {
            showFeedback('error', 'Quantidade de nós inválida.', ['Informe um inteiro maior ou igual a 2.']);
            return;
        }
        if (!Number.isInteger(cliqueFactor) || cliqueFactor < 1 || cliqueFactor >= nodeCount) {
            showFeedback('error', 'Fator de clique inválido.', ['Informe um inteiro maior ou igual a 1 e menor que a quantidade de nós.']);
            return;
        }

        setBusy(generateSubmit, true, 'Gerando...');
        try {
            const response = await fetch('/api/access_points/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ node_count: nodeCount, clique_factor: cliqueFactor })
            });
            const result = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(result.error || 'Falha ao gerar a topologia.');
            }

            stage(normalizeImportedPoints(result.payload), 'generate', result.payload);
        } catch (error) {
            stage([], null);
            showFeedback('error', 'Falha ao gerar a topologia.', [error.message]);
        } finally {
            setBusy(generateSubmit, false);
        }
    }

    function downloadStaged() {
        const payload = stagedPayload || { aps: stagedPoints };
        const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `powertrackz-infra-${stagedPoints.length}-aps.json`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    }

    function formatImportError(error) {
        const itemIndex = typeof error.index === 'number' ? error.index + 1 : '?';
        const itemLabel = error.id ? `Item ${itemIndex} (${error.id})` : `Item ${itemIndex}`;
        const reasons = Array.isArray(error.reasons) ? error.reasons.join('; ') : 'erro de validação';
        return `${itemLabel}: ${reasons}`;
    }

    async function saveStaged() {
        if (!stagedPoints.length) return;

        clearFeedback();
        setBusy(saveButton, true, 'Salvando...');
        try {
            const response = await fetch('/api/access_points/import', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(stagedPoints)
            });
            const result = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(result.error || 'Falha ao salvar os APs.');
            }

            const summary = result.summary || {};
            const details = [
                `Criados: ${summary.created || 0}`,
                `Atualizados: ${summary.updated || 0}`,
                `Rejeitados: ${summary.rejected || 0}`,
                ...(summary.errors || []).map(formatImportError)
            ];

            if (summary.rejected) {
                setBusy(saveButton, false);
                showFeedback('warning', 'Salvamento concluído com itens rejeitados.', details);
                return;
            }

            showFeedback('success', 'APs salvos. Atualizando a página...', details);
            window.setTimeout(() => window.location.reload(), 900);
        } catch (error) {
            setBusy(saveButton, false);
            showFeedback('error', 'Falha ao salvar os APs.', [error.message]);
        }
    }

    openButton?.addEventListener('click', openModal);
    closeButton.addEventListener('click', closeModal);
    cancelButton.addEventListener('click', closeModal);
    zabbixButton.addEventListener('click', loadFromZabbix);
    jsonButton.addEventListener('click', () => {
        generateForm.hidden = true;
        jsonInput.click();
    });
    jsonInput.addEventListener('change', loadFromJson);
    generateButton.addEventListener('click', () => {
        generateForm.hidden = !generateForm.hidden;
        if (!generateForm.hidden) nodeCountInput.focus();
    });
    generateForm.addEventListener('submit', loadFromGenerator);
    downloadButton.addEventListener('click', downloadStaged);
    saveButton.addEventListener('click', saveStaged);

    window.addEventListener('click', event => {
        if (event.target === modal) closeModal();
    });
    window.addEventListener('keydown', event => {
        if (event.key === 'Escape' && modal.style.display === 'flex') closeModal();
    });
});
