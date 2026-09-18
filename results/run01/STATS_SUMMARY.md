# Statistical summary

Source: `../data/run01_poisson.csv`
Bootstrap resamples: 2000. Permutations: 10000. Confidence level: 95%.
Chance baseline: 0.25 (4 balanced classes).

## RQ1 - attacker classification accuracy

| model        | condition   |    n |   balanced_accuracy |   ci95_low |   ci95_high |   chance | above_chance   |   p_vs_chance | p_reported   |
|:-------------|:------------|-----:|--------------------:|-----------:|------------:|---------:|:---------------|--------------:|:-------------|
| logreg       | noise_off   | 1000 |               0.864 |     0.8426 |      0.8843 |     0.25 | True           |     9.999e-05 | < 1.0e-04    |
| logreg       | noise_on    | 1000 |               0.84  |     0.8185 |      0.8609 |     0.25 | True           |     9.999e-05 | < 1.0e-04    |
| randomforest | noise_off   | 1000 |               0.912 |     0.894  |      0.9288 |     0.25 | True           |     9.999e-05 | < 1.0e-04    |
| randomforest | noise_on    | 1000 |               0.902 |     0.8838 |      0.92   |     0.25 | True           |     9.999e-05 | < 1.0e-04    |

### Reduction achieved by the defence

| model        |   accuracy_noise_off |   accuracy_noise_on |   reduction_pp |   reduction_ci95_low_pp |   reduction_ci95_high_pp | undefended_above_chance   |   pct_of_leak_removed | significant   |
|:-------------|---------------------:|--------------------:|---------------:|------------------------:|-------------------------:|:--------------------------|----------------------:|:--------------|
| logreg       |                0.864 |               0.84  |            2.4 |                   -0.55 |                     5.27 | True                      |                  3.91 | False         |
| randomforest |                0.912 |               0.902 |            1   |                   -1.5  |                     3.52 | True                      |                  1.51 | False         |

## RQ2 - cost of the defence

| metric        |   noise_off_mean |   noise_on_mean |   absolute_change |   pct_change |   cohens_d |   mannwhitney_p |
|:--------------|-----------------:|----------------:|------------------:|-------------:|-----------:|----------------:|
| median_ns     |       2469.16    |      2505.2     |          36.0345  |         1.46 |      0.024 |    0.0204503    |
| mean_ns       |       2559.6     |      2609.77    |          50.1703  |         1.96 |      0.033 |    0.0296891    |
| p95_ns        |       3130.85    |      3231.88    |         101.037   |         3.23 |      0.055 |    0.23648      |
| noise_cpu_s   |          0.00291 |         0.0167  |           0.01379 |       473.88 |      1.37  |    1.97869e-146 |
| victim_user_s |          0.00489 |         0.00495 |           6e-05   |         1.23 |      0.01  |    0.827088     |
| victim_sys_s  |          0.02327 |         0.02386 |           0.00059 |         2.54 |      0.037 |    0.317557     |

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

> Attacker balanced accuracy fell from 0.864 to 0.840 when the noise-injection defence was active, a reduction of 2.4 percentage points (95% CI [-0.6, 5.3]), removing 3.91% of the recoverable leak at a cost of 1.5% median packet latency.

Replace with your own wording - but keep the CI and the cost. A
reduction quoted without its cost is not an evaluation. Check
`trace_multiplication.csv` before calling the defence effective:
a reduction that vanishes as the observation budget grows is a
delay, not a mitigation.
