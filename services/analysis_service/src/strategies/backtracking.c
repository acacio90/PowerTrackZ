#define _POSIX_C_SOURCE 200809L

#include "backtracking.h"
#include "assignment.h"

#include <limits.h>
#include <math.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define TASK_EXPANSION_LEVELS 2
#define STOP_CHECK_INTERVAL 4096

// Perfis padrao de busca. Em 2,4 GHz so existem canais de 20 e 40 MHz; em 5 GHz, de 20, 40 e 80 MHz.
// A ordem desempata perfis de mesmo custo. Os dois perfis de 40 MHz em 2,4 GHz (1+5 e 7+11) se sobrepoem em
// 10 MHz (s = 0,25); a busca trata isso como interferencia. Mantidos por decisao da #78 (ver o README).
static const ProposedConfig CONFIG_PROFILES[] = {
    {"1", "40 MHz", "2.4 GHz"},
    {"11", "40 MHz", "2.4 GHz"},
    {"1", "20 MHz", "2.4 GHz"},
    {"6", "20 MHz", "2.4 GHz"},
    {"11", "20 MHz", "2.4 GHz"},
    {"36", "80 MHz", "5 GHz"},
    {"149", "80 MHz", "5 GHz"},
    {"36", "20 MHz", "5 GHz"},
    {"36", "40 MHz", "5 GHz"},
    {"44", "40 MHz", "5 GHz"},
    {"149", "40 MHz", "5 GHz"},
    {"157", "40 MHz", "5 GHz"},
    {"44", "20 MHz", "5 GHz"},
    {"149", "20 MHz", "5 GHz"},
    {"157", "20 MHz", "5 GHz"},
};

static const ProfileSet DEFAULT_PROFILE_SET = {
    CONFIG_PROFILES,
    (int) (sizeof(CONFIG_PROFILES) / sizeof(CONFIG_PROFILES[0])),
};

// Prefixo de atribuicoes que define uma tarefa independente da busca paralela.
typedef struct {
    int node_indexes[TASK_EXPANSION_LEVELS];
    int profile_indexes[TASK_EXPANSION_LEVELS];
    int length;
    int start_depth;
    AssignmentCost cost;
} SearchTask;

typedef struct {
    const SearchSetup *setup;
    SearchTask *tasks;
    int task_count;
    atomic_int next_task;
    atomic_int completed_tasks;
    pthread_mutex_t best_lock;
    atomic_uint best_version;
    AssignmentCost best_cost;
    int best_task;
    int *best_profiles;
    atomic_int stop_reason;
    double deadline;
    atomic_llong nodes_explored;
    Job *job;
    int stream_fd;
    pthread_mutex_t *stream_lock;
    const char *band_label;
    double progress_offset;
    double progress_scale;
} ParallelSearch;

typedef struct {
    ParallelSearch *search;
    int task_index;
    int *profiles;
    AssignmentCost current;
    AssignmentCost best_snapshot;
    int best_task_snapshot;
    unsigned best_version_seen;
    long long visits;
} WorkerState;

static void push_task(SearchTask **tasks, int *count, int *capacity, const SearchTask *task) {
    if (*count >= *capacity) {
        *capacity = *capacity > 0 ? *capacity * 2 : 16;
        SearchTask *grown = realloc(*tasks, sizeof(SearchTask) * (size_t) *capacity);
        if (!grown) {
            perror("realloc search tasks");
            exit(1);
        }
        *tasks = grown;
    }
    (*tasks)[(*count)++] = *task;
}

// Expande os primeiros niveis livres da arvore em tarefas, preservando a ordem da busca sequencial.
static void enumerate_tasks(
    const SearchSetup *setup,
    int *profiles,
    int depth,
    SearchTask prefix,
    int levels_left,
    SearchTask **tasks,
    int *count,
    int *capacity
) {
    const Graph *graph = setup->graph;
    while (depth < setup->order_count) {
        int node_index = setup->order[depth];
        if (assignment_node_is_fixed(graph, profiles, node_index)) {
            depth++;
            continue;
        }
        ProfileCandidate candidates[setup->profiles->count];
        int candidate_count = assignment_collect_candidates(setup, node_index, profiles, candidates);
        if (candidate_count == 0) {
            depth++;
            continue;
        }

        for (int candidate_index = 0; candidate_index < candidate_count; candidate_index++) {
            SearchTask next = prefix;
            next.node_indexes[next.length] = node_index;
            next.profile_indexes[next.length] = candidates[candidate_index].profile_index;
            next.length++;
            next.start_depth = depth + 1;
            add_assignment_cost(&next.cost, &candidates[candidate_index].delta);

            int previous_profile = profiles[node_index];
            profiles[node_index] = candidates[candidate_index].profile_index;
            if (levels_left <= 1) {
                push_task(tasks, count, capacity, &next);
            } else {
                enumerate_tasks(setup, profiles, depth + 1, next, levels_left - 1, tasks, count, capacity);
            }
            profiles[node_index] = previous_profile;
        }
        return;
    }

    prefix.start_depth = setup->order_count;
    push_task(tasks, count, capacity, &prefix);
}

