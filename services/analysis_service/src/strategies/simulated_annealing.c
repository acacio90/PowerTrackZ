#define _POSIX_C_SOURCE 200809L

#include "simulated_annealing.h"
#include "metaheuristic.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Vizinhos amostrados para calibrar as escalas e estimar a temperatura inicial, e a fracao de pioras que a
// temperatura inicial estimada aceita em media.
#define CALIBRATION_MOVES 200
#define INITIAL_ACCEPTANCE 0.8
#define DEFAULT_MIN_TEMPERATURE 0.001

typedef struct {
    // Escala de cada componente do custo: a media das variacoes nao nulas na amostra de vizinhos.
    double scale[META_COMPONENT_COUNT];
    double estimated_temperature;
} Calibration;

// Piora normalizada de "candidate" frente a "current": a variacao, dividida pela escala, no componente que
// decide a comparacao lexicografica. Assim, uma piora em conflitos e julgada pelo tamanho da piora em
// conflitos, mesmo que a interferencia melhore muito, e a ordem dos criterios e respeitada.
static double normalized_worsening(
    OptimizationObjective objective,
    const Calibration *calibration,
    const AssignmentCost *candidate,
    const AssignmentCost *current
) {
    int component = meta_deciding_component(objective, candidate, current);
    if (component < 0) {
        return 0.0;
    }
    return meta_component_worsening(candidate, current, (MetaCostComponent) component) / calibration->scale[component];
}

// Amostra vizinhos da solucao inicial (sem aplica-los) para obter as escalas dos componentes e a temperatura
// que aceita, em media, INITIAL_ACCEPTANCE das pioras: T0 = -media(piora normalizada) / ln(INITIAL_ACCEPTANCE).
static void calibrate(
    const MetaProblem *problem,
    MetaRng *rng,
    const int *profiles,
    const AssignmentCost *cost,
    Calibration *calibration
) {
    AssignmentCost candidates[CALIBRATION_MOVES];
    int sampled = 0;
    double sums[META_COMPONENT_COUNT] = {0};
    int counts[META_COMPONENT_COUNT] = {0};
    for (; sampled < CALIBRATION_MOVES; sampled++) {
        MetaMove move;
        if (!meta_random_move(problem, rng, profiles, &move)) {
            break;
        }
        AssignmentCost delta = meta_move_delta(problem, profiles, &move);
        candidates[sampled] = *cost;
        add_assignment_cost(&candidates[sampled], &delta);
        for (int component = 0; component < META_COMPONENT_COUNT; component++) {
            double change = fabs(meta_component_worsening(&candidates[sampled], cost, (MetaCostComponent) component));
            if (change > 0.0) {
                sums[component] += change;
                counts[component]++;
            }
        }
    }
    for (int component = 0; component < META_COMPONENT_COUNT; component++) {
        calibration->scale[component] = counts[component] > 0 ? sums[component] / counts[component] : 1.0;
    }

    OptimizationObjective objective = problem->setup.objective;
    double worsening_sum = 0.0;
    int worsening_count = 0;
    for (int index = 0; index < sampled; index++) {
        if (compare_assignment_costs(objective, &candidates[index], cost) > 0) {
            worsening_sum += normalized_worsening(objective, calibration, &candidates[index], cost);
            worsening_count++;
        }
    }
    double mean = worsening_count > 0 ? worsening_sum / worsening_count : 1.0;
    calibration->estimated_temperature = -mean / log(INITIAL_ACCEPTANCE);
}

static double number_parameter(cJSON *parameters, const char *name, double fallback) {
    cJSON *item = cJSON_IsObject(parameters) ? cJSON_GetObjectItemCaseSensitive(parameters, name) : NULL;
    return cJSON_IsNumber(item) ? item->valuedouble : fallback;
}

bool validate_simulated_annealing_parameters(cJSON *parameters, char *error, size_t error_size) {
    if (!meta_validate_parameters(parameters, error, error_size)) {
        return false;
    }
    if (strategy_parameter_given(parameters, "initial_temperature")) {
        double initial = number_parameter(parameters, "initial_temperature", 0.0);
        double minimum = number_parameter(parameters, "min_temperature", DEFAULT_MIN_TEMPERATURE);
        if (minimum >= initial) {
            snprintf(error, error_size, "A temperatura mínima deve ser menor que a temperatura inicial. Diminua a mínima ou aumente a inicial.");
            return false;
        }
    }
    return true;
}

