# Analysis Service

**English** | [Português](README.pt-BR.md)

C service that builds the conflict graph between access points and suggests the channel and bandwidth configuration of each one.

## Strategies

| Strategy | Description |
|---|---|
| `backtracking` | Exact *branch-and-bound* search. Minimizes the cost of the optimization criterion (section below); by default, in this order, the number of conflicts, the total interference and the inverse of the summed bandwidth. |
| `greedy` | Visits the APs in decreasing order of degree and assigns each one the profile with the lowest incremental cost in the optimization criterion (by default, the lowest local interference). It is also the initial solution of the exact search. |
| `local_search` | Local search on the common metaheuristic base (section below): at each iteration, it changes the profile of a random AP and accepts the change if it does not worsen the solution under the optimization criterion. It does not guarantee the optimum; it is the reference for the metaheuristics. |
| `simulated_annealing` | Simulated Annealing on the common base: accepts worsenings with the Metropolis probability, which decreases with the temperature (section below). It does not guarantee the optimum. |
| `tabu_search` | Tabu Search on the common base: applies the best non-forbidden profile change, even if worse, and forbids undoing it for a while (section below). It does not guarantee the optimum. |
| `genetic` | Genetic Algorithm on the common base: tournament selection, crossover, mutation and elitism (section below). It does not guarantee the optimum. |

## Parameters

Each strategy declares its parameters in `src/strategies/strategy.c`. They are sent in `parameters` in the request body:

| Strategy | Parameter | Type | Default | Range | Description |
|---|---|---|---|---|---|
| `backtracking` | `thread_count` | integer | `1` | 1 to 256 | Number of search *threads*. |
| `backtracking` | `time_limit_seconds` | number | `60` | 0 to 3600 | Maximum search time in each band, in seconds. `0` disables the limit. |
| `local_search` | `seed` | integer, optional | drawn | 0 to 4294967295 | Seed of the random generator. Without a value, the service draws one and returns it in `execution.seed`. |
| `local_search` | `time_limit_seconds` | number | `10` | 0 to 3600 | Maximum search time in each band, in seconds. `0` disables the limit. |
| `local_search` | `max_iterations` | integer | `1000000` | 0 to 10⁹ | Maximum number of iterations in each band. `0` disables the limit. |
| `local_search` | `max_iterations_without_improvement` | integer | `100000` | 0 to 10⁹ | Stops the search in the band after this number of iterations without improving the best solution. `0` disables the criterion. |
| `local_search` | `initial_solution` | choice | `greedy` | `greedy`, `random` | Initial solution: the greedy one or a random profile for each AP. |

The `greedy` strategy has no configurable parameters. The `simulated_annealing`, `tabu_search` and `genetic` parameters are in each one's section. In the metaheuristics, at least one of the three common stopping criteria must be active; with all three disabled, the request is rejected with HTTP 400.

`GET /strategies` describes these parameters in `strategy_details`, with name, label, type (`integer`, `number` or `choice`), default, limits, unit, whether the value `0` disables the feature, whether it is advanced (`advanced`, shown collapsed in the interface) and whether it is optional (`optional`, with no default: `default` is null, and `optional_label` tells what happens without a value, such as `Sorteada` or `Estimada`). Choice parameters (`choice`) list their options in `options` (`value` and `label`) and the default option in `default`, without `min` and `max`. Each strategy also declares its family (`family`: `exact`, `constructive` or `metaheuristic`). The interface builds its fields and groups the strategies from this description, so a new parameter or strategy only needs to be declared in the service.

Values outside the declared type or range, and options that are not in the list, are rejected with HTTP 400 and a message such as `O parâmetro time_limit_seconds deve estar entre 0 e 3600.`. Parameters not declared by the strategy are ignored. The values actually used appear in `execution.parameters`; the number of *threads* is limited to the number of APs in the graph, and the seed is the one used (given or drawn).

