#ifndef ANALYSIS_SERVICE_STRATEGIES_SIMULATED_ANNEALING_H
#define ANALYSIS_SERVICE_STRATEGIES_SIMULATED_ANNEALING_H

#include "strategy.h"

// Simulated Annealing sobre a base comum das metaheuristicas: aceita vizinhos piores com a probabilidade de
// Metropolis, calculada no componente do custo que decide a comparacao lexicografica (ver o README).
ProposedConfig *build_simulated_annealing_proposals(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats
);

bool validate_simulated_annealing_parameters(cJSON *parameters, char *error, size_t error_size);

#endif
