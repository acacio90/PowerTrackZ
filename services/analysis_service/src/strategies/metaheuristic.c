#define _POSIX_C_SOURCE 200809L

#include "metaheuristic.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

// A cada CHECK_INTERVAL iteracoes, confere tempo e cancelamento; a cada RESYNC_INTERVAL, recalcula o custo atual.
#define CHECK_INTERVAL 256
#define RESYNC_INTERVAL 4096
#define PROGRESS_INTERVAL_SECONDS 0.2
// Pontos da curva de convergencia por faixa; ao encher, um ponto a cada dois e descartado.
#define CURVE_MAX_POINTS 500

const StrategyParameterOption META_INITIAL_SOLUTION_OPTIONS[2] = {
    {"greedy", "Guloso"},
    {"random", "Aleatória"},
};

// ---------- Gerador aleatorio ----------

static uint64_t splitmix64(uint64_t *state) {
    uint64_t z = (*state += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

static uint64_t rotl(uint64_t value, int shift) {
    return (value << shift) | (value >> (64 - shift));
}

void meta_rng_seed(MetaRng *rng, uint64_t seed, uint64_t stream) {
    uint64_t state = seed ^ (stream * 0xD1B54A32D192ED03ULL);
    for (int index = 0; index < 4; index++) {
        rng->state[index] = splitmix64(&state);
    }
}

uint64_t meta_rng_next(MetaRng *rng) {
    uint64_t *s = rng->state;
    uint64_t result = rotl(s[1] * 5, 7) * 9;
    uint64_t t = s[1] << 17;
    s[2] ^= s[0];
    s[3] ^= s[1];
    s[1] ^= s[2];
    s[0] ^= s[3];
    s[2] ^= t;
    s[3] = rotl(s[3], 45);
    return result;
}

int meta_rng_below(MetaRng *rng, int bound) {
    if (bound <= 1) {
        return 0;
    }
    uint64_t limit = UINT64_MAX - (UINT64_MAX % (uint64_t) bound);
    uint64_t value;
    do {
        value = meta_rng_next(rng);
    } while (value >= limit);
    return (int) (value % (uint64_t) bound);
}

double meta_rng_unit(MetaRng *rng) {
    return (meta_rng_next(rng) >> 11) * (1.0 / 9007199254740992.0);
}

uint32_t meta_draw_seed(void) {
    uint32_t seed = 0;
    FILE *source = fopen("/dev/urandom", "rb");
    if (source) {
        size_t read = fread(&seed, sizeof(seed), 1, source);
        fclose(source);
        if (read == 1) {
            return seed;
        }
    }
    struct timespec now;
    clock_gettime(CLOCK_REALTIME, &now);
    uint64_t state = ((uint64_t) now.tv_sec << 32) ^ (uint64_t) now.tv_nsec ^ (uint64_t) getpid();
    return (uint32_t) splitmix64(&state);
}

// ---------- Problema e custo ----------

void meta_problem_init(MetaProblem *problem, const Graph *graph, const ProfileSet *profiles, OptimizationObjective objective) {
    assignment_setup(graph, profiles, objective, &problem->setup);
    const SearchSetup *setup = &problem->setup;
    int node_count = graph->node_count;
    problem->allowed_start = assignment_malloc(sizeof(int) * (size_t) (node_count + 1), "malloc allowed start");
    problem->allowed = assignment_malloc(sizeof(int) * (size_t) node_count * (size_t) setup->profiles->count, "malloc allowed profiles");
    problem->mobile = assignment_malloc(sizeof(int) * (size_t) node_count, "malloc mobile nodes");
    problem->mobile_count = 0;

    int used = 0;
    for (int node_index = 0; node_index < node_count; node_index++) {
        problem->allowed_start[node_index] = used;
        if (assignment_node_is_fixed(graph, setup->base_profiles, node_index)) {
            continue;
        }
        for (int profile_index = 0; profile_index < setup->searchable_count; profile_index++) {
            if (assignment_same_band(setup->profiles->items[profile_index].frequency, graph->nodes[node_index].frequency)) {
                problem->allowed[used++] = profile_index;
            }
        }
        if (used - problem->allowed_start[node_index] > 1) {
            problem->mobile[problem->mobile_count++] = node_index;
        }
    }
    problem->allowed_start[node_count] = used;
}

void meta_problem_free(MetaProblem *problem) {
    assignment_free_setup(&problem->setup);
    free(problem->allowed_start);
    free(problem->allowed);
    free(problem->mobile);
}

// Interferencia (w * s) entre dois APs com os perfis indicados; zero se um deles nao tem perfil.
static double pair_interference(const MetaProblem *problem, int left, int left_profile, int right, int right_profile) {
    if (left_profile < 0 || right_profile < 0) {
        return 0.0;
    }
    const Graph *graph = problem->setup.graph;
    const ProposedConfig *a = &problem->setup.profiles->items[left_profile];
    const ProposedConfig *b = &problem->setup.profiles->items[right_profile];
    return interference_percentage_for_config(
        &graph->nodes[left], a->channel, a->bandwidth, a->frequency,
        &graph->nodes[right], b->channel, b->bandwidth, b->frequency
    );
}

static void add_profile_cost(const MetaProblem *problem, AssignmentCost *cost, int profile_index, int sign) {
    const ProposedConfig *profile = &problem->setup.profiles->items[profile_index];
    cost->bandwidth += sign * assignment_bandwidth_score(profile->bandwidth);
    cost->power_mw += sign * objective_power_mw(profile->frequency, profile->bandwidth);
}

// Mesmas regras do custo incremental: base dos APs travados, banda e potencia de cada AP atribuido (nao fixo)
// e as arestas com os dois lados definidos, exceto entre dois APs fixos.
AssignmentCost meta_full_cost(const MetaProblem *problem, const int *profiles) {
    const Graph *graph = problem->setup.graph;
    AssignmentCost cost = {0, 0.0, problem->setup.base_bandwidth, problem->setup.base_power_mw};
    for (int node_index = 0; node_index < graph->node_count; node_index++) {
        if (profiles[node_index] >= 0 && !assignment_node_is_fixed(graph, profiles, node_index)) {
            add_profile_cost(problem, &cost, profiles[node_index], 1);
        }
    }
    for (int edge_index = 0; edge_index < graph->edge_count; edge_index++) {
        int left = graph->edges[edge_index].source;
        int right = graph->edges[edge_index].target;
        if (assignment_node_is_fixed(graph, profiles, left) && assignment_node_is_fixed(graph, profiles, right)) {
            continue;
        }
        double interference = pair_interference(problem, left, profiles[left], right, profiles[right]);
        if (interference > 0.0) {
            cost.conflicts++;
            cost.interference += interference;
        }
    }
    return cost;
}

AssignmentCost meta_move_delta(const MetaProblem *problem, const int *profiles, const MetaMove *move) {
    const Node *node = &problem->setup.graph->nodes[move->node_index];
    int old_profile = profiles[move->node_index];
    AssignmentCost delta = {0, 0.0, 0.0, 0};
    if (old_profile == move->profile_index) {
        return delta;
    }
    if (old_profile >= 0) {
        add_profile_cost(problem, &delta, old_profile, -1);
    }
    add_profile_cost(problem, &delta, move->profile_index, 1);
    for (int position = 0; position < node->neighbor_count; position++) {
        int neighbor = node->neighbors[position];
        double before = pair_interference(problem, move->node_index, old_profile, neighbor, profiles[neighbor]);
        double after = pair_interference(problem, move->node_index, move->profile_index, neighbor, profiles[neighbor]);
        delta.conflicts += (after > 0.0) - (before > 0.0);
        delta.interference += after - before;
    }
    return delta;
}

void meta_apply_move(int *profiles, AssignmentCost *cost, const MetaMove *move, const AssignmentCost *delta) {
    profiles[move->node_index] = move->profile_index;
    add_assignment_cost(cost, delta);
}

bool meta_random_move(const MetaProblem *problem, MetaRng *rng, const int *profiles, MetaMove *move) {
    if (problem->mobile_count == 0) {
        return false;
    }
    int node_index = problem->mobile[meta_rng_below(rng, problem->mobile_count)];
    int start = problem->allowed_start[node_index];
    int count = problem->allowed_start[node_index + 1] - start;
    // Sorteia entre os outros perfis: pula a posicao do perfil atual, se ele estiver na lista.
    int current_position = -1;
    for (int position = 0; position < count; position++) {
        if (problem->allowed[start + position] == profiles[node_index]) {
            current_position = position;
            break;
        }
    }
    int choices = current_position >= 0 ? count - 1 : count;
    int pick = meta_rng_below(rng, choices);
    if (current_position >= 0 && pick >= current_position) {
        pick++;
    }
    move->node_index = node_index;
    move->profile_index = problem->allowed[start + pick];
    return true;
}

AssignmentCost meta_initial_solution(const MetaProblem *problem, MetaRng *rng, MetaInitialSolution kind, int *profiles) {
    if (kind == META_INITIAL_GREEDY) {
        return assignment_greedy(&problem->setup, profiles);
    }
    const Graph *graph = problem->setup.graph;
    memcpy(profiles, problem->setup.base_profiles, sizeof(int) * (size_t) graph->node_count);
    for (int node_index = 0; node_index < graph->node_count; node_index++) {
        int start = problem->allowed_start[node_index];
        int count = problem->allowed_start[node_index + 1] - start;
        if (count > 0) {
            profiles[node_index] = problem->allowed[start + meta_rng_below(rng, count)];
        }
    }
    return meta_full_cost(problem, profiles);
}

// ---------- Parametros ----------

static double parameter_number(const AnalysisExecutionContext *context, const char *name, double fallback) {
    return context && context->strategy
        ? strategy_parameter_value(context->strategy, context->parameters, name, fallback)
        : fallback;
}

void meta_options_from_context(const AnalysisExecutionContext *context, MetaOptions *options) {
    options->time_limit_seconds = context ? context->time_limit_seconds : 0.0;
    options->max_iterations = (long long) parameter_number(context, "max_iterations", 0);
    options->max_iterations_without_improvement = (long long) parameter_number(context, "max_iterations_without_improvement", 0);
    const char *initial = context && context->strategy
        ? strategy_parameter_option(context->strategy, context->parameters, "initial_solution")
        : NULL;
    options->initial_solution = initial && strcmp(initial, "random") == 0 ? META_INITIAL_RANDOM : META_INITIAL_GREEDY;
}

bool meta_validate_parameters(cJSON *parameters, char *error, size_t error_size) {
    const char *names[] = {"time_limit_seconds", "max_iterations", "max_iterations_without_improvement"};
    for (size_t index = 0; index < sizeof(names) / sizeof(names[0]); index++) {
        cJSON *item = cJSON_IsObject(parameters) ? cJSON_GetObjectItemCaseSensitive(parameters, names[index]) : NULL;
        // Sem valor, vale o padrao, que e diferente de zero nos tres.
        if (!cJSON_IsNumber(item) || item->valuedouble != 0.0) {
            return true;
        }
    }
    snprintf(error, error_size, "Os três critérios de parada estão desativados. Informe um limite de tempo, de iterações ou de iterações sem melhora.");
    return false;
}

// ---------- APs em conflito ----------

static void conflict_set_refresh(MetaConflictSet *set, const MetaProblem *problem, int node_index) {
    bool mobile = problem->allowed_start[node_index + 1] - problem->allowed_start[node_index] > 1;
    bool inside = set->position[node_index] >= 0;
    if (mobile && set->counts[node_index] > 0 && !inside) {
        set->position[node_index] = set->member_count;
        set->members[set->member_count++] = node_index;
    } else if ((!mobile || set->counts[node_index] == 0) && inside) {
        int last = set->members[--set->member_count];
        set->members[set->position[node_index]] = last;
        set->position[last] = set->position[node_index];
        set->position[node_index] = -1;
    }
}

void meta_conflicts_init(MetaConflictSet *set, const MetaProblem *problem, const int *profiles) {
    const Graph *graph = problem->setup.graph;
    size_t size = sizeof(int) * (size_t) (graph->node_count > 0 ? graph->node_count : 1);
    set->counts = calloc(1, size);
    set->members = assignment_malloc(size, "malloc conflict members");
    set->position = assignment_malloc(size, "malloc conflict positions");
    if (!set->counts) {
        perror("calloc conflict counts");
        exit(1);
    }
    set->member_count = 0;
    for (int edge_index = 0; edge_index < graph->edge_count; edge_index++) {
        int left = graph->edges[edge_index].source;
        int right = graph->edges[edge_index].target;
        if (pair_interference(problem, left, profiles[left], right, profiles[right]) > 0.0) {
            set->counts[left]++;
            set->counts[right]++;
        }
    }
    for (int node_index = 0; node_index < graph->node_count; node_index++) {
        set->position[node_index] = -1;
        conflict_set_refresh(set, problem, node_index);
    }
}

void meta_conflicts_free(MetaConflictSet *set) {
    free(set->counts);
    free(set->members);
    free(set->position);
}

void meta_conflicts_update(MetaConflictSet *set, const MetaProblem *problem, const int *profiles, const MetaMove *move) {
    const Node *node = &problem->setup.graph->nodes[move->node_index];
    int old_profile = profiles[move->node_index];
    for (int position = 0; position < node->neighbor_count; position++) {
        int neighbor = node->neighbors[position];
        int before = pair_interference(problem, move->node_index, old_profile, neighbor, profiles[neighbor]) > 0.0;
        int after = pair_interference(problem, move->node_index, move->profile_index, neighbor, profiles[neighbor]) > 0.0;
        if (before != after) {
            set->counts[move->node_index] += after - before;
            set->counts[neighbor] += after - before;
            conflict_set_refresh(set, problem, neighbor);
        }
    }
    conflict_set_refresh(set, problem, move->node_index);
}

// ---------- Componentes do custo ----------

double meta_component_worsening(const AssignmentCost *candidate, const AssignmentCost *reference, MetaCostComponent component) {
    switch (component) {
        case META_COMPONENT_CONFLICTS:
            return (double) (candidate->conflicts - reference->conflicts);
        case META_COMPONENT_INTERFERENCE:
            return candidate->interference - reference->interference;
        case META_COMPONENT_BANDWIDTH:
            return reference->bandwidth - candidate->bandwidth;
        case META_COMPONENT_POWER:
            return (double) (candidate->power_mw - reference->power_mw) / 1000.0;
        default:
            return 0.0;
    }
}

int meta_deciding_component(OptimizationObjective objective, const AssignmentCost *left, const AssignmentCost *right) {
    static const MetaCostComponent default_order[] = {META_COMPONENT_CONFLICTS, META_COMPONENT_INTERFERENCE, META_COMPONENT_BANDWIDTH};
    static const MetaCostComponent energy_tiebreak_order[] = {META_COMPONENT_CONFLICTS, META_COMPONENT_INTERFERENCE, META_COMPONENT_POWER};
    static const MetaCostComponent energy_first_order[] = {META_COMPONENT_POWER, META_COMPONENT_CONFLICTS, META_COMPONENT_INTERFERENCE};
    const MetaCostComponent *order = objective == OBJECTIVE_ENERGY_TIEBREAK ? energy_tiebreak_order
        : objective == OBJECTIVE_ENERGY_FIRST ? energy_first_order
        : default_order;
    for (int index = 0; index < 3; index++) {
        if (meta_component_worsening(left, right, order[index]) != 0.0) {
            return (int) order[index];
        }
    }
    return -1;
}

// ---------- Execucao ----------

static void add_curve_point(MetaRun *run, long long iteration) {
    if (cJSON_GetArraySize(run->curve) >= CURVE_MAX_POINTS) {
        // Mantem o primeiro ponto e descarta um a cada dois dos seguintes.
        for (int index = cJSON_GetArraySize(run->curve) - 1; index >= 1; index--) {
            if (index % 2 == 1) {
                cJSON_DeleteItemFromArray(run->curve, index);
            }
        }
    }
    cJSON *point = cJSON_CreateObject();
    cJSON_AddNumberToObject(point, "iteration", (double) iteration);
    cJSON_AddNumberToObject(point, "time_ms", (assignment_monotonic_seconds() - run->started_at) * 1000.0);
    cJSON_AddNumberToObject(point, "conflicts", run->best.conflicts);
    cJSON_AddNumberToObject(point, "interference", run->best.interference);
    cJSON_AddNumberToObject(point, "bandwidth", run->best.bandwidth);
    cJSON_AddNumberToObject(point, "power_w", run->best.power_mw / 1000.0);
    cJSON_AddItemToArray(run->curve, point);
    run->curve_last_iteration = iteration;
}

// Fracao concluida da faixa: a do criterio de parada mais adiantado (tempo, iteracoes ou estagnacao).
static double band_fraction(const MetaRun *run, double now) {
    double fraction = 0.0;
    if (run->options.time_limit_seconds > 0.0) {
        fraction = fmax(fraction, (now - run->started_at) / run->options.time_limit_seconds);
    }
    if (run->options.max_iterations > 0) {
        fraction = fmax(fraction, (double) run->iteration / (double) run->options.max_iterations);
    }
    if (run->options.max_iterations_without_improvement > 0) {
        fraction = fmax(fraction, (double) (run->iteration - run->last_improvement) / (double) run->options.max_iterations_without_improvement);
    }
    return fmin(fraction, 0.99);
}

static void emit_progress(MetaRun *run, double now) {
    const AnalysisExecutionContext *context = run->context;
    if (!context || context->stream_fd < 0 || !context->stream_lock || !context->job || is_cancelled(context->job)) {
        return;
    }
    run->last_progress_at = now;
    double scale = context->progress_scale > 0.0 ? context->progress_scale : 1.0;
    double percentage = (context->progress_offset * 100.0) + (scale * 100.0 * band_fraction(run, now));
    int total_nodes = run->problem->setup.graph->node_count;
    cJSON *payload = cJSON_CreateObject();
    cJSON_AddStringToObject(payload, "stage", "assignment");
    cJSON_AddNumberToObject(payload, "assigned_nodes", total_nodes);
    cJSON_AddNumberToObject(payload, "total_nodes", total_nodes);
    cJSON_AddNumberToObject(payload, "percentage", percentage);
    cJSON_AddNumberToObject(payload, "stage_percentage", percentage);
    cJSON_AddNumberToObject(payload, "best_conflicts", run->best.conflicts);
    cJSON_AddBoolToObject(payload, "complete_assignment_found", true);
    cJSON_AddNumberToObject(payload, "iteration", (double) run->iteration);
    if (context->band_label) {
        cJSON_AddStringToObject(payload, "band", context->band_label);
    }
    if (!assignment_stream_event(context->stream_fd, context->stream_lock, "progress", payload)) {
        atomic_store(&context->job->cancelled, 1);
    }
}

void meta_run_begin(
    MetaRun *run,
    const MetaProblem *problem,
    const AnalysisExecutionContext *context,
    const MetaOptions *options,
    int *profiles,
    AssignmentCost *cost
) {
    int node_count = problem->setup.graph->node_count;
    memset(run, 0, sizeof(*run));
    run->problem = problem;
    run->context = context;
    run->options = *options;
    meta_rng_seed(&run->rng, context ? context->seed : 0, context ? (uint64_t) context->band_index : 0);
    run->started_at = assignment_monotonic_seconds();
    run->deadline = options->time_limit_seconds > 0.0 ? run->started_at + options->time_limit_seconds : 0.0;
    run->stop_reason = ASSIGNMENT_STOP_COMPLETED;
    run->check_interval = CHECK_INTERVAL;
    run->best_profiles = assignment_malloc(sizeof(int) * (size_t) node_count, "malloc best profiles");
    run->curve = cJSON_CreateArray();

    *cost = meta_initial_solution(problem, &run->rng, options->initial_solution, profiles);
    run->initial = *cost;
    run->best = *cost;
    memcpy(run->best_profiles, profiles, sizeof(int) * (size_t) node_count);
    add_curve_point(run, 0);
    emit_progress(run, run->started_at);
}

bool meta_run_next(MetaRun *run, const int *profiles, AssignmentCost *cost) {
    if (run->stop_reason != ASSIGNMENT_STOP_COMPLETED) {
        return false;
    }
    if (run->problem->mobile_count == 0) {
        // Nenhum AP pode mudar: a solucao inicial ja e a unica possivel.
        return false;
    }
    if (run->options.max_iterations > 0 && run->iteration >= run->options.max_iterations) {
        run->stop_reason = ASSIGNMENT_STOP_ITERATION_LIMIT;
        return false;
    }
    if (run->options.max_iterations_without_improvement > 0
        && run->iteration - run->last_improvement >= run->options.max_iterations_without_improvement) {
        run->stop_reason = ASSIGNMENT_STOP_NO_IMPROVEMENT;
        return false;
    }
    if (run->iteration % run->check_interval == 0) {
        const AnalysisExecutionContext *context = run->context;
        if (context && context->job && is_cancelled(context->job)) {
            run->stop_reason = ASSIGNMENT_STOP_CANCELLED;
            return false;
        }
        double now = assignment_monotonic_seconds();
        if (run->deadline > 0.0 && now >= run->deadline) {
            run->stop_reason = ASSIGNMENT_STOP_TIME_LIMIT;
            return false;
        }
        if (now - run->last_progress_at >= PROGRESS_INTERVAL_SECONDS) {
            emit_progress(run, now);
        }
    }
    if (run->iteration > 0 && run->iteration % RESYNC_INTERVAL == 0) {
        *cost = meta_full_cost(run->problem, profiles);
    }
    run->iteration++;
    return true;
}

bool meta_run_offer(MetaRun *run, const int *profiles, AssignmentCost *cost) {
    OptimizationObjective objective = run->problem->setup.objective;
    if (compare_assignment_costs(objective, cost, &run->best) >= 0) {
        return false;
    }
    *cost = meta_full_cost(run->problem, profiles);
    if (compare_assignment_costs(objective, cost, &run->best) >= 0) {
        return false;
    }
    run->best = *cost;
    memcpy(run->best_profiles, profiles, sizeof(int) * (size_t) run->problem->setup.graph->node_count);
    run->last_improvement = run->iteration;
    add_curve_point(run, run->iteration);
    return true;
}

ProposedConfig *meta_run_end(MetaRun *run, AssignmentStats *stats) {
    if (run->iteration > run->curve_last_iteration) {
        add_curve_point(run, run->iteration);
    }
    if (stats) {
        *stats = (AssignmentStats){
            .stop_reason = run->stop_reason,
            .optimal = false,
            .nodes_explored = run->iteration,
            .task_count = 1,
            .initial_conflicts = run->initial.conflicts,
            .conflicts = run->best.conflicts,
            .interference_score = run->best.interference,
            .bandwidth_score = run->best.bandwidth,
            .power_score_w = run->best.power_mw / 1000.0,
            .iterations = run->iteration,
            .convergence = run->curve,
        };
    } else {
        cJSON_Delete(run->curve);
    }
    run->curve = NULL;
    ProposedConfig *proposals = assignment_proposals(&run->problem->setup, run->best_profiles);
    free(run->best_profiles);
    run->best_profiles = NULL;
    return proposals;
}