The response reports in `execution.search` whether the solution is optimal (`optimal`), the reason the search stopped, the explored nodes, the conflicts of the initial and final solutions (`greedy_conflicts` and `conflicts`) and the components of the solution cost (`interference_score`, `bandwidth_score` and `power_score_w`). The stop reasons are `completed` (the search finished), `no_improvement` (iterations without improvement), `min_temperature` (Simulated Annealing's minimum temperature), `iteration_limit` (iteration limit), `time_limit` (time limit) and `cancelled` (cancellation); when the bands are consolidated, the reason with the highest precedence wins, in this same order. In the metaheuristics, `iterations` reports the iterations run, `nodes_explored` equals them and `greedy_conflicts` are the conflicts of the initial solution, which may be the random one.

## Optimization Criterion

The strategies compare solutions by a lexicographic order, chosen in the request's `objective` field:

| `objective` | Order |
|---|---|
| `default` | fewer conflicts → lower interference → larger summed bandwidth |
| `energy_tiebreak` | fewer conflicts → lower interference → lower power |
| `energy_first` | lower power → fewer conflicts → lower interference |

Without the field, `default` applies, which reproduces the results of previous versions; an unknown name is rejected with HTTP 400. `GET /strategies` lists the objectives in `objectives` (name, label, description and order) and the default in `default_objective`, and the analysis response reports the objective used in `execution.objective`.

The cost evaluation lives in a single place, `src/strategies/objective.c`: the cost of an assignment (`AssignmentCost`), the comparison in each order (`compare_assignment_costs`) and the power used by the criterion. Greedy picks, AP by AP, the profile with the lowest incremental cost in the objective, and backtracking visits the profiles in that same order. Backtracking pruning uses an optimistic bound of the branch: conflicts and interference only grow, the bandwidth adds at most the largest possible bandwidth of the remaining APs and the power adds at least their lowest possible power. Since every solution in the branch is, in each component, equal to or worse than this bound, pruning is correct in any order. Power enters the cost as integer milliwatts, so sums made by different *threads* give the same value and the result does not depend on the number of *threads*.

In the consumption model, wider bandwidths use less power. That is why `energy_tiebreak` usually matches `default` for an isolated AP, but differs on sums: two conflict-free APs at 40 + 40 MHz add up to 80 MHz and 20.6 W; at 80 + 20 MHz, 100 MHz and 21.0 W. `default` keeps the second solution and `energy_tiebreak` the first. `energy_first` accepts conflicts to reduce power.

**Configurations outside the consumption model.** In the optimization criterion, a configuration with no value in the model (160 MHz) counts as the highest modeled power of its band (11.1 W in 5 GHz), so a configuration without an estimate is never favored by energy. In a band with no value in the model (6 GHz), every profile counts as zero, and energy no longer tells them apart. The rule applies only to the optimization: the power totals in the response still leave these configurations out.

## Common Metaheuristic Base

The metaheuristics share the same pieces, in `src/strategies/metaheuristic.c`, so that the comparison with backtracking and greedy depends only on the method, not on implementation differences. Local search (`local_search.c`) is the reference that exercises this base.

- **Representation.** The solution is one profile index per AP, as in backtracking. In each band, only the APs that are not fixed and have profiles of their band change; the APs locked on an available profile stay fixed, with the same rules as backtracking (`assignment.c`).
- **Cost.** The cost is the optimization criterion's (`AssignmentCost` and `compare_assignment_costs`, in `objective.c`), with the same rules as the incremental cost of backtracking and greedy: it counts the conflicting edges with both ends defined, except between two fixed APs, and adds the bandwidth and power of each assigned AP. `meta_full_cost` recomputes the full cost, and `meta_move_delta` computes the change when the profile of one AP changes, in O(degree). Since interference is a real number, the incremental sum may accumulate rounding error over millions of moves; therefore, the current cost is fully recomputed every 4,096 iterations, and a solution only becomes the best one after its cost is recomputed. The C tests check that the incremental change matches the full recomputation over 20,000 random moves, in the three objectives.
- **Neighborhood.** The basic move is changing the profile of one AP; `meta_random_move` draws a mobile AP and an allowed profile different from the current one.
- **Initial solution.** The greedy one (`greedy`, default) or a random allowed profile for each AP (`random`).
- **Stopping.** The search stops at the time limit, at the maximum number of iterations or after a number of iterations without improving the best solution, whichever comes first, and reports the reason in `stop_reason`. Each band has its own limits.
- **Reproducibility.** Randomness comes from the service's own generator (xoshiro256\*\*, seeded by splitmix64), not from the C library's `rand()`. The seed is the one given in `seed` or a drawn one, returned in `execution.seed` and in `execution.parameters.seed`; each band uses a sequence derived from the seed and the band index. The same seed, with the same APs, channels, objective and parameters, produces the same result. The time limit is the exception: a search that stops on time depends on the speed of the machine, so, to reproduce a run, use the iteration limit or the iterations-without-improvement limit.
- **Convergence curve.** Each band in `execution.bands` reports in `convergence` the best solution along the search: one point at the initial solution, one at each improvement and one at the end, with `iteration`, `time_ms`, `conflicts`, `interference`, `bandwidth` and `power_w`. The curve keeps at most 500 points per band; when it fills up, every other point is dropped, keeping the first one.
- **Progress and cancellation.** On the *streaming* route, progress (`iteration`, `best_conflicts` and the completed fraction, that of the most advanced stopping criterion) is sent every 0.2 s, and cancellation is checked every 256 iterations.

To create a metaheuristic, declare the common parameters with the macros `META_SEED_PARAMETER`, `META_TIME_LIMIT_PARAMETER`, `META_MAX_ITERATIONS_PARAMETER`, `META_STAGNATION_PARAMETER` and `META_INITIAL_SOLUTION_PARAMETER`, use `meta_validate_parameters` for validation and follow the loop in `local_search.c`: `meta_run_begin`, `meta_run_next` at each iteration, `meta_run_offer` when the current solution changes and `meta_run_end` at the end. Comparisons use the objective's lexicographic order (`compare_assignment_costs`); a metaheuristic that needs a numeric cost difference (such as Simulated Annealing's acceptance) must document how it obtains one without violating that order.

