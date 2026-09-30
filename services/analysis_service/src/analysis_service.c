#define _POSIX_C_SOURCE 200809L

#include <arpa/inet.h>
#include <curl/curl.h>
#include <cjson/cJSON.h>
#include <math.h>
#include <netinet/in.h>
#include <pthread.h>
#include <signal.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

#define READ_CHUNK 8192

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#include "analysis_service.h"
#include "strategies/backtracking.h"
#include "strategies/strategy.h"

// Trechos contiguos de canais de 20 MHz permitidos no Brasil. Em 5 e 6 GHz os canais
// largos agregam blocos alinhados ao inicio do trecho; em 2,4 GHz os canais se sobrepoem
// e qualquer canal pode ser o primario de um canal de 40 MHz.
typedef struct {
    const char *frequency;
    int first_channel;
    int last_channel;
    int channel_step;
    bool aligned_blocks;
} ChannelSegment;

typedef struct {
    const char *frequency;
    int bandwidths[4];
    int bandwidth_count;
} BandBandwidths;

static const ChannelSegment CHANNEL_SEGMENTS[] = {
    {"2.4 GHz", 1, 13, 1, false},
    {"5 GHz", 36, 64, 4, true},
    {"5 GHz", 100, 144, 4, true},
    {"5 GHz", 149, 165, 4, true},
    {"6 GHz", 1, 233, 4, true},
};

static const BandBandwidths BAND_BANDWIDTHS[] = {
    {"2.4 GHz", {20, 40}, 2},
    {"5 GHz", {20, 40, 80, 160}, 4},
    {"6 GHz", {20, 40, 80, 160}, 4},
};

typedef struct {
    int fd;
} ConnectionContext;

typedef struct {
    char *method;
    char *path;
    char *body;
} Request;

typedef struct {
    char *data;
    size_t size;
} CurlBuffer;

static pthread_mutex_t jobs_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t log_mutex = PTHREAD_MUTEX_INITIALIZER;
static Job *jobs_head = NULL;
static volatile int server_running = 1;
static unsigned long long job_sequence = 0;
static AnalysisLogLevel configured_log_level = ANALYSIS_LOG_INFO;

static double now_seconds(void);
static long available_processor_count(void);

bool is_cancelled(const Job *job) {
    return job && atomic_load(&((Job *) job)->cancelled);
}

AnalysisLogLevel analysis_log_level(void) {
    return configured_log_level;
}

void analysis_log(AnalysisLogLevel level, const char *job_id, const char *fmt, ...) {
    if (level > configured_log_level) {
        return;
    }

    const char *level_name = level == ANALYSIS_LOG_ERROR ? "ERROR" : level == ANALYSIS_LOG_DEBUG ? "DEBUG" : "INFO";
    time_t raw_time = time(NULL);
    struct tm current_time;
#ifdef _WIN32
    localtime_s(&current_time, &raw_time);
#else
    localtime_r(&raw_time, &current_time);
#endif
    char timestamp[32];
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", &current_time);

    pthread_mutex_lock(&log_mutex);
    fprintf(stderr, "[%s] [%s]", timestamp, level_name);
    if (job_id && job_id[0] != '\0') {
        fprintf(stderr, " [job:%s]", job_id);
    }
    fprintf(stderr, " ");

    va_list args;
    va_start(args, fmt);
    vfprintf(stderr, fmt, args);
    va_end(args);

    fputc('\n', stderr);
    fflush(stderr);
    pthread_mutex_unlock(&log_mutex);
}

static long available_processor_count(void) {
    long count = sysconf(_SC_NPROCESSORS_ONLN);
    return count > 0 ? count : 1;
}

static char *dup_text(const char *value) {
    if (!value) {
        return strdup("");
    }
    char *copy = strdup(value);
    if (!copy) {
        perror("strdup");
        exit(1);
    }
    return copy;
}

static void free_graph(Graph *graph) {
    if (!graph) {
        return;
    }
    for (int i = 0; i < graph->node_count; i++) {
        free(graph->nodes[i].id);
        free(graph->nodes[i].label);
        free(graph->nodes[i].channel);
        free(graph->nodes[i].bandwidth);
        free(graph->nodes[i].frequency);
        free(graph->nodes[i].neighbors);
    }
    free(graph->nodes);
    free(graph->edges);
    memset(graph, 0, sizeof(*graph));
}

static void ensure_node_capacity(Graph *graph) {
    if (graph->node_count < graph->node_capacity) {
        return;
    }
    graph->node_capacity = graph->node_capacity == 0 ? 8 : graph->node_capacity * 2;
    graph->nodes = realloc(graph->nodes, sizeof(Node) * graph->node_capacity);
    if (!graph->nodes) {
        perror("realloc nodes");
        exit(1);
    }
}

static void ensure_edge_capacity(Graph *graph) {
    if (graph->edge_count < graph->edge_capacity) {
        return;
    }
    graph->edge_capacity = graph->edge_capacity == 0 ? 16 : graph->edge_capacity * 2;
    graph->edges = realloc(graph->edges, sizeof(Edge) * graph->edge_capacity);
    if (!graph->edges) {
        perror("realloc edges");
        exit(1);
    }
}

static void add_neighbor(Node *node, int neighbor) {
    if (node->neighbor_count >= node->neighbor_capacity) {
        node->neighbor_capacity = node->neighbor_capacity == 0 ? 8 : node->neighbor_capacity * 2;
        node->neighbors = realloc(node->neighbors, sizeof(int) * node->neighbor_capacity);
        if (!node->neighbors) {
            perror("realloc neighbors");
            exit(1);
        }
    }
    node->neighbors[node->neighbor_count++] = neighbor;
}

static void add_node(Graph *graph, Node node) {
    ensure_node_capacity(graph);
    graph->nodes[graph->node_count++] = node;
}

static void add_edge(Graph *graph, int source, int target, double peso) {
    ensure_edge_capacity(graph);
    graph->edges[graph->edge_count++] = (Edge){source, target, peso};
    add_neighbor(&graph->nodes[source], target);
    add_neighbor(&graph->nodes[target], source);
}

static unsigned long color_hash(const char *text) {
    unsigned long hash = 5381;
    const unsigned char *cursor = (const unsigned char *) text;
    while (cursor && *cursor) {
        hash = ((hash << 5) + hash) + *cursor;
        cursor++;
    }
    return hash & 0xFFFFFFUL;
}

static char *build_color(const Node *node) {
    char buffer[256];
    snprintf(
        buffer,
        sizeof(buffer),
        "%s-%s-%s",
        node->channel ? node->channel : "",
        node->bandwidth ? node->bandwidth : "",
        node->frequency ? node->frequency : ""
    );
    char *color = malloc(8);
    if (!color) {
        perror("malloc color");
        exit(1);
    }
    snprintf(color, 8, "#%06lx", color_hash(buffer));
    return color;
}

static char *build_profile_color(const char *channel, const char *bandwidth, const char *frequency) {
    char buffer[256];
    snprintf(
        buffer,
        sizeof(buffer),
        "%s-%s-%s",
        channel ? channel : "",
        bandwidth ? bandwidth : "",
        frequency ? frequency : ""
    );
    char *color = malloc(8);
    if (!color) {
        perror("malloc color");
        exit(1);
    }
    snprintf(color, 8, "#%06lx", color_hash(buffer));
    return color;
}

