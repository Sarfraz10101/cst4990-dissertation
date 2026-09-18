# Chapter 4: Results & Analysis

*Final. Matches the submitted dissertation (`CST4990_Dissertation_Masood_final.docx`).
Every number below is sourced in `CH4_NUMBERS.md`; do not hand-edit a figure here
without regenerating it from the corresponding CSV.*

## 4.1 Dataset summary

Four runs were collected on 26 and 27 August 2026, each following the collection
procedure and parameters fixed in Chapter 3 (2,000 trials per run, 250 per
configuration, 50 recorded batches of 200 packets per trial). The four runs
differ only in the two defence variables under test (triggering mode and
noise-injector placement) and are identified consistently by this table
throughout the chapter, so that every number below can be traced back to the
exact configuration that produced it:

| Run ID | Noise mode | Noise placement |
|---|---|---|
| run01 | Poisson | cross-core |
| run02 | reactive | cross-core |
| run03 | Poisson | same-core |
| run04 | reactive | same-core |

Every table and figure in this chapter labels results by this run ID rather
than by mode/placement alone, so a reader can trace any number back to Chapter
3's exact experimental setup for that run. Per-run environment details (kernel,
Python, `nftables` version, clock resolution, seed) are recorded individually
in `data/run*.meta.json` and do not vary across runs.

## 4.2 Signal characterisation

Median per-packet latency separates cleanly by chain depth:

| Config | Median ns/pkt |
|---|---|
| accept_shallow | 1059.6 |
| drop_shallow | 929.4 |
| accept_deep | 3986.4 |
| drop_deep | 3827.1 |

`snr_check.py` (120 batches per configuration) quantifies this as a near-perfect
signal on the depth axis (AUC 1.000 for both verdicts, Cohen's *d* of 3.74 for accept
and 9.64 for drop), against a much weaker signal on the verdict axis: AUC 0.601
(shallow) and 0.652 (deep). Chain depth is therefore roughly a four-fold effect on
raw latency and is separable from a single packet, while accept/drop is a
substantially smaller, marginal effect. This asymmetry between the two axes shapes
every result that follows.

[[FIGURE:fig1]]

## 4.3 Attacker accuracy: defence inactive

With the defence off, a random forest classifier under grouped cross-validation
achieves balanced accuracy well above the 25% chance floor in every run:

| Run | Placement | Balanced accuracy (noise off) |
|---|---|---|
| run01 (Poisson) | cross-core | 0.912 [0.894, 0.929] |
| run02 (reactive) | cross-core | 0.786 [0.762, 0.810] |
| run03 (Poisson) | same-core | 0.817 [0.794, 0.840] |
| run04 (reactive) | same-core | 0.906 [0.888, 0.924] |

[[FIGURE:fig2]]

The confusion matrix for run01 (`confusion_randomforest_noise_off.csv`) shows the
error structure implied by Section 4.2: the two shallow configurations are recovered almost
perfectly (250/250 and 234/250), while essentially all classification error is
confined to confusing `accept_deep` with `drop_deep` (24 and 48 misclassifications
out of 250 respectively). The classifier recovers chain depth almost perfectly and
is comparatively unreliable on verdict, exactly what the AUC values in Section 4.2
predict.

[[FIGURE:fig4rf]]

[[FIGURE:fig4lr]]

Feature importances (`feature_importance_*.csv`) confirm that all
discriminative power derives from `ns_per_pkt`-based statistics; no instrumentation
column contributes, by construction (Section 3.7).

[[FIGURE:fig5]]

The same asymmetry appears in all four runs, not only run01: balanced accuracy
never drops below 0.786 (run02) even though run02 and run04 use the reactive
triggering mode with no defence engaged yet, because the depth axis alone is
sufficient to carry a random forest well above chance regardless of which
triggering mode was later paired with it during collection. This is expected:
noise mode and injector placement are properties of the *defended* condition
only, and Section 4.3 reports the undefended condition, so cross-run variation here
reflects ordinary sampling variation in the classifier and collection schedule
rather than any property of the (as yet inactive) defence.

## 4.4 Attacker accuracy: defence active

| Run | Placement | Balanced accuracy (noise on) | Reduction, RF (pp) |
|---|---|---|---|
| run01 (Poisson) | cross-core | 0.902 [0.884, 0.920] | 1.0 [-1.5, 3.5] |
| run02 (reactive) | cross-core | 0.771 [0.745, 0.796] | 1.5 [-1.9, 5.1] |
| run03 (Poisson) | same-core | 0.827 [0.803, 0.850] | -1.0 [-4.5, 2.1] |
| run04 (reactive) | same-core | 0.904 [0.886, 0.922] | 0.2 [-2.1, 2.6] |

Every reduction confidence interval crosses zero, for both classifiers in all eight
run × model combinations tested. There is no statistically significant reduction in
single-shot classification accuracy in any configuration tested; three of the eight
point estimates are in fact negative.

**Why the reduction is null.** Per-packet quantile analysis of run04 (deep
configurations, `tail_quantile_inflation.csv`) shows the defence's effect is highly
non-uniform across the latency distribution:

