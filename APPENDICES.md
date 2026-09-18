# Appendices — CST4990

Handbook 10.2 requires **the project outline and a risk assessment** in the
appendix. Appendices A and B below satisfy that. C, D and E are optional but
cheap: appendices sit outside the 8,000-word count and the 50-page limit, so
there is no reason to leave evidence out.

Everything here is drafted to be pasted into the dissertation and edited. Fill
the bracketed placeholders once the real runs exist.

---

# Appendix A — Project outline

## A.1 Project identification

| | |
|---|---|
| Title | An Empirical Evaluation of Algorithmic Power-Noise Injection: Utilizing Machine Learning to Defend Enterprise Firewall Kernels Against Side-Channel Energy Analysis Attacks |
| Student | Sarfraz Masood, M01085839 |
| Programme | MSc Cyber Security and Emerging Threats |
| Module | CST4990 Postgraduate Individual Project |
| Supervisor | David Neilson |
| Institution | Middlesex University, Hendon |
| Submission | 23:59, 18 September 2026 (dissertation, 60%) — confirmed against `CST4990 Module Handbook-4.pdf` §7/§17.2, 29 Aug 2026 |
| Viva Voce | 21–25 September 2026 (40%) — confirmed, same source |

## A.2 Aim

To determine empirically whether algorithmic noise injection reduces the ability
of a machine-learning adversary to infer the configuration of a kernel packet
filter from resource-consumption side channels, and to quantify the
computational cost that defence imposes.

## A.3 Objectives

1. Construct a repeatable measurement harness that captures the
   resource-consumption footprint of a Linux `nftables` firewall under a set of
   controlled configurations.
2. Implement a randomised noise-injection defence and collect matched datasets
   with the defence inactive and active.
3. Train and evaluate a machine-learning adversary against both datasets, and
   quantify both the change in its accuracy and the overhead the defence
   imposes.

## A.4 Research questions

- **RQ1** — To what extent does algorithmic noise injection reduce a
  machine-learning adversary's accuracy in classifying firewall configuration
  from resource-consumption traces?
- **RQ2** — What computational overhead does the defence impose, in CPU time and
  in the latency paid by legitimate traffic?

Both are answered from a single dataset, against a chance baseline of 25% (four
balanced classes).

## A.5 Deliverables

| Deliverable | Form | Status |
|---|---|---|
| Measurement harness | 12 Python modules + 2 shell scripts, ~3,200 lines | Complete |
| Trace dataset | `data/run*.csv` + `run*.meta.json` (4 runs) | Complete — collected 26–27 Aug 2026 |
| Attacker evaluation | `results/*/accuracy.csv`, confusion matrices | Complete |
| Statistical analysis | `results/*/STATS_SUMMARY.md` | Complete |
| Observation-budget analysis | `trace_multiplication.csv`, sweep figure | Complete |
| Figures | 7 print-ready PNGs per run | Complete |
| Dissertation | 8,000 words ±10% | Complete — all 6 chapters drafted and formatted, within word-count target |
| Viva presentation | Slides + live demonstration | Not started — scheduled 19–20 Sept per `VIVA_PACK.md` |

## A.6 Schedule: as proposed, and as executed

The proposal's schedule is reproduced verbatim on the left. Report the variance
honestly — examiners credit accurate reflection over a schedule retro-fitted to
look perfect, and §5.6 of the dissertation asks for exactly this.

| Proposal | Planned work | What actually happened |
|---|---|---|
| Weeks 1–3 (late May) | Finalise proposal, complete ethics screening, submit to supervisor | As planned. Ethics screening self-assessment completed; supervisor confirmation outstanding |
| Weeks 4–6 (June) | Literature review | *[record actual]* |
| Weeks 7–9 (July) | Build Python measurement suite | *[record actual]* |
| Weeks 10–12 (August) | Code the randomised workload script; run trials | Harness built and validated. **Trial count raised from 50 to 2,000** — see §A.7. Sample-size reasoning in Chapter 3 |
| Weeks 13–15 (late Aug) | Process metrics in Excel; attacker simulation | **Analysis moved from Excel to scripted Python.** Bootstrap CIs, permutation tests and grouped cross-validation are not practical in a spreadsheet, and a script is reproducible where a workbook is not. CSV outputs remain Excel-openable |
| Weeks 16–17 (early Sept) | Write Results, Discussion, Critical Evaluation | Planned 27 Aug – 7 Sept |
| Week 18 (mid Sept) | Proofread, format to Calibri 12 / 1.5 spacing, submit via Turnitin | Planned 11–17 Sept, submitting one day early |
| Weeks 19–20 (late Sept) | Prepare Viva Voce presentation | Planned 19–20 Sept |

