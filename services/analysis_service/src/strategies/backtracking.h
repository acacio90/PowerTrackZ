#ifndef ANALYSIS_SERVICE_STRATEGIES_BACKTRACKING_H
#define ANALYSIS_SERVICE_STRATEGIES_BACKTRACKING_H

#include "../analysis_service.h"

typedef struct {
    const char *channel;
    const char *bandwidth;
    const char *frequency;
} ProposedConfig;

ProposedConfig *build_backtracking_proposals(
    const Graph *graph,
    Job *job,
    int thread_count,
    int stream_fd,
    pthread_mutex_t *stream_lock
);

#endif
