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

struct AnalysisStrategy;

// A analise roda uma vez por faixa: o progresso de cada execucao ocupa a fracao
// [progress_offset, progress_offset + progress_scale] do total.
typedef struct {
    const struct AnalysisStrategy *strategy;
    // Parametros da requisicao, para a estrategia ler os que declara.
    cJSON *parameters;
    // Semente da execucao (informada ou sorteada) e indice da faixa: cada faixa usa a sua sequencia.
    unsigned long long seed;
    int band_index;
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

// Motivo da parada. A ordem e a precedencia ao consolidar as faixas: vale o maior.
typedef enum {
    ASSIGNMENT_STOP_COMPLETED = 0,
    ASSIGNMENT_STOP_NO_IMPROVEMENT,
    ASSIGNMENT_STOP_ITERATION_LIMIT,
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
    // Metaheuristicas: iteracoes executadas e curva de convergencia (array JSON, de quem recebe as estatisticas).
    long long iterations;
    cJSON *convergence;
} AssignmentStats;

typedef ProposedConfig *(*AnalysisStrategyRun)(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats
);

typedef enum {
    STRATEGY_PARAMETER_INTEGER = 0,
    STRATEGY_PARAMETER_NUMBER,
    // Escolha entre opcoes de texto (por exemplo, a solucao inicial das metaheuristicas).
    STRATEGY_PARAMETER_CHOICE
} StrategyParameterType;

typedef struct {
    const char *value;
    const char *label;
} StrategyParameterOption;

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
    // Parametro avancado: a interface o mostra recolhido, com o valor padrao.
    bool advanced;
    // Parametro opcional, sem valor padrao (a semente: sem valor, o servico sorteia uma).
    bool optional;
    // Opcoes e opcao padrao dos parametros de escolha.
    const StrategyParameterOption *options;
    size_t option_count;
    const char *default_option;
} StrategyParameter;

typedef bool (*AnalysisStrategyValidate)(cJSON *parameters, char *error, size_t error_size);

typedef struct AnalysisStrategy {
    const char *name;
    const char *description;
    const char *mode;
    // Familia exibida na interface: "exact", "constructive" ou "metaheuristic".
    const char *family;
    // Metodo exato: quando termina dentro do limite de tempo, a solucao e comprovadamente otima.
    bool exact;
    const StrategyParameter *parameters;
    size_t parameter_count;
    AnalysisStrategyRun run;
    // Validacao que depende de mais de um parametro (opcional).
    AnalysisStrategyValidate validate;
} AnalysisStrategy;

const AnalysisStrategy *analysis_strategies(size_t *count);
const AnalysisStrategy *find_analysis_strategy(const char *name);
const StrategyParameter *find_strategy_parameter(const AnalysisStrategy *strategy, const char *name);
bool validate_strategy_parameters(const AnalysisStrategy *strategy, cJSON *parameters, char *error, size_t error_size);
double strategy_parameter_value(const AnalysisStrategy *strategy, cJSON *parameters, const char *name, double fallback);
// Opcao escolhida num parametro de escolha, ou a padrao; NULL se a estrategia nao declara o parametro.
const char *strategy_parameter_option(const AnalysisStrategy *strategy, cJSON *parameters, const char *name);
// Se a requisicao informa o parametro (um numero), por exemplo a semente.
bool strategy_parameter_given(cJSON *parameters, const char *name);
const char *strategy_parameter_type_name(StrategyParameterType type);
const char *assignment_stop_reason_name(AssignmentStopReason reason);

#endif
