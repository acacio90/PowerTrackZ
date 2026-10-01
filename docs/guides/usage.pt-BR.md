# Guia de Uso

[English](usage.md) | **Português**

Este guia descreve o fluxo principal da interface: carregar pontos de acesso, salvá-los no banco e analisar as configurações de canal. A instalação está descrita em [installation.pt-BR.md](installation.pt-BR.md).

## 1. Sua Infraestrutura

A página **Sua infraestrutura** (menu **Infraestrutura**, `/infrastructure`) reúne a lista e o mapa dos APs salvos no banco, nos cards **Pontos de acesso** e **Mapa dos pontos de acesso**. Os endereços antigos `/hosts` e `/register` redirecionam para ela.

### Carregar APs

O botão **Carregar APs** abre uma janela com três origens:

- **Zabbix:** lista os APs monitorados pelo Zabbix configurado (ver seção 4). O Zabbix não informa coordenadas; APs já salvos mantêm as coordenadas do inventário.
- **Importar JSON:** lê um arquivo com uma lista de APs ou um objeto com a chave `aps`, como o produzido pela opção abaixo.
- **Gerar topologia:** cria APs aleatórios já posicionados. Os parâmetros são:
  - *Quantidade de APs*: entre 2 e 1000;
  - *Grau mínimo*: número mínimo de vizinhos perto dos quais cada AP é posicionado, menor que a quantidade de APs. Essas ligações servem só para posicionar os APs; o grafo analisado é montado depois, pela sobreposição das coberturas na mesma faixa, e costuma ser bem mais denso;
  - *Semente* (opcional): inteiro entre 0 e 4294967295. A mesma semente, com os mesmos parâmetros e a mesma versão do PowerTrackZ, gera a mesma topologia; em branco, uma semente é sorteada. A semente usada aparece na revisão, no nome do arquivo baixado e no campo `metadata.seed` do JSON.

Os APs carregados aparecem para revisão, ainda sem salvar; os que não têm coordenadas ficam destacados em vermelho. Acima da lista, a revisão mostra as métricas do grafo que será analisado (APs, arestas, grau médio, grau máximo e densidade, no total e por faixa), úteis para descrever as instâncias de um experimento. **Baixar JSON** grava a lista em um arquivo, útil para repetir um experimento com a mesma topologia (que também pode ser recriada pela semente). **Salvar** grava os APs no banco: APs com o mesmo `id` de um AP salvo são atualizados, e os demais são criados.

### Editar o inventário

- **Adicionar:** clique no mapa para marcar a posição e use o botão **+** para informar descrição, faixa, largura de banda e canal; **Adicionar** grava o AP.
- **Editar:** o ícone ao lado de cada AP abre seus dados; as coordenadas também podem ser ajustadas clicando no mapa com a janela aberta.
- **Excluir:** marque os APs e clique em **Excluir selecionados**.

Ao adicionar ou editar um AP, faixa, largura de banda e canal são escolhidos em listas com os canais permitidos no Brasil (2,4 GHz: canais 1 a 13; 5 GHz: 36 a 64, 100 a 144 e 149 a 165; 6 GHz: 1 a 233). As larguras oferecidas dependem da faixa, e os canais, da faixa e da largura; ao trocar a faixa ou a largura, os campos seguintes passam a um valor válido. Um AP salvo com uma configuração fora dessas listas abre com os campos por selecionar.

Na lista, APs sem coordenadas aparecem em vermelho. Somente APs com coordenadas participam da análise.

## 2. Analisar

A página **Análise** (menu **Análise**, `/analysis`) monta o grafo de conflitos entre os APs salvos e indica uma nova configuração para cada um. Para comparar várias estratégias sobre os mesmos APs de uma vez, use **Comparar estratégias nesta infraestrutura**, no alto da página, que abre a comparação na página de Experimentos (seção 5). A configuração fica em uma coluna lateral, em quatro etapas numeradas, e o resultado, em abas ao lado; em telas estreitas, a coluna fica acima do resultado. Só a etapa 1 começa aberta; cada etapa recolhe e expande ao clicar no título (um parâmetro inválido abre a sua etapa ao executar); recolhida, mostra a escolha atual ao lado dele (a estratégia, o critério ou o k de cada faixa), para poupar espaço na tela.

