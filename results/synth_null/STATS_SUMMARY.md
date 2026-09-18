# Statistical summary

Source: `C:/Users/abdul/CST4990-dissertation/data/synth_null.csv`
Bootstrap resamples: 2000. Permutations: 10000. Confidence level: 95%.
Chance baseline: 0.25 (4 balanced classes).

## RQ1 - attacker classification accuracy

| model        | condition   |   n |   balanced_accuracy |   ci95_low |   ci95_high |   chance | above_chance   |   p_vs_chance |   p_reported |
|:-------------|:------------|----:|--------------------:|-----------:|------------:|---------:|:---------------|--------------:|-------------:|
| logreg       | noise_off   | 480 |              0.2479 |     0.2106 |      0.287  |     0.25 | False          |      0.554645 |       0.5546 |
| logreg       | noise_on    | 480 |              0.2417 |     0.2033 |      0.2799 |     0.25 | False          |      0.659634 |       0.6596 |
| randomforest | noise_off   | 480 |              0.2167 |     0.1823 |      0.2554 |     0.25 | False          |      0.960504 |       0.9605 |
| randomforest | noise_on    | 480 |              0.2188 |     0.1831 |      0.2556 |     0.25 | False          |      0.947005 |       0.947  |

### Reduction achieved by the defence

| model        |   accuracy_noise_off |   accuracy_noise_on |   reduction_pp |   reduction_ci95_low_pp |   reduction_ci95_high_pp | undefended_above_chance   | pct_of_leak_removed   | significant   |
|:-------------|---------------------:|--------------------:|---------------:|------------------------:|-------------------------:|:--------------------------|:----------------------|:--------------|
| logreg       |               0.2479 |              0.2417 |           0.62 |                   -4.95 |                     5.92 | False                     |                       | False         |
| randomforest |               0.2167 |              0.2188 |          -0.21 |                   -5.35 |                     4.95 | False                     |                       | False         |

## RQ2 - cost of the defence

| metric        |   noise_off_mean |   noise_on_mean |   absolute_change |   pct_change |   cohens_d |   mannwhitney_p |
|:--------------|-----------------:|----------------:|------------------:|-------------:|-----------:|----------------:|
| median_ns     |      1502.76     |     1502.86     |          0.093646 |         0.01 |      0.002 |    0.972607     |
| mean_ns       |      1519.04     |     1516.39     |         -2.65049  |        -0.17 |     -0.042 |    0.541669     |
| p95_ns        |      1580.66     |     1731.2      |        150.537    |         9.52 |      1.471 |    1.15739e-116 |
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

## No leak was established

The undefended attacker's 95% confidence interval includes the chance baseline (0.25), so there is no demonstrated side channel in this dataset and no reduction to attribute to the defence.

That is a reportable outcome, not a failed experiment - but it must be reported as a null result on RQ1, and the RQ2 overhead figures above stand on their own. Work through README section 6 before concluding the channel does not exist.
