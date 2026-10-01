#ifndef ANALYSIS_SERVICE_STRATEGIES_LOCAL_SEARCH_H
#define ANALYSIS_SERVICE_STRATEGIES_LOCAL_SEARCH_H

#include "metaheuristic.h"

// Busca local sobre a base comum das metaheuristicas: a cada iteracao, sorteia um vizinho (trocar o perfil
// de um AP) e o aceita se nao piorar a solucao atual no criterio de otimizacao. Serve de referencia para
// as demais metaheuristicas.
ProposedConfig *build_local_search_proposals(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats
);

// Descida da busca local aplicada a uma solucao (usada pelo AG hibrido): ate max_moves vizinhos sorteados,
// aceitando os que nao pioram. Nunca piora a solucao; ao fim, o custo e recalculado por completo. Para antes
// se "run" atingir o limite de tempo ou for cancelada. Devolve os vizinhos avaliados.
long long local_search_descent(
    const MetaProblem *problem,
    MetaRun *run,
    int *profiles,
    AssignmentCost *cost,
    long long max_moves
);

#endif
