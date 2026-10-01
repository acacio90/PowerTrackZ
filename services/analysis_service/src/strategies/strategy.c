#define _POSIX_C_SOURCE 200809L

#include "strategy.h"
#include "backtracking.h"
#include "local_search.h"
#include "metaheuristic.h"
#include "simulated_annealing.h"
#include "tabu_search.h"
#include "genetic.h"
#include "hybrid_genetic.h"

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

static ProposedConfig *run_simulated_annealing(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats
) {
    return build_simulated_annealing_proposals(graph, context, stats);
}

static const StrategyParameterOption COOLING_SCHEDULE_OPTIONS[] = {
    {"geometric", "Geométrico"},
    {"linear", "Linear"},
};

static const StrategyParameter SIMULATED_ANNEALING_PARAMETERS[] = {
    META_SEED_PARAMETER,
    META_TIME_LIMIT_PARAMETER,
    {
        .name = "initial_temperature",
        .label = "Temperatura inicial",
        .description = "Temperatura no início da busca; em branco, é estimada para aceitar cerca de 80% das pioras de uma amostra de vizinhos.",
        .type = STRATEGY_PARAMETER_NUMBER,
        .default_value = 0,
        .min_value = 0.0001,
        .max_value = 1000000,
        .unit = NULL,
        .zero_disables = false,
        .advanced = true,
        .optional = true,
        .optional_label = "Estimada",
    },
    {
        .name = "cooling_schedule",
        .label = "Resfriamento",
        .description = "Geométrico multiplica a temperatura pela taxa a cada patamar; linear subtrai dela a fração (1 - taxa) da temperatura inicial.",
        .type = STRATEGY_PARAMETER_CHOICE,
        .unit = NULL,
        .advanced = true,
        .options = COOLING_SCHEDULE_OPTIONS,
        .option_count = 2,
        .default_option = "geometric",
    },
    {
        .name = "cooling_rate",
        .label = "Taxa de resfriamento",
        .description = "Quanto a temperatura conserva a cada patamar: mais perto de 1, resfriamento mais lento.",
        .type = STRATEGY_PARAMETER_NUMBER,
        .default_value = 0.95,
        .min_value = 0.5,
        .max_value = 0.9999,
        .unit = NULL,
        .zero_disables = false,
        .advanced = true,
    },
    {
        .name = "iterations_per_temperature",
        .label = "Iterações por temperatura",
        .description = "Iterações em cada patamar de temperatura, antes de resfriar.",
        .type = STRATEGY_PARAMETER_INTEGER,
        .default_value = 1000,
        .min_value = 1,
        .max_value = 10000000,
        .unit = NULL,
        .zero_disables = false,
        .advanced = true,
    },
    {
        .name = "min_temperature",
        .label = "Temperatura mínima",
        .description = "A busca para na faixa quando a temperatura fica abaixo deste valor.",
        .type = STRATEGY_PARAMETER_NUMBER,
        .default_value = 0.001,
        .min_value = 0,
        .max_value = 1000000,
        .unit = NULL,
        .zero_disables = true,
        .advanced = true,
    },
    META_MAX_ITERATIONS_PARAMETER,
    META_STAGNATION_PARAMETER,
    META_INITIAL_SOLUTION_PARAMETER,
};

static ProposedConfig *run_tabu_search(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats
) {
    return build_tabu_search_proposals(graph, context, stats);
}

static const StrategyParameter TABU_SEARCH_PARAMETERS[] = {
    META_SEED_PARAMETER,
    META_TIME_LIMIT_PARAMETER,
    {
        .name = "tabu_tenure",
        .label = "Permanência na lista tabu",
        .description = "Por quantas iterações um AP fica proibido de voltar ao perfil que acabou de deixar.",
        .type = STRATEGY_PARAMETER_INTEGER,
        .default_value = 10,
        .min_value = 1,
        .max_value = 100000,
        .unit = NULL,
        .zero_disables = false,
        .advanced = true,
    },
    {
        .name = "candidate_nodes",
        .label = "APs avaliados por iteração",
        .description = "Quantos APs são sorteados a cada iteração, priorizando os em conflito; todas as trocas de perfil deles são avaliadas.",
        .type = STRATEGY_PARAMETER_INTEGER,
        .default_value = 20,
        .min_value = 1,
        .max_value = 10000,
        .unit = NULL,
        .zero_disables = false,
        .advanced = true,
    },
    META_MAX_ITERATIONS_PARAMETER,
    META_STAGNATION_PARAMETER,
    META_INITIAL_SOLUTION_PARAMETER,
};

