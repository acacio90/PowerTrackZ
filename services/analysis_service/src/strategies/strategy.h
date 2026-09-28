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
    double time_limit_seconds;
    int stream_fd;
    pthread_mutex_t *stream_lock;
} AnalysisExecutionContext;

typedef enum {
    ASSIGNMENT_STOP_COMPLETED = 0,
    ASSIGNMENT_STOP_TIME_LIMIT,
    ASSIGNMENT_STOP_CANCELLED
} AssignmentStopReason;

typedef struct {
    AssignmentStopReason stop_reason;
    bool optimal;
    long long nodes_explored;
    int task_count;
    int initial_conflicts;
    int conflicts;
    double interference_score;
    double bandwidth_score;
} AssignmentStats;

typedef ProposedConfig *(*AnalysisStrategyRun)(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats
);

typedef struct {
    const char *name;
    const char *description;
    const char *mode;
    bool uses_threads;
    bool uses_time_limit;
    AnalysisStrategyRun run;
} AnalysisStrategy;

const AnalysisStrategy *analysis_strategies(size_t *count);
const AnalysisStrategy *find_analysis_strategy(const char *name);
const char *assignment_stop_reason_name(AssignmentStopReason reason);

#endif