## Simulated Annealing

The `simulated_annealing` strategy (`src/strategies/simulated_annealing.c`) starts from the initial solution and, at each iteration, draws a neighbor. A neighbor that does not worsen the current solution is always accepted; one that worsens it is accepted with the Metropolis probability, exp(−Δ/T), which decreases with the temperature T. The solution returned is the best one found, even if the current one is worse at the end.

**Lexicographic cost difference.** The cost has several components compared in order (Optimization Criterion section), and Metropolis needs a number. Δ is the worsening in the component that decides the comparison, that is, the first one, in the objective's order, in which the neighbor and the current solution differ, divided by that component's scale. This way, the order of the criteria is respected: in the default objective, a neighbor with one more conflict is judged by the worsening in conflicts, however large the improvement in interference, and interference only weighs between solutions with the same conflicts. The scale of each component is the mean of the nonzero changes of that component in a sample of 200 neighbors of the initial solution; it makes the components comparable and makes T dimensionless. A weighted sum of the components, with large weights for the first ones, was discarded: it only respects the order if the weights dominate any change of the following components, which depends on the instance.

**Temperature.** Without `initial_temperature`, the initial temperature is estimated on the same sample, to accept 80% of the worsenings on average: T₀ = −mean(Δ) / ln 0.8. Every `iterations_per_temperature` iterations, the temperature drops: in geometric cooling (`geometric`, default), T ← T · `cooling_rate`; in linear cooling (`linear`), T ← T − T₀ · (1 − `cooling_rate`). The search in the band stops when T falls below `min_temperature` (reason `min_temperature`) or by one of the common criteria.

Each band in `execution.bands` reports in `search`: `initial_temperature` and `initial_temperature_estimated` (whether it was estimated), `final_temperature`, `temperature_levels` (temperature levels visited) and `accepted_worse` (worsenings accepted).

| Parameter | Type | Default | Range | Description |
|---|---|---|---|---|
| `initial_temperature` | number, optional | estimated | 0.0001 to 10⁶ | Initial temperature. |
| `cooling_schedule` | choice | `geometric` | `geometric`, `linear` | Cooling schedule. |
| `cooling_rate` | number | `0.95` | 0.5 to 0.9999 | Cooling rate. |
| `iterations_per_temperature` | integer | `1000` | 1 to 10⁷ | Iterations at each temperature level. |
| `min_temperature` | number | `0.001` | 0 to 10⁶ | Temperature at which the search stops; `0` disables the criterion (in linear cooling, the search stops when T reaches zero). |

Besides these, SA accepts the metaheuristics' common parameters (`seed`, `time_limit_seconds`, `max_iterations`, `max_iterations_without_improvement` and `initial_solution`). A minimum temperature equal to or above the given initial one is rejected with HTTP 400.

## Tabu Search

