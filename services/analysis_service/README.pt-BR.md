# Analysis Service

[English](README.md) | **Português**

Serviço em C que monta o grafo de conflitos entre pontos de acesso e indica a configuração de canal e largura de banda de cada um.

## Estratégias

| Estratégia | Descrição |
|---|---|
| `backtracking` | Busca exata por *branch-and-bound*. Minimiza o custo do critério de otimização (seção abaixo); no padrão, nesta ordem, o número de conflitos, a interferência total e o inverso da largura de banda somada. |
| `greedy` | Visita os APs em ordem decrescente de grau e atribui a cada um o perfil de menor custo incremental no critério de otimização (no padrão, o de menor interferência local). É também a solução inicial da busca exata. |
| `local_search` | Busca local sobre a base comum das metaheurísticas (seção abaixo): a cada iteração, troca o perfil de um AP sorteado e aceita a troca se ela não piorar a solução no critério de otimização. Não garante o ótimo; serve de referência para as metaheurísticas. |
| `genetic` | Ainda não implementada (retorna um *placeholder*). |

## Parâmetros

Cada estratégia declara seus parâmetros em `src/strategies/strategy.c`. Eles são enviados em `parameters` no corpo da requisição:

| Estratégia | Parâmetro | Tipo | Padrão | Intervalo | Descrição |
|---|---|---|---|---|---|
| `backtracking` | `thread_count` | inteiro | `1` | 1 a 256 | Número de *threads* da busca. |
| `backtracking` | `time_limit_seconds` | número | `60` | 0 a 3600 | Tempo máximo da busca em cada faixa, em segundos. `0` desativa o limite. |
| `local_search` | `seed` | inteiro, opcional | sorteada | 0 a 4294967295 | Semente do gerador aleatório. Sem valor, o serviço sorteia uma e a devolve em `execution.seed`. |
| `local_search` | `time_limit_seconds` | número | `10` | 0 a 3600 | Tempo máximo da busca em cada faixa, em segundos. `0` desativa o limite. |
| `local_search` | `max_iterations` | inteiro | `1000000` | 0 a 10⁹ | Número máximo de iterações em cada faixa. `0` desativa o limite. |
| `local_search` | `max_iterations_without_improvement` | inteiro | `100000` | 0 a 10⁹ | Para a busca na faixa depois deste número de iterações sem melhorar a melhor solução. `0` desativa o critério. |
| `local_search` | `initial_solution` | escolha | `greedy` | `greedy`, `random` | Solução inicial: a do guloso ou um perfil aleatório para cada AP. |

As estratégias `greedy` e `genetic` não têm parâmetros configuráveis. Na `local_search`, pelo menos um dos três critérios de parada precisa estar ativo; com os três desativados, a requisição é recusada com HTTP 400.

`GET /strategies` descreve esses parâmetros em `strategy_details`, com nome, rótulo, tipo (`integer`, `number` ou `choice`), padrão, limites, unidade, se o valor `0` desativa o recurso, se ele é avançado (`advanced`, exibido recolhido na interface) e se é opcional (`optional`, sem padrão: `default` vem nulo). Os parâmetros de escolha (`choice`) trazem as opções em `options` (`value` e `label`) e a opção padrão em `default`, sem `min` e `max`. Cada estratégia declara também a sua família (`family`: `exact`, `constructive` ou `metaheuristic`). A interface monta os campos e agrupa as estratégias a partir dessa descrição, de modo que um parâmetro ou uma estratégia nova precisa ser declarada apenas no serviço.

Valores fora do tipo ou do intervalo declarado, e opções que não estão na lista, são recusados com HTTP 400 e uma mensagem como `O parâmetro time_limit_seconds deve estar entre 0 e 3600.`. Parâmetros que a estratégia não declara são ignorados. Os valores efetivamente usados aparecem em `execution.parameters`; o número de *threads* é limitado ao número de APs do grafo, e a semente é a usada (informada ou sorteada).