static double normalize_frequency_band(const char *frequency) {
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

static int parse_channel_number(const char *channel) {
    if (!channel || channel[0] == '\0') {
        return -1;
    }
    return atoi(channel);
}

static double parse_bandwidth_mhz(const char *bandwidth) {
    if (!bandwidth || bandwidth[0] == '\0') {
        return 0.0;
    }
    return atof(bandwidth);
}

// Canal central do bloco agregado que contem o canal primario. Em 2,4 GHz, o secundario de um
// canal de 40 MHz fica 4 canais acima quando cabe na faixa (primarios 1 a 9) e abaixo nos demais.
// Em 5 e 6 GHz, o bloco e o alinhado ao inicio do trecho em CHANNEL_SEGMENTS; um canal sem bloco
// completo naquela largura mantem o proprio centro.
static int bonded_center_channel(double band, int channel, double bandwidth) {
    int channels_per_block = 0;
    if (bandwidth == 40.0) {
        channels_per_block = 2;
    } else if (bandwidth == 80.0) {
        channels_per_block = 4;
    } else if (bandwidth == 160.0) {
        channels_per_block = 8;
    }
    if (channels_per_block == 0) {
        return channel;
    }
    if (band == 2.4) {
        return channels_per_block == 2 ? (channel + 4 <= 13 ? channel + 2 : channel - 2) : channel;
    }

    size_t segment_count = sizeof(CHANNEL_SEGMENTS) / sizeof(CHANNEL_SEGMENTS[0]);
    for (size_t index = 0; index < segment_count; index++) {
        const ChannelSegment *segment = &CHANNEL_SEGMENTS[index];
        if (!segment->aligned_blocks
            || normalize_frequency_band(segment->frequency) != band
            || channel < segment->first_channel
            || channel > segment->last_channel
            || (channel - segment->first_channel) % segment->channel_step != 0) {
            continue;
        }
        int block_span = channels_per_block * segment->channel_step;
        int block_start = segment->first_channel + ((channel - segment->first_channel) / block_span) * block_span;
        int block_end = block_start + (channels_per_block - 1) * segment->channel_step;
        return block_end <= segment->last_channel ? (block_start + block_end) / 2 : channel;
    }
    return channel;
}

static double channel_center_mhz(double band, int channel, double bandwidth) {
    if (channel <= 0 || band == 0.0) {
        return 0.0;
    }
    int center_channel = bonded_center_channel(band, channel, bandwidth);
    if (band == 2.4) {
        return 2407.0 + (5.0 * center_channel);
    }
    if (band == 5.0) {
        return 5000.0 + (5.0 * center_channel);
    }
    if (band == 6.0) {
        return 5950.0 + (5.0 * center_channel);
    }
    return 0.0;
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

// Devolve a potencia do AP ou um valor negativo quando a configuracao nao esta no modelo.
static double access_point_power_w(const char *frequency, const char *bandwidth) {
    double band = normalize_frequency_band(frequency);
    double width = parse_bandwidth_mhz(bandwidth);
    size_t entry_count = sizeof(POWER_MODEL) / sizeof(POWER_MODEL[0]);
    for (size_t index = 0; index < entry_count; index++) {
        if (POWER_MODEL[index].band == band && POWER_MODEL[index].bandwidth == width) {
            return POWER_MODEL[index].watts;
        }
    }
    return -1.0;
}

static double center_frequency_mhz(const Node *node) {
    return channel_center_mhz(
        normalize_frequency_band(node->frequency),
        parse_channel_number(node->channel),
        parse_bandwidth_mhz(node->bandwidth)
    );
}

static double spectral_overlap_factor(const Node *left, const Node *right) {
    double left_band = normalize_frequency_band(left->frequency);
    double right_band = normalize_frequency_band(right->frequency);
    if (left_band == 0.0 || right_band == 0.0 || left_band != right_band) {
        return 0.0;
    }

    double left_center = center_frequency_mhz(left);
    double right_center = center_frequency_mhz(right);
    double left_bandwidth = parse_bandwidth_mhz(left->bandwidth);
    double right_bandwidth = parse_bandwidth_mhz(right->bandwidth);
    if (left_center <= 0.0 || right_center <= 0.0 || left_bandwidth <= 0.0 || right_bandwidth <= 0.0) {
        return 0.0;
    }

    double left_lower = left_center - (left_bandwidth / 2.0);
    double left_upper = left_center + (left_bandwidth / 2.0);
    double right_lower = right_center - (right_bandwidth / 2.0);
    double right_upper = right_center + (right_bandwidth / 2.0);

    double overlap = fmin(left_upper, right_upper) - fmax(left_lower, right_lower);
    if (overlap <= 0.0) {
        return 0.0;
    }

    double reference_width = fmin(left_bandwidth, right_bandwidth);
    if (reference_width <= 0.0) {
        return 0.0;
    }

    double factor = overlap / reference_width;
    if (factor < 0.0) {
        return 0.0;
    }
    if (factor > 1.0) {
        return 1.0;
    }
    return factor;
}

static double haversine(double lat1, double lon1, double lat2, double lon2) {
    double radius = 6371000.0;
    double phi1 = lat1 * M_PI / 180.0;
    double phi2 = lat2 * M_PI / 180.0;
    double delta_phi = (lat2 - lat1) * M_PI / 180.0;
    double delta_lambda = (lon2 - lon1) * M_PI / 180.0;
    double a = sin(delta_phi / 2.0) * sin(delta_phi / 2.0)
        + cos(phi1) * cos(phi2) * sin(delta_lambda / 2.0) * sin(delta_lambda / 2.0);
    double c = 2.0 * atan2(sqrt(a), sqrt(1.0 - a));
    return radius * c;
}

static double circle_intersection_area(double r1, double r2, double distance) {
    if (distance >= r1 + r2) {
        return 0.0;
    }
    if (distance <= fabs(r1 - r2)) {
        double min_r = r1 < r2 ? r1 : r2;
        return M_PI * min_r * min_r;
    }
    double term1 = r1 * r1 * acos((distance * distance + r1 * r1 - r2 * r2) / (2.0 * distance * r1));
    double term2 = r2 * r2 * acos((distance * distance + r2 * r2 - r1 * r1) / (2.0 * distance * r2));
    double term3 = 0.5 * sqrt(
        (-distance + r1 + r2) *
        (distance + r1 - r2) *
        (distance - r1 + r2) *
        (distance + r1 + r2)
    );
    return term1 + term2 - term3;
}

static double collision_percentage(const Node *left, const Node *right) {
    double distance = haversine(left->x, left->y, right->x, right->y);
    if (distance >= left->raio + right->raio) {
        return 0.0;
    }
    double area = circle_intersection_area(left->raio, right->raio, distance);
    double smaller_area = M_PI * pow(left->raio < right->raio ? left->raio : right->raio, 2.0);
    if (smaller_area <= 0.0) {
        return 0.0;
    }
    return (area / smaller_area) * 100.0;
}

static const char *json_string(cJSON *item, const char *fallback) {
    return cJSON_IsString(item) && item->valuestring ? item->valuestring : fallback;
}

static int parse_thread_count(cJSON *payload) {
    cJSON *parameters = cJSON_GetObjectItemCaseSensitive(payload, "parameters");
    if (!cJSON_IsObject(parameters)) {
        return 1;
    }
    cJSON *item = cJSON_GetObjectItemCaseSensitive(parameters, "thread_count");
    if (cJSON_IsNumber(item) && item->valuedouble > 0) {
        return (int) item->valuedouble;
    }
    return 1;
}

static cJSON *payload_parameters(cJSON *payload) {
    return cJSON_GetObjectItemCaseSensitive(payload, "parameters");
}

// Recusa a requisicao com 400 quando algum parametro declarado pela estrategia esta fora do contrato.
static bool reject_invalid_parameters(int fd, const AnalysisStrategy *strategy, cJSON *payload);

static int effective_thread_count(const Graph *graph, int requested_thread_count) {
    int max_useful = graph && graph->node_count > 0 ? graph->node_count : 1;
    int normalized = requested_thread_count > 0 ? requested_thread_count : 1;
    if (normalized > max_useful) {
        normalized = max_useful;
    }
    return normalized < 1 ? 1 : normalized;
}

static double graph_density(const Graph *graph) {
    if (graph->node_count <= 1) {
        return 0.0;
    }
    return (2.0 * graph->edge_count) / (graph->node_count * (graph->node_count - 1));
}

static double edge_density_from_counts(int node_count, int edge_count) {
    if (node_count <= 1) {
        return 0.0;
    }
    return (2.0 * edge_count) / (node_count * (node_count - 1));
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

static double spectral_overlap_factor_for_config(
    const Node *left,
    const char *left_channel,
    const char *left_bandwidth,
    const char *left_frequency,
    const Node *right,
    const char *right_channel,
    const char *right_bandwidth,
    const char *right_frequency
) {
    Node configured_left = *left;
    Node configured_right = *right;
    configured_left.channel = (char *) left_channel;
    configured_left.bandwidth = (char *) left_bandwidth;
    configured_left.frequency = (char *) left_frequency;
    configured_right.channel = (char *) right_channel;
    configured_right.bandwidth = (char *) right_bandwidth;
    configured_right.frequency = (char *) right_frequency;
    return spectral_overlap_factor(&configured_left, &configured_right);
}

double interference_percentage_for_config(
    const Node *left,
    const char *left_channel,
    const char *left_bandwidth,
    const char *left_frequency,
    const Node *right,
    const char *right_channel,
    const char *right_bandwidth,
    const char *right_frequency
) {
    double spatial_factor = collision_percentage(left, right);
    if (spatial_factor <= 0.0) {
        return 0.0;
    }

    double spectral_factor = spectral_overlap_factor_for_config(
        left,
        left_channel,
        left_bandwidth,
        left_frequency,
        right,
        right_channel,
        right_bandwidth,
        right_frequency
    );
    if (spectral_factor <= 0.0) {
        return 0.0;
    }

    return spatial_factor * spectral_factor;
}

// Conta as arestas em conflito (w * s > 0) na configuracao proposta; sem propostas, na configuracao atual.
// Em interference_total, devolve a soma das interferencias (w * s) dessas arestas.
static int count_conflicts_for_proposals(const Graph *graph, const ProposedConfig *proposals, double *interference_total) {
    int conflict_count = 0;
    double total = 0.0;
    for (int edge_index = 0; edge_index < graph->edge_count; edge_index++) {
        const Edge *edge = &graph->edges[edge_index];
        const Node *left_node = &graph->nodes[edge->source];
        const Node *right_node = &graph->nodes[edge->target];
        const ProposedConfig *left_proposal = proposals ? &proposals[edge->source] : NULL;
        const ProposedConfig *right_proposal = proposals ? &proposals[edge->target] : NULL;
        const char *left_channel = left_proposal && left_proposal->channel ? left_proposal->channel : left_node->channel;
        const char *left_bandwidth = left_proposal && left_proposal->bandwidth ? left_proposal->bandwidth : left_node->bandwidth;
        const char *left_frequency = left_proposal && left_proposal->frequency ? left_proposal->frequency : left_node->frequency;
        const char *right_channel = right_proposal && right_proposal->channel ? right_proposal->channel : right_node->channel;
        const char *right_bandwidth = right_proposal && right_proposal->bandwidth ? right_proposal->bandwidth : right_node->bandwidth;
        const char *right_frequency = right_proposal && right_proposal->frequency ? right_proposal->frequency : right_node->frequency;

        double interference = interference_percentage_for_config(
            left_node,
            left_channel,
            left_bandwidth,
            left_frequency,
            right_node,
            right_channel,
            right_bandwidth,
            right_frequency
        );
        if (interference > 0.0) {
            conflict_count++;
            total += interference;
        }
    }
    if (interference_total) {
        *interference_total = total;
    }
    return conflict_count;
}

// Mesma configuracao pelos valores numericos ("2.4GHz" e "2.4 GHz" sao a mesma faixa).
static bool same_configuration(const Node *node, const ProposedConfig *proposal) {
    return normalize_frequency_band(node->frequency) == normalize_frequency_band(proposal->frequency)
        && parse_channel_number(node->channel) == parse_channel_number(proposal->channel)
        && parse_bandwidth_mhz(node->bandwidth) == parse_bandwidth_mhz(proposal->bandwidth);
}

static cJSON *build_graph_json(const Graph *graph, const ProposedConfig *proposals) {
    cJSON *json = cJSON_CreateObject();
    cJSON *nodes = cJSON_AddArrayToObject(json, "nodes");
    cJSON *links = cJSON_AddArrayToObject(json, "links");
    double total_power = 0.0;
    int unmodeled_nodes = 0;

    for (int i = 0; i < graph->node_count; i++) {
        const Node *node = &graph->nodes[i];
        char *color = build_color(node);
        const ProposedConfig *proposal = proposals ? &proposals[i] : NULL;
        const char *proposed_channel = proposal && proposal->channel ? proposal->channel : node->channel;
        const char *proposed_bandwidth = proposal && proposal->bandwidth ? proposal->bandwidth : node->bandwidth;
        const char *proposed_frequency = proposal && proposal->frequency ? proposal->frequency : node->frequency;
        char *proposed_color = build_profile_color(proposed_channel, proposed_bandwidth, proposed_frequency);
        cJSON *item = cJSON_CreateObject();
        cJSON_AddStringToObject(item, "id", node->id);
        cJSON_AddStringToObject(item, "label", node->label);
        cJSON_AddStringToObject(item, "channel", node->channel);
        cJSON_AddStringToObject(item, "bandwidth", node->bandwidth);
        cJSON_AddStringToObject(item, "frequency", node->frequency);
        cJSON_AddStringToObject(item, "proposed_channel", proposed_channel);
        cJSON_AddStringToObject(item, "proposed_bandwidth", proposed_bandwidth);
        cJSON_AddStringToObject(item, "proposed_frequency", proposed_frequency);
        cJSON_AddStringToObject(item, "cor", color);
        cJSON_AddStringToObject(item, "proposed_cor", proposed_color);
        cJSON_AddNumberToObject(item, "x", node->x);
        cJSON_AddNumberToObject(item, "y", node->y);
        cJSON_AddNumberToObject(item, "raio", node->raio);
        cJSON_AddBoolToObject(item, "locked", node->locked);
        double power = access_point_power_w(node->frequency, node->bandwidth);
        double proposed_power = access_point_power_w(proposed_frequency, proposed_bandwidth);
        if (power >= 0.0) {
            cJSON_AddNumberToObject(item, "power_w", power);
        } else {
            cJSON_AddNullToObject(item, "power_w");
        }
        if (proposed_power >= 0.0) {
            cJSON_AddNumberToObject(item, "proposed_power_w", proposed_power);
            total_power += proposed_power;
        } else {
            cJSON_AddNullToObject(item, "proposed_power_w");
            unmodeled_nodes++;
        }
        cJSON_AddItemToArray(nodes, item);
        free(color);
        free(proposed_color);
    }
    // Potencia total da configuracao exibida (a proposta, quando ha; senao, a atual).
    cJSON_AddNumberToObject(json, "power_w", total_power);
    cJSON_AddNumberToObject(json, "power_unmodeled_nodes", unmodeled_nodes);

    for (int edge_index = 0; edge_index < graph->edge_count; edge_index++) {
        const Edge *edge = &graph->edges[edge_index];
        const Node *left_node = &graph->nodes[edge->source];
        const Node *right_node = &graph->nodes[edge->target];
        const ProposedConfig *left_proposal = proposals ? &proposals[edge->source] : NULL;
        const ProposedConfig *right_proposal = proposals ? &proposals[edge->target] : NULL;
        const char *left_channel = left_proposal && left_proposal->channel ? left_proposal->channel : left_node->channel;
        const char *left_bandwidth = left_proposal && left_proposal->bandwidth ? left_proposal->bandwidth : left_node->bandwidth;
        const char *left_frequency = left_proposal && left_proposal->frequency ? left_proposal->frequency : left_node->frequency;
        const char *right_channel = right_proposal && right_proposal->channel ? right_proposal->channel : right_node->channel;
        const char *right_bandwidth = right_proposal && right_proposal->bandwidth ? right_proposal->bandwidth : right_node->bandwidth;
        const char *right_frequency = right_proposal && right_proposal->frequency ? right_proposal->frequency : right_node->frequency;
        double interference_weight = interference_percentage_for_config(
            left_node,
            left_channel,
            left_bandwidth,
            left_frequency,
            right_node,
            right_channel,
            right_bandwidth,
            right_frequency
        );
        cJSON *item = cJSON_CreateObject();
        cJSON_AddStringToObject(item, "source", left_node->id);
        cJSON_AddStringToObject(item, "target", right_node->id);
        cJSON_AddNumberToObject(item, "peso", edge->peso);
        cJSON_AddNumberToObject(item, "collision_peso", edge->peso);
        cJSON_AddNumberToObject(item, "interference_peso", interference_weight);
        cJSON_AddItemToArray(links, item);
    }
    return json;
}

// Registra os parametros declarados pela estrategia com os valores efetivamente usados na execucao.
static cJSON *build_resolved_parameters_json(const AnalysisStrategy *strategy, cJSON *parameters, int effective_threads) {
    cJSON *json = cJSON_CreateObject();
    for (size_t index = 0; strategy && index < strategy->parameter_count; index++) {
        const char *name = strategy->parameters[index].name;
        double value = strcmp(name, "thread_count") == 0
            ? effective_threads
            : strategy_parameter_value(strategy, parameters, name, strategy->parameters[index].default_value);
        cJSON_AddNumberToObject(json, name, value);
    }
    return json;
}

static cJSON *build_execution_json(const char *strategy, const Graph *graph, cJSON *resolved_parameters, double started_at, double completed_at) {
    cJSON *json = cJSON_CreateObject();
    cJSON_AddStringToObject(json, "strategy", strategy);
    cJSON_AddNumberToObject(json, "started_at", started_at);
    cJSON_AddNumberToObject(json, "completed_at", completed_at);
    cJSON_AddNumberToObject(json, "duration_seconds", completed_at - started_at);
    cJSON_AddNumberToObject(json, "duration_ms", (completed_at - started_at) * 1000.0);
    cJSON_AddItemToObject(json, "parameters", resolved_parameters ? resolved_parameters : cJSON_CreateObject());
    cJSON *snapshot = cJSON_AddObjectToObject(json, "graph_snapshot");
    cJSON_AddNumberToObject(snapshot, "nodes", graph->node_count);
    cJSON_AddNumberToObject(snapshot, "edges", graph->edge_count);
    cJSON_AddNumberToObject(snapshot, "density", graph_density(graph));
    return json;
}

static void add_strategy_comparison_to_execution(cJSON *execution, const Graph *graph, const ProposedConfig *proposals) {
    if (!execution || !graph || !proposals) {
        return;
    }
    // Conflitos (arestas com w * s > 0) antes e depois; as sobreposicoes sem conflito ficam de fora.
    double interference_before = 0.0;
    double interference_after = 0.0;
    int conflicts_before = count_conflicts_for_proposals(graph, NULL, &interference_before);
    int conflicts_after = count_conflicts_for_proposals(graph, proposals, &interference_after);
    int changed_nodes = 0;
    for (int index = 0; index < graph->node_count; index++) {
        if (!same_configuration(&graph->nodes[index], &proposals[index])) {
            changed_nodes++;
        }
    }
    cJSON *comparison = cJSON_AddObjectToObject(execution, "comparison");
    cJSON_AddNumberToObject(comparison, "nodes", graph->node_count);
    cJSON_AddNumberToObject(comparison, "conflicts_before", conflicts_before);
    cJSON_AddNumberToObject(comparison, "conflicts_after", conflicts_after);
    cJSON_AddNumberToObject(comparison, "conflict_density_before", edge_density_from_counts(graph->node_count, conflicts_before));
    cJSON_AddNumberToObject(comparison, "conflict_density_after", edge_density_from_counts(graph->node_count, conflicts_after));
    cJSON_AddNumberToObject(comparison, "interference_before", interference_before);
    cJSON_AddNumberToObject(comparison, "interference_after", interference_after);
    cJSON_AddNumberToObject(comparison, "changed_nodes", changed_nodes);

    // Potencia total (W) antes e depois, pelo modelo de consumo; APs fora do modelo nao entram na soma.
    double power_before = 0.0;
    double power_after = 0.0;
    int unmodeled_before = 0;
    int unmodeled_after = 0;
    for (int index = 0; index < graph->node_count; index++) {
        const Node *node = &graph->nodes[index];
        double before = access_point_power_w(node->frequency, node->bandwidth);
        double after = access_point_power_w(
            proposals[index].frequency ? proposals[index].frequency : node->frequency,
            proposals[index].bandwidth ? proposals[index].bandwidth : node->bandwidth
        );
        if (before >= 0.0) {
            power_before += before;
        } else {
            unmodeled_before++;
        }
        if (after >= 0.0) {
            power_after += after;
        } else {
            unmodeled_after++;
        }
    }
    cJSON_AddNumberToObject(comparison, "power_before_w", power_before);
    cJSON_AddNumberToObject(comparison, "power_after_w", power_after);
    cJSON_AddNumberToObject(comparison, "power_unmodeled_before", unmodeled_before);
    cJSON_AddNumberToObject(comparison, "power_unmodeled_after", unmodeled_after);
}

static void add_search_stats_to_execution(cJSON *execution, const AssignmentStats *stats) {
    cJSON *search = cJSON_AddObjectToObject(execution, "search");
    cJSON_AddBoolToObject(search, "optimal", stats->optimal);
    cJSON_AddStringToObject(search, "stop_reason", assignment_stop_reason_name(stats->stop_reason));
    cJSON_AddNumberToObject(search, "nodes_explored", (double) stats->nodes_explored);
    cJSON_AddNumberToObject(search, "task_count", stats->task_count);
    cJSON_AddNumberToObject(search, "greedy_conflicts", stats->initial_conflicts);
    cJSON_AddNumberToObject(search, "conflicts", stats->conflicts);
    cJSON_AddNumberToObject(search, "interference_score", stats->interference_score);
    cJSON_AddNumberToObject(search, "bandwidth_score", stats->bandwidth_score);
}

static cJSON *build_summary_json(const Graph *graph) {
    cJSON *json = cJSON_CreateObject();
    cJSON_AddNumberToObject(json, "total_nodes", graph->node_count);
    cJSON_AddNumberToObject(json, "total_edges", graph->edge_count);
    cJSON_AddNumberToObject(json, "density", graph_density(graph));
    cJSON_AddNumberToObject(json, "connected_components", 1);
    return json;
}

static cJSON *build_strategy_analysis_json(const AnalysisStrategy *strategy, const Graph *graph, int thread_count) {
    cJSON *json = cJSON_CreateObject();
    cJSON_AddStringToObject(json, "strategy", strategy->name);
    cJSON_AddStringToObject(json, "description", strategy->description);
    cJSON_AddNumberToObject(json, "configured_nodes", graph->node_count);

    cJSON *graph_metrics = cJSON_AddObjectToObject(json, "graph_metrics");
    cJSON_AddNumberToObject(graph_metrics, "nodes", graph->node_count);
    cJSON_AddNumberToObject(graph_metrics, "edges", graph->edge_count);
    cJSON_AddNumberToObject(graph_metrics, "density", graph_density(graph));

    cJSON *parallelism = cJSON_AddObjectToObject(json, "parallelism");
    cJSON_AddNumberToObject(parallelism, "thread_count", thread_count);
    cJSON_AddStringToObject(parallelism, "mode", strategy->mode);
    cJSON_AddStringToObject(parallelism, "service", "analysis_service_c");
    return json;
}

static cJSON *build_placeholder_analysis_json(const char *strategy, const Graph *graph, int thread_count) {
    cJSON *json = cJSON_CreateObject();
    cJSON_AddStringToObject(json, "strategy", strategy);
    cJSON_AddStringToObject(json, "description", "Placeholder para preservar a chamada do frontend no servico em C");
    cJSON_AddBoolToObject(json, "implemented", false);
    cJSON_AddStringToObject(json, "message", "Estrategia ainda nao portada para C");

    cJSON *graph_metrics = cJSON_AddObjectToObject(json, "graph_metrics");
    cJSON_AddNumberToObject(graph_metrics, "nodes", graph->node_count);
    cJSON_AddNumberToObject(graph_metrics, "edges", graph->edge_count);
    cJSON_AddNumberToObject(graph_metrics, "density", graph_density(graph));

    cJSON *parallelism = cJSON_AddObjectToObject(json, "parallelism");
    cJSON_AddNumberToObject(parallelism, "thread_count", thread_count);
    cJSON_AddStringToObject(parallelism, "mode", "placeholder");
    cJSON_AddStringToObject(parallelism, "service", "analysis_service_c");
    return json;
}

#define MAX_BANDS 3

// Faixas presentes no grafo, em ordem crescente. APs de faixa desconhecida ficam fora e mantem a configuracao.
static int collect_bands(const Graph *graph, double *bands) {
    int count = 0;
    for (int index = 0; index < graph->node_count; index++) {
        double band = normalize_frequency_band(graph->nodes[index].frequency);
        bool known = band == 0.0;
        for (int position = 0; position < count && !known; position++) {
            known = bands[position] == band;
        }
        if (known || count >= MAX_BANDS) {
            continue;
        }
        int position = count++;
        while (position > 0 && bands[position - 1] > band) {
            bands[position] = bands[position - 1];
            position--;
        }
        bands[position] = band;
    }
    return count;
}

// Subgrafo com os APs de uma faixa. Os nos compartilham as cadeias do grafo original; so vizinhos, nos e
// arestas sao alocados, e free_band_subgraph libera apenas isso.
static void build_band_subgraph(const Graph *graph, double band, Graph *subgraph, int *original_indexes, int *local_indexes) {
    memset(subgraph, 0, sizeof(*subgraph));
    for (int index = 0; index < graph->node_count; index++) {
        local_indexes[index] = -1;
        if (normalize_frequency_band(graph->nodes[index].frequency) != band) {
            continue;
        }
        Node node = graph->nodes[index];
        node.neighbors = NULL;
        node.neighbor_count = 0;
        node.neighbor_capacity = 0;
        local_indexes[index] = subgraph->node_count;
        original_indexes[subgraph->node_count] = index;
        add_node(subgraph, node);
    }
    for (int edge_index = 0; edge_index < graph->edge_count; edge_index++) {
        const Edge *edge = &graph->edges[edge_index];
        int source = local_indexes[edge->source];
        int target = local_indexes[edge->target];
        if (source >= 0 && target >= 0) {
            add_edge(subgraph, source, target, edge->peso);
        }
    }
}

static void free_band_subgraph(Graph *subgraph) {
    for (int index = 0; index < subgraph->node_count; index++) {
        free(subgraph->nodes[index].neighbors);
    }
    free(subgraph->nodes);
    free(subgraph->edges);
    memset(subgraph, 0, sizeof(*subgraph));
}

// Consolida as faixas: somas de conflitos, interferencia, banda e busca; a solucao e otima so se todas forem.
static void accumulate_band_stats(AssignmentStats *total, const AssignmentStats *band) {
    total->nodes_explored += band->nodes_explored;
    total->task_count += band->task_count;
    total->initial_conflicts += band->initial_conflicts;
    total->conflicts += band->conflicts;
    total->interference_score += band->interference_score;
    total->bandwidth_score += band->bandwidth_score;
    total->optimal = total->optimal && band->optimal;
    if (band->stop_reason == ASSIGNMENT_STOP_CANCELLED
        || (band->stop_reason == ASSIGNMENT_STOP_TIME_LIMIT && total->stop_reason == ASSIGNMENT_STOP_COMPLETED)) {
        total->stop_reason = band->stop_reason;
    }
}

static cJSON *build_strategy_response_json(
    const AnalysisStrategy *strategy,
    Graph *graph,
    cJSON *parameters,
    const ProfileSet *profiles,
    Job *job,
    int stream_fd,
    pthread_mutex_t *stream_lock,
    double started_at
) {
    int requested_threads = (int) strategy_parameter_value(strategy, parameters, "thread_count", 1);
    bool uses_threads = find_strategy_parameter(strategy, "thread_count") != NULL;
    int effective_threads = uses_threads ? effective_thread_count(graph, requested_threads) : 1;
    double time_limit_seconds = strategy_parameter_value(strategy, parameters, "time_limit_seconds", 0.0);

    cJSON *json = cJSON_CreateObject();
    cJSON_AddBoolToObject(json, "success", true);
    cJSON_AddStringToObject(json, "strategy_used", strategy->name);
    cJSON_AddItemToObject(json, "analysis", build_strategy_analysis_json(strategy, graph, effective_threads));

    ProposedConfig *proposals = calloc((size_t) (graph->node_count > 0 ? graph->node_count : 1), sizeof(ProposedConfig));
    int *original_indexes = malloc(sizeof(int) * (size_t) (graph->node_count > 0 ? graph->node_count : 1));
    int *local_indexes = malloc(sizeof(int) * (size_t) (graph->node_count > 0 ? graph->node_count : 1));
    ProposedConfig *band_profile_items = malloc(sizeof(ProposedConfig) * (size_t) (profiles && profiles->count > 0 ? profiles->count : 1));
    if (!proposals || !original_indexes || !local_indexes || !band_profile_items) {
        perror("malloc band analysis");
        exit(1);
    }
    for (int index = 0; index < graph->node_count; index++) {
        const Node *node = &graph->nodes[index];
        proposals[index] = (ProposedConfig){node->channel, node->bandwidth, node->frequency};
    }

    double bands[MAX_BANDS];
    int band_count = collect_bands(graph, bands);
    AssignmentStats total = {.stop_reason = ASSIGNMENT_STOP_COMPLETED, .optimal = band_count > 0};
    cJSON *bands_json = cJSON_CreateArray();

    // Cada faixa e um problema independente, resolvido em sequencia com o proprio limite de tempo.
    for (int band_index = 0; band_index < band_count; band_index++) {
        if (job && is_cancelled(job)) {
            total.stop_reason = ASSIGNMENT_STOP_CANCELLED;
            total.optimal = false;
            break;
        }
        char band_label[32];
        snprintf(band_label, sizeof(band_label), "%g GHz", bands[band_index]);

        ProfileSet band_profiles = {band_profile_items, 0};
        for (int index = 0; profiles && index < profiles->count; index++) {
            if (normalize_frequency_band(profiles->items[index].frequency) == bands[band_index]) {
                band_profile_items[band_profiles.count++] = profiles->items[index];
            }
        }

        Graph subgraph;
        build_band_subgraph(graph, bands[band_index], &subgraph, original_indexes, local_indexes);
        AnalysisExecutionContext context = {
            .job = job,
            .thread_count = uses_threads ? effective_thread_count(&subgraph, requested_threads) : 1,
            .time_limit_seconds = time_limit_seconds,
            .stream_fd = stream_fd,
            .stream_lock = stream_lock,
            .profiles = &band_profiles,
            .band_label = band_label,
            .progress_offset = (double) band_index / band_count,
            .progress_scale = 1.0 / band_count,
        };
        AssignmentStats band_stats = {0};
        ProposedConfig *band_proposals = strategy->run(&subgraph, &context, &band_stats);
        for (int index = 0; index < subgraph.node_count; index++) {
            proposals[original_indexes[index]] = band_proposals[index];
        }
        accumulate_band_stats(&total, &band_stats);

        cJSON *band_json = cJSON_CreateObject();
        cJSON_AddStringToObject(band_json, "frequency", band_label);
        cJSON_AddNumberToObject(band_json, "nodes", subgraph.node_count);
        cJSON_AddNumberToObject(band_json, "edges", subgraph.edge_count);
        cJSON_AddNumberToObject(band_json, "density", graph_density(&subgraph));
        cJSON_AddNumberToObject(band_json, "profile_count", band_profiles.count);
        add_strategy_comparison_to_execution(band_json, &subgraph, band_proposals);
        add_search_stats_to_execution(band_json, &band_stats);
        cJSON_AddItemToArray(bands_json, band_json);

        free(band_proposals);
        free_band_subgraph(&subgraph);
    }

    double completed_at = now_seconds();
    cJSON *execution = build_execution_json(
        strategy->name,
        graph,
        build_resolved_parameters_json(strategy, parameters, effective_threads),
        started_at,
        completed_at
    );
    add_strategy_comparison_to_execution(execution, graph, proposals);
    add_search_stats_to_execution(execution, &total);
    cJSON_AddItemToObject(execution, "bands", bands_json);
    cJSON_AddItemToObject(json, "execution", execution);
    cJSON_AddItemToObject(json, "graph_data", build_graph_json(graph, proposals));
    cJSON_AddItemToObject(json, "summary", build_summary_json(graph));
    free(proposals);
    free(original_indexes);
    free(local_indexes);
    free(band_profile_items);
    return json;
}

static cJSON *build_placeholder_response_json(const char *strategy, Graph *graph, int thread_count, double started_at) {
    double completed_at = now_seconds();
    cJSON *json = cJSON_CreateObject();
    cJSON_AddBoolToObject(json, "success", true);
    cJSON_AddStringToObject(json, "strategy_used", strategy);
    cJSON_AddItemToObject(json, "analysis", build_placeholder_analysis_json(strategy, graph, thread_count));
    cJSON_AddItemToObject(json, "execution", build_execution_json(strategy, graph, NULL, started_at, completed_at));
    cJSON_AddItemToObject(json, "graph_data", build_graph_json(graph, NULL));
    cJSON_AddItemToObject(json, "summary", build_summary_json(graph));
    return json;
}

static void send_http(int fd, int status, const char *status_text, const char *content_type, const char *body) {
    size_t body_size = body ? strlen(body) : 0;
    dprintf(
        fd,
        "HTTP/1.1 %d %s\r\n"
        "Content-Type: %s\r\n"
        "Content-Length: %zu\r\n"
        "Connection: close\r\n"
        "\r\n",
        status,
        status_text,
        content_type,
        body_size
    );
    if (body_size > 0) {
        write(fd, body, body_size);
    }
}

static void send_json_error(int fd, int status, const char *message) {
    cJSON *json = cJSON_CreateObject();
    cJSON_AddBoolToObject(json, "success", false);
    cJSON_AddStringToObject(json, "error", message);
    char *text = cJSON_PrintUnformatted(json);
    cJSON_Delete(json);
    send_http(fd, status, status == 404 ? "Not Found" : status == 400 ? "Bad Request" : "Internal Server Error", "application/json", text);
    free(text);
}

static bool reject_invalid_parameters(int fd, const AnalysisStrategy *strategy, cJSON *payload) {
    char error[256];
    if (validate_strategy_parameters(strategy, payload_parameters(payload), error, sizeof(error))) {
        return false;
    }
    analysis_log(ANALYSIS_LOG_INFO, NULL, "parametros invalidos strategy=%s: %s", strategy->name, error);
    send_json_error(fd, 400, error);
    return true;
}

static cJSON *build_strategy_parameters_json(const AnalysisStrategy *strategy) {
    cJSON *json = cJSON_CreateArray();
    for (size_t index = 0; index < strategy->parameter_count; index++) {
        const StrategyParameter *parameter = &strategy->parameters[index];
        cJSON *item = cJSON_CreateObject();
        cJSON_AddStringToObject(item, "name", parameter->name);
        cJSON_AddStringToObject(item, "label", parameter->label);
        cJSON_AddStringToObject(item, "description", parameter->description);
        cJSON_AddStringToObject(item, "type", strategy_parameter_type_name(parameter->type));
        cJSON_AddNumberToObject(item, "default", parameter->default_value);
        cJSON_AddNumberToObject(item, "min", parameter->min_value);
        cJSON_AddNumberToObject(item, "max", parameter->max_value);
        if (parameter->unit) {
            cJSON_AddStringToObject(item, "unit", parameter->unit);
        } else {
            cJSON_AddNullToObject(item, "unit");
        }
        cJSON_AddBoolToObject(item, "zero_disables", parameter->zero_disables);
        cJSON_AddItemToArray(json, item);
    }
    return json;
}

// Raio de cobertura (m) usado quando o AP nao informa o seu; os mesmos valores da interface e do gerador.
static double default_coverage_radius(const char *frequency) {
    double band = normalize_frequency_band(frequency);
    if (band == 2.4) {
        return 20.0;
    }
    if (band == 5.0) {
        return 15.0;
    }
    if (band == 6.0) {
        return 12.0;
    }
    return 10.0;
}

static bool build_graph(cJSON *payload, Graph *graph, char **error_message) {
    double build_started_at = now_seconds();
    memset(graph, 0, sizeof(*graph));
    cJSON *aps = cJSON_GetObjectItemCaseSensitive(payload, "aps");
    if (!cJSON_IsArray(aps) || cJSON_GetArraySize(aps) == 0) {
        *error_message = dup_text("Lista de pontos de acesso vazia");
        return false;
    }

    for (int i = 0; i < cJSON_GetArraySize(aps); i++) {
        cJSON *ap = cJSON_GetArrayItem(aps, i);
        const char *id = json_string(cJSON_GetObjectItemCaseSensitive(ap, "id"), NULL);
        if (!id || id[0] == '\0') {
            continue;
        }

        Node node = {0};
        node.id = dup_text(id);
        node.label = dup_text(json_string(cJSON_GetObjectItemCaseSensitive(ap, "label"), id));
        node.channel = dup_text(json_string(cJSON_GetObjectItemCaseSensitive(ap, "channel"), ""));
        node.bandwidth = dup_text(json_string(cJSON_GetObjectItemCaseSensitive(ap, "bandwidth"), ""));
        node.frequency = dup_text(json_string(cJSON_GetObjectItemCaseSensitive(ap, "frequency"), ""));
        cJSON *x = cJSON_GetObjectItemCaseSensitive(ap, "x");
        cJSON *y = cJSON_GetObjectItemCaseSensitive(ap, "y");
        cJSON *raio = cJSON_GetObjectItemCaseSensitive(ap, "raio");
        cJSON *locked = cJSON_GetObjectItemCaseSensitive(ap, "locked");
        node.x = cJSON_IsNumber(x) ? x->valuedouble : 0.0;
        node.y = cJSON_IsNumber(y) ? y->valuedouble : 0.0;
        node.raio = cJSON_IsNumber(raio) ? raio->valuedouble : default_coverage_radius(node.frequency);
        node.locked = cJSON_IsBool(locked) ? cJSON_IsTrue(locked) : 0;
        add_node(graph, node);
    }

    if (graph->node_count == 0) {
        *error_message = dup_text("Grafo vazio - nenhum ponto de acesso valido");
        return false;
    }

    // APs de faixas diferentes nao interferem (s = 0): o grafo e a uniao disjunta dos grafos de cada faixa.
    for (int left = 0; left < graph->node_count; left++) {
        double left_band = normalize_frequency_band(graph->nodes[left].frequency);
        for (int right = left + 1; right < graph->node_count; right++) {
            if (left_band == 0.0 || normalize_frequency_band(graph->nodes[right].frequency) != left_band) {
                continue;
            }
            double peso = collision_percentage(&graph->nodes[left], &graph->nodes[right]);
            if (peso > 0.0) {
                add_edge(graph, left, right, peso);
            }
        }
    }
    analysis_log(
        ANALYSIS_LOG_DEBUG,
        NULL,
        "build_graph concluido: nodes=%d edges=%d duration_ms=%.2f",
        graph->node_count,
        graph->edge_count,
        (now_seconds() - build_started_at) * 1000.0
    );
    return true;
}

static size_t curl_callback(void *contents, size_t size, size_t nmemb, void *userp) {
    size_t real_size = size * nmemb;
    CurlBuffer *buffer = userp;
    char *ptr = realloc(buffer->data, buffer->size + real_size + 1);
    if (!ptr) {
        return 0;
    }
    buffer->data = ptr;
    memcpy(buffer->data + buffer->size, contents, real_size);
    buffer->size += real_size;
    buffer->data[buffer->size] = '\0';
    return real_size;
}

static cJSON *fetch_access_points(void) {
    const char *access_point_service_url = getenv("ACCESS_POINT_SERVICE_URL");
    if (!access_point_service_url || access_point_service_url[0] == '\0') {
        return NULL;
    }
    char url[512];
    snprintf(url, sizeof(url), "%s/access_points", access_point_service_url);

    CURL *curl = curl_easy_init();
    if (!curl) {
        return NULL;
    }
    CurlBuffer buffer = {0};
    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, curl_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &buffer);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 30L);

    CURLcode code = curl_easy_perform(curl);
    long http_code = 0;
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);
    curl_easy_cleanup(curl);
    if (code != CURLE_OK || http_code != 200 || !buffer.data) {
        free(buffer.data);
        return NULL;
    }
    cJSON *json = cJSON_Parse(buffer.data);
    free(buffer.data);
    return json;
}