// Envia o andamento da busca exata: a solucao gulosa ja existe e as tarefas restantes validam alternativas.
static void emit_search_progress(ParallelSearch *search, int completed_tasks) {
    if (search->stream_fd < 0 || !search->stream_lock || !search->job || is_cancelled(search->job)) {
        return;
    }

    pthread_mutex_lock(&search->best_lock);
    int best_conflicts = search->best_cost.conflicts;
    pthread_mutex_unlock(&search->best_lock);

    double band_percentage = search->task_count > 0 ? (95.0 * completed_tasks) / search->task_count : 95.0;
    double percentage = (search->progress_offset * 100.0) + (search->progress_scale * band_percentage);
    int total_nodes = search->setup->graph->node_count;
    cJSON *payload = cJSON_CreateObject();
    cJSON_AddStringToObject(payload, "stage", "assignment");
    cJSON_AddNumberToObject(payload, "assigned_nodes", total_nodes);
    cJSON_AddNumberToObject(payload, "total_nodes", total_nodes);
    cJSON_AddNumberToObject(payload, "percentage", percentage);
    cJSON_AddNumberToObject(payload, "stage_percentage", percentage);
    cJSON_AddNumberToObject(payload, "best_conflicts", best_conflicts);
    cJSON_AddBoolToObject(payload, "complete_assignment_found", true);
    cJSON_AddNumberToObject(payload, "completed_tasks", completed_tasks);
    cJSON_AddNumberToObject(payload, "task_count", search->task_count);
    if (search->band_label) {
        cJSON_AddStringToObject(payload, "band", search->band_label);
    }
    if (!assignment_stream_event(search->stream_fd, search->stream_lock, "progress", payload)) {
        atomic_store(&search->job->cancelled, 1);
    }
}

static void request_stop(ParallelSearch *search, AssignmentStopReason reason) {
    int expected = ASSIGNMENT_STOP_COMPLETED;
    atomic_compare_exchange_strong(&search->stop_reason, &expected, (int) reason);
}

static bool should_stop(WorkerState *worker) {
    ParallelSearch *search = worker->search;
    if (atomic_load(&search->stop_reason) != ASSIGNMENT_STOP_COMPLETED) {
        return true;
    }
    worker->visits++;
    if (worker->visits % STOP_CHECK_INTERVAL == 0) {
        if (search->job && is_cancelled(search->job)) {
            request_stop(search, ASSIGNMENT_STOP_CANCELLED);
            return true;
        }
        if (search->deadline > 0.0 && assignment_monotonic_seconds() >= search->deadline) {
            request_stop(search, ASSIGNMENT_STOP_TIME_LIMIT);
            return true;
        }
    }
    return false;
}

// Atualiza a copia local da melhor solucao apenas quando outra thread a substituiu.
static void refresh_best_snapshot(WorkerState *worker) {
    ParallelSearch *search = worker->search;
    if (atomic_load(&search->best_version) == worker->best_version_seen) {
        return;
    }
    pthread_mutex_lock(&search->best_lock);
    worker->best_snapshot = search->best_cost;
    worker->best_task_snapshot = search->best_task;
    worker->best_version_seen = atomic_load(&search->best_version);
    pthread_mutex_unlock(&search->best_lock);
}

// Poda o ramo se nem o limite otimista supera a melhor solucao. Conflitos e interferencia so crescem, a banda
// ganha no maximo remaining_bandwidth e a potencia cresce no minimo remaining_min_power_mw: toda solucao do
// ramo e, em cada componente, igual ou pior que o limite, entao a comparacao lexicografica vale para
// qualquer objetivo. Em empate, vence a tarefa de menor indice, o que reproduz o resultado da busca
// sequencial independentemente do numero de threads.
static bool can_prune(WorkerState *worker, int depth) {
    refresh_best_snapshot(worker);
    const SearchSetup *setup = worker->search->setup;
    AssignmentCost bound = worker->current;
    bound.bandwidth += setup->remaining_bandwidth[depth];
    bound.power_mw += setup->remaining_min_power_mw[depth];
    int comparison = compare_assignment_costs(setup->objective, &bound, &worker->best_snapshot);
    if (comparison > 0) {
        return true;
    }
    return comparison == 0 && worker->best_task_snapshot <= worker->task_index;
}