1. **Estratégia.** As estratégias aparecem agrupadas por família, cada uma com uma descrição curta e a indicação de método exato ou sem garantia de ótimo, conforme o analysis_service declara:
   - **Exata — Backtracking:** com poucos APs, devolve a configuração ótima; em redes grandes, para no limite de tempo e devolve a melhor configuração encontrada até ali.
   - **Construtiva — Guloso:** heurística rápida, adequada a redes grandes, sem garantia de ótimo.
   - **Metaheurísticas — Busca local:** troca o perfil de um AP sorteado e aceita a troca se ela não piorar a solução; sem garantia de ótimo. Serve de referência para as demais metaheurísticas, que usam a mesma base (custo, vizinhança, semente e critérios de parada).
   - **Metaheurísticas — Simulated Annealing:** aceita pioras com uma probabilidade que diminui com a temperatura, para escapar de ótimos locais; devolve a melhor solução encontrada.
   - **Metaheurísticas — Busca Tabu:** a cada iteração, aplica a melhor troca de perfil entre alguns APs sorteados (priorizando os em conflito), mesmo que pior, e proíbe por algumas iterações desfazê-la; devolve a melhor solução encontrada.
   - **Metaheurísticas — Algoritmo genético:** evolui uma população de soluções por seleção em torneio, cruzamento, mutação e elitismo; devolve a melhor solução encontrada.
   - **Metaheurísticas — Algoritmo genético híbrido:** o algoritmo genético com uma busca local aplicada a alguns indivíduos de cada geração, para refinar as soluções que o AG encontra.
2. **Critério de otimização.** Escolha a ordem em que as estratégias comparam as soluções; a explicação da opção escolhida aparece abaixo do campo:
   - **Padrão:** menos conflitos, depois menor interferência e, no desempate, maior largura de banda;
   - **Energia no desempate:** menos conflitos, depois menor interferência e, no desempate, menor potência;
   - **Energia primeiro:** menor potência, depois menos conflitos e menor interferência; aceita conflitos para economizar energia.

   A potência vem do mesmo modelo de consumo exibido nos resultados. Configurações sem valor no modelo (160 MHz) contam como a maior potência modelada da faixa, e, em 6 GHz, que não tem valores no modelo, a energia não diferencia os perfis. Rodar a mesma rede com critérios diferentes mostra quanto de energia se ganha ou se perde em troca de conflitos e interferência.
