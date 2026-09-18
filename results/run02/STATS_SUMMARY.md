# Statistical summary

Source: `../data/run02_reactive.csv`
Bootstrap resamples: 2000. Permutations: 10000. Confidence level: 95%.
Chance baseline: 0.25 (4 balanced classes).

## RQ1 - attacker classification accuracy

| model        | condition   |    n |   balanced_accuracy |   ci95_low |   ci95_high |   chance | above_chance   |   p_vs_chance | p_reported   |
|:-------------|:------------|-----:|--------------------:|-----------:|------------:|---------:|:---------------|--------------:|:-------------|
| logreg       | noise_off   | 1000 |               0.706 |     0.6779 |      0.7355 |     0.25 | True           |     9.999e-05 | < 1.0e-04    |
| logreg       | noise_on    | 1000 |               0.667 |     0.6382 |      0.694  |     0.25 | True           |     9.999e-05 | < 1.0e-04    |
| randomforest | noise_off   | 1000 |               0.786 |     0.7617 |      0.8096 |     0.25 | True           |     9.999e-05 | < 1.0e-04    |
| randomforest | noise_on    | 1000 |               0.771 |     0.7453 |      0.796  |     0.25 | True           |     9.999e-05 | < 1.0e-04    |

### Reduction achieved by the defence

| model        |   accuracy_noise_off |   accuracy_noise_on |   reduction_pp |   reduction_ci95_low_pp |   reduction_ci95_high_pp | undefended_above_chance   |   pct_of_leak_removed | significant   |
|:-------------|---------------------:|--------------------:|---------------:|------------------------:|-------------------------:|:--------------------------|----------------------:|:--------------|
| logreg       |                0.706 |               0.667 |            3.9 |                   -0.11 |                     7.95 | True                      |                  8.55 | False         |
| randomforest |                0.786 |               0.771 |            1.5 |                   -1.89 |                     5.06 | True                      |                  2.8  | False         |

## RQ2 - cost of the defence

| metric        |   noise_off_mean |   noise_on_mean |   absolute_change |   pct_change |   cohens_d |   mannwhitney_p |
|:--------------|-----------------:|----------------:|------------------:|-------------:|-----------:|----------------:|
| median_ns     |       2701.18    |      2708.92    |           7.7435  |         0.29 |      0.005 |     0.345151    |
| mean_ns       |       3465.9     |      3483.72    |          17.8122  |         0.51 |      0.008 |     0.526913    |
| p95_ns        |       6653.79    |      6706.99    |          53.1957  |         0.8  |      0.009 |     0.467623    |
| noise_cpu_s   |          0.00638 |         0.01377 |           0.00739 |       115.83 |      0.689 |     7.19595e-42 |
| victim_user_s |          0.00507 |         0.00553 |           0.00046 |         9.07 |      0.077 |     0.152256    |
| victim_sys_s  |          0.02602 |         0.02586 |          -0.00016 |        -0.61 |     -0.009 |     0.925165    |

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

> Attacker balanced accuracy fell from 0.706 to 0.667 when the noise-injection defence was active, a reduction of 3.9 percentage points (95% CI [-0.1, 8.0]), removing 8.55% of the recoverable leak at a cost of 0.3% median packet latency.

Replace with your own wording - but keep the CI and the cost. A
reduction quoted without its cost is not an evaluation. Check
`trace_multiplication.csv` before calling the defence effective:
a reduction that vanishes as the observation budget grows is a
delay, not a mitigation.
