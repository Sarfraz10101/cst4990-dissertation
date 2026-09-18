# Statistical summary

Source: `C:/Users/abdul/CST4990-dissertation/data/run03_poisson_samecore.csv`
Bootstrap resamples: 2000. Permutations: 10000. Confidence level: 95%.
Chance baseline: 0.25 (4 balanced classes).

## RQ1 - attacker classification accuracy

| model        | condition   |    n |   balanced_accuracy |   ci95_low |   ci95_high |   chance | above_chance   |   p_vs_chance | p_reported   |
|:-------------|:------------|-----:|--------------------:|-----------:|------------:|---------:|:---------------|--------------:|:-------------|
| logreg       | noise_off   | 1000 |               0.743 |     0.7176 |      0.7691 |     0.25 | True           |     9.999e-05 | < 1.0e-04    |
| logreg       | noise_on    | 1000 |               0.748 |     0.7211 |      0.7732 |     0.25 | True           |     9.999e-05 | < 1.0e-04    |
| randomforest | noise_off   | 1000 |               0.817 |     0.7938 |      0.8399 |     0.25 | True           |     9.999e-05 | < 1.0e-04    |
| randomforest | noise_on    | 1000 |               0.827 |     0.8033 |      0.8497 |     0.25 | True           |     9.999e-05 | < 1.0e-04    |

### Reduction achieved by the defence

| model        |   accuracy_noise_off |   accuracy_noise_on |   reduction_pp |   reduction_ci95_low_pp |   reduction_ci95_high_pp | undefended_above_chance   |   pct_of_leak_removed | significant   |
|:-------------|---------------------:|--------------------:|---------------:|------------------------:|-------------------------:|:--------------------------|----------------------:|:--------------|
| logreg       |                0.743 |               0.748 |           -0.5 |                   -4.16 |                     3.25 | True                      |                 -1.01 | False         |
| randomforest |                0.817 |               0.827 |           -1   |                   -4.46 |                     2.13 | True                      |                 -1.76 | False         |

## RQ2 - cost of the defence

| metric        |   noise_off_mean |   noise_on_mean |   absolute_change |   pct_change |   cohens_d |   mannwhitney_p |
|:--------------|-----------------:|----------------:|------------------:|-------------:|-----------:|----------------:|
| median_ns     |       2486.94    |      2560.6     |          73.6599  |         2.96 |      0.049 |    0.000219262  |
| mean_ns       |       2573.03    |      4913.65    |        2340.63    |        90.97 |      0.915 |    7.1862e-63   |
| p95_ns        |       3120.36    |     16598.2     |       13477.9     |       431.93 |      1.28  |    7.02892e-59  |
| noise_cpu_s   |          0.00059 |         0.02429 |           0.0237  |      4016.95 |      1.61  |    6.01066e-232 |
| victim_user_s |          0.00453 |         0.00504 |           0.00051 |        11.26 |      0.087 |    0.0559047    |
| victim_sys_s  |          0.02301 |         0.0245  |           0.00149 |         6.48 |      0.093 |    0.0262014    |

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

> Attacker balanced accuracy fell from 0.743 to 0.748 when the noise-injection defence was active, a reduction of -0.5 percentage points (95% CI [-4.2, 3.2]), removing -1.01% of the recoverable leak at a cost of 3.0% median packet latency.

Replace with your own wording - but keep the CI and the cost. A
reduction quoted without its cost is not an evaluation. Check
`trace_multiplication.csv` before calling the defence effective:
a reduction that vanishes as the observation budget grows is a
delay, not a mitigation.
