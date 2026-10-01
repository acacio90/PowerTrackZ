#ifndef ANALYSIS_SERVICE_STRATEGIES_GENETIC_H
#define ANALYSIS_SERVICE_STRATEGIES_GENETIC_H

#include "metaheuristic.h"

// Algoritmo Genetico sobre a base comum das metaheuristicas. Cada individuo e uma solucao da base (um perfil
// por AP), e a aptidao e o custo do criterio de otimizacao. Os operadores ficam aqui para o AG hibrido (#85)
// reutiliza-los. Ver o README.

typedef struct {
    int population_size;
    // Fracao da populacao inicial derivada do guloso (o proprio guloso e copias dele mutadas); o resto e aleatorio.
    double greedy_fraction;
    bool one_point_crossover;
    double crossover_rate;
    // Probabilidade de cada AP movel de um filho trocar de perfil.
    double mutation_rate;
    int tournament_size;
    // Individuos melhores que passam intactos para a geracao seguinte.
    int elitism;
} GeneticOptions;

// Populacao: os genes do individuo i ficam em genes[i * node_count .. (i + 1) * node_count).
typedef struct {
    int size;
    int node_count;
    int *genes;
    AssignmentCost *costs;
    // Na geracao recem-formada, os primeiros elite_count individuos sao a elite copiada da anterior.
    int elite_count;
} GeneticPopulation;

// Chamado a cada geracao recem-formada, antes da escolha da melhor solucao (o AG hibrido aplica a busca local
// aqui). Deve manter costs coerente com genes e respeitar o tempo e o cancelamento de "run".
typedef void (*GeneticGenerationHook)(void *hook_context, MetaRun *run, const MetaProblem *problem, GeneticPopulation *population);

void genetic_options_from_context(const AnalysisExecutionContext *context, GeneticOptions *options);
bool validate_genetic_parameters(cJSON *parameters, char *error, size_t error_size);

// Executa o AG numa faixa; "hook" e opcional. "details" recebe os contadores do AG, e o hook pode acrescentar os seus.
ProposedConfig *genetic_run(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats,
    const GeneticOptions *genetic,
    GeneticGenerationHook hook,
    void *hook_context,
    cJSON *details,
    const char *log_name
);

ProposedConfig *build_genetic_proposals(
    const Graph *graph,
    const AnalysisExecutionContext *context,
    AssignmentStats *stats
);

// Operadores, expostos para os testes em C e para o AG hibrido.
int genetic_tournament(const GeneticPopulation *population, MetaRng *rng, int tournament_size, OptimizationObjective objective);
void genetic_crossover(const MetaProblem *problem, MetaRng *rng, bool one_point, const int *left, const int *right, int *child);
int genetic_mutate(const MetaProblem *problem, MetaRng *rng, double rate, int *genes);

#endif
