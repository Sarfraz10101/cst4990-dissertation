# Abstract

*Final. Matches the submitted dissertation (`CST4990_Dissertation_Masood_final.docx`).
Front matter, excluded from the 8,000-word main-body count.*

Kernel packet filters leak configuration information to unprivileged, co-located
observers through a resource-consumption side channel: on the loopback path,
Linux evaluates the `nftables` `INPUT` chain synchronously in the sender's own
execution context, so `sendto()` latency reveals rule-chain depth and verdict.
This dissertation asks whether algorithmic noise injection is an effective
defence against a machine-learning adversary exploiting that leak.

An experimental harness collected 2,000 trials per run across four balanced
firewall configurations, under Poisson-timed and reactive noise injectors at two
core placements, with randomised interleaving, grouped cross-validation, and
shuffled-label controls. Without the defence, random forest and logistic
regression classifiers recover configuration well above chance (balanced
accuracy 0.79 to 0.91), driven by a near-perfectly separable rule-depth axis.
With the defence active, the single-shot accuracy reduction is not
statistically significant in any of eight run-by-model combinations tested.

An observation-budget sweep shows why: under the most effective configuration,
a defended attacker needs roughly twice as many observations to match an
undefended one, with that advantage eroding as the budget grows. A tail-quantile
analysis explains the null single-shot result: the additive noise inflates the
upper tail of the latency distribution by up to two orders of magnitude while
leaving the lower tail almost untouched, so a lower-tail-only attacker is barely
affected. The defence's cost is similarly asymmetric: median latency rose under
3%, but p95 latency rose by up to 431.9% and CPU consumption by up to 4017%.

These results reproduce, on a kernel firewall rather than cryptographic
hardware, Chari et al.'s (1999) prediction that noise-based countermeasures
raise observation cost without removing the leak. The methodological
contribution is demonstrating that a single accuracy figure cannot distinguish
a defence that delays an attacker from one that does nothing, and that noise
injection should be evaluated as a rate-limiting control, not a mitigation.
