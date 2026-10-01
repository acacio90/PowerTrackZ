#ifndef ANALYSIS_SERVICE_STRATEGIES_METAHEURISTIC_H
#define ANALYSIS_SERVICE_STRATEGIES_METAHEURISTIC_H

#include "assignment.h"

#include <stdint.h>

// Base comum das metaheuristicas: representacao da solucao, custo completo e incremental pelo criterio de
// otimizacao, vizinhanca, solucao inicial, gerador aleatorio com semente e controle da execucao (parada,
// melhor solucao, curva de convergencia, progresso e cancelamento). Ver o README do servico.

// Gerador aleatorio proprio (xoshiro256**, inicializado por splitmix64): a mesma semente produz a mesma
// sequencia em qualquer plataforma, sem depender do rand() da biblioteca C.
typedef struct {
    uint64_t state[4];
} MetaRng;

// Inicializa o gerador pela semente e pelo fluxo (a faixa): cada faixa tem a sua sequencia.
void meta_rng_seed(MetaRng *rng, uint64_t seed, uint64_t stream);
uint64_t meta_rng_next(MetaRng *rng);
// Inteiro uniforme em [0, bound), sem vies de modulo.
int meta_rng_below(MetaRng *rng, int bound);
// Real uniforme em [0, 1).
double meta_rng_unit(MetaRng *rng);
// Semente sorteada (32 bits) quando a requisicao nao informa uma.
uint32_t meta_draw_seed(void);

// O problema de uma faixa: a solucao e um indice de perfil por AP (como no backtracking), e so mudam os
// APs que nao estao fixos (travados com um perfil disponivel) e tem perfis da sua faixa.
typedef struct {
    SearchSetup setup;
    // Perfis permitidos de cada AP: allowed[allowed_start[i] .. allowed_start[i + 1]).
    int *allowed_start;
    int *allowed;
    // APs com mais de um perfil permitido: os unicos que a vizinhanca altera.
    int *mobile;
    int mobile_count;
} MetaProblem;

void meta_problem_init(MetaProblem *problem, const Graph *graph, const ProfileSet *profiles, OptimizationObjective objective);
void meta_problem_free(MetaProblem *problem);

// Custo completo da solucao, com as mesmas regras do custo incremental do backtracking e do guloso.
AssignmentCost meta_full_cost(const MetaProblem *problem, const int *profiles);

// Movimento basico da vizinhanca: trocar o perfil de um AP.
typedef struct {
    int node_index;
    int profile_index;
} MetaMove;

// Variacao do custo ao aplicar o movimento (so os vizinhos do AP mudam: O(grau)).
AssignmentCost meta_move_delta(const MetaProblem *problem, const int *profiles, const MetaMove *move);
void meta_apply_move(int *profiles, AssignmentCost *cost, const MetaMove *move, const AssignmentCost *delta);
// Vizinho aleatorio: um AP movel e um perfil permitido diferente do atual. Falso se nenhum AP pode mudar.
bool meta_random_move(const MetaProblem *problem, MetaRng *rng, const int *profiles, MetaMove *move);

typedef enum {
    META_INITIAL_GREEDY = 0,
    META_INITIAL_RANDOM
} MetaInitialSolution;

// Solucao inicial: a do guloso ou um perfil permitido aleatorio para cada AP movel.
AssignmentCost meta_initial_solution(const MetaProblem *problem, MetaRng *rng, MetaInitialSolution kind, int *profiles);

// Parametros comuns, lidos da requisicao pela estrategia (ver META_*_PARAMETER).
typedef struct {
    double time_limit_seconds;
    long long max_iterations;
    long long max_iterations_without_improvement;
    MetaInitialSolution initial_solution;
} MetaOptions;

void meta_options_from_context(const AnalysisExecutionContext *context, MetaOptions *options);
// Pelo menos um criterio de parada precisa estar ativo (tempo, iteracoes ou iteracoes sem melhora).
bool meta_validate_parameters(cJSON *parameters, char *error, size_t error_size);

// Execucao de uma metaheuristica numa faixa.
typedef struct {
    const MetaProblem *problem;
    const AnalysisExecutionContext *context;
    MetaOptions options;
    MetaRng rng;
    double started_at;
    double deadline;
    double last_progress_at;
    long long iteration;
    long long last_improvement;
    AssignmentStopReason stop_reason;
    int *best_profiles;
    AssignmentCost best;
    AssignmentCost initial;
    cJSON *curve;
    long long curve_last_iteration;
} MetaRun;

// Inicia a execucao: gerador pela semente da faixa, solucao inicial (em profiles e cost), primeiro ponto
// da curva e o progresso inicial.
void meta_run_begin(
    MetaRun *run,
    const MetaProblem *problem,
    const AnalysisExecutionContext *context,
    const MetaOptions *options,
    int *profiles,
    AssignmentCost *cost
);