static Job *register_job(void) {
    Job *job = calloc(1, sizeof(Job));
    if (!job) {
        perror("calloc job");
        exit(1);
    }
    pthread_mutex_lock(&jobs_mutex);
    job_sequence++;
    atomic_init(&job->cancelled, 0);
    snprintf(job->id, sizeof(job->id), "job-%llu", job_sequence);
    job->next = jobs_head;
    jobs_head = job;
    pthread_mutex_unlock(&jobs_mutex);
    analysis_log(ANALYSIS_LOG_INFO, job->id, "job registrado");
    return job;
}

static Job *find_job(const char *job_id) {
    pthread_mutex_lock(&jobs_mutex);
    Job *cursor = jobs_head;
    while (cursor) {
        if (strcmp(cursor->id, job_id) == 0) {
            pthread_mutex_unlock(&jobs_mutex);
            return cursor;
        }
        cursor = cursor->next;
    }
    pthread_mutex_unlock(&jobs_mutex);
    return NULL;
}

static void unregister_job(Job *job) {
    pthread_mutex_lock(&jobs_mutex);
    Job **cursor = &jobs_head;
    while (*cursor) {
        if (*cursor == job) {
            *cursor = job->next;
            break;
        }
        cursor = &(*cursor)->next;
    }
    pthread_mutex_unlock(&jobs_mutex);
    analysis_log(ANALYSIS_LOG_INFO, job->id, "job finalizado e removido");
    job->threads = NULL;
    job->thread_count = 0;
    free(job);
}