3. **Canais.** A etapa mostra o total de perfis (k) de cada faixa e se ele ainda é o padrão ou foi personalizado. **Escolher no mapa do espectro** abre o mapa de cada faixa: uma linha por largura de banda e, em cada linha, uma barra por opção, na posição e com a largura que ela ocupa no eixo de frequência. Clique nas barras para escolher os canais que as estratégias podem usar. A 40 MHz, cada barra é um par de primário e secundário, rotulado pelos dois canais (como 7+11); nas demais larguras, o rótulo é o canal primário, e a 80 e 160 MHz cada barra é um bloco de canais (como 36–48 a 80 MHz). A dica da barra mostra os canais, o primário enviado e o intervalo em MHz. Barras que se sobrepõem no eixo interferem entre si, e as marcadas que se sobrepõem a outra marcada da mesma largura ficam em laranja. Os atalhos **Padrão**, **Todos** e **Nenhum** marcam conjuntos prontos, e os de **Sem sobreposição** marcam uma única largura, com o maior conjunto de canais que não se sobrepõem (em 2,4 GHz, 1, 5, 9 e 13 a 20 MHz), desmarcando as demais. Os perfis padrão já vêm marcados; em 2,4 GHz, os dois de 40 MHz (1+5 e 7+11) se sobrepõem em 10 MHz e aparecem em laranja, e o atalho **Sem sobreposição** de 40 MHz troca-os por 1+5 e 9+13 quando o experimento não deve ter essa sobreposição (a decisão de mantê-los como padrão está no README do analysis_service). Em 2,4 e 5 GHz, é preciso manter ao menos um canal, e a faixa de 6 GHz começa vazia, com seus APs mantendo a configuração atual.
4. **Parâmetros.** Os parâmetros comuns da estratégia ficam visíveis, e os avançados, recolhidos em **Parâmetros avançados**, com os valores padrão. No backtracking, *Limite de tempo (s)* é comum (60 s por padrão, até 3600 s, aplicado a cada faixa; marque *Sem limite* para deixar a busca terminar por completo), e *Threads*, avançado (número de threads que dividem a busca, limitado ao número de APs). O guloso não tem parâmetros. Nas metaheurísticas, os comuns são *Semente* (em branco, o serviço sorteia uma; a usada aparece na aba **Execução**) e *Limite de tempo (s)* (10 s por padrão, em cada faixa), e os avançados, *Iterações* (máximo por faixa), *Iterações sem melhora* (para a busca quando a melhor solução não melhora por esse número de iterações) e *Solução inicial* (a do guloso ou aleatória). A busca para no critério que vier primeiro, e pelo menos um deles precisa estar ativo. No Simulated Annealing, os avançados incluem ainda *Temperatura inicial* (em branco, é estimada), *Resfriamento* (geométrico ou linear), *Taxa de resfriamento*, *Iterações por temperatura* e *Temperatura mínima*, em que a busca para; a aba **Execução** mostra, por faixa, as temperaturas inicial e final e as pioras aceitas. Na Busca Tabu, os avançados incluem *Permanência na lista tabu* e *APs avaliados por iteração*, e a aba **Execução** mostra os movimentos avaliados, os proibidos e os aceitos por aspiração. No Algoritmo genético, *População* é comum, e os avançados são *Gerações*, *Gerações sem melhora*, *Fração gulosa da população inicial*, *Cruzamento* (uniforme ou de um ponto), *Taxa de cruzamento*, *Taxa de mutação*, *Tamanho do torneio* e *Elite*; cada iteração é uma geração, e a curva de convergência usa gerações no eixo horizontal. O Algoritmo genético híbrido tem os mesmos parâmetros e mais *Busca local em* (descendentes ou melhores da geração), *Indivíduos refinados*, *Frequência da busca local* e *Profundidade da busca local*.

Clique em **Executar análise**, ao fim da coluna. Valores fora do intervalo aceito são indicados acima do botão, e a análise não é iniciada. Durante a execução, a página mostra a aba **Grafos**, com o progresso sobre o grafo da proposta, que indica a faixa em processamento; a execução pode ser cancelada enquanto estiver em andamento. Ao terminar, a página passa para a aba **Resumo**.

APs de faixas diferentes não interferem entre si: a análise monta um grafo para cada faixa, sem arestas entre faixas, e resolve cada um separadamente.

Os detalhes das estratégias e dos parâmetros aceitos pela API estão em [services/analysis_service/README.pt-BR.md](../../services/analysis_service/README.pt-BR.md).

## 3. Ler o Resultado

O resultado fica em cinco abas. A página abre na aba **Resumo**, que, antes da primeira análise, mostra a configuração atual: número de APs e de faixas, sobreposições (arestas do grafo), conflitos, interferência total e consumo no período, no total e por faixa, com as mesmas definições usadas no resultado. A aba **Grafos** já mostra o grafo da configuração original, enquadrado ao ser aberta.

- **Resumo:** a linha de abertura traz a estratégia, o critério, o tempo de execução, se a solução é ótima e a energia estimada do processamento (o tempo de CPU da análise multiplicado pela potência por núcleo; ver [docs/energy](../energy/README.pt-BR.md)); os cartões trazem os valores calculados pelo analysis_service:
  - *Conflitos*: arestas em conflito (em vermelho) antes e depois da otimização;
  - *Interferência total*: soma da interferência (w·s) das arestas em conflito, antes e depois;
  - *APs alterados*: quantos APs tiveram canal, largura de banda ou faixa alterados;
  - *Consumo*: estimativa de energia antes e depois, no número de dias do campo *Dias da estimativa de consumo*, no alto da aba.

  Cada variação aparece em verde, com ▼, quando melhora, e em vermelho, com ▲, quando piora; nas quatro métricas, valores menores são melhores. Abaixo dos cartões, a tabela **Resultados por faixa** traz, para cada faixa, os APs, o número de perfis (k), os conflitos, a interferência, a potência e a solução.
