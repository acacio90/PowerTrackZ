# Analysis Service

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
| `backtracking` | `time_limit_seconds` | número | `60` | 0 a 3600 | Tempo máximo da busca, em segundos. `0` desativa o limite. |

As estratégias `greedy` e `genetic` não têm parâmetros configuráveis.

`GET /strategies` descreve esses parâmetros em `strategy_details`, com nome, rótulo, tipo, padrão, limites, unidade e se o valor `0` desativa o recurso. A interface monta os campos a partir dessa descrição, de modo que um parâmetro novo precisa ser declarado apenas no serviço.

Valores fora do tipo ou do intervalo declarado são recusados com HTTP 400 e uma mensagem como `Parametro time_limit_seconds deve estar entre 0 e 3600`. Parâmetros que a estratégia não declara são ignorados. Os valores efetivamente usados aparecem em `execution.parameters`; o número de *threads* é limitado ao número de APs do grafo.

A resposta traz em `execution.search` se a solução é ótima (`optimal`), o motivo da parada (`completed`, `time_limit` ou `cancelled`), os nós explorados e os conflitos da solução gulosa e da final.

## Paralelismo

A busca começa pela solução gulosa, que serve de limite para a poda. Os dois primeiros níveis livres da árvore são expandidos em tarefas, consumidas por *pthreads* a partir de uma fila compartilhada. A melhor solução é compartilhada entre as *threads* sob *mutex*, e cada *thread* mantém uma cópia local atualizada por um contador de versão, o que evita travar o *mutex* a cada nó.

Em empate de custo, vence a tarefa de menor índice. Como as tarefas seguem a ordem da busca sequencial, o resultado é o mesmo para qualquer número de *threads*.

## Limitações

- O problema é NP-difícil. Em grafos grandes e densos, a busca exata não termina e para no limite de tempo, devolvendo a melhor solução encontrada (`optimal: false`).
- O ganho com mais *threads* depende do número de tarefas e da eficácia da poda. Com poucos perfis por faixa, os dois primeiros níveis geram no máximo 36 tarefas em 2,4 GHz e 100 em 5 GHz.
- O progresso enviado ao *frontend* é a fração de tarefas concluídas, e não uma estimativa do tempo restante.
- Conflitos entre dois APs travados não entram no custo, pois não dependem da atribuição.
