#define _POSIX_C_SOURCE 200809L

#include "genetic.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static double parameter(const AnalysisExecutionContext *context, const char *name, double fallback) {
    return context && context->strategy
        ? strategy_parameter_value(context->strategy, context->parameters, name, fallback)
        : fallback;
}

void genetic_options_from_context(const AnalysisExecutionContext *context, GeneticOptions *options) {
    const char *crossover = context && context->strategy
        ? strategy_parameter_option(context->strategy, context->parameters, "crossover")
        : NULL;
    options->population_size = (int) parameter(context, "population_size", 50);
    options->greedy_fraction = parameter(context, "greedy_fraction", 0.1);
    options->one_point_crossover = crossover && strcmp(crossover, "one_point") == 0;
    options->crossover_rate = parameter(context, "crossover_rate", 0.9);
    options->mutation_rate = parameter(context, "mutation_rate", 0.02);
    options->tournament_size = (int) parameter(context, "tournament_size", 3);
    options->elitism = (int) parameter(context, "elitism", 2);
}

static double number_parameter(cJSON *parameters, const char *name, double fallback) {
    cJSON *item = cJSON_IsObject(parameters) ? cJSON_GetObjectItemCaseSensitive(parameters, name) : NULL;
    return cJSON_IsNumber(item) ? item->valuedouble : fallback;
}

bool validate_genetic_parameters(cJSON *parameters, char *error, size_t error_size) {
    if (number_parameter(parameters, "time_limit_seconds", 1) == 0
        && number_parameter(parameters, "generations", 1) == 0
        && number_parameter(parameters, "max_iterations_without_improvement", 1) == 0) {
        snprintf(error, error_size, "Os três critérios de parada estão desativados. Informe um limite de tempo, de gerações ou de gerações sem melhora.");
        return false;
    }
    double population = number_parameter(parameters, "population_size", 50);
    if (number_parameter(parameters, "elitism", 2) >= population) {
        snprintf(error, error_size, "A elite deve ser menor que a população. Diminua a elite ou aumente a população.");
        return false;
    }
    if (number_parameter(parameters, "tournament_size", 3) > population) {
        snprintf(error, error_size, "O torneio não pode ser maior que a população. Diminua o torneio ou aumente a população.");
        return false;
    }
    return true;
}

// ---------- Operadores ----------

// Torneio: sorteia tournament_size individuos (com reposicao) e devolve o melhor; no empate, o primeiro sorteado.
int genetic_tournament(const GeneticPopulation *population, MetaRng *rng, int tournament_size, OptimizationObjective objective) {
    int winner = meta_rng_below(rng, population->size);
    for (int round = 1; round < tournament_size; round++) {
        int challenger = meta_rng_below(rng, population->size);
        if (compare_assignment_costs(objective, &population->costs[challenger], &population->costs[winner]) < 0) {
            winner = challenger;
        }
    }
    return winner;
}

// Cruzamento uniforme (cada AP herda o perfil de um dos pais, ao acaso) ou de um ponto (os APs antes do corte,
// na ordem do grafo, vem do primeiro pai, e os demais, do segundo). APs fixos sao iguais nos dois pais.
void genetic_crossover(const MetaProblem *problem, MetaRng *rng, bool one_point, const int *left, const int *right, int *child) {
    int node_count = problem->setup.graph->node_count;
    int cut = one_point ? 1 + meta_rng_below(rng, node_count > 1 ? node_count - 1 : 1) : 0;
    for (int node_index = 0; node_index < node_count; node_index++) {
        bool from_left = one_point ? node_index < cut : meta_rng_unit(rng) < 0.5;
        child[node_index] = from_left ? left[node_index] : right[node_index];
    }
}

// Mutacao: cada AP movel troca, com probabilidade "rate", para outro perfil permitido. Devolve quantos mudaram.
int genetic_mutate(const MetaProblem *problem, MetaRng *rng, double rate, int *genes) {
    int changed = 0;
    for (int index = 0; index < problem->mobile_count; index++) {
        if (meta_rng_unit(rng) >= rate) {
            continue;
        }
        int node_index = problem->mobile[index];
        int start = problem->allowed_start[node_index];
        int count = problem->allowed_start[node_index + 1] - start;
        // Sorteia entre os outros perfis permitidos: pula a posicao do atual, se ele estiver na lista.
        int current_position = -1;
        for (int position = 0; position < count; position++) {
            if (problem->allowed[start + position] == genes[node_index]) {
                current_position = position;
                break;
            }
        }
        int pick = meta_rng_below(rng, current_position >= 0 ? count - 1 : count);
        if (current_position >= 0 && pick >= current_position) {
            pick++;
        }
        int profile = problem->allowed[start + pick];
        genes[node_index] = profile;
        changed++;
    }
    return changed;
}

// ---------- Execucao ----------

static int *genes_of(GeneticPopulation *population, int index) {
    return population->genes + (size_t) index * (size_t) population->node_count;
}

static void population_init(GeneticPopulation *population, int size, int node_count) {
    population->size = size;
    population->node_count = node_count;
    population->genes = assignment_malloc(sizeof(int) * (size_t) size * (size_t) (node_count > 0 ? node_count : 1), "malloc population genes");
    population->costs = assignment_malloc(sizeof(AssignmentCost) * (size_t) size, "malloc population costs");
    population->elite_count = 0;
}

static void population_free(GeneticPopulation *population) {
    free(population->genes);
    free(population->costs);
}

static int best_individual(const GeneticPopulation *population, OptimizationObjective objective) {
    int best = 0;
    for (int index = 1; index < population->size; index++) {
        if (compare_assignment_costs(objective, &population->costs[index], &population->costs[best]) < 0) {
            best = index;
        }
    }
    return best;
}

