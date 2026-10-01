#ifndef ANALYSIS_SERVICE_STRATEGIES_LOCAL_SEARCH_H
#define ANALYSIS_SERVICE_STRATEGIES_LOCAL_SEARCH_H

#include "strategy.h"

// Busca local sobre a base comum das metaheuristicas: a cada iteracao, sorteia um vizinho (trocar o perfil
// de um AP) e o aceita se nao piorar a solucao atual no criterio de otimizacao. Serve de referencia para
// as demais metaheuristicas.
ProposedConfig *build_local_search_proposals(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats
);

#endif