// Conta uma iteracao; falso quando a execucao deve parar (o motivo fica em stop_reason). A cada tanto,
// confere o tempo e o cancelamento, envia o progresso e recalcula o custo da solucao atual, para que a soma
// incremental das interferencias nao acumule erro de arredondamento.
bool meta_run_next(MetaRun *run, const int *profiles, AssignmentCost *cost);

// Oferece a solucao atual como candidata a melhor. Se ela parecer melhor, o custo e recalculado por completo
// (e corrigido em cost) antes da comparacao; se for melhor, vira a melhor solucao e entra na curva.
bool meta_run_offer(MetaRun *run, const int *profiles, AssignmentCost *cost);

// Encerra a execucao: ultimo ponto da curva, estatisticas (com a curva) e a configuracao proposta.
ProposedConfig *meta_run_end(MetaRun *run, AssignmentStats *stats);

// APs moveis em conflito: conflitos de cada AP e o conjunto dos moveis com pelo menos um, atualizado a cada
// movimento em O(grau). Usado para priorizar os APs em conflito na vizinhanca.
typedef struct {
    int *counts;
    int *members;
    int *position;
    int member_count;
} MetaConflictSet;

void meta_conflicts_init(MetaConflictSet *set, const MetaProblem *problem, const int *profiles);
void meta_conflicts_free(MetaConflictSet *set);
// Chamar antes de aplicar o movimento (profiles ainda com o perfil antigo do AP).
void meta_conflicts_update(MetaConflictSet *set, const MetaProblem *problem, const int *profiles, const MetaMove *move);

// Componentes do custo, na ordem de AssignmentCost.
typedef enum {
    META_COMPONENT_CONFLICTS = 0,
    META_COMPONENT_INTERFERENCE,
    META_COMPONENT_BANDWIDTH,
    META_COMPONENT_POWER,
    META_COMPONENT_COUNT
} MetaCostComponent;

// Quanto "candidate" e pior que "reference" no componente (positivo se pior, negativo se melhor); a largura
// de banda e o unico componente em que maior e melhor.
double meta_component_worsening(const AssignmentCost *candidate, const AssignmentCost *reference, MetaCostComponent component);

// Primeiro componente, na ordem do objetivo, em que os custos diferem; -1 se forem iguais. E o componente que
// decide a comparacao lexicografica (compare_assignment_costs).
int meta_deciding_component(OptimizationObjective objective, const AssignmentCost *left, const AssignmentCost *right);

// Parametros comuns das metaheuristicas, para compor a lista de cada estrategia.
extern const StrategyParameterOption META_INITIAL_SOLUTION_OPTIONS[2];

#define META_SEED_PARAMETER { \
    .name = "seed", \
    .label = "Semente", \
    .description = "Semente do gerador aleatório; em branco, o serviço sorteia uma e a informa no resultado.", \
    .type = STRATEGY_PARAMETER_INTEGER, \
    .default_value = 0, \
    .min_value = 0, \
    .max_value = 4294967295.0, \
    .unit = NULL, \
    .zero_disables = false, \
    .advanced = false, \
    .optional = true, \
    .optional_label = "Sorteada", \
}

#define META_TIME_LIMIT_PARAMETER { \
    .name = "time_limit_seconds", \
    .label = "Limite de tempo", \
    .description = "Tempo máximo da busca em cada faixa; ao atingi-lo, devolve a melhor configuração encontrada.", \
    .type = STRATEGY_PARAMETER_NUMBER, \
    .default_value = 10, \
    .min_value = 0, \
    .max_value = 3600, \
    .unit = "s", \
    .zero_disables = true, \
    .advanced = false, \
}

#define META_MAX_ITERATIONS_PARAMETER { \
    .name = "max_iterations", \
    .label = "Iterações", \
    .description = "Número máximo de iterações em cada faixa.", \
    .type = STRATEGY_PARAMETER_INTEGER, \
    .default_value = 1000000, \
    .min_value = 0, \
    .max_value = 1000000000, \
    .unit = NULL, \
    .zero_disables = true, \
    .advanced = true, \
}

#define META_STAGNATION_PARAMETER { \
    .name = "max_iterations_without_improvement", \
    .label = "Iterações sem melhora", \
    .description = "Para a busca na faixa depois deste número de iterações sem melhorar a melhor solução.", \
    .type = STRATEGY_PARAMETER_INTEGER, \
    .default_value = 100000, \
    .min_value = 0, \
    .max_value = 1000000000, \
    .unit = NULL, \
    .zero_disables = true, \
    .advanced = true, \
}

#define META_INITIAL_SOLUTION_PARAMETER { \
    .name = "initial_solution", \
    .label = "Solução inicial", \
    .description = "Ponto de partida da busca: a solução do guloso ou um perfil aleatório para cada AP.", \
    .type = STRATEGY_PARAMETER_CHOICE, \
    .unit = NULL, \
    .advanced = true, \
    .options = META_INITIAL_SOLUTION_OPTIONS, \
    .option_count = 2, \
    .default_option = "greedy", \
}

#endif
