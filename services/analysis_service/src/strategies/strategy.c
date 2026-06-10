#define _POSIX_C_SOURCE 200809L

#include "strategy.h"
#include "backtracking.h"

#include <string.h>

static ProposedConfig *run_backtracking(
    const Graph *graph,
    const AnalysisExecutionContext *context
) {
    return build_backtracking_proposals(
        graph,
        context ? context->job : NULL,
        context ? context->thread_count : 1,
        context ? context->stream_fd : -1,
        context ? context->stream_lock : NULL
    );
}

static const AnalysisStrategy STRATEGIES[] = {
    {
        .name = "backtracking",
        .description = "Algoritmo de backtracking para atribuicao de configuracoes minimizando interferencia real",
        .mode = "pthread-root-branches",
        .run = run_backtracking,
    },
    {
        .name = "greedy",
        .description = "Estrategia greedy ainda nao portada para C",
        .mode = "placeholder",
        .run = NULL,
    },
    {
        .name = "genetic",
        .description = "Estrategia genetica ainda nao portada para C",
        .mode = "placeholder",
        .run = NULL,
    },
};

const AnalysisStrategy *analysis_strategies(size_t *count) {
    if (count) {
        *count = sizeof(STRATEGIES) / sizeof(STRATEGIES[0]);
    }
    return STRATEGIES;
}

const AnalysisStrategy *find_analysis_strategy(const char *name) {
    if (!name || name[0] == '\0') {
        name = "backtracking";
    }

    size_t count = 0;
    const AnalysisStrategy *strategies = analysis_strategies(&count);
    for (size_t index = 0; index < count; index++) {
        if (strcmp(strategies[index].name, name) == 0) {
            return &strategies[index];
        }
    }
    return NULL;
}
