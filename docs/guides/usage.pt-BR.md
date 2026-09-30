# Guia de Uso

[English](usage.md) | **Português**

Este guia descreve o fluxo principal da interface: carregar pontos de acesso, salvá-los no banco e analisar as configurações de canal. A instalação está descrita em [installation.pt-BR.md](installation.pt-BR.md).

## 1. Sua Infraestrutura

A página **Sua infraestrutura** (menu **Infraestrutura**, `/infrastructure`) reúne a lista e o mapa dos APs salvos no banco. Os endereços antigos `/hosts` e `/register` redirecionam para ela.

### Carregar APs

O botão **Carregar APs** abre uma janela com três origens:

- **Zabbix:** lista os APs monitorados pelo Zabbix configurado (ver seção 4). O Zabbix não informa coordenadas; APs já salvos mantêm as coordenadas do inventário.
- **Importar JSON:** lê um arquivo com uma lista de APs ou um objeto com a chave `aps`, como o produzido pela opção abaixo.
- **Gerar topologia:** cria APs aleatórios já posicionados. Os parâmetros são:
  - *Quantidade de nós*: número de APs, entre 2 e 1000;
  - *Grau mínimo*: número mínimo de vizinhos perto dos quais cada AP é posicionado, menor que a quantidade de nós. Essas ligações servem só para posicionar os APs; o grafo analisado é montado depois, pela sobreposição das coberturas na mesma faixa, e costuma ser bem mais denso;
  - *Semente* (opcional): inteiro entre 0 e 4294967295. A mesma semente, com os mesmos parâmetros e a mesma versão do PowerTrackZ, gera a mesma topologia; em branco, uma semente é sorteada. A semente usada aparece na revisão, no nome do arquivo baixado e no campo `metadata.seed` do JSON.

Os APs carregados aparecem para revisão, ainda sem salvar; os que não têm coordenadas ficam destacados em vermelho. Acima da lista, a revisão mostra as métricas do grafo que será analisado (APs, arestas, grau médio, grau máximo e densidade, no total e por faixa), úteis para descrever as instâncias de um experimento. **Baixar JSON** grava a lista em um arquivo, útil para repetir um experimento com a mesma topologia (que também pode ser recriada pela semente). **Salvar** grava os APs no banco: APs com o mesmo `id` de um AP salvo são atualizados, e os demais são criados.

### Editar o inventário

- **Adicionar:** clique no mapa para marcar a posição e use o botão **+** para informar descrição, frequência, largura de banda e canal.
- **Editar:** o ícone ao lado de cada AP abre seus dados; as coordenadas também podem ser ajustadas clicando no mapa com a janela aberta.
- **Excluir:** marque os APs e clique em **Excluir Selecionados**.

Ao adicionar ou editar um AP, frequência, largura de banda e canal são escolhidos em listas com os canais permitidos no Brasil (2,4 GHz: canais 1 a 13; 5 GHz: 36 a 64, 100 a 144 e 149 a 165; 6 GHz: 1 a 233). As larguras oferecidas dependem da frequência, e os canais, da frequência e da largura; ao trocar a frequência ou a largura, os campos seguintes passam a um valor válido. Um AP salvo com uma configuração fora dessas listas abre com os campos por selecionar.

Na lista, APs sem coordenadas aparecem em vermelho. Somente APs com coordenadas participam da análise.

## 2. Analisar

A página **Análise** (menu **Análise**, `/analysis`) monta o grafo de colisões entre os APs salvos e indica uma nova configuração para cada um.

1. Clique na estratégia desejada. A página passa a exibir os parâmetros dessa estratégia:
   - **Backtracking:** busca exata. Com poucos APs, devolve a configuração ótima; em redes grandes, para no limite de tempo e devolve a melhor configuração encontrada até ali. Parâmetros:
     - *Threads*: número de threads que dividem a busca, limitado ao número de APs;
     - *Limite de tempo (s)*: 60 s por padrão, até 3600 s, aplicado a cada faixa. Marque *Sem limite* para deixar a busca terminar por completo.
   - **Greedy:** heurística rápida, adequada a redes grandes, sem garantia de ótimo. Não possui parâmetros.
   - **Genetic:** ainda não implementada; devolve a configuração atual.
