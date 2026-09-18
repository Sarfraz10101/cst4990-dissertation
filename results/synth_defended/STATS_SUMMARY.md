# Statistical summary

Source: `../data/synth_defended.csv`
Bootstrap resamples: 500. Permutations: 2000. Confidence level: 95%.
Chance baseline: 0.25 (4 balanced classes).

## RQ1 - attacker classification accuracy

| model        | condition   |   n |   balanced_accuracy |   ci95_low |   ci95_high |   chance | above_chance   |   p_vs_chance | p_reported   |
|:-------------|:------------|----:|--------------------:|-----------:|------------:|---------:|:---------------|--------------:|:-------------|
| logreg       | noise_off   | 480 |              0.9458 |     0.9273 |      0.9639 |     0.25 | True           |    0.00049975 | < 5.0e-04    |
| logreg       | noise_on    | 480 |              0.4    |     0.3574 |      0.4439 |     0.25 | True           |    0.00049975 | < 5.0e-04    |
| randomforest | noise_off   | 480 |              0.9583 |     0.9414 |      0.9762 |     0.25 | True           |    0.00049975 | < 5.0e-04    |
| randomforest | noise_on    | 480 |              0.3917 |     0.3508 |      0.4326 |     0.25 | True           |    0.00049975 | < 5.0e-04    |

### Reduction achieved by the defence

| model        |   accuracy_noise_off |   accuracy_noise_on |   reduction_pp |   reduction_ci95_low_pp |   reduction_ci95_high_pp |   pct_of_leak_removed | significant   |
|:-------------|---------------------:|--------------------:|---------------:|------------------------:|-------------------------:|----------------------:|:--------------|
| logreg       |               0.9458 |              0.4    |          54.58 |                    49.2 |                    58.87 |                 78.44 | True          |
| randomforest |               0.9583 |              0.3917 |          56.67 |                    52.3 |                    60.73 |                 80    | True          |

## RQ2 - cost of the defence

| metric        |   noise_off_mean |   noise_on_mean |   absolute_change |   pct_change |   cohens_d |   mannwhitney_p |
|:--------------|-----------------:|----------------:|------------------:|-------------:|-----------:|----------------:|
| median_ns     |      1842.76     |     1553.86     |       -288.906    |       -15.68 |     -1.553 |    1.46996e-64  |
| mean_ns       |      1859.04     |     1567.39     |       -291.65     |       -15.69 |     -1.552 |    2.43733e-65  |
| p95_ns        |      1920.66     |     1782.2      |       -138.463    |        -7.21 |     -0.683 |    2.68185e-22  |
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

> Attacker balanced accuracy fell from 0.946 to 0.400 when the noise-injection defence was active, a reduction of 54.6 percentage points (95% CI [49.2, 58.9]), removing 78.44% of the recoverable leak at a cost of -15.7% median packet latency.

Replace with your own wording - but keep the CI and the cost. A
reduction quoted without its cost is not an evaluation.