static double now_seconds(void) {
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return ts.tv_sec + (ts.tv_nsec / 1000000000.0);
}

static void handle_health(int fd) {
    cJSON *json = cJSON_CreateObject();
    cJSON_AddStringToObject(json, "status", "healthy");
    cJSON_AddStringToObject(json, "service", "analysis_service");
    cJSON_AddNumberToObject(json, "port", atoi(getenv("PORT") ? getenv("PORT") : "5002"));
    char *text = cJSON_PrintUnformatted(json);
    cJSON_Delete(json);
    send_http(fd, 200, "OK", "application/json", text);
    free(text);
}

static void handle_strategies(int fd) {
    cJSON *json = cJSON_CreateObject();
    cJSON_AddBoolToObject(json, "success", true);
    cJSON *strategies = cJSON_AddObjectToObject(json, "strategies");
    size_t strategy_count = 0;
    const AnalysisStrategy *registered_strategies = analysis_strategies(&strategy_count);
    cJSON *details = cJSON_AddArrayToObject(json, "strategy_details");
    for (size_t index = 0; index < strategy_count; index++) {
        const AnalysisStrategy *strategy = &registered_strategies[index];
        cJSON_AddStringToObject(strategies, strategy->name, strategy->description);
        cJSON *detail = cJSON_CreateObject();
        cJSON_AddStringToObject(detail, "name", strategy->name);
        cJSON_AddStringToObject(detail, "description", strategy->description);
        cJSON_AddStringToObject(detail, "mode", strategy->mode);
        cJSON_AddBoolToObject(detail, "exact", strategy->exact);
        cJSON_AddBoolToObject(detail, "implemented", strategy->run != NULL);
        cJSON_AddItemToObject(detail, "parameters", build_strategy_parameters_json(strategy));
        cJSON_AddItemToArray(details, detail);
    }
    cJSON_AddStringToObject(json, "message", "Estrategias disponiveis para analise de grafos");
    char *text = cJSON_PrintUnformatted(json);
    cJSON_Delete(json);
    send_http(fd, 200, "OK", "application/json", text);
    free(text);
}