static void record_leaf(WorkerState *worker) {
    ParallelSearch *search = worker->search;
    pthread_mutex_lock(&search->best_lock);
    int comparison = compare_assignment_costs(search->setup->objective, &worker->current, &search->best_cost);
    if (comparison < 0 || (comparison == 0 && worker->task_index < search->best_task)) {
        search->best_cost = worker->current;
        search->best_task = worker->task_index;
        memcpy(search->best_profiles, worker->profiles, sizeof(int) * search->setup->graph->node_count);
        atomic_fetch_add(&search->best_version, 1);
    }
    pthread_mutex_unlock(&search->best_lock);
}

static void search_depth(WorkerState *worker, int depth) {
    if (should_stop(worker) || can_prune(worker, depth)) {
        return;
    }

    const SearchSetup *setup = worker->search->setup;
    if (depth >= setup->order_count) {
        record_leaf(worker);
        return;
    }

    const Graph *graph = setup->graph;
    int node_index = setup->order[depth];
    if (assignment_node_is_fixed(graph, worker->profiles, node_index)) {
        search_depth(worker, depth + 1);
        return;
    }

    ProfileCandidate candidates[setup->profiles->count];
    int candidate_count = assignment_collect_candidates(setup, node_index, worker->profiles, candidates);
    if (candidate_count == 0) {
        search_depth(worker, depth + 1);
        return;
    }

    AssignmentCost previous_cost = worker->current;
    int previous_profile = worker->profiles[node_index];
    for (int candidate_index = 0; candidate_index < candidate_count; candidate_index++) {
        worker->profiles[node_index] = candidates[candidate_index].profile_index;
        add_assignment_cost(&worker->current, &candidates[candidate_index].delta);
        search_depth(worker, depth + 1);
        worker->current = previous_cost;
        worker->profiles[node_index] = previous_profile;
        if (atomic_load(&worker->search->stop_reason) != ASSIGNMENT_STOP_COMPLETED) {
            return;
        }
    }
}

// Consome tarefas da fila compartilhada ate esgota-la ou ate a busca ser interrompida.
static void *search_worker(void *arg) {
    ParallelSearch *search = arg;
    const SearchSetup *setup = search->setup;
    int node_count = setup->graph->node_count;
    WorkerState worker = {
        .search = search,
        .profiles = assignment_malloc(sizeof(int) * node_count, "malloc worker profiles"),
        .best_version_seen = UINT_MAX,
    };

    while (atomic_load(&search->stop_reason) == ASSIGNMENT_STOP_COMPLETED) {
        int task_index = atomic_fetch_add(&search->next_task, 1);
        if (task_index >= search->task_count) {
            break;
        }
        const SearchTask *task = &search->tasks[task_index];
        memcpy(worker.profiles, setup->base_profiles, sizeof(int) * node_count);
        for (int step = 0; step < task->length; step++) {
            worker.profiles[task->node_indexes[step]] = task->profile_indexes[step];
        }
        worker.task_index = task_index;
        worker.current = task->cost;
        search_depth(&worker, task->start_depth);

        int completed = atomic_fetch_add(&search->completed_tasks, 1) + 1;
        emit_search_progress(search, completed);
    }

    atomic_fetch_add(&search->nodes_explored, worker.visits);
    free(worker.profiles);
    return NULL;
}

ProposedConfig *build_greedy_proposals(
    const Graph *graph,
    Job *job,
    const ProfileSet *profile_set,
    OptimizationObjective objective,
    AssignmentStats *stats
) {
    SearchSetup setup;
    assignment_setup(graph, profile_set, objective, &setup);
    int *profiles = assignment_malloc(sizeof(int) * graph->node_count, "malloc greedy profiles");
    AssignmentCost cost = assignment_greedy(&setup, profiles);
    ProposedConfig *proposals = assignment_proposals(&setup, profiles);

    if (stats) {
        *stats = (AssignmentStats){
            .stop_reason = ASSIGNMENT_STOP_COMPLETED,
            .optimal = false,
            .nodes_explored = graph->node_count,
            .task_count = 1,
            .initial_conflicts = cost.conflicts,
            .conflicts = cost.conflicts,
            .interference_score = cost.interference,
            .bandwidth_score = cost.bandwidth,
            .power_score_w = cost.power_mw / 1000.0,
        };
    }
    analysis_log(ANALYSIS_LOG_INFO, job ? job->id : NULL, "guloso concluido nodes=%d conflicts=%d", graph->node_count, cost.conflicts);

    free(profiles);
    assignment_free_setup(&setup);
    return proposals;
}

