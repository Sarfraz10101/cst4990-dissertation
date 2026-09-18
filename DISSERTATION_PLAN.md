# Dissertation plan, CST4990

Built from `CST4990-Dissertation-Template.docx`, the module handbook's School
rules, and the examiners' rubric. Word budgets are allocated against the rubric
criteria, so effort follows marks.

You write the prose. This file tells you what each section has to establish, and
which generated artefact supplies the evidence.

---

## 1. Binding constraints

These come from the handbook, section 10.2, which states School rules apply
**instead of** the template's own formatting advice. Where the two disagree, the
handbook wins.

| Rule | Value |
|---|---|
| Main body length | **8,000 words ±10%** (7,200 to 8,800) |
| Main body pages | **Max 50 pages**, Ch1 → final chapter. Over = **−5 marks** |
| Font | **Calibri 12** |
| Line spacing | **1.5** |
| Margins | **≥2 cm** all four sides |
| Justification | **Left-justified**, not full-justified |
| Excluded from limits | Front matter, abstract, references, appendices |
| Appendix must contain | Project outline **and** risk assessment |
| References | Harvard |

**Weighting, do not lose sight of this:** the dissertation is **60%**. The Viva
Voce on **21 to 25 September** is **40%**, and you must reach 40% on *both* to pass
the module. Budget real time for the presentation; it is worth two thirds of
what the entire written dissertation is worth.

---

## 2. The argument the dissertation makes

Everything should serve one thesis. Based on the pipeline's behaviour, the
finding will most likely be:

> Algorithmic noise injection raises the *observation cost* of a firewall
> configuration side-channel attack by a measurable factor, but does not
> eliminate the leak. Given sufficient observation budget the attacker recovers
> most of its accuracy, while the defence imposes a persistent latency and CPU
> penalty. Noise injection is therefore a rate-limiting control, not a
> mitigation, and evaluating it with a single accuracy figure overstates it.

That is a **strong** result, not a disappointing one. It reproduces Chari et
al.'s (1999) theoretical prediction about noise-based countermeasures on a
modern kernel firewall, and the methodological point, that single-number
evaluations mislead, is your originality claim.

Confirm the shape against real data before committing. If your measured curve
shows no recovery, the thesis inverts to "the defence holds within the tested
budget", which is equally publishable. Either way you have a dissertation.

---

## 3. Word budget

| Chapter | Words | Rubric criteria served |
|---|---:|---|
| Abstract *(front matter, excluded)* | ~500 | Abstract |
| 1. Introduction | 1,000 | Introduction & Overview; Problem Definition |
| 2. Literature Review | 1,800 | Literature Review |
| 3. Methodology / Research Design | 1,600 | Methodology / Research Design |
| 4. Results & Analysis | 1,600 | Data Results & Analysis |
| 5. Discussion & Critical Evaluation | 1,400 | Discussion, Critical Evaluation & Recommendations |
| 6. Conclusions & Further Work | 600 | Conclusion; Originality & Contributions |
| **Main body total** | **8,000** | |

Chapters 2 to 5 carry roughly two thirds of the marks between them. Do not let
Chapter 1 sprawl.

---

## 4. Chapter-by-chapter

### Front matter
Title page · Abstract · Declaration · Acknowledgements · Table of Contents ·
List of Tables · List of Figures

The **Declaration** in the template explicitly covers *"nor fabricated,
falsified or embellished data"*. You are signing that. Two consequences: the
fabricated reference must be gone, and `data/synth_*.csv` must never appear as a
result. Label it as a pipeline test fixture wherever it is mentioned.

The **Abstract** is ~500 words, one page maximum, and the rubric wants subject,
aims, approach, and conclusions. Write it last. `results/STATS_SUMMARY.md`
generates a draft headline sentence with the confidence interval already in it.

---

### Chapter 1, Introduction *(1,000 words)*

| Section | Words | Content |
|---|---:|---|
| 1.1 Background and motivation | 250 | Kernel packet filtering in zero-trust architectures; why configuration secrecy matters |
| 1.2 Problem definition | 250 | Resource-consumption signals leak firewall state to a co-located observer. Cite Ristenpart et al. (2009) for the co-tenancy setting |
| 1.3 Aim and objectives | 200 | Lift from the proposal; keep the three objectives verbatim so the marker can trace them |
| 1.4 Research questions | 150 | RQ1 accuracy reduction; RQ2 overhead. State the chance baseline (25%) here |
| 1.5 Scope and limitations | 100 | **Timing/resource channel, not electrical power.** RAPL energy counters are masked inside VirtualBox guests. Say this plainly on page one |
| 1.6 Dissertation structure | 50 | One sentence per chapter |