static void add_channel_to_plan(cJSON *plan, const char *frequency, const char *bandwidth, const char *channel) {
    cJSON *band = cJSON_GetObjectItemCaseSensitive(plan, frequency);
    if (!band) {
        band = cJSON_AddObjectToObject(plan, frequency);
    }
    cJSON *channels = cJSON_GetObjectItemCaseSensitive(band, bandwidth);
    if (!channels) {
        channels = cJSON_AddArrayToObject(band, bandwidth);
    }
    cJSON_AddItemToArray(channels, cJSON_CreateString(channel));
}

static cJSON *build_valid_channel_plan(void) {
    cJSON *plan = cJSON_CreateObject();
    size_t band_count = sizeof(BAND_BANDWIDTHS) / sizeof(BAND_BANDWIDTHS[0]);
    size_t segment_count = sizeof(CHANNEL_SEGMENTS) / sizeof(CHANNEL_SEGMENTS[0]);
    for (size_t band_index = 0; band_index < band_count; band_index++) {
        const BandBandwidths *band = &BAND_BANDWIDTHS[band_index];
        for (int width_index = 0; width_index < band->bandwidth_count; width_index++) {
            int bandwidth = band->bandwidths[width_index];
            int channels_per_block = bandwidth / 20;
            char bandwidth_label[16];
            snprintf(bandwidth_label, sizeof(bandwidth_label), "%d MHz", bandwidth);

            for (size_t segment_index = 0; segment_index < segment_count; segment_index++) {
                const ChannelSegment *segment = &CHANNEL_SEGMENTS[segment_index];
                if (strcmp(segment->frequency, band->frequency) != 0) {
                    continue;
                }
                int block_span = segment->aligned_blocks ? channels_per_block * segment->channel_step : segment->channel_step;
                int block_size = segment->aligned_blocks ? channels_per_block : 1;
                for (int block_start = segment->first_channel;
                     block_start + (block_size - 1) * segment->channel_step <= segment->last_channel;
                     block_start += block_span) {
                    for (int offset = 0; offset < block_size; offset++) {
                        char channel_label[8];
                        snprintf(channel_label, sizeof(channel_label), "%d", block_start + offset * segment->channel_step);
                        add_channel_to_plan(plan, band->frequency, bandwidth_label, channel_label);
                    }
                }
            }
        }
    }
    return plan;
}

static cJSON *build_search_profile_plan(void) {
    cJSON *plan = cJSON_CreateObject();
    const ProfileSet *profiles = default_search_profiles();
    for (int index = 0; index < profiles->count; index++) {
        const ProposedConfig *profile = &profiles->items[index];
        add_channel_to_plan(plan, profile->frequency, profile->bandwidth, profile->channel);
    }
    return plan;
}

// Primario enviado por uma opcao de busca: o do perfil padrao que cai no bloco, se houver (mantem os resultados
// padrao); senao, o primeiro canal do bloco. Qualquer primario do bloco tem o mesmo centro.
static const char *option_primary(const char *frequency, const char *bandwidth, cJSON *channels) {
    const ProfileSet *defaults = default_search_profiles();
    for (int index = 0; index < defaults->count; index++) {
        const ProposedConfig *profile = &defaults->items[index];
        if (strcmp(profile->frequency, frequency) != 0 || strcmp(profile->bandwidth, bandwidth) != 0) {
            continue;
        }
        cJSON *channel = NULL;
        cJSON_ArrayForEach(channel, channels) {
            if (strcmp(channel->valuestring, profile->channel) == 0) {
                return profile->channel;
            }
        }
    }
    return cJSON_GetArrayItem(channels, 0)->valuestring;
}