// Busca exata por branch-and-bound, iniciada pela solucao gulosa e paralelizada por tarefas.
ProposedConfig *build_backtracking_proposals(
    const Graph *graph,
    Job *job,
    const AssignmentOptions *options,
    AssignmentStats *stats
) {
    int thread_count = options && options->thread_count > 0 ? options->thread_count : 1;
    double time_limit = options ? options->time_limit_seconds : 0.0;
    analysis_log(
        ANALYSIS_LOG_INFO,
        job ? job->id : NULL,
        "backtracking iniciado nodes=%d edges=%d threads=%d time_limit=%.1fs objective=%s",
        graph->node_count,
        graph->edge_count,
        thread_count,
        time_limit,
        optimization_objective_name(options ? options->objective : OBJECTIVE_DEFAULT)
    );

    SearchSetup setup;
    assignment_setup(graph, options ? options->profiles : NULL, options ? options->objective : OBJECTIVE_DEFAULT, &setup);
    int *best_profiles = assignment_malloc(sizeof(int) * graph->node_count, "malloc best profiles");
    AssignmentCost initial = assignment_greedy(&setup, best_profiles);

    int *profiles = assignment_malloc(sizeof(int) * graph->node_count, "malloc task profiles");
    memcpy(profiles, setup.base_profiles, sizeof(int) * graph->node_count);
    SearchTask *tasks = NULL;
    int task_count = 0;
    int task_capacity = 0;
    SearchTask root = {.length = 0, .start_depth = 0, .cost = {0, 0.0, setup.base_bandwidth, setup.base_power_mw}};
    enumerate_tasks(&setup, profiles, 0, root, TASK_EXPANSION_LEVELS, &tasks, &task_count, &task_capacity);
    free(profiles);

    ParallelSearch search = {
        .setup = &setup,
        .tasks = tasks,
        .task_count = task_count,
        .best_cost = initial,
        .best_task = 0,
        .best_profiles = best_profiles,
        .deadline = time_limit > 0.0 ? assignment_monotonic_seconds() + time_limit : 0.0,
        .job = job,
        .stream_fd = options ? options->stream_fd : -1,
        .stream_lock = options ? options->stream_lock : NULL,
        .band_label = options ? options->band_label : NULL,
        .progress_offset = options ? options->progress_offset : 0.0,
        .progress_scale = options && options->progress_scale > 0.0 ? options->progress_scale : 1.0,
    };
    atomic_init(&search.next_task, 0);
    atomic_init(&search.completed_tasks, 0);
    atomic_init(&search.best_version, 0);
    atomic_init(&search.stop_reason, ASSIGNMENT_STOP_COMPLETED);
    atomic_init(&search.nodes_explored, 0);
    pthread_mutex_init(&search.best_lock, NULL);
    emit_search_progress(&search, 0);

    int worker_count = thread_count < task_count ? thread_count : task_count;
    if (worker_count < 1) {
        worker_count = 1;
    }
    analysis_log(ANALYSIS_LOG_DEBUG, job ? job->id : NULL, "busca paralela tasks=%d workers=%d greedy_conflicts=%d", task_count, worker_count, initial.conflicts);

    pthread_t *workers = assignment_malloc(sizeof(pthread_t) * worker_count, "malloc search workers");
    int started = 0;
    for (int worker_index = 0; worker_index < worker_count; worker_index++) {
        if (pthread_create(&workers[worker_index], NULL, search_worker, &search) != 0) {
            break;
        }
        started++;
    }
    if (started == 0) {
        search_worker(&search);
    }
    for (int worker_index = 0; worker_index < started; worker_index++) {
        pthread_join(workers[worker_index], NULL);
    }
    pthread_mutex_destroy(&search.best_lock);

    AssignmentStopReason stop_reason = (AssignmentStopReason) atomic_load(&search.stop_reason);
    if (stats) {
        *stats = (AssignmentStats){
            .stop_reason = stop_reason,
            .optimal = stop_reason == ASSIGNMENT_STOP_COMPLETED,
            .nodes_explored = atomic_load(&search.nodes_explored),
            .task_count = task_count,
            .initial_conflicts = initial.conflicts,
            .conflicts = search.best_cost.conflicts,
            .interference_score = search.best_cost.interference,
            .bandwidth_score = search.best_cost.bandwidth,
            .power_score_w = search.best_cost.power_mw / 1000.0,
        };
    }
    analysis_log(
        ANALYSIS_LOG_INFO,
        job ? job->id : NULL,
        "backtracking concluido stop=%s conflicts=%d greedy_conflicts=%d explored=%lld",
        assignment_stop_reason_name(stop_reason),
        search.best_cost.conflicts,
        initial.conflicts,
        (long long) atomic_load(&search.nodes_explored)
    );

    ProposedConfig *proposals = assignment_proposals(&setup, best_profiles);
    free(workers);
    free(tasks);
    free(best_profiles);
    assignment_free_setup(&setup);
    return proposals;
}

const ProfileSet *default_search_profiles(void) {
    return &DEFAULT_PROFILE_SET;
}
