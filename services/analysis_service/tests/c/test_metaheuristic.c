// Testes da base comum das metaheuristicas: custo incremental, vizinhanca, APs travados e gerador aleatorio.
// Compilados e executados no estagio "test" do Dockerfile (docker build --target test).
#define _POSIX_C_SOURCE 200809L

#include "../../src/analysis_service.h"
#include "../../src/strategies/backtracking.h"
#include "../../src/strategies/metaheuristic.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;

#define CHECK(condition, ...) do { \
    if (!(condition)) { \
        failures++; \
        fprintf(stderr, "FALHOU %s:%d: ", __FILE__, __LINE__); \
        fprintf(stderr, __VA_ARGS__); \
        fprintf(stderr, "\n"); \
    } \
} while (0)

// Grafo aleatorio e reprodutivel: APs proximos (muitas sobreposicoes) em 2,4 e 5 GHz; os de indice
// multiplo de 7 ficam travados no canal 6 (2,4 GHz) ou 44 (5 GHz), que estao nos perfis padrao.
static void build_test_graph(Graph *graph, int node_count, uint64_t seed) {
    MetaRng rng;
    meta_rng_seed(&rng, seed, 0);
    cJSON *payload = cJSON_CreateObject();
    cJSON *aps = cJSON_AddArrayToObject(payload, "aps");
    const char *channels24[] = {"1", "6", "11", "3"};
    const char *channels5[] = {"36", "44", "149", "100"};
    for (int index = 0; index < node_count; index++) {
        bool band24 = index % 2 == 0;
        bool locked = index % 7 == 0;
        char id[16];
        snprintf(id, sizeof(id), "ap%d", index);
        cJSON *ap = cJSON_CreateObject();
        cJSON_AddStringToObject(ap, "id", id);
        cJSON_AddNumberToObject(ap, "x", -23.55 + meta_rng_unit(&rng) * 0.0005);
        cJSON_AddNumberToObject(ap, "y", -46.63 + meta_rng_unit(&rng) * 0.0005);
        cJSON_AddStringToObject(ap, "frequency", band24 ? "2.4 GHz" : "5 GHz");
        cJSON_AddStringToObject(ap, "bandwidth", locked ? "20 MHz" : (meta_rng_below(&rng, 2) ? "20 MHz" : "40 MHz"));
        cJSON_AddStringToObject(ap, "channel", locked ? (band24 ? "6" : "44") : (band24 ? channels24[meta_rng_below(&rng, 4)] : channels5[meta_rng_below(&rng, 4)]));
        cJSON_AddBoolToObject(ap, "locked", locked);
        cJSON_AddItemToArray(aps, ap);
    }
    char *error = NULL;
    bool built = analysis_build_graph(payload, graph, &error);
    CHECK(built, "montagem do grafo: %s", error ? error : "?");
    free(error);
    cJSON_Delete(payload);
}

static bool same_cost(const AssignmentCost *left, const AssignmentCost *right) {
    return left->conflicts == right->conflicts
        && fabs(left->interference - right->interference) < 1e-6
        && left->bandwidth == right->bandwidth
        && left->power_mw == right->power_mw;
}

static void test_rng_is_reproducible(void) {
    MetaRng a, b, other_stream;
    meta_rng_seed(&a, 12345, 0);
    meta_rng_seed(&b, 12345, 0);
    meta_rng_seed(&other_stream, 12345, 1);
    int differences = 0;
    for (int index = 0; index < 1000; index++) {
        uint64_t value = meta_rng_next(&a);
        CHECK(value == meta_rng_next(&b), "mesma semente deu sequencias diferentes na posicao %d", index);
        differences += value != meta_rng_next(&other_stream);
    }
    CHECK(differences > 990, "outra faixa (fluxo) deveria ter outra sequencia: %d diferencas", differences);

    int counts[7] = {0};
    for (int index = 0; index < 70000; index++) {
        int value = meta_rng_below(&a, 7);
        CHECK(value >= 0 && value < 7, "meta_rng_below fora do intervalo: %d", value);
        if (value >= 0 && value < 7) {
            counts[value]++;
        }
        double unit = meta_rng_unit(&a);
        CHECK(unit >= 0.0 && unit < 1.0, "meta_rng_unit fora de [0, 1): %f", unit);
    }
    for (int value = 0; value < 7; value++) {
        CHECK(counts[value] > 9000 && counts[value] < 11000, "distribuicao desigual: %d saiu %d vezes", value, counts[value]);
    }
}