A resposta traz em `execution.search` se a solução é ótima (`optimal`), o motivo da parada, os nós explorados, os conflitos da solução inicial e da final (`greedy_conflicts` e `conflicts`) e os componentes do custo da solução (`interference_score`, `bandwidth_score` e `power_score_w`). Os motivos da parada são `completed` (a busca terminou), `no_improvement` (iterações sem melhora), `iteration_limit` (limite de iterações), `time_limit` (limite de tempo) e `cancelled` (cancelamento); ao consolidar as faixas, vale o motivo de maior precedência, nesta mesma ordem. Nas metaheurísticas, `iterations` informa as iterações executadas, `nodes_explored` é igual a elas e `greedy_conflicts` são os conflitos da solução inicial, que pode ser a aleatória.

## Critério de Otimização

As estratégias comparam as soluções por uma ordem lexicográfica, escolhida no campo `objective` da requisição:

| `objective` | Ordem |
|---|---|
| `default` | menos conflitos → menor interferência → maior largura de banda somada |
| `energy_tiebreak` | menos conflitos → menor interferência → menor potência |
| `energy_first` | menor potência → menos conflitos → menor interferência |

Sem o campo, vale `default`, que reproduz os resultados das versões anteriores; um nome desconhecido é recusado com HTTP 400. `GET /strategies` lista os objetivos em `objectives` (nome, rótulo, descrição e ordem) e o padrão em `default_objective`, e a resposta da análise informa o objetivo usado em `execution.objective`.

A avaliação de custo fica em um ponto único, `src/strategies/objective.c`: o custo de uma atribuição (`AssignmentCost`), a comparação em cada ordem (`compare_assignment_costs`) e a potência usada no critério. O guloso escolhe, AP a AP, o perfil de menor custo incremental no objetivo, e o backtracking visita os perfis nessa mesma ordem. A poda do backtracking usa um limite otimista do ramo: conflitos e interferência só crescem, a largura soma no máximo a maior largura possível dos APs restantes e a potência soma no mínimo a menor potência possível deles. Como toda solução do ramo é, em cada componente, igual ou pior que esse limite, a poda é correta em qualquer ordem. A potência entra no custo em miliwatts inteiros, para que somas feitas por *threads* diferentes deem o mesmo valor e o resultado não dependa do número de *threads*.

No modelo de consumo, larguras maiores gastam menos potência. Por isso, `energy_tiebreak` costuma coincidir com `default` num AP isolado, mas diverge nas somas: dois APs sem conflito a 40 + 40 MHz somam 80 MHz e 20,6 W; a 80 + 20 MHz, 100 MHz e 21,0 W. `default` fica com a segunda solução, e `energy_tiebreak`, com a primeira. `energy_first` aceita conflitos para reduzir a potência.

**Configurações fora do modelo de consumo.** No critério de otimização, uma configuração sem valor no modelo (160 MHz) vale a maior potência modelada da sua faixa (11,1 W em 5 GHz), para que uma configuração sem estimativa nunca seja favorecida pela energia. Numa faixa sem nenhum valor no modelo (6 GHz), todos os perfis valem zero, e a energia deixa de diferenciá-los. A regra vale só para a otimização: os totais de potência da resposta continuam deixando essas configurações de fora.

## Base Comum das Metaheurísticas

As metaheurísticas usam as mesmas peças, em `src/strategies/metaheuristic.c`, para que a comparação com o backtracking e com o guloso dependa só do método, e não de diferenças de implementação. A busca local (`local_search.c`) é a referência que exercita essa base.