### Deviations from the proposal, and why

Three substantive changes. All are defensible; none should be discovered by an
examiner rather than declared.

1. **Measurement channel.** The proposal describes power analysis and cites
   Kocher et al. (1999). The work measures a **timing and resource-utilisation**
   channel instead. Intel RAPL energy counters — the software proxy for power on
   a commodity machine — are masked inside VirtualBox and VMware guests, and
   true differential power analysis needs a shunt resistor and an oscilloscope.
   The channel measured is the same category of physical side channel one
   abstraction layer up. Declared in §1.5 and §5.4.
2. **Sample size raised from 50 trials to 2,000.** Fifty trials across four
   classes leaves twelve samples per class, which cannot support a confusion
   matrix or a usable confidence interval. The full run is still only minutes of
   wall-clock. Exceeding a proposed minimum is straightforward to defend.
3. **Evaluation method extended.** The proposal asked to what *mathematical
   extent* the defence reduces attacker accuracy. A single accuracy figure
   cannot answer that, because it cannot distinguish a defence that defeats an
   attacker from one that merely makes them collect more data. An
   observation-budget sweep was added, reporting a trace-multiplication factor.
   This is the project's main methodological contribution.

## A.7 Milestones

| # | Milestone | Target | Evidence |
|---|---|---|---|
| M1 | Proposal and ethics screening submitted | May 2026 | Proposal document |
| M2 | Harness complete and self-validating | Aug 2026 | `harness/`, synthetic fixture runs |
| M3 | Analysis pipeline validated against known ground truth | Aug 2026 | `results/synth_*/` — planted effect recovered, null data at chance |
| M4 | Side channel confirmed on real hardware | 26 Aug 2026 | `snr_check.py` output, AUC 1.000 (depth), 0.65 (verdict) |
| M5 | Full dataset collected | 27 Aug 2026 | `data/run01`–`run04` + metadata |
| M6 | All six chapters drafted | 28 Aug 2026 | `CH1_INTRODUCTION.md`–`CH6_CONCLUSIONS.md` |
| M7 | Complete formatted draft | 29 Aug 2026 | Assembled, rendered, bug-checked `.docx` |
| M8 | Draft sent to supervisor (ToC + one chapter, per handbook §10.2) | 7 Sept 2026 | Email/upload to David Neilson |
| M9 | Submitted | 18 Sept 2026, 23:59 | Turnitin receipt |
| M10 | Viva Voce | 21–25 Sept 2026 | Presentation |

**M3 deserves a sentence in Chapter 3.** The analysis pipeline was validated
against synthetic data with known planted parameters *before* any real data
existed: it recovers an effect that is present, returns chance when none is
planted, and all shuffled-label controls sit at chance. A pipeline that has
never been tested against a known answer cannot be trusted with an unknown one.

---

# Appendix B — Risk assessment

## B.1 Scope of assessment

All experimental work runs on the researcher's own laptop, inside a local
virtual machine, on the loopback interface. Specifically:

- **No human participants**, no personal data, no special-category data.
- **No third-party, institutional or production systems** are probed, scanned or
  attacked. The only host involved is the researcher's own.
- **No network traffic leaves the machine.** Probe packets are sent to
  `127.0.0.1`.
- **No physical laboratory hazards** — no hardware modification, no electrical
  instrumentation, no chemical or biological materials.

This is why the ethics self-assessment returns Low Risk (Appendix E).

Ratings below are Likelihood × Impact on a Low / Medium / High scale, assessed
*after* the stated mitigation.

## B.2 Technical and validity risks

These are the risks that could invalidate the results rather than delay them,
and they are the ones an examiner will care about.

