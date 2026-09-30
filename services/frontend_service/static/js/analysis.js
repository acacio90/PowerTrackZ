window.addEventListener('DOMContentLoaded', function() {
    // Canais escolhidos para as estrategias em cada faixa; nulo enquanto o plano de canais nao carrega.
    let seletorCanais = null;

    window.selectedStrategy = null;

    const style = document.createElement('style');
    style.textContent = `
        .page-container {
            display: flex;
            flex-direction: column;
        }
        .content-container {
            position: relative;
            flex: 1;
            margin-top: 20px;
            display: flex;
            flex-direction: column;
            border: none;
        }
        .analysis-summary {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.75rem;
            margin-bottom: 1rem;
        }
        .analysis-summary[hidden] {
            display: none;
        }
        .analysis-summary-item {
            display: flex;
            flex-direction: column;
            gap: 0.2rem;
            padding: 0.85rem 1rem;
            border: 1px solid #d9e2ec;
            border-radius: 12px;
            background: #f8fafc;
            min-width: 0;
        }
        .analysis-summary-label {
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            color: #607080;
        }
        .analysis-summary-value {
            font-size: 1.2rem;
            font-weight: 700;
            color: #18222d;
            overflow-wrap: anywhere;
        }
        .analysis-summary-detail {
            font-size: 0.85rem;
            color: #526272;
        }
        @media (max-width: 900px) {
            .analysis-summary {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
        .grafos-toolbar {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 0.75rem;
            flex-wrap: wrap;
            margin-bottom: 0.75rem;
            font-size: 0.85rem;
            color: #4b5a67;
        }
        .grafos-toolbar label {
            display: flex;
            align-items: center;
            gap: 0.4rem;
            margin: 0;
        }
        .grafos-toolbar input {
            width: 64px;
            padding: 0.2rem 0.4rem;
            border: 1px solid #c9d3dd;
            border-radius: 6px;
            text-align: center;
        }
        .grafos-comparacao {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 1.25rem;
        }
        .grafo-painel {
            display: flex;
            flex-direction: column;
            gap: 0.6rem;
            min-width: 0;
        }
        .grafo-painel-header {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            gap: 0.75rem;
            flex-wrap: wrap;
        }
        .grafo-painel-titulo {
            margin: 0;
            font-size: 1rem;
            font-weight: 700;
            color: #18222d;
        }
        .grafo-container {
            width: 100%;
            height: clamp(360px, 60vh, 560px);
            position: relative;
            border: 2px solid #ccc;
            border-radius: 8px;
            padding: 10px;
            background-color: #fff;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .cy {
            width: 100%;
            height: 100%;
        }
        .legenda {
            display: flex;
            flex-wrap: wrap;
            gap: 0.35rem 1rem;
            margin: 0;
        }
        .legenda:empty {
            display: none;
        }
        .legenda-item {
            display: flex;
            align-items: center;
        }
        .legenda .legenda-arestas {
            display: flex;
            flex-wrap: wrap;
            gap: 0.35rem 1rem;
            flex-basis: 100%;
            margin: 0 0 0.15rem;
            padding: 0 0 0.35rem;
        }
        .cor-amostra {
            width: 14px;
            height: 14px;
            border-radius: 50%;
            margin-right: 6px;
            border: 1px solid #ddd;
            flex-shrink: 0;
        }
        .nome-ap {
            font-size: 0.8rem;
            color: #5b6875;
        }
        #tabela-alteracoes-container {
            position: relative;
            z-index: 1;
            margin-top: 48px;
        }
        .info-gasto {
            color: #1a237e;
            font-size: 0.85rem;
        }
        @media (max-width: 1100px) {
            .grafos-comparacao {
                grid-template-columns: 1fr;
            }
        }
        .btn-server-analysis.is-selected {
            color: #fff !important;
            box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.18);
        }
        .btn-server-analysis[data-strategy='backtracking'].is-selected {
            background-color: #0d6efd;
            border-color: #0d6efd;
        }
        .btn-server-analysis[data-strategy='greedy'].is-selected {
            background-color: #6c757d;
            border-color: #6c757d;
        }
        .btn-server-analysis[data-strategy='genetic'].is-selected {
            background-color: #198754;
            border-color: #198754;
        }
        .analysis-loading-overlay {
            position: absolute;
            inset: 0;
            display: none;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
            background: rgba(255, 255, 255, 0.92);
            backdrop-filter: blur(3px);
            z-index: 20;
        }
        .analysis-loading-overlay.is-visible {
            display: flex;
        }
        .analysis-loading-card {
            width: min(420px, 100%);
            padding: 1.25rem 1.35rem;
            border: 1px solid rgba(13, 110, 253, 0.15);
            border-radius: 16px;
            background: #fff;
            box-shadow: 0 18px 36px rgba(24, 34, 45, 0.12);
        }
        .analysis-loading-header {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 0.9rem;
        }
        .analysis-loading-spinner {
            width: 1.1rem;
            height: 1.1rem;
            border: 2px solid rgba(13, 110, 253, 0.18);
            border-top-color: #0d6efd;
            border-radius: 999px;
            animation: analysis-spin 0.9s linear infinite;
            flex-shrink: 0;
        }
        .analysis-loading-title {
            margin: 0;
            font-size: 1rem;
            font-weight: 700;
            color: #18222d;
        }
        .analysis-loading-description {
            margin: 0 0 1rem;
            color: #526272;
            font-size: 0.92rem;
            line-height: 1.45;
        }
        .analysis-loading-bar {
            width: 100%;
            height: 0.7rem;
            overflow: hidden;
            border-radius: 999px;
            background: #e9eef4;
        }
        .analysis-loading-fill {
            height: 100%;
            width: 0%;
            border-radius: inherit;
            background: linear-gradient(90deg, #0d6efd 0%, #4dabf7 100%);
            transition: width 0.2s ease;
        }
        .analysis-loading-fill.is-indeterminate {
            width: 38%;
            animation: analysis-loading-slide 1.2s ease-in-out infinite;
        }
        .analysis-loading-meta {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            margin-top: 0.8rem;
            font-size: 0.84rem;
            color: #526272;
        }
        .analysis-loading-cancel {
            margin-top: 1rem;
            width: 100%;
        }
        .analysis-execution-card {
            margin-top: 1rem;
            padding: 1rem 1.1rem;
            border: 1px solid #d9e2ec;
            border-radius: 14px;
            background: #fff;
            box-shadow: 0 8px 20px rgba(24, 34, 45, 0.06);
        }
        .analysis-execution-card[hidden] {
            display: none;
        }
        .analysis-execution-title {
            margin: 0 0 0.75rem;
            font-size: 0.95rem;
            font-weight: 700;
            color: #18222d;
        }
        .analysis-execution-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.7rem 1rem;
        }
        .analysis-execution-item {
            min-width: 0;
        }
        .analysis-execution-label {
            display: block;
            margin-bottom: 0.2rem;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            color: #607080;
        }
        .analysis-execution-value {
            display: block;
            color: #22313f;
            font-size: 0.92rem;
            word-break: break-word;
        }
        @keyframes analysis-spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        @keyframes analysis-loading-slide {
            0% { transform: translateX(-120%); }
            50% { transform: translateX(120%); }
            100% { transform: translateX(-120%); }
        }
    `;
    document.head.appendChild(style);

    let apsOriginais = [];
    let apsOtimizado = [];
    let analysisRequestToken = 0;
    let currentAnalysisJobId = null;
    let currentAnalysisAbortController = null;
    let availableAnalysisThreads = null;
    const graphInstances = {};
    let originalGraphData = null;
    let optimizedGraphData = null;
    let showChangeHighlights = true;
    let lastSummaryExecution = null;
    let existingGraphContainer = document.querySelector('.content-container');
    let pageContainer = document.querySelector('.page-container');

    if (!existingGraphContainer) {
        pageContainer = document.createElement('div');
        pageContainer.className = 'page-container';

        const contentContainer = document.createElement('div');
        contentContainer.className = 'content-container';
        const strategyButtons = document.querySelector('.strategy-buttons-container');
        const runRow = document.querySelector('.analysis-run-row');
        const hrElement = document.querySelector('hr');
        const insertAfter = hrElement || runRow || strategyButtons || document.querySelector('h1');

        if (insertAfter && insertAfter.parentNode) {
            insertAfter.parentNode.insertBefore(pageContainer, insertAfter.nextSibling);
            pageContainer.appendChild(contentContainer);
            existingGraphContainer = contentContainer;
        }
    }

    const summaryContainer = document.createElement('div');
    summaryContainer.id = 'analysis-summary';
    summaryContainer.className = 'analysis-summary';
    summaryContainer.hidden = true;
    const grafosToolbar = document.createElement('div');
    grafosToolbar.className = 'grafos-toolbar';
    grafosToolbar.innerHTML = `
        <label for="input-dias">Dias da estimativa de consumo
            <input id="input-dias" type="number" min="1" value="15">
        </label>
        <button type="button" id="btn-reenquadrar" class="btn btn-sm btn-outline-secondary" title="Reenquadrar os dois grafos">
            <i class="fa-solid fa-expand"></i> Reenquadrar
        </button>
    `;
    const grafosComparacao = document.createElement('div');
    grafosComparacao.className = 'grafos-comparacao';
    grafosComparacao.appendChild(criarContainerGrafo('cy1', 'Configuração original'));
    grafosComparacao.appendChild(criarContainerGrafo('cy2', 'Configuração proposta'));
    const executionContainer = document.createElement('div');
    executionContainer.id = 'analysis-execution-container';
    executionContainer.className = 'analysis-execution-card';
    executionContainer.hidden = true;
    const tabelaContainer = document.createElement('div');
    tabelaContainer.id = 'tabela-alteracoes-container';
    tabelaContainer.style.margin = '30px 0 0 0';

    if (existingGraphContainer) {
        existingGraphContainer.appendChild(summaryContainer);
        existingGraphContainer.appendChild(grafosToolbar);
        existingGraphContainer.appendChild(grafosComparacao);
        existingGraphContainer.appendChild(executionContainer);
    }
    if (pageContainer) {
        pageContainer.appendChild(tabelaContainer);
    }

    // Cada painel tem titulo e consumo acima do quadro do grafo e a legenda abaixo, sem cobrir o grafo.
    function criarContainerGrafo(id, titulo) {
        const painel = document.createElement('section');
        painel.className = 'grafo-painel';

        const header = document.createElement('div');
        header.className = 'grafo-painel-header';
        header.innerHTML = `<h3 class="grafo-painel-titulo">${titulo}</h3><span class="info-gasto"></span>`;

        const container = document.createElement('div');
        container.className = 'grafo-container';

        const cyDiv = document.createElement('div');
        cyDiv.id = id;
        cyDiv.className = 'cy';

        const legenda = document.createElement('div');
        legenda.className = 'legenda';

        const loadingOverlay = document.createElement('div');
        loadingOverlay.className = 'analysis-loading-overlay';
        loadingOverlay.innerHTML = `
            <div class="analysis-loading-card">
                <div class="analysis-loading-header">
                    <div class="analysis-loading-spinner"></div>
                    <p class="analysis-loading-title">Processando analise</p>
                </div>
                <p class="analysis-loading-description">Preparando dados do grafo.</p>
                <div class="analysis-loading-bar">
                    <div class="analysis-loading-fill is-indeterminate"></div>
                </div>
                <div class="analysis-loading-meta">
                    <span class="analysis-loading-step">Aguardando resposta do servidor</span>
                    <span class="analysis-loading-percent">Progresso do algoritmo: --</span>
                </div>
                <button type="button" class="analysis-loading-cancel btn btn-outline-danger">Cancelar</button>
            </div>
        `;

        container.appendChild(cyDiv);
        container.appendChild(loadingOverlay);
        painel.appendChild(header);
        painel.appendChild(container);
        painel.appendChild(legenda);
        return painel;
    }

    function getGraphPanel(containerId) {
        return document.getElementById(containerId).closest('.grafo-painel');
    }

    function getLegendaDiv(containerId) {
        return getGraphPanel(containerId).querySelector('.legenda');
    }

    function getLoadingOverlay(containerId) {
        return getGraphPanel(containerId).querySelector('.analysis-loading-overlay');
    }

    function getStrategyDisplayName(strategy) {
        return {
            backtracking: 'Backtracking',
            greedy: 'Greedy',
            genetic: 'Genetic (AG)'
        }[strategy] || 'Selecione uma estrategia';
    }

    function setAnalysisButtonsDisabled(disabled) {
        document.querySelectorAll('.btn-server-analysis').forEach(button => {
            button.disabled = disabled;
        });
        const runButton = document.getElementById('analysis-run-button');
        if (runButton) {
            runButton.disabled = disabled || !window.selectedStrategy;
        }
    }

    // Parametros declarados por cada estrategia no servico de analise, indexados pelo nome da estrategia.
    let strategyDetails = {};

    function escapeHtml(text) {
        return String(text ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function parameterInputId(name) {
        return name === 'thread_count' ? 'analysis-thread-count' : `analysis-parameter-${name}`;
    }

    function renderParameterField(parameter) {
        const inputId = parameterInputId(parameter.name);
        const unit = parameter.unit ? ` (${escapeHtml(parameter.unit)})` : '';
        const startsDisabled = parameter.zero_disables && parameter.default === 0;
        const value = startsDisabled ? '' : parameter.default;
        const meta = parameter.name === 'thread_count'
            ? `<p id="analysis-thread-availability" class="analysis-parameter-meta">${escapeHtml(parameter.description)}</p>`
            : `<p class="analysis-parameter-meta">${escapeHtml(parameter.description)}</p>`;
        const toggle = parameter.zero_disables
            ? `<label class="analysis-parameter-toggle">
                    <input type="checkbox" data-parameter-toggle="${inputId}" ${startsDisabled ? 'checked' : ''}> Sem limite
               </label>`
            : '';

        return `
            <div class="analysis-parameter">
                <label for="${inputId}">${escapeHtml(parameter.label)}${unit}</label>
                <input id="${inputId}" type="number" min="${parameter.min}" max="${parameter.max}"
                       step="${parameter.type === 'integer' ? '1' : 'any'}" value="${value}">
                ${toggle}
                ${meta}
            </div>`;
    }

    function hideParameterError() {
        const errorElement = document.getElementById('analysis-parameter-error');
        if (errorElement) {
            errorElement.hidden = true;
            errorElement.textContent = '';
        }
    }

    function showParameterError(message) {
        const errorElement = document.getElementById('analysis-parameter-error');
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.hidden = false;
        }
    }

    // Monta apenas os campos da estrategia selecionada, a partir da descricao enviada pelo servico.
    function renderStrategyParameters(strategyName) {
        const container = document.getElementById('analysis-parameters');
        if (!container) {
            return;
        }
        hideParameterError();

        const detail = strategyDetails[strategyName];
        if (!detail) {
            container.innerHTML = '<p class="analysis-parameter-meta">Parametros indisponiveis para esta estrategia.</p>';
            return;
        }
        if (!detail.parameters || detail.parameters.length === 0) {
            container.innerHTML = '<p class="analysis-parameter-meta">Esta estrategia nao possui parametros configuraveis.</p>';
            return;
        }

        container.innerHTML = detail.parameters.map(renderParameterField).join('');
        container.querySelectorAll('[data-parameter-toggle]').forEach(toggle => {
            const input = document.getElementById(toggle.getAttribute('data-parameter-toggle'));
            const sync = () => {
                if (input) {
                    input.disabled = toggle.checked;
                }
            };
            toggle.addEventListener('change', sync);
            sync();
        });
        updateThreadAvailabilityInfo();
    }

    // Le e valida os campos da estrategia; devolve os valores ou a primeira mensagem de erro encontrada.
    function collectStrategyParameters() {
        const detail = strategyDetails[window.selectedStrategy];
        const values = {};
        if (!detail || !detail.parameters) {
            return { values };
        }

        for (const parameter of detail.parameters) {
            const inputId = parameterInputId(parameter.name);
            const toggle = document.querySelector(`[data-parameter-toggle="${inputId}"]`);
            if (toggle && toggle.checked) {
                values[parameter.name] = 0;
                continue;
            }

            const input = document.getElementById(inputId);
            const raw = input ? String(input.value).trim().replace(',', '.') : '';
            if (raw === '') {
                values[parameter.name] = parameter.default;
                continue;
            }

            const value = Number(raw);
            if (!Number.isFinite(value)) {
                return { error: `${parameter.label}: informe um numero.` };
            }
            if (parameter.type === 'integer' && !Number.isInteger(value)) {
                return { error: `${parameter.label}: informe um numero inteiro.` };
            }
            if (value < parameter.min || value > parameter.max) {
                return { error: `${parameter.label}: informe um valor entre ${parameter.min} e ${parameter.max}.` };
            }
            values[parameter.name] = value;
        }
        return { values };
    }

    function setEmptyOptimizedState(message) {
        if (graphInstances.cy2) {
            graphInstances.cy2.destroy();
            delete graphInstances.cy2;
        }

        const cy2 = document.getElementById('cy2');
        if (cy2) {
            cy2.innerHTML = `<p style="color:#526272; text-align:center; padding-top:3rem;">${message}</p>`;
        }

        const legenda = getLegendaDiv('cy2');
        if (legenda) {
            legenda.innerHTML = '';
        }
        clearInfoConsumo('cy2');
        optimizedGraphData = null;

        renderExecutionMetadata(null);
        renderResultSummary(null);

        const tableContainer = document.getElementById('tabela-alteracoes-container');
        if (tableContainer) {
            tableContainer.innerHTML = '';
            tableContainer.className = '';
        }
    }

    function formatExecutionParameters(parameters, strategyName) {
        const items = Object.entries(parameters || {});
        if (!items.length) {
            return 'Nenhum';
        }

        const declared = ((strategyDetails[strategyName] || {}).parameters || [])
            .reduce((byName, parameter) => ({ ...byName, [parameter.name]: parameter }), {});

        return items.map(([key, value]) => {
            const parameter = declared[key];
            if (!parameter) {
                return `${key}: ${value}`;
            }
            const label = parameter.label.toLowerCase();
            if (parameter.zero_disables && Number(value) === 0) {
                return `${label}: nenhum`;
            }
            return `${label}: ${value}${parameter.unit ? ` ${parameter.unit}` : ''}`;
        }).join(' | ');
    }

    // Traduz o resultado da busca: otima, interrompida pelo limite ou cancelada; o guloso nao garante otimo.
    function describeSearchOutcome(strategy, search) {
        if (strategy !== 'backtracking') {
            return 'Heuristica (sem garantia de otimo)';
        }
        if (search.optimal) {
            return 'Otima';
        }
        if (search.stop_reason === 'time_limit') {
            return 'Melhor encontrada ate o limite de tempo';
        }
        if (search.stop_reason === 'cancelled') {
            return 'Melhor encontrada ate o cancelamento';
        }
        return 'Nao otima';
    }

    function renderSearchMetadata(strategy, search) {
        if (!search) {
            return '';
        }

        const items = [`
                <div class="analysis-execution-item">
                    <span class="analysis-execution-label">Solucao</span>
                    <span class="analysis-execution-value">${describeSearchOutcome(strategy, search)}</span>
                </div>`];

        if (strategy === 'backtracking') {
            items.push(`
                <div class="analysis-execution-item">
                    <span class="analysis-execution-label">Conflitos Guloso / Final</span>
                    <span class="analysis-execution-value">${search.greedy_conflicts ?? '-'} / ${search.conflicts ?? '-'}</span>
                </div>`);
            items.push(`
                <div class="analysis-execution-item">
                    <span class="analysis-execution-label">Nos Explorados</span>
                    <span class="analysis-execution-value">${search.nodes_explored != null ? Number(search.nodes_explored).toLocaleString('pt-BR') : '-'}</span>
                </div>`);
        }

        return items.join('');
    }

    // Uma linha por faixa: cada faixa e um grafo resolvido separadamente, com o proprio conjunto de canais (k).
    function renderBandsMetadata(strategy, bands) {
        return (bands || []).map(band => {
            const search = band.search || {};
            const conflicts = strategy === 'backtracking'
                ? `conflitos ${search.greedy_conflicts ?? '-'} / ${search.conflicts ?? '-'}`
                : `conflitos ${search.conflicts ?? '-'}`;
            return `
                <div class="analysis-execution-item">
                    <span class="analysis-execution-label">Faixa ${escapeHtml(String(band.frequency).replace('.', ','))}</span>
                    <span class="analysis-execution-value">${band.nodes} APs | ${band.edges} arestas | k = ${band.profile_count} | ${conflicts} | ${describeSearchOutcome(strategy, search)}</span>
                </div>`;
        }).join('');
    }

    function renderExecutionMetadata(execution) {
        const container = document.getElementById('analysis-execution-container');
        if (!container) {
            return;
        }

        if (!execution) {
            container.hidden = true;
            container.innerHTML = '';
            return;
        }

        const graphSnapshot = execution.graph_snapshot || {};
        const comparison = execution.comparison || {};
        container.hidden = false;
        container.innerHTML = `
            <h3 class="analysis-execution-title">Metadados de Execucao</h3>
            <div class="analysis-execution-grid">
                <div class="analysis-execution-item">
                    <span class="analysis-execution-label">Estrategia</span>
                    <span class="analysis-execution-value">${execution.strategy || '-'}</span>
                </div>
                <div class="analysis-execution-item">
                    <span class="analysis-execution-label">Tempo</span>
                    <span class="analysis-execution-value">${execution.duration_ms != null ? `${execution.duration_ms} ms` : '-'}</span>
                </div>
                <div class="analysis-execution-item">
                    <span class="analysis-execution-label">Nos</span>
                    <span class="analysis-execution-value">${graphSnapshot.nodes ?? '-'}</span>
                </div>
                <div class="analysis-execution-item">
                    <span class="analysis-execution-label">Arestas</span>
                    <span class="analysis-execution-value">${graphSnapshot.edges ?? '-'}</span>
                </div>
                <div class="analysis-execution-item">
                    <span class="analysis-execution-label">Densidade</span>
                    <span class="analysis-execution-value">${graphSnapshot.density != null ? graphSnapshot.density : '-'}</span>
                </div>
                <div class="analysis-execution-item">
                    <span class="analysis-execution-label">Arestas Antes / Depois</span>
                    <span class="analysis-execution-value">${comparison.edges_before != null ? comparison.edges_before : '-'} / ${comparison.edges_after != null ? comparison.edges_after : '-'}</span>
                </div>
                <div class="analysis-execution-item">
                    <span class="analysis-execution-label">Densidade Antes / Depois</span>
                    <span class="analysis-execution-value">${comparison.density_before != null ? comparison.density_before : '-'} / ${comparison.density_after != null ? comparison.density_after : '-'}</span>
                </div>
                <div class="analysis-execution-item">
                    <span class="analysis-execution-label">Parametros</span>
                    <span class="analysis-execution-value">${formatExecutionParameters(execution.parameters, execution.strategy)}</span>
                </div>${renderSearchMetadata(execution.strategy, execution.search)}${renderBandsMetadata(execution.strategy, execution.bands)}
            </div>
        `;
    }

    function countConflicts(graphData) {
        return (graphData?.links || [])
            .filter(link => (Number(link.interference_peso ?? link.peso) || 0) > 0)
            .length;
    }

    function formatPercentChange(before, after) {
        if (!(before > 0)) {
            return '-';
        }
        const change = ((after - before) / before) * 100;
        return `${change > 0 ? '+' : ''}${change.toFixed(1).replace('.', ',')}%`;
    }

    function consumptionForDays(containerId) {
        const painel = getGraphPanel(containerId);
        if (painel.dataset.consumoTotal === undefined) {
            return null;
        }
        return (Number(painel.dataset.consumoTotal) * 24 * getConsumptionDays()) / 1000;
    }

    // Resumo do resultado acima dos grafos; os conflitos sao contados nas arestas desenhadas em vermelho.

    function renderResultSummary(execution) {
        const container = document.getElementById('analysis-summary');
        if (!container) {
            return;
        }

        lastSummaryExecution = execution;
        if (!execution || !optimizedGraphData) {
            container.hidden = true;
            container.innerHTML = '';
            return;
        }

        const conflictsBefore = countConflicts(originalGraphData);
        const conflictsAfter = countConflicts(optimizedGraphData);
        const nodes = optimizedGraphData.nodes || [];
        const changedCount = nodes.filter(nodeConfigChanged).length;
        const energyBefore = consumptionForDays('cy1');
        const energyAfter = consumptionForDays('cy2');
        const energyDelta = energyBefore != null && energyAfter != null ? energyAfter - energyBefore : null;
        const solution = execution.search
            ? describeSearchOutcome(execution.strategy, execution.search)
            : (execution.strategy === 'greedy' ? describeSearchOutcome('greedy', {}) : '-');
        const kwh = value => `${value.toFixed(2).replace('.', ',')} kWh`;

        container.hidden = false;
        container.innerHTML = `
            <div class="analysis-summary-item">
                <span class="analysis-summary-label">Conflitos</span>
                <span class="analysis-summary-value">${conflictsBefore} &rarr; ${conflictsAfter}</span>
                <span class="analysis-summary-detail">${formatPercentChange(conflictsBefore, conflictsAfter)}</span>
            </div>
            <div class="analysis-summary-item">
                <span class="analysis-summary-label">APs alterados</span>
                <span class="analysis-summary-value">${changedCount} de ${nodes.length}</span>
                <span class="analysis-summary-detail">${nodes.length ? `${Math.round((changedCount / nodes.length) * 100)}% dos APs` : '-'}</span>
            </div>
            <div class="analysis-summary-item">
                <span class="analysis-summary-label">Consumo em ${getConsumptionDays()} dia(s)</span>
                <span class="analysis-summary-value">${energyBefore != null && energyAfter != null ? `${kwh(energyBefore)} &rarr; ${kwh(energyAfter)}` : '-'}</span>
                <span class="analysis-summary-detail">${energyDelta != null ? `${energyDelta > 0 ? '+' : ''}${kwh(energyDelta)} (${formatPercentChange(energyBefore, energyAfter)})` : '-'}</span>
            </div>
            <div class="analysis-summary-item">
                <span class="analysis-summary-label">${escapeHtml(getStrategyDisplayName(execution.strategy))}</span>
                <span class="analysis-summary-value">${execution.duration_ms != null ? `${Number(execution.duration_ms).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} ms` : '-'}</span>
                <span class="analysis-summary-detail">${escapeHtml(solution)}</span>
            </div>
        `;
    }

    function setGraphLoading(containerId, options = {}) {
        const overlay = getLoadingOverlay(containerId);
        if (!overlay) {
            return;
        }

        const {
            visible = true,
            title = 'Processando analise',
            description = 'Preparando dados do grafo.',
            step = 'Aguardando resposta do servidor',
            percentage = null
        } = options;

        overlay.classList.toggle('is-visible', visible);
        if (!visible) {
            return;
        }

        overlay.querySelector('.analysis-loading-title').textContent = title;
        overlay.querySelector('.analysis-loading-description').textContent = description;
        overlay.querySelector('.analysis-loading-step').textContent = step;
        const cancelButton = overlay.querySelector('.analysis-loading-cancel');
        if (cancelButton) {
            cancelButton.hidden = !visible;
        }

        const percentEl = overlay.querySelector('.analysis-loading-percent');
        const fillEl = overlay.querySelector('.analysis-loading-fill');

        if (typeof percentage === 'number' && Number.isFinite(percentage)) {
            const normalized = Math.max(0, Math.min(100, percentage));
            percentEl.textContent = `Progresso do algoritmo: ${normalized.toFixed(0)}%`;
            fillEl.classList.remove('is-indeterminate');
            fillEl.style.width = `${normalized}%`;
        } else {
            percentEl.textContent = 'Progresso do algoritmo: --';
            fillEl.classList.add('is-indeterminate');
            fillEl.style.width = '';
        }
    }

    function atualizarBotoesEstrategia() {
        document.querySelectorAll('.btn-server-analysis').forEach(btn => {
            const ativa = btn.getAttribute('data-strategy') === window.selectedStrategy;
            btn.classList.toggle('is-selected', ativa);
            btn.setAttribute('aria-pressed', ativa ? 'true' : 'false');
        });
    }

    function getRaio(frequency) {
        if (!frequency) return 10;
        const freq = String(frequency).replace(',', '.');
        if (freq.startsWith('2.4')) return 20;
        if (freq.startsWith('5')) return 15;
        if (freq.startsWith('6')) return 12;
        return 10;
    }

    function carregarAPs(callback) {
        fetch(window.ACCESS_POINT_URL)
            .then(response => response.json())
            .then(points => {
                const aps = (points || [])
                    .filter(point => point.latitude != null && point.longitude != null)
                    .map(point => ({
                        id: point.id || point.name,
                        x: point.latitude,
                        y: point.longitude,
                        raio: getRaio(point.frequency),
                        label: point.name,
                        channel: point.channel,
                        bandwidth: point.bandwidth,
                        frequency: point.frequency,
                        locked: false
                    }));

                apsOriginais = aps.map(ap => ({ ...ap }));
                apsOtimizado = aps.map(ap => ({ ...ap }));
                updateThreadAvailabilityInfo();

                if (callback) callback();
            });
    }

    function montarPayloadAnalise(aps, parameters) {
        const resolvedParameters = { ...(parameters || {}) };
        if (resolvedParameters.thread_count != null) {
            resolvedParameters.thread_count = Math.min(resolvedParameters.thread_count, getUsefulThreadLimit());
        }

        return {
            aps: aps.map(ap => ({
                id: ap.id,
                x: ap.x,
                y: ap.y,
                raio: ap.raio || 50,
                label: ap.label || ap.id,
                channel: ap.channel,
                bandwidth: ap.bandwidth,
                frequency: ap.frequency,
                locked: Boolean(ap.locked)
            })),
            strategy: window.selectedStrategy,
            parameters: resolvedParameters,
            channels: seletorCanais ? seletorCanais.selecao() : undefined
        };
    }

    function getCurrentGraphNodeCount() {
        const nodes = Array.isArray(apsOtimizado) && apsOtimizado.length > 0
            ? apsOtimizado
            : apsOriginais;
        return Array.isArray(nodes) && nodes.length > 0 ? nodes.length : 1;
    }

    function getUsefulThreadLimit() {
        const graphNodeCount = getCurrentGraphNodeCount();
        if (Number.isFinite(availableAnalysisThreads) && availableAnalysisThreads > 0) {
            return Math.max(1, Math.min(availableAnalysisThreads, graphNodeCount));
        }
        return Math.max(1, graphNodeCount);
    }

    function updateThreadAvailabilityInfo() {
        const threadInput = document.getElementById('analysis-thread-count');
        const threadAvailabilityInfo = document.getElementById('analysis-thread-availability');
        const usefulThreadLimit = getUsefulThreadLimit();

        if (threadInput) {
            threadInput.max = String(usefulThreadLimit);
            const currentValue = parseInt(threadInput.value || '1', 10);
            if (!Number.isFinite(currentValue) || currentValue < 1) {
                threadInput.value = '1';
            } else if (currentValue > usefulThreadLimit) {
                threadInput.value = String(usefulThreadLimit);
            }
        }

        if (threadAvailabilityInfo) {
            if (Number.isFinite(availableAnalysisThreads) && availableAnalysisThreads > 0) {
                threadAvailabilityInfo.textContent = `Threads uteis para este grafo: ${usefulThreadLimit} de ${availableAnalysisThreads} disponiveis`;
            } else {
                threadAvailabilityInfo.textContent = `Threads uteis para este grafo: ${usefulThreadLimit}`;
            }
        }
    }

    function getAnalysisRequestUrls() {
        const api = window.ANALYSIS_API || {};
        if (window.selectedStrategy === 'backtracking') {
            return {
                analyze: api.backtracking || '/api/analysis/backtracking',
                stream: api.backtrackingStream || '/api/analysis/backtracking-stream'
            };
        }

        return {
            analyze: api.analyzeGraph || '/api/analysis/analyze-graph',
            stream: api.analyzeGraphStream || '/api/analysis/analyze-graph-stream'
        };
    }

    function renderizarLegenda(legendaDiv, nodes, usarConfiguracaoProposta) {
        legendaDiv.innerHTML = '';

        const legendGroups = new Map();

        nodes.forEach(node => {
            const channel = usarConfiguracaoProposta ? node.proposed_channel : node.channel;
            const bandwidth = usarConfiguracaoProposta ? node.proposed_bandwidth : node.bandwidth;
            const frequency = usarConfiguracaoProposta ? node.proposed_frequency : node.frequency;
            const color = usarConfiguracaoProposta
                ? (node.proposed_cor || node.cor || '#cccccc')
                : (node.cor || '#cccccc');
            const legendKey = [color, channel || '', bandwidth || '', frequency || ''].join('|');

            if (!legendGroups.has(legendKey)) {
                legendGroups.set(legendKey, {
                    color,
                    channel: channel || 'N/A',
                    bandwidth: bandwidth || 'N/A',
                    frequency: frequency || 'N/A',
                    count: 0
                });
            }

            legendGroups.get(legendKey).count += 1;
        });

        const edgeLegend = document.createElement('div');
        edgeLegend.className = 'legenda-arestas';
        edgeLegend.innerHTML = `
            <div class="legenda-item"><span class="linha-amostra linha-conflito"></span><div class="nome-ap">Conflito (interferencia %)</div></div>
            <div class="legenda-item"><span class="linha-amostra linha-sobreposicao"></span><div class="nome-ap">Sobreposicao sem conflito (%)</div></div>
        `;
        if (usarConfiguracaoProposta && showChangeHighlights) {
            const changedCount = nodes.filter(nodeConfigChanged).length;
            const resolvedCount = graphInstances.cy2 ? graphInstances.cy2.edges('[?resolved]').length : 0;
            edgeLegend.innerHTML += `
                <div class="legenda-item"><span class="linha-amostra linha-resolvida"></span><div class="nome-ap">Conflito resolvido (${resolvedCount})</div></div>
                <div class="legenda-item"><span class="cor-amostra no-alterado"></span><div class="nome-ap">AP com configuracao alterada (${changedCount})</div></div>
            `;
        }
        legendaDiv.appendChild(edgeLegend);

        Array.from(legendGroups.values()).forEach(item => {
            const legendaItem = document.createElement('div');
            legendaItem.className = 'legenda-item';
            legendaItem.innerHTML = `
                <div class="cor-amostra" style="background-color: ${item.color}"></div>
                <div class="nome-ap">${item.count} AP(s) · canal ${item.channel} · ${item.bandwidth} · ${item.frequency}</div>
            `;
            legendaDiv.appendChild(legendaItem);
        });
    }

    const EDGE_CONFLICT_COLOR = '#d62828';
    const EDGE_OVERLAP_COLOR = '#c3cad2';
    const OVERLAP_LABEL_EDGE_LIMIT = 40;

    // Rotulos das arestas sem conflito: visiveis por padrao apenas em grafos pequenos,
    // ate que o usuario escolha explicitamente pelo controle da pagina.
    let showOverlapLabels = true;
    let overlapLabelsChosenByUser = false;

    function applyDefaultOverlapLabelVisibility(edgeCount) {
        if (!overlapLabelsChosenByUser) {
            showOverlapLabels = edgeCount <= OVERLAP_LABEL_EDGE_LIMIT;
        }
        const toggle = document.getElementById('toggle-overlap-labels');
        if (toggle) {
            toggle.checked = showOverlapLabels;
        }
    }

    const CHANGED_NODE_BORDER_COLOR = '#1f2933';

    function edgeKey(source, target) {
        return [String(source), String(target)].sort().join('\u0000');
    }

    function originalConflictKeys() {
        const keys = new Set();
        (originalGraphData?.links || []).forEach(link => {
            if ((Number(link.interference_peso ?? link.peso) || 0) > 0) {
                keys.add(edgeKey(link.source, link.target));
            }
        });
        return keys;
    }

    function nodeConfigChanged(node) {
        return (node.channel || 'N/A') !== (node.proposed_channel || 'N/A')
            || (node.bandwidth || 'N/A') !== (node.proposed_bandwidth || 'N/A')
            || (node.frequency || 'N/A') !== (node.proposed_frequency || 'N/A');
    }

    const GRAPH_LAYOUT_SPAN = 900;
    const GRAPH_MIN_NODE_DISTANCE = 48;

    // Converte latitude e longitude em coordenadas planas (metros) em torno do centro do conjunto,
    // com o norte para cima. A funcao e deterministica, entao os grafos original e otimizado recebem
    // as mesmas posicoes para os mesmos APs.
    function projectNodeCoordinates(nodes) {
        const valid = nodes.filter(node => Number.isFinite(Number(node.x)) && Number.isFinite(Number(node.y)));
        if (valid.length < 2 || valid.length !== nodes.length) {
            return null;
        }

        const meanLatitude = valid.reduce((sum, node) => sum + Number(node.x), 0) / valid.length;
        const meanLongitude = valid.reduce((sum, node) => sum + Number(node.y), 0) / valid.length;
        const metersPerLongitudeDegree = 111320 * Math.cos(meanLatitude * Math.PI / 180);
        const metersPerLatitudeDegree = 110540;

        const projected = nodes.map(node => ({
            id: node.id,
            x: (Number(node.y) - meanLongitude) * metersPerLongitudeDegree,
            y: -(Number(node.x) - meanLatitude) * metersPerLatitudeDegree
        }));

        const xs = projected.map(point => point.x);
        const ys = projected.map(point => point.y);
        const span = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys));
        if (!(span > 0)) {
            return null;
        }

        const scale = GRAPH_LAYOUT_SPAN / span;
        return projected.map(point => ({ id: point.id, x: point.x * scale, y: point.y * scale }));
    }

    // Afasta minimamente os nos mais proximos que a distancia minima, sem alterar a disposicao geral.
    function separateOverlappingNodes(points) {
        for (let iteration = 0; iteration < 30; iteration++) {
            let moved = false;
            for (let i = 0; i < points.length; i++) {
                for (let j = i + 1; j < points.length; j++) {
                    let dx = points[j].x - points[i].x;
                    let dy = points[j].y - points[i].y;
                    let distance = Math.hypot(dx, dy);
                    if (distance >= GRAPH_MIN_NODE_DISTANCE) {
                        continue;
                    }
                    if (distance === 0) {
                        const angle = ((i * 7 + j * 13) % 360) * Math.PI / 180;
                        dx = Math.cos(angle);
                        dy = Math.sin(angle);
                        distance = 1;
                    }
                    const push = (GRAPH_MIN_NODE_DISTANCE - distance) / 2;
                    const ux = dx / distance;
                    const uy = dy / distance;
                    points[i].x -= ux * push;
                    points[i].y -= uy * push;
                    points[j].x += ux * push;
                    points[j].y += uy * push;
                    moved = true;
                }
            }
            if (!moved) {
                break;
            }
        }
        return points;
    }

    // Layout pelas coordenadas dos APs; sem coordenadas validas, usa um layout de forcas que evita sobreposicao.
    function buildGraphLayout(nodes) {
        const projected = projectNodeCoordinates(nodes);
        if (!projected) {
            return {
                name: 'cose',
                animate: false,
                fit: true,
                padding: 40,
                nodeOverlap: 20,
                randomize: false
            };
        }

        const positions = separateOverlappingNodes(projected)
            .reduce((byId, point) => ({ ...byId, [point.id]: { x: point.x, y: point.y } }), {});
        return {
            name: 'preset',
            positions: node => positions[node.id()],
            fit: true,
            padding: 40,
            animate: false
        };
    }

    function renderizarCytoscape(containerId, graphData, usarConfiguracaoProposta = false) {
        if (graphInstances[containerId]) {
            graphInstances[containerId].destroy();
        }

        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = '';
        }

        const elements = [];
        // No grafo otimizado, os conflitos do grafo original que deixaram de existir sao marcados como resolvidos.
        const originalConflicts = usarConfiguracaoProposta ? originalConflictKeys() : new Set();
        const optimizedEdgeKeys = new Set();

        graphData.nodes.forEach(node => {
            elements.push({
                data: {
                    id: node.id,
                    label: node.label || node.id,
                    cor: usarConfiguracaoProposta
                        ? (node.proposed_cor || node.cor || '#cccccc')
                        : (node.cor || '#cccccc'),
                    changed: usarConfiguracaoProposta && nodeConfigChanged(node)
                }
            });
        });

        graphData.links.forEach(link => {
            const collision = Number(link.collision_peso ?? link.peso) || 0;
            const interference = Number(link.interference_peso ?? link.peso) || 0;
            const key = edgeKey(link.source, link.target);
            optimizedEdgeKeys.add(key);
            elements.push({
                data: {
                    source: link.source,
                    target: link.target,
                    peso: link.peso,
                    collision,
                    interference,
                    conflict: interference > 0,
                    resolved: interference <= 0 && originalConflicts.has(key)
                }
            });
        });

        // A nova frequencia pode desfazer a sobreposicao; a aresta resolvida e exibida mesmo assim.
        originalConflicts.forEach(key => {
            if (optimizedEdgeKeys.has(key)) {
                return;
            }
            const [source, target] = key.split('\u0000');
            elements.push({
                data: { source, target, peso: 0, collision: 0, interference: 0, conflict: false, resolved: true, synthetic: true }
            });
        });

        applyDefaultOverlapLabelVisibility(graphData.links.length);

        graphInstances[containerId] = cytoscape({
            container,
            elements,
            style: [
                {
                    selector: 'node',
                    style: {
                        'background-color': 'data(cor)',
                        'label': 'data(label)'
                    }
                },
                {
                    selector: 'node[?changed]',
                    style: {
                        'border-width': function() {
                            return showChangeHighlights ? 4 : 0;
                        },
                        'border-color': CHANGED_NODE_BORDER_COLOR,
                        'font-weight': function() {
                            return showChangeHighlights ? 'bold' : 'normal';
                        }
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 1,
                        'line-color': EDGE_OVERLAP_COLOR,
                        'label': function(ele) {
                            return showOverlapLabels ? `${ele.data('collision').toFixed(1)}%` : '';
                        },
                        'font-size': 9,
                        'color': '#7a8591',
                        'text-background-color': '#fff',
                        'text-background-opacity': 0.8,
                        'text-background-padding': 2,
                        'z-index': 1
                    }
                },
                {
                    // Com os destaques desativados, a aresta resolvida volta a ser uma sobreposicao comum
                    // e a que nao tem mais sobreposicao some.
                    selector: 'edge[?resolved]',
                    style: {
                        'display': function(ele) {
                            return showChangeHighlights || !ele.data('synthetic') ? 'element' : 'none';
                        },
                        'width': function() {
                            return showChangeHighlights ? 2 : 1;
                        },
                        'line-color': function() {
                            return showChangeHighlights ? EDGE_CONFLICT_COLOR : EDGE_OVERLAP_COLOR;
                        },
                        'line-style': function() {
                            return showChangeHighlights ? 'dashed' : 'solid';
                        },
                        'opacity': function() {
                            return showChangeHighlights ? 0.35 : 1;
                        },
                        'label': function(ele) {
                            if (showChangeHighlights || ele.data('synthetic') || !showOverlapLabels) {
                                return '';
                            }
                            return `${ele.data('collision').toFixed(1)}%`;
                        },
                        'z-index': 5
                    }
                },
                {
                    selector: 'edge[?conflict]',
                    style: {
                        'width': function(ele) {
                            return Math.min(8, Math.max(2.5, ele.data('interference') * 0.06));
                        },
                        'line-color': EDGE_CONFLICT_COLOR,
                        'label': function(ele) {
                            return `${ele.data('interference').toFixed(1)}%`;
                        },
                        'font-size': 10,
                        'font-weight': 'bold',
                        'color': EDGE_CONFLICT_COLOR,
                        'z-index': 10
                    }
                }
            ],
            layout: buildGraphLayout(graphData.nodes),
            minZoom: 0.05,
            maxZoom: 3.0
        });

        const cy = graphInstances[containerId];
        const partner = graphInstances[partnerGraphId(containerId)];
        if (partner) {
            // O grafo novo assume o enquadramento atual do outro, para a comparacao continuar alinhada.
            copyViewport(partner, cy);
        }
        cy.on('viewport', () => syncViewport(containerId));
    }

    // Os dois grafos usam as mesmas posicoes, entao replicar zoom e deslocamento mantem cada AP
    // no mesmo ponto da tela nos dois quadros.
    let syncingViewport = false;

    function partnerGraphId(containerId) {
        return containerId === 'cy1' ? 'cy2' : 'cy1';
    }

    function copyViewport(source, target) {
        syncingViewport = true;
        try {
            target.viewport({ zoom: source.zoom(), pan: { ...source.pan() } });
        } finally {
            syncingViewport = false;
        }
    }

    function syncViewport(containerId) {
        if (syncingViewport) {
            return;
        }
        const source = graphInstances[containerId];
        const target = graphInstances[partnerGraphId(containerId)];
        if (source && target) {
            copyViewport(source, target);
        }
    }

    function refitGraphs() {
        const cy = graphInstances.cy1 || graphInstances.cy2;
        if (cy) {
            cy.fit(undefined, 40);
        }
    }

    const btnReenquadrar = document.getElementById('btn-reenquadrar');
    if (btnReenquadrar) {
        btnReenquadrar.addEventListener('click', refitGraphs);
    }

    function consumoEnergia25Mbps(bandwidth, frequency) {
        const bw = String(bandwidth || '').replace(/[^0-9]/g, '');
        const freq = String(frequency || '').replace(',', '.');

        if (freq.startsWith('5')) {
            if (bw === '20') return 11.1;
            if (bw === '40') return 10.3;
            if (bw === '80') return 9.9;
        } else if (freq.startsWith('2.4')) {
            if (bw === '20') return 14.5;
            if (bw === '40') return 13.8;
        }
        return null;
    }

    function getConsumptionDays() {
        const input = document.getElementById('input-dias');
        return Math.max(1, parseInt(input && input.value, 10) || 1);
    }

    // Potencia total (W) guardada no painel; o texto e recalculado quando o numero de dias muda.
    function renderInfoConsumo(painel) {
        const infoGasto = painel.querySelector('.info-gasto');
        if (!infoGasto || painel.dataset.consumoTotal === undefined) {
            return;
        }
        const dias = getConsumptionDays();
        const consumoDias = (Number(painel.dataset.consumoTotal) * 24 * dias) / 1000;
        const valorFinal = consumoDias * 0.72;
        infoGasto.innerHTML = `Consumo em ${dias} dia(s): <b>${consumoDias.toFixed(2)} kWh</b> | Custo: <b>R$ ${valorFinal.toFixed(2)}</b>`;
    }

    function atualizarInfoConsumo(containerId, nodes, usarConfiguracaoProposta) {
        let consumoTotal = 0;

        nodes.forEach(node => {
            const bandwidth = usarConfiguracaoProposta ? node.proposed_bandwidth : node.bandwidth;
            const frequency = usarConfiguracaoProposta ? node.proposed_frequency : node.frequency;
            const consumo = consumoEnergia25Mbps(bandwidth, frequency);
            if (consumo) consumoTotal += consumo;
        });

        const painel = getGraphPanel(containerId);
        painel.dataset.consumoTotal = String(consumoTotal);
        renderInfoConsumo(painel);
    }

    function clearInfoConsumo(containerId) {
        const painel = getGraphPanel(containerId);
        delete painel.dataset.consumoTotal;
        const infoGasto = painel.querySelector('.info-gasto');
        if (infoGasto) {
            infoGasto.innerHTML = '';
        }
    }

    const inputDias = document.getElementById('input-dias');
    if (inputDias) {
        inputDias.addEventListener('input', () => {
            document.querySelectorAll('.grafo-painel').forEach(renderInfoConsumo);
            if (lastSummaryExecution) {
                renderResultSummary(lastSummaryExecution);
            }
        });
    }

    function exibirTabelaAlteracoes(nodes, estrategia = null) {
        const container = document.getElementById('tabela-alteracoes-container');
        container.innerHTML = '';
        container.className = 'app-table-card analysis-changes';

        const tabela = document.createElement('table');
        tabela.className = 'app-table analysis-table';
        tabela.innerHTML = `
            <colgroup>
                <col />
                <col />
                <col />
                <col />
            </colgroup>
            <thead>
                <tr>
                    <th>Nome do AP</th>
                    <th>Configuracao Original</th>
                    <th>Configuracao Proposta</th>
                    <th>Acoes</th>
                </tr>
            </thead>
            <tbody></tbody>
        `;

        const tbody = tabela.querySelector('tbody');

        nodes.forEach((node, idx) => {
            const original = {
                channel: node.channel || 'N/A',
                bandwidth: node.bandwidth || 'N/A',
                frequency: node.frequency || 'N/A'
            };
            const proposta = {
                channel: node.proposed_channel || 'N/A',
                bandwidth: node.proposed_bandwidth || 'N/A',
                frequency: node.proposed_frequency || 'N/A'
            };
            const mudou = nodeConfigChanged(node);

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="analysis-ap-name">${node.label || node.id}</td>
                <td>${renderConfigPills(original, false)}</td>
                <td class="td-proposta">${renderConfigPills(proposta, mudou)}</td>
                <td><button class="analysis-edit-button btn-editar" type="button"><i class="fa-solid fa-pen"></i><span>Editar</span></button></td>
            `;
            tbody.appendChild(tr);

            const button = tr.querySelector('.btn-editar');
            button.addEventListener('click', async function() {
                const tdProposta = tr.querySelector('.td-proposta');

                if (!button.classList.contains('is-saving')) {
                    let plano;
                    try {
                        plano = await window.ChannelPlan.carregar();
                    } catch (err) {
                        alert(err.message);
                        return;
                    }

                    // Na proposta, so os canais escolhidos para as estrategias (ou os perfis padrao, sem o seletor).
                    tdProposta.innerHTML = `
                        <div class="analysis-inline-edit">
                            <select class="input-edit" data-field="channel" aria-label="Canal"></select>
                            <select class="input-edit" data-field="bandwidth" aria-label="Largura de banda"></select>
                            <select class="input-edit" data-field="frequency" aria-label="Frequencia"></select>
                        </div>
                    `;
                    const selects = {
                        channel: tdProposta.querySelector('[data-field="channel"]'),
                        bandwidth: tdProposta.querySelector('[data-field="bandwidth"]'),
                        frequency: tdProposta.querySelector('[data-field="frequency"]')
                    };
                    const opcoes = seletorCanais ? seletorCanais.selecao() : plano.profiles;
                    window.ChannelPlan.vincular(selects, opcoes, proposta, { manterAtual: true });
                    button.classList.add('is-saving');
                    button.innerHTML = '<i class="fa-solid fa-floppy-disk"></i><span>Salvar</span>';
                    return;
                }

                apsOtimizado[idx].channel = tdProposta.querySelector('[data-field="channel"]').value;
                apsOtimizado[idx].bandwidth = tdProposta.querySelector('[data-field="bandwidth"]').value;
                apsOtimizado[idx].frequency = tdProposta.querySelector('[data-field="frequency"]').value;
                apsOtimizado[idx].locked = true;
                criarAnaliseOtimizada();
            });
        });

        const titulo = document.createElement('h3');
        const estrategiaNome = estrategia || window.selectedStrategy;
        const nomeEstrategia = getStrategyDisplayName(estrategiaNome);

        titulo.className = 'app-table-title analysis-changes-title';
        titulo.textContent = `Alteracoes de Configuracao Propostas pelo ${nomeEstrategia}`;
        container.appendChild(titulo);

        const tableShell = document.createElement('div');
        tableShell.className = 'app-table-shell analysis-table-shell';

        const tableWrap = document.createElement('div');
        tableWrap.className = 'app-table-wrap analysis-table-wrap';
        tableWrap.appendChild(tabela);
        tableShell.appendChild(tableWrap);

        container.appendChild(tableShell);
    }

    function renderConfigPills(config, highlight = false) {
        const pillClass = highlight ? 'analysis-config-pill is-new' : 'analysis-config-pill';
        const changeIcon = highlight
            ? '<span class="analysis-change-icon" title="Configuracao alterada">&#8635;</span>'
            : '';

        return `
            <div class="analysis-config">
                <span class="${pillClass}">${config.channel}</span>
                <span class="${pillClass}">${config.bandwidth}</span>
                <span class="${pillClass}">${config.frequency}</span>
                ${changeIcon}
            </div>
        `;
    }

    function criarGrafoOriginal() {
        fetch((window.BACKEND_URL || '/api/analysis/collision-graph'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ aps: apsOriginais })
        })
            .then(response => response.json())
            .then(graphData => {
                originalGraphData = graphData;
                renderizarCytoscape('cy1', graphData, false);
                renderizarLegenda(getLegendaDiv('cy1'), graphData.nodes, false);
                atualizarInfoConsumo('cy1', graphData.nodes, false);
            })
            .catch(error => {
                document.getElementById('cy1').innerHTML = '<p style="color:red">Erro ao carregar o grafo.</p>';
                console.error('Erro ao carregar grafo original:', error);
            });
    }

    async function cancelarAnaliseEmExecucao() {
        analysisRequestToken += 1;

        if (!currentAnalysisJobId) {
            if (currentAnalysisAbortController) {
                currentAnalysisAbortController.abort();
                currentAnalysisAbortController = null;
            }
            renderExecutionMetadata(null);
            renderResultSummary(null);
            setGraphLoading('cy2', { visible: false });
            setAnalysisButtonsDisabled(false);
            return;
        }

        try {
            await fetch(
                (window.ANALYSIS_API && window.ANALYSIS_API.cancelAnalysis) || '/api/analysis/cancel-analysis',
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ job_id: currentAnalysisJobId })
                }
            );
        } catch (error) {
            console.warn('Falha ao solicitar cancelamento da analise:', error);
        }

        if (currentAnalysisAbortController) {
            currentAnalysisAbortController.abort();
            currentAnalysisAbortController = null;
        }

        currentAnalysisJobId = null;
        setGraphLoading('cy2', { visible: false });
        setAnalysisButtonsDisabled(false);
        setEmptyOptimizedState('Execucao cancelada. Selecione uma estrategia para iniciar novamente.');
    }

    function cancelarAnaliseSilenciosamenteAoSair() {
        if (!currentAnalysisJobId) {
            return;
        }

        const url = (window.ANALYSIS_API && window.ANALYSIS_API.cancelAnalysis) || '/api/analysis/cancel-analysis';
        const body = JSON.stringify({ job_id: currentAnalysisJobId });

        try {
            if (navigator.sendBeacon) {
                navigator.sendBeacon(url, new Blob([body], { type: 'application/json' }));
            } else {
                fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body,
                    keepalive: true
                }).catch(() => {});
            }
        } catch (error) {
            console.warn('Falha ao solicitar cancelamento ao sair da pagina:', error);
        }
    }

    function aplicarResultadoAnalise(data, requestToken) {
        if (requestToken !== analysisRequestToken) {
            return;
        }

        if (!data.success) {
            throw new Error(data.error || 'Falha na analise');
        }

        const graphData = data.graph_data || { nodes: [], links: [] };
        optimizedGraphData = graphData;
        renderizarCytoscape('cy2', graphData, true);
        renderizarLegenda(getLegendaDiv('cy2'), graphData.nodes, true);
        atualizarInfoConsumo('cy2', graphData.nodes, true);
        renderExecutionMetadata(data.execution || null);
        renderResultSummary(data.execution || { strategy: data.strategy_used });
        exibirTabelaAlteracoes(graphData.nodes, data.strategy_used);
        setGraphLoading('cy2', {
            visible: true,
            title: `Executando ${getStrategyDisplayName(data.strategy_used)}`,
            description: 'Analise concluida com sucesso.',
            step: 'Processamento finalizado',
            percentage: 100
        });
        setAnalysisButtonsDisabled(false);
        currentAnalysisJobId = null;
        currentAnalysisAbortController = null;
        setTimeout(() => {
            if (requestToken === analysisRequestToken) {
                setGraphLoading('cy2', { visible: false });
            }
        }, 500);
    }

    async function consumirStreamAnalise(payload, requestToken) {
        const requestUrls = getAnalysisRequestUrls();
        currentAnalysisAbortController = new AbortController();
        const response = await fetch(
            requestUrls.stream,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
                signal: currentAnalysisAbortController.signal
            }
        );

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || 'Falha ao iniciar a analise');
        }

        if (!response.body || typeof TextDecoder === 'undefined') {
            const fallback = await fetch(
                requestUrls.analyze,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                }
            );
            const fallbackData = await fallback.json();
            aplicarResultadoAnalise(fallbackData, requestToken);
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let finalResult = null;

        while (true) {
            const { value, done } = await reader.read();
            if (done) {
                break;
            }

            buffer += decoder.decode(value, { stream: true });
            let lineBreakIndex = buffer.indexOf('\n');

            while (lineBreakIndex >= 0) {
                const line = buffer.slice(0, lineBreakIndex).trim();
                buffer = buffer.slice(lineBreakIndex + 1);

                if (line) {
                    const event = JSON.parse(line);
                    if (requestToken !== analysisRequestToken) {
                        return;
                    }

                    if (event.type === 'started') {
                        currentAnalysisJobId = event.payload.job_id || null;
                        setGraphLoading('cy2', {
                            visible: true,
                            title: `Executando ${getStrategyDisplayName(window.selectedStrategy)}`,
                            description: 'Aplicando a estrategia escolhida para atribuir configuracoes com menor interferencia.',
                            step: event.payload.message || 'Iniciando processamento',
                            percentage: null
                        });
                    } else if (event.type === 'progress') {
                        const progress = event.payload || {};
                        const stage = progress.stage || 'assignment';
                        let description = 'Processando estrategia.';
                        let stepText = 'Executando';

                        if (stage === 'assignment') {
                            const assignedNodes = progress.assigned_nodes || 0;
                            const totalNodes = progress.total_nodes || 0;
                            const completeAssignmentFound = Boolean(progress.complete_assignment_found);
                            const bestConflicts = Number.isFinite(progress.best_conflicts) && progress.best_conflicts >= 0
                                ? ` | Melhor conflito: ${progress.best_conflicts}`
                                : '';
                            description = 'Atribuindo configuracoes aos APs para minimizar interferencia real.';
                            stepText = completeAssignmentFound
                                ? `Atribuicao completa encontrada, validando alternativas${bestConflicts}`
                                : `${assignedNodes}/${totalNodes} nos com configuracao atribuida${bestConflicts}`;
                        } else {
                            description = 'Montando dados para a atribuicao de configuracoes.';
                            stepText = 'Preparando busca';
                        }
                        setGraphLoading('cy2', {
                            visible: true,
                            title: `Executando ${getStrategyDisplayName(window.selectedStrategy)}`,
                            description,
                            step: progress.band ? `Faixa ${String(progress.band).replace('.', ',')}: ${stepText}` : stepText,
                            percentage: progress.percentage
                        });
                    } else if (event.type === 'result') {
                        finalResult = event.payload;
                    } else if (event.type === 'cancelled') {
                        throw new Error((event.payload && event.payload.error) || 'Analise cancelada pelo usuario');
                    } else if (event.type === 'error') {
                        throw new Error((event.payload && event.payload.error) || 'Falha na analise');
                    }
                }

                lineBreakIndex = buffer.indexOf('\n');
            }
        }

        buffer += decoder.decode();
        if (buffer.trim()) {
            const event = JSON.parse(buffer.trim());
            if (event.type === 'result') {
                finalResult = event.payload;
            } else if (event.type === 'error') {
                throw new Error((event.payload && event.payload.error) || 'Falha na analise');
            }
        }

        if (!finalResult) {
            throw new Error('Resposta de analise incompleta.');
        }

        aplicarResultadoAnalise(finalResult, requestToken);
    }

    async function criarAnaliseOtimizada() {
        if (!window.selectedStrategy) {
            return;
        }

        const { values, error: parameterError } = collectStrategyParameters();
        const channelError = seletorCanais ? seletorCanais.validar() : null;
        if (parameterError || channelError) {
            showParameterError(parameterError || channelError);
            return;
        }
        hideParameterError();

        const payload = montarPayloadAnalise(apsOtimizado, values);
        const requestToken = ++analysisRequestToken;

        setAnalysisButtonsDisabled(true);
        currentAnalysisJobId = null;
        setGraphLoading('cy2', {
            visible: true,
            title: `Executando ${getStrategyDisplayName(window.selectedStrategy)}`,
            description: 'Preparando a analise otimizada do grafo.',
            step: 'Enviando dados para o servidor',
            percentage: null
        });

        try {
            await consumirStreamAnalise(payload, requestToken);
        } catch (error) {
            if (requestToken !== analysisRequestToken) {
                return;
            }

            currentAnalysisJobId = null;
            currentAnalysisAbortController = null;
            renderExecutionMetadata(null);
            renderResultSummary(null);
            setGraphLoading('cy2', { visible: false });
            setAnalysisButtonsDisabled(false);
            if (error && error.name === 'AbortError') {
                return;
            }
            const message = error && error.message ? error.message : 'Erro ao carregar a analise.';
            document.getElementById('cy2').innerHTML = `<p style="color:red">${escapeHtml(message)}</p>`;
            console.error('Erro ao carregar analise otimizada:', error);
        }
    }

    const strategyInfo = document.getElementById('strategyInfo');
    async function fetchStrategiesFromServer() {
        try {
            const res = await fetch((window.ANALYSIS_API && window.ANALYSIS_API.strategies) || '/api/analysis/strategies');
            if (!res.ok) return;

            const data = await res.json();
            if (data && data.success && data.strategies && strategyInfo) {
                strategyInfo.textContent = 'Estrategias: ' + Object.keys(data.strategies).join(', ');
            }
            if (data && Array.isArray(data.strategy_details)) {
                strategyDetails = data.strategy_details.reduce(
                    (byName, detail) => ({ ...byName, [detail.name]: detail }),
                    {}
                );
                if (window.selectedStrategy) {
                    renderStrategyParameters(window.selectedStrategy);
                }
            }
        } catch (error) {
            console.warn('Nao foi possivel obter estrategias do servidor:', error);
        }
    }

    async function fetchAnalysisCapabilities() {
        try {
            const res = await fetch((window.ANALYSIS_API && window.ANALYSIS_API.capabilities) || '/api/analysis/capabilities');
            if (!res.ok) return;

            const data = await res.json();
            const availableThreads = parseInt(data && data.available_threads, 10);
            if (!Number.isFinite(availableThreads) || availableThreads < 1) {
                return;
            }

            availableAnalysisThreads = availableThreads;
            updateThreadAvailabilityInfo();
        } catch (error) {
            console.warn('Nao foi possivel obter capacidades do servidor de analise:', error);
        }
    }

    // Escolher a estrategia apenas exibe seus parametros; a execucao parte do botao Executar analise.
    document.querySelectorAll('.btn-server-analysis').forEach(btn => {
        btn.addEventListener('click', () => {
            window.selectedStrategy = btn.getAttribute('data-strategy');
            atualizarBotoesEstrategia();
            renderStrategyParameters(window.selectedStrategy);
            setAnalysisButtonsDisabled(false);
        });
    });

    const overlapLabelsToggle = document.getElementById('toggle-overlap-labels');
    if (overlapLabelsToggle) {
        overlapLabelsToggle.addEventListener('change', () => {
            overlapLabelsChosenByUser = true;
            showOverlapLabels = overlapLabelsToggle.checked;
            Object.values(graphInstances).forEach(cy => cy.style().update());
        });
    }

    const changeHighlightsToggle = document.getElementById('toggle-change-highlights');
    if (changeHighlightsToggle) {
        changeHighlightsToggle.addEventListener('change', () => {
            showChangeHighlights = changeHighlightsToggle.checked;
            if (graphInstances.cy2) {
                graphInstances.cy2.style().update();
            }
            if (optimizedGraphData) {
                renderizarLegenda(getLegendaDiv('cy2'), optimizedGraphData.nodes, true);
            }
        });
    }

    const runAnalysisButton = document.getElementById('analysis-run-button');
    if (runAnalysisButton) {
        runAnalysisButton.addEventListener('click', () => {
            criarAnaliseOtimizada();
        });
    }

    document.querySelectorAll('.analysis-loading-cancel').forEach(button => {
        button.addEventListener('click', () => {
            cancelarAnaliseEmExecucao();
        });
    });

    window.addEventListener('pagehide', cancelarAnaliseSilenciosamenteAoSair);
    window.addEventListener('beforeunload', cancelarAnaliseSilenciosamenteAoSair);

    const channelsContainer = document.getElementById('analysis-channels');
    if (channelsContainer && window.ChannelPlan) {
        window.ChannelPlan.carregar()
            .then(plano => {
                seletorCanais = window.ChannelPlan.criarSeletor(channelsContainer, plano);
            })
            .catch(err => {
                channelsContainer.innerHTML = '<p class="analysis-parameter-meta">Nao foi possivel carregar os canais; a analise usara os perfis padrao.</p>';
                console.warn(err);
            });
    }

    fetchStrategiesFromServer();
    fetchAnalysisCapabilities();
    atualizarBotoesEstrategia();

    carregarAPs(() => {
        criarGrafoOriginal();
        setEmptyOptimizedState('Selecione uma estrategia, ajuste os parametros e clique em Executar analise.');
    });
});