ProposedConfig *build_simulated_annealing_proposals(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats
) {
    OptimizationObjective objective = context ? context->objective : OBJECTIVE_DEFAULT;
    const AnalysisStrategy *strategy = context ? context->strategy : NULL;
    cJSON *parameters = context ? context->parameters : NULL;
    double cooling_rate = strategy ? strategy_parameter_value(strategy, parameters, "cooling_rate", 0.95) : 0.95;
    long long per_temperature = strategy ? (long long) strategy_parameter_value(strategy, parameters, "iterations_per_temperature", 1000) : 1000;
    double min_temperature = strategy ? strategy_parameter_value(strategy, parameters, "min_temperature", DEFAULT_MIN_TEMPERATURE) : DEFAULT_MIN_TEMPERATURE;
    const char *schedule = strategy ? strategy_parameter_option(strategy, parameters, "cooling_schedule") : NULL;
    bool linear = schedule && strcmp(schedule, "linear") == 0;

    MetaOptions options;
    meta_options_from_context(context, &options);
    MetaProblem problem;
    meta_problem_init(&problem, graph, context ? context->profiles : NULL, objective);
    int *profiles = assignment_malloc(sizeof(int) * (size_t) graph->node_count, "malloc annealing profiles");
    AssignmentCost cost;
    MetaRun run;
    meta_run_begin(&run, &problem, context, &options, profiles, &cost);

    Calibration calibration;
    calibrate(&problem, &run.rng, profiles, &cost, &calibration);
    bool estimated = !strategy_parameter_given(parameters, "initial_temperature");
    double initial_temperature = estimated ? calibration.estimated_temperature : number_parameter(parameters, "initial_temperature", 1.0);
    double temperature = initial_temperature;
    long long steps_at_temperature = 0;
    long long temperature_levels = 0;
    long long accepted_worse = 0;

    while (meta_run_next(&run, profiles, &cost)) {
        MetaMove move;
        if (!meta_random_move(&problem, &run.rng, profiles, &move)) {
            break;
        }
        AssignmentCost delta = meta_move_delta(&problem, profiles, &move);
        AssignmentCost candidate = cost;
        add_assignment_cost(&candidate, &delta);
        int comparison = compare_assignment_costs(objective, &candidate, &cost);
        bool accept = comparison <= 0;
        if (!accept) {
            // Metropolis: aceita a piora com probabilidade exp(-piora normalizada / T).
            double worsening = normalized_worsening(objective, &calibration, &candidate, &cost);
            if (meta_rng_unit(&run.rng) < exp(-worsening / temperature)) {
                accept = true;
                accepted_worse++;
            }
        }
        if (accept) {
            meta_apply_move(profiles, &cost, &move, &delta);
            if (comparison < 0) {
                meta_run_offer(&run, profiles, &cost);
            }
        }

        if (++steps_at_temperature >= per_temperature) {
            steps_at_temperature = 0;
            temperature_levels++;
            temperature = linear ? temperature - initial_temperature * (1.0 - cooling_rate) : temperature * cooling_rate;
            if (temperature <= 0.0 || (min_temperature > 0.0 && temperature < min_temperature)) {
                run.stop_reason = ASSIGNMENT_STOP_MIN_TEMPERATURE;
                break;
            }
        }
    }

    ProposedConfig *proposals = meta_run_end(&run, stats);
    if (stats) {
        stats->details = cJSON_CreateObject();
        cJSON_AddNumberToObject(stats->details, "initial_temperature", initial_temperature);
        cJSON_AddBoolToObject(stats->details, "initial_temperature_estimated", estimated);
        cJSON_AddNumberToObject(stats->details, "final_temperature", temperature > 0.0 ? temperature : 0.0);
        cJSON_AddNumberToObject(stats->details, "temperature_levels", (double) temperature_levels);
        cJSON_AddNumberToObject(stats->details, "accepted_worse", (double) accepted_worse);
    }
    analysis_log(
        ANALYSIS_LOG_INFO,
        context && context->job ? context->job->id : NULL,
        "simulated annealing concluido nodes=%d stop=%s iterations=%lld conflicts=%d t0=%.4f t=%.6f accepted_worse=%lld",
        graph->node_count,
        assignment_stop_reason_name(run.stop_reason),
        run.iteration,
        run.best.conflicts,
        initial_temperature,
        temperature,
        accepted_worse
    );
    free(profiles);
    meta_problem_free(&problem);
    return proposals;
}