The rubric scores Problem Definition separately from Introduction & Overview, so
give Section 1.2 its own visible heading. Distinction-level wording is *"scope is
comprehensive and well justified"*, Section 1.5 is where you earn that, by naming the
limitation before an examiner does.

---

### Chapter 2, Literature Review *(1,800 words)*

| Section | Words | Content |
|---|---:|---|
| 2.1 Physical side-channel analysis | 350 | Kocher et al. (1999) DPA; Genkin et al. (2015, 2016) on commodity PCs |
| 2.2 Noise and masking countermeasures | 400 | **Chari et al. (1999)**, the theoretical core. Noise multiplies required traces; it does not remove the leak. Your results test this claim |
| 2.3 Side channels in virtualised co-tenancy | 350 | Ristenpart et al. (2009) and later cache/timing work |
| 2.4 Machine learning as the attacker model | 350 | Why a classifier is a credible adversary; evaluation pitfalls (leakage, imbalance) |
| 2.5 Kernel packet filtering and ACL cost | 200 | nftables/netfilter traversal cost; why depth is observable |
| 2.6 Research gap | 150 | Noise injection is well studied on crypto primitives, thinly on *kernel policy enforcement*, and rarely evaluated against observation budget |

The rubric penalises description over evaluation. For every source, add a
sentence on what it means *for your design*, that converts a summary into
critical engagement. Section 2.2 must set up the prediction your Chapter 4 tests;
that link is what makes the review load-bearing rather than decorative.

Verified citations are in `REFERENCES.md`. **Check every additional source
against DBLP by exact title before it enters the document.**

---

### Chapter 3, Methodology *(1,600 words)*

| Section | Words | Content | Source |
|---|---:|---|---|
| 3.1 Research approach | 150 | Quantitative experimental; isolated lab; no human data | proposal |
| 3.2 Threat model | 200 | Unprivileged co-located observer; what it can and cannot see | `README.md` Section 1 |
| 3.3 Experimental environment | 200 | Host CPU, guest VM spec, kernel, nft version, core pinning | `run*.meta.json` |
| 3.4 Firewall configurations | 200 | The 4 classes; why filler rules are individual rather than a set | `firewall.py` |
| 3.5 Measurement design | 300 | Loopback synchronous INPUT evaluation; batching to lift SNR; warm-up exclusion | `collect.py` |
| 3.6 The defence | 200 | Processes not threads (GIL); Poisson and reactive modes; gated not respawned | `noise.py` |
| 3.7 Experimental controls | 200 | Randomised interleaving; core pinning; shuffled-label control; trial-level aggregation | `README.md` Section 9 |
| 3.8 Analysis procedure | 150 | Features, CV, balanced accuracy, bootstrap CIs, permutation test | `attack.py`, `stats.py` |

Section 3.7 is where Distinction marks live. The rubric rewards a *"well-reasoned"*
design, and each control exists because a specific artefact would otherwise
have faked your result, say which. Justify the 250-trial sample size against
the proposal's 25 explicitly, giving the confusion-matrix reason.

---

### Chapter 4, Results & Analysis *(1,600 words)*

| Section | Words | Content | Source |
|---|---:|---|---|
| 4.1 Dataset summary | 150 | Trials per cell, batches, packets, collection duration | `run*.meta.json` |
| 4.2 Signal characterisation | 250 | Latency by configuration; is the leak present at all? | `snr_check.py` output |
| 4.3 Attacker accuracy, defence inactive | 250 | Balanced accuracy, CI, confusion matrix, feature importances | `rq1_accuracy_ci.csv`, `confusion_*_noise_off.csv` |
| 4.4 Attacker accuracy, defence active | 250 | Same, plus the reduction and its CI | `rq1_reduction.csv` |
| 4.5 **Observation-budget curve** | 350 | Accuracy vs batches for both conditions; trace-multiplication factor | `figure_sweep_curve.csv`, `trace_multiplication.csv` |
| 4.6 Cost of the defence | 250 | CPU seconds; median **and p95** latency increase | `rq2_overhead.csv` |
| 4.7 Validity checks | 100 | Shuffled-label controls at chance; null-data check | `accuracy.csv` |