ProposedConfig *genetic_run(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats,
    const GeneticOptions *genetic,
    GeneticGenerationHook hook,
    void *hook_context,
    cJSON *details,
    const char *log_name
) {
    OptimizationObjective objective = context ? context->objective : OBJECTIVE_DEFAULT;
    MetaOptions options;
    meta_options_from_context(context, &options);
    // No AG, cada iteracao da base e uma geracao.
    options.max_iterations = (long long) parameter(context, "generations", 1000);
    options.initial_solution = META_INITIAL_GREEDY;
    MetaProblem problem;
    meta_problem_init(&problem, graph, context ? context->profiles : NULL, objective);
    int node_count = graph->node_count;
    size_t gene_bytes = sizeof(int) * (size_t) node_count;
    int *profiles = assignment_malloc(gene_bytes, "malloc genetic profiles");
    AssignmentCost cost;
    MetaRun run;
    meta_run_begin(&run, &problem, context, &options, profiles, &cost);
    run.check_interval = 1;

    int size = genetic->population_size;
    GeneticPopulation current;
    GeneticPopulation next;
    population_init(&current, size, node_count);
    population_init(&next, size, node_count);
    bool *taken = assignment_malloc(sizeof(bool) * (size_t) size, "malloc elite marks");

    // Populacao inicial: o guloso, copias mutadas dele (ate greedy_fraction da populacao) e solucoes aleatorias.
    int greedy_count = (int) llround(genetic->greedy_fraction * size);
    if (genetic->greedy_fraction > 0.0 && greedy_count < 1) {
        greedy_count = 1;
    }
    for (int index = 0; index < size; index++) {
        int *genes = genes_of(&current, index);
        if (index < greedy_count) {
            memcpy(genes, profiles, gene_bytes);
            if (index > 0) {
                genetic_mutate(&problem, &run.rng, genetic->mutation_rate, genes);
            }
            current.costs[index] = meta_full_cost(&problem, genes);
        } else {
            current.costs[index] = meta_initial_solution(&problem, &run.rng, META_INITIAL_RANDOM, genes);
        }
    }
    long long evaluations = size;
    long long generation_best_worsened = 0;
    int best = best_individual(&current, objective);
    AssignmentCost previous_best = current.costs[best];
    memcpy(profiles, genes_of(&current, best), gene_bytes);
    cost = current.costs[best];
    meta_run_offer(&run, profiles, &cost);

    while (meta_run_next(&run, profiles, &cost)) {
        // Elitismo: os "elitism" melhores passam intactos.
        int elite = genetic->elitism < size ? genetic->elitism : size - 1;
        memset(taken, 0, sizeof(bool) * (size_t) size);
        for (int slot = 0; slot < elite; slot++) {
            int chosen = -1;
            for (int index = 0; index < size; index++) {
                if (!taken[index] && (chosen < 0 || compare_assignment_costs(objective, &current.costs[index], &current.costs[chosen]) < 0)) {
                    chosen = index;
                }
            }
            taken[chosen] = true;
            memcpy(genes_of(&next, slot), genes_of(&current, chosen), gene_bytes);
            next.costs[slot] = current.costs[chosen];
        }
        // Os demais sao filhos: torneio, cruzamento (com a taxa de cruzamento; sem ele, copia o primeiro pai) e mutacao.
        for (int slot = elite; slot < size; slot++) {
            int *child = genes_of(&next, slot);
            int left = genetic_tournament(&current, &run.rng, genetic->tournament_size, objective);
            if (meta_rng_unit(&run.rng) < genetic->crossover_rate) {
                int right = genetic_tournament(&current, &run.rng, genetic->tournament_size, objective);
                genetic_crossover(&problem, &run.rng, genetic->one_point_crossover, genes_of(&current, left), genes_of(&current, right), child);
            } else {
                memcpy(child, genes_of(&current, left), gene_bytes);
            }
            genetic_mutate(&problem, &run.rng, genetic->mutation_rate, child);
            next.costs[slot] = meta_full_cost(&problem, child);
            evaluations++;
        }
        next.elite_count = elite;
        if (hook) {
            hook(hook_context, &run, &problem, &next);
        }

        GeneticPopulation swap = current;
        current = next;
        next = swap;
        best = best_individual(&current, objective);
        if (compare_assignment_costs(objective, &current.costs[best], &previous_best) > 0) {
            generation_best_worsened++;
        }
        previous_best = current.costs[best];
        memcpy(profiles, genes_of(&current, best), gene_bytes);
        cost = current.costs[best];
        meta_run_offer(&run, profiles, &cost);
    }

    ProposedConfig *proposals = meta_run_end(&run, stats);
    if (!details) {
        details = cJSON_CreateObject();
    }
    cJSON_AddNumberToObject(details, "population_size", size);
    cJSON_AddNumberToObject(details, "evaluations", (double) evaluations);
    cJSON_AddNumberToObject(details, "generation_best_worsened", (double) generation_best_worsened);
    if (stats) {
        stats->details = details;
    } else {
        cJSON_Delete(details);
    }
    analysis_log(
        ANALYSIS_LOG_INFO,
        context && context->job ? context->job->id : NULL,
        "%s concluido nodes=%d stop=%s generations=%lld conflicts=%d evaluations=%lld",
        log_name,
        graph->node_count,
        assignment_stop_reason_name(run.stop_reason),
        run.iteration,
        run.best.conflicts,
        evaluations
    );
    free(taken);
    population_free(&current);
    population_free(&next);
    free(profiles);
    meta_problem_free(&problem);
    return proposals;
}

ProposedConfig *build_genetic_proposals(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats
) {
    GeneticOptions options;
    genetic_options_from_context(context, &options);
    return genetic_run(graph, context, stats, &options, NULL, NULL, NULL, "algoritmo genetico");
}
