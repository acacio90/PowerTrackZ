#define _POSIX_C_SOURCE 200809L

#include "backtracking.h"

#include <limits.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define TASK_EXPANSION_LEVELS 2
#define STOP_CHECK_INTERVAL 4096

typedef struct {
    const char *channel;
    const char *bandwidth;
    const char *frequency;
} ConfigProfile;

// Em 2,4 GHz so existem canais de 20 e 40 MHz; em 5 GHz, de 20, 40 e 80 MHz.
static const ConfigProfile CONFIG_PROFILES[] = {
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

#define PROFILE_COUNT ((int) (sizeof(CONFIG_PROFILES) / sizeof(CONFIG_PROFILES[0])))

typedef struct {
    int profile_index;
    int delta_conflicts;
    double delta_interference_score;
} ProfileCandidate;

// Custo lexicografico: menos conflitos, depois menor interferencia e, por fim, maior largura de banda.
typedef struct {
    int conflicts;
    double interference;
    double bandwidth;
} AssignmentCost;

// Dados comuns as estrategias: ordem de visita, perfis fixos e limite superior de banda restante.
typedef struct {
    const Graph *graph;
    int *order;
    int order_count;
    int *base_profiles;
    double base_bandwidth;
    double *remaining_bandwidth;
} SearchSetup;

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

static double monotonic_seconds(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + (ts.tv_nsec / 1000000000.0);
}

static void *checked_malloc(size_t size, const char *what) {
    void *memory = malloc(size > 0 ? size : 1);
    if (!memory) {
        perror(what);
        exit(1);
    }
    return memory;
}

// Ordena nos de maior grau primeiro para priorizar os mais restritivos na busca.
static int compare_node_degree_desc(const Graph *graph, int left, int right) {
    int left_degree = graph->nodes[left].neighbor_count;
    int right_degree = graph->nodes[right].neighbor_count;
    if (left_degree != right_degree) {
        return right_degree - left_degree;
    }
    return strcmp(graph->nodes[left].id, graph->nodes[right].id);
}

// Aplica uma ordenacao simples em funcao do grau dos nos.
static void sort_indices_by_degree(const Graph *graph, int *items, int count) {
    for (int i = 0; i < count - 1; i++) {
        for (int j = i + 1; j < count; j++) {
            if (compare_node_degree_desc(graph, items[i], items[j]) > 0) {
                int temp = items[i];
                items[i] = items[j];
                items[j] = temp;
            }
        }
    }
}

// Converte a largura de banda textual em um valor numerico comparavel.
static double bandwidth_score(const char *bandwidth) {
    if (!bandwidth || bandwidth[0] == '\0') {
        return 0.0;
    }
    double score = atof(bandwidth);
    return score > 0.0 ? score : 0.0;
}

static int compare_costs(const AssignmentCost *left, const AssignmentCost *right) {
    if (left->conflicts != right->conflicts) {
        return left->conflicts < right->conflicts ? -1 : 1;
    }
    if (left->interference != right->interference) {
        return left->interference < right->interference ? -1 : 1;
    }
    if (left->bandwidth != right->bandwidth) {
        return left->bandwidth > right->bandwidth ? -1 : 1;
    }
    return 0;
}

static bool node_is_fixed(const Graph *graph, const int *profiles, int node_index) {
    return graph->nodes[node_index].locked && profiles[node_index] >= 0;
}

// Calcula o custo incremental de aplicar um perfil ao no atual frente aos vizinhos ja definidos.
static int node_conflict_delta(
    const Graph *graph,
    int node_index,
    int profile_index,
    const int *assigned_profiles,
    double *interference_score
) {
    int conflicts = 0;
    double total_interference = 0.0;
    const ConfigProfile *profile = &CONFIG_PROFILES[profile_index];
    const Node *node = &graph->nodes[node_index];

    for (int neighbor_pos = 0; neighbor_pos < node->neighbor_count; neighbor_pos++) {
        int neighbor_index = node->neighbors[neighbor_pos];
        int neighbor_profile_index = assigned_profiles[neighbor_index];
        if (neighbor_profile_index < 0) {
            continue;
        }

        const ConfigProfile *neighbor_profile = &CONFIG_PROFILES[neighbor_profile_index];
        double interference = interference_percentage_for_config(
            node,
            profile->channel,
            profile->bandwidth,
            profile->frequency,
            &graph->nodes[neighbor_index],
            neighbor_profile->channel,
            neighbor_profile->bandwidth,
            neighbor_profile->frequency
        );
        if (interference > 0.0) {
            conflicts++;
            total_interference += interference;
        }
    }

    *interference_score = total_interference;
    return conflicts;
}

// Prioriza perfis sem conflito; em empate, favorece maior largura de banda e menor interferencia.
static int compare_profile_candidates(const void *left_ptr, const void *right_ptr) {
    const ProfileCandidate *left = left_ptr;
    const ProfileCandidate *right = right_ptr;
    const bool left_is_clean = left->delta_conflicts == 0;
    const bool right_is_clean = right->delta_conflicts == 0;
    double left_bandwidth = bandwidth_score(CONFIG_PROFILES[left->profile_index].bandwidth);
    double right_bandwidth = bandwidth_score(CONFIG_PROFILES[right->profile_index].bandwidth);

    if (left_is_clean != right_is_clean) {
        return left_is_clean ? -1 : 1;
    }

    if (left_is_clean && right_is_clean) {
        if (left_bandwidth > right_bandwidth) {
            return -1;
        }
        if (left_bandwidth < right_bandwidth) {
            return 1;
        }
        return left->profile_index - right->profile_index;
    }

    if (left->delta_conflicts != right->delta_conflicts) {
        return left->delta_conflicts - right->delta_conflicts;
    }
    if (left->delta_interference_score < right->delta_interference_score) {
        return -1;
    }
    if (left->delta_interference_score > right->delta_interference_score) {
        return 1;
    }
    if (left_bandwidth > right_bandwidth) {
        return -1;
    }
    if (left_bandwidth < right_bandwidth) {
        return 1;
    }
    return left->profile_index - right->profile_index;
}

// Lista os perfis compativeis com a frequencia do no, ja ordenados pela prioridade de busca.
static int collect_candidates(
    const Graph *graph,
    int node_index,
    const int *assigned_profiles,
    ProfileCandidate *candidates
) {
    int candidate_count = 0;
    const Node *node = &graph->nodes[node_index];
    for (int profile_index = 0; profile_index < PROFILE_COUNT; profile_index++) {
        if (strcmp(CONFIG_PROFILES[profile_index].frequency, node->frequency) != 0) {
            continue;
        }
        double delta_interference_score = 0.0;
        int delta_conflicts = node_conflict_delta(graph, node_index, profile_index, assigned_profiles, &delta_interference_score);
        candidates[candidate_count++] = (ProfileCandidate){
            .profile_index = profile_index,
            .delta_conflicts = delta_conflicts,
            .delta_interference_score = delta_interference_score,
        };
    }
    qsort(candidates, (size_t) candidate_count, sizeof(ProfileCandidate), compare_profile_candidates);
    return candidate_count;
}

static void apply_candidate(AssignmentCost *cost, const ProfileCandidate *candidate) {
    cost->conflicts += candidate->delta_conflicts;
    cost->interference += candidate->delta_interference_score;
    cost->bandwidth += bandwidth_score(CONFIG_PROFILES[candidate->profile_index].bandwidth);
}

static double max_bandwidth_for_frequency(const char *frequency) {
    double best = 0.0;
    for (int profile_index = 0; profile_index < PROFILE_COUNT; profile_index++) {
        if (strcmp(CONFIG_PROFILES[profile_index].frequency, frequency) == 0) {
            double score = bandwidth_score(CONFIG_PROFILES[profile_index].bandwidth);
            if (score > best) {
                best = score;
            }
        }
    }
    return best;
}

// Prepara ordem de visita, perfis dos APs travados e o limite superior de banda por profundidade.
static void setup_search(const Graph *graph, SearchSetup *setup) {
    int node_count = graph->node_count;
    setup->graph = graph;
    setup->order = checked_malloc(sizeof(int) * node_count, "malloc search order");
    setup->base_profiles = checked_malloc(sizeof(int) * node_count, "malloc base profiles");
    setup->remaining_bandwidth = checked_malloc(sizeof(double) * (node_count + 1), "malloc remaining bandwidth");
    setup->order_count = node_count;
    setup->base_bandwidth = 0.0;

    for (int node_index = 0; node_index < node_count; node_index++) {
        setup->order[node_index] = node_index;
        setup->base_profiles[node_index] = -1;
        const Node *node = &graph->nodes[node_index];
        if (!node->locked) {
            continue;
        }
        setup->base_bandwidth += bandwidth_score(node->bandwidth);
        for (int profile_index = 0; profile_index < PROFILE_COUNT; profile_index++) {
            const ConfigProfile *profile = &CONFIG_PROFILES[profile_index];
            if (strcmp(profile->channel, node->channel) == 0 &&
                strcmp(profile->bandwidth, node->bandwidth) == 0 &&
                strcmp(profile->frequency, node->frequency) == 0) {
                setup->base_profiles[node_index] = profile_index;
                break;
            }
        }
    }
    sort_indices_by_degree(graph, setup->order, node_count);

    setup->remaining_bandwidth[node_count] = 0.0;
    for (int depth = node_count - 1; depth >= 0; depth--) {
        int node_index = setup->order[depth];
        double node_bound = node_is_fixed(graph, setup->base_profiles, node_index)
            ? 0.0
            : max_bandwidth_for_frequency(graph->nodes[node_index].frequency);
        setup->remaining_bandwidth[depth] = setup->remaining_bandwidth[depth + 1] + node_bound;
    }
}

static void free_setup(SearchSetup *setup) {
    free(setup->order);
    free(setup->base_profiles);
    free(setup->remaining_bandwidth);
}

// Atribui a cada no, na ordem de grau, o melhor perfil local; e a primeira folha da busca exata.
static AssignmentCost greedy_assign(const SearchSetup *setup, int *profiles) {
    const Graph *graph = setup->graph;
    ProfileCandidate candidates[PROFILE_COUNT];
    AssignmentCost cost = {0, 0.0, setup->base_bandwidth};
    memcpy(profiles, setup->base_profiles, sizeof(int) * graph->node_count);

    for (int depth = 0; depth < setup->order_count; depth++) {
        int node_index = setup->order[depth];
        if (node_is_fixed(graph, profiles, node_index)) {
            continue;
        }
        int candidate_count = collect_candidates(graph, node_index, profiles, candidates);
        if (candidate_count == 0) {
            continue;
        }
        profiles[node_index] = candidates[0].profile_index;
        apply_candidate(&cost, &candidates[0]);
    }
    return cost;
}

static ProposedConfig *proposals_from_profiles(const Graph *graph, const int *profiles) {
    ProposedConfig *proposals = calloc((size_t) (graph->node_count > 0 ? graph->node_count : 1), sizeof(ProposedConfig));
    if (!proposals) {
        perror("calloc proposals");
        exit(1);
    }
    for (int node_index = 0; node_index < graph->node_count; node_index++) {
        int chosen_profile = profiles[node_index];
        const Node *node = &graph->nodes[node_index];
        if (chosen_profile < 0) {
            proposals[node_index] = (ProposedConfig){node->channel, node->bandwidth, node->frequency};
            continue;
        }
        proposals[node_index] = (ProposedConfig){
            CONFIG_PROFILES[chosen_profile].channel,
            CONFIG_PROFILES[chosen_profile].bandwidth,
            CONFIG_PROFILES[chosen_profile].frequency,
        };
    }
    return proposals;
}

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
        if (node_is_fixed(graph, profiles, node_index)) {
            depth++;
            continue;
        }
        ProfileCandidate candidates[PROFILE_COUNT];
        int candidate_count = collect_candidates(graph, node_index, profiles, candidates);
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
            apply_candidate(&next.cost, &candidates[candidate_index]);

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

static bool stream_event(int fd, pthread_mutex_t *lock, const char *type, cJSON *payload) {
    cJSON *event = cJSON_CreateObject();
    cJSON_AddStringToObject(event, "type", type);
    cJSON_AddItemToObject(event, "payload", payload);
    char *text = cJSON_PrintUnformatted(event);
    cJSON_Delete(event);
    pthread_mutex_lock(lock);
    int written = dprintf(fd, "%s\n", text);
    pthread_mutex_unlock(lock);
    free(text);
    return written >= 0;
}

// Envia o andamento da busca exata: a solucao gulosa ja existe e as tarefas restantes validam alternativas.
static void emit_search_progress(ParallelSearch *search, int completed_tasks) {
    if (search->stream_fd < 0 || !search->stream_lock || !search->job || is_cancelled(search->job)) {
        return;
    }

    pthread_mutex_lock(&search->best_lock);
    int best_conflicts = search->best_cost.conflicts;
    pthread_mutex_unlock(&search->best_lock);

    double percentage = search->task_count > 0 ? (95.0 * completed_tasks) / search->task_count : 95.0;
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
    if (!stream_event(search->stream_fd, search->stream_lock, "progress", payload)) {
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
        if (search->deadline > 0.0 && monotonic_seconds() >= search->deadline) {
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

// Poda o ramo se nem o limite otimista supera a melhor solucao. Em empate, vence a tarefa de menor indice,
// o que reproduz o resultado da busca sequencial independentemente do numero de threads.
static bool can_prune(WorkerState *worker, int depth) {
    refresh_best_snapshot(worker);
    AssignmentCost bound = worker->current;
    bound.bandwidth += worker->search->setup->remaining_bandwidth[depth];
    int comparison = compare_costs(&bound, &worker->best_snapshot);
    if (comparison > 0) {
        return true;
    }
    return comparison == 0 && worker->best_task_snapshot <= worker->task_index;
}

static void record_leaf(WorkerState *worker) {
    ParallelSearch *search = worker->search;
    pthread_mutex_lock(&search->best_lock);
    int comparison = compare_costs(&worker->current, &search->best_cost);
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
    if (node_is_fixed(graph, worker->profiles, node_index)) {
        search_depth(worker, depth + 1);
        return;
    }

    ProfileCandidate candidates[PROFILE_COUNT];
    int candidate_count = collect_candidates(graph, node_index, worker->profiles, candidates);
    if (candidate_count == 0) {
        search_depth(worker, depth + 1);
        return;
    }

    AssignmentCost previous_cost = worker->current;
    int previous_profile = worker->profiles[node_index];
    for (int candidate_index = 0; candidate_index < candidate_count; candidate_index++) {
        worker->profiles[node_index] = candidates[candidate_index].profile_index;
        apply_candidate(&worker->current, &candidates[candidate_index]);
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
        .profiles = checked_malloc(sizeof(int) * node_count, "malloc worker profiles"),
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

ProposedConfig *build_greedy_proposals(const Graph *graph, Job *job, AssignmentStats *stats) {
    SearchSetup setup;
    setup_search(graph, &setup);
    int *profiles = checked_malloc(sizeof(int) * graph->node_count, "malloc greedy profiles");
    AssignmentCost cost = greedy_assign(&setup, profiles);
    ProposedConfig *proposals = proposals_from_profiles(graph, profiles);

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
        };
    }
    analysis_log(ANALYSIS_LOG_INFO, job ? job->id : NULL, "guloso concluido nodes=%d conflicts=%d", graph->node_count, cost.conflicts);

    free(profiles);
    free_setup(&setup);
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
        "backtracking iniciado nodes=%d edges=%d threads=%d time_limit=%.1fs",
        graph->node_count,
        graph->edge_count,
        thread_count,
        time_limit
    );

    SearchSetup setup;
    setup_search(graph, &setup);
    int *best_profiles = checked_malloc(sizeof(int) * graph->node_count, "malloc best profiles");
    AssignmentCost initial = greedy_assign(&setup, best_profiles);

    int *profiles = checked_malloc(sizeof(int) * graph->node_count, "malloc task profiles");
    memcpy(profiles, setup.base_profiles, sizeof(int) * graph->node_count);
    SearchTask *tasks = NULL;
    int task_count = 0;
    int task_capacity = 0;
    SearchTask root = {.length = 0, .start_depth = 0, .cost = {0, 0.0, setup.base_bandwidth}};
    enumerate_tasks(&setup, profiles, 0, root, TASK_EXPANSION_LEVELS, &tasks, &task_count, &task_capacity);
    free(profiles);

    ParallelSearch search = {
        .setup = &setup,
        .tasks = tasks,
        .task_count = task_count,
        .best_cost = initial,
        .best_task = 0,
        .best_profiles = best_profiles,
        .deadline = time_limit > 0.0 ? monotonic_seconds() + time_limit : 0.0,
        .job = job,
        .stream_fd = options ? options->stream_fd : -1,
        .stream_lock = options ? options->stream_lock : NULL,
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

    pthread_t *workers = checked_malloc(sizeof(pthread_t) * worker_count, "malloc search workers");
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

    ProposedConfig *proposals = proposals_from_profiles(graph, best_profiles);
    free(workers);
    free(tasks);
    free(best_profiles);
    free_setup(&setup);
    return proposals;
}

int search_profile_count(void) {
    return PROFILE_COUNT;
}

ProposedConfig search_profile_at(int index) {
    ProposedConfig profile = {NULL, NULL, NULL};
    if (index >= 0 && index < PROFILE_COUNT) {
        profile.channel = CONFIG_PROFILES[index].channel;
        profile.bandwidth = CONFIG_PROFILES[index].bandwidth;
        profile.frequency = CONFIG_PROFILES[index].frequency;
    }
    return profile;
}
