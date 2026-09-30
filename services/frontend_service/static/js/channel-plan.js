// Listas dependentes de frequencia, largura de banda e canal, montadas a partir do plano de
// canais do analysis_service: "valid" traz todos os canais permitidos e "profiles", os perfis
// que as estrategias podem propor.
(function() {
    let planoPromise = null;

    function carregarPlano() {
        if (!planoPromise) {
            planoPromise = fetch('/api/analysis/channel-plan')
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Não foi possível carregar o plano de canais.');
                    }
                    return response.json();
                })
                .catch(err => {
                    planoPromise = null;
                    throw err;
                });
        }
        return planoPromise;
    }

    function numero(valor) {
        const convertido = parseFloat(String(valor ?? '').replace(',', '.'));
        return Number.isFinite(convertido) ? convertido : null;
    }

    function chaveEquivalente(chaves, valor) {
        const alvo = numero(valor);
        if (alvo === null) return null;
        return chaves.find(chave => numero(chave) === alvo) ?? null;
    }

    function ordenar(chaves) {
        return [...chaves].sort((a, b) => numero(a) - numero(b));
    }

    function preencher(select, valores, selecionado, placeholder) {
        select.innerHTML = '';
        if (placeholder) {
            select.appendChild(new Option(placeholder, ''));
        }
        valores.forEach(valor => select.appendChild(new Option(valor, valor)));
        select.value = selecionado ?? (placeholder ? '' : (valores[0] ?? ''));
    }

    // Inclui a configuracao atual nas opcoes, para nao descarta-la ao editar um AP que esta
    // fora do conjunto (por exemplo, um AP em 6 GHz na edicao da proposta).
    function incluirConfiguracao(opcoes, atual) {
        const plano = JSON.parse(JSON.stringify(opcoes || {}));
        if ([atual.frequency, atual.bandwidth, atual.channel].some(valor => numero(valor) === null)) return plano;

        const frequencia = chaveEquivalente(Object.keys(plano), atual.frequency) ?? atual.frequency;
        plano[frequencia] = plano[frequencia] || {};
        const larguras = plano[frequencia];
        const largura = chaveEquivalente(Object.keys(larguras), atual.bandwidth) ?? atual.bandwidth;
        larguras[largura] = larguras[largura] || [];
        if (chaveEquivalente(larguras[largura], atual.channel) === null) {
            larguras[largura].push(String(atual.channel));
        }
        return plano;
    }

    // selects: {frequency, bandwidth, channel}. Com manterAtual, a configuracao atual e sempre
    // uma opcao; sem ele, uma configuracao atual invalida deixa os campos por selecionar.
    function vincular(selects, opcoes, atual = {}, { manterAtual = false } = {}) {
        const plano = manterAtual ? incluirConfiguracao(opcoes, atual) : (opcoes || {});
        const placeholder = manterAtual ? null : 'Selecione';

        function atualizarCanais(canalDesejado, inicial) {
            const larguras = plano[selects.frequency.value] || {};
            const canais = ordenar(larguras[selects.bandwidth.value] || []);
            const canal = chaveEquivalente(canais, canalDesejado) ?? (inicial ? null : canais[0]);
            preencher(selects.channel, canais, canal, placeholder);
        }

        function atualizarLarguras(larguraDesejada, canalDesejado, inicial) {
            const larguras = ordenar(Object.keys(plano[selects.frequency.value] || {}));
            const largura = chaveEquivalente(larguras, larguraDesejada) ?? (inicial ? null : larguras[0]);
            preencher(selects.bandwidth, larguras, largura, placeholder);
            atualizarCanais(canalDesejado, inicial);
        }

        const frequencias = ordenar(Object.keys(plano));
        preencher(selects.frequency, frequencias, chaveEquivalente(frequencias, atual.frequency), placeholder);
        atualizarLarguras(atual.bandwidth, atual.channel, true);

        selects.frequency.onchange = () => atualizarLarguras(selects.bandwidth.value, selects.channel.value, false);
        selects.bandwidth.onchange = () => atualizarCanais(selects.channel.value, false);
    }

    function rotuloFaixa(frequencia) {
        return String(frequencia).replace('.', ',');
    }

    // Largura minima de uma barra de 20 MHz, em pixels; faixas largas (5 e 6 GHz) ganham rolagem horizontal.
    const PIXELS_POR_MHZ = 1.4;
    const ALTURA_DA_RAIA = 26;

    function formatarMhz(valor) {
        return Number(valor).toLocaleString('pt-BR', { useGrouping: false });
    }

    // Distribui as barras em raias: cada uma vai para a primeira raia em que nao se sobrepoe a outra.
    // Barras que apenas se encostam (fim de uma igual ao inicio da outra) podem dividir a raia. Quando isso
    // nao reduz as raias ao menos a metade (como os pares de 40 MHz em 2,4 GHz), cada barra fica na sua
    // raia, em ordem de frequencia, para a escada nao ficar fora de ordem.
    function distribuirEmRaias(opcoes) {
        const ordenadas = [...opcoes].sort((a, b) => a.lower_mhz - b.lower_mhz);
        const fins = [];
        const empacotadas = ordenadas.map(opcao => {
            let raia = fins.findIndex(fim => fim <= opcao.lower_mhz);
            if (raia < 0) {
                raia = fins.length;
                fins.push(0);
            }
            fins[raia] = opcao.upper_mhz;
            return { opcao, raia };
        });
        return fins.length * 2 > ordenadas.length
            ? ordenadas.map((opcao, raia) => ({ opcao, raia }))
            : empacotadas;
    }

    // Em cada largura, o maior conjunto de opcoes sem sobreposicao (escolha gulosa pela que termina primeiro).
    function semSobreposicao(opcoes) {
        let fim = -Infinity;
        return [...opcoes]
            .sort((a, b) => a.upper_mhz - b.upper_mhz)
            .filter(opcao => {
                if (opcao.lower_mhz < fim) return false;
                fim = opcao.upper_mhz;
                return true;
            })
            .map(opcao => opcao.channel);
    }

    function passoDoEixo(intervalo) {
        if (intervalo <= 100) return 10;
        if (intervalo <= 400) return 50;
        return 100;
    }

    // Mapa do espectro dos perfis que as estrategias podem usar em cada faixa (o k de cada grafo). Cada opcao
    // ("options" do plano) e uma barra na posicao e com a largura que ocupa, com uma linha por largura de banda;
    // barras sobrepostas no eixo interferem entre si. O rotulo e o canal primario, o que se configura no AP.
    // Os perfis padrao ja vem marcados e as faixas comecam recolhidas; sem canais marcados em 6 GHz, que nao
    // tem perfis padrao, seus APs mantem a configuracao.
    function criarSeletor(container, plano) {
        const opcoesPorFaixa = plano.options || {};
        const faixas = ordenar(Object.keys(opcoesPorFaixa));
        const padrao = plano.profiles || {};
        const barras = [];
        container.innerHTML = '';

        const legenda = document.createElement('p');
        legenda.className = 'spectrum-legend';
        legenda.innerHTML = 'Clique nas barras para escolher os canais. Barras que se sobrepõem no eixo de frequência '
            + 'interferem entre si; as marcadas que se sobrepõem a outra marcada da mesma largura ficam em '
            + '<span class="spectrum-legend-overlap">laranja</span>.';
        container.appendChild(legenda);

        faixas.forEach(frequencia => {
            const larguras = ordenar(Object.keys(opcoesPorFaixa[frequencia]));
            const todas = larguras.flatMap(largura => opcoesPorFaixa[frequencia][largura]);
            const inicio = Math.min(...todas.map(opcao => opcao.lower_mhz));
            const fim = Math.max(...todas.map(opcao => opcao.upper_mhz));
            const intervalo = fim - inicio;
            const posicao = mhz => `${((mhz - inicio) / intervalo) * 100}%`;
            const barrasDaFaixa = [];

            const detalhes = document.createElement('details');
            detalhes.className = 'panel panel-compact spectrum-band';
            const resumo = document.createElement('summary');
            detalhes.appendChild(resumo);

            const atalhos = document.createElement('div');
            atalhos.className = 'spectrum-actions';
            // Um conjunto sem sobreposicao usa uma largura so: toda barra se sobrepoe as de outras larguras que a
            // contem. Por isso ha um atalho por largura, que marca o maior conjunto dela e desmarca as demais.
            const presets = [
                ['Padrão', largura => (padrao[frequencia] || {})[largura] || [], 'Perfis padrão das estratégias'],
                ['Todos', largura => opcoesPorFaixa[frequencia][largura].map(opcao => opcao.channel), 'Todas as opções'],
                ['Nenhum', () => [], 'Nenhuma opção'],
                ...larguras.map(unica => [
                    unica,
                    largura => (largura === unica ? semSobreposicao(opcoesPorFaixa[frequencia][largura]) : []),
                    `Só ${unica}, com o maior conjunto de canais que não se sobrepõem`,
                ]),
            ];
            presets.forEach(([rotulo, escolher, dica], indice) => {
                if (indice === 3) {
                    const titulo = document.createElement('span');
                    titulo.className = 'spectrum-actions-label';
                    titulo.textContent = 'Sem sobreposição:';
                    atalhos.appendChild(titulo);
                }
                const botao = document.createElement('button');
                botao.type = 'button';
                botao.className = 'chip spectrum-action';
                botao.textContent = rotulo;
                botao.title = dica;
                botao.addEventListener('click', () => {
                    const escolhidos = Object.fromEntries(larguras.map(largura => [largura, escolher(largura)]));
                    barrasDaFaixa.forEach(barra => marcar(barra, (escolhidos[barra.dataset.bandwidth] || []).includes(barra.dataset.channel)));
                    atualizarFaixa();
                });
                atalhos.appendChild(botao);
            });
            detalhes.appendChild(atalhos);

            const corpo = document.createElement('div');
            corpo.className = 'spectrum-body';
            const rotulos = document.createElement('div');
            rotulos.className = 'spectrum-labels';
            const rolagem = document.createElement('div');
            rolagem.className = 'spectrum-scroll';
            const tela = document.createElement('div');
            tela.className = 'spectrum-canvas';
            tela.style.minWidth = `${Math.ceil(intervalo * PIXELS_POR_MHZ)}px`;
            const contadores = {};

            larguras.forEach(largura => {
                const distribuidas = distribuirEmRaias(opcoesPorFaixa[frequencia][largura]);
                const raias = Math.max(...distribuidas.map(item => item.raia)) + 1;
                const altura = `${raias * ALTURA_DA_RAIA + 6}px`;
                const marcados = (padrao[frequencia] || {})[largura] || [];

                const rotulo = document.createElement('div');
                rotulo.className = 'spectrum-label';
                rotulo.style.height = altura;
                rotulo.textContent = largura;
                const contador = document.createElement('small');
                rotulo.appendChild(contador);
                contadores[largura] = contador;
                rotulos.appendChild(rotulo);

                const linha = document.createElement('div');
                linha.className = 'spectrum-row';
                linha.style.height = altura;
                distribuidas.forEach(({ opcao, raia }) => {
                    const barra = document.createElement('button');
                    barra.type = 'button';
                    barra.className = 'spectrum-bar';
                    barra.style.left = posicao(opcao.lower_mhz);
                    barra.style.width = `${((opcao.upper_mhz - opcao.lower_mhz) / intervalo) * 100}%`;
                    barra.style.top = `${raia * ALTURA_DA_RAIA + 3}px`;
                    barra.dataset.frequency = frequencia;
                    barra.dataset.bandwidth = largura;
                    barra.dataset.channel = opcao.channel;
                    barra.dataset.lower = opcao.lower_mhz;
                    barra.dataset.upper = opcao.upper_mhz;
                    const canais = opcao.channels || [opcao.channel];
                    barra.title = `${canais.length > 1 ? `Canais ${canais.join(', ')}, primário ${opcao.channel}` : `Canal ${opcao.channel}`}`
                        + ` | ${largura} | ${formatarMhz(opcao.lower_mhz)}–${formatarMhz(opcao.upper_mhz)} MHz`;
                    // Canais de 40 MHz sao pares (primario e secundario): o rotulo mostra os dois, para a escada de
                    // 2,4 GHz ser lida em ordem (7+11, e nao 11). Blocos maiores mostram o primario.
                    barra.textContent = canais.length === 2 ? canais.join('+') : opcao.channel;
                    marcar(barra, marcados.includes(opcao.channel));
                    barra.addEventListener('click', () => {
                        marcar(barra, barra.getAttribute('aria-pressed') !== 'true');
                        atualizarFaixa();
                    });
                    linha.appendChild(barra);
                    barrasDaFaixa.push(barra);
                    barras.push(barra);
                });
                tela.appendChild(linha);
            });

            // Eixo de frequencia, com marcas em multiplos redondos de MHz.
            const eixo = document.createElement('div');
            eixo.className = 'spectrum-axis';
            const passo = passoDoEixo(intervalo);
            for (let marca = Math.ceil(inicio / passo) * passo; marca <= fim; marca += passo) {
                const rotuloMarca = document.createElement('span');
                rotuloMarca.className = 'spectrum-tick';
                rotuloMarca.style.left = posicao(marca);
                // As marcas das pontas ficam dentro do eixo, para nao criar rolagem.
                const fracao = (marca - inicio) / intervalo;
                rotuloMarca.style.transform = fracao > 0.97 ? 'translateX(-100%)' : fracao < 0.03 ? 'none' : 'translateX(-50%)';
                rotuloMarca.textContent = formatarMhz(marca);
                eixo.appendChild(rotuloMarca);
            }
            tela.appendChild(eixo);
            const rotuloEixo = document.createElement('div');
            rotuloEixo.className = 'spectrum-label spectrum-axis-label';
            rotuloEixo.textContent = 'MHz';
            rotulos.appendChild(rotuloEixo);

            rolagem.appendChild(tela);
            corpo.appendChild(rotulos);
            corpo.appendChild(rolagem);
            detalhes.appendChild(corpo);
            container.appendChild(detalhes);

            function atualizarFaixa() {
                const marcadas = barrasDaFaixa.filter(barra => barra.getAttribute('aria-pressed') === 'true');
                barrasDaFaixa.forEach(barra => {
                    // So na mesma largura: toda barra se sobrepoe as de outras larguras que a contem.
                    const sobreposta = barra.getAttribute('aria-pressed') === 'true' && marcadas.some(outra => outra !== barra
                        && outra.dataset.bandwidth === barra.dataset.bandwidth
                        && Number(outra.dataset.lower) < Number(barra.dataset.upper)
                        && Number(barra.dataset.lower) < Number(outra.dataset.upper));
                    barra.classList.toggle('is-overlapping', sobreposta);
                });
                larguras.forEach(largura => {
                    const total = marcadas.filter(barra => barra.dataset.bandwidth === largura).length;
                    contadores[largura].textContent = ` (${total})`;
                });
                const total = marcadas.length;
                resumo.textContent = `${rotuloFaixa(frequencia)}: k = ${total} perfi${total === 1 ? 'l' : 's'}`;
            }
            atualizarFaixa();
        });

        function marcar(barra, marcada) {
            barra.setAttribute('aria-pressed', marcada ? 'true' : 'false');
            barra.classList.toggle('is-selected', marcada);
        }

        // {frequencia: {largura: [canais]}} com as faixas que tem ao menos um canal marcado.
        function selecao() {
            const escolhidos = {};
            barras.filter(barra => barra.getAttribute('aria-pressed') === 'true').forEach(barra => {
                const larguras = escolhidos[barra.dataset.frequency] = escolhidos[barra.dataset.frequency] || {};
                (larguras[barra.dataset.bandwidth] = larguras[barra.dataset.bandwidth] || []).push(barra.dataset.channel);
            });
            return escolhidos;
        }

        // Faixas com perfis padrao precisam de ao menos um canal; sem ele, a analise usaria o padrao sem aviso.
        function validar() {
            const escolhidos = selecao();
            const faltando = faixas.filter(frequencia => Object.keys(padrao[frequencia] || {}).length > 0 && !escolhidos[frequencia]);
            return faltando.length
                ? `Selecione ao menos um canal em ${faltando.map(rotuloFaixa).join(' e ')}.`
                : null;
        }

        return { selecao, validar };
    }

    window.ChannelPlan = {
        carregar: carregarPlano,
        vincular,
        criarSeletor
    };
})();
