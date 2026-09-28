#define _POSIX_C_SOURCE 200809L

#include "strategy.h"
#include "backtracking.h"

#include <string.h>

static ProposedConfig *run_backtracking(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats
) {
    AssignmentOptions options = {
        .thread_count = context ? context->thread_count : 1,
        .time_limit_seconds = context ? context->time_limit_seconds : 0.0,
        .stream_fd = context ? context->stream_fd : -1,
        .stream_lock = context ? context->stream_lock : NULL,
    };
    return build_backtracking_proposals(graph, context ? context->job : NULL, &options, stats);
}

static ProposedConfig *run_greedy(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats
) {
    return build_greedy_proposals(graph, context ? context->job : NULL, stats);
}

static const AnalysisStrategy STRATEGIES[] = {
    {
        .name = "backtracking",
        .description = "Busca exata por branch-and-bound que minimiza conflitos e interferencia real, com limite de tempo",
        .mode = "pthread-task-queue",
        .uses_threads = true,
        .uses_time_limit = true,
        .run = run_backtracking,
    },
    {
        .name = "greedy",
        .description = "Heuristica gulosa que atribui a cada AP, em ordem de grau, o perfil de menor interferencia local",
        .mode = "sequential",
        .uses_threads = false,
        .uses_time_limit = false,
        .run = run_greedy,
    },
    {
        .name = "genetic",
        .description = "Estrategia genetica ainda nao portada para C",
        .mode = "placeholder",
        .uses_threads = false,
        .uses_time_limit = false,
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

const char *assignment_stop_reason_name(AssignmentStopReason reason) {
    switch (reason) {
        case ASSIGNMENT_STOP_TIME_LIMIT:
            return "time_limit";
        case ASSIGNMENT_STOP_CANCELLED:
            return "cancelled";
        default:
            return "completed";
    }
}