static ProposedConfig *run_genetic(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats
) {
    return build_genetic_proposals(graph, context, stats);
}

static const StrategyParameterOption CROSSOVER_OPTIONS[] = {
    {"uniform", "Uniforme"},
    {"one_point", "Um ponto"},
};

// Parametros do Algoritmo Genetico, compartilhados com o AG hibrido.
#define GENETIC_PARAMETERS     META_SEED_PARAMETER,     META_TIME_LIMIT_PARAMETER,     {         .name = "population_size",         .label = "População",         .description = "Número de indivíduos (soluções) em cada geração.",         .type = STRATEGY_PARAMETER_INTEGER,         .default_value = 50,         .min_value = 4,         .max_value = 10000,         .advanced = false,     },     {         .name = "generations",         .label = "Gerações",         .description = "Número máximo de gerações em cada faixa.",         .type = STRATEGY_PARAMETER_INTEGER,         .default_value = 1000,         .min_value = 0,         .max_value = 10000000,         .zero_disables = true,         .advanced = true,     },     {         .name = "max_iterations_without_improvement",         .label = "Gerações sem melhora",         .description = "Para a busca na faixa depois deste número de gerações sem melhorar a melhor solução.",         .type = STRATEGY_PARAMETER_INTEGER,         .default_value = 200,         .min_value = 0,         .max_value = 10000000,         .zero_disables = true,         .advanced = true,     },     {         .name = "greedy_fraction",         .label = "Fração gulosa da população inicial",         .description = "Fração da população inicial que parte do guloso (ele e cópias mutadas dele); o restante é aleatório.",         .type = STRATEGY_PARAMETER_NUMBER,         .default_value = 0.1,         .min_value = 0,         .max_value = 1,         .advanced = true,     },     {         .name = "crossover",         .label = "Cruzamento",         .description = "Uniforme: cada AP herda o perfil de um dos pais, ao acaso; um ponto: os APs antes de um corte vêm de um pai e os demais, do outro.",         .type = STRATEGY_PARAMETER_CHOICE,         .advanced = true,         .options = CROSSOVER_OPTIONS,         .option_count = 2,         .default_option = "uniform",     },     {         .name = "crossover_rate",         .label = "Taxa de cruzamento",         .description = "Probabilidade de um filho vir do cruzamento de dois pais; sem cruzamento, ele copia o primeiro pai.",         .type = STRATEGY_PARAMETER_NUMBER,         .default_value = 0.9,         .min_value = 0,         .max_value = 1,         .advanced = true,     },     {         .name = "mutation_rate",         .label = "Taxa de mutação",         .description = "Probabilidade de cada AP de um filho trocar de perfil.",         .type = STRATEGY_PARAMETER_NUMBER,         .default_value = 0.02,         .min_value = 0,         .max_value = 1,         .advanced = true,     },     {         .name = "tournament_size",         .label = "Tamanho do torneio",         .description = "Indivíduos sorteados em cada torneio de seleção; vence o melhor.",         .type = STRATEGY_PARAMETER_INTEGER,         .default_value = 3,         .min_value = 1,         .max_value = 10000,         .advanced = true,     },     {         .name = "elitism",         .label = "Elite",         .description = "Melhores indivíduos que passam intactos para a geração seguinte.",         .type = STRATEGY_PARAMETER_INTEGER,         .default_value = 2,         .min_value = 0,         .max_value = 9999,         .advanced = true,     }

static const StrategyParameter GENETIC_PARAMETERS_LIST[] = {
    GENETIC_PARAMETERS,
};