- **Representação.** A solução é um índice de perfil por AP, como no backtracking. Em cada faixa, só mudam os APs que não estão fixos e têm perfis da sua faixa; os APs travados num perfil disponível ficam fixos, com as mesmas regras do backtracking (`assignment.c`).
- **Custo.** O custo é o do critério de otimização (`AssignmentCost` e `compare_assignment_costs`, em `objective.c`), com as mesmas regras do custo incremental do backtracking e do guloso: conta as arestas em conflito com os dois lados definidos, exceto entre dois APs fixos, e soma a largura e a potência de cada AP atribuído. `meta_full_cost` recalcula o custo completo, e `meta_move_delta` calcula a variação ao trocar o perfil de um AP, em O(grau). Como a interferência é real, a soma incremental pode acumular erro de arredondamento ao longo de milhões de movimentos; por isso, o custo atual é recalculado por completo a cada 4.096 iterações, e uma solução só vira a melhor depois de o seu custo ser recalculado. Os testes em C conferem que a variação incremental coincide com o recálculo completo em 20.000 movimentos aleatórios, nos três objetivos.
- **Vizinhança.** O movimento básico é trocar o perfil de um AP; `meta_random_move` sorteia um AP móvel e um perfil permitido diferente do atual.
- **Solução inicial.** A do guloso (`greedy`, padrão) ou um perfil permitido aleatório para cada AP (`random`).
- **Parada.** A busca para pelo limite de tempo, pelo número máximo de iterações ou por um número de iterações sem melhorar a melhor solução, o que vier primeiro, e informa o motivo em `stop_reason`. Cada faixa tem os próprios limites.
- **Reprodutibilidade.** A aleatoriedade vem de um gerador próprio (xoshiro256\*\*, inicializado por splitmix64), e não do `rand()` da biblioteca C. A semente é a informada em `seed` ou uma sorteada, devolvida em `execution.seed` e em `execution.parameters.seed`; cada faixa usa uma sequência derivada da semente e do índice da faixa. A mesma semente, com os mesmos APs, canais, objetivo e parâmetros, produz o mesmo resultado. O limite de tempo é a exceção: uma busca que para pelo tempo depende da velocidade da máquina, então, para reproduzir uma execução, use o limite de iterações ou o de iterações sem melhora.
- **Curva de convergência.** Cada faixa de `execution.bands` traz em `convergence` a melhor solução ao longo da busca: um ponto na solução inicial, um a cada melhora e um no fim, com `iteration`, `time_ms`, `conflicts`, `interference`, `bandwidth` e `power_w`. A curva guarda no máximo 500 pontos por faixa; ao enchê-la, um ponto a cada dois é descartado, mantendo o primeiro.
- **Progresso e cancelamento.** Na rota com *streaming*, o progresso (`iteration`, `best_conflicts` e a fração concluída, a do critério de parada mais adiantado) é enviado a cada 0,2 s, e o cancelamento é conferido a cada 256 iterações.

Para criar uma metaheurística, declare os parâmetros comuns com as macros `META_SEED_PARAMETER`, `META_TIME_LIMIT_PARAMETER`, `META_MAX_ITERATIONS_PARAMETER`, `META_STAGNATION_PARAMETER` e `META_INITIAL_SOLUTION_PARAMETER`, use `meta_validate_parameters` na validação e siga o laço de `local_search.c`: `meta_run_begin`, `meta_run_next` a cada iteração, `meta_run_offer` quando a solução atual mudar e `meta_run_end` no fim. As comparações usam a ordem lexicográfica do objetivo (`compare_assignment_costs`); uma metaheurística que precise de uma diferença numérica de custo (como a aceitação do Simulated Annealing) deve documentar como a obtém sem violar essa ordem.

## Interferência

A interferência entre dois APs é o produto da sobreposição espacial das coberturas (w, em porcentagem da menor área) pela sobreposição espectral dos canais (s, de 0 a 1); há conflito quando o produto é maior que zero. O fator s é a fração da largura do canal mais estreito que se sobrepõe ao outro, com cada canal ocupando a sua largura em torno da frequência central.

Em canais agregados, a frequência central é a do bloco inteiro, e não a do canal primário: 36 a 80 MHz ocupa os canais 36 a 48, com centro no canal 42 (5210 MHz); 44 a 40 MHz ocupa 44 e 48, com centro no 46 (5230 MHz). Em 2,4 GHz, o secundário de um canal de 40 MHz fica 4 canais acima do primário quando cabe na faixa (primários 1 a 9) e 4 canais abaixo nos demais; assim, 1 a 40 MHz tem centro no canal 3 (2422 MHz) e 11 a 40 MHz, no canal 9 (2452 MHz).

## Consumo de Energia

