# Viva Voce pack — CST4990

**40% of the module.** Same weight as roughly two-thirds of the dissertation,
prepared in a fraction of the time. This file is the preparation.

Viva window: **21–25 September 2026.** The dissertation goes in on 18 September,
so there are three clear days between submission and the earliest possible slot —
that is the rehearsal window, and it is enough only if the material below already
exists.

---

## 0. Confirm the format before you build slides

I do not know these, and guessing wrong wastes preparation:

- **Duration** — presentation length and question time
- **Whether slides are expected**, and whether they are submitted in advance
- **Whether a live demonstration is permitted** (this matters most — see §3)
- **Who is on the panel** — supervisor alone, or a second marker
- **Room and equipment** — will your laptop connect, or must it run on theirs

Ask at the first showcase. Everything below is built for the common shape,
roughly **15 minutes presenting, 15 minutes of questions**; if the real slot is
shorter, cut from §2 in the order marked.

---

## 1. The one thing to get right

Most viva marks are lost by describing what you built instead of arguing what it
shows. You have an argument. Lead with it, and return to it after every question:

> Noise injection did not remove the side channel. It multiplied the number of
> observations the attacker needed. That makes it a rate-limiting control, not a
> mitigation — and I can show the curve where the attacker recovers.

If you say nothing else all session, say that. It is the difference between a
project that ran an experiment and a project that has a finding.

Second-order point, ready when they push on whether the defence is worth it:

> The leak comes from linear chain traversal. nftables already supports sets and
> maps with near-constant-time lookup. Rewriting the ruleset that way removes the
> depth signal at no CPU cost, which is strictly better than burning three cores
> on noise. My evaluation is what shows noise to be the weaker option.

That answer demonstrates you understand your own result well enough to argue
against your own defence. Examiners reward that far more than advocacy.

---

## 2. Presentation structure

Fifteen minutes, ten slides. Times are speaking times. **Cut order if the slot is
shorter: slide 4, then slide 9, then halve slide 2.** Never cut 5, 6 or 7.

| # | Slide | Time | On the slide | What you say |
|---|---|---|---|---|
| 1 | Title | 0:20 | Title, name, M01085839, supervisor, module | Nothing beyond your name. Do not read the title aloud |
| 2 | The problem | 1:30 | A firewall evaluating rules in a linear chain; a co-located observer | A packet filter's work depends on its configuration. Work is observable. Therefore configuration is observable |
| 3 | Research questions | 1:00 | RQ1 and RQ2, chance baseline 25% | Two questions: does the defence reduce attacker accuracy, and what does it cost. Both from one dataset |
| 4 | Related work | 1:00 | Kocher et al. 1999; Chari et al. 1999 | Chari predicted noise multiplies traces rather than removing leaks. My contribution is testing that on a kernel packet filter |
| 5 | Method | 2:30 | The 4 configurations; interleaved schedule; pinning; the 4 controls | Spend the time here. Method is where the marks are |
| 6 | The leak exists | 2:00 | **fig1** latency by configuration | Point at the separation. This is the channel, before any machine learning |
| 7 | The finding | 3:00 | **fig3** the sweep curve | Your best slide. Walk the curve left to right. Name the trace-multiplication factor |
| 8 | The cost | 1:30 | **fig2** accuracy + controls, and the RQ2 overhead table | Accuracy fell by X points; it cost Y% median latency and Z CPU seconds per trial |
| 9 | Limitations | 1:00 | Four bullets, no hedging | Timing not power; single host; four-class proxy; co-located attacker |
| 10 | Conclusion | 0:40 | The one-sentence claim from §1 | Say it, stop, invite questions |

Notes that matter more than they look:

- **Slide 9 is a scoring slide, not an apology.** Naming your own limitations
  before the panel does converts their strongest questions into agreement. Say
  them flatly, do not soften them, do not explain them at length.
- **No slide should need you to say "you probably can't read this."** If it does,
  the slide is wrong.
- Have **fig4** (confusion matrices) and **fig5** (feature importance) as
  appendix slides after slide 10, ready to jump to.

---

## 3. Live demonstration

You told me you can only showcase work in person. Use that. A thirty-second
`snr_check.py` run that prints a real AUC does more for your credibility than any
slide, because it cannot be faked and it shows the system is genuinely working.

### The demo, in order

Have the VM **already booted, venv activated, and `cd harness` done** before you
start. Never do setup in front of a panel.

```bash
# 0. Prove the machine is fit for the experiment          (~15 s)
sudo -E python3 preflight.py

# 1. Prove the side channel exists, live                  (~30 s)
sudo -E python3 snr_check.py

# 2. Prove the defence runs and costs something           (~60 s)
sudo -E python3 collect.py --dry-run --out ../data/demo.csv

# 3. Show the analysis on the real dataset (pre-run)      (~40 s)
bash run_analysis.sh ../data/run04_reactive_samecore.csv ../results/demo
```

