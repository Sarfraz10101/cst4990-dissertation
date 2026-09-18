# Chapter 3 — Methodology / Research Design

*Draft. Word target 1,600 (currently under — pad with transitional sentences during the
formatting pass, not with new claims). Figures/tables cite their generating file so a
marker can trace every number to code.*

## 3.1 Research approach

This dissertation follows a quantitative experimental design, conducted entirely on a
single isolated host with no human participants and no external network dependency.
Both independent variables — the firewall configuration and the presence of the
defence — are under direct experimental control, and the dependent variables (attacker
classification accuracy, CPU overhead, latency inflation) are measured directly from
instrumented code rather than estimated or self-reported. This design was chosen
because the research questions concern a causal, mechanistic relationship (does
injected noise reduce the information an observer can extract, and at what cost) that
a controlled measurement can answer more precisely than a survey or case-study design.
The experiment sits within a Low-Risk ethics self-assessment: no participants, no
personal data, and no system other than the researcher's own laptop and virtual
machine is touched.

## 3.2 Threat model

The attacker is an unprivileged process co-located with a packet-filtering host — able
to run code on, or send traffic to, the victim, but unable to read its configuration
files, query its management interface, or receive any response that reveals firewall
state directly. This is the threat model of interest because it is the one a
correctly-configured firewall is supposed to defeat: an attacker with root or
filesystem access does not need a side channel at all. The observer's only source of
information is a resource-consumption signal — in this case, the wall-clock latency of
a `sendto()` call on the loopback path, which the Linux kernel evaluates against the
`nftables` `input` hook synchronously, in the sending process's own execution context.
The secret the attacker tries to recover is which of four firewall configurations is
currently active (Table 3.1); a working defence should push classification accuracy
toward the 25% chance floor.

## 3.3 Experimental environment

All data collection ran inside a Lubuntu 22.04 guest (kernel 5.15.0-139-generic,
Python 3.8.10, nftables v0.9.3) under VirtualBox on a host with a 13th Gen Intel
Core i9-13980HX. The guest was provisioned with 4 vCPUs and 4 GB RAM — one vCPU to
host the victim process, three to host the noise injector, so that the two never
compete for a single time-sliced core by accident. The VirtualBox process itself was
pinned to the host's eight physical performance cores (excluding the four efficiency
cores) for every collection session, because a vCPU thread migrating between a
P-core and an E-core mid-experiment produces a timing discontinuity an order of
magnitude larger than the side-channel signal itself; this pinning is recorded as an
experimental control in Section 3.7. Timestamps were taken with `CLOCK_MONOTONIC_RAW` at
1 ns nominal resolution. Every run's exact environment (kernel, CPU model, `nft`
version, clock resolution, and every collection parameter) is written to a
`run*.meta.json` file alongside its data, so any run can be independently checked for
drift.

## 3.4 Firewall configurations

The attacker's task is to distinguish four `nftables` configurations, which vary
along two independent axes: **verdict** (accept or drop) and **depth** — the number of
non-matching filler rules the packet traverses before reaching the rule that decides
its fate.

| Config | Verdict | Rules before match |
|---|---|---|
| `accept_shallow` | accept | 0 |
| `accept_deep` | accept | 256 |
| `drop_shallow` | drop | 0 |
| `drop_deep` | drop | 256 |

Four balanced classes give a chance-level baseline of 25%. Depth was implemented as
individually generated filler rules rather than a single compound rule so that
traversal cost accumulates the way it would in a real, incrementally-grown enterprise
ACL, rather than being collapsed into one cheap kernel-side check.

## 3.5 Measurement design

The probe traffic is sent over loopback rather than a physical NIC. This is a
deliberate design choice, not a convenience: on loopback, the kernel evaluates the
`INPUT` chain synchronously inside the sender's own `sendto()` call, so the chain
traversal cost is directly visible in the caller's measured latency. Routing the same
probe through a physical interface would push filtering into a softirq handled on a
different core, and the signal would be lost in ordinary scheduling jitter.

Each trial times 60 batches of 200 `sendto()` calls (`PACKETS_PER_BATCH = 200`,
`BATCHES_PER_TRIAL = 50` recorded, plus 10 discarded); batching amortises the
~1 microsecond of CPython interpreter overhead per call against the 1–20 microsecond
effect of interest, which raises signal-to-noise ratio without rewriting the probe in
a lower-level language. The first ten batches of every trial are discarded as warm-up,
to exclude cold-cache and first-touch effects that are artefacts of process start-up
rather than of the firewall configuration under test. The resulting per-packet
latency (`ns_per_pkt`) is the sole raw measurement from which every downstream feature
is derived.

