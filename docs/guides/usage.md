# Guia de Uso

Este guia descreve o fluxo principal da interface: carregar pontos de acesso, salva-los no banco e analisar as configuracoes de canal. A instalacao esta descrita em `installation.md`.

## 1. Sua Infraestrutura

A pagina **Sua infraestrutura** (menu **Infraestrutura**, `/infrastructure`) reune a lista e o mapa dos APs salvos no banco. Os enderecos antigos `/hosts` e `/register` redirecionam para ela.

### Carregar APs

O botao **Carregar APs** abre uma janela com tres origens:

- **Zabbix:** lista os APs monitorados pelo Zabbix configurado (ver secao 4). O Zabbix nao informa coordenadas; APs ja salvos mantem as coordenadas do inventario.
- **Importar JSON:** le um arquivo com uma lista de APs ou um objeto com a chave `aps`, como o produzido pela opcao abaixo.
- **Gerar topologia:** cria APs aleatorios ja posicionados. Os parametros sao:
  - *Quantidade de nos*: numero de APs, entre 2 e 500;
  - *Fator de clique*: numero minimo de vizinhos que cada AP tenta manter, menor que a quantidade de nos.

Os APs carregados aparecem para revisao, ainda sem salvar; os que nao tem coordenadas ficam destacados em vermelho. **Baixar JSON** grava a lista em um arquivo, util para repetir um experimento com a mesma topologia. **Salvar** grava os APs no banco: APs com o mesmo `id` de um AP salvo sao atualizados, e os demais sao criados.

### Editar o inventario

- **Adicionar:** clique no mapa para marcar a posicao e use o botao **+** para informar descricao, frequencia, largura de banda e canal.
- **Editar:** o icone ao lado de cada AP abre seus dados; as coordenadas tambem podem ser ajustadas clicando no mapa com a janela aberta.
- **Excluir:** marque os APs e clique em **Excluir Selecionados**.

Na lista, APs sem coordenadas aparecem em vermelho. Somente APs com coordenadas participam da analise.

## 2. Analisar

A pagina **Analise** (menu **Analise**, `/analysis`) monta o grafo de colisoes entre os APs salvos e indica uma nova configuracao para cada um.

1. Clique na estrategia desejada. A pagina passa a exibir os parametros dessa estrategia:
   - **Backtracking:** busca exata. Com poucos APs, devolve a configuracao otima; em redes grandes, para no limite de tempo e devolve a melhor configuracao encontrada ate ali. Parametros:
     - *Threads*: numero de threads que dividem a busca, limitado ao numero de APs;
     - *Limite de tempo (s)*: 60 s por padrao, ate 3600 s. Marque *Sem limite* para deixar a busca terminar por completo.
   - **Greedy:** heuristica rapida, adequada a redes grandes, sem garantia de otimo. Nao possui parametros.
   - **Genetic:** ainda nao implementada; devolve a configuracao atual.
2. Ajuste os parametros e clique em **Executar analise**. Valores fora do intervalo aceito sao indicados abaixo dos campos, e a analise nao e iniciada.
3. Acompanhe o progresso no grafo da direita. A execucao pode ser cancelada enquanto estiver em andamento.

Os detalhes das estrategias e dos parametros aceitos pela API estao em `services/analysis_service/README.md`.

## 3. Ler o Resultado

- **Grafos:** *Configuracao original* e *Configuracao proposta* ficam lado a lado em telas largas e empilhados em telas estreitas. Os APs sao posicionados pelas suas coordenadas, na mesma posicao nos dois grafos, e zoom e deslocamento feitos em um grafo sao replicados no outro; **Reenquadrar** volta a exibir os grafos inteiros. A legenda de cores e arestas fica abaixo de cada grafo. Cada aresta liga dois APs cujas areas de cobertura se sobrepoem:
  - em **vermelho**, mais grossa, quando os dois APs estao em conflito na configuracao exibida, com a interferencia em porcentagem;
  - em **cinza claro** quando ha apenas sobreposicao, sem conflito, com a porcentagem de sobreposicao. Em grafos com muitas arestas, esses rotulos ficam ocultos; use *Mostrar pesos das arestas sem conflito* para exibi-los.

  No grafo otimizado, os APs cuja configuracao mudou ganham borda escura, e os conflitos do grafo original resolvidos pela estrategia aparecem tracejados e atenuados. A legenda informa quantos APs mudaram e quantos conflitos foram resolvidos. Desmarque *Destacar mudancas no grafo otimizado* para ocultar esses destaques.
- **Tabela de configuracoes:** canal, largura de banda e frequencia atuais e propostos de cada AP.
- **Consumo:** estimativa de energia (kWh) e custo (R$), acima de cada grafo, no periodo informado no campo *Dias da estimativa de consumo*.
- **Metadados de Execucao:**
  - *Arestas Antes / Depois*: pares de APs em conflito antes e depois da otimizacao;
  - *Solucao*: se a configuracao e otima, se a busca parou no limite de tempo ou se foi cancelada;
  - *Conflitos Guloso / Final*: no backtracking, conflitos da solucao inicial gulosa e da solucao final;
  - *Nos Explorados*: tamanho da busca realizada;
  - *Parametros*: threads e limite de tempo usados.

## 4. Configurar o Zabbix

As configuracoes abrem pelo icone de engrenagem na barra de navegacao, em qualquer pagina, e recebem a URL da API do Zabbix, o usuario e a senha. Use **Testar Conexao** antes de **Salvar**. O endereco `/settings` leva a tela inicial com as configuracoes abertas. As credenciais ficam armazenadas no banco SQLite do `access_point_service`.
