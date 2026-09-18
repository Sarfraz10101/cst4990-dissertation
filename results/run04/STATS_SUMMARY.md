# Statistical summary

Source: `C:/Users/abdul/CST4990-dissertation/data/run04_reactive_samecore.csv`
Bootstrap resamples: 2000. Permutations: 10000. Confidence level: 95%.
Chance baseline: 0.25 (4 balanced classes).

## RQ1 - attacker classification accuracy

| model        | condition   |    n |   balanced_accuracy |   ci95_low |   ci95_high |   chance | above_chance   |   p_vs_chance | p_reported   |
|:-------------|:------------|-----:|--------------------:|-----------:|------------:|---------:|:---------------|--------------:|:-------------|
| logreg       | noise_off   | 1000 |               0.857 |     0.8359 |      0.8774 |     0.25 | True           |     9.999e-05 | < 1.0e-04    |
| logreg       | noise_on    | 1000 |               0.858 |     0.8358 |      0.8779 |     0.25 | True           |     9.999e-05 | < 1.0e-04    |
| randomforest | noise_off   | 1000 |               0.906 |     0.8883 |      0.9238 |     0.25 | True           |     9.999e-05 | < 1.0e-04    |
| randomforest | noise_on    | 1000 |               0.904 |     0.8863 |      0.9219 |     0.25 | True           |     9.999e-05 | < 1.0e-04    |

### Reduction achieved by the defence

| model        |   accuracy_noise_off |   accuracy_noise_on |   reduction_pp |   reduction_ci95_low_pp |   reduction_ci95_high_pp | undefended_above_chance   |   pct_of_leak_removed | significant   |
|:-------------|---------------------:|--------------------:|---------------:|------------------------:|-------------------------:|:--------------------------|----------------------:|:--------------|
| logreg       |                0.857 |               0.858 |           -0.1 |                   -3.13 |                     2.79 | True                      |                 -0.16 | False         |
| randomforest |                0.906 |               0.904 |            0.2 |                   -2.08 |                     2.59 | True                      |                  0.3  | False         |

## RQ2 - cost of the defence

| metric        |   noise_off_mean |   noise_on_mean |   absolute_change |   pct_change |   cohens_d |   mannwhitney_p |
|:--------------|-----------------:|----------------:|------------------:|-------------:|-----------:|----------------:|
| median_ns     |       2416.63    |      2487.86    |          71.2329  |         2.95 |      0.048 |    0.000122495  |
| mean_ns       |       3049.16    |      4610.32    |        1561.16    |        51.2  |      0.583 |    5.78662e-39  |
| p95_ns        |       6161.83    |     15312.2     |        9150.41    |       148.5  |      0.811 |    2.70759e-18  |
| noise_cpu_s   |          0.00262 |         0.01665 |           0.01403 |       535.5  |      1.224 |    1.12422e-119 |
| victim_user_s |          0.00437 |         0.00468 |           0.00031 |         7.09 |      0.055 |    0.341746     |
| victim_sys_s  |          0.02232 |         0.02368 |           0.00136 |         6.09 |      0.088 |    0.0331649    |

### Reading this table

- `noise_cpu_s` is CPU seconds the injector's worker processes
  consumed per trial, read from `/proc/<pid>/stat`. This is the
  direct CPU price of the defence.
- `median_ns` / `mean_ns` / `p95_ns` are per-packet latency. Their
  increase is the price paid by legitimate traffic - the figure an
  operator would actually care about.
- `p95_ns` matters more than the mean for a latency-sensitive service:
  tail latency is what users experience.

## Sentence for the abstract

> Attacker balanced accuracy fell from 0.857 to 0.858 when the noise-injection defence was active, a reduction of -0.1 percentage points (95% CI [-3.1, 2.8]), removing -0.16% of the recoverable leak at a cost of 3.0% median packet latency.

Replace with your own wording - but keep the CI and the cost. A
reduction quoted without its cost is not an evaluation. Check
`trace_multiplication.csv` before calling the defence effective:
a reduction that vanishes as the observation budget grows is a
delay, not a mitigation.
