#ifndef ANALYSIS_SERVICE_STRATEGIES_STRATEGY_H
#define ANALYSIS_SERVICE_STRATEGIES_STRATEGY_H

#include "../analysis_service.h"

#include <stddef.h>

typedef struct {
    const char *channel;
    const char *bandwidth;
    const char *frequency;
} ProposedConfig;

typedef struct {
    Job *job;
    int thread_count;
    int stream_fd;
    pthread_mutex_t *stream_lock;
} AnalysisExecutionContext;

typedef ProposedConfig *(*AnalysisStrategyRun)(
    const Graph *graph,
    const AnalysisExecutionContext *context
);

typedef struct {
    const char *name;
    const char *description;
    const char *mode;
    AnalysisStrategyRun run;
} AnalysisStrategy;

const AnalysisStrategy *analysis_strategies(size_t *count);
const AnalysisStrategy *find_analysis_strategy(const char *name);

#endif