The `tabu_search` strategy (`src/strategies/tabu_search.c`) moves the current solution, at each iteration, to the best admissible neighbor, even if it is worse, and returns the best solution found.

- **Candidates.** At each iteration, `candidate_nodes` APs are drawn, and all their profile changes are evaluated with the common base's incremental cost. Each AP is drawn among the mobile APs in conflict with probability 0.8 (when there is any) and, otherwise, among all mobile APs, so that the search also changes APs without conflict, in which interference, bandwidth and power can still improve. The APs in conflict are tracked at each move, in O(degree) (`MetaConflictSet`, in the common base).
- **Tabu list.** When the profile of an AP changes, returning that AP to the profile it left is forbidden for `tabu_tenure` iterations. The forbidden attribute is the pair (AP, profile left), not the whole move, which prevents undoing the change without preventing other changes of the same AP.
- **Aspiration.** A forbidden move is accepted if it leads to a solution better than the best one found so far.
- **No admissible move.** If every candidate is forbidden and none meets the aspiration criterion, the iteration passes without a move (`blocked_iterations`).

Each band in `execution.bands` reports in `search`: `evaluated_moves` (moves evaluated), `tabu_rejections` (candidates discarded for being forbidden), `aspirations` (forbidden moves accepted by aspiration), `worsening_moves` (applied moves that worsened the current solution) and `blocked_iterations`.

| Parameter | Type | Default | Range | Description |
|---|---|---|---|---|
| `tabu_tenure` | integer | `10` | 1 to 100,000 | Iterations during which an AP is forbidden from returning to the profile it left. |
| `candidate_nodes` | integer | `20` | 1 to 10,000 | APs drawn at each iteration, all of whose profile changes are evaluated. |

Besides these, Tabu Search accepts the metaheuristics' common parameters. Each iteration evaluates dozens of moves, so, with the defaults, the search usually stops at the time limit.

## Genetic Algorithm

The `genetic` strategy (`src/strategies/genetic.c`) evolves a population of solutions. Each individual is a solution of the common base (one profile per AP), and the fitness is the cost of the optimization criterion, compared by the objective's lexicographic order, without turning the components into a number. In the common base, each iteration is a generation: `generations` is the iteration limit, and `max_iterations_without_improvement` counts generations.

- **Initial population.** The greedy solution, mutated copies of it (up to the fraction `greedy_fraction` of the population, so they are not identical) and, for the rest, random solutions.
- **Selection.** By tournament: draws `tournament_size` individuals, with replacement, and the best one wins. Tournament was chosen because it only uses comparisons between costs, which preserves the lexicographic order; roulette would require a numeric fitness.
- **Crossover.** With probability `crossover_rate`, the child comes from crossing two parents; otherwise, it copies the first one. In uniform crossover (`uniform`, default), each AP inherits the profile of one of the parents, at random; in one-point crossover (`one_point`), the APs before a cut, in graph order, come from the first parent, and the others from the second. Uniform is the default because the order of the APs in the graph does not reflect the neighborhood between them, and one-point splits neighboring APs at random.
- **Mutation.** Each mobile AP of the child changes, with probability `mutation_rate`, to another allowed profile of its band.
- **Elitism.** The `elitism` best individuals pass unchanged to the next generation; with an elite, the best fitness of a generation never gets worse.
- **Locked APs.** They are the same in every individual: both parents have the same profile on them, and mutation only changes mobile APs.

