window.addEventListener('DOMContentLoaded', function() {
    // Canais escolhidos para as estrategias em cada faixa; nulo enquanto o plano de canais nao carrega.
    let seletorCanais = null;

    window.selectedStrategy = null;

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
    // Ultima configuracao enviada, para repetir a analise com os mesmos dados (aba Execucao).
    let lastAnalysisPayload = null;
    // Grafos criados com a aba Grafos oculta precisam ser redimensionados e reenquadrados ao abri-la.
    const graphsPendingFit = new Set();

    const graphsContainer = document.getElementById('analysis-graphs');
    graphsContainer.appendChild(criarContainerGrafo('cy1', 'Configuração original'));
    graphsContainer.appendChild(criarContainerGrafo('cy2', 'Configuração proposta'));

    // Abas do resultado: Resumo, Grafos, Convergencia, Configuracoes e Execucao.
    const resultTabs = Array.from(document.querySelectorAll('.analysis-tab'));

    function showTab(name) {
        resultTabs.forEach(tab => {
            const active = tab.dataset.tab === name;
            tab.classList.toggle('is-active', active);
            tab.setAttribute('aria-selected', active ? 'true' : 'false');
            tab.tabIndex = active ? 0 : -1;
            document.getElementById(tab.getAttribute('aria-controls')).hidden = !active;
        });
        if (name === 'grafos') {
            Object.values(graphInstances).forEach(cy => cy.resize());
            if (graphsPendingFit.size) {
                graphsPendingFit.clear();
                refitGraphs();
            }
        }
    }

    resultTabs.forEach((tab, index) => {
        tab.addEventListener('click', () => showTab(tab.dataset.tab));
        tab.addEventListener('keydown', event => {
            const step = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
            if (!step) {
                return;
            }
            event.preventDefault();
            const next = resultTabs[(index + step + resultTabs.length) % resultTabs.length];
            showTab(next.dataset.tab);
            next.focus();
        });
    });

    function setEmptyMessage(id, visible) {
        const element = document.getElementById(id);
        if (element) {
            element.hidden = !visible;
        }
    }

    // Cada painel tem titulo e consumo acima do quadro do grafo e a legenda abaixo, sem cobrir o grafo.
    function criarContainerGrafo(id, titulo) {
        const painel = document.createElement('section');
        painel.className = 'grafo-painel';

        const header = document.createElement('div');
        header.className = 'grafo-painel-header';
        header.innerHTML = `<h3 class="grafo-painel-titulo">${titulo}</h3><span class="info-gasto"></span>`;

        const container = document.createElement('div');
        container.className = 'panel panel-flush grafo-container';

        const cyDiv = document.createElement('div');
        cyDiv.id = id;
        cyDiv.className = 'cy';

        const legenda = document.createElement('div');
        legenda.className = 'legenda';

        const loadingOverlay = document.createElement('div');
        loadingOverlay.className = 'analysis-loading-overlay';
        loadingOverlay.innerHTML = `
            <div class="panel panel-floating analysis-loading-card">
                <div class="analysis-loading-header">
                    <div class="analysis-loading-spinner"></div>
                    <p class="analysis-loading-title">Processando a análise</p>
                </div>
                <p class="analysis-loading-description">Preparando dados do grafo.</p>
                <div class="analysis-loading-bar">
                    <div class="analysis-loading-fill is-indeterminate"></div>
                </div>
                <div class="analysis-loading-meta">
                    <span class="analysis-loading-step">Aguardando resposta do servidor</span>
                    <span class="analysis-loading-percent">Progresso do algoritmo: --</span>
                </div>
                <button type="button" class="btn btn-secondary analysis-loading-cancel">Cancelar</button>
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
            greedy: 'Guloso',
            genetic: 'Algoritmo genético'
        }[strategy] || strategy || 'Nenhuma estratégia';
    }

    function setAnalysisButtonsDisabled(disabled) {
        document.querySelectorAll('.btn-server-analysis').forEach(button => {
            button.disabled = disabled || button.dataset.implemented === 'false';
        });
        const runButton = document.getElementById('analysis-run-button');
        if (runButton) {
            runButton.disabled = disabled || !window.selectedStrategy;
        }
    }

    // Parametros declarados por cada estrategia no servico de analise, indexados pelo nome da estrategia.
    let strategyDetails = {};
    // Criterios de otimizacao publicados pelo analysis_service (nome -> rotulo e descricao).
    let objectiveDetails = {};
    const objectiveSelect = document.getElementById('analysis-objective');
    const objectiveDescription = document.getElementById('analysis-objective-description');

    function getObjectiveLabel(name) {
        return (objectiveDetails[name] && objectiveDetails[name].label) || name || 'Padrão';
    }

    function renderObjectiveOptions(objectives, defaultObjective) {
        if (!objectiveSelect || !Array.isArray(objectives) || !objectives.length) {
            return;
        }
        objectiveDetails = objectives.reduce((byName, objective) => ({ ...byName, [objective.name]: objective }), {});
        const current = objectiveSelect.value;
        objectiveSelect.innerHTML = objectives
            .map(objective => `<option value="${escapeHtml(objective.name)}">${escapeHtml(objective.label)}</option>`)
            .join('');
        objectiveSelect.value = objectiveDetails[current] ? current : (defaultObjective || objectives[0].name);
        updateObjectiveDescription();
    }

    function updateObjectiveDescription() {
        const detail = objectiveDetails[objectiveSelect && objectiveSelect.value];
        setStepValue('objective', getObjectiveLabel(objectiveSelect && objectiveSelect.value));
        if (objectiveDescription && detail) {
            objectiveDescription.textContent = detail.description;
        }
    }

    if (objectiveSelect) {
        objectiveSelect.addEventListener('change', updateObjectiveDescription);
    }

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

    // Abre as etapas e secoes recolhidas que contem o campo e o coloca em foco.
    function revealField(input) {
        for (let details = input.closest('details'); details; details = details.parentElement.closest('details')) {
            details.open = true;
        }
        input.focus();
    }

    function showParameterError(message) {
        const errorElement = document.getElementById('analysis-parameter-error');
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.hidden = false;
        }
    }

    // Monta os campos da estrategia selecionada a partir da descricao enviada pelo servico: os comuns
    // ficam visiveis, e os avancados, recolhidos com o valor padrao.
    function renderStrategyParameters(strategyName) {
        const container = document.getElementById('analysis-parameters');
        const advanced = document.getElementById('analysis-advanced');
        const advancedContainer = document.getElementById('analysis-advanced-parameters');
        if (!container) {
            return;
        }
        hideParameterError();
        advanced.hidden = true;
        advancedContainer.innerHTML = '';

        const detail = strategyDetails[strategyName];
        if (!detail) {
            container.innerHTML = '<p class="analysis-parameter-meta">Os parâmetros desta estratégia não estão disponíveis. Recarregue a página.</p>';
            return;
        }
        const parameters = detail.parameters || [];
        const common = parameters.filter(parameter => !parameter.advanced);
        const advancedParameters = parameters.filter(parameter => parameter.advanced);
        container.innerHTML = common.length
            ? common.map(renderParameterField).join('')
            : `<p class="analysis-parameter-meta">${parameters.length ? 'Só há parâmetros avançados nesta estratégia.' : 'Esta estratégia não tem parâmetros configuráveis.'}</p>`;
        if (advancedParameters.length) {
            advancedContainer.innerHTML = advancedParameters.map(renderParameterField).join('');
            advanced.hidden = false;
        }

        document.querySelectorAll('.analysis-sidebar [data-parameter-toggle]').forEach(toggle => {
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
                return { error: `${parameter.label}: informe um número.`, input };
            }
            if (parameter.type === 'integer' && !Number.isInteger(value)) {
                return { error: `${parameter.label}: informe um número inteiro.`, input };
            }
            if (value < parameter.min || value > parameter.max) {
                return { error: `${parameter.label}: informe um valor entre ${parameter.min} e ${parameter.max}.`, input };
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
            cy2.innerHTML = `<p class="cy-message">${message}</p>`;
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
        setEmptyMessage('analysis-changes-empty', true);
        renderConvergence(null);
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
            return 'Heurística (sem garantia de ótimo)';
        }
        if (search.optimal) {
            return 'Ótima';
        }
        if (search.stop_reason === 'time_limit') {
            return 'Melhor encontrada até o limite de tempo';
        }
        if (search.stop_reason === 'cancelled') {
            return 'Melhor encontrada até o cancelamento';
        }
        return 'Não ótima';
    }

    function renderSearchMetadata(strategy, search) {
        if (!search) {
            return '';
        }

        const items = [`
                <div class="analysis-execution-item">
                    <span class="analysis-execution-label">Solução</span>
                    <span class="analysis-execution-value">${describeSearchOutcome(strategy, search)}</span>
                </div>`];

        if (strategy === 'backtracking') {
            items.push(`
                <div class="analysis-execution-item">
                    <span class="analysis-execution-label">Conflitos (guloso / final)</span>
                    <span class="analysis-execution-value">${search.greedy_conflicts ?? '-'} / ${search.conflicts ?? '-'}</span>
                </div>`);
            items.push(`
                <div class="analysis-execution-item">
                    <span class="analysis-execution-label">Nós explorados</span>
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
            setEmptyMessage('analysis-execution-empty', true);
            return;
        }

        const graphSnapshot = execution.graph_snapshot || {};
        const comparison = execution.comparison || {};
        const seed = execution.parameters && execution.parameters.seed != null ? execution.parameters.seed : null;
        setEmptyMessage('analysis-execution-empty', false);
        container.hidden = false;
        container.innerHTML = `
            <div class="analysis-execution-actions">
                <button type="button" id="analysis-repeat" class="btn btn-secondary btn-sm">
                    <i class="fa-solid fa-rotate-right"></i> ${seed != null ? 'Repetir com a mesma semente' : 'Repetir com a mesma configuração'}
                </button>
                <span class="analysis-parameter-meta">${seed != null
                    ? `Semente usada: <strong>${escapeHtml(String(seed))}</strong>`
                    : 'Esta estratégia não usa semente: repetir executa de novo com a mesma estratégia, critério, canais e parâmetros.'}</span>
            </div>
            <h3 class="analysis-execution-title">Metadados da execução</h3>
            <div class="analysis-execution-grid">
                <div class="analysis-execution-item">
                    <span class="analysis-execution-label">Estratégia</span>
                    <span class="analysis-execution-value">${execution.strategy ? escapeHtml(getStrategyDisplayName(execution.strategy)) : '-'}</span>
                </div>
                <div class="analysis-execution-item">
                    <span class="analysis-execution-label">Critério de otimização</span>
                    <span class="analysis-execution-value">${escapeHtml(getObjectiveLabel(execution.objective || 'default'))}</span>
                </div>
                <div class="analysis-execution-item">
                    <span class="analysis-execution-label">Tempo</span>
                    <span class="analysis-execution-value">${execution.duration_ms != null ? `${execution.duration_ms} ms` : '-'}</span>
                </div>
                <div class="analysis-execution-item">
                    <span class="analysis-execution-label">APs</span>
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
                    <span class="analysis-execution-label">Conflitos (antes / depois)</span>
                    <span class="analysis-execution-value">${comparison.conflicts_before != null ? comparison.conflicts_before : '-'} / ${comparison.conflicts_after != null ? comparison.conflicts_after : '-'}</span>
                </div>
                <div class="analysis-execution-item">
                    <span class="analysis-execution-label">Densidade de conflitos (antes / depois)</span>
                    <span class="analysis-execution-value">${comparison.conflict_density_before != null ? comparison.conflict_density_before : '-'} / ${comparison.conflict_density_after != null ? comparison.conflict_density_after : '-'}</span>
                </div>
                <div class="analysis-execution-item">
                    <span class="analysis-execution-label">Parâmetros</span>
                    <span class="analysis-execution-value">${formatExecutionParameters(execution.parameters, execution.strategy)}</span>
                </div>${renderSearchMetadata(execution.strategy, execution.search)}${renderBandsMetadata(execution.strategy, execution.bands)}
            </div>
        `;
        document.getElementById('analysis-repeat').addEventListener('click', () => repetirAnalise(seed));
    }

    // Repete a ultima analise com os mesmos dados enviados; nas estrategias com semente, com a semente usada.
    function repetirAnalise(seed) {
        if (!lastAnalysisPayload) {
            return;
        }
        const payload = JSON.parse(JSON.stringify(lastAnalysisPayload));
        if (seed != null) {
            payload.parameters = { ...(payload.parameters || {}), seed };
        }
        criarAnaliseOtimizada({ payload });
    }

    // Aba Convergencia: so as estrategias iterativas (metaheuristicas) produzem a curva.
    function renderConvergence(execution) {
        const container = document.getElementById('analysis-convergence');
        if (!container) {
            return;
        }
        if (!execution) {
            container.innerHTML = '<p class="analysis-empty">Execute uma análise para ver a convergência.</p>';
            return;
        }
        if (!Array.isArray(execution.convergence) || !execution.convergence.length) {
            const name = escapeHtml(getStrategyDisplayName(execution.strategy));
            container.innerHTML = `<p class="analysis-empty"><i class="fa-solid fa-circle-info"></i> ${name} não produz curva de convergência: a curva mostra a melhor solução encontrada ao longo das iterações das metaheurísticas.</p>`;
            return;
        }
        container.innerHTML = '<p class="analysis-empty">A curva de convergência desta estratégia será exibida aqui.</p>';
    }

    function formatNumber(value, digits = 1) {
        return Number(value).toLocaleString('pt-BR', { minimumFractionDigits: digits, maximumFractionDigits: digits });
    }

    // Variacao de uma metrica em que menor e melhor (conflitos, interferencia, consumo): o sinal e a seta
    // acompanham a cor, para a leitura nao depender so dela.
    function formatChange(before, after, unit = '') {
        if (before == null || after == null) {
            return '<span class="analysis-change is-neutral">-</span>';
        }
        const delta = after - before;
        if (Math.abs(delta) < 1e-9) {
            return '<span class="analysis-change is-neutral">sem alteração</span>';
        }
        const state = delta < 0 ? 'is-better' : delta > 0 ? 'is-worse' : 'is-neutral';
        const arrow = delta < 0 ? '▼' : delta > 0 ? '▲' : '=';
        const sign = delta > 0 ? '+' : delta < 0 ? '−' : '';
        const absolute = `${sign}${formatNumber(Math.abs(delta), unit ? 2 : Number.isInteger(delta) ? 0 : 1)}${unit}`;
        const percent = before > 0 ? ` (${sign}${formatNumber(Math.abs((delta / before) * 100))}%)` : '';
        const meaning = delta < 0 ? 'melhora' : delta > 0 ? 'piora' : 'sem alteração';
        return `<span class="analysis-change ${state}" title="${meaning}">${arrow} ${absolute}${percent}</span>`;
    }

    function pluralizeDays(days) {
        return `${days} dia${days === 1 ? '' : 's'}`;
    }

    // Antes da analise, o Resumo mostra a configuracao atual: as metricas saem do grafo original
    // (/collision-graph), com as mesmas definicoes de conflito (w * s > 0) e interferencia do resultado.
    function frequencyKey(frequency) {
        const value = parseFloat(String(frequency || '').replace(',', '.'));
        return Number.isFinite(value) ? value : null;
    }

    function describeCurrentGraph(nodes, links) {
        const conflicts = links.filter(link => Number(link.interference_peso) > 0);
        const modeled = nodes.filter(node => node.power_w != null);
        return {
            nodes: nodes.length,
            overlaps: links.length,
            conflicts: conflicts.length,
            interference: conflicts.reduce((sum, link) => sum + Number(link.interference_peso), 0),
            power: modeled.reduce((sum, node) => sum + Number(node.power_w), 0),
            unmodeled: nodes.length - modeled.length
        };
    }

    function renderCurrentSummary() {
        const container = document.getElementById('analysis-current');
        if (!originalGraphData) {
            container.hidden = true;
            setEmptyMessage('analysis-summary-empty', true);
            return;
        }
        const nodes = originalGraphData.nodes || [];
        const links = originalGraphData.links || [];
        setEmptyMessage('analysis-summary-empty', false);
        container.hidden = false;
        if (!nodes.length) {
            container.innerHTML = '<p class="analysis-empty">Nenhum AP com coordenadas. Cadastre os APs na página Infraestrutura.</p>';
            return;
        }

        const total = describeCurrentGraph(nodes, links);
        const days = getConsumptionDays();
        const kwh = watts => (watts * 24 * days) / 1000;
        const bandOf = Object.fromEntries(nodes.map(node => [node.id, frequencyKey(node.frequency)]));
        const bands = [...new Set(nodes.map(node => frequencyKey(node.frequency)))]
            .filter(band => band != null)
            .sort((a, b) => a - b);
        const bandRows = bands.map(band => {
            const metrics = describeCurrentGraph(
                nodes.filter(node => bandOf[node.id] === band),
                links.filter(link => bandOf[link.source] === band)
            );
            return `
                <tr>
                    <th scope="row">${band.toLocaleString('pt-BR')} GHz</th>
                    <td>${metrics.nodes}</td>
                    <td>${metrics.overlaps}</td>
                    <td>${metrics.conflicts}</td>
                    <td>${formatNumber(metrics.interference)}</td>
                    <td>${formatNumber(metrics.power)} W</td>
                </tr>`;
        }).join('');
        const unmodeled = total.unmodeled ? ` · ${total.unmodeled} AP(s) fora do modelo de consumo` : '';

        container.innerHTML = `
            <p class="analysis-summary-run">
                <strong>Configuração atual</strong> · antes da análise
            </p>
            <div class="analysis-summary-cards">
                <div class="panel panel-muted panel-compact analysis-summary-item">
                    <span class="analysis-summary-label">APs</span>
                    <span class="analysis-summary-value">${total.nodes}</span>
                    <span class="analysis-summary-detail">em ${bands.length} faixa${bands.length === 1 ? '' : 's'}</span>
                </div>
                <div class="panel panel-muted panel-compact analysis-summary-item">
                    <span class="analysis-summary-label" title="Pares de APs com coberturas sobrepostas na mesma faixa">Sobreposições</span>
                    <span class="analysis-summary-value">${total.overlaps}</span>
                    <span class="analysis-summary-detail">arestas do grafo</span>
                </div>
                <div class="panel panel-muted panel-compact analysis-summary-item">
                    <span class="analysis-summary-label">Conflitos</span>
                    <span class="analysis-summary-value">${total.conflicts}</span>
                    <span class="analysis-summary-detail">${total.overlaps ? `${Math.round((total.conflicts / total.overlaps) * 100)}% das sobreposições` : '-'}</span>
                </div>
                <div class="panel panel-muted panel-compact analysis-summary-item">
                    <span class="analysis-summary-label" title="Soma de w·s nas arestas em conflito">Interferência total</span>
                    <span class="analysis-summary-value">${formatNumber(total.interference)}</span>
                    <span class="analysis-summary-detail">soma de w·s</span>
                </div>
                <div class="panel panel-muted panel-compact analysis-summary-item">
                    <span class="analysis-summary-label">Consumo em ${pluralizeDays(days)} <span class="analysis-summary-unit">(kWh)</span></span>
                    <span class="analysis-summary-value">${formatNumber(kwh(total.power), 2)}</span>
                    <span class="analysis-summary-detail">${formatNumber(total.power)} W${unmodeled}</span>
                </div>
            </div>
            ${bands.length ? `
            <div class="analysis-summary-bands">
                <table class="app-table app-table-compact">
                    <caption>Configuração atual por faixa</caption>
                    <thead>
                        <tr>
                            <th scope="col">Faixa</th>
                            <th scope="col">APs</th>
                            <th scope="col" title="Pares de APs com coberturas sobrepostas">Sobreposições</th>
                            <th scope="col">Conflitos</th>
                            <th scope="col" title="Soma de w·s nas arestas em conflito">Interferência</th>
                            <th scope="col">Potência</th>
                        </tr>
                    </thead>
                    <tbody>${bandRows}</tbody>
                </table>
            </div>` : ''}
            <p class="analysis-parameter-meta">Execute uma análise para comparar com a configuração proposta.</p>`;
    }

    // Resumo do resultado acima dos grafos. Os valores vem da resposta do analysis_service: conflitos e
    // interferencia (soma de w * s) antes e depois, APs alterados e potencia pelo modelo de consumo.
    function renderResultSummary(execution) {
        const container = document.getElementById('analysis-summary');
        if (!container) {
            return;
        }

        lastSummaryExecution = execution;
        if (!execution || !optimizedGraphData || !execution.comparison) {
            container.hidden = true;
            container.innerHTML = '';
            renderCurrentSummary();
            return;
        }
        setEmptyMessage('analysis-summary-empty', false);
        document.getElementById('analysis-current').hidden = true;

        const comparison = execution.comparison;
        const days = getConsumptionDays();
        const kwh = watts => (watts * 24 * days) / 1000;
        const energyBefore = comparison.power_before_w != null ? kwh(comparison.power_before_w) : null;
        const energyAfter = comparison.power_after_w != null ? kwh(comparison.power_after_w) : null;
        const nodes = comparison.nodes || 0;
        const changed = comparison.changed_nodes ?? 0;
        const solution = describeSearchOutcome(execution.strategy, execution.search || {});
        const unmodeled = comparison.power_unmodeled_after
            ? ` · ${comparison.power_unmodeled_after} AP(s) fora do modelo de consumo`
            : '';

        const bands = execution.bands || [];
        const bandRows = bands.map(band => {
            const bandComparison = band.comparison || {};
            const bandSearch = band.search || {};
            return `
                <tr>
                    <th scope="row">${escapeHtml(String(band.frequency).replace('.', ','))}</th>
                    <td>${band.nodes}</td>
                    <td>${band.profile_count}</td>
                    <td>${bandComparison.conflicts_before} → ${bandComparison.conflicts_after} ${formatChange(bandComparison.conflicts_before, bandComparison.conflicts_after)}</td>
                    <td>${formatNumber(bandComparison.interference_before)} → ${formatNumber(bandComparison.interference_after)} ${formatChange(bandComparison.interference_before, bandComparison.interference_after)}</td>
                    <td>${formatNumber(bandComparison.power_before_w)} → ${formatNumber(bandComparison.power_after_w)} W ${formatChange(bandComparison.power_before_w, bandComparison.power_after_w, ' W')}</td>
                    <td>${escapeHtml(describeSearchOutcome(execution.strategy, bandSearch))}</td>
                </tr>`;
        }).join('');

        container.hidden = false;
        container.innerHTML = `
            <p class="analysis-summary-run">
                <strong>${escapeHtml(getStrategyDisplayName(execution.strategy))}</strong>
                · ${escapeHtml(getObjectiveLabel(execution.objective || 'default'))}
                · ${execution.duration_ms != null ? `${Number(execution.duration_ms).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} ms` : '-'}
                · ${escapeHtml(solution)}
            </p>
            <div class="analysis-summary-cards">
                <div class="panel panel-muted panel-compact analysis-summary-item">
                    <span class="analysis-summary-label">Conflitos</span>
                    <span class="analysis-summary-value">${comparison.conflicts_before} → ${comparison.conflicts_after}</span>
                    <span class="analysis-summary-detail">${formatChange(comparison.conflicts_before, comparison.conflicts_after)}</span>
                </div>
                <div class="panel panel-muted panel-compact analysis-summary-item">
                    <span class="analysis-summary-label" title="Soma de w·s nas arestas em conflito">Interferência total</span>
                    <span class="analysis-summary-value">${formatNumber(comparison.interference_before)} → ${formatNumber(comparison.interference_after)}</span>
                    <span class="analysis-summary-detail">${formatChange(comparison.interference_before, comparison.interference_after)}</span>
                </div>
                <div class="panel panel-muted panel-compact analysis-summary-item">
                    <span class="analysis-summary-label">APs alterados</span>
                    <span class="analysis-summary-value">${changed} de ${nodes}</span>
                    <span class="analysis-summary-detail">${nodes ? `${Math.round((changed / nodes) * 100)}% dos APs` : '-'}</span>
                </div>
                <div class="panel panel-muted panel-compact analysis-summary-item">
                    <span class="analysis-summary-label">Consumo em ${pluralizeDays(days)} <span class="analysis-summary-unit">(kWh)</span></span>
                    <span class="analysis-summary-value">${energyBefore != null && energyAfter != null ? `${formatNumber(energyBefore, 2)} → ${formatNumber(energyAfter, 2)}` : '-'}</span>
                    <span class="analysis-summary-detail">${formatChange(energyBefore, energyAfter, ' kWh')}${unmodeled}</span>
                </div>
            </div>
            ${bands.length ? `
            <div class="analysis-summary-bands">
                <table class="app-table app-table-compact">
                    <caption>Resultados por faixa</caption>
                    <thead>
                        <tr>
                            <th scope="col">Faixa</th>
                            <th scope="col">APs</th>
                            <th scope="col" title="Número de perfis de canal disponíveis">k</th>
                            <th scope="col">Conflitos</th>
                            <th scope="col" title="Soma de w·s nas arestas em conflito">Interferência</th>
                            <th scope="col">Potência</th>
                            <th scope="col">Solução</th>
                        </tr>
                    </thead>
                    <tbody>${bandRows}</tbody>
                </table>
            </div>` : ''}
        `;
    }

    function setGraphLoading(containerId, options = {}) {
        const overlay = getLoadingOverlay(containerId);
        if (!overlay) {
            return;
        }

        const {
            visible = true,
            title = 'Processando a análise',
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
        setStepValue('strategy', window.selectedStrategy ? getStrategyDisplayName(window.selectedStrategy) : 'nenhuma');
    }

    // Escolha atual de cada etapa, exibida ao lado do titulo quando a etapa esta recolhida.
    function setStepValue(step, text) {
        const element = document.getElementById(`analysis-step-value-${step}`);
        if (element) {
            element.textContent = text;
            element.title = text;
        }
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
            channels: seletorCanais ? seletorCanais.selecao() : undefined,
            objective: objectiveSelect ? objectiveSelect.value : undefined
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
                threadAvailabilityInfo.textContent = `Threads úteis para este grafo: ${usefulThreadLimit} de ${availableAnalysisThreads} disponíveis`;
            } else {
                threadAvailabilityInfo.textContent = `Threads úteis para este grafo: ${usefulThreadLimit}`;
            }
        }
    }

    function getAnalysisRequestUrls(strategy = window.selectedStrategy) {
        const api = window.ANALYSIS_API || {};
        if (strategy === 'backtracking') {
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

    // Cores das configuracoes nos grafos: paleta categorica dos tokens (--color-graph-series-1..8), atribuida em
    // ordem fixa as configuracoes ordenadas por faixa, largura e canal, e combinada com a forma do no. Nas 8
    // primeiras, laranja e vermelho, que se confundem com outras cores para daltonicos, ganham forma propria; da
    // 9a em diante as cores se repetem em outra forma, sem pares confundiveis na mesma forma (docs/design).
    const GRAPH_SHAPES = ['ellipse', 'round-rectangle', 'triangle', 'diamond', 'hexagon'];
    const CONFIG_STYLE_SEQUENCE = [
        [0, 0], [1, 1], [2, 0], [3, 0], [4, 0], [5, 0], [6, 0], [7, 2],
        [0, 1], [2, 1], [6, 1],
        [0, 2], [2, 2], [3, 2], [5, 2], [6, 2],
        [0, 3], [2, 3], [3, 3], [4, 3], [5, 3], [6, 3],
        [0, 4], [2, 4], [3, 4], [5, 4], [6, 4], [7, 4]
    ];
    let configStyles = new Map();

    function cssToken(name, fallback) {
        const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
        return value || fallback;
    }

    function configKey(channel, bandwidth, frequency) {
        return [channel || 'N/A', bandwidth || 'N/A', frequency || 'N/A'].join('|');
    }

    function firstNumber(text) {
        const match = String(text || '').match(/\d+(?:[.,]\d+)?/);
        return match ? Number(match[0].replace(',', '.')) : Number.POSITIVE_INFINITY;
    }

    function compareConfigs(a, b) {
        return firstNumber(a.frequency) - firstNumber(b.frequency)
            || firstNumber(a.bandwidth) - firstNumber(b.bandwidth)
            || firstNumber(a.channel) - firstNumber(b.channel)
            || a.key.localeCompare(b.key);
    }

    // Recalcula o estilo de cada configuracao a partir das configuracoes dos dois grafos, para que a mesma
    // configuracao tenha a mesma cor e forma no original, no proposto e nas legendas; redesenha o original.
    function atualizarEstilosConfiguracoes() {
        const configs = new Map();
        const add = (channel, bandwidth, frequency) => {
            const key = configKey(channel, bandwidth, frequency);
            if (!configs.has(key)) {
                configs.set(key, { key, channel, bandwidth, frequency });
            }
        };
        (originalGraphData?.nodes || []).forEach(node => add(node.channel, node.bandwidth, node.frequency));
        (optimizedGraphData?.nodes || []).forEach(node => add(node.proposed_channel, node.proposed_bandwidth, node.proposed_frequency));

        const palette = Array.from({ length: 8 }, (_, index) => cssToken(`--color-graph-series-${index + 1}`, '#607080'));
        configStyles = new Map(Array.from(configs.values()).sort(compareConfigs).map((config, index) => {
            const [color, shape] = CONFIG_STYLE_SEQUENCE[index % CONFIG_STYLE_SEQUENCE.length];
            return [config.key, { color: palette[color], shape: GRAPH_SHAPES[shape], order: index }];
        }));

        const cy1 = graphInstances.cy1;
        if (cy1 && originalGraphData) {
            cy1.nodes().forEach(element => {
                const node = originalGraphData.nodes.find(item => String(item.id) === element.id());
                if (node) {
                    const style = estiloConfiguracao(node.channel, node.bandwidth, node.frequency);
                    element.data({ cor: style.color, forma: style.shape });
                }
            });
            renderizarLegenda(getLegendaDiv('cy1'), originalGraphData.nodes, false);
        }
    }

    function estiloConfiguracao(channel, bandwidth, frequency) {
        return configStyles.get(configKey(channel, bandwidth, frequency))
            || { color: cssToken('--color-text-muted', '#607080'), shape: GRAPH_SHAPES[0], order: Number.POSITIVE_INFINITY };
    }

    function renderizarLegenda(legendaDiv, nodes, usarConfiguracaoProposta) {
        if (!legendaDiv) {
            return;
        }
        legendaDiv.innerHTML = '';

        const legendGroups = new Map();

        nodes.forEach(node => {
            const channel = usarConfiguracaoProposta ? node.proposed_channel : node.channel;
            const bandwidth = usarConfiguracaoProposta ? node.proposed_bandwidth : node.bandwidth;
            const frequency = usarConfiguracaoProposta ? node.proposed_frequency : node.frequency;
            const legendKey = configKey(channel, bandwidth, frequency);

            if (!legendGroups.has(legendKey)) {
                const style = estiloConfiguracao(channel, bandwidth, frequency);
                legendGroups.set(legendKey, {
                    color: style.color,
                    shape: style.shape,
                    order: style.order,
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
            <div class="legenda-item"><span class="linha-amostra linha-conflito"></span><div class="nome-ap">Conflito (interferência, %)</div></div>
            <div class="legenda-item"><span class="linha-amostra linha-sobreposicao"></span><div class="nome-ap">Sobreposição sem conflito (%)</div></div>
        `;
        if (usarConfiguracaoProposta && showChangeHighlights) {
            const changedCount = nodes.filter(nodeConfigChanged).length;
            const resolvedCount = graphInstances.cy2 ? graphInstances.cy2.edges('[?resolved]').length : 0;
            edgeLegend.innerHTML += `
                <div class="legenda-item"><span class="linha-amostra linha-resolvida"></span><div class="nome-ap">Conflito resolvido (${resolvedCount})</div></div>
                <div class="legenda-item"><span class="cor-amostra no-alterado"></span><div class="nome-ap">AP com configuração alterada (${changedCount})</div></div>
            `;
        }
        legendaDiv.appendChild(edgeLegend);

        Array.from(legendGroups.values()).sort((a, b) => a.order - b.order).forEach(item => {
            const legendaItem = document.createElement('div');
            legendaItem.className = 'legenda-item';
            legendaItem.innerHTML = `
                <div class="cor-amostra forma-${item.shape}" style="background-color: ${item.color}"></div>
                <div class="nome-ap">${item.count} AP(s) · canal ${item.channel} · ${item.bandwidth} · ${item.frequency}</div>
            `;
            legendaDiv.appendChild(legendaItem);
        });
    }

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
            const style = usarConfiguracaoProposta
                ? estiloConfiguracao(node.proposed_channel, node.proposed_bandwidth, node.proposed_frequency)
                : estiloConfiguracao(node.channel, node.bandwidth, node.frequency);
            elements.push({
                data: {
                    id: node.id,
                    label: node.label || node.id,
                    cor: style.color,
                    forma: style.shape,
                    changed: usarConfiguracaoProposta && nodeConfigChanged(node)
                }
            });
        });

        const conflictColor = cssToken('--color-graph-conflict', '#d62828');
        const overlapColor = cssToken('--color-graph-overlap', '#c3cad2');
        const resolvedColor = cssToken('--color-graph-resolved', 'rgba(214, 40, 40, 0.35)');
        const changedBorderColor = cssToken('--color-text-strong', '#18222d');
        const edgeLabelColor = cssToken('--color-text-muted', '#607080');
        const edgeLabelBackground = cssToken('--color-surface', '#fff');

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
                        'shape': 'data(forma)',
                        'label': 'data(label)'
                    }
                },
                {
                    selector: 'node[?changed]',
                    style: {
                        'border-width': function() {
                            return showChangeHighlights ? 4 : 0;
                        },
                        'border-color': changedBorderColor,
                        'font-weight': function() {
                            return showChangeHighlights ? 'bold' : 'normal';
                        }
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 1,
                        'line-color': overlapColor,
                        'label': function(ele) {
                            return showOverlapLabels ? `${ele.data('collision').toFixed(1)}%` : '';
                        },
                        'font-size': 9,
                        'color': edgeLabelColor,
                        'text-background-color': edgeLabelBackground,
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
                            return showChangeHighlights ? resolvedColor : overlapColor;
                        },
                        'line-style': function() {
                            return showChangeHighlights ? 'dashed' : 'solid';
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
                        'line-color': conflictColor,
                        'label': function(ele) {
                            return `${ele.data('interference').toFixed(1)}%`;
                        },
                        'font-size': 10,
                        'font-weight': 'bold',
                        'color': conflictColor,
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
        if (!container || container.offsetWidth === 0) {
            graphsPendingFit.add(containerId);
        }
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
        infoGasto.innerHTML = `Consumo em ${pluralizeDays(dias)}: <b>${formatNumber(consumoDias, 2)} kWh</b> | Custo: <b>R$ ${formatNumber(valorFinal, 2)}</b>`;
    }

    // A potencia total (W) da configuracao exibida vem do analysis_service (modelo de Dembele et al., 2023).
    function atualizarInfoConsumo(containerId, graphData) {
        const painel = getGraphPanel(containerId);
        const potencia = Number(graphData && graphData.power_w);
        if (!Number.isFinite(potencia)) {
            clearInfoConsumo(containerId);
            return;
        }
        painel.dataset.consumoTotal = String(potencia);
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
            renderResultSummary(lastSummaryExecution);
        });
    }

    function exibirTabelaAlteracoes(nodes, estrategia = null) {
        const container = document.getElementById('tabela-alteracoes-container');
        container.innerHTML = '';
        container.className = 'analysis-changes';
        setEmptyMessage('analysis-changes-empty', false);

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
                    <th>Configuração original</th>
                    <th>Configuração proposta</th>
                    <th>Ações</th>
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
                <td><button class="btn btn-secondary btn-sm analysis-edit-button btn-editar" type="button"><i class="fa-solid fa-pen"></i><span>Editar</span></button></td>
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
                            <select class="input-edit" data-field="frequency" aria-label="Faixa"></select>
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
        titulo.textContent = `Configurações propostas (${nomeEstrategia})`;
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
        const pillClass = highlight ? 'tag tag-accent' : 'tag';
        const changeIcon = highlight
            ? '<span class="analysis-change-icon" title="Configuração alterada">&#8635;</span>'
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
                atualizarEstilosConfiguracoes();
                renderizarCytoscape('cy1', graphData, false);
                renderizarLegenda(getLegendaDiv('cy1'), graphData.nodes, false);
                atualizarInfoConsumo('cy1', graphData);
                if (!lastSummaryExecution) {
                    renderCurrentSummary();
                }
            })
            .catch(error => {
                document.getElementById('analysis-summary-empty').textContent = 'Não foi possível carregar a configuração atual. Recarregue a página.';
                document.getElementById('cy1').innerHTML = '<p class="cy-error">Não foi possível carregar o grafo. Recarregue a página.</p>';
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
        setEmptyOptimizedState('Análise cancelada. Clique em Executar análise para iniciar de novo.');
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
            throw new Error(data.error || 'A análise falhou. Tente executar de novo.');
        }

        const graphData = data.graph_data || { nodes: [], links: [] };
        optimizedGraphData = graphData;
        atualizarEstilosConfiguracoes();
        renderizarCytoscape('cy2', graphData, true);
        renderizarLegenda(getLegendaDiv('cy2'), graphData.nodes, true);
        atualizarInfoConsumo('cy2', graphData);
        renderExecutionMetadata(data.execution || null);
        renderResultSummary(data.execution || { strategy: data.strategy_used });
        exibirTabelaAlteracoes(graphData.nodes, data.strategy_used);
        renderConvergence(data.execution || { strategy: data.strategy_used });
        showTab('resumo');
        setGraphLoading('cy2', {
            visible: true,
            title: `Executando ${getStrategyDisplayName(data.strategy_used)}`,
            description: 'Análise concluída.',
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
        const requestUrls = getAnalysisRequestUrls(payload.strategy);
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
            throw new Error(errorData.error || 'Não foi possível iniciar a análise. Tente executar de novo.');
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
                            description: 'Aplicando a estratégia escolhida para atribuir as configurações de menor interferência.',
                            step: event.payload.message || 'Iniciando processamento',
                            percentage: null
                        });
                    } else if (event.type === 'progress') {
                        const progress = event.payload || {};
                        const stage = progress.stage || 'assignment';
                        let description = 'Processando a estratégia.';
                        let stepText = 'Executando';

                        if (stage === 'assignment') {
                            const assignedNodes = progress.assigned_nodes || 0;
                            const totalNodes = progress.total_nodes || 0;
                            const completeAssignmentFound = Boolean(progress.complete_assignment_found);
                            const bestConflicts = Number.isFinite(progress.best_conflicts) && progress.best_conflicts >= 0
                                ? ` | Melhor conflito: ${progress.best_conflicts}`
                                : '';
                            description = 'Atribuindo configurações aos APs para minimizar a interferência.';
                            stepText = completeAssignmentFound
                                ? `Atribuição completa encontrada, conferindo alternativas${bestConflicts}`
                                : `${assignedNodes}/${totalNodes} APs com configuração atribuída${bestConflicts}`;
                        } else {
                            description = 'Montando os dados para a atribuição de configurações.';
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
                        throw new Error((event.payload && event.payload.error) || 'Análise cancelada.');
                    } else if (event.type === 'error') {
                        throw new Error((event.payload && event.payload.error) || 'A análise falhou. Tente executar de novo.');
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
                throw new Error((event.payload && event.payload.error) || 'A análise falhou. Tente executar de novo.');
            }
        }

        if (!finalResult) {
            throw new Error('A resposta da análise veio incompleta. Tente executar de novo.');
        }

        aplicarResultadoAnalise(finalResult, requestToken);
    }

    async function criarAnaliseOtimizada(options = {}) {
        let payload = options.payload || null;
        if (!payload) {
            if (!window.selectedStrategy) {
                return;
            }
            const { values, error: parameterError, input: invalidInput } = collectStrategyParameters();
            const channelError = seletorCanais ? seletorCanais.validar() : null;
            if (parameterError || channelError) {
                showParameterError(parameterError || channelError);
                if (invalidInput) {
                    revealField(invalidInput);
                }
                return;
            }
            hideParameterError();
            payload = montarPayloadAnalise(apsOtimizado, values);
        }
        lastAnalysisPayload = payload;
        const requestToken = ++analysisRequestToken;
        // O progresso e o cancelamento aparecem sobre o grafo proposto.
        showTab('grafos');

        setAnalysisButtonsDisabled(true);
        currentAnalysisJobId = null;
        setGraphLoading('cy2', {
            visible: true,
            title: `Executando ${getStrategyDisplayName(payload.strategy)}`,
            description: 'Preparando a análise do grafo.',
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
            const message = error && error.message ? error.message : 'Não foi possível carregar a análise. Tente executar de novo.';
            document.getElementById('cy2').innerHTML = `<p class="cy-error">${escapeHtml(message)}</p>`;
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
                strategyInfo.textContent = 'Estratégias: ' + Object.keys(data.strategies).map(getStrategyDisplayName).join(', ');
            }
            if (data && Array.isArray(data.objectives)) {
                renderObjectiveOptions(data.objectives, data.default_objective);
            }
            if (data && Array.isArray(data.strategy_details)) {
                strategyDetails = data.strategy_details.reduce(
                    (byName, detail) => ({ ...byName, [detail.name]: detail }),
                    {}
                );
                renderStrategyList(data.strategy_details);
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

    // Familias exibidas na etapa 1, na ordem; o servico informa a familia de cada estrategia.
    const STRATEGY_FAMILIES = [
        { id: 'exact', label: 'Exata' },
        { id: 'constructive', label: 'Construtiva' },
        { id: 'metaheuristic', label: 'Metaheurísticas' }
    ];
    const STRATEGY_ICONS = { backtracking: 'fa-sitemap', greedy: 'fa-bolt', genetic: 'fa-dna' };
    const strategyList = document.getElementById('analysis-strategy-list');

    function renderStrategyCard(detail) {
        const implemented = detail.implemented !== false;
        const guarantee = detail.exact
            ? '<span class="tag tag-accent">Exato</span>'
            : '<span class="tag">Sem garantia de ótimo</span>';
        return `
            <button type="button" class="analysis-strategy btn-server-analysis" data-strategy="${escapeHtml(detail.name)}"
                    data-implemented="${implemented}" aria-pressed="false" ${implemented ? '' : 'disabled'}>
                <span class="analysis-strategy-name">
                    <i class="fa-solid ${STRATEGY_ICONS[detail.name] || 'fa-diagram-project'}"></i>
                    ${escapeHtml(getStrategyDisplayName(detail.name))}
                </span>
                <span class="analysis-strategy-description">${escapeHtml(detail.description || '')}</span>
                <span class="analysis-strategy-tags">${guarantee}${implemented ? '' : '<span class="tag">Não implementada</span>'}</span>
            </button>`;
    }

    function renderStrategyList(details) {
        const known = STRATEGY_FAMILIES.map(family => family.id);
        const groups = STRATEGY_FAMILIES.concat(
            [...new Set(details.map(detail => detail.family).filter(family => family && !known.includes(family)))]
                .map(family => ({ id: family, label: family }))
        );
        strategyList.innerHTML = groups.map(family => {
            const members = details.filter(detail => (detail.family || 'constructive') === family.id);
            if (!members.length) {
                return '';
            }
            return `
                <div class="analysis-family" role="group" aria-label="${escapeHtml(family.label)}">
                    <h3 class="analysis-family-title">${escapeHtml(family.label)}</h3>
                    ${members.map(renderStrategyCard).join('')}
                </div>`;
        }).join('');
        atualizarBotoesEstrategia();
        setAnalysisButtonsDisabled(Boolean(currentAnalysisJobId));
    }

    // Escolher a estrategia apenas exibe seus parametros; a execucao parte do botao Executar analise.
    strategyList.addEventListener('click', event => {
        const button = event.target.closest('.btn-server-analysis');
        if (!button || button.disabled) {
            return;
        }
        window.selectedStrategy = button.getAttribute('data-strategy');
        atualizarBotoesEstrategia();
        renderStrategyParameters(window.selectedStrategy);
        setAnalysisButtonsDisabled(false);
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

    // Etapa 3: resumo do k de cada faixa; o mapa do espectro abre em um modal.
    const channelsContainer = document.getElementById('analysis-channels');
    const channelSummary = document.getElementById('analysis-channel-summary');
    const spectrumModal = document.getElementById('spectrum-modal');
    const openSpectrumButton = document.getElementById('analysis-open-spectrum');

    function renderChannelSummary() {
        if (!seletorCanais || !seletorCanais.resumo) {
            return;
        }
        const faixas = seletorCanais.resumo();
        setStepValue('channels', faixas.filter(faixa => faixa.k > 0).map(faixa => `${faixa.rotulo}: k = ${faixa.k}`).join(' · '));
        channelSummary.innerHTML = faixas.map(faixa => `
            <li class="analysis-channel-band">
                <span>${escapeHtml(faixa.rotulo)}</span>
                <strong>k = ${faixa.k}</strong>
                <span class="tag ${faixa.padrao ? '' : 'tag-accent'}">${faixa.padrao ? 'padrão' : 'personalizado'}</span>
            </li>`).join('');
    }

    function setSpectrumModal(open) {
        spectrumModal.style.display = open ? 'flex' : 'none';
        if (open) {
            document.getElementById('spectrum-modal-done').focus();
        } else {
            openSpectrumButton.focus();
        }
    }

    openSpectrumButton.addEventListener('click', () => setSpectrumModal(true));
    document.getElementById('spectrum-modal-close').addEventListener('click', () => setSpectrumModal(false));
    document.getElementById('spectrum-modal-done').addEventListener('click', () => setSpectrumModal(false));
    spectrumModal.addEventListener('click', event => {
        if (event.target === spectrumModal) {
            setSpectrumModal(false);
        }
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && spectrumModal.style.display === 'flex') {
            setSpectrumModal(false);
        }
    });
    channelsContainer.addEventListener('channelplan:change', renderChannelSummary);

    if (channelsContainer && window.ChannelPlan) {
        window.ChannelPlan.carregar()
            .then(plano => {
                seletorCanais = window.ChannelPlan.criarSeletor(channelsContainer, plano);
                renderChannelSummary();
                openSpectrumButton.disabled = false;
            })
            .catch(err => {
                channelSummary.innerHTML = '<li class="analysis-parameter-meta">Não foi possível carregar os canais. A análise usará os perfis padrão; recarregue a página para escolher os canais.</li>';
                console.warn(err);
            });
    }

    showTab('resumo');

    fetchStrategiesFromServer();
    fetchAnalysisCapabilities();
    atualizarBotoesEstrategia();

    carregarAPs(() => {
        criarGrafoOriginal();
        setEmptyOptimizedState('Selecione uma estratégia, ajuste os parâmetros e clique em Executar análise.');
    });
});
