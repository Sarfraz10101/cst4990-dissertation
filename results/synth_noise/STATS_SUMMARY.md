# Statistical summary

Source: `C:/Users/abdul/CST4990-dissertation/data/synth_noise.csv`
Bootstrap resamples: 2000. Permutations: 10000. Confidence level: 95%.
Chance baseline: 0.25 (4 balanced classes).

## RQ1 - attacker classification accuracy

| model        | condition   |   n |   balanced_accuracy |   ci95_low |   ci95_high |   chance | above_chance   |   p_vs_chance | p_reported   |
|:-------------|:------------|----:|--------------------:|-----------:|------------:|---------:|:---------------|--------------:|:-------------|
| logreg       | noise_off   | 480 |              0.9458 |     0.9255 |      0.9645 |     0.25 | True           |     9.999e-05 | < 1.0e-04    |
| logreg       | noise_on    | 480 |              0.8833 |     0.8544 |      0.911  |     0.25 | True           |     9.999e-05 | < 1.0e-04    |
| randomforest | noise_off   | 480 |              0.9583 |     0.9408 |      0.9749 |     0.25 | True           |     9.999e-05 | < 1.0e-04    |
| randomforest | noise_on    | 480 |              0.9042 |     0.8772 |      0.9289 |     0.25 | True           |     9.999e-05 | < 1.0e-04    |

### Reduction achieved by the defence

| model        |   accuracy_noise_off |   accuracy_noise_on |   reduction_pp |   reduction_ci95_low_pp |   reduction_ci95_high_pp | undefended_above_chance   |   pct_of_leak_removed | significant   |
|:-------------|---------------------:|--------------------:|---------------:|------------------------:|-------------------------:|:--------------------------|----------------------:|:--------------|
| logreg       |               0.9458 |              0.8833 |           6.25 |                    2.79 |                     9.84 | True                      |                  8.98 | True          |
| randomforest |               0.9583 |              0.9042 |           5.42 |                    2.33 |                     8.49 | True                      |                  7.65 | True          |

## RQ2 - cost of the defence

| metric        |   noise_off_mean |   noise_on_mean |   absolute_change |   pct_change |   cohens_d |   mannwhitney_p |
|:--------------|-----------------:|----------------:|------------------:|-------------:|-----------:|----------------:|
| median_ns     |      1842.76     |     2031.21     |        188.446    |        10.23 |      0.738 |    8.46005e-24  |
| mean_ns       |      1859.04     |     2040.59     |        181.549    |         9.77 |      0.707 |    7.22413e-22  |
| p95_ns        |      1920.66     |     2560.94     |        640.277    |        33.34 |      2.373 |    3.48843e-131 |
| noise_cpu_s   |         0        |        0.021037 |          0.021037 |       nan    |     17.317 |    8.91972e-181 |
| victim_user_s |         0.004001 |        0.004017 |          1.6e-05  |         0.4  |      0.04  |    0.495315     |
| victim_sys_s  |         0.011095 |        0.01266  |          0.001565 |        14.11 |      1.318 |    1.06236e-66  |

### Reading this table

- `noise_cpu_s` is CPU seconds the injector consumed per trial, from
  `RUSAGE_CHILDREN`. This is the direct CPU price of the defence.
- `median_ns` / `mean_ns` / `p95_ns` are per-packet latency. Their
  increase is the price paid by legitimate traffic - the figure an
  operator would actually care about.
- `p95_ns` matters more than the mean for a latency-sensitive service:
  tail latency is what users experience.

## Sentence for the abstract

> Attacker balanced accuracy fell from 0.946 to 0.883 when the noise-injection defence was active, a reduction of 6.2 percentage points (95% CI [2.8, 9.8]), removing 8.98% of the recoverable leak at a cost of 10.2% median packet latency.

Replace with your own wording - but keep the CI and the cost. A
reduction quoted without its cost is not an evaluation. Check
`trace_multiplication.csv` before calling the defence effective:
a reduction that vanishes as the observation budget grows is a
delay, not a mitigation.
