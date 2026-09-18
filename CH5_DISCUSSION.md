# Chapter 5 — Discussion & Critical Evaluation

*Draft. Word target 1,400.*

## 5.1 Answering RQ1

RQ1 asked to what extent algorithmic noise injection lowers an attacker's
classification accuracy. Taken as a single number, the answer is "not
significantly": every reduction confidence interval across eight run × model
combinations crosses zero (Section 4.4), and three of the eight point estimates are
negative. Read that way, the defence appears to do nothing.

That reading is incomplete, and the observation-budget curve in Section 4.5 shows why.
Under the most effective configuration tested — reactive triggering with the
injector sharing the victim's core — the defended attacker needs roughly twice as
many observation batches to reach the accuracy an undefended attacker reaches at
the same budget, with a mean accuracy gap of +0.061 and a peak of +0.144 at five
batches. The defence does not lower the attacker's *ceiling*; it raises the
*cost of observation* needed to reach it. A single accuracy figure, collected at
one arbitrarily-chosen budget, cannot distinguish "the defence does nothing" from
"the defence delays the attacker by a factor of two" — both look identical at a
budget large enough for the curves to reconverge. This is the central
methodological argument of the dissertation: RQ1 does not have a single-number
answer, and evaluations that report only one should be treated with suspicion.

## 5.2 Answering RQ2

RQ2 asked what computational overhead the defence imposes. The cost is
substantial and asymmetric between the median and the tail. Median latency
inflation stayed under 3% in every run, which in isolation looks acceptable. p95
latency, however, rose by 148.5% in the best-performing configuration (run04) and
by 431.9% in the worst (run03); CPU overhead ranged from +116% to +4017% across
the four runs. Whether this trade is acceptable depends entirely on which
statistic a deployment is judged against: a defence that triples tail latency to
buy a two-fold increase in an attacker's required observation budget is a very
different proposition from one framed only by its sub-3% median cost. Section 5.5 argues
that reporting the median alone, as much prior noise-injection evaluation does, is
itself part of the problem this dissertation identifies.

The CPU figure needs the same scrutiny before it is used to argue for or against
deployment. A CPU increase reported as a percentage of an already-tiny baseline is
easy to misread: run01's headline +474% corresponds to an absolute rise from 0.0029
to 0.0167 CPU-seconds per trial (Section 4.6), which is negligible in isolation on a
single host but does not by itself say what happens under production load, where
the injector's workers compete with real traffic-handling processes for the same
cores rather than running on an otherwise-idle guest. The percentage answers "how
much more work is the defence doing relative to itself", not "can this host afford
it", and only the second question determines whether the trade is acceptable at a
given deployment's utilisation level. Reporting both the relative increase and the
absolute CPU-seconds figure, as this dissertation does throughout Section 4.6, is
necessary for exactly this reason: a relative figure alone cannot be evaluated
against a specific host's spare capacity.

## 5.3 Relation to prior work

Chari et al. (1999) predicted, for noise-based countermeasures against power
analysis, that noise multiplies the number of traces an attacker needs rather than
eliminating the underlying leak. The observation-budget curve in Section 4.5 reproduces
exactly this shape on a modern kernel firewall, a very different system from the
cryptographic hardware Chari et al. analysed: accuracy under the defence starts
below the undefended curve and converges toward it as the attacker is given more
observations, rather than remaining suppressed indefinitely. That the same
qualitative behaviour appears in kernel-level packet filtering as in hardware
power traces is evidence that the theoretical argument — additive noise raises
cost rather than removing information — generalises beyond the domain it was
originally proposed for.

The tail-quantile analysis in Section 4.4 adds a mechanism Chari et al.'s original
argument does not need to specify, because it assumes noise perturbs the signal
more or less uniformly. This defence does not: because the injected noise is
additive, it can only slow packets down, so it inflates the upper tail of the
latency distribution by two orders of magnitude while leaving the lower tail
almost untouched (Section 4.4). An attacker who trains a classifier on lower-tail
statistics alone is essentially unaffected by the defence. Where prior evaluations
report a single accuracy number, this result shows *why* that number can be null
even when the defence is measurably changing the underlying distribution — the
attacker is not defeated, it is redirected to the part of the distribution the
defence does not reach.