// O custo mantido pelos deltas deve coincidir com o recalculo completo a cada movimento.
static void test_incremental_cost_matches_full_cost(OptimizationObjective objective, MetaInitialSolution initial) {
    Graph graph;
    build_test_graph(&graph, 80, 99);
    MetaProblem problem;
    meta_problem_init(&problem, &graph, default_search_profiles(), objective);
    MetaRng rng;
    meta_rng_seed(&rng, 7, 0);
    int *profiles = malloc(sizeof(int) * (size_t) graph.node_count);
    AssignmentCost cost = meta_initial_solution(&problem, &rng, initial, profiles);
    AssignmentCost full = meta_full_cost(&problem, profiles);
    CHECK(same_cost(&cost, &full), "custo da solucao inicial difere do recalculo completo");

    int mismatches = 0;
    for (int step = 0; step < 20000; step++) {
        MetaMove move;
        CHECK(meta_random_move(&problem, &rng, profiles, &move), "sem movimento possivel");
        AssignmentCost delta = meta_move_delta(&problem, profiles, &move);
        meta_apply_move(profiles, &cost, &move, &delta);
        full = meta_full_cost(&problem, profiles);
        if (!same_cost(&cost, &full)) {
            mismatches++;
        }
        // Recomeca do custo exato para que o teste meca o erro de cada movimento, e nao o acumulado.
        cost = full;
    }
    CHECK(mismatches == 0, "custo incremental difere do completo em %d movimentos (objetivo %d)", mismatches, objective);
    free(profiles);
    meta_problem_free(&problem);
    analysis_free_graph(&graph);
}

// A solucao gulosa da base e a do backtracking/guloso: o custo dela deve bater com o recalculo completo.
static void test_greedy_cost_matches_full_cost(void) {
    Graph graph;
    build_test_graph(&graph, 60, 5);
    MetaProblem problem;
    meta_problem_init(&problem, &graph, default_search_profiles(), OBJECTIVE_DEFAULT);
    MetaRng rng;
    meta_rng_seed(&rng, 1, 0);
    int *profiles = malloc(sizeof(int) * (size_t) graph.node_count);
    AssignmentCost greedy = meta_initial_solution(&problem, &rng, META_INITIAL_GREEDY, profiles);
    AssignmentCost full = meta_full_cost(&problem, profiles);
    CHECK(same_cost(&greedy, &full), "custo do guloso (%d, %f) difere do completo (%d, %f)",
          greedy.conflicts, greedy.interference, full.conflicts, full.interference);
    free(profiles);
    meta_problem_free(&problem);
    analysis_free_graph(&graph);
}

// Vizinhos: so APs moveis, nunca o perfil atual, sempre um perfil da faixa do AP; travados nunca mudam.
static void test_neighbors_respect_bands_and_locked_access_points(void) {
    Graph graph;
    build_test_graph(&graph, 50, 11);
    MetaProblem problem;
    meta_problem_init(&problem, &graph, default_search_profiles(), OBJECTIVE_DEFAULT);
    const ProfileSet *profiles_set = problem.setup.profiles;
    MetaRng rng;
    meta_rng_seed(&rng, 3, 0);
    int *profiles = malloc(sizeof(int) * (size_t) graph.node_count);
    meta_initial_solution(&problem, &rng, META_INITIAL_RANDOM, profiles);
    int *locked_profiles = malloc(sizeof(int) * (size_t) graph.node_count);
    memcpy(locked_profiles, profiles, sizeof(int) * (size_t) graph.node_count);

    for (int index = 0; index < problem.mobile_count; index++) {
        CHECK(!graph.nodes[problem.mobile[index]].locked, "AP travado %s esta entre os moveis", graph.nodes[problem.mobile[index]].id);
    }
    for (int step = 0; step < 5000; step++) {
        MetaMove move;
        meta_random_move(&problem, &rng, profiles, &move);
        CHECK(move.profile_index != profiles[move.node_index], "vizinho repete o perfil atual");
        CHECK(assignment_same_band(profiles_set->items[move.profile_index].frequency, graph.nodes[move.node_index].frequency),
              "vizinho troca a faixa do AP %s", graph.nodes[move.node_index].id);
        AssignmentCost delta = meta_move_delta(&problem, profiles, &move);
        AssignmentCost cost = {0, 0.0, 0.0, 0};
        meta_apply_move(profiles, &cost, &move, &delta);
    }
    for (int node_index = 0; node_index < graph.node_count; node_index++) {
        if (graph.nodes[node_index].locked) {
            CHECK(profiles[node_index] == locked_profiles[node_index] && profiles[node_index] >= 0,
                  "AP travado %s mudou de perfil", graph.nodes[node_index].id);
        }
    }
    free(locked_profiles);
    free(profiles);
    meta_problem_free(&problem);
    analysis_free_graph(&graph);
}

int main(void) {
    test_rng_is_reproducible();
    test_greedy_cost_matches_full_cost();
    test_neighbors_respect_bands_and_locked_access_points();
    for (int objective = OBJECTIVE_DEFAULT; objective <= OBJECTIVE_ENERGY_FIRST; objective++) {
        test_incremental_cost_matches_full_cost((OptimizationObjective) objective, META_INITIAL_RANDOM);
    }
    test_incremental_cost_matches_full_cost(OBJECTIVE_DEFAULT, META_INITIAL_GREEDY);
    if (failures) {
        fprintf(stderr, "%d verificacao(oes) falharam\n", failures);
        return 1;
    }
    printf("testes da base das metaheuristicas: ok\n");
    return 0;
}
