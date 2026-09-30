#ifndef ANALYSIS_SERVICE_STRATEGIES_STRATEGY_H
#define ANALYSIS_SERVICE_STRATEGIES_STRATEGY_H

#include "../analysis_service.h"
#include "objective.h"

#include <stddef.h>

typedef struct {
    const char *channel;
    const char *bandwidth;
    const char *frequency;
} ProposedConfig;

// Perfis (canal, largura e frequencia) que a estrategia pode atribuir.
typedef struct {
    const ProposedConfig *items;
    int count;
} ProfileSet;

// A analise roda uma vez por faixa: o progresso de cada execucao ocupa a fracao
// [progress_offset, progress_offset + progress_scale] do total.
typedef struct {
    Job *job;
    int thread_count;
    double time_limit_seconds;
    int stream_fd;
    pthread_mutex_t *stream_lock;
    const ProfileSet *profiles;
    const char *band_label;
    double progress_offset;
    double progress_scale;
    OptimizationObjective objective;
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
    double power_score_w;
} AssignmentStats;

typedef ProposedConfig *(*AnalysisStrategyRun)(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats
);

typedef enum {
    STRATEGY_PARAMETER_INTEGER = 0,
    STRATEGY_PARAMETER_NUMBER
} StrategyParameterType;

// Parametro configuravel de uma estrategia, descrito para que a interface monte o formulario.
typedef struct {
    const char *name;
    const char *label;
    const char *description;
    StrategyParameterType type;
    double default_value;
    double min_value;
    double max_value;
    const char *unit;
    bool zero_disables;
} StrategyParameter;

typedef struct {
    const char *name;
    const char *description;
    const char *mode;
    // Metodo exato: quando termina dentro do limite de tempo, a solucao e comprovadamente otima.
    bool exact;
    const StrategyParameter *parameters;
    size_t parameter_count;
    AnalysisStrategyRun run;
} AnalysisStrategy;

const AnalysisStrategy *analysis_strategies(size_t *count);
const AnalysisStrategy *find_analysis_strategy(const char *name);
const StrategyParameter *find_strategy_parameter(const AnalysisStrategy *strategy, const char *name);
bool validate_strategy_parameters(const AnalysisStrategy *strategy, cJSON *parameters, char *error, size_t error_size);
double strategy_parameter_value(const AnalysisStrategy *strategy, cJSON *parameters, const char *name, double fallback);
const char *strategy_parameter_type_name(StrategyParameterType type);
const char *assignment_stop_reason_name(AssignmentStopReason reason);

#endif
