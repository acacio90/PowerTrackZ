#define _POSIX_C_SOURCE 200809L

#include "strategy.h"
#include "backtracking.h"
#include "local_search.h"
#include "metaheuristic.h"

#include <math.h>
#include <stdio.h>
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
        .profiles = context ? context->profiles : NULL,
        .band_label = context ? context->band_label : NULL,
        .progress_offset = context ? context->progress_offset : 0.0,
        .progress_scale = context && context->progress_scale > 0.0 ? context->progress_scale : 1.0,
        .objective = context ? context->objective : OBJECTIVE_DEFAULT,
    };
    return build_backtracking_proposals(graph, context ? context->job : NULL, &options, stats);
}

static ProposedConfig *run_greedy(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats
) {
    return build_greedy_proposals(
        graph,
        context ? context->job : NULL,
        context ? context->profiles : NULL,
        context ? context->objective : OBJECTIVE_DEFAULT,
        stats
    );
}

static const StrategyParameter BACKTRACKING_PARAMETERS[] = {
    {
        .name = "thread_count",
        .label = "Threads",
        .description = "Número de threads que dividem a busca.",
        .type = STRATEGY_PARAMETER_INTEGER,
        .default_value = 1,
        .min_value = 1,
        .max_value = 256,
        .unit = NULL,
        .zero_disables = false,
        .advanced = true,
    },
    {
        .name = "time_limit_seconds",
        .label = "Limite de tempo",
        .description = "Tempo máximo da busca em cada faixa; ao atingi-lo, devolve a melhor configuração encontrada.",
        .type = STRATEGY_PARAMETER_NUMBER,
        .default_value = 60,
        .min_value = 0,
        .max_value = 3600,
        .unit = "s",
        .zero_disables = true,
        .advanced = false,
    },
};

static ProposedConfig *run_local_search(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats
) {
    return build_local_search_proposals(graph, context, stats);
}

static const StrategyParameter LOCAL_SEARCH_PARAMETERS[] = {
    META_SEED_PARAMETER,
    META_TIME_LIMIT_PARAMETER,
    META_MAX_ITERATIONS_PARAMETER,
    META_STAGNATION_PARAMETER,
    META_INITIAL_SOLUTION_PARAMETER,
};

#define PARAMETER_COUNT(parameters) (sizeof(parameters) / sizeof((parameters)[0]))

