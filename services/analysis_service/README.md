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
| `backtracking` | `time_limit_seconds` | number | `60` | 0 to 3600 | Maximum search time in each band, in seconds. `0` disables the limit. |

The `greedy` and `genetic` strategies have no configurable parameters.

`GET /strategies` describes these parameters in `strategy_details`, with name, label, type, default, limits, unit and whether the value `0` disables the feature. The interface builds its fields from this description, so a new parameter only needs to be declared in the service.

Values outside the declared type or range are rejected with HTTP 400 and a message such as `Parametro time_limit_seconds deve estar entre 0 e 3600`. Parameters not declared by the strategy are ignored. The values actually used appear in `execution.parameters`; the number of *threads* is limited to the number of APs in the graph.

The response reports in `execution.search` whether the solution is optimal (`optimal`), the reason the search stopped (`completed`, `time_limit` or `cancelled`), the explored nodes and the conflicts of the greedy and final solutions.

## Interference

The interference between two APs is the product of the spatial overlap of their coverage areas (w, as a percentage of the smaller area) and the spectral overlap of their channels (s, from 0 to 1); there is a conflict when the product is greater than zero. The factor s is the fraction of the narrower channel's width that overlaps the other one, with each channel occupying its width around its center frequency.

For bonded channels, the center frequency is that of the whole block, not that of the primary channel: 36 at 80 MHz occupies channels 36 to 48, centered on channel 42 (5210 MHz); 44 at 40 MHz occupies 44 and 48, centered on 46 (5230 MHz). In 2.4 GHz, the secondary of a 40 MHz channel is 4 channels above the primary when it fits in the band (primaries 1 to 9) and 4 channels below otherwise; so 1 at 40 MHz is centered on channel 3 (2422 MHz) and 11 at 40 MHz on channel 9 (2452 MHz).

## Per-Band Graph and Available Channels

APs in different bands do not interfere (s = 0), so the graph has no edges between bands: it is the union of the 2.4, 5 and 6 GHz graphs. The analysis routes solve each band separately, in sequence, each with its own time limit. APs in an unknown band are left out of the search and keep their configuration.

The `channels` field of the request sets the profiles (the k of each graph) in the same format as `profiles` in `GET /channel-plan`, for example `{"2.4 GHz": {"20 MHz": ["1", "6", "11"]}}`. Each combination is validated against `valid`, and a band that is given needs at least one channel; otherwise, the response is HTTP 400. Bands that are not given use the default profiles.

The response has one entry per band in `execution.bands`, with `frequency`, `nodes`, `edges`, `density`, `profile_count`, `comparison` and `search`. The `execution.search` and `execution.comparison` fields consolidate the bands: conflicts, interference, bandwidth and explored nodes are added up, and the solution is only optimal if every band's is.

## Channel Plan

`GET /channel-plan` reports the channels offered by the interface, grouped by frequency and bandwidth:

- `valid`: every channel allowed in Brazil. In 2.4 GHz, channels 1 to 13, at 20 and 40 MHz (any channel can be the primary of a 40 MHz channel). In 5 GHz (36 to 64, 100 to 144 and 149 to 165) and in 6 GHz (1 to 233), the 40, 80 and 160 MHz channels bond aligned blocks of 2, 4 and 8 channels, and a channel only appears at a width when the whole block exists. The segments are in `CHANNEL_SEGMENTS`, in `src/analysis_service.c`.
- `profiles`: the default profiles of the strategies, used for the bands the request does not give in `channels`, read from `CONFIG_PROFILES`, in `src/strategies/backtracking.c`.

## Parallelism

The search starts from the greedy solution, which serves as the bound for pruning. The first two free levels of the tree are expanded into tasks, consumed by *pthreads* from a shared queue. The best solution is shared between the *threads* under a *mutex*, and each *thread* keeps a local copy updated through a version counter, which avoids locking the *mutex* at every node.

On a cost tie, the task with the lowest index wins. Since the tasks follow the order of the sequential search, the result is the same for any number of *threads*.

## Limitations

- The problem is NP-hard. On large and dense graphs, the exact search does not finish and stops at the time limit, returning the best solution found (`optimal: false`).
- The gain from more *threads* depends on the number of tasks and on how effective the pruning is. With few profiles per band, the first two levels produce at most 25 tasks in 2.4 GHz and 100 in 5 GHz.
- The progress sent to the *frontend* is the fraction of completed tasks, not an estimate of the remaining time.
- Conflicts between two locked APs are not counted in the cost, since they do not depend on the assignment.
