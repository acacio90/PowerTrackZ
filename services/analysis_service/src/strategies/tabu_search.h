#ifndef ANALYSIS_SERVICE_STRATEGIES_TABU_SEARCH_H
#define ANALYSIS_SERVICE_STRATEGIES_TABU_SEARCH_H

#include "strategy.h"

// Busca Tabu sobre a base comum das metaheuristicas: a cada iteracao, avalia as trocas de perfil de alguns
// APs (priorizando os em conflito) e aplica a melhor nao proibida, mesmo que pior. Ver o README.
ProposedConfig *build_tabu_search_proposals(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats
);

// Lista tabu: voltar um AP a um perfil que ele acabou de deixar fica proibido por "tenure" iteracoes.
typedef struct {
    long long *until;
    int profile_count;
} TabuList;

void tabu_list_init(TabuList *list, int node_count, int profile_count);
void tabu_list_free(TabuList *list);
// Proibe dar ao AP o perfil indicado ate a iteracao "iteration + tenure" (exclusive).
void tabu_forbid(TabuList *list, int node_index, int profile_index, long long iteration, long long tenure);
bool tabu_is_forbidden(const TabuList *list, int node_index, int profile_index, long long iteration);
// Movimento admissivel: nao proibido ou, se proibido, que leva a uma solucao melhor que a melhor ja encontrada
// (criterio de aspiracao, informado em "aspiration").
bool tabu_admissible(
    const TabuList *list,
    int node_index,
    int profile_index,
    long long iteration,
    OptimizationObjective objective,
    const AssignmentCost *candidate,
    const AssignmentCost *best,
    bool *aspiration
);

#endif
