# Guia de Uso

Este guia descreve o fluxo principal da interface: carregar pontos de acesso, salva-los no banco e analisar as configuracoes de canal. A instalacao esta descrita em `installation.md`.

## 1. Carregar Pontos de Acesso

A pagina **Pontos de Acesso** (menu **Pontos**, `/hosts`) mostra os APs carregados, ainda sem salvar no banco. Ha tres formas de carrega-los:

- **Zabbix:** quando a conexao esta configurada (ver secao 4), a pagina lista os APs monitorados pelo Zabbix externo.
- **Importar JSON:** carrega um arquivo com APs e ligacoes, como o produzido pela opcao abaixo. A importacao substitui a lista carregada.
- **Gerar JSON:** cria uma topologia aleatoria e baixa o arquivo correspondente. Os parametros sao:
  - *Quantidade de nos*: numero de APs, entre 2 e 500;
  - *Fator de clique*: numero minimo de vizinhos que cada AP tenta manter, menor que a quantidade de nos.

  O arquivo gerado nao e carregado automaticamente: use **Importar JSON** em seguida.

Depois de conferir a lista, clique em **Salvar** para gravar os APs no banco. Somente APs com coordenadas participam da analise.

A pagina **Registrar** (`/register`) permite cadastrar e editar um AP manualmente, informando latitude, longitude, frequencia, largura de banda e canal.

## 2. Analisar

A pagina **Analise** (`/analysis`) monta o grafo de colisoes entre os APs salvos e indica uma nova configuracao para cada um.

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

- **Grafos:** o primeiro mostra a configuracao atual e o segundo, a proposta. Os APs sao posicionados pelas suas coordenadas, na mesma posicao nos dois grafos. Cada aresta liga dois APs cujas areas de cobertura se sobrepoem:
  - em **vermelho**, mais grossa, quando os dois APs estao em conflito na configuracao exibida, com a interferencia em porcentagem;
  - em **cinza claro** quando ha apenas sobreposicao, sem conflito, com a porcentagem de sobreposicao. Em grafos com muitas arestas, esses rotulos ficam ocultos; use *Mostrar pesos das arestas sem conflito* para exibi-los.
- **Tabela de configuracoes:** canal, largura de banda e frequencia atuais e propostos de cada AP.
- **Consumo:** estimativa de energia (kWh) e custo (R$) no periodo informado no campo *Dias*.
- **Metadados de Execucao:**
  - *Arestas Antes / Depois*: pares de APs em conflito antes e depois da otimizacao;
  - *Solucao*: se a configuracao e otima, se a busca parou no limite de tempo ou se foi cancelada;
  - *Conflitos Guloso / Final*: no backtracking, conflitos da solucao inicial gulosa e da solucao final;
  - *Nos Explorados*: tamanho da busca realizada;
  - *Parametros*: threads e limite de tempo usados.

## 4. Configurar o Zabbix

As configuracoes abrem pelo icone de engrenagem na barra de navegacao, em qualquer pagina, e recebem a URL da API do Zabbix, o usuario e a senha. Use **Testar Conexao** antes de **Salvar**. O endereco `/settings` leva a tela inicial com as configuracoes abertas. As credenciais ficam armazenadas no banco SQLite do `access_point_service`.