Section 4.5 is the centrepiece, it is the only section that can answer *"to what
mathematical extent"* rather than "yes/no". Make it your largest figure.

Report **p95 latency alongside the median**. The tail is what a real operator
feels, and it moves far more than the mean.

Present, do not interpret. Interpretation is Chapter 5.

---

### Chapter 5, Discussion & Critical Evaluation *(1,400 words)*

| Section | Words | Content |
|---|---:|---|
| 5.1 Answering RQ1 | 250 | The reduction, its CI, and its collapse as budget grows |
| 5.2 Answering RQ2 | 200 | Cost in CPU and latency; is the trade acceptable? |
| 5.3 Relation to prior work | 250 | Does the curve match Chari et al.'s prediction? This is the payoff of Section 2.2 |
| 5.4 Limitations | 300 | Timing not electrical power; VM not bare metal; loopback not NIC; synthetic ACLs; single host; Python-level timing floor |
| 5.5 Recommendations | 250 | Where noise injection is and is not worth deploying; pair it with constant-time policy evaluation |
| 5.6 Reflection | 150 | What you would do differently |

Section 5.4 is the highest-leverage section in the dissertation. The rubric's
Distinction band rewards *"strong critical"* evaluation, and an examiner will
find these limitations whether or not you list them. Listing them first, with
the reason each was unavoidable, converts a weakness into evidence of judgement.

Section 5.5 must not be generic. "Use noise injection only where the adversary's
observation budget is bounded, for example behind rate limiting, because
unbounded observation defeats it" is a real recommendation. "Organisations
should consider security" is not.

---

### Chapter 6, Conclusions & Further Work *(600 words)*

| Section | Words | Content |
|---|---:|---|
| 6.1 Conclusions | 250 | Answer both RQs in one paragraph each. No new material |
| 6.2 Contributions | 200 | The dataset; the harness; the budget-curve evaluation method; the empirical trace-multiplication figure |
| 6.3 Further work | 150 | Bare-metal RAPL replication; eBPF/XDP; constant-time policy evaluation; host-side observer |

The rubric scores **Originality & Contributions** as its own criterion, so Section 6.2
needs its own heading. Your strongest claim is methodological: evaluating a
noise defence against *observation budget* rather than a single accuracy number.

---

### Back matter
References (Harvard) · Appendix A: Project outline *(required)* · Appendix B:
Risk assessment *(required)* · Appendix C: Source code listing · Appendix D:
Run metadata · Appendix E: Ethics screening form

Appendices A and B are mandatory per handbook Section 10.2. They are outside the page
limit, so there is no reason to skimp.

---

## 5. Schedule, verified against the actual CST4990 handbook

**Revised 29 Aug 2026.** `CST4990 Module Handbook-4.pdf` (read in full, Section 7 and
Section 17.2) confirms the real hard dates: dissertation submission via Turnitin on My
Learning is **23:59, Friday 18 September**, and the Viva Voce is **21 to 25
September**. The earlier "7 Sept" plan was a self-imposed target, not the
module deadline, kept below as the date you re-contact your supervisor with a
working draft, since you have gone quiet since proposal approval and want to
show something real rather than send a status update.

The handbook also matters for two things this plan didn't account for before:

- Your supervisor **can only comment on the table of contents and one selected
  chapter**, and the handbook asks you to **allow at least 3 weeks** for that
  turnaround. Sending it 7 Sept gives closer to 11 days before the 18 Sept
  deadline, short of 3 weeks, but far better than sending nothing.
- Every formatting rule already in this plan is confirmed verbatim by the
  handbook: ≤50 main-body pages (Ch1→final chapter, **5-mark penalty** if
  exceeded), 8,000 words ±10%, 2cm minimum margins, left-justified, 1.5
  spacing, Calibri 12, and the project outline + risk assessment required in
  the appendix.

Done already: the harness (14 modules), the figure renderer, all five
appendices, the viva pack, all six chapter drafts, the reference list, and a
fully assembled, rendered, bug-checked `.docx`.

