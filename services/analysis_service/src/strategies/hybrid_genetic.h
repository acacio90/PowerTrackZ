#ifndef ANALYSIS_SERVICE_STRATEGIES_HYBRID_GENETIC_H
#define ANALYSIS_SERVICE_STRATEGIES_HYBRID_GENETIC_H

#include "strategy.h"

// Algoritmo Genetico hibrido (memetico): o AG de genetic.c, com a descida da busca local (local_search.c)
// aplicada a alguns individuos de cada geracao. Ver o README.
ProposedConfig *build_hybrid_genetic_proposals(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats
);

#endif
