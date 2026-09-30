#ifndef ANALYSIS_SERVICE_STRATEGIES_OBJECTIVE_H
#define ANALYSIS_SERVICE_STRATEGIES_OBJECTIVE_H

#include <stdbool.h>
#include <stddef.h>

// Criterio de otimizacao: ordem lexicografica em que as estrategias comparam as solucoes.
typedef enum {
    OBJECTIVE_DEFAULT = 0,        // conflitos -> interferencia -> maior largura de banda
    OBJECTIVE_ENERGY_TIEBREAK,    // conflitos -> interferencia -> menor potencia
    OBJECTIVE_ENERGY_FIRST        // menor potencia -> conflitos -> interferencia
} OptimizationObjective;

typedef struct {
    OptimizationObjective id;
    const char *name;
    const char *label;
    const char *description;
    const char *const *order;
    size_t order_length;
} ObjectiveInfo;

// Custo de uma atribuicao (ou o incremento de atribuir um perfil a um AP). A potencia fica em
// miliwatts inteiros para que somas em ordens diferentes (threads diferentes) deem o mesmo valor.
typedef struct {
    int conflicts;
    double interference;
    double bandwidth;
    long long power_mw;
} AssignmentCost;

const ObjectiveInfo *optimization_objectives(size_t *count);
const ObjectiveInfo *find_optimization_objective(const char *name);
const char *optimization_objective_name(OptimizationObjective objective);

// Negativo quando left e melhor que right no objetivo, positivo quando e pior e zero no empate.
int compare_assignment_costs(OptimizationObjective objective, const AssignmentCost *left, const AssignmentCost *right);
void add_assignment_cost(AssignmentCost *total, const AssignmentCost *delta);

// Potencia media (W) do AP pelo modelo de consumo, ou um valor negativo fora do modelo.
double access_point_power_w(const char *frequency, const char *bandwidth);

// Potencia usada no criterio de otimizacao (mW). Fora do modelo, vale a maior potencia modelada da faixa,
// para que uma configuracao sem estimativa nunca seja favorecida; numa faixa sem valores no modelo
// (6 GHz), vale zero, e a energia deixa de diferenciar os perfis dessa faixa.
long long objective_power_mw(const char *frequency, const char *bandwidth);

#endif