run04 is used here deliberately, not run01: it is the figure of record for the
whole dissertation (the 2.0× trace-multiplication factor, the tail-inflation
finding), so if a panel member asks to see the number behind any slide, this is
the run that produces it.

Total under three minutes. Say what each step proves *before* you run it, so a
slow command is anticipation rather than dead air.

### What each step buys you

| Step | The question it pre-empts |
|---|---|
| `preflight.py` | "How do you know the environment was controlled?" — it prints the controls, including achieved parallelism |
| `snr_check.py` | "How do you know there's a real channel and not a classifier artefact?" |
| `collect.py --dry-run` | "Did the defence actually run?" — the CPU accounting is right there |
| `run_analysis.sh` | "Is this reproducible?" — one command, and the control check passes at the end. If pressed, the stronger claim: re-running it on a stored trace reproduces all nine result CSVs **byte for byte**, because every stage seeds explicitly. Verified on run04. "Reproducible" means matching hashes, not similar-looking conclusions |
| `contrast.py` | "How do you know the 2.5x isn't just noise?" — the table prints mean gap beside the factor, and run03's is +0.004 |

### When it breaks

It will break, or be slower than at home. Have this ready:

- **Rehearse the whole demo at least three times**, including once on battery and
  once after a cold boot.
- **Record a screen capture of a clean run** and keep it on the same machine. If
  the live run fails, play the recording and keep talking. Say plainly that it is
  a recording.
- **Keep `results/run01/` fully populated** so every figure and CSV is available
  with no computation at all.
- If a command fails, **do not debug it in front of the panel**. One sentence —
  "that's the port still bound from the previous run, here's the recorded version"
  — then move on. Composure is being assessed; the bug is not.
- Never run the full 2,000-trial collection live. It takes minutes and it can only
  hurt you.

---

## 4. Question bank

Grouped by what they are really testing. The answers are yours to say in your own
words — memorising phrasing sounds worse than thinking aloud from a known
position.

### 4.1 The title problem — they will open here

**"You call this power analysis. Did you measure power?"**
No. I measured timing and resource utilisation. RAPL energy counters are masked
inside a VirtualBox guest, and true differential power analysis needs a shunt
resistor and an oscilloscope, which were out of scope. The channel I measured is
the same class of physical side channel one abstraction layer up, and §1.5 states
that before any result is presented. `preflight.py` prints the RAPL check, so the
unavailability is recorded evidence rather than a claim.

**"Then is your title accurate?"**
The title describes the defence — algorithmic power-noise injection — which is
what I implemented and evaluated. The measurement channel is narrower than the
title suggests, which is why the scope is restated in the introduction rather than
buried. If I were retitling it now I would say *resource-consumption side
channels*.

*Do not get defensive here.* Conceding a title is imprecise costs nothing.
Defending an inaccuracy costs a lot.

### 4.2 Threat model — the sharpest question in the set

**"Your attacker runs code on the firewall host. If they're already inside, why
do they need a side channel?"**

This is the strongest objection to the design, so answer it head-on rather than
waiting to be pushed:

- The model is a **co-located unprivileged observer**: a container, a low-privilege
  service account, or a co-tenant VM. They can execute code but cannot read
  `/etc/nftables.conf` or run `nft list ruleset`, both of which need root.
- What they gain is **reconnaissance without touching the policy**: which egress
  paths are permitted, and whether the ruleset is deep enough that a scan will be
  noticed. That is real value in a lateral-movement stage.
- Crucially, **it is invisible.** They never send a packet the firewall logs as
  refused. Configuration recovery by port scanning is detectable; this is not.
- **Honest limit:** an attacker measuring round-trip time from off-host is the
  more threatening version, and I did not test it. Loopback was necessary because
  the INPUT hook is evaluated synchronously in the sender's context there — on a
  real NIC, filtering moves into a softirq on another core and the signal is lost
  in scheduling noise. Remote timing is the obvious next experiment.

**"Isn't the four-class problem artificially easy?"**
Yes, deliberately. Four classes with a 25% floor is a proxy for configuration
recovery, chosen so that accuracy is interpretable and a confusion matrix is
readable. It establishes that the channel carries information about both verdict
and rule depth. Scaling to a realistic secret space is the natural extension, and
it would make the attacker's job harder, not easier — so my result is the
optimistic case for the attacker and the pessimistic case for the defence.

### 4.3 Validity — "how do you know it's real?"