static const AnalysisStrategy STRATEGIES[] = {
    {
        .name = "backtracking",
        .description = "Busca exata por branch-and-bound que minimiza os conflitos e a interferência, com limite de tempo.",
        .mode = "pthread-task-queue",
        .family = "exact",
        .exact = true,
        .parameters = BACKTRACKING_PARAMETERS,
        .parameter_count = PARAMETER_COUNT(BACKTRACKING_PARAMETERS),
        .run = run_backtracking,
    },
    {
        .name = "greedy",
        .description = "Heurística gulosa que atribui a cada AP, em ordem de grau, o perfil de menor interferência local.",
        .mode = "sequential",
        .family = "constructive",
        .exact = false,
        .parameters = NULL,
        .parameter_count = 0,
        .run = run_greedy,
    },
    {
        .name = "local_search",
        .description = "Busca local: troca o perfil de um AP sorteado e aceita a troca se não piorar a solução; referência para as metaheurísticas.",
        .mode = "sequential",
        .family = "metaheuristic",
        .exact = false,
        .parameters = LOCAL_SEARCH_PARAMETERS,
        .parameter_count = PARAMETER_COUNT(LOCAL_SEARCH_PARAMETERS),
        .run = run_local_search,
        .validate = meta_validate_parameters,
    },
    {
        .name = "genetic",
        .description = "Algoritmo genético; ainda não implementado no serviço em C.",
        .mode = "placeholder",
        .family = "metaheuristic",
        .exact = false,
        .parameters = NULL,
        .parameter_count = 0,
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

const StrategyParameter *find_strategy_parameter(const AnalysisStrategy *strategy, const char *name) {
    if (!strategy || !name) {
        return NULL;
    }
    for (size_t index = 0; index < strategy->parameter_count; index++) {
        if (strcmp(strategy->parameters[index].name, name) == 0) {
            return &strategy->parameters[index];
        }
    }
    return NULL;
}

// Valida apenas os parametros declarados pela estrategia; os demais sao ignorados.
bool validate_strategy_parameters(const AnalysisStrategy *strategy, cJSON *parameters, char *error, size_t error_size) {
    if (!cJSON_IsObject(parameters)) {
        return true;
    }
    for (size_t index = 0; index < strategy->parameter_count; index++) {
        const StrategyParameter *parameter = &strategy->parameters[index];
        cJSON *item = cJSON_GetObjectItemCaseSensitive(parameters, parameter->name);
        if (!item || cJSON_IsNull(item)) {
            continue;
        }
        if (parameter->type == STRATEGY_PARAMETER_CHOICE) {
            bool known = false;
            for (size_t option = 0; cJSON_IsString(item) && option < parameter->option_count; option++) {
                known = known || strcmp(item->valuestring, parameter->options[option].value) == 0;
            }
            if (!known) {
                snprintf(error, error_size, "O parâmetro %s tem um valor desconhecido. Use uma das opções listadas em /strategies.", parameter->name);
                return false;
            }
            continue;
        }
        if (!cJSON_IsNumber(item)) {
            snprintf(error, error_size, "O parâmetro %s deve ser numérico.", parameter->name);
            return false;
        }
        double value = item->valuedouble;
        if (parameter->type == STRATEGY_PARAMETER_INTEGER && floor(value) != value) {
            snprintf(error, error_size, "O parâmetro %s deve ser inteiro.", parameter->name);
            return false;
        }
        if (value < parameter->min_value || value > parameter->max_value) {
            snprintf(
                error,
                error_size,
                "O parâmetro %s deve estar entre %g e %g.",
                parameter->name,
                parameter->min_value,
                parameter->max_value
            );
            return false;
        }
    }
    return strategy->validate ? strategy->validate(parameters, error, error_size) : true;
}

// Valor informado para o parametro, o padrao da estrategia ou, se ela nao o declara, o valor de reserva.
double strategy_parameter_value(const AnalysisStrategy *strategy, cJSON *parameters, const char *name, double fallback) {
    const StrategyParameter *parameter = find_strategy_parameter(strategy, name);
    if (!parameter) {
        return fallback;
    }
    cJSON *item = cJSON_IsObject(parameters) ? cJSON_GetObjectItemCaseSensitive(parameters, name) : NULL;
    return cJSON_IsNumber(item) ? item->valuedouble : parameter->default_value;
}

const char *strategy_parameter_option(const AnalysisStrategy *strategy, cJSON *parameters, const char *name) {
    const StrategyParameter *parameter = find_strategy_parameter(strategy, name);
    if (!parameter || parameter->type != STRATEGY_PARAMETER_CHOICE) {
        return NULL;
    }
    cJSON *item = cJSON_IsObject(parameters) ? cJSON_GetObjectItemCaseSensitive(parameters, name) : NULL;
    for (size_t option = 0; cJSON_IsString(item) && option < parameter->option_count; option++) {
        if (strcmp(item->valuestring, parameter->options[option].value) == 0) {
            return parameter->options[option].value;
        }
    }
    return parameter->default_option;
}

bool strategy_parameter_given(cJSON *parameters, const char *name) {
    cJSON *item = cJSON_IsObject(parameters) ? cJSON_GetObjectItemCaseSensitive(parameters, name) : NULL;
    return cJSON_IsNumber(item);
}

const char *strategy_parameter_type_name(StrategyParameterType type) {
    switch (type) {
        case STRATEGY_PARAMETER_INTEGER:
            return "integer";
        case STRATEGY_PARAMETER_CHOICE:
            return "choice";
        default:
            return "number";
    }
}

const char *assignment_stop_reason_name(AssignmentStopReason reason) {
    switch (reason) {
        case ASSIGNMENT_STOP_NO_IMPROVEMENT:
            return "no_improvement";
        case ASSIGNMENT_STOP_ITERATION_LIMIT:
            return "iteration_limit";
        case ASSIGNMENT_STOP_TIME_LIMIT:
            return "time_limit";
        case ASSIGNMENT_STOP_CANCELLED:
            return "cancelled";
        default:
            return "completed";
    }
}
