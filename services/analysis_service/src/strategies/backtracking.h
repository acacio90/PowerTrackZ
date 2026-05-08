#ifndef ANALYSIS_SERVICE_STRATEGIES_BACKTRACKING_H
#define ANALYSIS_SERVICE_STRATEGIES_BACKTRACKING_H

#include "strategy.h"

ProposedConfig *build_backtracking_proposals(
    const Graph *graph,
    Job *job,
    int thread_count,
    int stream_fd,
    pthread_mutex_t *stream_lock
);

#endif
