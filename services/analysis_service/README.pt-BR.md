# Analysis Service

[English](README.md) | **Português**

Serviço em C que monta o grafo de colisões entre pontos de acesso e indica a configuração de canal e largura de banda de cada um.

## Estratégias

| Estratégia | Descrição |
|---|---|
| `backtracking` | Busca exata por *branch-and-bound*. Minimiza, nesta ordem, o número de conflitos, a interferência total e o inverso da largura de banda somada. |
| `greedy` | Visita os APs em ordem decrescente de grau e atribui a cada um o perfil de menor interferência local. É também a solução inicial da busca exata. |
| `genetic` | Ainda não implementada (retorna um *placeholder*). |

## Parâmetros

Cada estratégia declara seus parâmetros em `src/strategies/strategy.c`. Eles são enviados em `parameters` no corpo da requisição:

| Estratégia | Parâmetro | Tipo | Padrão | Intervalo | Descrição |
|---|---|---|---|---|---|
| `backtracking` | `thread_count` | inteiro | `1` | 1 a 256 | Número de *threads* da busca. |
| `backtracking` | `time_limit_seconds` | número | `60` | 0 a 3600 | Tempo máximo da busca em cada faixa, em segundos. `0` desativa o limite. |

As estratégias `greedy` e `genetic` não têm parâmetros configuráveis.

`GET /strategies` descreve esses parâmetros em `strategy_details`, com nome, rótulo, tipo, padrão, limites, unidade e se o valor `0` desativa o recurso. A interface monta os campos a partir dessa descrição, de modo que um parâmetro novo precisa ser declarado apenas no serviço.

Valores fora do tipo ou do intervalo declarado são recusados com HTTP 400 e uma mensagem como `Parametro time_limit_seconds deve estar entre 0 e 3600`. Parâmetros que a estratégia não declara são ignorados. Os valores efetivamente usados aparecem em `execution.parameters`; o número de *threads* é limitado ao número de APs do grafo.

A resposta traz em `execution.search` se a solução é ótima (`optimal`), o motivo da parada (`completed`, `time_limit` ou `cancelled`), os nós explorados e os conflitos da solução gulosa e da final.

## Interferência

A interferência entre dois APs é o produto da sobreposição espacial das coberturas (w, em porcentagem da menor área) pela sobreposição espectral dos canais (s, de 0 a 1); há conflito quando o produto é maior que zero. O fator s é a fração da largura do canal mais estreito que se sobrepõe ao outro, com cada canal ocupando a sua largura em torno da frequência central.

Em canais agregados, a frequência central é a do bloco inteiro, e não a do canal primário: 36 a 80 MHz ocupa os canais 36 a 48, com centro no canal 42 (5210 MHz); 44 a 40 MHz ocupa 44 e 48, com centro no 46 (5230 MHz). Em 2,4 GHz, o secundário de um canal de 40 MHz fica 4 canais acima do primário quando cabe na faixa (primários 1 a 9) e 4 canais abaixo nos demais; assim, 1 a 40 MHz tem centro no canal 3 (2422 MHz) e 11 a 40 MHz, no canal 9 (2452 MHz).

## Consumo de Energia

A potência de cada AP segue o modelo de Dembélé et al. (2023): a potência média de um AP transmitindo a 25 Mbps, pela faixa e pela largura de banda. Os valores ficam em `POWER_MODEL`, em `src/analysis_service.c`:

| Faixa | 20 MHz | 40 MHz | 80 MHz |
|---|---|---|---|
| 2,4 GHz | 14,5 W | 13,8 W | — |
| 5 GHz | 11,1 W | 10,3 W | 9,9 W |

Configurações fora da tabela (160 MHz e 6 GHz) não têm valor no modelo e ficam fora das somas. Cada nó de `graph_data.nodes` traz `power_w` (configuração atual) e `proposed_power_w` (configuração proposta), nulos fora do modelo; `graph_data` traz `power_w`, o total da configuração exibida, e `power_unmodeled_nodes`. Em `execution.comparison` e em cada faixa de `execution.bands`, `power_before_w` e `power_after_w` dão o total antes e depois da otimização, e `power_unmodeled_before` e `power_unmodeled_after`, os APs fora do modelo. A conversão para energia e custo no período escolhido é feita pela interface.

## Grafo por Faixa e Canais Disponíveis