- **Grafos:** *Configuração original* e *Configuração proposta* ficam lado a lado em telas muito largas e empilhados nas demais. Os APs são posicionados pelas suas coordenadas, na mesma posição nos dois grafos, e o zoom e o deslocamento feitos em um grafo são replicados no outro; **Reenquadrar** volta a exibir os grafos inteiros. Acima de cada grafo, aparecem a estimativa de energia (kWh) e o custo (R$, a R$ 0,72 por kWh) no período escolhido no Resumo; a potência de cada AP é calculada pelo analysis_service com o modelo de Dembélé et al. (2023), pela faixa e pela largura de banda, e APs a 160 MHz ou em 6 GHz, que não têm valor no modelo, ficam fora da soma. A legenda fica abaixo de cada grafo. Cada configuração de canal, largura e faixa tem uma cor e uma forma de nó (círculo, quadrado, triângulo, losango ou hexágono), as mesmas nos dois grafos; a legenda mostra a amostra com a cor e a forma, o número de APs e a configuração. Cada aresta liga dois APs cujas áreas de cobertura se sobrepõem:
  - em **vermelho**, mais grossa, quando os dois APs estão em conflito na configuração exibida, com a interferência em porcentagem;
  - em **cinza-claro** quando há apenas sobreposição, sem conflito, com a porcentagem de sobreposição. Em grafos com muitas arestas, esses rótulos ficam ocultos; use *Mostrar pesos das arestas sem conflito*, no alto da aba, para exibi-los.

  No grafo otimizado, os APs cuja configuração mudou ganham borda escura, e os conflitos do grafo original resolvidos pela estratégia aparecem tracejados e atenuados. A legenda informa quantos APs mudaram e quantos conflitos foram resolvidos. Desmarque *Destacar mudanças no grafo otimizado* para ocultar esses destaques.

  Em redes grandes (mais de 2.000 arestas), os grafos são exibidos de forma simplificada, sem as arestas de simples sobreposição e sem rótulos, e um aviso no alto da aba informa isso. **Exibir o grafo completo** desenha todas as arestas e rótulos, o que pode deixar a página lenta; **Voltar à exibição simplificada** desfaz a escolha. O resumo, as configurações e a execução não mudam. Com 1.000 APs e cerca de 41 mil arestas, o resultado aparece em cerca de 1 s depois da resposta do serviço.