static ProposedConfig *run_hybrid_genetic(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats
) {
    return build_hybrid_genetic_proposals(graph, context, stats);
}

static const StrategyParameterOption LOCAL_SEARCH_TARGET_OPTIONS[] = {
    {"children", "Descendentes"},
    {"best", "Melhores da geração"},
};

static const StrategyParameter HYBRID_GENETIC_PARAMETERS[] = {
    GENETIC_PARAMETERS,
    {
        .name = "local_search_target",
        .label = "Busca local em",
        .description = "Descendentes: filhos sorteados de cada geração; melhores da geração: os melhores indivíduos, inclusive a elite.",
        .type = STRATEGY_PARAMETER_CHOICE,
        .advanced = true,
        .options = LOCAL_SEARCH_TARGET_OPTIONS,
        .option_count = 2,
        .default_option = "children",
    },
    {
        .name = "local_search_count",
        .label = "Indivíduos refinados",
        .description = "Quantos indivíduos recebem a busca local em cada geração em que ela é aplicada.",
        .type = STRATEGY_PARAMETER_INTEGER,
        .default_value = 5,
        .min_value = 1,
        .max_value = 10000,
        .advanced = true,
    },
    {
        .name = "local_search_frequency",
        .label = "Frequência da busca local",
        .description = "A busca local é aplicada a cada este número de gerações (1 = em todas).",
        .type = STRATEGY_PARAMETER_INTEGER,
        .default_value = 1,
        .min_value = 1,
        .max_value = 100000,
        .advanced = true,
    },
    {
        .name = "local_search_depth",
        .label = "Profundidade da busca local",
        .description = "Vizinhos avaliados em cada indivíduo refinado; a busca aceita os que não pioram.",
        .type = STRATEGY_PARAMETER_INTEGER,
        .default_value = 200,
        .min_value = 1,
        .max_value = 10000000,
        .advanced = true,
    },
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
        .name = "simulated_annealing",
        .description = "Simulated Annealing: aceita pioras com probabilidade que diminui com a temperatura, para escapar de ótimos locais.",
        .mode = "sequential",
        .family = "metaheuristic",
        .exact = false,
        .parameters = SIMULATED_ANNEALING_PARAMETERS,
        .parameter_count = PARAMETER_COUNT(SIMULATED_ANNEALING_PARAMETERS),
        .run = run_simulated_annealing,
        .validate = validate_simulated_annealing_parameters,
    },
    {
        .name = "tabu_search",
        .description = "Busca Tabu: aplica a melhor troca de perfil não proibida, mesmo que pior, e proíbe por um tempo desfazê-la.",
        .mode = "sequential",
        .family = "metaheuristic",
        .exact = false,
        .parameters = TABU_SEARCH_PARAMETERS,
        .parameter_count = PARAMETER_COUNT(TABU_SEARCH_PARAMETERS),
        .run = run_tabu_search,
        .validate = meta_validate_parameters,
    },
    {
        .name = "genetic",
        .description = "Algoritmo genético: evolui uma população de soluções por seleção em torneio, cruzamento, mutação e elitismo.",
        .mode = "sequential",
        .family = "metaheuristic",
        .exact = false,
        .parameters = GENETIC_PARAMETERS_LIST,
        .parameter_count = PARAMETER_COUNT(GENETIC_PARAMETERS_LIST),
        .run = run_genetic,
        .validate = validate_genetic_parameters,
    },
    {
        .name = "hybrid_genetic",
        .description = "Algoritmo genético híbrido: o algoritmo genético com uma busca local aplicada a alguns indivíduos de cada geração.",
        .mode = "sequential",
        .family = "metaheuristic",
        .exact = false,
        .parameters = HYBRID_GENETIC_PARAMETERS,
        .parameter_count = PARAMETER_COUNT(HYBRID_GENETIC_PARAMETERS),
        .run = run_hybrid_genetic,
        .validate = validate_genetic_parameters,
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
        case ASSIGNMENT_STOP_MIN_TEMPERATURE:
            return "min_temperature";
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