APs de faixas diferentes não interferem (s = 0), então o grafo não tem arestas entre faixas: ele é a união dos grafos de 2,4, 5 e 6 GHz. As rotas de análise resolvem cada faixa separadamente, em sequência, cada uma com o próprio limite de tempo. APs de faixa desconhecida ficam fora da busca e mantêm a configuração.

O campo `channels` da requisição define os perfis (o k de cada grafo) no mesmo formato de `profiles` em `GET /channel-plan`, por exemplo `{"2.4 GHz": {"20 MHz": ["1", "6", "11"]}}`. Cada combinação é validada contra `valid`, e uma faixa informada precisa de ao menos um canal; caso contrário, a resposta é HTTP 400. As faixas não informadas usam os perfis padrão.

A resposta traz em `execution.bands` uma entrada por faixa, com `frequency`, `nodes`, `edges`, `density`, `profile_count`, `comparison` e `search`. Os campos `execution.search` e `execution.comparison` consolidam as faixas: conflitos, interferência, largura de banda e nós explorados são somados, e a solução só é ótima se todas as faixas forem. Em `comparison`, `conflicts_before` e `conflicts_after` contam as arestas em conflito (w·s > 0) na configuração atual e na proposta, `conflict_density_before` e `conflict_density_after` dão a fração dos pares possíveis de APs em conflito, `interference_before` e `interference_after`, a soma de w·s dessas arestas, e `changed_nodes`, quantos APs tiveram a configuração alterada; `edges`, por sua vez, conta todas as sobreposições de cobertura, com ou sem conflito.

## Plano de Canais

`GET /channel-plan` informa os canais oferecidos pela interface, agrupados por frequência e largura de banda:

- `valid`: todos os canais permitidos no Brasil. Em 2,4 GHz, os canais 1 a 13, a 20 e 40 MHz (qualquer canal pode ser o primário de um canal de 40 MHz). Em 5 GHz (36 a 64, 100 a 144 e 149 a 165) e em 6 GHz (1 a 233), os canais de 40, 80 e 160 MHz agregam blocos alinhados de 2, 4 e 8 canais, e um canal só aparece numa largura quando o bloco inteiro existe. Os trechos ficam em `CHANNEL_SEGMENTS`, em `src/analysis_service.c`.
- `profiles`: os perfis padrão das estratégias, usados nas faixas que a requisição não informa em `channels`, lidos de `CONFIG_PROFILES`, em `src/strategies/backtracking.c`.
- `options`: as opções para escolher os perfis de busca, uma por posição distinta no espectro, com os canais que ela ocupa (`channels`), o primário enviado em `channels` da requisição (`channel`) e o intervalo que ocupa no espectro (`lower_mhz` e `upper_mhz`), usado no mapa do espectro da interface. Em 5 e 6 GHz, cada bloco agregado é uma opção (a 80 MHz em 5 GHz, 36–48, 52–64, 100–112, 116–128, 132–144 e 149–161); em 2,4 GHz, cada canal de 20 MHz e cada par de 40 MHz, de 1+5 a 9+13. O primário é o do perfil padrão quando ele cai no bloco (o par 7+11 envia o 11) e, nos demais, o primeiro canal do bloco.

## Paralelismo

A busca começa pela solução gulosa, que serve de limite para a poda. Os dois primeiros níveis livres da árvore são expandidos em tarefas, consumidas por *pthreads* a partir de uma fila compartilhada. A melhor solução é compartilhada entre as *threads* sob *mutex*, e cada *thread* mantém uma cópia local atualizada por um contador de versão, o que evita travar o *mutex* a cada nó.

Em empate de custo, vence a tarefa de menor índice. Como as tarefas seguem a ordem da busca sequencial, o resultado é o mesmo para qualquer número de *threads*.

## Limitações

- O problema é NP-difícil. Em grafos grandes e densos, a busca exata não termina e para no limite de tempo, devolvendo a melhor solução encontrada (`optimal: false`).
- O ganho com mais *threads* depende do número de tarefas e da eficácia da poda. Com poucos perfis por faixa, os dois primeiros níveis geram no máximo 25 tarefas em 2,4 GHz e 100 em 5 GHz.
- O progresso enviado ao *frontend* é a fração de tarefas concluídas, e não uma estimativa do tempo restante.
- Conflitos entre dois APs travados não entram no custo, pois não dependem da atribuição.
