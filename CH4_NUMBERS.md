# Chapter 4 numbers sheet

Every figure Chapter 4 needs, with its source file and the section it serves.
Generated from the four real runs collected 26–27 Aug 2026. Nothing here is
synthetic — `data/synth_*` and `results/synth_*` are pipeline fixtures and must
never appear as results.

**Present, do not interpret.** Interpretation is Chapter 5; the pointers below
say which §5 section each number pays off in.

---

## §4.1 Dataset summary

| Quantity | Value |
|---|---|
| Runs | 4 (2 noise modes x 2 noise placements) |
| Trials per run | 2,000 (250 per config x 4 configs x 2 conditions) |
| Batches per trial | 50 recorded, 10 warm-up discarded |
| Packets per batch | 200 |
| Rows per run | 100,000 |
| Packets timed per run | 2,000 x 50 x 200 = 20,000,000 |
| Collection time | 1.9–2.6 min per run |
| Classes | 4, balanced → chance = 0.25 |

Environment (`data/run0*.meta.json`, quote in §3.3): kernel 5.15.0-139-generic,
Python 3.8.10, nftables v0.9.3, 4 vCPU guest on an i9-13980HX pinned to the eight
P-cores (host affinity mask 65535), `CLOCK_MONOTONIC_RAW` at 1 ns resolution,
seed 20260821.

## §4.2 Signal characterisation

Per-config median ns/packet (run01; run04 is within ~30 ns on medians):

| Config | Median ns/pkt |
|---|---|
| accept_shallow | 1059.6 |
| drop_shallow | 929.4 |
| accept_deep | 3986.4 |
| drop_deep | 3827.1 |

`snr_check.py`, 120 batches per config:

- shallow vs deep: **AUC 1.000** both verdicts (d = 3.74 accept, 9.64 drop)
- accept vs drop: AUC 0.601 shallow, **0.652** deep

So depth is a ~4x effect and near-perfectly separable; verdict is marginal. This
asymmetry drives everything downstream — say it here, before the confusion
matrices show it.

## §4.3 / §4.4 Attacker accuracy

Balanced accuracy, random forest, grouped CV (`rq1_accuracy_ci.csv`):

| Run | Placement | noise_off | noise_on |
|---|---|---|---|
| run01 poisson | cross-core | 0.912 [0.894, 0.929] | 0.902 [0.884, 0.920] |
| run02 reactive | cross-core | 0.786 [0.762, 0.810] | 0.771 [0.745, 0.796] |
| run03 poisson | same-core | 0.817 [0.794, 0.840] | 0.827 [0.803, 0.850] |
| run04 reactive | same-core | 0.906 [0.888, 0.924] | 0.904 [0.886, 0.922] |

Reduction (`rq1_reduction.csv`), logreg / random forest:

| Run | logreg pp | RF pp | significant? |
|---|---|---|---|
| run01 | 2.4 [-0.6, 5.3] | 1.0 [-1.5, 3.5] | No |
| run02 | 3.9 [-0.1, 8.0] | 1.5 [-1.9, 5.1] | No |
| run03 | -0.5 [-4.2, 3.3] | -1.0 [-4.5, 2.1] | No |
| run04 | -0.1 [-3.1, 2.8] | 0.2 [-2.1, 2.6] | No |

**Every reduction CI crosses zero**, in all eight run x model combinations. Word
this as "no statistically significant reduction in single-shot accuracy". Do not
report the 2.4 pp or 3.9 pp as a reduction the defence achieved — the interval
does not exclude zero, and three of the eight point estimates are negative.

Confusion (`confusion_randomforest_noise_off.csv`, run01): all error mass is
accept_deep <-> drop_deep (24 and 48 of 250); shallow classes are 250/250 and
234/250. The classifier recovers depth almost perfectly and guesses verdict —
exactly what §4.2's AUCs predict.

