#define _POSIX_C_SOURCE 200809L

#include "backtracking.h"

#include <cjson/cJSON.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

typedef struct {
    const char *channel;
    const char *bandwidth;
    const char *frequency;
} ConfigProfile;

typedef struct {
    int *order;
    int order_count;
    int *assigned_profiles;
    int *best_profiles;
    int current_conflicts;
    int best_conflicts;
    double current_interference_score;
    double best_interference_score;
    double current_bandwidth_score;
    double best_bandwidth_score;
    const Graph *graph;
    Job *job;
} AssignmentSearchState;

typedef struct {
    const Graph *graph;
    const int *order;
    int order_count;
    int anchor_depth;
    int anchor_node_index;
    const int *branch_profiles;
    int branch_count;
    int next_branch;
    double base_bandwidth_score;
    int *base_assigned_profiles;
    int *best_profiles;
    int best_conflicts;
    double best_interference_score;
    double best_bandwidth_score;
    int deepest_assigned_nodes;
    atomic_int solution_found;
    int stream_fd;
    pthread_mutex_t *stream_lock;
    pthread_mutex_t best_lock;
    pthread_mutex_t branch_lock;
    Job *job;
} AssignmentParallelContext;

typedef struct {
    int profile_index;
    int delta_conflicts;
    double delta_interference_score;
} ProfileCandidate;