static void add_option_to_plan(cJSON *plan, const char *frequency, const char *bandwidth, cJSON *channels) {
    cJSON *band = cJSON_GetObjectItemCaseSensitive(plan, frequency);
    if (!band) {
        band = cJSON_AddObjectToObject(plan, frequency);
    }
    cJSON *options = cJSON_GetObjectItemCaseSensitive(band, bandwidth);
    if (!options) {
        options = cJSON_AddArrayToObject(band, bandwidth);
    }
    const char *primary = option_primary(frequency, bandwidth, channels);
    double width = parse_bandwidth_mhz(bandwidth);
    double center = channel_center_mhz(normalize_frequency_band(frequency), parse_channel_number(primary), width);
    cJSON *option = cJSON_CreateObject();
    cJSON_AddStringToObject(option, "channel", primary);
    cJSON_AddItemToObject(option, "channels", channels);
    cJSON_AddNumberToObject(option, "lower_mhz", center - (width / 2.0));
    cJSON_AddNumberToObject(option, "upper_mhz", center + (width / 2.0));
    cJSON_AddItemToArray(options, option);
}

// Opcoes para escolher os perfis de busca: uma por posicao distinta no espectro. Em 5 e 6 GHz, cada bloco
// alinhado de canais agregados e uma opcao. Em 2,4 GHz, cada canal de 20 MHz e uma opcao, e cada par de 40 MHz
// (primario e secundario 4 canais acima) tambem; os primarios 10 a 13 repetem os pares 6+10 a 9+13.
static cJSON *build_search_option_plan(void) {
    cJSON *plan = cJSON_CreateObject();
    size_t band_count = sizeof(BAND_BANDWIDTHS) / sizeof(BAND_BANDWIDTHS[0]);
    size_t segment_count = sizeof(CHANNEL_SEGMENTS) / sizeof(CHANNEL_SEGMENTS[0]);
    for (size_t band_index = 0; band_index < band_count; band_index++) {
        const BandBandwidths *band = &BAND_BANDWIDTHS[band_index];
        for (int width_index = 0; width_index < band->bandwidth_count; width_index++) {
            int bandwidth = band->bandwidths[width_index];
            int channels_per_block = bandwidth / 20;
            char bandwidth_label[16];
            snprintf(bandwidth_label, sizeof(bandwidth_label), "%d MHz", bandwidth);

            for (size_t segment_index = 0; segment_index < segment_count; segment_index++) {
                const ChannelSegment *segment = &CHANNEL_SEGMENTS[segment_index];
                if (strcmp(segment->frequency, band->frequency) != 0) {
                    continue;
                }
                // Distancia entre o primeiro e o ultimo canal de 20 MHz do bloco.
                int block_reach = segment->aligned_blocks
                    ? (channels_per_block - 1) * segment->channel_step
                    : (channels_per_block - 1) * 4;
                int block_span = segment->aligned_blocks ? channels_per_block * segment->channel_step : segment->channel_step;
                for (int block_start = segment->first_channel;
                     block_start + block_reach <= segment->last_channel;
                     block_start += block_span) {
                    cJSON *channels = cJSON_CreateArray();
                    int channel_step = segment->aligned_blocks ? segment->channel_step : 4;
                    for (int offset = 0; offset < channels_per_block; offset++) {
                        char channel_label[8];
                        snprintf(channel_label, sizeof(channel_label), "%d", block_start + offset * channel_step);
                        cJSON_AddItemToArray(channels, cJSON_CreateString(channel_label));
                    }
                    add_option_to_plan(plan, band->frequency, bandwidth_label, channels);
                }
            }
        }
    }
    return plan;
}

typedef struct {
    ProposedConfig *items;
    int count;
    int capacity;
} ProfileList;

static void append_profile(ProfileList *list, const char *channel, const char *bandwidth, const char *frequency) {
    if (list->count >= list->capacity) {
        list->capacity = list->capacity > 0 ? list->capacity * 2 : 32;
        list->items = realloc(list->items, sizeof(ProposedConfig) * (size_t) list->capacity);
        if (!list->items) {
            perror("realloc profiles");
            exit(1);
        }
    }
    list->items[list->count++] = (ProposedConfig){channel, bandwidth, frequency};
}

static bool channel_in_plan(cJSON *plan, const char *frequency, const char *bandwidth, const char *channel) {
    cJSON *channels = cJSON_GetObjectItemCaseSensitive(cJSON_GetObjectItemCaseSensitive(plan, frequency), bandwidth);
    cJSON *item = NULL;
    cJSON_ArrayForEach(item, channels) {
        if (cJSON_IsString(item) && strcmp(item->valuestring, channel) == 0) {
            return true;
        }
    }
    return false;
}

// Perfis da requisicao: as faixas informadas em "channels" usam os canais escolhidos, validados contra o plano
// de canais permitidos; as demais usam os perfis padrao. As cadeias apontam para o payload, que vive ate o fim
// da requisicao.
static bool build_requested_profiles(cJSON *payload, ProfileList *list, char *error, size_t error_size) {
    memset(list, 0, sizeof(*list));
    cJSON *channels = cJSON_GetObjectItemCaseSensitive(payload, "channels");
    if (channels && !cJSON_IsNull(channels) && !cJSON_IsObject(channels)) {
        snprintf(error, error_size, "Campo channels deve ser um objeto por faixa e largura de banda");
        return false;
    }
    bool has_selection = cJSON_IsObject(channels);

    if (has_selection) {
        cJSON *valid = build_valid_channel_plan();
        cJSON *band = NULL;
        cJSON_ArrayForEach(band, channels) {
            if (!cJSON_IsObject(band) || !cJSON_GetObjectItemCaseSensitive(valid, band->string)) {
                snprintf(error, error_size, "Faixa invalida em channels: %s", band->string);
                cJSON_Delete(valid);
                return false;
            }
            int band_profiles = 0;
            cJSON *width = NULL;
            cJSON_ArrayForEach(width, band) {
                if (!cJSON_IsArray(width) || !cJSON_GetObjectItemCaseSensitive(cJSON_GetObjectItemCaseSensitive(valid, band->string), width->string)) {
                    snprintf(error, error_size, "Largura de banda invalida em %s: %s", band->string, width->string);
                    cJSON_Delete(valid);
                    return false;
                }
                cJSON *channel = NULL;
                cJSON_ArrayForEach(channel, width) {
                    if (!cJSON_IsString(channel) || !channel_in_plan(valid, band->string, width->string, channel->valuestring)) {
                        snprintf(
                            error,
                            error_size,
                            "Canal invalido em %s a %s: %s",
                            band->string,
                            width->string,
                            cJSON_IsString(channel) ? channel->valuestring : "(nao textual)"
                        );
                        cJSON_Delete(valid);
                        return false;
                    }
                    append_profile(list, channel->valuestring, width->string, band->string);
                    band_profiles++;
                }
            }
            if (band_profiles == 0) {
                snprintf(error, error_size, "Informe ao menos um canal para a faixa %s", band->string);
                cJSON_Delete(valid);
                return false;
            }
        }
        cJSON_Delete(valid);
    }

    const ProfileSet *defaults = default_search_profiles();
    for (int index = 0; index < defaults->count; index++) {
        const ProposedConfig *profile = &defaults->items[index];
        if (!has_selection || !cJSON_GetObjectItemCaseSensitive(channels, profile->frequency)) {
            append_profile(list, profile->channel, profile->bandwidth, profile->frequency);
        }
    }
    return true;
}

static bool reject_invalid_channels(int fd, cJSON *payload, ProfileList *profiles) {
    char error[256];
    if (build_requested_profiles(payload, profiles, error, sizeof(error))) {
        return false;
    }
    free(profiles->items);
    memset(profiles, 0, sizeof(*profiles));
    analysis_log(ANALYSIS_LOG_INFO, NULL, "canais invalidos: %s", error);
    send_json_error(fd, 400, error);
    return true;
}

static void handle_channel_plan(int fd) {
    cJSON *json = cJSON_CreateObject();
    cJSON_AddBoolToObject(json, "success", true);
    cJSON_AddItemToObject(json, "valid", build_valid_channel_plan());
    cJSON_AddItemToObject(json, "profiles", build_search_profile_plan());
    cJSON_AddItemToObject(json, "options", build_search_option_plan());
    char *text = cJSON_PrintUnformatted(json);
    cJSON_Delete(json);
    send_http(fd, 200, "OK", "application/json", text);
    free(text);
}

static void handle_capabilities(int fd) {
    cJSON *json = cJSON_CreateObject();
    cJSON_AddBoolToObject(json, "success", true);
    cJSON_AddNumberToObject(json, "available_threads", available_processor_count());
    cJSON_AddStringToObject(json, "service", "analysis_service");
    char *text = cJSON_PrintUnformatted(json);
    cJSON_Delete(json);
    send_http(fd, 200, "OK", "application/json", text);
    free(text);
}

static void handle_analyze_overview(int fd) {
    cJSON *aps = fetch_access_points();
    if (!aps || !cJSON_IsArray(aps)) {
        cJSON_Delete(aps);
        send_json_error(fd, 500, "Erro ao buscar pontos de acesso");
        return;
    }

    int total = cJSON_GetArraySize(aps);
    int with_coordinates = 0;
    cJSON *json = cJSON_CreateObject();
    cJSON *frequency_distribution = cJSON_AddObjectToObject(json, "frequency_distribution");
    cJSON *channel_distribution = cJSON_AddObjectToObject(json, "channel_distribution");
    cJSON *bandwidth_distribution = cJSON_AddObjectToObject(json, "bandwidth_distribution");
    cJSON *available_strategies = cJSON_AddObjectToObject(json, "available_strategies");
    size_t strategy_count = 0;
    const AnalysisStrategy *registered_strategies = analysis_strategies(&strategy_count);
    for (size_t index = 0; index < strategy_count; index++) {
        cJSON_AddStringToObject(available_strategies, registered_strategies[index].name, registered_strategies[index].description);
    }

    for (int i = 0; i < total; i++) {
        cJSON *ap = cJSON_GetArrayItem(aps, i);
        cJSON *lat = cJSON_GetObjectItemCaseSensitive(ap, "latitude");
        cJSON *lon = cJSON_GetObjectItemCaseSensitive(ap, "longitude");
        if (cJSON_IsNumber(lat) && cJSON_IsNumber(lon)) {
            with_coordinates++;
        }

        const char *frequency = json_string(cJSON_GetObjectItemCaseSensitive(ap, "frequency"), "Unknown");
        const char *channel = json_string(cJSON_GetObjectItemCaseSensitive(ap, "channel"), "Unknown");
        const char *bandwidth = json_string(cJSON_GetObjectItemCaseSensitive(ap, "bandwidth"), "Unknown");

        cJSON *freq = cJSON_GetObjectItemCaseSensitive(frequency_distribution, frequency);
        cJSON *chan = cJSON_GetObjectItemCaseSensitive(channel_distribution, channel);
        cJSON *band = cJSON_GetObjectItemCaseSensitive(bandwidth_distribution, bandwidth);
        if (freq) { freq->valuedouble += 1; freq->valueint += 1; } else { cJSON_AddNumberToObject(frequency_distribution, frequency, 1); }
        if (chan) { chan->valuedouble += 1; chan->valueint += 1; } else { cJSON_AddNumberToObject(channel_distribution, channel, 1); }
        if (band) { band->valuedouble += 1; band->valueint += 1; } else { cJSON_AddNumberToObject(bandwidth_distribution, bandwidth, 1); }
    }

    cJSON_AddNumberToObject(json, "total_points", total);
    cJSON_AddNumberToObject(json, "with_coordinates", with_coordinates);
    cJSON_AddNumberToObject(json, "without_coordinates", total - with_coordinates);

    char *text = cJSON_PrintUnformatted(json);
    cJSON_Delete(json);
    cJSON_Delete(aps);
    send_http(fd, 200, "OK", "application/json", text);
    free(text);
}

