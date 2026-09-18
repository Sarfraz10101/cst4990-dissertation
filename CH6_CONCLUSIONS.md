# Chapter 6 — Conclusions & Further Work

*Draft. Word target 600.*

## 6.1 Conclusions

This dissertation set out to evaluate whether algorithmic noise injection is an
effective defence against resource-consumption side-channel analysis of kernel
firewall configuration. On RQ1, the answer is qualified rather than binary: across
eight run × model combinations, noise injection produced no statistically
significant reduction in single-shot attacker accuracy, with confidence intervals
on the reduction crossing zero in every case. Read only at a single observation
budget, the defence appears ineffective. The observation-budget curve constructed
to test this properly shows otherwise — under the most effective configuration
tested, the defended attacker required roughly twice the observation budget of the
undefended one to reach equivalent accuracy, with that advantage eroding as the
attacker was allowed to observe for longer. The defence is a rate-limiting
control on observation cost, not a mitigation of the underlying leak, and this
matches the theoretical prediction of Chari et al. (1999) for noise-based
countermeasures against power analysis — a prediction Masure, Dumas and Prouff
(2020) show still holds against modern deep-learning attackers, not only the
classical statistical distinguishers Chari et al. considered — reproduced here
on a different class of system. On RQ2, the defence's cost is real and asymmetric: median latency
inflation stayed under 3%, but tail (p95) latency rose by up to 431.9% and CPU
consumption by up to 4017%, depending on triggering mode and injector placement.

## 6.2 Contributions

This dissertation makes four contributions. First, an empirical dataset of eight
run × model accuracy measurements, four observation-budget sweep curves, and
paired overhead measurements, collected under controls (randomised interleaving,
grouped cross-validation, shuffled-label controls, core pinning) designed to rule
out the artefacts that commonly inflate reported accuracy in side-channel machine-
learning evaluations. Second, an experimental harness — firewall configuration
generation, noise injection in two triggering modes, deterministic and
byte-reproducible analysis — that can be re-run on new hardware or extended to new
defences. Third, a methodological argument, supported directly by the data: that a
single accuracy figure at one observation budget cannot distinguish a defence that
delays an attacker from one that does nothing, and that observation-budget curves
should be reported as standard practice for this class of defence. Fourth, an
empirical trace-multiplication figure and a mechanistic explanation for it —
additive noise inflates the upper tail of a latency distribution far more than its
floor, so a full-feature attacker is barely affected while a lower-tail-only
attacker is nearly defeated — which is a specific, actionable finding for anyone
designing rather than merely evaluating this class of defence.

## 6.3 Further work

Three extensions follow directly from the limitations in Section 5.4. A bare-metal
replication with working RAPL access would test whether the results hold in the
true electrical-power domain, rather than the timing/resource-utilisation domain
this dissertation was confined to inside a hypervisor. Reimplementing the packet
filter at the eBPF/XDP layer would test whether the same leak and the same
noise-injection defence behave the same way earlier in the network stack, before
traffic reaches `nftables`. Finally, evaluating a constant-time or padded-to-
fixed-minimum policy-evaluation design directly against the tail-inflation finding
in Section 4.4 would test the recommendation in Section 5.5: that raising the floor, not the
tail, is what an additive-noise defence structurally cannot do.
