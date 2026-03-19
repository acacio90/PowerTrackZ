window.addEventListener('DOMContentLoaded', function() {
    window.selectedStrategy = 'backtracking';

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
    `;
    document.head.appendChild(style);

    let apsOriginais = [];
    let apsOtimizado = [];
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
    const tabelaContainer = document.createElement('div');
    tabelaContainer.id = 'tabela-alteracoes-container';
    tabelaContainer.style.margin = '30px 0 0 0';

    if (existingGraphContainer) {
        existingGraphContainer.appendChild(grafoContainer1);
        existingGraphContainer.appendChild(grafoContainer2);
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

        container.appendChild(cyDiv);
        container.appendChild(legenda);
        return container;
    }

    function getLegendaDiv(containerId) {
        return document.getElementById(containerId).parentNode.querySelector('.legenda');
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
                    Frequência: ${frequency || 'N/A'}
                </div>
            `;
            legendaDiv.appendChild(legendaItem);
        });
    }

    function renderizarCytoscape(containerId, graphData) {
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

        cytoscape({
            container: document.getElementById(containerId),
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
                    <th>Configura\u00e7\u00e3o Original</th>
                    <th>Configura\u00e7\u00e3o Proposta</th>
                    <th>A\u00e7\u00f5es</th>
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
        const nomeEstrategia = {
            backtracking: 'Backtracking',
            greedy: 'Greedy',
            genetic: 'Genetic (AG)'
        }[estrategiaNome] || 'Backtracking';

        titulo.className = 'app-table-title analysis-changes-title';
        titulo.textContent = `Altera\u00e7\u00f5es de Configura\u00e7\u00e3o Propostas pelo ${nomeEstrategia}`;
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
            ? '<span class="analysis-change-icon" title="Configura\u00e7\u00e3o alterada">&#8635;</span>'
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

    function criarAnaliseOtimizada() {
        fetch((window.ANALYSIS_API && window.ANALYSIS_API.analyzeGraph) || '/api/analysis/analyze-graph', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(montarPayloadAnalise(apsOtimizado))
        })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    throw new Error(data.error || 'Falha na análise');
                }

                const graphData = data.graph_data || { nodes: [], links: [] };
                renderizarCytoscape('cy2', graphData);
                renderizarLegenda(getLegendaDiv('cy2'), graphData.nodes, true);
                atualizarInfoConsumo('cy2', graphData.nodes, true);
                exibirTabelaAlteracoes(graphData.nodes, data.strategy_used);
            })
            .catch(error => {
                document.getElementById('cy2').innerHTML = '<p style="color:red">Erro ao carregar a análise.</p>';
                console.error('Erro ao carregar análise otimizada:', error);
            });
    }

    const strategyInfo = document.getElementById('strategyInfo');
    async function fetchStrategiesFromServer() {
        try {
            const res = await fetch((window.ANALYSIS_API && window.ANALYSIS_API.strategies) || '/api/analysis/strategies');
            if (!res.ok) return;

            const data = await res.json();
            if (data && data.success && data.strategies && strategyInfo) {
                strategyInfo.textContent = 'Estratégias: ' + Object.keys(data.strategies).join(', ');
            }
        } catch (error) {
            console.warn('Não foi possível obter estratégias do servidor:', error);
        }
    }

    document.querySelectorAll('.btn-server-analysis').forEach(btn => {
        btn.addEventListener('click', () => {
            window.selectedStrategy = btn.getAttribute('data-strategy');
            atualizarBotoesEstrategia();
            criarAnaliseOtimizada();
        });
    });

    fetchStrategiesFromServer();
    atualizarBotoesEstrategia();

    carregarAPs(() => {
        criarGrafoOriginal();
        criarAnaliseOtimizada();
    });
});
