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
    const STOP_LABELS = {
        completed: 'concluída',
        time_limit: 'limite de tempo',
        cancelled: 'cancelada',
        iteration_limit: 'limite de iterações',
        no_improvement: 'sem melhora',
        min_temperature: 'temperatura mínima',
    };
    // A semente, o limite de tempo e as threads sao do teste (iguais para todas as estrategias); o resto e de cada uma.
    const SHARED_PARAMETERS = new Set(['seed', 'time_limit_seconds', 'thread_count']);

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
    let strategyDetails = {};
    let channelSelector = null;
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
        const own = Object.entries(parameters.strategy_parameters || {})
            .filter(([, values]) => Object.keys(values).length)
            .map(([name, values]) => `${strategyName(name)}: ${Object.entries(values).map(([key, value]) => `${key} ${value}`).join(', ')}`);
        return `até ${parameters.max_nodes} APs, passo ${parameters.step}, grau mínimo ${parameters.min_degree}, `
            + `semente ${parameters.seed}, limite ${formatNumber(parameters.time_limit_seconds, 1)} s, ${parameters.thread_count} thread(s), `
            + `critério ${objectiveLabel(parameters.objective)}`
            + `${parameters.repetitions > 1 ? `, ${parameters.repetitions} repetições` : ''}`
            + `${parameters.channels && parameters.channels !== 'padrao' ? ', canais escolhidos' : ''}`
            + `${own.length ? `; ${own.join('; ')}` : ''}`;
    }

    function describeBreak(run, strategy) {
        const size = run.breaks[strategy.name];
        if (size != null) {
            if (strategy.exact) return `quebra em ${size} APs (ótimo não encontrado no limite)`;
            return strategy.stochastic
                ? `quebra em ${size} APs (maioria das repetições no limite de tempo)`
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
            strategyDetails = details.reduce((byName, detail) => ({ ...byName, [detail.name]: detail }), {});
            const implemented = details.filter(detail => detail.implemented);
            // Exatas e construtivas vem marcadas; as metaheuristicas, repetidas por semente, sao escolhidas pelo usuario.
            strategiesBox.innerHTML = '<span class="scal-field-label">Estratégias:</span>' + implemented.map(detail => {
                const own = (detail.parameters || []).filter(parameter => !SHARED_PARAMETERS.has(parameter.name));
                const stochastic = (detail.parameters || []).some(parameter => parameter.name === 'seed');
                return `
                <div class="scal-strategy">
                    <label>
                        <input type="checkbox" name="strategy" value="${escapeHtml(detail.name)}" ${detail.family === 'metaheuristic' ? '' : 'checked'}>
                        ${escapeHtml(strategyName(detail.name))}
                        <span class="scal-kind">(${detail.exact ? 'exato' : stochastic ? 'estocástica' : 'sem garantia de ótimo'})</span>
                    </label>
                    ${own.length ? `
                    <details class="scal-strategy-params">
                        <summary>Parâmetros</summary>
                        <div class="scal-param-grid">${own.map(parameter => renderParameter(detail.name, parameter)).join('')}</div>
                    </details>` : ''}
                </div>`;
            }).join('');
        } catch (error) {
            strategiesBox.innerHTML = `<span class="scal-note">Não foi possível carregar as estratégias: ${escapeHtml(error.message)} Recarregue a página.</span>`;
        }
    }

    function parameterId(strategy, name) {
        return `scal-param-${strategy}-${name}`;
    }

    // Campo de um parametro da estrategia, a partir da descricao de /strategies; o padrao vem preenchido.
    function renderParameter(strategy, parameter) {
        const id = parameterId(strategy, parameter.name);
        const unit = parameter.unit ? ` (${escapeHtml(parameter.unit)})` : '';
        const hint = `${parameter.description || ''}${parameter.zero_disables ? ' 0 desativa.' : ''}`;
        if (parameter.type === 'choice') {
            return `<div><label for="${id}" title="${escapeHtml(hint)}">${escapeHtml(parameter.label)}</label>
                <select id="${id}" data-strategy="${escapeHtml(strategy)}" data-parameter="${escapeHtml(parameter.name)}">
                ${(parameter.options || []).map(option => `<option value="${escapeHtml(option.value)}" ${option.value === parameter.default ? 'selected' : ''}>${escapeHtml(option.label)}</option>`).join('')}
                </select></div>`;
        }
        const value = parameter.default == null ? '' : parameter.default;
        return `<div><label for="${id}" title="${escapeHtml(hint)}">${escapeHtml(parameter.label)}${unit}</label>
            <input type="number" id="${id}" data-strategy="${escapeHtml(strategy)}" data-parameter="${escapeHtml(parameter.name)}"
                   min="${parameter.min}" max="${parameter.max}" step="${parameter.type === 'integer' ? '1' : 'any'}" value="${value}"
                   placeholder="${escapeHtml(parameter.optional_label || '')}"></div>`;
    }

    // Parametros proprios das estrategias marcadas; so os que diferem do padrao vao na requisicao.
    function readStrategyParameters(strategies) {
        const result = {};
        const errors = [];
        strategies.forEach(name => {
            const values = {};
            (strategyDetails[name]?.parameters || []).filter(parameter => !SHARED_PARAMETERS.has(parameter.name)).forEach(parameter => {
                const field = document.getElementById(parameterId(name, parameter.name));
                if (!field) return;
                if (parameter.type === 'choice') {
                    if (field.value !== parameter.default) values[parameter.name] = field.value;
                    return;
                }
                const raw = field.value.trim().replace(',', '.');
                if (raw === '') return;
                const value = Number(raw);
                if (!Number.isFinite(value) || (parameter.type === 'integer' && !Number.isInteger(value))
                    || value < parameter.min || value > parameter.max) {
                    errors.push(`${strategyName(name)}, ${parameter.label}: informe um valor entre ${parameter.min} e ${parameter.max}.`);
                    return;
                }
                if (value !== parameter.default) values[parameter.name] = value;
            });
            if (Object.keys(values).length) result[name] = values;
        });
        return { result, error: errors[0] || null };
    }

    function channelsChosen() {
        if (!channelSelector) return null;
        return channelSelector.resumo().every(band => band.padrao) ? null : channelSelector.selecao();
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
            repetitions: integer('scal-repetitions'),
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
        if (!Number.isInteger(parameters.repetitions) || parameters.repetitions < 1 || parameters.repetitions > 100) return 'As repetições devem ser um inteiro entre 1 e 100.';
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
        const own = readStrategyParameters(parameters.strategies);
        const channelError = channelSelector ? channelSelector.validar() : null;
        const invalid = validateForm(parameters) || own.error || channelError;
        showError(invalid);
        if (invalid) return;
        parameters.strategy_parameters = own.result;
        const channels = channelsChosen();
        if (channels) parameters.channels = channels;
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

    // Uma serie por estrategia, pela media de cada tamanho (nas deterministicas, o proprio valor); nas estocasticas,
    // uma faixa sombreada do pior ao melhor valor das repeticoes mostra a dispersao.
    function summariesOf(run, strategy) {
        if (Array.isArray(run.summaries) && run.summaries.length) {
            return run.summaries.filter(summary => summary.strategy === strategy).sort((a, b) => a.nodes - b.nodes);
        }
        // Execucoes antigas, sem resumo: um ponto por tamanho.
        return (run.points || []).filter(point => point.strategy === strategy).map(point => ({
            nodes: point.nodes, strategy, repetitions: 1, broke: point.broke,
            duration_seconds: { mean: point.duration_seconds, std: 0, min: point.duration_seconds, max: point.duration_seconds },
            conflicts: { mean: point.conflicts, std: 0, min: point.conflicts, max: point.conflicts },
        }));
    }

    // Cor da serie com transparencia, para a faixa de dispersao (as cores dos tokens sao hexadecimais).
    function withAlpha(color, alpha) {
        const hex = String(color).trim().replace('#', '');
        if (!/^[0-9a-f]{6}$/i.test(hex)) return color;
        const [r, g, b] = [0, 2, 4].map(index => parseInt(hex.slice(index, index + 2), 16));
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }

    function chartDatasets(run, field, transform = value => value) {
        const datasets = [];
        (run.strategies || []).forEach(strategy => {
            const style = strategyStyle(strategy.name);
            const summaries = summariesOf(run, strategy.name).filter(summary => summary[field] && summary[field].mean != null);
            datasets.push({
                label: strategyName(strategy.name),
                data: summaries.map(summary => ({ x: summary.nodes, y: transform(summary[field].mean), summary })),
                borderColor: style.color,
                backgroundColor: style.color,
                borderWidth: 2,
                pointStyle: summaries.map(summary => (summary.broke ? 'crossRot' : style.marker)),
                pointRadius: summaries.map(summary => (summary.broke ? 9 : 4)),
                pointBorderWidth: summaries.map(summary => (summary.broke ? 3 : 1)),
                pointHoverRadius: 7,
                tension: 0,
            });
            if (summaries.some(summary => summary.repetitions > 1)) {
                const band = {
                    borderWidth: 0,
                    pointRadius: 0,
                    pointHoverRadius: 0,
                    tension: 0,
                    spread: true,
                    backgroundColor: withAlpha(style.color, 0.18),
                };
                datasets.push({ ...band, label: `${strategyName(strategy.name)} (pior)`, data: summaries.map(summary => ({ x: summary.nodes, y: transform(summary[field].max) })), fill: false });
                datasets.push({ ...band, label: `${strategyName(strategy.name)} (melhor)`, data: summaries.map(summary => ({ x: summary.nodes, y: transform(summary[field].min) })), fill: '-1' });
            }
        });
        return datasets;
    }

    function describeSummary(summary, field, format) {
        const value = summary[field];
        if (!value || value.mean == null) return '-';
        if (summary.repetitions <= 1) return format(value.mean);
        return `${format(value.mean)} ± ${format(value.std)} (melhor ${format(value.min)}, pior ${format(value.max)})`;
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
                    legend: {
                        position: 'bottom',
                        labels: { usePointStyle: true, color: CHART_TEXT_STRONG, filter: item => !datasets[item.datasetIndex].spread },
                    },
                    tooltip: {
                        filter: item => !item.dataset.spread,
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
        const timeDatasets = chartDatasets(run, 'duration_seconds', value => Math.max(value, 1e-5));
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
            const summary = context.raw.summary;
            if (!summary) return `Limite de tempo: ${formatNumber(limit, 1)} s`;
            return `${context.dataset.label}: ${describeSummary(summary, 'duration_seconds', formatSeconds)}${summary.broke ? ' (ponto de quebra)' : ''}`;
        });
        renderChart('conflicts', 'scal-chart-conflicts', chartDatasets(run, 'conflicts'), {
            beginAtZero: true,
            title: { display: true, text: 'Conflitos', color: CHART_TEXT },
        }, context => {
            const summary = context.raw.summary;
            const point = (run.points || []).find(item => item.strategy === summary.strategy && item.nodes === summary.nodes) || {};
            const gap = summary.repetitions <= 1 && point.gap_conflicts != null ? `, ${point.gap_conflicts >= 0 ? '+' : ''}${point.gap_conflicts} do ótimo` : '';
            return `${context.dataset.label}: ${describeSummary(summary, 'conflicts', value => formatNumber(value, summary.repetitions > 1 ? 1 : 0))} conflitos${point.optimal ? ' (ótimo)' : gap}`;
        });

        // Uma linha por tamanho e estrategia; nas estocasticas, a media ± o desvio-padrao das repeticoes.
        const rows = [];
        (run.strategies || []).forEach(strategy => summariesOf(run, strategy.name).forEach(summary => rows.push(summary)));
        rows.sort((a, b) => a.nodes - b.nodes || strategyOrder.indexOf(a.strategy) - strategyOrder.indexOf(b.strategy));
        const spread = (summary, field, digits, format) => {
            const value = summary[field];
            if (!value || value.mean == null) return '-';
            const main = format ? format(value.mean) : formatNumber(value.mean, summary.repetitions > 1 ? Math.max(digits, 1) : digits);
            return summary.repetitions > 1
                ? `${main} <span class="scal-spread">± ${format ? format(value.std) : formatNumber(value.std, Math.max(digits, 1))}</span>`
                : main;
        };
        document.getElementById('scal-points').innerHTML = rows.map(summary => {
            const points = (run.points || []).filter(point => point.strategy === summary.strategy && point.nodes === summary.nodes);
            const first = points[0] || {};
            const stops = points.reduce((counts, point) => ({ ...counts, [point.stop_reason]: (counts[point.stop_reason] || 0) + 1 }), {});
            const stopText = Object.entries(stops)
                .map(([reason, count]) => `${points.length > 1 ? `${count}× ` : ''}${STOP_LABELS[reason] || reason}`).join(', ');
            const mean = field => {
                const values = points.map(point => point[field]).filter(value => value != null);
                return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
            };
            return `
            <tr class="${summary.broke ? 'is-broken' : ''}">
                <td>${summary.nodes}</td>
                <td>${formatNumber(first.edges)}</td>
                <td>${formatNumber(first.density, 3)}</td>
                <td>${escapeHtml(strategyName(summary.strategy))}${summary.broke ? ' · quebra' : ''}</td>
                <td>${summary.repetitions}</td>
                <td>${spread(summary, 'duration_seconds', 2, formatSeconds)}</td>
                <td>${spread(summary, 'conflicts', 0)}${first.optimal ? ' (ótimo)' : ''}</td>
                <td>${summary.repetitions <= 1 && first.gap_conflicts != null ? formatNumber(first.gap_conflicts) : '-'}</td>
                <td>${spread(summary, 'interference', 1)}</td>
                <td>${spread(summary, 'power_w', 1)}</td>
                <td>${formatNumber(mean('nodes_explored'))}</td>
                <td>${spread(summary, 'processing_energy_j', 2)}</td>
                <td>${escapeHtml(stopText)}</td>
            </tr>`;
        }).join('');
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

    // Canais: o mesmo seletor da pagina de Analise, num modal; sem mudancas, o teste usa os perfis padrao.
    const spectrumModal = document.getElementById('scal-spectrum-modal');
    const openSpectrum = document.getElementById('scal-open-spectrum');
    const channelsSummary = document.getElementById('scal-channels-summary');

    function renderChannelsSummary() {
        if (!channelSelector) return;
        const bands = channelSelector.resumo().filter(band => band.k > 0);
        const custom = bands.some(band => !band.padrao) || channelSelector.resumo().some(band => !band.padrao);
        channelsSummary.textContent = `${custom ? 'Personalizados' : 'Perfis padrão'}: ${bands.map(band => `${band.rotulo} k = ${band.k}`).join(' · ')}`;
    }

    function setSpectrumModal(open) {
        spectrumModal.style.display = open ? 'flex' : 'none';
        (open ? document.getElementById('scal-spectrum-done') : openSpectrum).focus();
        if (!open) renderChannelsSummary();
    }

    openSpectrum.addEventListener('click', () => setSpectrumModal(true));
    document.getElementById('scal-spectrum-close').addEventListener('click', () => setSpectrumModal(false));
    document.getElementById('scal-spectrum-done').addEventListener('click', () => setSpectrumModal(false));
    spectrumModal.addEventListener('click', event => {
        if (event.target === spectrumModal) setSpectrumModal(false);
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && spectrumModal.style.display === 'flex') setSpectrumModal(false);
    });
    if (window.ChannelPlan) {
        const container = document.getElementById('scal-channels');
        window.ChannelPlan.carregar()
            .then(plan => {
                channelSelector = window.ChannelPlan.criarSeletor(container, plan);
                container.addEventListener('channelplan:change', renderChannelsSummary);
                renderChannelsSummary();
                openSpectrum.disabled = false;
            })
            .catch(() => {
                channelsSummary.textContent = 'Perfis padrão (não foi possível carregar o mapa do espectro; recarregue a página para escolher os canais).';
            });
    }

    loadStrategies().then(loadHistory);
});
