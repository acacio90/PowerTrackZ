#define _POSIX_C_SOURCE 200809L

#include "local_search.h"
#include "metaheuristic.h"

#include <stdlib.h>

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
