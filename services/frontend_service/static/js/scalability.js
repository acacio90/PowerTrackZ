// Teste de escalabilidade: parametros, acompanhamento da execucao, graficos e historico. A execucao roda no
// access_point_service; esta pagina so a inicia, consulta o andamento e le os resultados salvos.
document.addEventListener('DOMContentLoaded', () => {
    const API = '/api/experiments/scalability';
    // Cor e marcador seguem a estrategia (pela ordem de registro no analysis_service), nunca a posicao no grafico.
    // Paleta categorica validada, lida dos tokens (--color-graph-series-1..8); o marcador proprio de cada serie e a
    // codificacao secundaria exigida pela validacao.
    const cssToken = (name, fallback) => getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
    const SERIES_COLORS = Array.from({ length: 8 }, (_, index) => cssToken(`--color-graph-series-${index + 1}`, '#607080'));
    const CHART_TEXT = cssToken('--color-text', '#304556');
    const CHART_TEXT_MUTED = cssToken('--color-text-muted', '#607080');
    const CHART_TEXT_STRONG = cssToken('--color-text-strong', '#18222d');
    const CHART_GRID = cssToken('--color-surface-sunken', '#eef2f5');
    const SERIES_MARKERS = ['circle', 'rectRot', 'triangle', 'rect', 'star', 'rectRounded', 'circle', 'triangle'];
    const STATUS_LABELS = {
        running: 'Em execução',
        completed: 'Concluída',
        cancelled: 'Cancelada',
        failed: 'Falhou',
        interrupted: 'Interrompida',
    };
    const STOP_LABELS = { completed: 'concluída', time_limit: 'limite de tempo', cancelled: 'cancelada' };

    const form = document.getElementById('scal-form');
    const strategiesBox = document.getElementById('scal-strategies');
    const objectiveSelect = document.getElementById('scal-objective');
    const errorBox = document.getElementById('scal-error');
    const startButton = document.getElementById('scal-start');
    const progressCard = document.getElementById('scal-progress');
    const progressFill = document.getElementById('scal-progress-fill');
    const progressText = document.getElementById('scal-progress-text');
    const cancelButton = document.getElementById('scal-cancel');
    const resultCard = document.getElementById('scal-result');
    const historyBody = document.getElementById('scal-history');
    const historyEmpty = document.getElementById('scal-history-empty');

    let strategyOrder = [];
    let displayNames = {};
    let objectiveLabels = {};
    let pollTimer = null;
    let selectedRunId = null;
    const charts = {};

    function escapeHtml(text) {
        return String(text ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
    }

    function formatNumber(value, digits = 0) {
        if (value == null || Number.isNaN(Number(value))) return '-';
        return Number(value).toLocaleString('pt-BR', { minimumFractionDigits: digits, maximumFractionDigits: digits });
    }

    function formatSeconds(value) {
        if (value == null) return '-';
        return value < 0.01 ? `${formatNumber(value * 1000, 2)} ms` : `${formatNumber(value, 2)} s`;
    }

    function strategyName(name) {
        return displayNames[name] || name.charAt(0).toUpperCase() + name.slice(1);
    }

    function strategyStyle(name) {
        const index = Math.max(0, strategyOrder.indexOf(name));
        return { color: SERIES_COLORS[index % SERIES_COLORS.length], marker: SERIES_MARKERS[index % SERIES_MARKERS.length] };
    }

    function describeVersion(version, withBranch = true) {
        if (!version || !version.commit) return 'desconhecida';
        const commit = version.commit.slice(0, 7);
        const label = version.tag ? `${version.tag} (${commit})` : commit;
        return withBranch && version.branch ? `${label}, ${version.branch}` : label;
    }

    // Eixo logaritmico: rotulos so nas potencias de 10, em unidades legiveis.
    function logTick(value) {
        const exponent = Math.log10(value);
        if (Math.abs(exponent - Math.round(exponent)) > 1e-9) return '';
        return value < 1 ? `${formatNumber(value * 1000, value < 0.001 ? 2 : 0)} ms` : `${formatNumber(value)} s`;
    }

    // Execucoes anteriores ao criterio configuravel usaram o objetivo padrao.
    function objectiveLabel(name) {
        return objectiveLabels[name || 'default'] || name || 'Padrão';
    }

    function describeParameters(parameters) {
        return `até ${parameters.max_nodes} APs, passo ${parameters.step}, grau mínimo ${parameters.min_degree}, `
            + `semente ${parameters.seed}, limite ${formatNumber(parameters.time_limit_seconds, 1)} s, ${parameters.thread_count} thread(s), `
            + `critério ${objectiveLabel(parameters.objective)}`;
    }

    function describeBreak(run, strategy) {
        const size = run.breaks[strategy.name];
        if (size != null) {
            return strategy.exact
                ? `quebra em ${size} APs (ótimo não encontrado no limite)`
                : `quebra em ${size} APs (limite de tempo excedido)`;
        }
        const tested = (run.points || []).filter(point => point.strategy === strategy.name).map(point => point.nodes);
        const largest = tested.length ? Math.max(...tested) : null;
        if (run.status === 'running') return 'em teste';
        return largest != null ? `não quebrou até ${largest} APs` : 'não executada';
    }

    function showError(message) {
        errorBox.textContent = message;
        errorBox.hidden = !message;
    }

    async function requestJson(url, options = {}) {
        const response = await fetch(url, options);
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.success === false) {
            throw new Error(data.error || `O servidor respondeu com erro (${response.status}). Tente de novo.`);
        }
        return data;
    }

    async function loadStrategies() {
        try {
            const data = await requestJson('/api/analysis/strategies');
            const details = data.strategy_details || [];
            strategyOrder = details.map(detail => detail.name);
            displayNames = { backtracking: 'Backtracking', greedy: 'Guloso', local_search: 'Busca local', simulated_annealing: 'Simulated Annealing', tabu_search: 'Busca Tabu', genetic: 'Algoritmo genético', hybrid_genetic: 'Algoritmo genético híbrido' };
            const objectives = Array.isArray(data.objectives) ? data.objectives : [];
            if (objectives.length) {
                objectiveLabels = objectives.reduce((byName, objective) => ({ ...byName, [objective.name]: objective.label }), {});
                objectiveSelect.innerHTML = objectives.map(objective => `
                    <option value="${escapeHtml(objective.name)}" title="${escapeHtml(objective.description)}">${escapeHtml(objective.label)}</option>`).join('');
                objectiveSelect.value = data.default_objective || objectives[0].name;
            }
            // As metaheuristicas ainda nao entram no teste: o ponto de quebra delas depende de repeticoes por semente.
            const implemented = details.filter(detail => detail.implemented && detail.family !== 'metaheuristic');
            strategiesBox.innerHTML = '<span class="scal-field-label">Estratégias:</span>' + implemented.map(detail => `
                <label>
                    <input type="checkbox" name="strategy" value="${escapeHtml(detail.name)}" checked>
                    ${escapeHtml(strategyName(detail.name))}
                    <span class="scal-kind">(${detail.exact ? 'exato' : 'sem garantia de ótimo'})</span>
                </label>`).join('');
        } catch (error) {
            strategiesBox.innerHTML = `<span class="scal-note">Não foi possível carregar as estratégias: ${escapeHtml(error.message)} Recarregue a página.</span>`;
        }
    }

    function readForm() {
        const integer = id => Number.parseInt(document.getElementById(id).value, 10);
        const seedText = document.getElementById('scal-seed').value.trim();
        return {
            max_nodes: integer('scal-max-nodes'),
            step: integer('scal-step'),
            min_degree: integer('scal-min-degree'),
            seed: seedText === '' ? null : Number(seedText),
            time_limit_seconds: Number(document.getElementById('scal-time-limit').value),
            thread_count: integer('scal-threads'),
            objective: objectiveSelect.value,
            strategies: [...strategiesBox.querySelectorAll('input[name="strategy"]:checked')].map(input => input.value),
        };
    }

    function validateForm(parameters) {
        if (!Number.isInteger(parameters.max_nodes) || parameters.max_nodes < 2 || parameters.max_nodes > 1000) return 'O tamanho máximo deve ser um inteiro entre 2 e 1000.';
        if (!Number.isInteger(parameters.step) || parameters.step < 1 || parameters.step > parameters.max_nodes) return 'O passo deve ser um inteiro entre 1 e o tamanho máximo.';
        if (!Number.isInteger(parameters.min_degree) || parameters.min_degree < 1 || parameters.min_degree >= parameters.max_nodes) return 'O grau mínimo deve ser um inteiro maior que 0 e menor que o tamanho máximo.';
        if (parameters.seed !== null && (!Number.isInteger(parameters.seed) || parameters.seed < 0 || parameters.seed > 4294967295)) return 'A semente deve ser um inteiro entre 0 e 4294967295 ou ficar em branco.';
        if (!(parameters.time_limit_seconds > 0 && parameters.time_limit_seconds <= 3600)) return 'O limite de tempo deve ser maior que 0 e até 3600 s.';
        if (!Number.isInteger(parameters.thread_count) || parameters.thread_count < 1 || parameters.thread_count > 256) return 'As threads devem ser um inteiro entre 1 e 256.';
        if (!parameters.strategies.length) return 'Selecione ao menos uma estratégia.';
        return null;
    }

    function setRunning(run) {
        const running = run && run.status === 'running';
        progressCard.hidden = !running;
        startButton.disabled = Boolean(running);
        if (!running) return;
        progressFill.style.width = `${Math.round((run.progress || 0) * 100)}%`;
        progressText.textContent = `Execução #${run.id}: ${Math.round((run.progress || 0) * 100)}%`
            + (run.current_step ? ` · analisando ${run.current_step}` : '');
        cancelButton.onclick = async () => {
            cancelButton.disabled = true;
            try {
                await requestJson(`${API}/${run.id}/cancel`, { method: 'POST' });
            } catch (error) {
                showError(error.message);
            } finally {
                cancelButton.disabled = false;
            }
        };
    }

    function poll(runId) {
        clearTimeout(pollTimer);
        pollTimer = setTimeout(async () => {
            try {
                const { run } = await requestJson(`${API}/${runId}`);
                setRunning(run);
                if (run.status === 'running') {
                    if (selectedRunId === runId) renderResult(run);
                    poll(runId);
                } else {
                    renderResult(run);
                    loadHistory();
                }
            } catch (error) {
                showError(error.message);
                poll(runId);
            }
        }, 1000);
    }

    form.addEventListener('submit', async event => {
        event.preventDefault();
        const parameters = readForm();
        const invalid = validateForm(parameters);
        showError(invalid);
        if (invalid) return;
        startButton.disabled = true;
        try {
            const { run } = await requestJson(API, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(parameters),
            });
            selectedRunId = run.id;
            setRunning(run);
            renderResult(run);
            loadHistory();
            poll(run.id);
        } catch (error) {
            showError(error.message);
            startButton.disabled = false;
        }
    });

    function chartDatasets(run, valueOf) {
        return (run.strategies || []).map(strategy => {
            const style = strategyStyle(strategy.name);
            const points = (run.points || []).filter(point => point.strategy === strategy.name);
            return {
                label: strategyName(strategy.name),
                data: points.map(point => ({ x: point.nodes, y: valueOf(point), point })),
                borderColor: style.color,
                backgroundColor: style.color,
                borderWidth: 2,
                pointStyle: points.map(point => (point.broke ? 'crossRot' : style.marker)),
                pointRadius: points.map(point => (point.broke ? 9 : 4)),
                pointBorderWidth: points.map(point => (point.broke ? 3 : 1)),
                pointHoverRadius: 7,
                tension: 0,
            };
        });
    }

    function renderChart(key, canvasId, datasets, yScale, tooltipLabel) {
        if (charts[key]) charts[key].destroy();
        charts[key] = new Chart(document.getElementById(canvasId), {
            type: 'line',
            data: { datasets },
            options: {
                maintainAspectRatio: false,
                animation: false,
                interaction: { mode: 'nearest', axis: 'x', intersect: false },
                scales: {
                    x: {
                        type: 'linear',
                        title: { display: true, text: 'Número de APs', color: CHART_TEXT },
                        grid: { color: CHART_GRID },
                        ticks: { color: CHART_TEXT_MUTED },
                    },
                    y: {
                        ...yScale,
                        // No eixo log, grade so nas potencias de 10, que sao as marcas rotuladas.
                        grid: { color: context => (yScale.type === 'logarithmic' && !logTick(context.tick?.value) ? 'transparent' : CHART_GRID) },
                        ticks: { ...(yScale.ticks || {}), color: CHART_TEXT_MUTED },
                    },
                },
                plugins: {
                    legend: { position: 'bottom', labels: { usePointStyle: true, color: CHART_TEXT_STRONG } },
                    tooltip: {
                        callbacks: {
                            title: items => `${items[0].parsed.x} APs`,
                            label: context => tooltipLabel(context),
                        },
                    },
                },
            },
        });
    }

    function renderResult(run) {
        selectedRunId = run.id;
        resultCard.hidden = false;
        document.getElementById('scal-result-title').textContent = `Execução #${run.id}`;
        const created = run.created_at ? new Date(run.created_at).toLocaleString('pt-BR') : '-';
        document.getElementById('scal-result-meta').innerHTML = `
            <span><strong>Situação:</strong> ${escapeHtml(STATUS_LABELS[run.status] || run.status)}${run.error ? ` (${escapeHtml(run.error)})` : ''}</span>
            <span><strong>Data:</strong> ${escapeHtml(created)}</span>
            <span><strong>Versão:</strong> ${escapeHtml(describeVersion(run.version))}</span>
            <span><strong>Parâmetros:</strong> ${escapeHtml(describeParameters(run.parameters))}</span>
            <span class="scal-row-actions"><a class="btn btn-ghost btn-sm" href="${API}/${run.id}/export?format=csv">CSV</a><a class="btn btn-ghost btn-sm" href="${API}/${run.id}/export?format=json">JSON</a></span>`;
        document.getElementById('scal-result-breaks').innerHTML = (run.strategies || []).map(strategy => `
            <span class="tag tag-outline scal-break">
                <span class="scal-swatch" style="background:${strategyStyle(strategy.name).color}"></span>
                <strong>${escapeHtml(strategyName(strategy.name))}</strong> ${escapeHtml(describeBreak(run, strategy))}
            </span>`).join('');

        const limit = run.parameters.time_limit_seconds;
        const sizes = (run.points || []).map(point => point.nodes);
        const timeDatasets = chartDatasets(run, point => Math.max(point.duration_seconds, 1e-5));
        if (sizes.length) {
            timeDatasets.push({
                label: 'Limite de tempo',
                data: [{ x: Math.min(...sizes), y: limit }, { x: Math.max(...sizes), y: limit }],
                borderColor: CHART_TEXT_MUTED,
                borderDash: [6, 4],
                borderWidth: 1.5,
                pointRadius: 0,
                pointHoverRadius: 0,
            });
        }
        renderChart('time', 'scal-chart-time', timeDatasets, {
            type: 'logarithmic',
            title: { display: true, text: 'Tempo (escala log)', color: CHART_TEXT },
            ticks: { callback: logTick, autoSkip: false },
        }, context => {
            const point = context.raw.point;
            if (!point) return `Limite de tempo: ${formatNumber(limit, 1)} s`;
            return `${context.dataset.label}: ${formatSeconds(point.duration_seconds)}${point.broke ? ' (ponto de quebra)' : ''}`;
        });
        renderChart('conflicts', 'scal-chart-conflicts', chartDatasets(run, point => point.conflicts), {
            beginAtZero: true,
            title: { display: true, text: 'Conflitos', color: CHART_TEXT },
        }, context => {
            const point = context.raw.point;
            const gap = point.gap_conflicts != null ? `, ${point.gap_conflicts >= 0 ? '+' : ''}${point.gap_conflicts} do ótimo` : '';
            return `${context.dataset.label}: ${formatNumber(point.conflicts)} conflitos${point.optimal ? ' (ótimo)' : gap}`;
        });

        document.getElementById('scal-points').innerHTML = (run.points || []).map(point => `
            <tr class="${point.broke ? 'is-broken' : ''}">
                <td>${point.nodes}</td>
                <td>${formatNumber(point.edges)}</td>
                <td>${formatNumber(point.density, 3)}</td>
                <td>${escapeHtml(strategyName(point.strategy))}${point.broke ? ' · quebra' : ''}</td>
                <td>${formatSeconds(point.duration_seconds)}</td>
                <td>${formatNumber(point.conflicts)}${point.optimal ? ' (ótimo)' : ''}</td>
                <td>${point.gap_conflicts != null ? formatNumber(point.gap_conflicts) : '-'}</td>
                <td>${formatNumber(point.interference, 1)}</td>
                <td>${formatNumber(point.power_w, 1)}</td>
                <td>${formatNumber(point.nodes_explored)}</td>
                <td>${escapeHtml(STOP_LABELS[point.stop_reason] || point.stop_reason)}</td>
            </tr>`).join('');
        highlightSelected();
    }

    function highlightSelected() {
        historyBody.querySelectorAll('tr').forEach(row => row.classList.toggle('is-selected', Number(row.dataset.id) === selectedRunId));
    }

    async function loadHistory() {
        try {
            const { runs } = await requestJson(API);
            historyEmpty.hidden = runs.length > 0;
            historyBody.innerHTML = runs.map(run => `
                <tr data-id="${run.id}">
                    <td>${run.id}</td>
                    <td>${escapeHtml(run.created_at ? new Date(run.created_at).toLocaleString('pt-BR') : '-')}</td>
                    <td title="${escapeHtml(describeVersion(run.version))}">${escapeHtml(describeVersion(run.version, false))}</td>
                    <td class="scal-params">${escapeHtml(describeParameters(run.parameters))}</td>
                    <td class="scal-status">${escapeHtml(STATUS_LABELS[run.status] || run.status)}</td>
                    <td>${(run.strategies || []).map(strategy => `${escapeHtml(strategyName(strategy.name))}: ${run.breaks[strategy.name] != null ? `${run.breaks[strategy.name]} APs` : '—'}`).join('<br>')}</td>
                    <td><div class="scal-row-actions">
                        <button type="button" class="btn btn-ghost btn-sm" data-action="view">Ver</button>
                        <a class="btn btn-ghost btn-sm" href="${API}/${run.id}/export?format=csv">CSV</a>
                        <a class="btn btn-ghost btn-sm" href="${API}/${run.id}/export?format=json">JSON</a>
                        ${run.status === 'running' ? '' : '<button type="button" class="btn btn-danger btn-sm" data-action="delete">Excluir</button>'}
                    </div></td>
                </tr>`).join('');
            highlightSelected();
            const running = runs.find(run => run.status === 'running');
            if (running && !pollTimer) {
                setRunning(running);
                poll(running.id);
            }
        } catch (error) {
            showError(error.message);
        }
    }

    historyBody.addEventListener('click', async event => {
        const button = event.target.closest('button[data-action]');
        if (!button) return;
        const runId = Number(button.closest('tr').dataset.id);
        try {
            if (button.dataset.action === 'view') {
                const { run } = await requestJson(`${API}/${runId}`);
                renderResult(run);
                resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else if (button.dataset.action === 'delete' && window.confirm(`Excluir a execução #${runId}?`)) {
                await requestJson(`${API}/${runId}`, { method: 'DELETE' });
                if (selectedRunId === runId) {
                    resultCard.hidden = true;
                    selectedRunId = null;
                }
                loadHistory();
            }
        } catch (error) {
            showError(error.message);
        }
    });

    loadStrategies().then(loadHistory);
});
