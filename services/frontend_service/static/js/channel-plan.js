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

    window.ChannelPlan = {
        carregar: carregarPlano,
        vincular
    };
})();