The best solution found is returned. Each band in `execution.bands` reports in `search`: `population_size`, `evaluations` (solutions evaluated, the initial population plus each generation's children) and `generation_best_worsened` (generations in which the population's best got worse than the previous one's; zero with an elite).

| Parameter | Type | Default | Range | Description |
|---|---|---|---|---|
| `population_size` | integer | `50` | 4 to 10,000 | Individuals in each generation. |
| `generations` | integer | `1000` | 0 to 10⁷ | Maximum number of generations in each band; `0` disables the limit. |
| `max_iterations_without_improvement` | integer | `200` | 0 to 10⁷ | Generations without improving the best solution; `0` disables the criterion. |
| `greedy_fraction` | number | `0.1` | 0 to 1 | Fraction of the initial population derived from greedy. |
| `crossover` | choice | `uniform` | `uniform`, `one_point` | Crossover type. |
| `crossover_rate` | number | `0.9` | 0 to 1 | Crossover probability. |
| `mutation_rate` | number | `0.02` | 0 to 1 | Mutation probability of each AP. |
| `tournament_size` | integer | `3` | 1 to 10,000 | Individuals per tournament; cannot exceed the population. |
| `elitism` | integer | `2` | 0 to 9,999 | Elite individuals; must be smaller than the population. |

Besides these, the GA accepts the seed (`seed`) and the time limit (`time_limit_seconds`); at least one of the stopping criteria (time, generations or generations without improvement) must be active.

## Interference

The interference between two APs is the product of the spatial overlap of their coverage areas (w, as a percentage of the smaller area) and the spectral overlap of their channels (s, from 0 to 1); there is a conflict when the product is greater than zero. The factor s is the fraction of the narrower channel's width that overlaps the other one, with each channel occupying its width around its center frequency.

For bonded channels, the center frequency is that of the whole block, not that of the primary channel: 36 at 80 MHz occupies channels 36 to 48, centered on channel 42 (5210 MHz); 44 at 40 MHz occupies 44 and 48, centered on 46 (5230 MHz). In 2.4 GHz, the secondary of a 40 MHz channel is 4 channels above the primary when it fits in the band (primaries 1 to 9) and 4 channels below otherwise; so 1 at 40 MHz is centered on channel 3 (2422 MHz) and 11 at 40 MHz on channel 9 (2452 MHz).

## Energy Consumption

The power of each AP follows the Dembélé et al. (2023) model: the average power of an AP transmitting at 25 Mbps, by band and bandwidth. The values are in `POWER_MODEL`, in `src/strategies/objective.c`, and are used both in the response totals and in the optimization criterion:

| Band | 20 MHz | 40 MHz | 80 MHz |
|---|---|---|---|
| 2.4 GHz | 14.5 W | 13.8 W | — |
| 5 GHz | 11.1 W | 10.3 W | 9.9 W |

Configurations outside the table (160 MHz and 6 GHz) have no value in the model and are left out of the sums. Each node in `graph_data.nodes` has `power_w` (current configuration) and `proposed_power_w` (proposed configuration), null outside the model; `graph_data` has `power_w`, the total of the displayed configuration, and `power_unmodeled_nodes`. In `execution.comparison` and in each band of `execution.bands`, `power_before_w` and `power_after_w` give the total before and after the optimization, and `power_unmodeled_before` and `power_unmodeled_after`, the APs outside the model. The conversion into energy and cost for the chosen period is done by the interface.

## Per-Band Graph and Available Channels

The coverage radius of each AP comes from the `raio` field (in meters); without it, the band's default applies: 20 m in 2.4 GHz, 15 m in 5 GHz and 12 m in 6 GHz, the same values as the interface and the generator. `POST /graph-metrics` returns the metrics of this graph (nodes, edges, density, average degree and maximum degree, in total and per band) without running a strategy.

APs in different bands do not interfere (s = 0), so the graph has no edges between bands: it is the union of the 2.4, 5 and 6 GHz graphs. The analysis routes solve each band separately, in sequence, each with its own time limit. APs in an unknown band are left out of the search and keep their configuration.

The `channels` field of the request sets the profiles (the k of each graph) in the same format as `profiles` in `GET /channel-plan`, for example `{"2.4 GHz": {"20 MHz": ["1", "6", "11"]}}`. Each combination is validated against `valid`, and a band that is given needs at least one channel; otherwise, the response is HTTP 400. Bands that are not given use the default profiles.

The response has one entry per band in `execution.bands`, with `frequency`, `nodes`, `edges`, `density`, `profile_count`, `comparison` and `search`. The `execution.search` and `execution.comparison` fields consolidate the bands: conflicts, interference, bandwidth and explored nodes are added up, and the solution is only optimal if every band's is. In `comparison`, `conflicts_before` and `conflicts_after` count the edges in conflict (w·s > 0) in the current and in the proposed configuration, `conflict_density_before` and `conflict_density_after` give the fraction of the possible pairs of APs in conflict, `interference_before` and `interference_after`, the sum of w·s over those edges, and `changed_nodes`, how many APs had their configuration changed; `edges`, in turn, counts every coverage overlap, with or without conflict.

## Channel Plan

`GET /channel-plan` reports the channels offered by the interface, grouped by frequency and bandwidth:

- `valid`: every channel allowed in Brazil. In 2.4 GHz, channels 1 to 13, at 20 and 40 MHz (any channel can be the primary of a 40 MHz channel). In 5 GHz (36 to 64, 100 to 144 and 149 to 165) and in 6 GHz (1 to 233), the 40, 80 and 160 MHz channels bond aligned blocks of 2, 4 and 8 channels, and a channel only appears at a width when the whole block exists. The segments are in `CHANNEL_SEGMENTS`, in `src/analysis_service.c`.
- `profiles`: the default profiles of the strategies, used for the bands the request does not give in `channels`, read from `CONFIG_PROFILES`, in `src/strategies/backtracking.c`.
- `options`: the options for choosing the search profiles, one per distinct position in the spectrum, with the channels it occupies (`channels`), the primary sent in the request's `channels` (`channel`) and the range it occupies in the spectrum (`lower_mhz` and `upper_mhz`), used by the interface's spectrum map. In 5 and 6 GHz, each bonded block is one option (at 80 MHz in 5 GHz, 36–48, 52–64, 100–112, 116–128, 132–144 and 149–161); in 2.4 GHz, each 20 MHz channel and each 40 MHz pair, from 1+5 to 9+13. The primary is the default profile's when it falls in the block (the 7+11 pair sends 11) and otherwise the block's first channel.

## Default Profiles

The default profiles (`CONFIG_PROFILES`, in `src/strategies/backtracking.c`) are used in the bands the request does not give in `channels`:

| Band | 20 MHz | 40 MHz | 80 MHz | k |
|---|---|---|---|---|
| 2.4 GHz | 1, 6, 11 | 1 (1+5), 11 (7+11) | — | 5 |
| 5 GHz | 36, 44, 149, 157 | 36, 44, 149, 157 | 36, 149 | 10 |

The order of the list breaks ties between profiles of the same cost and is fixed, so the result is deterministic.

**The 40 MHz profiles in 2.4 GHz overlap.** 1+5 occupies 2402–2442 MHz and 7+11 occupies 2432–2472 MHz: they share 10 MHz (s = 0.25), and two neighboring APs with these profiles conflict, with interference equal to 25% of the spatial overlap. The decision (#78) was to keep them and document the overlap, instead of replacing them with 1+5 and 9+13 (the only non-overlapping pair) or removing 40 MHz from the defaults:

- default results and the scalability test history remain comparable with previous versions;
- channels 12 and 13, needed for 9+13, are allowed in Brazil, but not every client supports them;
- 40 MHz stays in the search space, which matters for the optimization criterion: in the consumption model, 40 MHz uses less power than 20 MHz, and removing it would take that trade-off out of the energy analysis;
- the overlap is not ignored: it counts as interference, and the search only uses both pairs on neighboring APs when that pays off in the chosen criterion.

For an experiment without this overlap, choose the channels in `channels` (for example, `{"2.4 GHz": {"40 MHz": ["1", "9"]}}`, the 1+5 and 9+13 pairs) or, in the interface, use the 40 MHz **Sem sobreposição** shortcut on the spectrum map, which already marks overlapping bars in orange.

## Parallelism

The search starts from the greedy solution, which serves as the bound for pruning. The first two free levels of the tree are expanded into tasks, consumed by *pthreads* from a shared queue. The best solution is shared between the *threads* under a *mutex*, and each *thread* keeps a local copy updated through a version counter, which avoids locking the *mutex* at every node.

On a cost tie, the task with the lowest index wins. Since the tasks follow the order of the sequential search, the result is the same for any number of *threads*.

## Limitations

- The problem is NP-hard. On large and dense graphs, the exact search does not finish and stops at the time limit, returning the best solution found (`optimal: false`).
- The gain from more *threads* depends on the number of tasks and on how effective the pruning is. With few profiles per band, the first two levels produce at most 25 tasks in 2.4 GHz and 100 in 5 GHz.
- In backtracking, the progress sent to the *frontend* is the fraction of completed tasks, not an estimate of the remaining time.
- The metaheuristics are not part of the scalability test yet: the break point of methods without an optimality guarantee (time limit exceeded) does not describe a search that stops on time, and the comparison needs repetitions per seed.
- Conflicts between two locked APs are not counted in the cost, since they do not depend on the assignment.