2. Em **Canais disponíveis por faixa**, abra cada faixa para ver o mapa do espectro: uma linha por largura de banda e, em cada linha, uma barra por opção, na posição e com a largura que ela ocupa no eixo de frequência. Clique nas barras para escolher os canais que as estratégias podem usar. A 40 MHz, cada barra é um par de primário e secundário, rotulado pelos dois canais (como 7+11); nas demais larguras, o rótulo é o canal primário, e a 80 e 160 MHz cada barra é um bloco de canais (como 36–48 a 80 MHz). A dica da barra mostra os canais, o primário enviado e o intervalo em MHz. Barras que se sobrepõem no eixo interferem entre si, e as marcadas que se sobrepõem a outra marcada da mesma largura ficam em laranja. Os atalhos **Padrão**, **Todos** e **Nenhum** marcam conjuntos prontos, e os de **Sem sobreposição** marcam uma única largura, com o maior conjunto de canais que não se sobrepõem (em 2,4 GHz, 1, 5, 9 e 13 a 20 MHz), desmarcando as demais. O resumo de cada faixa mostra o total de perfis (k), e cada largura, a sua parte. Os perfis padrão já vêm marcados; em 2,4 e 5 GHz é preciso manter ao menos um canal, e a faixa de 6 GHz começa vazia, com seus APs mantendo a configuração atual.
3. Ajuste os parâmetros e clique em **Executar análise**. Valores fora do intervalo aceito são indicados abaixo dos campos, e a análise não é iniciada.
4. Acompanhe o progresso no grafo da direita, que indica a faixa em processamento. A execução pode ser cancelada enquanto estiver em andamento.

APs de faixas diferentes não interferem entre si: a análise monta um grafo para cada faixa, sem arestas entre faixas, e resolve cada um separadamente.

Os detalhes das estratégias e dos parâmetros aceitos pela API estão em [services/analysis_service/README.pt-BR.md](../../services/analysis_service/README.pt-BR.md).

## 3. Ler o Resultado

- **Resumo:** acima dos grafos, aparece depois de cada análise, com os valores calculados pelo analysis_service:
  - *Conflitos*: arestas em conflito (em vermelho) antes e depois da otimização;
  - *Interferência total*: soma da interferência (w·s) das arestas em conflito, antes e depois;
  - *APs alterados*: quantos APs tiveram canal, largura de banda ou frequência alterados;
  - *Consumo*: estimativa de energia antes e depois, no número de dias informado;
  - *Estratégia*: tempo de execução e se a solução é ótima.

  Cada variação aparece em verde, com ▼, quando melhora, e em vermelho, com ▲, quando piora; nas quatro métricas, valores menores são melhores. Abaixo dos cartões, a tabela **Resultados por faixa** traz, para cada faixa, os APs, o número de perfis (k), os conflitos, a interferência, a potência e a solução.
- **Grafos:** *Configuração original* e *Configuração proposta* ficam lado a lado em telas largas e empilhados em telas estreitas. Os APs são posicionados pelas suas coordenadas, na mesma posição nos dois grafos, e o zoom e o deslocamento feitos em um grafo são replicados no outro; **Reenquadrar** volta a exibir os grafos inteiros. A legenda de cores e arestas fica abaixo de cada grafo. Cada aresta liga dois APs cujas áreas de cobertura se sobrepõem:
  - em **vermelho**, mais grossa, quando os dois APs estão em conflito na configuração exibida, com a interferência em porcentagem;
  - em **cinza-claro** quando há apenas sobreposição, sem conflito, com a porcentagem de sobreposição. Em grafos com muitas arestas, esses rótulos ficam ocultos; use *Mostrar pesos das arestas sem conflito* para exibi-los.

  No grafo otimizado, os APs cuja configuração mudou ganham borda escura, e os conflitos do grafo original resolvidos pela estratégia aparecem tracejados e atenuados. A legenda informa quantos APs mudaram e quantos conflitos foram resolvidos. Desmarque *Destacar mudanças no grafo otimizado* para ocultar esses destaques.