static void add_graph_metrics(cJSON *json, const Graph *graph) {
    int max_degree = 0;
    for (int index = 0; index < graph->node_count; index++) {
        if (graph->nodes[index].neighbor_count > max_degree) {
            max_degree = graph->nodes[index].neighbor_count;
        }
    }
    cJSON_AddNumberToObject(json, "nodes", graph->node_count);
    cJSON_AddNumberToObject(json, "edges", graph->edge_count);
    cJSON_AddNumberToObject(json, "density", graph_density(graph));
    cJSON_AddNumberToObject(json, "average_degree", graph->node_count > 0 ? (2.0 * graph->edge_count) / graph->node_count : 0.0);
    cJSON_AddNumberToObject(json, "max_degree", max_degree);
}

// Metricas do grafo de conflitos potenciais (APs da mesma faixa com coberturas sobrepostas), no total e por
// faixa, sem executar estrategia nem devolver o grafo inteiro.
static void handle_graph_metrics(int fd, cJSON *payload) {
    Graph graph;
    char *error_message = NULL;
    if (!build_graph(payload, &graph, &error_message)) {
        send_json_error(fd, 400, error_message ? error_message : "Erro ao montar grafo");
        free(error_message);
        return;
    }

    cJSON *json = cJSON_CreateObject();
    cJSON_AddBoolToObject(json, "success", true);
    add_graph_metrics(json, &graph);
    cJSON *bands_json = cJSON_AddArrayToObject(json, "bands");
    double bands[MAX_BANDS];
    int band_count = collect_bands(&graph, bands);
    int *original_indexes = malloc(sizeof(int) * (size_t) graph.node_count);
    int *local_indexes = malloc(sizeof(int) * (size_t) graph.node_count);
    if (!original_indexes || !local_indexes) {
        perror("malloc graph metrics");
        exit(1);
    }
    for (int band_index = 0; band_index < band_count; band_index++) {
        Graph subgraph;
        build_band_subgraph(&graph, bands[band_index], &subgraph, original_indexes, local_indexes);
        char band_label[32];
        snprintf(band_label, sizeof(band_label), "%g GHz", bands[band_index]);
        cJSON *band_json = cJSON_CreateObject();
        cJSON_AddStringToObject(band_json, "frequency", band_label);
        add_graph_metrics(band_json, &subgraph);
        cJSON_AddItemToArray(bands_json, band_json);
        free_band_subgraph(&subgraph);
    }
    free(original_indexes);
    free(local_indexes);

    char *text = cJSON_PrintUnformatted(json);
    cJSON_Delete(json);
    send_http(fd, 200, "OK", "application/json", text);
    free(text);
    free_graph(&graph);
}

static void handle_collision_graph(int fd, cJSON *payload) {
    Graph graph;
    char *error_message = NULL;
    analysis_log(ANALYSIS_LOG_INFO, NULL, "POST /collision-graph iniciado");
    if (!build_graph(payload, &graph, &error_message)) {
        send_json_error(fd, 400, error_message ? error_message : "Erro ao montar grafo");
        free(error_message);
        return;
    }
    cJSON *json = build_graph_json(&graph, NULL);
    char *text = cJSON_PrintUnformatted(json);
    cJSON_Delete(json);
    send_http(fd, 200, "OK", "application/json", text);
    free(text);
    free_graph(&graph);
}

static void handle_analyze_graph(int fd, cJSON *payload) {
    Graph graph;
    char *error_message = NULL;
    const char *strategy = json_string(cJSON_GetObjectItemCaseSensitive(payload, "strategy"), "backtracking");
    int thread_count = parse_thread_count(payload);
    analysis_log(ANALYSIS_LOG_INFO, NULL, "POST /analyze-graph strategy=%s threads=%d", strategy, thread_count);
    const AnalysisStrategy *selected_strategy = find_analysis_strategy(strategy);
    if (!selected_strategy) {
        send_json_error(fd, 400, "Estrategia nao encontrada. Estrategias disponiveis: backtracking, greedy, genetic");
        return;
    }
    if (reject_invalid_parameters(fd, selected_strategy, payload)) {
        return;
    }
    ProfileList profiles;
    if (reject_invalid_channels(fd, payload, &profiles)) {
        return;
    }
    if (!build_graph(payload, &graph, &error_message)) {
        send_json_error(fd, 400, error_message ? error_message : "Erro ao montar grafo");
        free(error_message);
        free(profiles.items);
        return;
    }
    double started_at = now_seconds();
    ProfileSet profile_set = {profiles.items, profiles.count};
    cJSON *json = selected_strategy->run
        ? build_strategy_response_json(selected_strategy, &graph, payload_parameters(payload), &profile_set, NULL, -1, NULL, started_at)
        : build_placeholder_response_json(selected_strategy->name, &graph, thread_count, started_at);
    free(profiles.items);
    char *text = cJSON_PrintUnformatted(json);
    cJSON_Delete(json);
    send_http(fd, 200, "OK", "application/json", text);
    analysis_log(ANALYSIS_LOG_INFO, NULL, "POST /analyze-graph concluido strategy=%s duration_ms=%.2f", strategy, (now_seconds() - started_at) * 1000.0);
    free(text);
    free_graph(&graph);
}

static void handle_analyze_graph_stream(int fd, cJSON *payload) {
    const char *strategy = json_string(cJSON_GetObjectItemCaseSensitive(payload, "strategy"), "backtracking");
    const AnalysisStrategy *selected_strategy = find_analysis_strategy(strategy);
    if (!selected_strategy) {
        send_json_error(fd, 400, "Estrategia nao encontrada. Estrategias disponiveis: backtracking, greedy, genetic");
        return;
    }
    if (reject_invalid_parameters(fd, selected_strategy, payload)) {
        return;
    }
    ProfileList profiles;
    if (reject_invalid_channels(fd, payload, &profiles)) {
        return;
    }

    Job *job = register_job();
    int thread_count = parse_thread_count(payload);
    analysis_log(ANALYSIS_LOG_INFO, job->id, "POST /analyze-graph-stream strategy=%s threads=%d", strategy, thread_count);
    pthread_mutex_t stream_lock;
    pthread_mutex_init(&stream_lock, NULL);

    dprintf(fd, "HTTP/1.1 200 OK\r\nContent-Type: application/x-ndjson\r\nConnection: close\r\n\r\n");

    cJSON *started = cJSON_CreateObject();
    cJSON_AddStringToObject(started, "job_id", job->id);
    cJSON_AddStringToObject(started, "strategy", strategy);
    cJSON_AddStringToObject(started, "message", "Montando grafo base e preparando atribuicao");
    if (!stream_event(fd, &stream_lock, "started", started)) {
        analysis_log(ANALYSIS_LOG_ERROR, job->id, "falha ao enviar evento started");
        free(profiles.items);
        pthread_mutex_destroy(&stream_lock);
        unregister_job(job);
        return;
    }

    Graph graph;
    char *error_message = NULL;
    if (!build_graph(payload, &graph, &error_message)) {
        analysis_log(ANALYSIS_LOG_ERROR, job->id, "falha ao montar grafo: %s", error_message ? error_message : "erro desconhecido");
        cJSON *error_payload = cJSON_CreateObject();
        cJSON_AddBoolToObject(error_payload, "success", false);
        cJSON_AddStringToObject(error_payload, "error", error_message ? error_message : "Erro ao montar grafo");
        cJSON_AddNumberToObject(error_payload, "status_code", 400);
        stream_event(fd, &stream_lock, "error", error_payload);
        free(error_message);
        free(profiles.items);
        pthread_mutex_destroy(&stream_lock);
        unregister_job(job);
        return;
    }

    double started_at = now_seconds();
    ProfileSet profile_set = {profiles.items, profiles.count};
    cJSON *json = selected_strategy->run
        ? build_strategy_response_json(selected_strategy, &graph, payload_parameters(payload), &profile_set, job, fd, &stream_lock, started_at)
        : build_placeholder_response_json(selected_strategy->name, &graph, thread_count, started_at);
    free(profiles.items);
    if (atomic_load(&job->cancelled)) {
        analysis_log(ANALYSIS_LOG_INFO, job->id, "analise cancelada durante execucao");
        cJSON *cancelled = cJSON_CreateObject();
        cJSON_AddBoolToObject(cancelled, "success", false);
        cJSON_AddStringToObject(cancelled, "error", "Analise cancelada pelo usuario");
        cJSON_AddStringToObject(cancelled, "job_id", job->id);
        stream_event(fd, &stream_lock, "cancelled", cancelled);
    } else {
        analysis_log(ANALYSIS_LOG_INFO, job->id, "analise concluida strategy=%s duration_ms=%.2f", strategy, (now_seconds() - started_at) * 1000.0);
        stream_event(fd, &stream_lock, "result", json);
    }

    pthread_mutex_destroy(&stream_lock);
    unregister_job(job);
    free_graph(&graph);
}

static void handle_cancel_analysis(int fd, cJSON *payload) {
    const char *job_id = json_string(cJSON_GetObjectItemCaseSensitive(payload, "job_id"), NULL);
    if (!job_id || job_id[0] == '\0') {
        send_json_error(fd, 400, "job_id obrigatorio");
        return;
    }
    Job *job = find_job(job_id);
    if (!job) {
        send_json_error(fd, 404, "Execucao nao encontrada ou ja finalizada");
        return;
    }
    atomic_store(&job->cancelled, 1);
    analysis_log(ANALYSIS_LOG_INFO, job->id, "cancelamento solicitado pelo cliente");
    for (int index = 0; index < job->thread_count; index++) {
        pthread_cancel(job->threads[index]);
    }

    cJSON *json = cJSON_CreateObject();
    cJSON_AddBoolToObject(json, "success", true);
    cJSON_AddStringToObject(json, "job_id", job_id);
    cJSON_AddStringToObject(json, "message", "Cancelamento solicitado");
    char *text = cJSON_PrintUnformatted(json);
    cJSON_Delete(json);
    send_http(fd, 200, "OK", "application/json", text);
    free(text);
}

