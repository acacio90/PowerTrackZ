# Analysis Service

**English** | [Português](README.pt-BR.md)

C service that builds the collision graph between access points and suggests the channel and bandwidth configuration of each one.

## Strategies

| Strategy | Description |
|---|---|
| `backtracking` | Exact *branch-and-bound* search. Minimizes, in this order, the number of conflicts, the total interference and the inverse of the summed bandwidth. |
| `greedy` | Visits the APs in decreasing order of degree and assigns each one the profile with the lowest local interference. It is also the initial solution of the exact search. |
| `genetic` | Not implemented yet (returns a *placeholder*). |

## Parameters

Each strategy declares its parameters in `src/strategies/strategy.c`. They are sent in `parameters` in the request body:

| Strategy | Parameter | Type | Default | Range | Description |
|---|---|---|---|---|---|
| `backtracking` | `thread_count` | integer | `1` | 1 to 256 | Number of search *threads*. |
| `backtracking` | `time_limit_seconds` | number | `60` | 0 to 3600 | Maximum search time, in seconds. `0` disables the limit. |

The `greedy` and `genetic` strategies have no configurable parameters.

`GET /strategies` describes these parameters in `strategy_details`, with name, label, type, default, limits, unit and whether the value `0` disables the feature. The interface builds its fields from this description, so a new parameter only needs to be declared in the service.

Values outside the declared type or range are rejected with HTTP 400 and a message such as `Parametro time_limit_seconds deve estar entre 0 e 3600`. Parameters not declared by the strategy are ignored. The values actually used appear in `execution.parameters`; the number of *threads* is limited to the number of APs in the graph.

The response reports in `execution.search` whether the solution is optimal (`optimal`), the reason the search stopped (`completed`, `time_limit` or `cancelled`), the explored nodes and the conflicts of the greedy and final solutions.

## Parallelism

The search starts from the greedy solution, which serves as the bound for pruning. The first two free levels of the tree are expanded into tasks, consumed by *pthreads* from a shared queue. The best solution is shared between the *threads* under a *mutex*, and each *thread* keeps a local copy updated through a version counter, which avoids locking the *mutex* at every node.

On a cost tie, the task with the lowest index wins. Since the tasks follow the order of the sequential search, the result is the same for any number of *threads*.

## Limitations

- The problem is NP-hard. On large and dense graphs, the exact search does not finish and stops at the time limit, returning the best solution found (`optimal: false`).
- The gain from more *threads* depends on the number of tasks and on how effective the pruning is. With few profiles per band, the first two levels produce at most 36 tasks in 2.4 GHz and 100 in 5 GHz.
- The progress sent to the *frontend* is the fraction of completed tasks, not an estimate of the remaining time.
- Conflicts between two locked APs are not counted in the cost, since they do not depend on the assignment.