Feature importance: `feature_importance_*.csv`. Features derive from
`ns_per_pkt` only (§9's no-instrumentation control).

## §4.5 Observation-budget curve — the centrepiece

Sweep the **verdict** axis (`--target verdict`, chance 0.5), not the 4-class
axis. The 4-class curve saturates: it opens at 0.717, already past its 0.581
target, so the factor is 1.0 by construction and measures nothing. The floor is
~0.5 rather than 0.25 because perfect depth + coin-flip verdict already scores
half. Report the saturation as a result — depth leaks too strongly to delay —
then use verdict for the actual measurement.

| Run | Placement | TMF | mean gap | max gap | off-curve backward steps |
|---|---|---|---|---|---|
| run01 poisson | cross-core | 1.5x | +0.017 | +0.042 @b2 | 1/8 |
| run02 reactive | cross-core | 1.0x | +0.001 | +0.038 @b2 | 1/8 |
| run03 poisson | same-core | 2.5x | +0.004 | +0.048 @b8 | 3/8 |
| **run04 reactive** | **same-core** | **2.0x** | **+0.061** | **+0.144 @b5** | 3/8 |

That table is generated, not typed: `python harness/contrast.py` rebuilds
`results/CONTRAST_placement.csv` from the per-run CSVs, deriving the placement
column from each run's `noise_cpus` vs `pin` rather than trusting the filename.
Re-run it if any run is re-analysed.

**Use run04 as the figure.** Its curve separates cleanly from batch 2 to 12 and
then recovers — the shape Chari et al. (1999) predict. run03's 2.5x is larger but
rests on one crossing of a curve whose mean gap is +0.004 and which steps
backwards three times; that factor is noise dressed as a result. Quoting the
factor without the gap would overstate run03 and understate run04.

run04 verdict curve (`results/run04/figure_sweep_curve_verdict.csv`):

| batches | noise_off | noise_on |
|---:|---:|---:|
| 1 | 0.660 | 0.628 |
| 2 | 0.722 | 0.664 |
| 3 | 0.754 | 0.672 |
| 5 | 0.814 | 0.670 |
| 8 | 0.810 | 0.682 |
| 12 | 0.806 | 0.726 |
| 20 | 0.786 | 0.768 |
| 32 | 0.804 | 0.780 |
| 50 | 0.816 | 0.834 |

By 50 batches the defended attacker has caught up and marginally passed the
undefended one. That recovery is the point: the defence delays, it does not
defeat. Pays off in §5.3.

## §4.4b Why the reduction is null — the low-tail channel

`python harness/tails.py --data data/run04_reactive_samecore.csv --out results/run04`
→ `tail_quantile_inflation.csv`, `tail_importance_shift.csv`, `tail_ablation.csv`.

The null in §4.4 is not "the defence did nothing". It is "the defence moved the
wrong part of the distribution". Injected noise is **additive**: a competing burst
can only make a send slower, and nothing the injector does can make the victim's
fastest packets faster. So the floor survives.

run04, deep configs, per-packet quantiles (`tail_quantile_inflation.csv`):

| Quantile | noise_off ns | noise_on ns | change |
|---|---:|---:|---:|
| q05 | 3427.1 | 3461.6 | **+1.0%** |
| q10 | 3487.8 | 3533.9 | +1.3% |
| q25 | 3600.7 | 3650.6 | +1.4% |
| q50 | 3829.5 | 3931.2 | +2.7% |
| q75 | 4308.1 | 4876.4 | +13.2% |
| q90 | 8465.2 | 17406.7 | +105.6% |
| q95 | 12126.0 | 32745.5 | **+170.0%** |

A 170-fold-steeper effect at q95 than at q05. The forest follows the signal:
low-tail importance mass rises +0.067 while upper-tail mass falls −0.084
(`tail_importance_shift.csv`), and fig5 shows this visually.

**The decisive test** (`tail_ablation.csv`) — train on one group only, verdict
axis, chance 0.5:

| Run | Placement | low-tail off→on | upper-tail off→on |
|---|---|---|---|
| run01 poisson | cross-core | 0.834 → 0.796 (+0.038) | 0.662 → 0.660 (+0.002) |
| run02 reactive | cross-core | 0.672 → 0.672 (**0.000**) | 0.570 → 0.502 (+0.068) |
| run03 poisson | same-core | 0.718 → 0.720 (**−0.002**) | 0.686 → 0.520 (+0.166) |
| **run04 reactive** | **same-core** | 0.832 → 0.824 (**+0.008**) | 0.658 → 0.538 (**+0.120**) |

In run04 the upper-tail classifier loses 15x more accuracy than the low-tail one,
and falls to 0.538 — near chance. The low-tail classifier is untouched. Both
same-core runs show it; run02 shows it weakly; run01 does not.

Report this in §4.4 as the explanation for the crossing CIs, and note that the
full 19-feature attacker loses **0.000** in run04 — it simply routes around the
defence.

Pays off twice in Chapter 5. §5.3: Chari et al. (1999) assume noise raises the
attacker's work uniformly, and on an additive-noise-versus-order-statistic channel
it does not. §5.5 gets a specific, non-generic recommendation: **a timing defence
must raise the floor, not the tail.** Constant-time padding to a fixed minimum
would do that; random bursts cannot, however expensive they are — and run03 paid
+4017% CPU for exactly this failure.

## §4.6 Cost of the defence

`rq2_overhead.csv`. Note p95 alongside the median — the tail moves far more:

| Run | Placement | median lat | p95 lat | CPU (noise_cpu_s) |
|---|---|---|---|---|
| run01 poisson | cross-core | +1.46% | +3.23% | +474% |
| run02 reactive | cross-core | +0.29% | +0.80% | +116% |
| run03 poisson | same-core | +2.96% | **+431.9%** | **+4017%** |
| run04 reactive | same-core | +2.95% | +148.5% | +536% |

run03 raw p95: 4,474 → 23,619 ns. `noise_cpu_s` per trial, run01: 0.0029 →
0.0167 CPU-s, p ≈ 2e-146.

The trade for run04's 2.0x is +149% p95 latency and +536% CPU. State the pairing
plainly here; argue about acceptability in §5.2 and §5.5.

## §4.7 Validity checks

- Shuffled-label controls (`accuracy.csv`): 0.231–0.258 against chance 0.25, all
  four runs, both models. `run_analysis.sh` asserts every fit is within 0.08 of
  chance and printed **control check PASSED** for all four.
- Interleaved schedule, seed 20260821; trial-level aggregation; grouped CV on
  `trial_idx`; instrumentation columns excluded from predictors.
- Null synthetic fixture sits at 0.25 in both conditions.
- `preflight.py` verdict READY, one caveat: RAPL `energy_uj` unreadable —
  hypervisor-masked. That is the evidence for §1.5 and §5.4's "timing, not
  electrical power" scoping, and it is recorded in `data/preflight.json` rather
  than asserted.

## Known defects to disclose, not hide

1. **`noise_cpu_s` read zero in the first collection** (26 Aug).
   `getrusage(RUSAGE_CHILDREN)` only counts *reaped* children, and the worker
   pool is deliberately long-lived, so the counter could never move. Fixed to
   read `/proc/<pid>/stat`; both runs re-collected. Any RQ2 CPU figure predating
   27 Aug is invalid. Latency figures from those runs were unaffected. Worth a
   sentence in §5.6 — it is a good instrumentation-vs-phenomenon anecdote.
2. **Cross-core placement made the defence inert** (§9). `--noise-cpus` defaults
   to every core *except* `--pin`, so the injector never contended with the
   victim. Kept as the "misconfigured defence" baseline rather than discarded.

## Figures

`results/run04/figures/` (and per run): `fig1_latency_by_config.png`,
`fig2_accuracy_and_controls.png`, `fig3_sweep_curve.png`,
`fig3b_sweep_curve_verdict.png`, `fig4_confusion_{logreg,randomforest}.png`,
`fig5_feature_importance.png`, plus `FIGURE_CAPTIONS.md` with draft captions.
Cross-run table: `results/CONTRAST_placement.csv`.

**For §4.5 use `results/run04/figures/fig3b_sweep_curve_verdict.png`.** That is
the verdict axis, chance 0.5, with the 2.0x arrow drawn at the 0.658 target and
the mean separation quoted in the caption. `fig3_sweep_curve.png` is the
four-class panel: it now states its own saturation on the face of the plot
("both conditions clear the target at the smallest budget tested, so the factor
is 1.0 by construction") rather than drawing a zero-length arrow. Both are worth
including — the saturated one is the evidence for the "depth leaks too strongly
to delay" claim in §4.5's opening.
