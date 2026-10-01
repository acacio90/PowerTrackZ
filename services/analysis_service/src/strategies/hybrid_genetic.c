#define _POSIX_C_SOURCE 200809L

#include "hybrid_genetic.h"
#include "genetic.h"
#include "local_search.h"

#include <stdlib.h>
#include <string.h>

typedef struct {
    // Alvo da busca local: os descendentes (filhos sorteados) ou os melhores de cada geracao.
    bool children;
    int count;
    long long frequency;
    long long depth;
    long long applied;
    long long improved;
    long long worsened;
    long long moves;
} HybridState;

static void refine(HybridState *state, MetaRun *run, const MetaProblem *problem, GeneticPopulation *population, int index) {
    int *genes = population->genes + (size_t) index * (size_t) population->node_count;
    AssignmentCost before = population->costs[index];
    state->moves += local_search_descent(problem, run, genes, &population->costs[index], state->depth);
    state->applied++;
    int comparison = compare_assignment_costs(problem->setup.objective, &population->costs[index], &before);
    state->improved += comparison < 0;
    state->worsened += comparison > 0;
}

// A cada "frequency" geracoes, aplica a descida a "count" individuos da geracao recem-formada.
static void hybrid_generation(void *hook_context, MetaRun *run, const MetaProblem *problem, GeneticPopulation *population) {
    HybridState *state = hook_context;
    if (run->iteration % state->frequency != 0) {
        return;
    }
    int size = population->size;
    int *order = assignment_malloc(sizeof(int) * (size_t) size, "malloc hybrid order");
    int targets = 0;
    if (state->children) {
        // Filhos distintos, sorteados entre os que nao sao elite (Fisher-Yates parcial).
        int first = population->elite_count;
        int available = size - first;
        for (int index = 0; index < available; index++) {
            order[index] = first + index;
        }
        targets = state->count < available ? state->count : available;
        for (int index = 0; index < targets; index++) {
            int other = index + meta_rng_below(&run->rng, available - index);
            int swap = order[index];
            order[index] = order[other];
            order[other] = swap;
        }
    } else {
        // Os melhores da geracao, do melhor para o pior.
        bool *taken = calloc((size_t) size, sizeof(bool));
        if (!taken) {
            free(order);
            return;
        }
        targets = state->count < size ? state->count : size;
        for (int slot = 0; slot < targets; slot++) {
            int chosen = -1;
            for (int index = 0; index < size; index++) {
                if (!taken[index] && (chosen < 0 || compare_assignment_costs(problem->setup.objective, &population->costs[index], &population->costs[chosen]) < 0)) {
                    chosen = index;
                }
            }
            taken[chosen] = true;
            order[slot] = chosen;
        }
        free(taken);
    }
    for (int index = 0; index < targets; index++) {
        refine(state, run, problem, population, order[index]);
    }
    free(order);
}

ProposedConfig *build_hybrid_genetic_proposals(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats
) {
    GeneticOptions genetic;
    genetic_options_from_context(context, &genetic);
    const AnalysisStrategy *strategy = context ? context->strategy : NULL;
    cJSON *parameters = context ? context->parameters : NULL;
    const char *target = strategy ? strategy_parameter_option(strategy, parameters, "local_search_target") : NULL;
    HybridState state = {
        .children = !target || strcmp(target, "children") == 0,
        .count = strategy ? (int) strategy_parameter_value(strategy, parameters, "local_search_count", 5) : 5,
        .frequency = strategy ? (long long) strategy_parameter_value(strategy, parameters, "local_search_frequency", 1) : 1,
        .depth = strategy ? (long long) strategy_parameter_value(strategy, parameters, "local_search_depth", 200) : 200,
    };
    if (state.frequency < 1) {
        state.frequency = 1;
    }

    // genetic_run acrescenta os contadores do AG; os da busca local vao depois, quando ja estao completos.
    ProposedConfig *proposals = genetic_run(
        graph, context, stats, &genetic, hybrid_generation, &state, cJSON_CreateObject(), "algoritmo genetico hibrido"
    );
    if (stats && stats->details) {
        cJSON_AddNumberToObject(stats->details, "local_search_applied", (double) state.applied);
        cJSON_AddNumberToObject(stats->details, "local_search_improved", (double) state.improved);
        cJSON_AddNumberToObject(stats->details, "local_search_worsened", (double) state.worsened);
        cJSON_AddNumberToObject(stats->details, "local_search_moves", (double) state.moves);
    }
    return proposals;
}