Sample size was raised from the proposal's 25 trials per condition to 250
(2,000 trials in total: 250 × 4 configurations × 2 defence conditions). Twenty-five
samples spread across a four-class confusion matrix leaves roughly six examples per
class, which cannot support a stable estimate of per-class accuracy or a usable 95%
confidence interval; 250 per cell still collects in under three minutes of wall-clock
time, so the increase costs nothing but is necessary for the statistics in Chapter 4
to be meaningful. Exceeding a proposed minimum is straightforward to justify;
falling short of one is not.

## 3.6 The defence

[[FIGURE:arch]]

The defence, `noise.py`, is a multiprocess noise injector intended to model
algorithmic power-noise injection: randomised bursts of CPU-bound work run in
parallel with the victim process, with the aim of masking the victim's true resource
footprint from an external observer. It uses operating-system processes rather than
threads because CPython's global interpreter lock prevents a multi-threaded injector
from saturating more than one core at a time, which would produce far less execution-
footprint entropy than a process-based design.

Two triggering modes were implemented and evaluated independently: a **Poisson**
mode, in which three worker processes emit bursts at a fixed mean rate of 120 Hz with
burst durations drawn uniformly from 0.5–4.0 ms; and a **reactive** mode, which polls
the `nftables` packet counter every 5 ms and fires a burst only when it changes —
matching the proposal's framing of noise injected "whenever security policies are
triggered". Both modes are evaluated against both of the placement conditions
described in Section 3.7, giving four collected runs in total.

## 3.7 Experimental controls

Five controls were built into the harness because, absent them, a specific artefact
would produce a result that looked like a genuine finding.

**Noise placement.** `--noise-cpus` defaults to every vCPU *except* the one the victim
is pinned to. Under that default, the injector and the victim never contend for the
same core, and the defence cannot perturb the execution footprint it exists to mask —
confirmed empirically by a mean sweep-curve accuracy gap of only +0.017 and +0.001 in
the two cross-core runs (Chapter 4). Re-running with the injector explicitly pinned to
the victim's own core (`--noise-cpus 0`) is what produces a measurable effect. Both
placements were kept as a paired control rather than discarding the ineffective one,
because the contrast is itself a finding: an algorithmic noise defence only works if
it contends for the resource the attacker is measuring, and a naive co-tenancy
deployment does not guarantee that.

**Randomised, interleaved scheduling.** All 2,000 trials for a run are shuffled into a
single randomised order rather than collected block-by-block (all noise-off trials,
then all noise-on trials). Block collection would let ordinary thermal or scheduler
drift over the run's multi-minute duration separate the two conditions with high
apparent accuracy — a pure artefact of collection order rather than of the defence.

**Core pinning.** The VirtualBox process was pinned to the host's physical
performance cores for every session (Section 3.3); without it, a vCPU migrating to an
efficiency core introduces a timing step larger than the effect under test. This
pinning restricts *which* physical cores the guest may use; it does not alter how
the guest's own virtual CPUs are scheduled relative to one another, so it changes
nothing about the noise-placement comparison in Chapter 4 — same-core and
cross-core conditions are both collected under identical, all-performance-core
pinning, and `preflight.py`'s achieved-parallelism check confirms the expected
number of concurrently-runnable workers under pinning before every real
collection, so this control was verified empirically rather than assumed.

**Trial-level aggregation and grouped cross-validation.** The 50 batches within one
trial share a single thermal and scheduling state, so splitting them across the
train/test boundary would leak label information between folds and inflate accuracy
toward 100%. Batches are aggregated to one feature vector per trial, and
cross-validation folds are grouped on `trial_idx`, so no trial's data appears on both
sides of a split. This is the single most common way published side-channel
classifiers overstate their accuracy: Zhou et al. (2018) show the same failure
mode for hardware-performance-counter-based malware classifiers, where splitting
correlated samples from the same execution at random rather than by program
inflates reported detection accuracy, and demonstrate that a grouped split
removes the inflation.

**Shuffled-label control.** Every classifier fit is repeated with permuted labels and
reported alongside the real score. A shuffled-label score materially above the 25%
chance floor would indicate the pipeline is leaking information through some channel
other than the intended signal, invalidating the real result.

## 3.8 Analysis procedure

Nineteen features are derived from `ns_per_pkt` alone per trial (instrumentation
columns such as `noise_cpu_s` are excluded from the predictor set, since they
represent information available to the experimenter, not to a real observer). Two
classifiers — logistic regression and random forest — are trained under grouped
stratified cross-validation, and balanced accuracy is reported with bootstrap 95%
confidence intervals and a permutation test against the chance baseline. To answer
RQ1 with more than a single accuracy figure, `sweep.py` re-runs the attack at
observation budgets of 1, 2, 3, 5, 8, 12, 20, 32 and 50 batches per trial and reports
a trace-multiplication factor: the number of additional batches a defended attacker
needs to reach the accuracy an undefended one reaches at a given budget. The entire
pipeline is deterministic under a fixed seed, and was verified to reproduce all nine
result files byte-for-byte on repeated runs over the same input trace.