static const ConfigProfile CONFIG_PROFILES[] = {
    {"1", "60 MHz", "2.4 GHz"},
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

double interference_percentage_for_config(
    const Node *left,
    const char *left_channel,
    const char *left_bandwidth,
    const char *left_frequency,
    const Node *right,
    const char *right_channel,
    const char *right_bandwidth,
    const char *right_frequency
);

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

static void emit_assignment_progress(
    int stream_fd,
    pthread_mutex_t *stream_lock,
    Job *job,
    int assigned_nodes,
    int total_nodes,
    int best_conflicts,
    int edge_count
) {
    if (stream_fd < 0 || !stream_lock || !job || is_cancelled(job) || total_nodes <= 0) {
        return;
    }

    cJSON *payload = cJSON_CreateObject();
    cJSON_AddStringToObject(payload, "stage", "assignment");
    cJSON_AddNumberToObject(payload, "assigned_nodes", assigned_nodes);
    cJSON_AddNumberToObject(payload, "total_nodes", total_nodes);
    bool complete_assignment_found = assigned_nodes >= total_nodes;
    double displayed_nodes = complete_assignment_found ? (double) (total_nodes - 1) : (double) assigned_nodes;
    if (displayed_nodes < 0.0) {
        displayed_nodes = 0.0;
    }
    double percentage = (95.0 * displayed_nodes) / total_nodes;
    double stage_percentage = percentage;
    if (percentage > 95.0) { percentage = 95.0; }
    if (stage_percentage > 95.0) { stage_percentage = 95.0; }
    cJSON_AddNumberToObject(payload, "percentage", percentage);
    cJSON_AddNumberToObject(payload, "stage_percentage", stage_percentage);
    cJSON_AddNumberToObject(payload, "best_conflicts", best_conflicts <= edge_count ? best_conflicts : -1);
    cJSON_AddBoolToObject(payload, "complete_assignment_found", complete_assignment_found);
    analysis_log(
        ANALYSIS_LOG_DEBUG,
        job ? job->id : NULL,
        "progresso atribuicao assigned=%d/%d best_conflicts=%d complete=%s",
        assigned_nodes,
        total_nodes,
        best_conflicts <= edge_count ? best_conflicts : -1,
        complete_assignment_found ? "true" : "false"
    );
    if (!stream_event(stream_fd, stream_lock, "progress", payload)) {
        atomic_store(&job->cancelled, 1);
    }
}

static void maybe_emit_assignment_depth_progress(AssignmentParallelContext *ctx, int assigned_nodes) {
    if (!ctx || assigned_nodes <= 0) {
        return;
    }

    pthread_mutex_lock(&ctx->best_lock);
    if (assigned_nodes <= ctx->deepest_assigned_nodes) {
        pthread_mutex_unlock(&ctx->best_lock);
        return;
    }

    ctx->deepest_assigned_nodes = assigned_nodes;
    int best_conflicts = ctx->best_conflicts;
    pthread_mutex_unlock(&ctx->best_lock);

    emit_assignment_progress(
        ctx->stream_fd,
        ctx->stream_lock,
        ctx->job,
        assigned_nodes,
        ctx->graph->node_count,
        best_conflicts,
        ctx->graph->edge_count
    );
}

static int compare_node_degree_desc(const Graph *graph, int left, int right) {
    int left_degree = graph->nodes[left].neighbor_count;
    int right_degree = graph->nodes[right].neighbor_count;
    if (left_degree != right_degree) {
        return right_degree - left_degree;
    }
    return strcmp(graph->nodes[left].id, graph->nodes[right].id);
}

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

static double bandwidth_score(const char *bandwidth) {
    if (!bandwidth || bandwidth[0] == '\0') {
        return 0.0;
    }
    double score = atof(bandwidth);
    return score > 0.0 ? score : 0.0;
}

static int node_conflict_delta(
    const Graph *graph,
    int node_index,
    int profile_index,
    const int *assigned_profiles,
    double *interference_score,
    bool *has_available_profile
) {
    int conflicts = 0;
    double total_interference = 0.0;
    const ConfigProfile *profile = &CONFIG_PROFILES[profile_index];
    const Node *node = &graph->nodes[node_index];

    *has_available_profile = false;

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

    *has_available_profile = true;
    if (interference_score) {
        *interference_score = total_interference;
    }
    return conflicts;
}

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

static void search_backtracking_assignment(AssignmentSearchState *state, int depth, AssignmentParallelContext *ctx) {
    if (state->job && is_cancelled(state->job)) {
        return;
    }
    if (ctx && atomic_load(&ctx->solution_found)) {
        return;
    }

    maybe_emit_assignment_depth_progress(ctx, depth);

    if (depth >= state->order_count) {
        if (!ctx || !atomic_exchange(&ctx->solution_found, 1)) {
            memcpy(state->best_profiles, state->assigned_profiles, sizeof(int) * state->graph->node_count);
            state->best_conflicts = state->current_conflicts;
            state->best_interference_score = state->current_interference_score;
            state->best_bandwidth_score = state->current_bandwidth_score;
            analysis_log(
                ANALYSIS_LOG_INFO,
                state->job ? state->job->id : NULL,
                "primeira solucao encontrada conflicts=%d interference=%.4f bandwidth=%.2f",
                state->best_conflicts,
                state->best_interference_score,
                state->best_bandwidth_score
            );
        }
        return;
    }

    int node_index = state->order[depth];
    const Node *node = &state->graph->nodes[node_index];

    if (node->locked && state->assigned_profiles[node_index] >= 0) {
        search_backtracking_assignment(state, depth + 1, ctx);
        return;
    }

    ProfileCandidate candidates[sizeof(CONFIG_PROFILES) / sizeof(CONFIG_PROFILES[0])];
    int candidate_count = 0;
    for (int profile_index = 0; profile_index < (int) (sizeof(CONFIG_PROFILES) / sizeof(CONFIG_PROFILES[0])); profile_index++) {
        const ConfigProfile *profile = &CONFIG_PROFILES[profile_index];
        if (strcmp(profile->frequency, node->frequency) != 0) {
            continue;
        }

        bool has_available_profile = false;
        double delta_interference_score = 0.0;
        int delta_conflicts = node_conflict_delta(
            state->graph,
            node_index,
            profile_index,
            state->assigned_profiles,
            &delta_interference_score,
            &has_available_profile
        );
        if (!has_available_profile) {
            continue;
        }
        candidates[candidate_count++] = (ProfileCandidate){
            .profile_index = profile_index,
            .delta_conflicts = delta_conflicts,
            .delta_interference_score = delta_interference_score,
        };
    }

    if (candidate_count == 0) {
        search_backtracking_assignment(state, depth + 1, ctx);
        return;
    }

    qsort(candidates, (size_t) candidate_count, sizeof(ProfileCandidate), compare_profile_candidates);

    for (int candidate_index = 0; candidate_index < candidate_count; candidate_index++) {
        if (ctx && atomic_load(&ctx->solution_found)) {
            return;
        }
        int profile_index = candidates[candidate_index].profile_index;
        const ConfigProfile *profile = &CONFIG_PROFILES[profile_index];
        int previous_profile = state->assigned_profiles[node_index];
        int previous_conflicts = state->current_conflicts;
        double previous_interference_score = state->current_interference_score;
        double previous_bandwidth_score = state->current_bandwidth_score;

        state->assigned_profiles[node_index] = profile_index;
        state->current_conflicts += candidates[candidate_index].delta_conflicts;
        state->current_interference_score += candidates[candidate_index].delta_interference_score;
        state->current_bandwidth_score += bandwidth_score(profile->bandwidth);

        search_backtracking_assignment(state, depth + 1, ctx);

        state->assigned_profiles[node_index] = previous_profile;
        state->current_conflicts = previous_conflicts;
        state->current_interference_score = previous_interference_score;
        state->current_bandwidth_score = previous_bandwidth_score;
    }
}

static void merge_assignment_best(AssignmentParallelContext *ctx, const AssignmentSearchState *state) {
    pthread_mutex_lock(&ctx->best_lock);
    if (atomic_load(&ctx->solution_found) &&
        state->best_conflicts <= ctx->graph->edge_count &&
        state->best_interference_score < 1e18) {
        memcpy(ctx->best_profiles, state->best_profiles, sizeof(int) * ctx->graph->node_count);
        ctx->best_conflicts = state->best_conflicts;
        ctx->best_interference_score = state->best_interference_score;
        ctx->best_bandwidth_score = state->best_bandwidth_score;
    }
    int best_conflicts = ctx->best_conflicts;
    int deepest_assigned_nodes = ctx->deepest_assigned_nodes;
    pthread_mutex_unlock(&ctx->best_lock);

    emit_assignment_progress(
        ctx->stream_fd,
        ctx->stream_lock,
        ctx->job,
        deepest_assigned_nodes,
        ctx->graph->node_count,
        best_conflicts,
        ctx->graph->edge_count
    );
}

static void *assignment_worker(void *arg) {
    AssignmentParallelContext *ctx = arg;
    while (!is_cancelled(ctx->job)) {
        pthread_mutex_lock(&ctx->branch_lock);
        int branch_index = ctx->next_branch++;
        pthread_mutex_unlock(&ctx->branch_lock);

        if (branch_index >= ctx->branch_count) {
            break;
        }

        int profile_index = ctx->branch_profiles[branch_index];
        bool has_available_profile = false;
        double delta_interference_score = 0.0;
        int delta_conflicts = node_conflict_delta(
            ctx->graph,
            ctx->anchor_node_index,
            profile_index,
            ctx->base_assigned_profiles,
            &delta_interference_score,
            &has_available_profile
        );
        if (!has_available_profile) {
            continue;
        }

        int node_count = ctx->graph->node_count;
        int *assigned_profiles = malloc(sizeof(int) * node_count);
        int *best_profiles = malloc(sizeof(int) * node_count);
        if (!assigned_profiles || !best_profiles) {
            perror("malloc assignment worker profiles");
            exit(1);
        }
        memcpy(assigned_profiles, ctx->base_assigned_profiles, sizeof(int) * node_count);
        memcpy(best_profiles, ctx->base_assigned_profiles, sizeof(int) * node_count);
        assigned_profiles[ctx->anchor_node_index] = profile_index;

        AssignmentSearchState state = {
            .order = (int *) ctx->order,
            .order_count = ctx->order_count,
            .assigned_profiles = assigned_profiles,
            .best_profiles = best_profiles,
            .current_conflicts = delta_conflicts,
            .best_conflicts = ctx->graph->edge_count + 1,
            .current_interference_score = delta_interference_score,
            .best_interference_score = 1e18,
            .current_bandwidth_score = ctx->base_bandwidth_score + bandwidth_score(CONFIG_PROFILES[profile_index].bandwidth),
            .best_bandwidth_score = -1.0,
            .graph = ctx->graph,
            .job = ctx->job,
        };
        maybe_emit_assignment_depth_progress(ctx, ctx->anchor_depth + 1);
        search_backtracking_assignment(&state, ctx->anchor_depth + 1, ctx);
        merge_assignment_best(ctx, &state);

        free(assigned_profiles);
        free(best_profiles);
    }
    return NULL;
}

ProposedConfig *build_backtracking_proposals(
    const Graph *graph,
    Job *job,
    int thread_count,
    int stream_fd,
    pthread_mutex_t *stream_lock
) {
    analysis_log(
        ANALYSIS_LOG_INFO,
        job ? job->id : NULL,
        "backtracking de atribuicao iniciado nodes=%d edges=%d threads=%d",
        graph->node_count,
        graph->edge_count,
        thread_count
    );
    const int profile_count = (int) (sizeof(CONFIG_PROFILES) / sizeof(CONFIG_PROFILES[0]));
    ProposedConfig *proposals = calloc((size_t) graph->node_count, sizeof(ProposedConfig));
    int *assigned_profiles = malloc(sizeof(int) * graph->node_count);
    int *best_profiles = malloc(sizeof(int) * graph->node_count);
    int *order = malloc(sizeof(int) * graph->node_count);
    if (!proposals || !assigned_profiles || !best_profiles || !order) {
        perror("malloc proposals");
        exit(1);
    }

    for (int i = 0; i < graph->node_count; i++) {
        assigned_profiles[i] = -1;
        best_profiles[i] = -1;
    }

    int order_count = 0;
    for (int i = 0; i < graph->node_count; i++) {
        order[order_count++] = i;
    }
    sort_indices_by_degree(graph, order, order_count);

    double initial_bandwidth_score = 0.0;
    for (int i = 0; i < graph->node_count; i++) {
        const Node *node = &graph->nodes[i];
        if (!node->locked) {
            continue;
        }
        initial_bandwidth_score += bandwidth_score(node->bandwidth);
    }

    for (int node_index = 0; node_index < graph->node_count; node_index++) {
        const Node *node = &graph->nodes[node_index];
        if (node->locked) {
            for (int profile_index = 0; profile_index < profile_count; profile_index++) {
                const ConfigProfile *profile = &CONFIG_PROFILES[profile_index];
                if (strcmp(profile->channel, node->channel) == 0 &&
                    strcmp(profile->bandwidth, node->bandwidth) == 0 &&
                    strcmp(profile->frequency, node->frequency) == 0) {
                    assigned_profiles[node_index] = profile_index;
                    break;
                }
            }
        }
    }

    int anchor_depth = 0;
    while (anchor_depth < order_count) {
        int node_index = order[anchor_depth];
        if (!(graph->nodes[node_index].locked && assigned_profiles[node_index] >= 0)) {
            break;
        }
        anchor_depth++;
    }

    if (anchor_depth >= order_count) {
        memcpy(best_profiles, assigned_profiles, sizeof(int) * graph->node_count);
    } else {
        int anchor_node_index = order[anchor_depth];
        ProfileCandidate *branch_candidates = malloc(sizeof(ProfileCandidate) * profile_count);
        int *branch_profiles = malloc(sizeof(int) * profile_count);
        int branch_count = 0;
        for (int profile_index = 0; profile_index < profile_count; profile_index++) {
            if (strcmp(CONFIG_PROFILES[profile_index].frequency, graph->nodes[anchor_node_index].frequency) != 0) {
                continue;
            }

            bool has_available_profile = false;
            double delta_interference_score = 0.0;
            int delta_conflicts = node_conflict_delta(
                graph,
                anchor_node_index,
                profile_index,
                assigned_profiles,
                &delta_interference_score,
                &has_available_profile
            );
            if (!has_available_profile) {
                continue;
            }
            branch_candidates[branch_count++] = (ProfileCandidate){
                .profile_index = profile_index,
                .delta_conflicts = delta_conflicts,
                .delta_interference_score = delta_interference_score,
            };
        }
        qsort(branch_candidates, (size_t) branch_count, sizeof(ProfileCandidate), compare_profile_candidates);
        for (int index = 0; index < branch_count; index++) {
            branch_profiles[index] = branch_candidates[index].profile_index;
        }
        free(branch_candidates);

        AssignmentParallelContext ctx = {
            .graph = graph,
            .order = order,
            .order_count = order_count,
            .anchor_depth = anchor_depth,
            .anchor_node_index = anchor_node_index,
            .branch_profiles = branch_profiles,
            .branch_count = branch_count,
            .next_branch = 0,
            .base_bandwidth_score = initial_bandwidth_score,
            .base_assigned_profiles = assigned_profiles,
            .best_profiles = best_profiles,
            .best_conflicts = graph->edge_count + 1,
            .best_interference_score = 1e18,
            .best_bandwidth_score = -1.0,
            .deepest_assigned_nodes = anchor_depth,
            .solution_found = 0,
            .stream_fd = stream_fd,
            .stream_lock = stream_lock,
            .job = job,
        };
        pthread_mutex_init(&ctx.best_lock, NULL);
        pthread_mutex_init(&ctx.branch_lock, NULL);

        int worker_count = thread_count > 0 ? thread_count : 1;
        if (worker_count > branch_count) {
            worker_count = branch_count;
        }
        if (worker_count < 1) {
            worker_count = 1;
        }
        analysis_log(
            ANALYSIS_LOG_DEBUG,
            job ? job->id : NULL,
            "atribuicao paralela anchor_depth=%d branch_count=%d workers=%d",
            anchor_depth,
            branch_count,
            worker_count
        );

        pthread_t *workers = malloc(sizeof(pthread_t) * worker_count);
        if (!workers) {
            perror("malloc assignment workers");
            exit(1);
        }
        for (int worker_index = 0; worker_index < worker_count; worker_index++) {
            pthread_create(&workers[worker_index], NULL, assignment_worker, &ctx);
        }
        for (int worker_index = 0; worker_index < worker_count; worker_index++) {
            pthread_join(workers[worker_index], NULL);
        }

        pthread_mutex_destroy(&ctx.best_lock);
        pthread_mutex_destroy(&ctx.branch_lock);
        free(workers);
        free(branch_profiles);
    }

    for (int node_index = 0; node_index < graph->node_count; node_index++) {
        int chosen_profile = best_profiles[node_index];
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

    free(assigned_profiles);
    free(best_profiles);
    free(order);
    analysis_log(
        ANALYSIS_LOG_INFO,
        job ? job->id : NULL,
        "backtracking de atribuicao concluido nodes=%d",
        graph->node_count
    );
    return proposals;
}
