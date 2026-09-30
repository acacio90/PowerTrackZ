#ifndef ANALYSIS_SERVICE_STRATEGIES_BACKTRACKING_H
#define ANALYSIS_SERVICE_STRATEGIES_BACKTRACKING_H

#include "strategy.h"

typedef struct {
    int thread_count;
    double time_limit_seconds;
    int stream_fd;
    pthread_mutex_t *stream_lock;
} AssignmentOptions;

ProposedConfig *build_greedy_proposals(
    const Graph *graph,
    Job *job,
    AssignmentStats *stats
);

ProposedConfig *build_backtracking_proposals(
    const Graph *graph,
    Job *job,
    const AssignmentOptions *options,
    AssignmentStats *stats
);

// Perfis (canal, largura e frequencia) que as estrategias podem propor.
int search_profile_count(void);
ProposedConfig search_profile_at(int index);

#endif
