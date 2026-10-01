#define _POSIX_C_SOURCE 200809L

#include "tabu_search.h"
#include "metaheuristic.h"

#include <stdio.h>
#include <stdlib.h>

// Probabilidade de sortear o AP de cada candidato entre os APs em conflito (quando ha algum); no restante, o
// AP e sorteado entre todos os moveis, para que a busca tambem mexa em APs sem conflito (interferencia,
// largura e potencia ainda podem melhorar).
#define CONFLICT_PRIORITY 0.8

void tabu_list_init(TabuList *list, int node_count, int profile_count) {
    size_t cells = (size_t) (node_count > 0 ? node_count : 1) * (size_t) (profile_count > 0 ? profile_count : 1);
    list->until = calloc(cells, sizeof(long long));
    if (!list->until) {
        perror("calloc tabu list");
        exit(1);
    }
    list->profile_count = profile_count;
}

void tabu_list_free(TabuList *list) {
    free(list->until);
    list->until = NULL;
}

void tabu_forbid(TabuList *list, int node_index, int profile_index, long long iteration, long long tenure) {
    if (profile_index >= 0) {
        list->until[(size_t) node_index * (size_t) list->profile_count + (size_t) profile_index] = iteration + tenure;
    }
}

bool tabu_is_forbidden(const TabuList *list, int node_index, int profile_index, long long iteration) {
    return iteration < list->until[(size_t) node_index * (size_t) list->profile_count + (size_t) profile_index];
}

bool tabu_admissible(
    const TabuList *list,
    int node_index,
    int profile_index,
    long long iteration,
    OptimizationObjective objective,
    const AssignmentCost *candidate,
    const AssignmentCost *best,
    bool *aspiration
) {
    *aspiration = false;
    if (!tabu_is_forbidden(list, node_index, profile_index, iteration)) {
        return true;
    }
    *aspiration = compare_assignment_costs(objective, candidate, best) < 0;
    return *aspiration;
}

ProposedConfig *build_tabu_search_proposals(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats
) {
    OptimizationObjective objective = context ? context->objective : OBJECTIVE_DEFAULT;
    const AnalysisStrategy *strategy = context ? context->strategy : NULL;
    cJSON *parameters = context ? context->parameters : NULL;
    long long tenure = strategy ? (long long) strategy_parameter_value(strategy, parameters, "tabu_tenure", 10) : 10;
    int candidate_nodes = strategy ? (int) strategy_parameter_value(strategy, parameters, "candidate_nodes", 20) : 20;

    MetaOptions options;
    meta_options_from_context(context, &options);
    MetaProblem problem;
    meta_problem_init(&problem, graph, context ? context->profiles : NULL, objective);
    int *profiles = assignment_malloc(sizeof(int) * (size_t) graph->node_count, "malloc tabu profiles");
    AssignmentCost cost;
    MetaRun run;
    meta_run_begin(&run, &problem, context, &options, profiles, &cost);

    TabuList tabu;
    tabu_list_init(&tabu, graph->node_count, problem.setup.profiles->count);
    MetaConflictSet conflicts;
    meta_conflicts_init(&conflicts, &problem, profiles);
    long long evaluated_moves = 0;
    long long tabu_rejections = 0;
    long long aspirations = 0;
    long long worsening_moves = 0;
    long long blocked_iterations = 0;

    while (meta_run_next(&run, profiles, &cost)) {
        // Vizinhanca da iteracao: todas as trocas de perfil de candidate_nodes APs sorteados.
        bool found = false;
        bool chosen_aspiration = false;
        MetaMove chosen = {0, 0};
        AssignmentCost chosen_delta = {0, 0.0, 0.0, 0};
        AssignmentCost chosen_cost = cost;
        for (int sample = 0; sample < candidate_nodes; sample++) {
            int node_index = conflicts.member_count > 0 && meta_rng_unit(&run.rng) < CONFLICT_PRIORITY
                ? conflicts.members[meta_rng_below(&run.rng, conflicts.member_count)]
                : problem.mobile[meta_rng_below(&run.rng, problem.mobile_count)];
            for (int position = problem.allowed_start[node_index]; position < problem.allowed_start[node_index + 1]; position++) {
                MetaMove move = {node_index, problem.allowed[position]};
                if (move.profile_index == profiles[node_index]) {
                    continue;
                }
                AssignmentCost delta = meta_move_delta(&problem, profiles, &move);
                AssignmentCost candidate = cost;
                add_assignment_cost(&candidate, &delta);
                evaluated_moves++;
                bool aspiration = false;
                if (!tabu_admissible(&tabu, node_index, move.profile_index, run.iteration, objective, &candidate, &run.best, &aspiration)) {
                    tabu_rejections++;
                    continue;
                }
                if (!found || compare_assignment_costs(objective, &candidate, &chosen_cost) < 0) {
                    found = true;
                    chosen = move;
                    chosen_delta = delta;
                    chosen_cost = candidate;
                    chosen_aspiration = aspiration;
                }
            }
        }
        if (!found) {
            // Todos os candidatos estao proibidos e nenhum supera a melhor: a iteracao passa sem movimento.
            blocked_iterations++;
            continue;
        }
        aspirations += chosen_aspiration;
        worsening_moves += compare_assignment_costs(objective, &chosen_cost, &cost) > 0;
        int old_profile = profiles[chosen.node_index];
        meta_conflicts_update(&conflicts, &problem, profiles, &chosen);
        meta_apply_move(profiles, &cost, &chosen, &chosen_delta);
        // Proibe o AP de voltar ao perfil que acabou de deixar.
        tabu_forbid(&tabu, chosen.node_index, old_profile, run.iteration, tenure);
        meta_run_offer(&run, profiles, &cost);
    }

    ProposedConfig *proposals = meta_run_end(&run, stats);
    if (stats) {
        stats->details = cJSON_CreateObject();
        cJSON_AddNumberToObject(stats->details, "evaluated_moves", (double) evaluated_moves);
        cJSON_AddNumberToObject(stats->details, "tabu_rejections", (double) tabu_rejections);
        cJSON_AddNumberToObject(stats->details, "aspirations", (double) aspirations);
        cJSON_AddNumberToObject(stats->details, "worsening_moves", (double) worsening_moves);
        cJSON_AddNumberToObject(stats->details, "blocked_iterations", (double) blocked_iterations);
    }
    analysis_log(
        ANALYSIS_LOG_INFO,
        context && context->job ? context->job->id : NULL,
        "busca tabu concluida nodes=%d stop=%s iterations=%lld conflicts=%d evaluated=%lld tabu=%lld aspirations=%lld",
        graph->node_count,
        assignment_stop_reason_name(run.stop_reason),
        run.iteration,
        run.best.conflicts,
        evaluated_moves,
        tabu_rejections,
        aspirations
    );
    meta_conflicts_free(&conflicts);
    tabu_list_free(&tabu);
    free(profiles);
    meta_problem_free(&problem);
    return proposals;
}