A potência de cada AP segue o modelo de Dembélé et al. (2023): a potência média de um AP transmitindo a 25 Mbps, pela faixa e pela largura de banda. Os valores ficam em `POWER_MODEL`, em `src/strategies/objective.c`, e são usados tanto nos totais da resposta quanto no critério de otimização:

| Faixa | 20 MHz | 40 MHz | 80 MHz |
|---|---|---|---|
| 2,4 GHz | 14,5 W | 13,8 W | — |
| 5 GHz | 11,1 W | 10,3 W | 9,9 W |

Configurações fora da tabela (160 MHz e 6 GHz) não têm valor no modelo e ficam fora das somas. Cada nó de `graph_data.nodes` traz `power_w` (configuração atual) e `proposed_power_w` (configuração proposta), nulos fora do modelo; `graph_data` traz `power_w`, o total da configuração exibida, e `power_unmodeled_nodes`. Em `execution.comparison` e em cada faixa de `execution.bands`, `power_before_w` e `power_after_w` dão o total antes e depois da otimização, e `power_unmodeled_before` e `power_unmodeled_after`, os APs fora do modelo. A conversão para energia e custo no período escolhido é feita pela interface.

## Grafo por Faixa e Canais Disponíveis

O raio de cobertura de cada AP vem do campo `raio` (em metros); sem ele, vale o padrão da faixa: 20 m em 2,4 GHz, 15 m em 5 GHz e 12 m em 6 GHz, os mesmos valores da interface e do gerador. `POST /graph-metrics` devolve as métricas desse grafo (nós, arestas, densidade, grau médio e grau máximo, no total e por faixa) sem executar estratégia.

APs de faixas diferentes não interferem (s = 0), então o grafo não tem arestas entre faixas: ele é a união dos grafos de 2,4, 5 e 6 GHz. As rotas de análise resolvem cada faixa separadamente, em sequência, cada uma com o próprio limite de tempo. APs de faixa desconhecida ficam fora da busca e mantêm a configuração.

O campo `channels` da requisição define os perfis (o k de cada grafo) no mesmo formato de `profiles` em `GET /channel-plan`, por exemplo `{"2.4 GHz": {"20 MHz": ["1", "6", "11"]}}`. Cada combinação é validada contra `valid`, e uma faixa informada precisa de ao menos um canal; caso contrário, a resposta é HTTP 400. As faixas não informadas usam os perfis padrão.

A resposta traz em `execution.bands` uma entrada por faixa, com `frequency`, `nodes`, `edges`, `density`, `profile_count`, `comparison` e `search`. Os campos `execution.search` e `execution.comparison` consolidam as faixas: conflitos, interferência, largura de banda e nós explorados são somados, e a solução só é ótima se todas as faixas forem. Em `comparison`, `conflicts_before` e `conflicts_after` contam as arestas em conflito (w·s > 0) na configuração atual e na proposta, `conflict_density_before` e `conflict_density_after` dão a fração dos pares possíveis de APs em conflito, `interference_before` e `interference_after`, a soma de w·s dessas arestas, e `changed_nodes`, quantos APs tiveram a configuração alterada; `edges`, por sua vez, conta todas as sobreposições de cobertura, com ou sem conflito.

## Plano de Canais

`GET /channel-plan` informa os canais oferecidos pela interface, agrupados por frequência e largura de banda:

- `valid`: todos os canais permitidos no Brasil. Em 2,4 GHz, os canais 1 a 13, a 20 e 40 MHz (qualquer canal pode ser o primário de um canal de 40 MHz). Em 5 GHz (36 a 64, 100 a 144 e 149 a 165) e em 6 GHz (1 a 233), os canais de 40, 80 e 160 MHz agregam blocos alinhados de 2, 4 e 8 canais, e um canal só aparece numa largura quando o bloco inteiro existe. Os trechos ficam em `CHANNEL_SEGMENTS`, em `src/analysis_service.c`.
- `profiles`: os perfis padrão das estratégias, usados nas faixas que a requisição não informa em `channels`, lidos de `CONFIG_PROFILES`, em `src/strategies/backtracking.c`.
- `options`: as opções para escolher os perfis de busca, uma por posição distinta no espectro, com os canais que ela ocupa (`channels`), o primário enviado em `channels` da requisição (`channel`) e o intervalo que ocupa no espectro (`lower_mhz` e `upper_mhz`), usado no mapa do espectro da interface. Em 5 e 6 GHz, cada bloco agregado é uma opção (a 80 MHz em 5 GHz, 36–48, 52–64, 100–112, 116–128, 132–144 e 149–161); em 2,4 GHz, cada canal de 20 MHz e cada par de 40 MHz, de 1+5 a 9+13. O primário é o do perfil padrão quando ele cai no bloco (o par 7+11 envia o 11) e, nos demais, o primeiro canal do bloco.