| # | Risk | L | I | Mitigation | Contingency |
|---|---|---|---|---|---|
| T1 | Side channel too weak to detect; RQ1 unanswerable | M | H | `snr_check.py` gates every run with a 30-second go/no-go before committing to a full collection | Six-step escalation ladder (README §6): more packets per batch, deeper chains, costlier rules, C hot loop, throughput signal. If nothing works, report a null result on RQ1 — RQ2 remains fully measurable |
| T2 | RAPL energy counters unavailable in the guest, so power cannot be measured | H | M | Confirmed absent early; scope restated as a timing / resource-utilisation channel | Declared in §1.5 and §5.4; bare-metal replication named as further work |
| T3 | Thermal drift separates the conditions instead of the firewall doing so | H | H | All 2,000 trials randomly **interleaved** by `build_schedule()`, so condition is not correlated with time | Within-trial slope is captured as a feature, making drift visible rather than silent |
| T4 | Thread migration between P-cores and E-cores swamps the signal | H | H | Collector pinned with `--pin`; noise workers confined to other vCPUs; host VM process restricted to the eight P-cores (0xFFFF). **VirtualBox's hardened loader denies `ProcessorAffinity` on `VirtualBoxVM.exe` even to an elevated shell**, so the mask is applied to `VBoxSVC` and inherited by the VM at creation — `launch_vm_pinned.ps1` does this and verifies it | Verified per session: the VM process must report affinity 65535. Report the CPU topology and the mask in Chapter 3 |
| T5 | Cross-validation leakage inflates accuracy toward 100% | M | H | Features aggregated to one row per trial; `StratifiedGroupKFold` grouped on `trial_idx` in batch mode; shuffled-label control on every fit | Any control scoring above chance blocks reporting until the cause is found — `run_analysis.sh` exits non-zero on this |
| T6 | Instrumentation columns leak into the feature set and fake a side channel | L | H | `features.EXCLUDED_FROM_FEATURES` bars the CPU-accounting columns; predictors derive from `ns_per_pkt` alone | Feature list printed in Chapter 3 so the exclusion is auditable |
| T7 | A headline statistic computed from noise (e.g. a trace-multiplication factor on chance-level data) | M | H | Both `sweep.py` and `stats.py` refuse to report ratios unless the undefended attacker clears chance — by bootstrap CI and by a 3-standard-error threshold respectively | Verified against the null fixture: the guard fires and the factor is reported as undefined |
| T8 | ICMP port-unreachable replies dominate the measurement | L | H | A real listener is bound on the probe port, so accepted packets are delivered rather than provoking an ICMP reply | Documented in `collect.py`; `send_errors` recorded per batch |
| T9 | Single-host results do not generalise | H | M | Not mitigable within scope | Stated plainly as a limitation in §5.4; generalisation named as further work |

## B.3 Project delivery risks

| # | Risk | L | I | Mitigation | Contingency |
|---|---|---|---|---|---|
| D1 | Guest VM has one vCPU, so the defence time-slices the victim instead of running beside it | H | H | Reconfigure to 4 vCPU / 4 GB before collection; command and reversal recorded in README §3 | 1-vCPU results would be reported as invalid, not published |
| D2 | Insufficient time — 28 days from harness completion to deadline | M | H | Day-by-day schedule in `DISSERTATION_PLAN.md` §5; submit 17 Sept, one day early | Documented cut order: Chapter 2 to 1,400 words and Chapter 5 to 1,100 before touching Chapters 3 or 4 |
| D3 | Data loss — laptop failure, VM corruption | L | H | Traces are small CSVs, copied out of the guest after each run. **Action outstanding: the project directory is not yet under version control** — run `git init && git add -A && git commit` before collection begins | Collection is minutes of wall-clock and fully re-runnable from a fixed seed |
| D4 | Exceeding the 50-page main-body limit — an automatic 5-mark penalty | M | M | Word and page count checked at the 11–13 Sept formatting pass, not at the end | Move tables and code listings into appendices, which are outside the limit |
| D5 | Unverifiable or incorrect citation | L | H | Every reference checked against DBLP by exact title; one fabricated citation found and removed, with the evidence recorded in `REFERENCES.md` | No source enters the document without verification |
| D6 | Synthetic test data mistaken for a real result | L | H | Fixture output confined to `data/synth_*.csv` and `results/synth_*/`; labelled as a fixture in every file that touches it | The signed declaration covers fabricated data — this risk is treated as high-impact by design |
| D7 | Illness, or supervisor unavailable at a decision point | M | M | Buffer days 14–16 Sept; no task depends on a same-day response | Reorder writing; scope questions carry a stated default assumption rather than blocking |
| D8 | Turnitin similarity flag | L | M | All prose original; quotations marked and cited; generated tables clearly attributed to the harness | Turnitin check at 14–16 Sept, before submission, leaving time to revise |