| Quantile | noise off (ns) | noise on (ns) | change |
|---|---:|---:|---:|
| q05 | 3427.1 | 3461.6 | +1.0% |
| q50 | 3829.5 | 3931.2 | +2.7% |
| q90 | 8465.2 | 17406.7 | +105.6% |
| q95 | 12126.0 | 32745.5 | +170.0% |

The injected noise is additive, so it can only make a `sendto()` call slower; it
cannot make the victim's fastest packets faster. The lower tail of the distribution
is therefore almost unaffected while the upper tail inflates by two orders of
magnitude more. A decisive ablation (`tail_ablation.csv`) trains separate classifiers
on low-tail-only and upper-tail-only features (verdict axis, chance 0.5): in run04,
the upper-tail classifier drops from 0.658 to 0.538 (near chance) when the defence is
active, while the low-tail classifier is essentially untouched (0.832 → 0.824). A
classifier using the full 19-feature set loses 0.000 balanced accuracy in the same
run. It simply routes around the part of the distribution the defence perturbs.

## 4.5 Observation-budget curve

A single accuracy figure understates what the defence does. Sweeping the observation
budget (batches per trial) on the **verdict** axis (chance 0.5), the axis on which
noise has measurable room to act per Section 4.2, shows accuracy climbing with budget under
both conditions, with the defended curve initially lagging the undefended one:

| Placement / mode | Trace-multiplication factor | Mean gap | Max gap |
|---|---|---|---|
| run01, Poisson, cross-core | 1.5× | +0.017 | +0.042 @ 2 batches |
| run02, reactive, cross-core | 1.0× | +0.001 | +0.038 @ 2 batches |
| run03, Poisson, same-core | 2.5× | +0.004 | +0.048 @ 8 batches |
| **run04, reactive, same-core** | **2.0×** | **+0.061** | **+0.144 @ 5 batches** |

run03's larger nominal factor rests on a single crossing of a curve whose mean gap is
+0.004 and which steps backward three times out of eight sampled budgets; run04's
smaller factor sits on a curve that separates cleanly from 2 to 12 batches with a
mean gap an order of magnitude larger, and is the figure of record for this section
(`fig3b_sweep_curve_verdict.png`):

| Batches | noise off | noise on |
|---:|---:|---:|
| 1 | 0.660 | 0.628 |
| 2 | 0.722 | 0.664 |
| 5 | 0.814 | 0.670 |
| 12 | 0.806 | 0.726 |
| 20 | 0.786 | 0.768 |
| 50 | 0.816 | 0.834 |

By 50 batches the defended attacker has caught up to, and marginally exceeded, the
undefended one. The equivalent sweep on the 4-class axis saturates: both conditions
already clear the half-way accuracy target at the smallest budget tested (1 batch,
opening accuracy 0.717), so the trace-multiplication factor is 1.0 by construction
and the sweep measures nothing on that axis. This saturation is itself a result:
chain depth leaks far more strongly, and far faster, than verdict does.

[[FIGURE:fig3]]

[[FIGURE:fig3b]]

## 4.6 Cost of the defence

| Run | Placement | Median latency increase | p95 latency increase | CPU increase |
|---|---|---:|---:|---:|
| run01, Poisson | cross-core | +1.46% | +3.23% | +474% |
| run02, reactive | cross-core | +0.29% | +0.80% | +116% |
| run03, Poisson | same-core | +2.96% | +431.9% | +4017% |
| run04, reactive | same-core | +2.95% | +148.5% | +536% |

The tail moves far more than the median: run03's raw p95 latency rises from 4,474 ns
to 23,619 ns. `noise_cpu_s` per trial in run01 rises from 0.0029 to 0.0167 CPU-seconds
(*p* ≈ 2 × 10⁻¹⁴⁶). The trade attached to run04's 2.0× trace-multiplication factor is
+148.5% p95 latency and +536% CPU overhead.

The two same-core runs (run03, run04) pay markedly more CPU overhead than the
two cross-core runs (run01, run02) despite using the same three-worker,
120 Hz-mean burst configuration, because same-core placement forces the
injector to contend with the victim for scheduling quanta on a single vCPU
rather than running unopposed on idle cores. The same placement choice that
Section 4.5 shows is necessary for the defence to have any accuracy effect at all is
also the more computationally expensive one to run. Poisson triggering (run01,
run03) is consistently costlier than reactive triggering (run02, run04) at
matched placement, since Poisson bursts fire continuously at a fixed mean rate
regardless of firewall activity, whereas reactive bursts fire only when the
`nftables` counter moves.

## 4.7 Validity checks

Shuffled-label controls sit between 0.231 and 0.258 against a chance baseline of 0.25
across all four runs and both classifiers; `run_analysis.sh` asserts every such
control is within 0.08 of chance and reports a pass for all four runs. A synthetic
null-data fixture (`data/synth_null.csv`, not a result) scores at the chance floor in
both conditions, confirming the pipeline does not manufacture a signal where none
exists. `preflight.py` reported a READY verdict prior to every collection, with one
recorded caveat: the RAPL `energy_uj` counter is unreadable inside the VirtualBox
guest, consistent with the scoping stated in Section 1.5.