## Perfis Padrão

Os perfis padrão (`CONFIG_PROFILES`, em `src/strategies/backtracking.c`) são usados nas faixas que a requisição não informa em `channels`:

| Faixa | 20 MHz | 40 MHz | 80 MHz | k |
|---|---|---|---|---|
| 2,4 GHz | 1, 6, 11 | 1 (1+5), 11 (7+11) | — | 5 |
| 5 GHz | 36, 44, 149, 157 | 36, 44, 149, 157 | 36, 149 | 10 |

A ordem da lista desempata perfis de mesmo custo e é fixa, então o resultado é determinístico.

**Os perfis de 40 MHz em 2,4 GHz se sobrepõem.** 1+5 ocupa 2402–2442 MHz e 7+11 ocupa 2432–2472 MHz: os dois compartilham 10 MHz (s = 0,25), e dois APs vizinhos com esses perfis entram em conflito, com interferência de 25% da sobreposição espacial. A decisão (#78) foi mantê-los e documentar a sobreposição, em vez de trocá-los por 1+5 e 9+13 (o único par sem sobreposição) ou de retirar os 40 MHz do padrão:

- os resultados padrão e o histórico do teste de escalabilidade continuam comparáveis com os das versões anteriores;
- os canais 12 e 13, necessários para 9+13, são permitidos no Brasil, mas nem todos os clientes os aceitam;
- os 40 MHz continuam no espaço de busca, o que importa para o critério de otimização: no modelo de consumo, 40 MHz gasta menos que 20 MHz, e retirá-los tiraria essa troca da análise de energia;
- a sobreposição não é ignorada: ela entra como interferência, e a busca só usa os dois pares em APs vizinhos quando isso compensa no critério escolhido.

Para um experimento sem essa sobreposição, escolha os canais em `channels` (por exemplo, `{"2.4 GHz": {"40 MHz": ["1", "9"]}}`, os pares 1+5 e 9+13) ou, na interface, use o atalho **Sem sobreposição** de 40 MHz no mapa do espectro, que já marca em laranja as barras sobrepostas.

## Paralelismo

A busca começa pela solução gulosa, que serve de limite para a poda. Os dois primeiros níveis livres da árvore são expandidos em tarefas, consumidas por *pthreads* a partir de uma fila compartilhada. A melhor solução é compartilhada entre as *threads* sob *mutex*, e cada *thread* mantém uma cópia local atualizada por um contador de versão, o que evita travar o *mutex* a cada nó.

Em empate de custo, vence a tarefa de menor índice. Como as tarefas seguem a ordem da busca sequencial, o resultado é o mesmo para qualquer número de *threads*.

## Limitações

- O problema é NP-difícil. Em grafos grandes e densos, a busca exata não termina e para no limite de tempo, devolvendo a melhor solução encontrada (`optimal: false`).
- O ganho com mais *threads* depende do número de tarefas e da eficácia da poda. Com poucos perfis por faixa, os dois primeiros níveis geram no máximo 25 tarefas em 2,4 GHz e 100 em 5 GHz.
- No backtracking, o progresso enviado ao *frontend* é a fração de tarefas concluídas, e não uma estimativa do tempo restante.
- As metaheurísticas ainda não participam do teste de escalabilidade: o ponto de quebra dos métodos sem garantia de ótimo (limite de tempo excedido) não descreve uma busca que para pelo tempo, e a comparação precisa de repetições por semente.
- Conflitos entre dois APs travados não entram no custo, pois não dependem da atribuição.