| Date | Work | Output | Status |
|---|---|---|---|
| ~~21 to 23 Aug~~ | ~~VM to 4 vCPU; provision; `preflight.py`; `snr_check.py`~~ | preflight READY, AUC 1.000 | **Done** |
| ~~24 to 27 Aug~~ | ~~Full runs; attack, sweep, stats~~ | 4 runs, `results/run01` to `run04` | **Done** |
| ~~28 Aug~~ | ~~Draft all 6 chapters; verify Ch2 citations against DBLP~~ | 6 chapter drafts | **Done** |
| ~~29 Aug~~ | ~~Assemble full docx; fix rendering bugs; table captions; continuity check~~ | Reviewed, bug-fixed `.docx` | **Done** |
| **30 to 31 Aug** | Your own final read-through of the assembled docx | Confirmed-clean draft | |
| **1 to 6 Sept** | Polish: page numbers in List of Tables/Figures, final word/page count, any content gaps you flag | Submission-quality draft | |
| **Sun 7 Sept** | **Send working draft to supervisor** (ToC + one chapter, per handbook Section 10.2), also start viva prep in parallel | Supervisor review clock starts | |
| **8 to 14 Sept** | Incorporate supervisor feedback on the reviewed chapter; continue viva rehearsal | Revised draft | |
| **15 to 17 Sept** | Turnitin check; final proofread | Originality-checked, final draft | |
| **Fri 18 Sept, 23:59** | **Submit via Turnitin on My Learning** | | |
| 19 to 20 Sept | Finish slides + rehearse from `VIVA_PACK.md` | Slides + demo | |
| 21 to 25 Sept | **Viva Voce (40%)** | | |

This is materially less rushed than the version of this plan built on 28 Aug, there is real slack now. Use it for supervisor feedback and viva rehearsal
rather than compressing further.

Two things the real data changed, which the original chapter plan predates:

- **No significant single-shot reduction.** All eight run x model reduction CIs
  cross zero. Section 4.3/Section 4.4 report that; the argument moves to Section 4.5's budget curve,
  which strengthens rather than weakens the thesis in Section 2, a single accuracy
  figure genuinely does mislead here, and now you can show it rather than say it.
- **A fifth control appeared: noise placement** (README Section 9). The injector must
  share the victim's core or it does nothing. Section 3.6 and Section 3.7 both need a paragraph,
  and it is the strongest "what would you do differently" answer for Section 5.6.

Two things the data changed, which the chapter plan above predates:

- **No significant single-shot reduction.** All eight run x model reduction CIs
  cross zero. Section 4.3/Section 4.4 report that; the argument moves to Section 4.5's budget curve,
  which strengthens rather than weakens the thesis in Section 2, a single accuracy
  figure genuinely does mislead here, and now you can show it rather than say it.
- **A fifth control appeared: noise placement** (README Section 9). The injector must
  share the victim's core or it does nothing. Section 3.6 and Section 3.7 both need a paragraph,
  and it is the strongest "what would you do differently" answer for Section 5.6.

**If the schedule slips:** cut Chapter 2 to 1,400 words and Chapter 5 to 1,100
before you cut anything from Chapters 3 or 4. Methodology and Results are where
an empirical dissertation is won.

---

## 6. Viva preparation, 40% of the module

**Full pack: `VIVA_PACK.md`.** It has the ten-slide structure with speaking times
and a cut order, the three-minute live demo script with a failure playbook, a
question bank grouped by what each question is really testing, a cram sheet of the
five numbers to memorise, and a three-day rehearsal plan.

Start it on 19 Sept at the latest. These four questions are the ones your design
invites, and they are the spine of the pack:

1. **"You call this power analysis. Did you measure power?"** No, timing and
   resource utilisation. RAPL is masked in VirtualBox guests. Have Section 1.5 ready, and
   `preflight.py`'s RAPL check as evidence rather than assertion.
2. **"Your accuracy only drops 5 points. Does the defence work?"** It raises
   observation cost roughly N-fold without removing the leak. Show the sweep
   curve; this is your strongest moment.
3. **"How do you know the classifier isn't learning an artefact?"** Shuffled-label
   controls at chance, randomised interleaving, trial-level aggregation, null-data
   validation. Have `accuracy.csv` open.
4. **"Why 250 trials and not the 25 you proposed?"** Confusion matrix on 4 classes.
   Explain why you exceeded rather than met the proposal.

The sharpest question is not in that list, and `VIVA_PACK.md` Section 4.2 answers it:
*your attacker already runs code on the firewall host, so why do they need a side
channel?* Prepare that one before the four above.

A live demo of `snr_check.py` is worth more than any slide. It runs in thirty
seconds and it shows the leak existing in real time.