- **Convergência:** a curva da melhor solução ao longo da busca, produzida pelas metaheurísticas, com um gráfico por faixa. O eixo vertical é o primeiro critério do objetivo (conflitos, ou potência em *Energia primeiro*), e o horizontal, à escolha, as iterações em escala logarítmica (padrão, que mostra as melhoras do início, onde costumam se concentrar), as iterações em escala linear ou o tempo. A curva é em degraus: o valor só muda quando a busca encontra uma solução melhor, marcada por um ponto. Passe o mouse sobre o gráfico para ver a melhor solução até aquele ponto (iteração, tempo, conflitos, interferência e potência), e use *Ver os pontos da curva* para a tabela. O backtracking e o guloso não produzem a curva, e a aba informa isso.
- **Configurações:** canal, largura de banda e faixa atuais e propostos de cada AP. **Editar** permite trocar a configuração proposta, escolhida em listas com os canais marcados na etapa **Canais**; ao salvar, o AP fica travado nessa configuração e a análise otimizada é refeita.
- **Execução:** os metadados da execução e o botão **Repetir com a mesma configuração**, que executa de novo a análise exibida com a mesma estratégia, critério, canais e parâmetros, mesmo que a coluna lateral tenha mudado depois. Nas estratégias com semente (as metaheurísticas), o botão passa a **Repetir com a mesma semente**, a aba mostra a semente usada, e a repetição reproduz o resultado, exceto quando a busca para pelo limite de tempo, que depende da velocidade da máquina (para reproduzir com certeza, use os limites de iterações). Os metadados são:
  - *Estratégia* e *Critério de otimização*: a estratégia e o critério usados;
  - *Arestas*: pares de APs com sobreposição de cobertura na mesma faixa, com ou sem conflito;
  - *Conflitos (antes / depois)*: pares de APs em conflito (interferência maior que zero) antes e depois da otimização;
  - *Densidade de conflitos (antes / depois)*: fração dos pares possíveis de APs que estão em conflito;
  - *Solução*: se a configuração é ótima, se a busca parou no limite de tempo ou se foi cancelada;
  - *Conflitos (guloso / final)*: no backtracking, conflitos da solução inicial gulosa e da solução final; nas metaheurísticas, *Conflitos (solução inicial / final)*;
  - *Iterações*: nas metaheurísticas, iterações executadas, somadas as faixas;
  - *Nós explorados*: tamanho da busca realizada;
  - *Processamento (energia estimada)*: o tempo de CPU da análise e a energia estimada, com a potência por núcleo usada e o valor no turbo máximo; cada faixa traz os seus;
  - *Parâmetros*: os parâmetros usados, com a semente nas metaheurísticas;
  - *Faixa*: uma linha por faixa, com APs, arestas, número de perfis (k), conflitos e se a solução da faixa é ótima. Os demais metadados somam as faixas.

## 4. Configurar o Zabbix

As configurações abrem pelo ícone de engrenagem na barra de navegação, em qualquer página, e recebem a URL da API do Zabbix, o usuário e a senha. Use **Testar conexão** antes de **Salvar**. O endereço `/settings` leva à tela inicial com as configurações abertas. As credenciais ficam armazenadas no banco SQLite do `access_point_service`.

## 5. Experimentos

A página **Experimentos** (card na tela inicial, `/experiments`) tem dois modos, escolhidos no alto: **Comparação**, que compara as estratégias sobre a infraestrutura cadastrada, e **Escalabilidade**, que mede até que tamanho de rede cada estratégia resolve o problema. O endereço anterior, `/scalability`, abre o modo Escalabilidade. Os dois modos usam os mesmos campos de semente, limite de tempo, repetições, threads, critério de otimização, canais e estratégias, com os parâmetros de cada uma, e as execuções ficam no mesmo **Histórico de execuções**.

### Comparação

A página de Análise tem o atalho **Comparar estratégias nesta infraestrutura**, que abre este modo.

1. Escolha as estratégias, os parâmetros de cada uma, as **repetições** das estocásticas, o critério e os canais. A instância são os APs cadastrados com coordenadas, os mesmos da página de Análise; a quantidade aparece acima do formulário. Uma cópia deles é guardada quando a comparação começa, então editar os APs depois não muda o resultado nem a proposta guardada.
2. Clique em **Executar experimento**. Todas as estratégias rodam sobre os mesmos APs, com o mesmo critério, os mesmos canais e, nas estocásticas, as mesmas sementes: a repetição 1 de cada estratégia usa a mesma semente, a 2 também, e assim por diante.
3. A tabela **Resultados por estratégia** traz, para cada uma, as repetições, os conflitos, a interferência, a potência, os APs alterados, o tempo, a energia estimada do processamento e o motivo da parada. Nas estocásticas, cada valor é a média ± o desvio-padrão das repetições. O melhor valor de cada métrica (o menor) fica em negrito. O gráfico **Comparação por métrica** mostra a métrica escolhida em barras, com a média e um traço do melhor ao pior valor.
4. **Abrir na Análise** abre, na página de Análise, a configuração proposta da melhor repetição da estratégia (a de menos conflitos e, no empate, menor interferência; em *Energia primeiro*, a de menor potência), com os grafos, o resumo, as configurações e a execução, como numa análise normal. Um aviso no alto da página indica que é a proposta de uma comparação, feita com os APs de quando ela rodou. As demais repetições podem ser reproduzidas pela semente, que está no CSV; **Repetir com a mesma semente** roda de novo a repetição aberta.

