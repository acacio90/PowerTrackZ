window.addEventListener('DOMContentLoaded', function() {
    // Variável global para armazenar a estratégia selecionada
    window.selectedStrategy = 'backtracking'; // padrão

    // Estilos CSS para layout e componentes visuais
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
            padding: 10px;
            background-color: #fff;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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
            width: 200px;
            padding: 15px;
            background: rgba(245, 245, 245, 0.95);
            border: 1px solid #ddd;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            max-height: calc(100% - 40px);
            overflow-y: auto;
            z-index: 1000;
            margin: 0;
            float: none;
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
        }
        .nome-ap {
            font-size: 14px;
            color: #666;
        }
        .grafo-container + .grafo-container {
            margin-top: 32px;
        }
        .grafo-container {
            position: relative;
            padding: 16px 10px 32px;
        }
        .campo-consumo {
            position: static;
            margin: 24px 0 0;
            padding: 18px 12px 12px;
            background: #f0f8ff;
            border: 2px solid #b3d1ff;
            border-radius: 8px;
            text-align: center;
            color: #1a237e;
            box-shadow: 0 2px 5px rgba(0,0,0,0.04);
        }
        .campo-consumo input[type='number'] {
            margin-bottom: 12px;
        }
        .campo-consumo br {
            margin-bottom: 10px;
            display: block;
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
            z-index: 1100;
            padding: 0;
            margin: 0;
        }
    `;
    document.head.appendChild(style);

    // Verifica se já existe um container de grafos
    let existingGraphContainer = document.querySelector('.content-container');
    let pageContainer = document.querySelector('.page-container');
    
    if (!existingGraphContainer) {
        // Cria containers apenas se não existirem
        pageContainer = document.createElement('div');
        pageContainer.className = 'page-container';
        const contentContainer = document.createElement('div');
        contentContainer.className = 'content-container';
        
        // Encontra onde inserir os containers (após os botões de estratégia)
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

    defineLegendaDivs();

    function defineLegendaDivs() {
        window.legendaDiv1 = grafoContainer1.querySelector('.legenda');
        window.legendaDiv2 = grafoContainer2.querySelector('.legenda');
    }

    if (existingGraphContainer) {
        existingGraphContainer.appendChild(grafoContainer1);
        existingGraphContainer.appendChild(grafoContainer2);
    }

    const tabelaContainer = document.createElement('div');
    tabelaContainer.id = 'tabela-alteracoes-container';
    tabelaContainer.style.margin = '30px 0 0 0';
    if (pageContainer) {
        pageContainer.appendChild(tabelaContainer);
    }


    const coresPorConfiguracao = new Map();

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

    function gerarChaveConfiguracao(ap) {
        return `${ap.channel || 'N/A'}-${ap.bandwidth || 'N/A'}-${ap.frequency}`;
    }

    function gerarCorAleatoria() {
        return '#' + Math.floor(Math.random()*16777215).toString(16);
    }

    function obterCorConfiguracao(config) {
        if (!coresPorConfiguracao.has(config)) {
            coresPorConfiguracao.set(config, gerarCorAleatoria());
        }
        return coresPorConfiguracao.get(config);
    }

    function podeAtribuirConfiguracao(grafo, no, config, configuracoes) {
        const vizinhos = grafo.get(no) || new Set();
        return ![...vizinhos].some(v => configuracoes[v] === config);
    }

    function gerarConfigsPossiveis(aps) {
        const bandasPorFreq = {
            '2.4': ['40', '20'],
            '5': ['80', '40', '20'],
            '6': ['80', '40', '20']
        };
        const configs = new Set();
        aps.forEach(ap => {
            let freq = String(ap.frequency).replace(',', '.');
            let freqBase = freq.startsWith('2.4') ? '2.4' : freq.startsWith('5') ? '5' : freq.startsWith('6') ? '6' : null;
            if (freqBase && bandasPorFreq[freqBase]) {
                bandasPorFreq[freqBase].forEach(bw => {
                    configs.add(`${ap.channel || 'N/A'}-${bw}-${ap.frequency}`);
                });
            } else {
                configs.add(`${ap.channel || 'N/A'}-${ap.bandwidth || 'N/A'}-${ap.frequency}`);
            }
        });
        return Array.from(configs);
    }

    // Algoritmo de coloração gulosa
    function colorirGulosoPrioritario(grafo, nos, configsDisponiveis, aps, data) {
        const arestasOrdenadas = [...(data.links || [])].sort((a, b) => b.peso - a.peso);
        const configuracoes = {};
        nos.forEach(no => {
            const ap = aps.find(ap => ap.id === no);
            if (ap && ap.locked) {
                configuracoes[no] = `${ap.channel}-${ap.bandwidth}-${ap.frequency}`;
            } else {
                configuracoes[no] = null;
            }
        });
        for (const no of nos) {
            const ap = aps.find(ap => ap.id === no);
            if (ap && ap.locked) continue;
            let freq = ap ? String(ap.frequency).replace(',', '.') : null;
            let configsPossiveis = configsDisponiveis;
            if (freq) {
                configsPossiveis = configsDisponiveis.filter(cfg => {
                    const freqCfg = (cfg.split('-')[2] || '').trim().replace(',', '.');
                    return freqCfg === freq;
                });
            }
            configsPossiveis.sort((a, b) => parseInt((b.split('-')[1]||'').replace(/[^0-9]/g,'')) - parseInt((a.split('-')[1]||'').replace(/[^0-9]/g,'')));
            let melhorConfig = configsPossiveis[0];
            let menorConflito = Infinity;
            for (const config of configsPossiveis) {
                let conflito = 0;
                const vizinhos = grafo.get(no) || new Set();
                for (const vizinho of vizinhos) {
                    if (configuracoes[vizinho] === config) {
                        const aresta = arestasOrdenadas.find(a => (a.source === no && a.target === vizinho) || (a.source === vizinho && a.target === no));
                        conflito += aresta ? aresta.peso : 1;
                    }
                }
                if (conflito < menorConflito || (conflito === menorConflito && config === configsPossiveis[0])) {
                    menorConflito = conflito;
                    melhorConfig = config;
                }
            }
            configuracoes[no] = melhorConfig || configsDisponiveis[0];
        }
        return configuracoes;
    }

    // Cálculo de consumo de energia
    function consumoEnergia25Mbps(bandwidth, frequency) {
        const bw = String(bandwidth).replace(/[^0-9]/g, '');
        const freq = String(frequency).replace(',', '.');
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

    let apsOriginais = [];
    let apsOtimizado = [];

    // Carrega APs do backend
    function carregarAPs(callback) {
        fetch(window.ACCESS_POINT_URL)
            .then(response => response.json())
            .then(points => {
                function getRaio(frequency) {
                    if (!frequency) return 10;
                    const freq = String(frequency).replace(',', '.');
                    if (freq.startsWith('2.4')) return 20;
                    if (freq.startsWith('5')) return 15;
                    if (freq.startsWith('6')) return 12;
                    return 10;
                }
                const aps = (points || [])
                    .filter(p => p.latitude != null && p.longitude != null)
                    .map(p => ({
                        id: p.id || p.name,
                        x: p.latitude,
                        y: p.longitude,
                        raio: getRaio(p.frequency),
                        label: p.name,
                        channel: p.channel,
                        bandwidth: p.bandwidth,
                        frequency: p.frequency
                    }));
                apsOriginais = aps.map(ap => ({ ...ap }));
                apsOtimizado = aps.map(ap => ({ ...ap }));
                if (callback) callback();
            });
    }

    // Renderiza grafo de colisão
    function criarGrafo(containerId, legendaDiv, usarBacktracking = false, callbackConfiguracoes = null, apsCustom = null) {
        const aps = apsCustom || (usarBacktracking ? apsOtimizado : apsOriginais);
        // Identifica configurações únicas
        const configuracoesUnicas = new Set();
        aps.forEach(ap => {
            const config = gerarChaveConfiguracao(ap);
            if (config !== 'N/A-N/A-N/A') {
                configuracoesUnicas.add(config);
            }
        });
        // Inicializa cores
        configuracoesUnicas.forEach(config => {
            obterCorConfiguracao(config);
        });
        const payload = { aps };
        const backendUrl = window.BACKEND_URL || 'http://localhost:5002/collision-graph';
        fetch(backendUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        })
        .then(response => response.json())
        .then(data => {
            console.log('Dados do grafo:', data);

            // Constrói grafo
            const grafo = new Map();
            data.nodes.forEach(node => {
                grafo.set(node.id, new Set());
            });
            data.links.forEach(link => {
                grafo.get(link.source).add(link.target);
                grafo.get(link.target).add(link.source);
            });

            const elements = [];
            let configuracoesDistribuidas = null;
            if (usarBacktracking) {
                // Aplica algoritmo guloso
                const nos = data.nodes.map(node => node.id);
                const configsDisponiveis = gerarConfigsPossiveis(aps);
                configuracoesDistribuidas = colorirGulosoPrioritario(grafo, nos, configsDisponiveis, aps, data);
                // Cria elementos
                data.nodes.forEach(node => {
                    const config = configuracoesDistribuidas[node.id];
                    elements.push({ 
                        data: { 
                            id: node.id, 
                            label: node.label || node.id,
                            cor: obterCorConfiguracao(config)
                        } 
                    });
                });
            } else {
                // Usa configs originais
                data.nodes.forEach(node => {
                    const ap = aps.find(ap => ap.id === node.id);
                    const config = ap ? gerarChaveConfiguracao(ap) : 'N/A-N/A-N/A';
                    elements.push({ 
                        data: { 
                            id: node.id, 
                            label: node.label || node.id,
                            cor: obterCorConfiguracao(config) || '#CCCCCC'
                        } 
                    });
                });
            }

            data.links.forEach(link => {
                elements.push({ data: { source: link.source, target: link.target, peso: link.peso } });
            });

            // Atualiza legenda
            legendaDiv.innerHTML = '';
            if (usarBacktracking) {
                // Mostra configs em uso
                const configuracoesUtilizadas = new Set();
                data.nodes.forEach(node => {
                    const cor = elements.find(e => e.data.id === node.id)?.data.cor;
                    const config = Array.from(coresPorConfiguracao.entries()).find(([, v]) => v === cor)?.[0];
                    if (config && config !== 'N/A-N/A-N/A') {
                        configuracoesUtilizadas.add(config);
                    }
                });
                configuracoesUtilizadas.forEach(config => {
                    const [channel, bandwidth, frequency] = config.split('-');
                    const legendaItem = document.createElement('div');
                    legendaItem.className = 'legenda-item';
                    legendaItem.innerHTML = `
                        <div class="cor-amostra" style="background-color: ${obterCorConfiguracao(config)}"></div>
                        <div class="nome-ap">
                            Canal: ${channel}<br>
                            Bandwidth: ${bandwidth}<br>
                            Frequência: ${frequency}
                        </div>
                    `;
                    legendaDiv.appendChild(legendaItem);
                });
            } else {
                // Mostra todas configs
                configuracoesUnicas.forEach(config => {
                    const [channel, bandwidth, frequency] = config.split('-');
                    const legendaItem = document.createElement('div');
                    legendaItem.className = 'legenda-item';
                    legendaItem.innerHTML = `
                        <div class="cor-amostra" style="background-color: ${obterCorConfiguracao(config)}"></div>
                        <div class="nome-ap">
                            Canal: ${channel}<br>
                            Bandwidth: ${bandwidth}<br>
                            Frequência: ${frequency}
                        </div>
                    `;
                    legendaDiv.appendChild(legendaItem);
                });
            }

            console.log('Elementos do Cytoscape:', elements);

            // Renderiza grafo
            cytoscape({
                container: document.getElementById(containerId),
                elements: elements,
                style: [
                    { selector: 'node', style: { 
                        'background-color': 'data(cor)',
                        'label': 'data(label)'
                    }},
                    { selector: 'edge', style: {
                        'width': function(ele) { return ele.data('peso') * 0.1; },
                        'line-color': '#000',
                        'label': function(ele) { return ele.data('peso').toFixed(2) + '%'; },
                        'font-size': 10,
                        'color': '#333',
                        'text-background-color': '#fff',
                        'text-background-opacity': 0.7,
                        'text-background-padding': 2
                    } }
                ],
                layout: { 
                    name: 'concentric',
                    minNodeSpacing: 100,
                    padding: 50,
                    concentric: function(node) {
                        return node.degree();
                    },
                    levelWidth: function(nodes) {
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

            // Atualiza estado do container
            const container = document.getElementById(containerId).parentNode;
            if (!data.nodes || data.nodes.length === 0) {
                container.classList.add('vazio');
            } else {
                container.classList.remove('vazio');
            }

            // Calcula consumo de energia
            let consumoTotal = 0;
            if (usarBacktracking && configuracoesDistribuidas) {
                // Consumo proposto
                data.nodes.forEach(node => {
                    const config = configuracoesDistribuidas[node.id];
                    if (config) {
                        const partes = config.split('-');
                        const bandwidth = partes[1] || '';
                        const frequency = partes[2] || '';
                        const consumo = consumoEnergia25Mbps(bandwidth, frequency);
                        if (consumo) consumoTotal += consumo;
                    }
                });
            } else {
                // Consumo original
                data.nodes.forEach(node => {
                    const ap = aps.find(ap => ap.id === node.id);
                    if (ap) {
                        const consumo = consumoEnergia25Mbps(ap.bandwidth, ap.frequency);
                        if (consumo) consumoTotal += consumo;
                    }
                });
            }
            // Exibe consumo
            let infoGasto = container.querySelector('.info-gasto');
            if (!infoGasto) {
                infoGasto = document.createElement('div');
                infoGasto.className = 'info-gasto';
                container.appendChild(infoGasto);
            }
            let dias = 15;
            let inputExistente = infoGasto.querySelector(`#input-dias-${containerId}`);
            if (inputExistente) dias = parseInt(inputExistente.value) || 15;
            const consumoDias = (consumoTotal * 24 * dias) / 1000;
            const valorFinal = consumoDias * 0.72;
            infoGasto.innerHTML = `Dias: <input id='input-dias-${containerId}' type='number' min='1' value='${dias}' style='width:48px; padding:2px; border-radius:4px; border:1px solid #b3d1ff; text-align:center; margin:0 4px 0 4px; font-size:13px;'> <br>Consumo: <b><span id='consumo-span-${containerId}'>${consumoDias.toFixed(2)}</span> kWh</b> | Custo: <b>R$ <span id='custo-span-${containerId}'>${valorFinal.toFixed(2)}</span></b>`;
            const inputDias = infoGasto.querySelector(`#input-dias-${containerId}`);
            const consumoSpan = infoGasto.querySelector(`#consumo-span-${containerId}`);
            const custoSpan = infoGasto.querySelector(`#custo-span-${containerId}`);
            inputDias.oninput = function() {
                let diasNovo = parseInt(inputDias.value) || 1;
                const consumoNovo = (consumoTotal * 24 * diasNovo) / 1000;
                const valorFinalNovo = consumoNovo * 0.72;
                consumoSpan.textContent = consumoNovo.toFixed(2);
                custoSpan.textContent = valorFinalNovo.toFixed(2);
            };

            if (callbackConfiguracoes && configuracoesDistribuidas) {
                callbackConfiguracoes(aps, configuracoesDistribuidas, window.selectedStrategy);
            }

            // Posiciona info de consumo
            if (infoGasto) {
                const legenda = container.querySelector('.legenda');
                if (legenda && legenda.nextSibling !== infoGasto) {
                    container.insertBefore(infoGasto, legenda.nextSibling);
                } else if (!legenda && container.lastChild !== infoGasto) {
                    container.appendChild(infoGasto);
                }
            }
        })
        .catch(err => {
            const container = document.getElementById(containerId).parentNode;
            container.classList.add('vazio');
            document.getElementById(containerId).innerHTML = '<p style="color:red">Erro ao carregar o grafo.</p>';
            console.error('Erro ao carregar grafo:', err);
        });
    }

    // Gera tabela de alterações
    function exibirTabelaAlteracoes(aps, configuracoesDistribuidas, estrategia = null) {
        const container = document.getElementById('tabela-alteracoes-container');
        container.innerHTML = '';
        if (!aps || !configuracoesDistribuidas) return;
        // Estrutura da tabela
        const tabela = document.createElement('table');
        tabela.style.width = '100%';
        tabela.style.borderCollapse = 'collapse';
        tabela.innerHTML = `
            <thead>
                <tr style="background:#f5f5f5">
                    <th style="border:1px solid #ccc;padding:8px">Nome do AP</th>
                    <th style="border:1px solid #ccc;padding:8px">Configuração Original</th>
                    <th style="border:1px solid #ccc;padding:8px">Configuração Proposta</th>
                    <th style="border:1px solid #ccc;padding:8px">Ações</th>
                </tr>
            </thead>
            <tbody></tbody>
        `;
        const tbody = tabela.querySelector('tbody');
        aps.forEach(ap => {
            const id = ap.id;
            const original = {
                channel: ap.channel || 'N/A',
                bandwidth: ap.bandwidth || 'N/A',
                frequency: ap.frequency || 'N/A'
            };
            let proposta = { channel: 'N/A', bandwidth: 'N/A', frequency: 'N/A' };
            const configProposta = configuracoesDistribuidas[id];
            if (configProposta) {
                const partes = configProposta.split('-');
                proposta = {
                    channel: (partes[0] || '').trim(),
                    bandwidth: (partes[1] || '').trim(),
                    frequency: (partes[2] || '').trim()
                };
            }
            const mudou = original.channel !== proposta.channel || original.bandwidth !== proposta.bandwidth || original.frequency !== proposta.frequency;
            // Detecta upgrade
            const freqOrig = String(original.frequency).replace(',', '.');
            const freqProp = String(proposta.frequency).replace(',', '.');
            const bwOrig = parseInt(String(original.bandwidth).replace(/[^0-9]/g, '')) || 0;
            const bwProp = parseInt(String(proposta.bandwidth).replace(/[^0-9]/g, '')) || 0;
            let upgrade = false;
            let upgradeTexto = '';
            if (freqOrig === freqProp && bwProp > bwOrig && bwOrig > 0) {
                upgrade = true;
                upgradeTexto = `<span style='color:#388e3c;font-weight:bold;margin-left:8px;' title='Upgrade de banda'>⬆️ ${freqOrig} GHz: ${bwOrig} → ${bwProp} MHz</span>`;
            }
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style=\"border:1px solid #ccc;padding:8px\">${ap.label || ap.id}</td>
                <td style=\"border:1px solid #ccc;padding:8px\">${original.channel} - ${original.bandwidth} - ${original.frequency}</td>
                <td class=\"td-proposta\" style=\"border:1px solid #ccc;padding:8px\">${proposta.channel} - ${proposta.bandwidth} - ${proposta.frequency} ${mudou ? '<span title=\"Configuração alterada\" style=\"margin-left:6px;font-size:16px;vertical-align:middle;\">🔄</span>' : ''} ${upgradeTexto}</td>
                <td style=\"border:1px solid #ccc;padding:8px\"><button class=\"btn-editar\">Editar</button></td>
            `;
            if (upgrade) {
                tr.style.background = '#e8f5e9';
            }
            tbody.appendChild(tr);
        });
        // Eventos dos botões
        Array.from(tbody.querySelectorAll('.btn-editar')).forEach((btn, idx) => {
            btn.addEventListener('click', function() {
                const tr = btn.closest('tr');
                const tdProposta = tr.querySelector('.td-proposta');
                if (btn.textContent === 'Editar') {
                    // Modo edição
                    const valores = tdProposta.textContent.split(' - ').map(v => v.replace('🔄','').trim());
                    tdProposta.innerHTML = `
                        <input type='text' class='input-edit' style='width:40px' value='${valores[0]}' /> -
                        <input type='text' class='input-edit' style='width:40px' value='${valores[1]}' /> -
                        <input type='text' class='input-edit' style='width:60px' value='${valores[2]}' />
                    `;
                    btn.textContent = 'Salvar';
                } else {
                    // Salva mudanças
                    const inputs = tdProposta.querySelectorAll('.input-edit');
                    const novoChannel = inputs[0].value;
                    const novoBandwidth = inputs[1].value;
                    const novoFrequency = inputs[2].value;
                    tdProposta.innerHTML = `${novoChannel} - ${novoBandwidth} - ${novoFrequency}`;
                    btn.textContent = 'Editar';
                    // Atualiza AP
                    const apId = aps[idx].id;
                    const ap = aps.find(ap => ap.id === apId);
                    if (ap) {
                        ap.channel = novoChannel;
                        ap.bandwidth = novoBandwidth;
                        ap.frequency = novoFrequency;
                        ap.locked = true;
                    }
                    apsOtimizado[idx].channel = novoChannel;
                    apsOtimizado[idx].bandwidth = novoBandwidth;
                    apsOtimizado[idx].frequency = novoFrequency;
                    apsOtimizado[idx].locked = true;
                    // Recarrega grafo
                    criarGrafo('cy2', window.legendaDiv2, true, exibirTabelaAlteracoes, apsOtimizado);
                }
            });
        });
        // Exibe resultados
        if (tbody.children.length > 0) {
            const titulo = document.createElement('h3');
            const estrategiaNome = estrategia || window.selectedStrategy;
            const nomeEstrategia = {
                'backtracking': 'Backtracking',
                'greedy': 'Greedy',
                'genetic': 'Genetic (ML)'
            }[estrategiaNome] || 'Backtracking';
            titulo.textContent = `Alterações de Configuração Propostas pelo ${nomeEstrategia}`;
            container.appendChild(titulo);
            container.appendChild(tabela);
        }
    }

    // UI: estratégia
    const strategySelect = document.getElementById('strategySelect');
    const btnRun = document.getElementById('btnRunAnalysis');
    const strategyInfo = document.getElementById('strategyInfo');

    async function fetchStrategiesFromServer() {
        try {
            const res = await fetch((window.ANALYSIS_API && window.ANALYSIS_API.strategies) || '/api/analysis/strategies');
            if (!res.ok) return;
            const data = await res.json();
            if (data && data.success && data.strategies) {
                // atualiza informações
                strategyInfo.textContent = 'Estratégias: ' + Object.keys(data.strategies).join(', ');
            }
        } catch (e) {
            console.warn('Não foi possível obter estratégias do servidor:', e);
        }
    }

    // Botão Executar Análise (sempre via servidor)
    if (btnRun) {
        btnRun.addEventListener('click', async () => {
            try {
                // Monta APS no formato esperado pelo analysis_service
                const aps = apsOriginais.map(ap => ({
                    id: ap.id,
                    x: parseFloat(ap.latitude),
                    y: parseFloat(ap.longitude),
                    raio: ap.raio || 50,
                    canal: ap.canal || ap.channel,
                    label: ap.name || ap.id
                })).filter(ap => !Number.isNaN(ap.x) && !Number.isNaN(ap.y));

                const payload = {
                    aps,
                    strategy: 'backtracking', // padrão no servidor; pode ser alterado no futuro pelo backend
                    parameters: {}
                };

                const url = (window.ANALYSIS_API && window.ANALYSIS_API.analyzeGraph) || '/api/analysis/analyze-graph';
                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (!res.ok || !data.success) {
                    alert('Falha na análise no servidor: ' + (data.error || res.status));
                    return;
                }

                // Renderiza com base no graph_data retornado
                const graph = data.graph_data;
                const elements = [];
                graph.nodes.forEach(node => {
                    elements.push({
                        data: {
                            id: node.id,
                            label: node.label || node.id,
                            cor: '#1976d2'
                        }
                    });
                });
                graph.links.forEach(link => {
                    elements.push({ data: { id: link.source + '_' + link.target, source: link.source, target: link.target } });
                });

                const cy = cytoscape({
                    container: document.getElementById('cy'),
                    elements,
                    style: [
                        { selector: 'node', style: { 'background-color': 'data(cor)', 'label': 'data(label)', 'color': '#333', 'font-size': '10px' } },
                        { selector: 'edge', style: { 'line-color': '#bbb' } }
                    ],
                    layout: { name: 'cose', animate: true }
                });
            } catch (err) {
                console.error('Erro ao executar análise no servidor:', err);
                alert('Erro ao executar análise no servidor. Ver console.');
            }
        });
    }

    // Botões de estratégia do servidor
    const serverButtons = document.querySelectorAll('.btn-server-analysis');
    if (serverButtons && serverButtons.length) {
        serverButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const strategy = btn.getAttribute('data-strategy');
                console.log(`[DEBUG] Estratégia selecionada (servidor): ${strategy}`);
                
                // Atualiza a estratégia selecionada
                window.selectedStrategy = strategy;
                
                // Recarrega a análise com a nova estratégia
                if (window.legendaDiv2) {
                    criarGrafo('cy2', window.legendaDiv2, true, exibirTabelaAlteracoes, apsOtimizado);
                }
                
                alert(`DEBUG: Estratégia (servidor) selecionada: ${strategy}`);
            });
        });
    }

    fetchStrategiesFromServer();

    // Inicializa página
    carregarAPs(() => {
        defineLegendaDivs();
        criarGrafo('cy1', window.legendaDiv1, false, null, apsOriginais); // Grafo original
        criarGrafo('cy2', window.legendaDiv2, true, exibirTabelaAlteracoes, apsOtimizado); // Grafo otimizado
    });
});