**"How do you know the classifier isn't learning an artefact?"**
Four independent controls, and I can show each:

1. **Randomised interleaving** — all 2,000 trials shuffled, so condition is not
   correlated with time. Thermal or frequency drift cannot separate the classes.
2. **Trial-level aggregation with grouped cross-validation** —
   `StratifiedGroupKFold` grouped on `trial_idx`, so no two batches from the same
   trial land on opposite sides of a split.
3. **Shuffled-label controls** — the whole pipeline refitted on permuted labels
   must score at chance, and `run_analysis.sh` exits non-zero if it does not.
4. **No instrumentation in the feature set** — the CPU-accounting columns are
   excluded via `features.EXCLUDED_FROM_FEATURES`. If they were in there, the
   classifier could read "the defence was on" straight off the label.

**"How do you know your analysis code is correct?"**
I validated it against synthetic data with known planted parameters before any
real data existed. It recovers an effect that is planted, returns chance when
nothing is planted, and every shuffled-label control sits at chance. A pipeline
that has never been tested against a known answer cannot be trusted with an
unknown one.

**"What if you had found nothing?"**
Then RQ1 would be reported as a null result and RQ2 would stand on its own — the
overhead is measurable regardless. The escalation options are documented in README
§6, and `snr_check.py` exists specifically so that question is answered in thirty
seconds rather than after a full collection. The pipeline refuses to report a
trace-multiplication factor unless the undefended attacker clears chance by three
standard errors, so a null dataset cannot produce a confident-looking headline.

### 4.4 Statistics

**"Why balanced accuracy rather than accuracy?"**
The design is balanced, so they nearly coincide — but balanced accuracy is the
mean of per-class recall, so it cannot be inflated by a classifier that
over-predicts one class, and it has an interpretable floor at 1/K. That floor is
what the entire sweep analysis is measured against.

**"Why bootstrap intervals rather than a t-test?"**
Balanced accuracy has no clean closed-form sampling distribution, and the latency
distributions are right-skewed by scheduling spikes. Percentile bootstrap for the
accuracy intervals, Mann-Whitney U for the latency comparisons, Cohen's d for
effect size, and permutation tests with an add-one correction so no p-value is
ever reported as zero.

**"What does your p-value actually test?"**
Two different things, and I report both. The permutation test in `stats.py`
permutes the fitted predictions, testing whether predicted and true labels are
associated. The shuffled-label control in `attack.py` permutes labels *before*
cross-validation and refits everything, which rules out pipeline leakage. The
control is the stronger claim; the p-value quantifies the result.

**"Why 250 trials when you proposed 25?"**
Twenty-five per class cannot support a four-by-four confusion matrix or a usable
confidence interval. Two thousand trials is still only a few minutes of
wall-clock, so there was no reason to accept the weaker design. Exceeding a
proposed minimum is straightforward; falling short would not be.

### 4.5 The finding, and whether the defence is any good

**"Accuracy only dropped a few points. Does the defence work?"**
This is your best moment — go to fig3 and take your time.

It works in a narrow sense and fails in the sense an operator cares about. At a
fixed observation budget accuracy falls. But the defended curve climbs back
toward the undefended one as the budget grows: the noise is zero-mean, so
averaging over more observations recovers the signal. What the defence buys is a
trace-multiplication factor — the attacker needs N times more observation to
reach the same accuracy. That is rate limiting, not mitigation. Chari et al.
predicted exactly this for noise countermeasures in 1999; the contribution here is
measuring it on a kernel packet filter.

**"Would you deploy it?"**
No, not as configured. It spends three cores of CPU and a measurable latency
penalty to multiply attacker effort by a single-digit factor, and a patient
attacker just waits. I would fix the ruleset instead: the leak comes from linear
chain traversal, and nftables sets and maps give near-constant-time lookup, which
removes the depth signal at no CPU cost. Noise injection is worth deploying only
where the ruleset cannot be restructured and the attacker's observation window is
genuinely bounded.

**"So your project concludes your defence is a bad idea?"**
It concludes that this class of defence buys less than a single accuracy figure
implies, and it quantifies how much less. That is the useful result. A dissertation
that only reported the accuracy drop would have overstated the defence — the
observation-budget analysis is what stops that happening, and it is the part I
would defend hardest.

### 4.6 Ethics

**"You built an attack tool. Is that appropriate?"**
The purpose is defensive: the attacker is a measurement instrument for evaluating
a countermeasure, and the output is an evaluation, including the finding that the
countermeasure is weaker than it looks. The target is my own isolated VM on
loopback — no third-party or institutional system is involved. Nothing exploitable
is produced: there is no vulnerability disclosure, no privilege escalation, no
access-control bypass. Implementing the attack is standard practice in
side-channel countermeasure evaluation; Kocher and Chari both established that
pattern. Appendix B §B.6 sets out the reasoning.

