#ifndef ANALYSIS_SERVICE_STRATEGIES_BACKTRACKING_H
#define ANALYSIS_SERVICE_STRATEGIES_BACKTRACKING_H

#include "strategy.h"

typedef struct {
    int thread_count;
    double time_limit_seconds;
    int stream_fd;
    pthread_mutex_t *stream_lock;
    const ProfileSet *profiles;
    const char *band_label;
    double progress_offset;
    double progress_scale;
    OptimizationObjective objective;
} AssignmentOptions;

ProposedConfig *build_greedy_proposals(
    const Graph *graph,
    Job *job,
    const ProfileSet *profiles,
    OptimizationObjective objective,
    AssignmentStats *stats
);

ProposedConfig *build_backtracking_proposals(
    const Graph *graph,
    Job *job,
    const AssignmentOptions *options,
    AssignmentStats *stats
);

// Perfis usados quando a requisicao nao informa os canais de uma faixa.
const ProfileSet *default_search_profiles(void);

#endif
