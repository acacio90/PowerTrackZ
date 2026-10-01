#define _POSIX_C_SOURCE 200809L

#include "assignment.h"
#include "backtracking.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

double assignment_monotonic_seconds(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + (ts.tv_nsec / 1000000000.0);
}

double assignment_thread_cpu_seconds(void) {
    struct timespec ts;
    clock_gettime(CLOCK_THREAD_CPUTIME_ID, &ts);
    return ts.tv_sec + (ts.tv_nsec / 1000000000.0);
}

void *assignment_malloc(size_t size, const char *what) {
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
double assignment_bandwidth_score(const char *bandwidth) {
    if (!bandwidth || bandwidth[0] == '\0') {
        return 0.0;
    }
    double score = atof(bandwidth);
    return score > 0.0 ? score : 0.0;
}

// Compara faixas pelo valor numerico ("2.4 GHz" e "2.4GHz" sao a mesma faixa).
bool assignment_same_band(const char *left, const char *right) {
    double left_band = left ? atof(left) : 0.0;
    double right_band = right ? atof(right) : 0.0;
    return left_band > 0.0 && fabs(left_band - right_band) < 1e-9;
}

static bool same_profile(const ProposedConfig *profile, const Node *node) {
    return assignment_same_band(profile->frequency, node->frequency)
        && atoi(profile->channel) == atoi(node->channel)
        && assignment_bandwidth_score(profile->bandwidth) == assignment_bandwidth_score(node->bandwidth);
}

bool assignment_node_is_fixed(const Graph *graph, const int *profiles, int node_index) {
    return graph->nodes[node_index].locked && profiles[node_index] >= 0;
}

// Calcula o custo incremental de aplicar um perfil ao no atual frente aos vizinhos ja definidos.
int assignment_conflict_delta(
    const SearchSetup *setup,
    int node_index,
    int profile_index,
    const int *assigned_profiles,
    double *interference_score
) {
    const Graph *graph = setup->graph;
    int conflicts = 0;
    double total_interference = 0.0;
    const ProposedConfig *profile = &setup->profiles->items[profile_index];
    const Node *node = &graph->nodes[node_index];

    for (int neighbor_pos = 0; neighbor_pos < node->neighbor_count; neighbor_pos++) {
        int neighbor_index = node->neighbors[neighbor_pos];
        int neighbor_profile_index = assigned_profiles[neighbor_index];
        if (neighbor_profile_index < 0) {
            continue;
        }

        const ProposedConfig *neighbor_profile = &setup->profiles->items[neighbor_profile_index];
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

// Ordena os candidatos pelo custo incremental no objetivo (o melhor primeiro); em empate, pela ordem dos
// perfis. E a ordem de visita da busca exata e a escolha do guloso.
static void sort_candidates(OptimizationObjective objective, ProfileCandidate *candidates, int count) {
    for (int i = 1; i < count; i++) {
        ProfileCandidate current = candidates[i];
        int j = i - 1;
        while (j >= 0) {
            int comparison = compare_assignment_costs(objective, &candidates[j].delta, &current.delta);
            if (comparison < 0 || (comparison == 0 && candidates[j].profile_index < current.profile_index)) {
                break;
            }
            candidates[j + 1] = candidates[j];
            j--;
        }
        candidates[j + 1] = current;
    }
}

// Lista os perfis compativeis com a frequencia do no, ja ordenados pela prioridade de busca.
int assignment_collect_candidates(
    const SearchSetup *setup,
    int node_index,
    const int *assigned_profiles,
    ProfileCandidate *candidates
) {
    int candidate_count = 0;
    const Node *node = &setup->graph->nodes[node_index];
    for (int profile_index = 0; profile_index < setup->searchable_count; profile_index++) {
        const ProposedConfig *profile = &setup->profiles->items[profile_index];
        if (!assignment_same_band(profile->frequency, node->frequency)) {
            continue;
        }
        double delta_interference = 0.0;
        int delta_conflicts = assignment_conflict_delta(setup, node_index, profile_index, assigned_profiles, &delta_interference);
        candidates[candidate_count++] = (ProfileCandidate){
            .profile_index = profile_index,
            .delta = {
                .conflicts = delta_conflicts,
                .interference = delta_interference,
                .bandwidth = assignment_bandwidth_score(profile->bandwidth),
                .power_mw = objective_power_mw(profile->frequency, profile->bandwidth),
            },
        };
    }
    sort_candidates(setup->objective, candidates, candidate_count);
    return candidate_count;
}

static void apply_candidate(AssignmentCost *cost, const ProfileCandidate *candidate) {
    add_assignment_cost(cost, &candidate->delta);
}

static double max_bandwidth_for_frequency(const ProfileSet *profiles, int count, const char *frequency) {
    double best = 0.0;
    for (int profile_index = 0; profile_index < count; profile_index++) {
        if (assignment_same_band(profiles->items[profile_index].frequency, frequency)) {
            double score = assignment_bandwidth_score(profiles->items[profile_index].bandwidth);
            if (score > best) {
                best = score;
            }
        }
    }
    return best;
}

// Menor potencia (no criterio de otimizacao) entre os perfis da faixa; zero se a faixa nao tem perfis.
static long long min_power_for_frequency(const ProfileSet *profiles, int count, const char *frequency) {
    long long best = -1;
    for (int profile_index = 0; profile_index < count; profile_index++) {
        if (assignment_same_band(profiles->items[profile_index].frequency, frequency)) {
            long long power = objective_power_mw(profiles->items[profile_index].frequency, profiles->items[profile_index].bandwidth);
            if (best < 0 || power < best) {
                best = power;
            }
        }
    }
    return best < 0 ? 0 : best;
}

// Prepara ordem de visita, perfis dos APs travados e, por profundidade, os limites otimistas de banda
// (a maior possivel) e de potencia (a menor possivel) do que falta atribuir.
void assignment_setup(const Graph *graph, const ProfileSet *profiles, OptimizationObjective objective, SearchSetup *setup) {
    int node_count = graph->node_count;
    setup->graph = graph;
    const ProfileSet *search_profiles = profiles && profiles->count > 0 ? profiles : default_search_profiles();
    setup->profiles = search_profiles;
    setup->searchable_count = search_profiles->count;
    setup->extended_items = NULL;
    setup->objective = objective;
    setup->order = assignment_malloc(sizeof(int) * node_count, "malloc search order");
    setup->base_profiles = assignment_malloc(sizeof(int) * node_count, "malloc base profiles");
    setup->remaining_bandwidth = assignment_malloc(sizeof(double) * (node_count + 1), "malloc remaining bandwidth");
    setup->remaining_min_power_mw = assignment_malloc(sizeof(long long) * (node_count + 1), "malloc remaining power");
    setup->order_count = node_count;
    setup->base_bandwidth = 0.0;
    setup->base_power_mw = 0;

    for (int node_index = 0; node_index < node_count; node_index++) {
        setup->order[node_index] = node_index;
        setup->base_profiles[node_index] = -1;
        const Node *node = &graph->nodes[node_index];
        if (!node->locked) {
            continue;
        }
        setup->base_bandwidth += assignment_bandwidth_score(node->bandwidth);
        setup->base_power_mw += objective_power_mw(node->frequency, node->bandwidth);
        for (int profile_index = 0; profile_index < search_profiles->count; profile_index++) {
            if (same_profile(&search_profiles->items[profile_index], node)) {
                setup->base_profiles[node_index] = profile_index;
                break;
            }
        }
    }

    // APs travados fora dos perfis: cada um ganha um perfil proprio, no fim da lista, com a sua configuracao.
    int extra = 0;
    for (int node_index = 0; node_index < node_count; node_index++) {
        extra += graph->nodes[node_index].locked && setup->base_profiles[node_index] < 0;
    }
    if (extra > 0) {
        int total = search_profiles->count + extra;
        setup->extended_items = assignment_malloc(sizeof(ProposedConfig) * (size_t) total, "malloc locked profiles");
        memcpy(setup->extended_items, search_profiles->items, sizeof(ProposedConfig) * (size_t) search_profiles->count);
        int next = search_profiles->count;
        for (int node_index = 0; node_index < node_count; node_index++) {
            const Node *node = &graph->nodes[node_index];
            if (node->locked && setup->base_profiles[node_index] < 0) {
                setup->extended_items[next] = (ProposedConfig){node->channel, node->bandwidth, node->frequency};
                setup->base_profiles[node_index] = next++;
            }
        }
        setup->extended_profiles = (ProfileSet){setup->extended_items, total};
        setup->profiles = &setup->extended_profiles;
    }
    sort_indices_by_degree(graph, setup->order, node_count);

    setup->remaining_bandwidth[node_count] = 0.0;
    setup->remaining_min_power_mw[node_count] = 0;
    for (int depth = node_count - 1; depth >= 0; depth--) {
        int node_index = setup->order[depth];
        bool fixed = assignment_node_is_fixed(graph, setup->base_profiles, node_index);
        const char *frequency = graph->nodes[node_index].frequency;
        double bandwidth_bound = fixed ? 0.0 : max_bandwidth_for_frequency(setup->profiles, setup->searchable_count, frequency);
        long long power_bound = fixed ? 0 : min_power_for_frequency(setup->profiles, setup->searchable_count, frequency);
        setup->remaining_bandwidth[depth] = setup->remaining_bandwidth[depth + 1] + bandwidth_bound;
        setup->remaining_min_power_mw[depth] = setup->remaining_min_power_mw[depth + 1] + power_bound;
    }
}

void assignment_free_setup(SearchSetup *setup) {
    free(setup->order);
    free(setup->base_profiles);
    free(setup->remaining_bandwidth);
    free(setup->remaining_min_power_mw);
    free(setup->extended_items);
}

// Atribui a cada no, na ordem de grau, o melhor perfil local; e a primeira folha da busca exata.
AssignmentCost assignment_greedy(const SearchSetup *setup, int *profiles) {
    const Graph *graph = setup->graph;
    ProfileCandidate candidates[setup->profiles->count];
    AssignmentCost cost = {0, 0.0, setup->base_bandwidth, setup->base_power_mw};
    memcpy(profiles, setup->base_profiles, sizeof(int) * graph->node_count);

    for (int depth = 0; depth < setup->order_count; depth++) {
        int node_index = setup->order[depth];
        if (assignment_node_is_fixed(graph, profiles, node_index)) {
            continue;
        }
        int candidate_count = assignment_collect_candidates(setup, node_index, profiles, candidates);
        if (candidate_count == 0) {
            continue;
        }
        profiles[node_index] = candidates[0].profile_index;
        apply_candidate(&cost, &candidates[0]);
    }
    return cost;
}

ProposedConfig *assignment_proposals(const SearchSetup *setup, const int *profiles) {
    const Graph *graph = setup->graph;
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
        proposals[node_index] = setup->profiles->items[chosen_profile];
    }
    return proposals;
}

bool assignment_stream_event(int fd, pthread_mutex_t *lock, const char *type, cJSON *payload) {
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