### 4.7 Process and reflection

**"What went wrong?"**
Pick two real ones and be specific — vague answers here read as unreflective:

- The guest VM was provisioned with one vCPU, which would have made the defence
  time-slice the victim instead of running beside it. `preflight.py` now measures
  achieved parallelism directly rather than trusting `nproc`.
- The sweep script initially reported a confident trace-multiplication factor on
  data with no planted signal, because two curves wobbling around chance still
  cross an arbitrary target at different points. I added a three-standard-error
  gate; the guard now fires on null data and the factor is reported as undefined.

That second one is a good answer because it shows you found an integrity problem
in your own analysis and closed it.

**"What would you do differently?"**
Bare metal with real RAPL counters, so the power claim in the title is measured
rather than approximated. A remote timing attacker, which is the threatening
version of the threat model. And a constant-time ruleset as a comparison
defence — that would turn a single-defence evaluation into a comparison, which is
a stronger design.

**"What's the contribution?"**
The observation-budget methodology. Evaluating a noise countermeasure by accuracy
at a fixed budget cannot distinguish defeating an attacker from delaying one, and
those have opposite operational implications. Reporting a trace-multiplication
factor does distinguish them.

### 4.8 Questions where the answer is "I don't know"

Have these ready as clean admissions. A confident "I didn't test that, here is how
I would" scores better than an invented answer:

- Does it hold on bare metal with real energy counters? Untested.
- Does it hold across kernel versions or CPU microarchitectures? Untested, and
  chain traversal cost is kernel-version dependent.
- Does it hold for a remote attacker measuring RTT? Untested — and the honest
  expectation is that network jitter would need a much larger observation budget.
- What is the optimal noise rate? Not swept. I fixed the rate at 120 Hz per
  worker; a rate-versus-cost sweep is obvious further work.

---

## 5. Cram sheet — the five numbers to know cold

Filled in from `CH4_NUMBERS.md`, using **run04** (reactive, same-core) — the
figure of record for the whole dissertation. Memorise these; nothing damages a
viva faster than hunting through a spreadsheet for your own headline.

| | Value |
|---|---|
| Chance baseline (4-class) | 0.25 |
| Chance baseline (verdict axis, the one that matters for §4.5) | 0.5 |
| Undefended attacker accuracy (run04, 4-class) | 0.906 [0.888, 0.924] |
| Defended attacker accuracy (run04, 4-class) | 0.904 [0.886, 0.922] — **not a significant drop, CI crosses zero** |
| Trace-multiplication factor (run04, verdict axis) | **2.0×** |
| Mean sweep-curve gap (run04) | +0.061 balanced accuracy |
| Median latency cost (run04) | +2.95% |
| p95 latency cost (run04) | +148.5% |
| CPU cost (run04, relative) | +536% |
| CPU cost, absolute example (run01, illustrative only) | 0.0029 → 0.0167 CPU-s/trial |
| Number of trials | 2,000 per run (250 × 4 configs × 2 conditions), 4 runs total |

**The line to have ready if asked "so did it work?":** No significant single-shot
reduction (0.906 → 0.904), but the observation-budget curve shows a real 2.0×
trace-multiplication factor — the defence delays, it doesn't defeat.

Also know, without looking: why loopback, why processes rather than threads, why
interleaved ordering, what `EXCLUDED_FROM_FEATURES` prevents, and why noise
placement (same-core vs cross-core) matters — the cross-core runs (run01/run02)
show almost no effect (mean gap +0.017 and +0.001) because the injector never
contends with the victim.

---

## 6. Rehearsal checklist

Three days, in this order.

**Day 1 — build.** Slides from §2. Fill the cram sheet. Run the demo once end to
end and record it.

**Day 2 — rehearse.** Present out loud, timed, three times. Out loud matters: the
sentences that collapse are never the ones that collapse silently. Then have
someone ask you §4 out of order, and answer without notes.

**Day 3 — stress.** Demo on battery, after a cold boot. Answer the four questions
in §4.8 without flinching. Re-read your own limitations section. Sleep.

On the day: VM booted and venv active before you walk in, recording on the
desktop, `results/run01/` populated, figures open in a second window, one printed
copy of the cram sheet.

---

## 7. Two things to avoid

**Overclaiming.** Every number you present has a confidence interval and a scope
limit. Say "on this host, in this configuration" and you can defend everything you
said. Drop it and one question unravels the session.

**Reading the slides.** The panel can read. Your job is the argument between the
slides — which is why §1 is at the top of this file and not the bottom.