O CSV e o JSON trazem uma linha por repetição, como no modo Escalabilidade.

### Escalabilidade

O modo **Escalabilidade** mede até que tamanho de rede cada estratégia resolve o problema. Ele gera uma topologia pela semente, com o tamanho máximo, e analisa prefixos dela de tamanho crescente (os primeiros 10 APs, os primeiros 20, ...), de modo que cada instância contém a anterior. Nada é salvo no inventário de APs, e os grafos não são desenhados.

1. Informe o **tamanho máximo** (até 1.000 APs), o **passo**, o **grau mínimo**, a **semente** (em branco, uma é sorteada), o **limite de tempo**, as **threads**, o **critério de otimização** as **repetições** e as **estratégias**. O limite de tempo e as threads valem para todas as estratégias; os demais parâmetros de cada uma (iterações, temperatura, população...) ficam em **Parâmetros**, abaixo dela, com os mesmos campos da página de Análise. As estratégias estocásticas (as metaheurísticas, que usam semente) são executadas o número de **repetições** em cada tamanho, com sementes derivadas da semente do teste: a repetição 1 usa a mesma semente em todas as estratégias e tamanhos, a repetição 2 também, e assim por diante, o que permite repetir o teste e comparar as estratégias nas mesmas condições. O backtracking e o guloso, que são determinísticos, rodam uma vez. Os canais são os perfis padrão, ou os escolhidos em **Escolher no mapa do espectro**, o mesmo mapa da página de Análise. O critério aparece nos parâmetros de cada execução do histórico e na coluna `objective` do CSV.
2. Clique em **Executar experimento**. O progresso mostra o tamanho e a estratégia em análise, e a execução pode ser cancelada. Só uma execução roda por vez, para que os tempos medidos não se misturem.
3. Para cada tamanho, as estratégias exatas rodam primeiro. Uma estratégia **quebra** no primeiro tamanho em que deixa de resolver o problema: um método exato (o backtracking), quando não encontra o ótimo dentro do limite de tempo, que vale para cada faixa; um método determinístico sem garantia de ótimo (o guloso), quando excede o limite de tempo; uma estratégia estocástica, quando a maioria das repetições para pelo limite de tempo antes dos próprios critérios de parada (iterações, iterações sem melhora ou temperatura mínima). Por isso, para medir uma metaheurística, deixe os critérios dela ativos e use o limite de tempo como teto: com só o limite de tempo, ela quebra no primeiro tamanho. Depois de quebrar, ela não é mais executada nos tamanhos seguintes, e o teste termina quando todas quebram ou o tamanho máximo é atingido.

O resultado mostra o ponto de quebra de cada estratégia e dois gráficos em função do número de APs: o tempo de execução, em escala logarítmica, com a linha do limite de tempo, e os conflitos após a otimização. O ponto de quebra aparece como um X. A **Tabela dos pontos medidos** traz, para cada tamanho e estratégia, as arestas, a densidade, o tempo, os conflitos, a distância até o ótimo (enquanto o método exato o encontra), a interferência, a potência, os nós explorados, a energia estimada do processamento e o motivo da parada. Nas estratégias estocásticas, os gráficos mostram a média das repetições, com uma faixa sombreada do melhor ao pior valor, e a tabela traz o número de repetições e a média ± o desvio-padrão. O CSV traz uma linha por repetição e também, nas últimas colunas, o tempo de CPU (`cpu_seconds`), a energia estimada (`processing_energy_j` e `processing_max_energy_j`), a repetição (`repetition`) e a semente usada (`seed`, vazia nas determinísticas).

Cada execução fica no **Histórico de execuções** com a data, os parâmetros e a versão do PowerTrackZ (commit, branch e, quando houver, a tag), o que permite repetir o teste em outra versão e comparar os resultados. **Ver** abre os gráficos de uma execução, **CSV** e **JSON** baixam os pontos medidos, e **Excluir** remove a execução. Uma execução interrompida pela reinicialização do serviço fica registrada como **Interrompida**.