## B.4 Health, safety and environmental

| # | Risk | L | I | Mitigation |
|---|---|---|---|---|
| H1 | Sustained multi-core CPU load causing overheating or thermal throttling | M | L | Runs are minutes, not hours; laptop on a hard surface with clear vents; throttling would show up as within-trial slope and is monitored | 
| H2 | Display-screen equipment: eye strain, posture, repetitive strain over an intensive writing period | M | L | Regular breaks; standard DSE practice |
| H3 | Electrical safety | L | L | No hardware modification. **Note:** the shunt-resistor instrumentation that true DPA would need is deliberately out of scope, which removes an electrical-safety risk as well as a practical one |
| H4 | Environmental impact | L | L | Negligible — one laptop, minutes of compute, no travel |

No fieldwork, no lone working in hazardous locations, no travel.

## B.5 Legal and ethical risks

| # | Risk | L | I | Mitigation |
|---|---|---|---|---|
| E1 | Work construed as developing technology to breach security systems | L | H | See B.6 — this needs an explicit answer, not a blank box |
| E2 | Unauthorised access to systems not owned by the researcher | L | H | Target is the researcher's own VM on `127.0.0.1`. Nothing is scanned, probed or attacked beyond the local host |
| E3 | Damaging the host's own firewall configuration | M | M | `firewall.py` creates and deletes **only its own table** (`inet cst4990`) and never issues `nft flush ruleset`, which would wipe unrelated rules |
| E4 | Publishing a usable attack against deployed systems | L | M | The attack recovers a coarse configuration class on a synthetic ruleset in a lab; it is a measurement instrument for evaluating a defence, not a deployable tool. The defensive finding is the contribution |
| E5 | Personal data processing | L | H | None collected. Traces contain nanosecond timings and CPU counters only |

## B.6 The one ethics question this project has to answer properly

The screening form asks about *"development of technology intended to be used in
an illegal/harmful context **or to breach security systems**"*. For a project
whose title contains the word "Attacks", ticking **No** and moving on would look
careless. The answer is still No, and here is why — put this justification in
the dissertation, not just in the form:

- The **purpose is defensive**: the attacker is a measurement instrument built
  to evaluate a countermeasure. The research output is an evaluation of the
  defence, including the finding that it is weaker than a single accuracy figure
  suggests.
- The **target is the researcher's own isolated system**. No third-party,
  institutional or production system is involved at any point.
- **Nothing exploitable is produced.** There is no vulnerability disclosure, no
  exploit, no privilege escalation, no bypass of an access control. The attack
  recovers which of four synthetic rulesets is loaded on a machine the
  researcher already administers.
- This is **standard practice in the field**. Side-channel countermeasure
  evaluation requires implementing the attack; Kocher et al. (1999) and Chari et
  al. (1999) established the pattern.

If in any doubt, raise it with the supervisor at the confirmation stage. A
justified No is fine; an unexamined No is not.

## B.7 Data management

| Question | Answer |
|---|---|
| What data is collected? | Nanosecond timing measurements, CPU-time counters, and firewall configuration labels |
| Personal data? | None |
| Volume | Order of tens of MB of CSV |
| Where held | Researcher's own machine; a local git repository once initialised (see B.3 D3) |
| Retention | Retained to the end of the assessment period, including the viva |
| Sharing | Included in the submission as a reproducibility appendix; nothing restricted |
| Reproducibility | Fixed random seed (`RANDOM_SEED = 20260821`); every parameter written to `run*.meta.json` alongside each trace |

---

# Appendix C — Source code manifest

Total 3,591 lines across 14 Python modules plus 2 shell scripts and a PowerShell
host launcher (regenerated 28 Aug 2026 via `wc -l harness/*.py`). Listing the
whole harness in the appendix is legitimate but bulky; a manifest plus the two or
three modules that carry the methodological argument (`firewall.py`, `noise.py`,
`collect.py`) is usually the better use of a marker's attention.