- **Tabela de configurações:** canal, largura de banda e frequência atuais e propostos de cada AP. **Editar** permite trocar a configuração proposta, escolhida em listas com os canais marcados em **Canais disponíveis por faixa**; ao salvar, o AP fica travado nessa configuração e a análise otimizada é refeita.
- **Consumo:** estimativa de energia (kWh) e custo (R$, a R$ 0,72 por kWh), acima de cada grafo, no período informado no campo *Dias da estimativa de consumo*. A potência de cada AP é calculada pelo analysis_service com o modelo de Dembélé et al. (2023), pela faixa e pela largura de banda; APs a 160 MHz ou em 6 GHz, que não têm valor no modelo, ficam fora da soma.
- **Metadados de Execução:**
  - *Arestas*: pares de APs com sobreposição de cobertura na mesma faixa, com ou sem conflito;
  - *Conflitos Antes / Depois*: pares de APs em conflito (interferência maior que zero) antes e depois da otimização;
  - *Densidade de Conflitos Antes / Depois*: fração dos pares possíveis de APs que estão em conflito;
  - *Solução*: se a configuração é ótima, se a busca parou no limite de tempo ou se foi cancelada;
  - *Conflitos Guloso / Final*: no backtracking, conflitos da solução inicial gulosa e da solução final;
  - *Nós Explorados*: tamanho da busca realizada;
  - *Parâmetros*: threads e limite de tempo usados;
  - *Faixa*: uma linha por faixa, com APs, arestas, número de perfis (k), conflitos e se a solução da faixa é ótima. Os demais metadados somam as faixas.

## 4. Configurar o Zabbix

As configurações abrem pelo ícone de engrenagem na barra de navegação, em qualquer página, e recebem a URL da API do Zabbix, o usuário e a senha. Use **Testar Conexão** antes de **Salvar**. O endereço `/settings` leva à tela inicial com as configurações abertas. As credenciais ficam armazenadas no banco SQLite do `access_point_service`.

## 5. Teste de Escalabilidade

A página **Teste de escalabilidade** (card na tela inicial, `/scalability`) mede até que tamanho de rede cada estratégia resolve o problema. Ela gera uma topologia pela semente, com o tamanho máximo, e analisa prefixos dela de tamanho crescente (os primeiros 10 APs, os primeiros 20, ...), de modo que cada instância contém a anterior. Nada é salvo no inventário de APs, e os grafos não são desenhados.

1. Informe o **tamanho máximo** (até 1.000 APs), o **passo**, o **grau mínimo**, a **semente** (em branco, uma é sorteada), o **limite de tempo**, as **threads** e as **estratégias**. Os canais usados são os perfis padrão.
2. Clique em **Executar teste**. O progresso mostra o tamanho e a estratégia em análise, e a execução pode ser cancelada. Só uma execução roda por vez, para que os tempos medidos não se misturem.
3. Para cada tamanho, as estratégias exatas rodam primeiro. Uma estratégia **quebra** no primeiro tamanho em que deixa de resolver o problema: um método exato (o backtracking), quando não encontra o ótimo dentro do limite de tempo, que vale para cada faixa; um método sem garantia de ótimo (o guloso), quando excede o limite de tempo. Depois de quebrar, ela não é mais executada nos tamanhos seguintes, e o teste termina quando todas quebram ou o tamanho máximo é atingido.

O resultado mostra o ponto de quebra de cada estratégia e dois gráficos em função do número de APs: o tempo de execução, em escala logarítmica, com a linha do limite de tempo, e os conflitos após a otimização. O ponto de quebra aparece como um X. A **Tabela dos pontos medidos** traz, para cada tamanho e estratégia, as arestas, a densidade, o tempo, os conflitos, a distância até o ótimo (enquanto o método exato o encontra), a interferência, a potência, os nós explorados e o motivo da parada.

Cada execução fica no **Histórico de execuções** com a data, os parâmetros e a versão do PowerTrackZ (commit, branch e, quando houver, a tag), o que permite repetir o teste em outra versão e comparar os resultados. **Ver** abre os gráficos de uma execução, **CSV** e **JSON** baixam os pontos medidos, e **Excluir** remove a execução. Uma execução interrompida pela reinicialização do serviço fica registrada como **Interrompida**.
