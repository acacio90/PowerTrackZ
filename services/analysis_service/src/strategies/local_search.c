#define _POSIX_C_SOURCE 200809L

#include "local_search.h"
#include "metaheuristic.h"

#include <stdlib.h>

// A cada CHECK_MOVES vizinhos, a descida confere o tempo e o cancelamento.
#define CHECK_MOVES 64

long long local_search_descent(
    const MetaProblem *problem,
    MetaRun *run,
    int *profiles,
    AssignmentCost *cost,
    long long max_moves
) {
    OptimizationObjective objective = problem->setup.objective;
    const AnalysisExecutionContext *context = run->context;
    long long moves = 0;
    for (; moves < max_moves; moves++) {
        if (moves % CHECK_MOVES == 0) {
            if ((run->deadline > 0.0 && assignment_monotonic_seconds() >= run->deadline)
                || (context && context->job && is_cancelled(context->job))) {
                break;
            }
        }
        MetaMove move;
        if (!meta_random_move(problem, &run->rng, profiles, &move)) {
            break;
        }
        AssignmentCost delta = meta_move_delta(problem, profiles, &move);
        AssignmentCost candidate = *cost;
        add_assignment_cost(&candidate, &delta);
        if (compare_assignment_costs(objective, &candidate, cost) <= 0) {
            meta_apply_move(profiles, cost, &move, &delta);
        }
    }
    *cost = meta_full_cost(problem, profiles);
    return moves;
}

ProposedConfig *build_local_search_proposals(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats
) {
    OptimizationObjective objective = context ? context->objective : OBJECTIVE_DEFAULT;
    MetaOptions options;
    meta_options_from_context(context, &options);
    MetaProblem problem;
    meta_problem_init(&problem, graph, context ? context->profiles : NULL, objective);

    int *profiles = assignment_malloc(sizeof(int) * (size_t) graph->node_count, "malloc local search profiles");
    AssignmentCost cost;
    MetaRun run;
    meta_run_begin(&run, &problem, context, &options, profiles, &cost);

    while (meta_run_next(&run, profiles, &cost)) {
        MetaMove move;
        if (!meta_random_move(&problem, &run.rng, profiles, &move)) {
            break;
        }
        AssignmentCost delta = meta_move_delta(&problem, profiles, &move);
        AssignmentCost candidate = cost;
        add_assignment_cost(&candidate, &delta);
        // Aceita o vizinho que nao piora: os de mesmo custo deixam a busca andar por platos.
        if (compare_assignment_costs(objective, &candidate, &cost) <= 0) {
            meta_apply_move(profiles, &cost, &move, &delta);
            meta_run_offer(&run, profiles, &cost);
        }
    }

    ProposedConfig *proposals = meta_run_end(&run, stats);
    analysis_log(
        ANALYSIS_LOG_INFO,
        context && context->job ? context->job->id : NULL,
        "busca local concluida nodes=%d stop=%s iterations=%lld conflicts=%d initial_conflicts=%d",
        graph->node_count,
        assignment_stop_reason_name(stats ? stats->stop_reason : run.stop_reason),
        run.iteration,
        stats ? stats->conflicts : run.best.conflicts,
        run.initial.conflicts
    );
    free(profiles);
    meta_problem_free(&problem);
    return proposals;
}