| File | Lines | Role |
|---|---:|---|
| `harness/config.py` | 101 | Every experimental parameter, in one place |
| `harness/firewall.py` | 120 | nftables ruleset generation, atomic apply, safe teardown |
| `harness/noise.py` | 227 | The defence — multiprocess randomised CPU bursts |
| `harness/collect.py` | 289 | Trace collector, randomised interleaved schedule |
| `harness/snr_check.py` | 133 | 30-second go/no-go: does the leak exist? |
| `harness/preflight.py` | 548 | Pre-run readiness check: 16 environment and validity gates |
| `harness/features.py` | 148 | Trace → 19 features per trial |
| `harness/attack.py` | 235 | The adversary, with grouped CV and shuffled-label controls |
| `harness/stats.py` | 388 | Bootstrap CIs, permutation tests, overhead analysis |
| `harness/sweep.py` | 274 | Observation-budget curve, trace-multiplication factor |
| `harness/figures.py` | 558 | Print-ready figures |
| `harness/contrast.py` | 177 | Cross-run placement × mode table (§4.5) |
| `harness/tails.py` | 205 | Tail-quantile and tail-ablation analysis (§4.4b) |
| `harness/synth.py` | 188 | Synthetic fixture — pipeline validation, **not a result** |
| `harness/run_analysis.sh` | 115 | Pipeline runner with a control-check gate |
| `setup_guest.sh` | 73 | Guest provisioning |
| `launch_vm_pinned.ps1` + `.bat` | 84 | Host launcher that pins the VM to P-cores by VBoxSVC inheritance |

Regenerate the line counts before submitting: `wc -l harness/*.py`.

---

# Appendix D — Run metadata and reproducibility

Every collection writes `run*.meta.json` beside its trace. Reproduce the file
verbatim in this appendix — it is the difference between a claim of
reproducibility and evidence of it.

| Field | Why it matters |
|---|---|
| `started_utc` | Orders the runs; lets thermal state be reasoned about |
| `kernel` | nftables traversal cost is kernel-version dependent |
| `python` | Interpreter overhead is part of the measurement floor |
| `cpu_model`, `cpu_count` | The signal is a property of this microarchitecture |
| `nft_version` | Rule evaluation changes between releases |
| `clock_resolution_ns` | Bounds the smallest difference that could be detected at all |
| `args` | Exact invocation, including `--pin` and `--noise-mode` |
| `parameters` | Packets per batch, batches per trial, warm-up count, chain depths, noise worker count and burst rate, and the random seed |

Reproduction instructions:

```bash
# collection (guest, root)
sudo -E python3 collect.py --pin 0 --out ../data/run01_poisson.csv

# analysis (anywhere)
bash run_analysis.sh ../data/run01_poisson.csv ../results/run01
```

With `RANDOM_SEED` unchanged the trial *schedule* is identical between runs;
the timings themselves are not, because they are physical measurements.

---

# Appendix E — Research ethics screening

Reproduce the completed Section 2 form from the proposal. Two things still need
doing on it:

1. **The Yes/No column was left blank in the submitted proposal.** Every row
   needs an explicit **No** — the Low Risk conclusion only follows from
   answering *all* items. Section B.1 above justifies each one; B.6 covers the
   only row that needs argument rather than assertion.
2. **The supervisor's confirmation boxes and signature are outstanding.** The
   form's own wording is *"Your research supervisor will confirm this below"*,
   so this cannot be self-completed. Raise it at the first showcase.

Student declaration: signed Sarfraz Masood, 29 May 2026.

Answers, for transcription — every item **No**:

| Item | Answer |
|---|---|
| Animals or animal parts | No |
| Cell lines / cell culture / human tissue | No |
| Clinical audits or assessments | No |
| Conflict of interest or lack of impartiality | No |
| Data not freely available | No |
| Damage to artefacts, the environment, or significant risk to society | No |
| External organisation or government-commissioned research | No |
| Fieldwork | No |
| GMOs / gene therapy or DNA sequence data | No |
| Human participants — anonymous questionnaires | No |
| Human participants — identifiable | No |
| Illegal or harmful activities research | No — justification in B.6 |
| Permission required to access premises or participants | No |
| Personal data processing | No |
| Public works doctorates | No |
| Risk of physical or psychological harm | No |
| Security clearance required | No |
| Sensitive topics | No |

All items No ⇒ **Low Risk**; no Ethics Monitor application required, subject to
supervisor confirmation.
