# Processing Energy of the Strategies

**English** | [Português](README.pt-BR.md)

PowerTrackZ estimates the energy consumed by the access points with the proposed configuration, but not the energy spent to compute that configuration. This document records the investigation of #87: the measurement options, the feasibility of each one in the project environment, the chosen method and the results of a prototype.

## Environment

The measurements were made on the development machine, on 2026-10-01:

- Dell OptiPlex SFF Plus 7020 (desktop, no battery), with an Intel Core i7-14700: 20 cores (8 performance and 12 efficiency), 28 threads, processor base power (PBP) of 65 W and maximum turbo power (MTP) of 219 W;
- Windows, with the services in Docker containers on WSL2 (kernel `6.6.87.2-microsoft-standard-WSL2`);
- analysis_service runs in its own container, with no CPU limit (`cpu.max` = `max`).

## Options Evaluated

| Option | Accuracy | Requirements | Limitations | Feasible in the environment? |
|---|---|---|---|---|
| RAPL through `powercap` (`/sys/class/powercap/intel-rapl`) | Good for the processor package (Khan et al., 2018), with a granularity of about 1 ms | Linux with direct access to the processor | Measures the whole processor, not the process; needs an idle baseline | **No**: the directory does not exist in WSL2, not even in a privileged container |
| RAPL through `perf` (`power` PMU, events `energy-pkg`, `energy-cores`...) | Same as above | Linux, permissive `perf_event_paranoid`, privileged container | Same as above | **No**: the `power` PMU exists in the WSL2 kernel, but without events, and opening `energy-pkg`, `energy-cores`, `energy-ram`, `energy-gpu` or `energy-psys` through the `perf_event_open` call returns `EINVAL` |
| RAPL on Windows through a tool (LibreHardwareMonitor, HWiNFO, Intel PCM) | Good for the package, with sampling of about 1 s in the monitoring tools | Installing the tool and a kernel driver, as administrator | Measures the whole machine, including Windows and the WSL2 VM; needs a baseline and runs that are long compared to the sampling; depends on the host and does not fit into PowerTrackZ | **Possible, not verified**: no tool is installed, and the project terminal does not run as administrator. Intel Power Gadget has been discontinued |
| Windows energy counters ("Energy Meter" and "Power Meter" counter sets) | Varies | Firmware that exposes them | Only available on some hardware | **No**: neither counter set exists on this machine |
| Windows per-process estimate (Energy Estimation Engine, `powercfg /srumutil`) | Low: hourly aggregated model | Administrator; aimed at battery-powered devices | Does not separate one run from another | **Not suitable** for per-run measurement |
| External wall-power meter | Good for the whole machine | Measuring equipment | Measures everything the machine consumes; needs a baseline and long runs; cannot be automated in the project | **Possible, not verified**: depends on equipment |
| **CPU time × power per core** | Estimate: assumes constant power per busy core | CPU accounting of the process or container | Does not capture frequency, turbo, the difference between performance and efficiency cores, memory or idle consumption | **Yes**: the container cgroup (`cpu.stat`, `usage_usec`) is accessible, and the process itself can measure the CPU time of its threads |

## Chosen Method

**Estimated energy = CPU time of the analysis × power per core.**

- The CPU time comes from the operating system's accounting: in the prototype, the change in `usage_usec` in the analysis_service container cgroup during the analysis, with the service idle; in an integration, the CPU time of the analysis's own threads, measured by the service.
- The power per core is a configurable coefficient. The default is the base power divided by the cores (65 W / 20 = 3.25 W), as in the Green Algorithms calculator (Lannelongue, Grealey and Inouye, 2021), which estimates energy from the run time, the cores used and the processor's power per core. The upper bound uses the maximum turbo power (219 W / 20 = 10.95 W). The CodeCarbon library falls back to the same estimate from the nominal power when RAPL is not available.

**Justification.**

1. It is the only method feasible inside the project environment, with no kernel driver or equipment.
2. It is applied in the same way to every strategy: it does not depend on how each one is implemented, only on the CPU time it consumes, including with several threads (backtracking with 4 threads spends 4 seconds of CPU per second).
3. It is reproducible on any machine: the CPU time is measured, and the power per core is a parameter declared in the results.
4. To compare strategies, what matters is the ratio between them, which does not depend on the coefficient. The absolute value is an estimate and should be presented as a range (base to turbo power) or with the coefficient stated.

**What the estimate does not capture:** frequency changes and turbo, the difference between performance and efficiency cores (the Windows and WSL2 scheduler picks the cores), memory energy and the machine's idle consumption. Therefore, it measures the energy attributable to the strategy's processing, not the machine's total consumption.

**Future work: calibration with real measurement.** With a RAPL tool on Windows or a wall-power meter, the estimate can be calibrated: measure the machine at idle and during long runs of the same strategy, subtract the baseline and compare with the run's CPU time. This calibration would replace the default coefficient with one measured on this machine.

## Prototype

The script [`scripts/experiments/processing_energy.py`](../../scripts/experiments/processing_energy.py) generates a topology from the seed, runs each strategy a few times on it, one at a time, and measures the CPU time through the container cgroup, discounting the cost of the reading itself (`docker exec` runs inside the container; about 12 ms of CPU per reading).

```bash
docker compose up -d
python scripts/experiments/processing_energy.py --nodes 100 --repetitions 3
```

Result with 100 APs (seed 2026, minimum degree 3), mean of 3 repetitions:

| Strategy | Time (s) | CPU (s) | Cores | Energy (J), base to turbo | Conflicts |
|---|---|---|---|---|---|
| Greedy | 0.022 | 0.005 | 0.24 | 0.02 to 0.06 | 211 |
| Backtracking, 1 thread, 10 s limit | 20.9 | 20.9 | 1.00 | 68 to 229 | 201 |
| Backtracking, 4 threads, 10 s limit | 20.9 | 83.6 | 4.00 | 272 to 916 | 158 |
| Local search, 200 thousand iterations | 0.85 | 0.85 | 1.00 | 2.8 to 9.3 | 94 |
| Simulated Annealing, 200 thousand iterations | 1.39 | 1.39 | 1.00 | 4.5 to 15.2 | 77 |

Backtracking stopped at the time limit in both bands (10 s each), so it spends CPU time proportional to the limit and to the number of threads: with 4 threads, the same wall-clock time costs four times more energy. On this instance, the metaheuristics reached fewer conflicts with a fraction of the energy of the interrupted backtracking. In greedy, the CPU time (5 ms) is of the order of the reading variation (about 2 ms), so very short runs need repetitions.

## Integration into PowerTrackZ

The integration is feasible with no new dependencies: analysis_service would measure the CPU time of each analysis (adding up that of the threads that run it, so as not to mix simultaneous analyses) and report it in the response, per band and in total, together with the energy estimated with the configured coefficient. The scalability test and the strategy comparison would start recording these values. The proposal is described in #124.

## References

- KHAN, K. N.; HIRKI, M.; NIEMI, T.; NURMINEN, J. K.; OU, Z. RAPL in Action: Experiences in Using RAPL for Power Measurements. *ACM Transactions on Modeling and Performance Evaluation of Computing Systems*, v. 3, n. 2, 2018.
- LANNELONGUE, L.; GREALEY, J.; INOUYE, M. Green Algorithms: Quantifying the Carbon Footprint of Computation. *Advanced Science*, v. 8, n. 12, 2021.
- CodeCarbon. Documentation of the processor energy estimation method. Available at: https://mlco2.github.io/codecarbon/.
