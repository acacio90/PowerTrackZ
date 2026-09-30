#include "objective.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

static const char *const DEFAULT_ORDER[] = {"conflicts", "interference", "bandwidth"};
static const char *const ENERGY_TIEBREAK_ORDER[] = {"conflicts", "interference", "power"};
static const char *const ENERGY_FIRST_ORDER[] = {"power", "conflicts", "interference"};

#define ORDER_LENGTH(order) (sizeof(order) / sizeof((order)[0]))

static const ObjectiveInfo OBJECTIVES[] = {
    {
        .id = OBJECTIVE_DEFAULT,
        .name = "default",
        .label = "Padrão",
        .description = "Menos conflitos, depois menor interferência e, no desempate, maior largura de banda.",
        .order = DEFAULT_ORDER,
        .order_length = ORDER_LENGTH(DEFAULT_ORDER),
    },
    {
        .id = OBJECTIVE_ENERGY_TIEBREAK,
        .name = "energy_tiebreak",
        .label = "Energia no desempate",
        .description = "Menos conflitos, depois menor interferência e, no desempate, menor potência.",
        .order = ENERGY_TIEBREAK_ORDER,
        .order_length = ORDER_LENGTH(ENERGY_TIEBREAK_ORDER),
    },
    {
        .id = OBJECTIVE_ENERGY_FIRST,
        .name = "energy_first",
        .label = "Energia primeiro",
        .description = "Menor potência, depois menos conflitos e menor interferência.",
        .order = ENERGY_FIRST_ORDER,
        .order_length = ORDER_LENGTH(ENERGY_FIRST_ORDER),
    },
};

const ObjectiveInfo *optimization_objectives(size_t *count) {
    if (count) {
        *count = sizeof(OBJECTIVES) / sizeof(OBJECTIVES[0]);
    }
    return OBJECTIVES;
}

const ObjectiveInfo *find_optimization_objective(const char *name) {
    size_t count = 0;
    const ObjectiveInfo *objectives = optimization_objectives(&count);
    for (size_t index = 0; name && index < count; index++) {
        if (strcmp(objectives[index].name, name) == 0) {
            return &objectives[index];
        }
    }
    return NULL;
}

const char *optimization_objective_name(OptimizationObjective objective) {
    size_t count = 0;
    const ObjectiveInfo *objectives = optimization_objectives(&count);
    for (size_t index = 0; index < count; index++) {
        if (objectives[index].id == objective) {
            return objectives[index].name;
        }
    }
    return objectives[0].name;
}

static int compare_conflicts(const AssignmentCost *left, const AssignmentCost *right) {
    return left->conflicts == right->conflicts ? 0 : left->conflicts < right->conflicts ? -1 : 1;
}

static int compare_interference(const AssignmentCost *left, const AssignmentCost *right) {
    return left->interference == right->interference ? 0 : left->interference < right->interference ? -1 : 1;
}

static int compare_bandwidth(const AssignmentCost *left, const AssignmentCost *right) {
    return left->bandwidth == right->bandwidth ? 0 : left->bandwidth > right->bandwidth ? -1 : 1;
}

static int compare_power(const AssignmentCost *left, const AssignmentCost *right) {
    return left->power_mw == right->power_mw ? 0 : left->power_mw < right->power_mw ? -1 : 1;
}

int compare_assignment_costs(OptimizationObjective objective, const AssignmentCost *left, const AssignmentCost *right) {
    int (*const default_order[])(const AssignmentCost *, const AssignmentCost *) = {
        compare_conflicts, compare_interference, compare_bandwidth,
    };
    int (*const energy_tiebreak_order[])(const AssignmentCost *, const AssignmentCost *) = {
        compare_conflicts, compare_interference, compare_power,
    };
    int (*const energy_first_order[])(const AssignmentCost *, const AssignmentCost *) = {
        compare_power, compare_conflicts, compare_interference,
    };
    int (*const *order)(const AssignmentCost *, const AssignmentCost *) =
        objective == OBJECTIVE_ENERGY_TIEBREAK ? energy_tiebreak_order
        : objective == OBJECTIVE_ENERGY_FIRST ? energy_first_order
        : default_order;
    for (int index = 0; index < 3; index++) {
        int comparison = order[index](left, right);
        if (comparison != 0) {
            return comparison;
        }
    }
    return 0;
}

void add_assignment_cost(AssignmentCost *total, const AssignmentCost *delta) {
    total->conflicts += delta->conflicts;
    total->interference += delta->interference;
    total->bandwidth += delta->bandwidth;
    total->power_mw += delta->power_mw;
}

// Potencia media (W) de um AP transmitindo a 25 Mbps, por faixa e largura (Dembele et al., 2023). Faixas e
// larguras fora da tabela (160 MHz e 6 GHz) nao tem valor no modelo.
typedef struct {
    double band;
    double bandwidth;
    double watts;
} PowerModelEntry;

static const PowerModelEntry POWER_MODEL[] = {
    {2.4, 20.0, 14.5},
    {2.4, 40.0, 13.8},
    {5.0, 20.0, 11.1},
    {5.0, 40.0, 10.3},
    {5.0, 80.0, 9.9},
};

#define POWER_MODEL_COUNT (sizeof(POWER_MODEL) / sizeof(POWER_MODEL[0]))

// Mesma leitura da faixa usada no restante do servico ("2.4 GHz", "2.4GHz", "5 GHz"...).
static double model_band(const char *frequency) {
    if (!frequency) {
        return 0.0;
    }
    if (strstr(frequency, "2.4") != NULL) {
        return 2.4;
    }
    if (strstr(frequency, "5") != NULL) {
        return 5.0;
    }
    if (strstr(frequency, "6") != NULL) {
        return 6.0;
    }
    return 0.0;
}

double access_point_power_w(const char *frequency, const char *bandwidth) {
    double band = model_band(frequency);
    double width = bandwidth && bandwidth[0] != '\0' ? atof(bandwidth) : 0.0;
    for (size_t index = 0; index < POWER_MODEL_COUNT; index++) {
        if (POWER_MODEL[index].band == band && POWER_MODEL[index].bandwidth == width) {
            return POWER_MODEL[index].watts;
        }
    }
    return -1.0;
}

long long objective_power_mw(const char *frequency, const char *bandwidth) {
    double watts = access_point_power_w(frequency, bandwidth);
    if (watts < 0.0) {
        double band = model_band(frequency);
        watts = 0.0;
        for (size_t index = 0; index < POWER_MODEL_COUNT; index++) {
            if (POWER_MODEL[index].band == band && POWER_MODEL[index].watts > watts) {
                watts = POWER_MODEL[index].watts;
            }
        }
    }
    return llround(watts * 1000.0);
}
