window.addEventListener('DOMContentLoaded', function() {
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
        .grafo-container {
            width: 100%;
            height: 45vh;
            position: relative;
            border: 2px solid #ccc;
            border-radius: 8px;
            padding: 16px 10px 32px;
            background-color: #fff;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .grafo-container + .grafo-container {
            margin-top: 32px;
        }
        .grafo-container.vazio {
            border: none;
            background: transparent;
            box-shadow: none;
        }
        .cy {
            width: 100%;
            height: 100%;
        }
        .legenda {
            position: absolute;
            top: 20px;
            right: 20px;
            width: 220px;
            padding: 15px;
            background: rgba(245, 245, 245, 0.95);
            border: 1px solid #ddd;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            max-height: calc(100% - 40px);
            overflow-y: auto;
            z-index: 10;
            margin: 0;
        }
        .legenda-item {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }
        .cor-amostra {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            margin-right: 10px;
            border: 1px solid #ddd;
            flex-shrink: 0;
        }
        .nome-ap {
            font-size: 14px;
            color: #666;
        }
        #tabela-alteracoes-container {
            position: relative;
            z-index: 1;
            margin-top: 48px;
        }
        .info-gasto {
            position: absolute;
            left: 20px;
            bottom: 16px;
            background: none;
            color: #1a237e;
            font-size: 14px;
            font-weight: 400;
            border: none;
            border-radius: 0;
            box-shadow: none;
            text-align: left;
            z-index: 10;
            padding: 0;
            margin: 0;
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
    const graphInstances = {};
    let existingGraphContainer = document.querySelector('.content-container');
    let pageContainer = document.querySelector('.page-container');

    if (!existingGraphContainer) {
        pageContainer = document.createElement('div');
        pageContainer.className = 'page-container';

        const contentContainer = document.createElement('div');
        contentContainer.className = 'content-container';
        const strategyButtons = document.querySelector('.strategy-buttons-container');
        const hrElement = document.querySelector('hr');
        const insertAfter = hrElement || strategyButtons || document.querySelector('h1');

        if (insertAfter && insertAfter.parentNode) {
            insertAfter.parentNode.insertBefore(pageContainer, insertAfter.nextSibling);
            pageContainer.appendChild(contentContainer);
            existingGraphContainer = contentContainer;
        }
    }

    const grafoContainer1 = criarContainerGrafo('cy1');
    const grafoContainer2 = criarContainerGrafo('cy2');
    const executionContainer = document.createElement('div');
    executionContainer.id = 'analysis-execution-container';
    executionContainer.className = 'analysis-execution-card';
    executionContainer.hidden = true;
    const tabelaContainer = document.createElement('div');
    tabelaContainer.id = 'tabela-alteracoes-container';
    tabelaContainer.style.margin = '30px 0 0 0';

    if (existingGraphContainer) {
        existingGraphContainer.appendChild(grafoContainer1);
        existingGraphContainer.appendChild(grafoContainer2);
        existingGraphContainer.appendChild(executionContainer);
    }
    if (pageContainer) {
        pageContainer.appendChild(tabelaContainer);
    }

    function criarContainerGrafo(id) {
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
        container.appendChild(legenda);
        container.appendChild(loadingOverlay);
        return container;
    }

    function getLegendaDiv(containerId) {
        return document.getElementById(containerId).parentNode.querySelector('.legenda');
    }

    function getLoadingOverlay(containerId) {
        return document.getElementById(containerId).parentNode.querySelector('.analysis-loading-overlay');
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

        renderExecutionMetadata(null);

        const tableContainer = document.getElementById('tabela-alteracoes-container');
        if (tableContainer) {
            tableContainer.innerHTML = '';
            tableContainer.className = '';
        }
    }

    function formatExecutionParameters(parameters) {
        const items = Object.entries(parameters || {});
        if (!items.length) {
            return 'Padrao';
        }

        return items.map(([key, value]) => `${key}: ${value}`).join(' | ');
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
                    <span class="analysis-execution-label">Parametros</span>
                    <span class="analysis-execution-value">${formatExecutionParameters(execution.parameters)}</span>
                </div>
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

                if (callback) callback();
            });
    }

    function montarPayloadAnalise(aps) {
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
            parameters: {}
        };
    }

    function renderizarLegenda(legendaDiv, nodes, usarConfiguracaoProposta) {
        legendaDiv.innerHTML = '';

        nodes.forEach(node => {
            const channel = usarConfiguracaoProposta ? node.proposed_channel : node.channel;
            const bandwidth = usarConfiguracaoProposta ? node.proposed_bandwidth : node.bandwidth;
            const frequency = usarConfiguracaoProposta ? node.proposed_frequency : node.frequency;

            const legendaItem = document.createElement('div');
            legendaItem.className = 'legenda-item';
            legendaItem.innerHTML = `
                <div class="cor-amostra" style="background-color: ${node.cor || '#cccccc'}"></div>
                <div class="nome-ap">
                    ${node.label || node.id}<br>
                    Canal: ${channel || 'N/A'}<br>
                    Bandwidth: ${bandwidth || 'N/A'}<br>
                    Frequencia: ${frequency || 'N/A'}
                </div>
            `;
            legendaDiv.appendChild(legendaItem);
        });
    }

    function renderizarCytoscape(containerId, graphData) {
        if (graphInstances[containerId]) {
            graphInstances[containerId].destroy();
        }

        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = '';
        }

        const elements = [];

        graphData.nodes.forEach(node => {
            elements.push({
                data: {
                    id: node.id,
                    label: node.label || node.id,
                    cor: node.cor || '#cccccc'
                }
            });
        });

        graphData.links.forEach(link => {
            elements.push({
                data: {
                    source: link.source,
                    target: link.target,
                    peso: link.peso
                }
            });
        });

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
                    selector: 'edge',
                    style: {
                        'width': function(ele) { return ele.data('peso') * 0.1; },
                        'line-color': '#000',
                        'label': function(ele) {
                            const peso = ele.data('peso');
                            return typeof peso === 'number' ? `${peso.toFixed(2)}%` : '';
                        },
                        'font-size': 10,
                        'color': '#333',
                        'text-background-color': '#fff',
                        'text-background-opacity': 0.7,
                        'text-background-padding': 2
                    }
                }
            ],
            layout: {
                name: 'concentric',
                minNodeSpacing: 100,
                padding: 50,
                concentric: function(node) {
                    return node.degree();
                },
                levelWidth: function() {
                    return 1.5;
                },
                spacingFactor: 1.5,
                animate: true,
                animationDuration: 1000,
                fit: true
            },
            minZoom: 0.1,
            maxZoom: 2.0,
            zoom: 0.5
        });
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

    function atualizarInfoConsumo(containerId, nodes, usarConfiguracaoProposta) {
        const container = document.getElementById(containerId).parentNode;
        let consumoTotal = 0;

        nodes.forEach(node => {
            const bandwidth = usarConfiguracaoProposta ? node.proposed_bandwidth : node.bandwidth;
            const frequency = usarConfiguracaoProposta ? node.proposed_frequency : node.frequency;
            const consumo = consumoEnergia25Mbps(bandwidth, frequency);
            if (consumo) consumoTotal += consumo;
        });

        let infoGasto = container.querySelector('.info-gasto');
        if (!infoGasto) {
            infoGasto = document.createElement('div');
            infoGasto.className = 'info-gasto';
            container.appendChild(infoGasto);
        }

        let dias = 15;
        const inputExistente = infoGasto.querySelector(`#input-dias-${containerId}`);
        if (inputExistente) dias = parseInt(inputExistente.value, 10) || 15;

        const consumoDias = (consumoTotal * 24 * dias) / 1000;
        const valorFinal = consumoDias * 0.72;
        infoGasto.innerHTML = `Dias: <input id='input-dias-${containerId}' type='number' min='1' value='${dias}' style='width:48px; padding:2px; border-radius:4px; border:1px solid #b3d1ff; text-align:center; margin:0 4px 0 4px; font-size:13px;'> <br>Consumo: <b><span id='consumo-span-${containerId}'>${consumoDias.toFixed(2)}</span> kWh</b> | Custo: <b>R$ <span id='custo-span-${containerId}'>${valorFinal.toFixed(2)}</span></b>`;

        const inputDias = infoGasto.querySelector(`#input-dias-${containerId}`);
        const consumoSpan = infoGasto.querySelector(`#consumo-span-${containerId}`);
        const custoSpan = infoGasto.querySelector(`#custo-span-${containerId}`);

        inputDias.oninput = function() {
            const diasNovo = parseInt(inputDias.value, 10) || 1;
            const consumoNovo = (consumoTotal * 24 * diasNovo) / 1000;
            const valorFinalNovo = consumoNovo * 0.72;
            consumoSpan.textContent = consumoNovo.toFixed(2);
            custoSpan.textContent = valorFinalNovo.toFixed(2);
        };
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
            const mudou = (
                original.channel !== proposta.channel ||
                original.bandwidth !== proposta.bandwidth ||
                original.frequency !== proposta.frequency
            );

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="analysis-ap-name">${node.label || node.id}</td>
                <td>${renderConfigPills(original, false)}</td>
                <td class="td-proposta">${renderConfigPills(proposta, mudou)}</td>
                <td><button class="analysis-edit-button btn-editar" type="button"><i class="fa-solid fa-pen"></i><span>Editar</span></button></td>
            `;
            tbody.appendChild(tr);

            const button = tr.querySelector('.btn-editar');
            button.addEventListener('click', function() {
                const tdProposta = tr.querySelector('.td-proposta');

                if (!button.classList.contains('is-saving')) {
                    tdProposta.innerHTML = `
                        <div class="analysis-inline-edit">
                            <input type='text' class='input-edit' value='${proposta.channel}' />
                            <input type='text' class='input-edit' value='${proposta.bandwidth}' />
                            <input type='text' class='input-edit' value='${proposta.frequency}' />
                        </div>
                    `;
                    button.classList.add('is-saving');
                    button.innerHTML = '<i class="fa-solid fa-floppy-disk"></i><span>Salvar</span>';
                    return;
                }

                const inputs = tdProposta.querySelectorAll('.input-edit');
                apsOtimizado[idx].channel = inputs[0].value;
                apsOtimizado[idx].bandwidth = inputs[1].value;
                apsOtimizado[idx].frequency = inputs[2].value;
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
                renderizarCytoscape('cy1', graphData);
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

    function aplicarResultadoAnalise(data, requestToken) {
        if (requestToken !== analysisRequestToken) {
            return;
        }

        if (!data.success) {
            throw new Error(data.error || 'Falha na analise');
        }

        const graphData = data.graph_data || { nodes: [], links: [] };
        renderizarCytoscape('cy2', graphData);
        renderizarLegenda(getLegendaDiv('cy2'), graphData.nodes, true);
        atualizarInfoConsumo('cy2', graphData.nodes, true);
        renderExecutionMetadata(data.execution || null);
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
        currentAnalysisAbortController = new AbortController();
        const response = await fetch(
            (window.ANALYSIS_API && window.ANALYSIS_API.analyzeGraphStream) || '/api/analysis/analyze-graph-stream',
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
                (window.ANALYSIS_API && window.ANALYSIS_API.analyzeGraph) || '/api/analysis/analyze-graph',
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
                            description: 'Aplicando a estrategia escolhida sobre o grafo de colisoes.',
                            step: event.payload.message || 'Iniciando processamento',
                            percentage: null
                        });
                    } else if (event.type === 'progress') {
                        const progress = event.payload || {};
                        const totalNodes = progress.total_nodes || 0;
                        const currentNode = progress.current_node ? ` | Atual: ${progress.current_node}` : '';
                        const isSearchStage = progress.stage === 'search';
                        const processedNodes = isSearchStage
                            ? (progress.processed_nodes || 0)
                            : (progress.painted_nodes || 0);
                        const description = isSearchStage
                            ? 'Buscando cliques maximos no grafo antes da coloracao.'
                            : 'Colorindo os nos do grafo conforme a estrategia selecionada.';
                        const stepText = isSearchStage
                            ? `${processedNodes}/${totalNodes} nos-base explorados${currentNode}`
                            : `${processedNodes}/${totalNodes} nos pintados${currentNode}`;
                        setGraphLoading('cy2', {
                            visible: true,
                            title: `Executando ${getStrategyDisplayName(window.selectedStrategy)}`,
                            description,
                            step: stepText,
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

        const payload = montarPayloadAnalise(apsOtimizado);
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
            setGraphLoading('cy2', { visible: false });
            setAnalysisButtonsDisabled(false);
            if (error && error.name === 'AbortError') {
                return;
            }
            document.getElementById('cy2').innerHTML = '<p style="color:red">Erro ao carregar a analise.</p>';
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
        } catch (error) {
            console.warn('Nao foi possivel obter estrategias do servidor:', error);
        }
    }

    document.querySelectorAll('.btn-server-analysis').forEach(btn => {
        btn.addEventListener('click', () => {
            window.selectedStrategy = btn.getAttribute('data-strategy');
            atualizarBotoesEstrategia();
            criarAnaliseOtimizada();
        });
    });

    document.querySelectorAll('.analysis-loading-cancel').forEach(button => {
        button.addEventListener('click', () => {
            cancelarAnaliseEmExecucao();
        });
    });

    fetchStrategiesFromServer();
    atualizarBotoesEstrategia();

    carregarAPs(() => {
        criarGrafoOriginal();
        setEmptyOptimizedState('Selecione uma estrategia para executar a analise otimizada.');
    });
});
