#ifndef ANALYSIS_SERVICE_STRATEGIES_ASSIGNMENT_H
#define ANALYSIS_SERVICE_STRATEGIES_ASSIGNMENT_H

#include "strategy.h"

// Pecas comuns as estrategias: a atribuicao e um indice de perfil por AP (-1 = mantem a configuracao atual),
// avaliada pelo criterio de otimizacao (objective.h).

// Perfil candidato para um AP e o custo incremental de atribui-lo, frente aos vizinhos ja definidos.
typedef struct {
    int profile_index;
    AssignmentCost delta;
} ProfileCandidate;

// Dados comuns as estrategias: objetivo, perfis disponiveis, ordem de visita, perfis fixos e, por
// profundidade, os limites otimistas do que falta atribuir (maior banda e menor potencia possiveis).
typedef struct {
    const Graph *graph;
    // Perfis da busca seguidos dos perfis proprios dos APs travados fora deles: so os searchable_count primeiros
    // sao oferecidos aos APs livres; cada perfil extra serve apenas ao AP travado que o originou.
    const ProfileSet *profiles;
    int searchable_count;
    ProfileSet extended_profiles;
    ProposedConfig *extended_items;
    OptimizationObjective objective;
    int *order;
    int order_count;
    int *base_profiles;
    double base_bandwidth;
    long long base_power_mw;
    double *remaining_bandwidth;
    long long *remaining_min_power_mw;
} SearchSetup;

void *assignment_malloc(size_t size, const char *what);
double assignment_monotonic_seconds(void);
// Tempo de CPU (s) consumido ate agora pela thread que chama.
double assignment_thread_cpu_seconds(void);
double assignment_bandwidth_score(const char *bandwidth);
bool assignment_same_band(const char *left, const char *right);

// AP travado: fica fixo e nao entra na busca. Se a configuracao dele nao esta entre os perfis da busca, ele
// recebe um perfil proprio, para manter a configuracao e ter a interferencia com os vizinhos no custo.
bool assignment_node_is_fixed(const Graph *graph, const int *profiles, int node_index);

// Conflitos e interferencia (w * s) de dar ao AP o perfil indicado, frente aos vizinhos com perfil definido.
int assignment_conflict_delta(
    const SearchSetup *setup,
    int node_index,
    int profile_index,
    const int *assigned_profiles,
    double *interference_score
);

// Perfis da faixa do AP com o custo incremental de cada um, do melhor para o pior no objetivo.
int assignment_collect_candidates(
    const SearchSetup *setup,
    int node_index,
    const int *assigned_profiles,
    ProfileCandidate *candidates
);

void assignment_setup(const Graph *graph, const ProfileSet *profiles, OptimizationObjective objective, SearchSetup *setup);
void assignment_free_setup(SearchSetup *setup);

// Atribui a cada AP, na ordem de grau, o melhor perfil local (o guloso) e devolve o custo da atribuicao.
AssignmentCost assignment_greedy(const SearchSetup *setup, int *profiles);

ProposedConfig *assignment_proposals(const SearchSetup *setup, const int *profiles);

// Envia um evento NDJSON do streaming (progress, result...).
bool assignment_stream_event(int fd, pthread_mutex_t *lock, const char *type, cJSON *payload);

#endif
