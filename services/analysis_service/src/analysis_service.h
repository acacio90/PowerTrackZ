#ifndef ANALYSIS_SERVICE_H
#define ANALYSIS_SERVICE_H

#include <cjson/cJSON.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdarg.h>

#define JOB_ID_SIZE 64

typedef struct {
    char *id;
    char *label;
    char *channel;
    char *bandwidth;
    char *frequency;
    double x;
    double y;
    double raio;
    int locked;
    int *neighbors;
    int neighbor_count;
    int neighbor_capacity;
} Node;

typedef struct {
    int source;
    int target;
    double peso;
} Edge;

typedef struct {
    Node *nodes;
    int node_count;
    int node_capacity;
    Edge *edges;
    int edge_count;
    int edge_capacity;
} Graph;

typedef struct Job {
    char id[JOB_ID_SIZE];
    atomic_int cancelled;
    pthread_t *threads;
    int thread_count;
    struct Job *next;
} Job;

typedef enum {
    ANALYSIS_LOG_ERROR = 0,
    ANALYSIS_LOG_INFO = 1,
    ANALYSIS_LOG_DEBUG = 2
} AnalysisLogLevel;

int run_analysis_service(void);
bool is_cancelled(const Job *job);
AnalysisLogLevel analysis_log_level(void);
void analysis_log(AnalysisLogLevel level, const char *job_id, const char *fmt, ...);

#endif