static void handle_compare_strategies(int fd, cJSON *payload) {
    Graph graph;
    char *error_message = NULL;
    ProfileList profiles;
    if (reject_invalid_channels(fd, payload, &profiles)) {
        return;
    }
    ProfileSet profile_set = {profiles.items, profiles.count};
    if (!build_graph(payload, &graph, &error_message)) {
        send_json_error(fd, 400, error_message ? error_message : "Erro ao montar grafo");
        free(error_message);
        free(profiles.items);
        return;
    }

    cJSON *json = cJSON_CreateObject();
    cJSON_AddBoolToObject(json, "success", true);
    cJSON *results = cJSON_AddObjectToObject(json, "comparison_results");
    cJSON *summary = cJSON_AddObjectToObject(json, "comparison_summary");
    cJSON *tested = cJSON_AddArrayToObject(summary, "strategies_tested");

    cJSON *strategies = cJSON_GetObjectItemCaseSensitive(payload, "strategies");
    if (!cJSON_IsArray(strategies) || cJSON_GetArraySize(strategies) == 0) {
        strategies = cJSON_CreateArray();
        size_t strategy_count = 0;
        const AnalysisStrategy *registered_strategies = analysis_strategies(&strategy_count);
        for (size_t index = 0; index < strategy_count; index++) {
            cJSON_AddItemToArray(strategies, cJSON_CreateString(registered_strategies[index].name));
        }
    }

    for (int i = 0; i < cJSON_GetArraySize(strategies); i++) {
        const char *strategy = json_string(cJSON_GetArrayItem(strategies, i), "backtracking");
        const AnalysisStrategy *selected_strategy = find_analysis_strategy(strategy);
        if (!selected_strategy) {
            continue;
        }
        cJSON_AddItemToArray(tested, cJSON_CreateString(strategy));
        char parameter_error[256];
        if (!validate_strategy_parameters(selected_strategy, payload_parameters(payload), parameter_error, sizeof(parameter_error))) {
            cJSON *failure = cJSON_CreateObject();
            cJSON_AddStringToObject(failure, "error", parameter_error);
            cJSON_AddItemToObject(results, strategy, failure);
            continue;
        }
        cJSON *result = selected_strategy->run
            ? build_strategy_response_json(selected_strategy, &graph, payload_parameters(payload), &profile_set, NULL, -1, NULL, now_seconds())
            : build_placeholder_response_json(selected_strategy->name, &graph, 1, now_seconds());
        if (result) {
            cJSON *analysis = cJSON_DetachItemFromObject(result, "analysis");
            cJSON *execution = cJSON_DetachItemFromObject(result, "execution");
            cJSON_AddItemToObject(analysis, "execution", execution);
            cJSON_AddItemToObject(results, strategy, analysis);
            cJSON_Delete(result);
        }
    }

    cJSON_AddStringToObject(summary, "best_strategy", "backtracking");
    cJSON_AddItemToObject(summary, "performance_metrics", cJSON_CreateObject());
    cJSON *graph_info = cJSON_AddObjectToObject(json, "graph_info");
    cJSON_AddNumberToObject(graph_info, "nodes", graph.node_count);
    cJSON_AddNumberToObject(graph_info, "edges", graph.edge_count);
    cJSON_AddNumberToObject(graph_info, "density", graph_density(&graph));

    char *text = cJSON_PrintUnformatted(json);
    cJSON_Delete(json);
    send_http(fd, 200, "OK", "application/json", text);
    free(text);
    free_graph(&graph);
    free(profiles.items);
}

static char *read_request_text(int fd) {
    size_t capacity = READ_CHUNK;
    size_t size = 0;
    char *buffer = malloc(capacity + 1);
    if (!buffer) {
        perror("malloc request");
        exit(1);
    }
    while (1) {
        if (size == capacity) {
            capacity *= 2;
            buffer = realloc(buffer, capacity + 1);
            if (!buffer) {
                perror("realloc request");
                exit(1);
            }
        }
        ssize_t received = recv(fd, buffer + size, capacity - size, 0);
        if (received <= 0) {
            break;
        }
        size += (size_t) received;
        buffer[size] = '\0';
        if (strstr(buffer, "\r\n\r\n")) {
            break;
        }
    }
    buffer[size] = '\0';
    return buffer;
}

static Request *parse_request(int fd) {
    char *raw = read_request_text(fd);
    if (!raw || raw[0] == '\0') {
        free(raw);
        return NULL;
    }
    char *header_end = strstr(raw, "\r\n\r\n");
    if (!header_end) {
        free(raw);
        return NULL;
    }
    size_t header_size = (size_t) (header_end - raw) + 4;
    char method[16] = {0};
    char path[256] = {0};
    sscanf(raw, "%15s %255s", method, path);

    size_t content_length = 0;
    char *content_length_header = strstr(raw, "Content-Length:");
    if (content_length_header) {
        sscanf(content_length_header, "Content-Length: %zu", &content_length);
    }

    char *body = malloc(content_length + 1);
    if (!body) {
        perror("malloc body");
        exit(1);
    }
    size_t body_bytes = strlen(raw) > header_size ? strlen(raw) - header_size : 0;
    if (body_bytes > 0) {
        memcpy(body, raw + header_size, body_bytes);
    }
    while (body_bytes < content_length) {
        ssize_t received = recv(fd, body + body_bytes, content_length - body_bytes, 0);
        if (received <= 0) {
            break;
        }
        body_bytes += (size_t) received;
    }
    body[body_bytes] = '\0';
    free(raw);

    Request *request = calloc(1, sizeof(Request));
    if (!request) {
        perror("calloc request");
        exit(1);
    }
    request->method = dup_text(method);
    request->path = dup_text(path);
    request->body = body;
    return request;
}

static void free_request(Request *request) {
    if (!request) {
        return;
    }
    free(request->method);
    free(request->path);
    free(request->body);
    free(request);
}

static void route_request(int fd, Request *request) {
    if (!request) {
        send_json_error(fd, 400, "Requisicao invalida");
        return;
    }
    if (strcmp(request->method, "GET") == 0 && strcmp(request->path, "/health") == 0) { handle_health(fd); return; }
    if (strcmp(request->method, "GET") == 0 && strcmp(request->path, "/strategies") == 0) { handle_strategies(fd); return; }
    if (strcmp(request->method, "GET") == 0 && strcmp(request->path, "/capabilities") == 0) { handle_capabilities(fd); return; }
    if (strcmp(request->method, "GET") == 0 && strcmp(request->path, "/channel-plan") == 0) { handle_channel_plan(fd); return; }
    if (strcmp(request->method, "GET") == 0 && strcmp(request->path, "/analyze") == 0) { handle_analyze_overview(fd); return; }

    cJSON *payload = request->body && request->body[0] ? cJSON_Parse(request->body) : cJSON_CreateObject();
    if (!payload) {
        payload = cJSON_CreateObject();
    }

    if (strcmp(request->method, "POST") == 0 && strcmp(request->path, "/collision-graph") == 0) {
        handle_collision_graph(fd, payload);
    } else if (strcmp(request->method, "POST") == 0 && strcmp(request->path, "/graph-metrics") == 0) {
        handle_graph_metrics(fd, payload);
    } else if (strcmp(request->method, "POST") == 0 && strcmp(request->path, "/backtracking") == 0) {
        cJSON_ReplaceItemInObject(payload, "strategy", cJSON_CreateString("backtracking"));
        handle_analyze_graph(fd, payload);
    } else if (strcmp(request->method, "POST") == 0 && strcmp(request->path, "/backtracking-stream") == 0) {
        cJSON_ReplaceItemInObject(payload, "strategy", cJSON_CreateString("backtracking"));
        handle_analyze_graph_stream(fd, payload);
    } else if (strcmp(request->method, "POST") == 0 && strcmp(request->path, "/analyze-graph") == 0) {
        handle_analyze_graph(fd, payload);
    } else if (strcmp(request->method, "POST") == 0 && strcmp(request->path, "/analyze-graph-stream") == 0) {
        handle_analyze_graph_stream(fd, payload);
    } else if (strcmp(request->method, "POST") == 0 && strcmp(request->path, "/cancel-analysis") == 0) {
        handle_cancel_analysis(fd, payload);
    } else if (strcmp(request->method, "POST") == 0 && strcmp(request->path, "/compare-strategies") == 0) {
        handle_compare_strategies(fd, payload);
    } else {
        send_json_error(fd, 404, "Rota nao encontrada");
    }

    cJSON_Delete(payload);
}

static void *handle_connection(void *arg) {
    ConnectionContext *context = arg;
    Request *request = parse_request(context->fd);
    route_request(context->fd, request);
    free_request(request);
    close(context->fd);
    free(context);
    return NULL;
}

static void handle_signal(int signal_number) {
    (void) signal_number;
    server_running = 0;
}

int run_analysis_service(void) {
    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);
    curl_global_init(CURL_GLOBAL_DEFAULT);

    const char *host = getenv("HOST");
    const char *port_env = getenv("PORT");
    const char *log_level_env = getenv("ANALYSIS_LOG_LEVEL");
    int port = port_env ? atoi(port_env) : 5002;
    if (!host || host[0] == '\0') {
        host = "0.0.0.0";
    }
    if (log_level_env && strcasecmp(log_level_env, "DEBUG") == 0) {
        configured_log_level = ANALYSIS_LOG_DEBUG;
    } else if (log_level_env && strcasecmp(log_level_env, "ERROR") == 0) {
        configured_log_level = ANALYSIS_LOG_ERROR;
    } else {
        configured_log_level = ANALYSIS_LOG_INFO;
    }

    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        perror("socket");
        return 1;
    }

    int opt = 1;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    struct sockaddr_in address;
    memset(&address, 0, sizeof(address));
    address.sin_family = AF_INET;
    address.sin_port = htons((uint16_t) port);
    address.sin_addr.s_addr = strcmp(host, "0.0.0.0") == 0 ? INADDR_ANY : inet_addr(host);

    if (bind(server_fd, (struct sockaddr *) &address, sizeof(address)) < 0) {
        perror("bind");
        close(server_fd);
        return 1;
    }
    if (listen(server_fd, 32) < 0) {
        perror("listen");
        close(server_fd);
        return 1;
    }

    analysis_log(ANALYSIS_LOG_INFO, NULL, "analysis_service (C) listening on %s:%d log_level=%s", host, port, log_level_env ? log_level_env : "INFO");

    while (server_running) {
        struct sockaddr_in client_address;
        socklen_t client_length = sizeof(client_address);
        int client_fd = accept(server_fd, (struct sockaddr *) &client_address, &client_length);
        if (client_fd < 0) {
            if (!server_running) {
                break;
            }
            continue;
        }

        ConnectionContext *context = malloc(sizeof(ConnectionContext));
        if (!context) {
            close(client_fd);
            continue;
        }
        context->fd = client_fd;

        pthread_t thread;
        if (pthread_create(&thread, NULL, handle_connection, context) != 0) {
            close(client_fd);
            free(context);
            continue;
        }
        pthread_detach(thread);
    }

    close(server_fd);
    curl_global_cleanup();
    return 0;
}
