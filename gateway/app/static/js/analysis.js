window.addEventListener('DOMContentLoaded', function() {
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
            gap: 20px;
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
            border: none !important;
            background: transparent !important;
            box-shadow: none !important;
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
    `;
    document.head.appendChild(style);

    // Inicializa estrutura básica da página
    const pageContainer = document.createElement('div');
    pageContainer.className = 'page-container';
    const contentContainer = document.createElement('div');
    contentContainer.className = 'content-container';
    
    // Posiciona o título no topo
    const titulo = document.querySelector('h1');
    if (titulo) {
        titulo.parentNode.insertBefore(pageContainer, titulo);
        pageContainer.appendChild(titulo);
    }

    // Inicializa containers para os grafos e suas legendas
    const grafoContainer1 = document.createElement('div');
    grafoContainer1.className = 'grafo-container';
    const cyDiv1 = document.createElement('div');
    cyDiv1.id = 'cy1';
    cyDiv1.className = 'cy';
    const legendaDiv1 = document.createElement('div');
    legendaDiv1.className = 'legenda';
    grafoContainer1.appendChild(cyDiv1);
    grafoContainer1.appendChild(legendaDiv1);

    const grafoContainer2 = document.createElement('div');
    grafoContainer2.className = 'grafo-container';
    const cyDiv2 = document.createElement('div');
    cyDiv2.id = 'cy2';
    cyDiv2.className = 'cy';
    const legendaDiv2 = document.createElement('div');
    legendaDiv2.className = 'legenda';
    grafoContainer2.appendChild(cyDiv2);
    grafoContainer2.appendChild(legendaDiv2);

    contentContainer.appendChild(grafoContainer1);
    contentContainer.appendChild(grafoContainer2);
    pageContainer.appendChild(contentContainer);

    // Inicializa container para tabela de mudanças propostas
    const tabelaAlteracoesContainer = document.createElement('div');
    tabelaAlteracoesContainer.id = 'tabela-alteracoes-container';
    tabelaAlteracoesContainer.style.margin = '30px 0 0 0';
    pageContainer.appendChild(tabelaAlteracoesContainer);

    // Armazena mapeamento de cores para configurações
    const coresPorConfiguracao = new Map();

    // Gera chave única para identificar configurações
    function gerarChaveConfiguracao(ap) {
        const channel = ap.channel || 'N/A';
        const bandwidth = ap.bandwidth || 'N/A';
        const frequency = ap.frequency || 'N/A';
        return `${channel}-${bandwidth}-${frequency}`;
    }

    function gerarCorAleatoria() {
        const letras = '0123456789ABCDEF';
        let cor = '#';
        for (let i = 0; i < 6; i++) {
            cor += letras[Math.floor(Math.random() * 16)];
        }
        return cor;
    }

    // Gerencia cores para configurações
    function obterCorConfiguracao(config) {
        if (!coresPorConfiguracao.has(config)) {
            coresPorConfiguracao.set(config, gerarCorAleatoria());
        }
        return coresPorConfiguracao.get(config);
    }

    // Valida atribuição de configuração considerando vizinhos
    function podeAtribuirConfiguracao(grafo, no, config, configuracoes) {
        const vizinhos = grafo.get(no) || new Set();
        for (const vizinho of vizinhos) {
            if (configuracoes[vizinho] === config) {
                return false;
            }
        }
        return true;
    }

    // Implementa algoritmo de backtracking para distribuição de configurações
    function distribuirConfiguracoes(grafo, nos, configuracoes, configsDisponiveis, index = 0, aps = null) {
        if (index === nos.length) {
            return true;
        }

        const no = nos[index];
        // Obtém frequência do AP atual
        let freq = null;
        if (aps) {
            const ap = aps.find(ap => ap.id === no);
            if (ap) freq = String(ap.frequency).replace(',', '.');
        }

        // Filtra configurações compatíveis com a frequência
        let configsFiltradas = [...configsDisponiveis];
        if (freq) {
            configsFiltradas = configsFiltradas.filter(cfg => {
                const freqCfg = (cfg.split('-')[2] || '').trim().replace(',', '.');
                return freqCfg === freq;
            });
        }

        // Ordena configurações por prioridade de banda
        let configsOrdenadas = [...configsFiltradas];
        if (freq) {
            configsOrdenadas.sort((a, b) => {
                const bandaA = (a.split('-')[1] || '').replace(/[^0-9]/g, '');
                const bandaB = (b.split('-')[1] || '').replace(/[^0-9]/g, '');
                if (freq.startsWith('2.4')) {
                    if (bandaA === '40' && bandaB !== '40') return -1;
                    if (bandaB === '40' && bandaA !== '40') return 1;
                    if (bandaA === '20' && bandaB !== '20') return -1;
                    if (bandaB === '20' && bandaA !== '20') return 1;
                } else if (freq.startsWith('5')) {
                    if (bandaA === '80' && bandaB !== '80') return -1;
                    if (bandaB === '80' && bandaA !== '80') return 1;
                    if (bandaA === '40' && bandaB !== '40') return -1;
                    if (bandaB === '40' && bandaA !== '40') return 1;
                    if (bandaA === '20' && bandaB !== '20') return -1;
                    if (bandaB === '20' && bandaA !== '20') return 1;
                }
                return 0;
            });
        }

        for (const config of configsOrdenadas) {
            if (podeAtribuirConfiguracao(grafo, no, config, configuracoes)) {
                configuracoes[no] = config;
                if (distribuirConfiguracoes(grafo, nos, configuracoes, configsDisponiveis, index + 1, aps)) {
                    return true;
                }
                configuracoes[no] = null;
            }
        }

        return false;
    }

    // Renderiza grafo de colisão com dados dos APs
    function criarGrafo(containerId, legendaDiv, usarBacktracking = false, callbackConfiguracoes = null) {
        fetch(window.ACCESS_POINT_URL)
            .then(response => response.json())
            .then(points => {
                console.log('Pontos recebidos:', points);

                function getRaio(frequency) {
                    if (!frequency) return 10;
                    const freq = String(frequency).replace(',', '.');
                    if (freq.startsWith('2.4')) return 20;
                    if (freq.startsWith('5')) return 15;
                    if (freq.startsWith('6')) return 12;
                    return 10;
                }

                // Prepara dados dos APs para visualização
                const aps = (points || [])
                    .filter(p => p.latitude !== null && p.latitude !== undefined && 
                               p.longitude !== null && p.longitude !== undefined)
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

                // Identifica configurações únicas
                const configuracoesUnicas = new Set();
                aps.forEach(ap => {
                    const config = gerarChaveConfiguracao(ap);
                    if (config !== 'N/A-N/A-N/A') {
                        configuracoesUnicas.add(config);
                    }
                });

                // Inicializa cores para configurações
                configuracoesUnicas.forEach(config => {
                    obterCorConfiguracao(config);
                });

                console.log('Configurações únicas:', configuracoesUnicas);

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

                    // Constrói estrutura do grafo
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
                        // Aplica algoritmo de backtracking
                        const nos = data.nodes.map(node => node.id);
                        const configuracoes = {};
                        const configsDisponiveis = Array.from(configuracoesUnicas);
                        
                        if (distribuirConfiguracoes(grafo, nos, configuracoes, configsDisponiveis, 0, aps)) {
                            configuracoesDistribuidas = {...configuracoes};
                            console.log('Configurações distribuídas:', configuracoes);
                            
                            // Cria elementos com novas configurações
                            data.nodes.forEach(node => {
                                const config = configuracoes[node.id];
                                elements.push({ 
                                    data: { 
                                        id: node.id, 
                                        label: node.label || node.id,
                                        cor: obterCorConfiguracao(config)
                                    } 
                                });
                            });
                        } else {
                            console.log('Não foi possível encontrar uma distribuição válida');
                            // Mantém configurações originais
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
                    } else {
                        // Usa configurações originais
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

                    // Atualiza legenda do grafo
                    legendaDiv.innerHTML = '';
                    if (usarBacktracking) {
                        // Mostra apenas configurações em uso
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
                        // Mostra todas as configurações
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

                    // Atualiza estado visual do container
                    const container = document.getElementById(containerId).parentNode;
                    if (!data.nodes || data.nodes.length === 0) {
                        container.classList.add('vazio');
                    } else {
                        container.classList.remove('vazio');
                    }

                    if (callbackConfiguracoes && configuracoesDistribuidas) {
                        callbackConfiguracoes(aps, configuracoesDistribuidas);
                    }
                })
                .catch(err => {
                    const container = document.getElementById(containerId).parentNode;
                    container.classList.add('vazio');
                    document.getElementById(containerId).innerHTML = '<p style="color:red">Erro ao carregar o grafo.</p>';
                    console.error('Erro ao carregar grafo:', err);
                });
            })
            .catch(err => {
                const container = document.getElementById(containerId).parentNode;
                container.classList.add('vazio');
                document.getElementById(containerId).innerHTML = '<p style="color:red">Erro ao buscar pontos de acesso.</p>';
                console.error('Erro ao buscar pontos:', err);
            });
    }

    // Gera e exibe tabela comparativa de configurações
    function exibirTabelaAlteracoes(aps, configuracoesDistribuidas) {
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
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style=\"border:1px solid #ccc;padding:8px\">${ap.label || ap.id}</td>
                <td style=\"border:1px solid #ccc;padding:8px\">${original.channel} - ${original.bandwidth} - ${original.frequency}</td>
                <td style=\"border:1px solid #ccc;padding:8px\">${proposta.channel} - ${proposta.bandwidth} - ${proposta.frequency} ${mudou ? '<span title=\\"Configuração alterada\\" style=\\"margin-left:6px;font-size:16px;vertical-align:middle;\\">🔄</span>' : ''}</td>
            `;
            tbody.appendChild(tr);
        });
        // Exibe resultados
        if (tbody.children.length > 0) {
            const titulo = document.createElement('h3');
            titulo.textContent = 'Alterações de Configuração Propostas pelo Backtracking';
            container.appendChild(titulo);
            container.appendChild(tabela);
        }
    }

    // Inicializa visualização dos grafos
    criarGrafo('cy1', legendaDiv1, false); // Grafo com configurações originais
    criarGrafo('cy2', legendaDiv2, true, exibirTabelaAlteracoes);  // Grafo com otimização por backtracking
});