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
                        throw new Error('Nao foi possivel carregar o plano de canais.');
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

    // Caixas de selecao dos perfis que as estrategias podem usar em cada faixa (o k de cada grafo). Ha uma
    // caixa por posicao distinta no espectro ("options" do plano): em larguras agregadas, um bloco como 36-48
    // a 80 MHz, que envia o seu canal primario. Os perfis padrao ja vem marcados, e as faixas comecam
    // recolhidas; sem canais marcados em 6 GHz, que nao tem perfis padrao, seus APs mantem a configuracao.
    function criarSeletor(container, plano) {
        const opcoesPorFaixa = plano.options || {};
        const faixas = ordenar(Object.keys(opcoesPorFaixa));
        const padrao = plano.profiles || {};
        container.innerHTML = '';

        faixas.forEach(frequencia => {
            const detalhes = document.createElement('details');
            detalhes.className = 'analysis-channel-band';
            const resumo = document.createElement('summary');
            detalhes.appendChild(resumo);

            ordenar(Object.keys(opcoesPorFaixa[frequencia])).forEach(largura => {
                const linha = document.createElement('div');
                linha.className = 'analysis-channel-row';
                const rotulo = document.createElement('span');
                rotulo.className = 'analysis-channel-width';
                rotulo.textContent = largura;
                const canais = document.createElement('div');
                canais.className = 'analysis-channel-options';
                const marcados = (padrao[frequencia] || {})[largura] || [];

                opcoesPorFaixa[frequencia][largura].forEach(bloco => {
                    const opcao = document.createElement('label');
                    opcao.className = 'analysis-channel-chip';
                    const caixa = document.createElement('input');
                    caixa.type = 'checkbox';
                    caixa.value = bloco.channel;
                    caixa.dataset.frequency = frequencia;
                    caixa.dataset.bandwidth = largura;
                    caixa.checked = marcados.includes(bloco.channel);
                    caixa.addEventListener('change', () => atualizarResumo(detalhes, frequencia));
                    const canaisDoBloco = bloco.channels || [bloco.channel];
                    opcao.title = canaisDoBloco.length > 1
                        ? `Canais ${canaisDoBloco.join(', ')} (primario ${bloco.channel})`
                        : `Canal ${bloco.channel}`;
                    opcao.appendChild(caixa);
                    opcao.appendChild(document.createTextNode(
                        canaisDoBloco.length > 1 ? `${canaisDoBloco[0]}–${canaisDoBloco[canaisDoBloco.length - 1]}` : bloco.channel
                    ));
                    canais.appendChild(opcao);
                });

                linha.appendChild(rotulo);
                linha.appendChild(canais);
                detalhes.appendChild(linha);
            });

            container.appendChild(detalhes);
            atualizarResumo(detalhes, frequencia);
        });

        function atualizarResumo(detalhes, frequencia) {
            const total = detalhes.querySelectorAll('input:checked').length;
            detalhes.querySelector('summary').textContent = `${rotuloFaixa(frequencia)}: k = ${total} perfi${total === 1 ? 'l' : 's'}`;
        }

        // {frequencia: {largura: [canais]}} com as faixas que tem ao menos um canal marcado.
        function selecao() {
            const escolhidos = {};
            container.querySelectorAll('input:checked').forEach(caixa => {
                const larguras = escolhidos[caixa.dataset.frequency] = escolhidos[caixa.dataset.frequency] || {};
                (larguras[caixa.dataset.bandwidth] = larguras[caixa.dataset.bandwidth] || []).push(caixa.value);
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