## 5.4 Limitations

**Timing and resource utilisation, not electrical power.** The proposal was
framed around power analysis; this implementation measures execution time and CPU
utilisation. Intel RAPL energy counters, the software proxy for electrical power
draw, are masked inside VirtualBox guests (confirmed by `preflight.py` on every
run, Section 4.7), so a genuine power-domain replication was not possible on this
hardware. The result is best read as evidence about a resource-utilisation side
channel one abstraction layer above true DPA, not as a power-analysis result
itself.

**Virtualised, not bare-metal.** All measurements were taken inside a VirtualBox
guest. Hypervisor scheduling, even with core pinning applied, introduces jitter
that a bare-metal deployment would not have; the true signal-to-noise ratio on
native hardware could differ in either direction.

**Loopback, not a physical network path.** Probing over loopback was necessary to
keep the `nftables` chain traversal synchronous with the sender (Section 3.5), but this
means the result does not directly generalise to a firewall filtering traffic
arriving over a real NIC, where the softirq handling the packet may run on a
different core from the observer's timing loop.

**Synthetic ACL structure.** The 256-rule "deep" configuration models chain
length with individually generated filler rules of uniform, minimal cost. Real
enterprise rule sets mix rule types of varying per-rule cost (stateful matches,
address-set lookups), which this design does not capture.

**Single host, single hardware generation.** All four runs were collected on one
laptop. The magnitude of both the leak (Section 4.2) and the defence's effect (Section 4.5) may
be specific to this CPU's cache and scheduling characteristics.

**A Python-level timing floor.** The probe and the classifier's feature extractor
both run in CPython, whose per-call interpreter overhead (~1 µs) is a non-trivial
fraction of the shallow-configuration latency (~1 µs). Batching (Section 3.5) was used to
manage this, but a native implementation would have a lower and more stable
measurement floor.

## 5.5 Recommendations

Algorithmic noise injection is worth deploying only where an attacker's
observation budget is independently bounded — for example, behind connection or
rate limiting that caps how many timed samples an adversary can collect before
being throttled or detected. Deployed without such a bound, this evaluation shows
the defence is a delay, not a barrier: given enough batches, the defended and
undefended curves converge (Section 4.5).

Where a genuine floor-level guarantee is required, the tail-inflation result
(Section 4.4) points to a specific design correction. An additive-noise defence cannot
raise the *minimum* achievable latency in a given configuration, only its upper
tail; a constant-time or padded-to-fixed-minimum policy-evaluation design would
instead raise the floor itself, closing exactly the channel the low-tail attacker
in Section 4.4 exploits. The two approaches are complementary rather than competing:
noise injection raises the cost of prolonged observation, and a raised floor
removes the low-tail escape route.

Evaluations of this class of defence should report an observation-budget curve
and a trace-multiplication factor alongside any single accuracy figure, and
should report tail latency (p95 or higher) alongside the median cost. Either
number reported alone systematically favours the defence.

## 5.6 Reflection

The most useful methodological lesson from this project was operational rather
than statistical: `noise_cpu_s`, the CPU-overhead measurement underpinning Section 4.6,
initially read as zero throughout the first collection run. The cause was
`getrusage(RUSAGE_CHILDREN)`, which only accounts for CPU time of children that
have already been reaped — and the noise injector, by design, is a long-lived
worker pool that is never reaped mid-run. The fix was to read `/proc/<pid>/stat`
for the live worker processes directly; every run predating the fix was discarded
and recollected. The result was correct in the sense that the pipeline reported
what it was actually asked to measure — nothing was fabricated — but the
underlying measurement was silently wrong until checked against an independent
source. Given the timeline again, I would validate every new instrumentation
channel against a known-nonzero synthetic case before trusting it on real data,
rather than after.

The second lesson was about the defence's own placement (Section 3.7, Section 4.5): the
noise-cpus default excludes the victim's own core, which produces a defence that
runs, consumes CPU, and does precisely nothing to the metric it is meant to
protect. Finding this only by comparing cross-core and same-core runs side by
side suggests that any future noise-injection defence should include an explicit,
automated check that the injector and the victim are contending for the same
resource, rather than trusting a command-line default.
