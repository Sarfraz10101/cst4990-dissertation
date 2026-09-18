# CST4990 — Algorithmic Power-Noise Injection Against Firewall Side-Channel Analysis

Experimental harness for the MSc dissertation. Everything here runs on one
laptop with no external network dependency and no human participants, matching
the Low-Risk ethics self-assessment.

**Where to look:**

| File | Contents |
|---|---|
| `DISSERTATION_PLAN.md` | Chapter plan, word budgets, the schedule to 18 September |
| `VIVA_PACK.md` | Slide structure, demo script, question bank — the viva is 40% |
| `APPENDICES.md` | Project outline, risk assessment, code manifest, ethics form |
| `REFERENCES.md` | Verified citations only |
| this file | The experiment itself |

---

## 1. What the experiment actually measures

**Threat model.** An unprivileged observer co-located with a packet-filtering
host tries to recover the firewall's configuration from resource-consumption
signals alone — without reading config files or receiving replies.

**The leak.** On the loopback path the Linux kernel evaluates the `input` hook
*synchronously in the sending process's context*. A `sendto()` call therefore
pays the cost of nftables chain traversal inline, and that cost scales with how
many rules are evaluated before a match. Rule depth and verdict both leak into
send latency.

**The secret to recover.** Which of four configurations is live:

| Config | Verdict | Rules before match |
|---|---|---|
| `accept_shallow` | accept | 0 |
| `accept_deep` | accept | 256 |
| `drop_shallow` | drop | 0 |
| `drop_deep` | drop | 256 |

Four balanced classes, so **chance accuracy = 25%**.

**The defence.** `noise.py` runs randomised CPU bursts in parallel processes,
injecting entropy into the execution footprint. Two modes: Poisson-timed, and
reactive (bursts when the nftables counter moves — the proposal's "whenever
security policies are triggered").

**The result.** Attacker accuracy with noise off vs on. A working defence drives
accuracy toward 25% at an acceptable CPU and latency cost.

```
        ┌──────────────── Lubuntu guest (victim) ────────────────┐
        │                                                        │
        │   collect.py ──sendto()──▶ [ nftables input chain ]     │
        │     (pinned vCPU 0)          256 rules │ verdict        │
        │        ▲                               ▼               │
        │        └──── ns/packet ───────  listener socket         │
        │                                                        │
        │   noise.py  ── 3 worker processes on vCPUs 1..3         │
        │               randomised bursts (the defence)           │
        └────────────────────────────────────────────────────────┘
                                  │
                            run.csv (tidy long)
                                  │
        features.py ─▶ attack.py ─▶ stats.py ─▶ sweep.py ─▶ figures.py
                                  │
                          STATS_SUMMARY.md + figures/
```

---

## 2. Honest scoping — read this before writing Chapter 3

The proposal is titled *power*-noise injection and cites Kocher et al.'s
differential power analysis. **This harness measures a timing / resource-
utilisation channel, not electrical power.** That distinction will be probed at
the viva, so state it deliberately rather than letting a marker find it:

- True DPA needs a shunt resistor and an oscilloscope, at nanosecond
  resolution per instruction.
- The software proxy is Intel RAPL (`/sys/class/powercap/.../energy_uj`), but
  **RAPL is masked inside VirtualBox and VMware guests**, so it is unavailable
  in this setup. Only a native Linux install would expose it.
- What *is* measurable is execution-time and CPU-utilisation footprint — the
  same category of physical side channel, one abstraction layer up.

Recommended framing: position the work as evaluating noise injection against
**resource-utilisation side-channel profiling in a virtualised co-tenancy
setting**, and cite DPA as the origin of the noise-injection countermeasure
rather than as the attack you reproduce. Then add a limitations paragraph
saying an electrical-power replication on bare metal is the natural next step.

This is a change of stated scope, so raise it with David Neilson at the first
showcase — with the harness running, so the constraint is demonstrated rather
than asserted. `snr_check.py` plus the RAPL path being absent in the guest makes
the case in under a minute. Until then it lives in §1.5 and §5.4 of the
dissertation, not in an email.

---

## 3. Setup

### Reconfigure the VM (host, VM powered off)

The VM is currently 1 vCPU / 2 GB. One core cannot host both the victim and a
parallel noise injector — the defence would merely time-slice the probe.

```powershell
$vbm = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
& $vbm modifyvm "Lubuntu-Beginner" --cpus 4 --memory 4096
& $vbm showvminfo "Lubuntu-Beginner" --machinereadable | Select-String '^(cpus|memory)='
```

Reversible: `--cpus 1 --memory 2048`.

### Pin the VM to P-cores (host, every session)

The host is an i9-13980HX: 24 cores / 32 logical — 8 P-cores (logical 0–15, two
SMT threads each) plus 16 E-cores (logical 16–31). A thread migrating between core
types produces a timing step far larger than the side-channel signal, so the
requirement is simply *stay on P-cores*.

```
launch_vm_pinned.bat        (double-click, or run from a normal shell)
```

It prints `PINNED CORRECTLY` when the VM process reports affinity 65535.

**Do not start the VM from the VirtualBox GUI's Start button** — it will run
unpinned, and you cannot fix it afterwards. Setting `ProcessorAffinity` on
`VirtualBoxVM.exe` fails with "Access is denied" *even from an elevated
PowerShell*: VirtualBox's hardened loader puts a restrictive DACL on the VM
process. This is not a privileges problem and no amount of admin will move it.

What works instead, with no elevation: pin **`VBoxSVC`** — the COM server that
spawns the VM — and let the VM inherit the mask at creation. That is what the
launcher does:

```powershell
(Get-Process VBoxSVC).ProcessorAffinity = [IntPtr]0xFFFF
VBoxManage startvm "Lubuntu-Beginner" --type gui
```

Verify by hand any time (no elevation needed to read it):

```powershell
Get-Process VirtualBoxVM | ForEach-Object { "$($_.Id) threads=$($_.Threads.Count) affinity=$($_.ProcessorAffinity)" }
```

The process with tens of threads is the VM; the one- and two-thread processes are
loader stubs. The VM must read **65535**.

All eight P-cores rather than four: `VirtualBoxVM` runs about 50 threads (one EMT
per vCPU, plus IO and display), and squeezing those onto 8 logical CPUs adds
scheduling contention of its own. Sixteen P-core threads for 4 vCPUs is
comfortable, and no E-core is ever eligible.

Affinity resets when the VM restarts. Record that you applied it — it is a
methodology control worth a paragraph.

### Get files in and out of the guest

The base image has no Guest Additions, so shared folders, drag-drop and clipboard
sharing are all unavailable. SSH over a NAT port forward needs none of them, works
in both directions, and gives you copy-paste into the guest:

```powershell
# host, once. 127.0.0.1 keeps the guest's SSH off the LAN. Survives restarts.
VBoxManage controlvm "Lubuntu-Beginner" natpf1 "ssh,tcp,127.0.0.1,2222,,22"
# undo: VBoxManage controlvm "Lubuntu-Beginner" natpf1 delete ssh
```

```bash
# guest console, once
sudo apt-get install -y openssh-server && sudo systemctl start ssh
```

```bash
# host: push the harness in, pull traces back out
scp -P 2222 -r ~/CST4990-dissertation <user>@127.0.0.1:~/
scp -P 2222 <user>@127.0.0.1:~/CST4990-dissertation/data/run01_poisson.csv ./data/
```

### Provision the guest

With the folder copied in (see above):

```bash
cd ~/CST4990-dissertation
bash setup_guest.sh --quiet
source ~/cst4990-venv/bin/activate
```

---

## 4. Run order

### Collection — in the guest, needs root

```bash
cd harness

# 1. Is this machine fit to collect on? ~15 s. Blocks on a 1-vCPU guest,
#    a stale ruleset, a busy port, or an injector that cannot run in parallel.
sudo -E python3 preflight.py --json ../data/preflight.json

# 2. Does the leak exist? ~30 s. Do not skip.
sudo -E python3 snr_check.py

# 3. Smoke-test the full pipeline. ~1 min.
sudo -E python3 collect.py --dry-run --out ../data/smoke.csv

# 4. Full run: 250 trials x 4 configs x 2 conditions = 2000 trials.
sudo -E python3 collect.py --pin 0 --out ../data/run01_poisson.csv
sudo -E python3 collect.py --pin 0 --noise-mode reactive \
                           --out ../data/run02_reactive.csv
```

`preflight.py` exits non-zero if anything would invalidate the run. Two of its
checks earn their place: **achieved parallelism** forks the same number of busy
processes the defence uses and measures the CPU time they actually got, so a
single-core guest is caught by measurement rather than inferred from `nproc`; and
the **RAPL check** records that energy counters are unavailable, which turns the
scoping claim in §2 into evidence.

Each run writes `run*.csv` plus `run*.meta.json` (kernel, CPU model, nft
version, clock resolution, every parameter) — that pair is your reproducibility
appendix.

### The four runs that exist (collected 26–27 Aug 2026)

| Run | Mode | Noise placement | Command |
|---|---|---|---|
| `run01_poisson` | Poisson | cross-core (1–3) | `--pin 0` |
| `run02_reactive` | reactive | cross-core (1–3) | `--pin 0 --noise-mode reactive` |
| `run03_poisson_samecore` | Poisson | same-core (0) | `--pin 0 --noise-cpus 0` |
| `run04_reactive_samecore` | reactive | same-core (0) | `--pin 0 --noise-cpus 0 --noise-mode reactive` |

Side-by-side numbers: `results/CONTRAST_placement.csv`, regenerated by
`python3 contrast.py`. See §9 for why placement is the variable that decides
whether the defence does anything at all.

### Analysis — runs anywhere, no root, no kernel access

Collect in the VM, analyse on the host if you prefer. One command does all five
stages:

```bash
bash run_analysis.sh ../data/run01_poisson.csv ../results/run01
```

Or step by step, which is what the script calls:

```bash
python3 attack.py  --data ../data/run01_poisson.csv --out ../results/run01
python3 stats.py   --data ../data/run01_poisson.csv --results ../results/run01
python3 sweep.py   --data ../data/run01_poisson.csv --out ../results/run01
python3 sweep.py   --data ../data/run01_poisson.csv --out ../results/run01 --target verdict
python3 figures.py --results ../results/run01
python3 contrast.py                       # cross-run table, after all four runs
```

**This is deterministic.** Every stage seeds explicitly (`--seed`, default
`config.RANDOM_SEED` for collection and 12345 for the bootstraps), so re-running
the pipeline on a stored trace reproduces its results *byte for byte* — verified
on run04, 27–28 Aug, across all nine result CSVs including both sweep curves and
both trace-multiplication tables. If a re-run ever differs, the trace or the code
changed; nothing in the analysis path is allowed to drift on its own. Worth
saying in the viva: "reproducible" here means the file hashes match, not that the
conclusions look similar.

Read `results/run01/STATS_SUMMARY.md` first — it is Chapter 4 in draft form.

### Pipeline validation on synthetic data

Before real data exists, prove the analysis can find an effect it is given and
reports chance when there is none:

```bash
python3 synth.py --out ../data/synth_noise.csv                 # realistic defence
python3 synth.py --out ../data/synth_null.csv --null           # no effect at all
bash run_analysis.sh ../data/synth_noise.csv ../results/synth_noise
bash run_analysis.sh ../data/synth_null.csv  ../results/synth_null
```

The null run must sit at 0.25 in both conditions. Anything higher is a bug in
the pipeline, not a discovery. **Synthetic output is a test fixture and must
never be reported as a result** — the declaration you sign covers fabricated
data. Keep it in `data/synth_*.csv` and `results/synth_*/` so it cannot be
confused with a real run.

---

## 5. Sample size

The proposal specified 50 trials (25 per condition). That cannot support a
confusion matrix: 25 samples spread over 4 classes is 6 per class, and the 95%
CI on accuracy would span most of the possible range.

The harness defaults to **250 trials per cell = 2000 total**, each containing 50
timed batches of 200 packets. That is still only minutes of wall-clock. Exceeding
a proposed minimum is straightforward to defend; falling short of one is not.
Say so explicitly in Chapter 3 and give this reason.

---

## 6. If the signal is weak

If `snr_check.py` reports AUC below ~0.65, escalate in this order — cheapest
first, and stop as soon as the signal is usable:

1. **Raise `PACKETS_PER_BATCH`** (200 → 800) in `config.py`. Amortises Python
   interpreter overhead further. Costs nothing but time.
2. **Raise `DEEP_DEPTH`** (256 → 1024 or 4096). More traversal per packet. Note
   that very long chains are also *more* realistic for enterprise ACLs.
3. **Make each rule more expensive** — swap the `udp dport N drop` filler for
   expressions with real per-rule cost, e.g. `ct state`, `meta skuid`, or a
   payload string match. Justify it as modelling stateful enterprise policy.
4. **Move the hot loop to C** and call it via `ctypes`, removing ~1 µs/call of
   interpreter overhead. Perhaps 40 lines.
5. **Switch to a throughput signal** — sustained packets/sec over a fixed window
   instead of per-packet latency. Coarser, but far more robust to jitter.
6. **Last resort:** if no configuration leak survives, that is *still a valid
   finding* ("nftables traversal cost is not observable at this abstraction
   layer"), and RQ2 — the overhead of the defence — remains fully measurable.
   The dissertation survives a null result on RQ1 if you frame it as one.

---

## 7. How this maps to your research questions

**RQ1 — extent to which noise injection lowers attacker classification
accuracy.** Balanced accuracy of the classifier on noise-off vs noise-on trials,
with bootstrap CIs and a permutation test against the 25% chance baseline.
Confusion matrices per condition.

**RQ2 — computational overhead of the defence.** Two independent measures from
the same dataset: `noise_cpu_s` (CPU seconds the injector consumed per trial,
via `RUSAGE_CHILDREN`) and the inflation in `ns_per_pkt` between conditions,
which is the latency cost paid by legitimate traffic.

One dataset answers both. That is deliberate.

**A single accuracy figure cannot answer RQ1 properly**, which is why
`sweep.py` exists. Two very different defences produce the same headline number:

- one that **defeats** the attacker — accuracy stays near chance however long
  they observe;
- one that only **delays** them — accuracy climbs back as the observation budget
  grows, because zero-mean noise averages away while a deterministic signal does
  not.

The sweep separates these by re-running the attack at 1, 2, 3, 5, … 50 batches
per trial and reporting the **trace-multiplication factor**: how many more
batches the defended attacker needs to reach the same accuracy. Chari et al.
(1999) predicted the second outcome for noise countermeasures. If your curve
recovers, you have reproduced a known theoretical result on your own system —
a finding, not a failure. That is the answer to *"to what mathematical extent"*.

**Sweep the verdict axis, not the 4-class axis.** `sweep.py --target config`
(the default) saturates on this system: chain depth is separable from roughly a
single packet, so the 4-class curve opens at 0.717 — already past the 0.581
half-way target — and the factor collapses to 1.0 by construction. The accuracy
floor is also ~0.5, not 0.25, because perfect depth recovery plus a coin-flip on
verdict already scores half. Shrinking `PACKETS_PER_BATCH` does not fix this
(tested at 20: still opens at 0.76).

`--target verdict` restricts to the deep configs and asks only accept vs drop
(chance 0.5) — the axis `snr_check.py` reports as marginal, AUC ~0.65, and the
only axis where noise has room to act. It writes `*_verdict.csv` alongside the
4-class outputs rather than replacing them. Report both: the 4-class curve
saturating is itself evidence that depth leaks far more strongly than verdict.
`figures.py` renders both without being asked — `fig3_sweep_curve.png` for the
4-class panel and `fig3b_sweep_curve_verdict.png` for the verdict one, each
reading its chance level from its own CSV rather than from `config.py`, so the
0.5 panel is not mislabelled 0.25. The saturated panel prints its saturation on
the face of the plot instead of drawing a zero-length trace-multiplication arrow.

**Read the curve, not just the factor.** A factor is one crossing of one target
line, so on a non-monotonic curve it is fragile. run03's 2.5x rests on a curve
whose mean off/on gap is +0.004 and which steps backwards 3 times out of 8 —
that factor is noise. run04's 2.0x sits on a mean gap of +0.061 peaking at
+0.144, with clean separation from batch 2 to 12 and recovery by 50. Quote the
mean and maximum gap next to the factor; run04 is the honest §4.5 figure.

---

## 8. Files

| File | Purpose |
|---|---|
| `harness/config.py` | Every tunable, in one place, for Chapter 3 to quote |
| `harness/firewall.py` | nftables ruleset generation, atomic apply, teardown |
| `harness/noise.py` | The defence — multiprocess randomised bursts |
| `harness/collect.py` | Trace collector, randomised interleaved schedule |
| `harness/snr_check.py` | 30-second answer to "does the leak exist?" |
| `harness/preflight.py` | 16 readiness gates run immediately before a collection |
| `harness/features.py` | Trace → one feature vector per trial (19 features) |
| `harness/attack.py` | The attacker: logistic regression + random forest, grouped CV, shuffled-label control |
| `harness/stats.py` | Bootstrap CIs, permutation test, RQ2 overhead → `STATS_SUMMARY.md` |
| `harness/sweep.py` | Observation-budget curve and trace-multiplication factor |
| `harness/figures.py` | Renders the seven dissertation figures as PNG, plus draft captions |
| `harness/contrast.py` | Cross-run 2x2 table: placement x mode, with mean gap next to TMF |
| `harness/synth.py` | Synthetic fixture for validating the pipeline — **not a result** |
| `harness/run_analysis.sh` | Runs attack → stats → sweep (both axes) → figures in order |
| `setup_guest.sh` | Guest provisioning |
| `data/` | Traces and run metadata |
| `results/` | Analysis output, one subdirectory per run |

### What lands in `results/<run>/`

| Output | Feeds |
|---|---|
| `STATS_SUMMARY.md` | Chapter 4 — read this first |
| `rq1_accuracy_ci.csv` | §4.3, §4.4 — accuracy with CIs and p-values |
| `rq1_reduction.csv` | §5.1 — the reduction and its CI |
| `figure_sweep_curve.csv`, `trace_multiplication.csv` | §4.5 — the centrepiece |
| `rq2_overhead.csv` | §4.6, §5.2 — CPU and latency cost |
| `confusion_*.csv`, `per_class_*.csv` | §4.3, §4.4 — which configs confuse |
| `feature_importance_*.csv` | §4.2 — which statistic carries the leak |
| `accuracy.csv` | §4.7 — includes the shuffled-label controls |
| `figures/*.png` | Chapters 4 and 5 |

---

## 9. Five controls that decide whether your results are real

**Noise placement — the injector must share the core it is defending.**
`--noise-cpus` defaults to *every vCPU except* `--pin` (`collect.py:209`), so
`--pin 0` alone puts the victim on vCPU 0 and the injector on 1–3. The two never
contend, and the defence cannot perturb the very execution footprint it is
supposed to mask: run01/run02 (cross-core) show a mean sweep-curve gap of +0.017
and +0.001, i.e. nothing. Re-running with `--noise-cpus 0` — injector *on* the
victim's core — is what produces an effect: run04 reaches a +0.144 accuracy gap
at 5 batches and a 2.0x trace-multiplication factor.

Keep both placements. The contrast is a finding in its own right: noise
injection only works if it contends for the resource the attacker is measuring,
which is the mechanism Chari et al. (1999) assume and which a co-tenancy
deployment does not automatically provide. Cross-core is the honest
"misconfigured defence" baseline; do not quietly discard it.

**Interleaving.** `build_schedule()` shuffles all 2000 trials so conditions are
randomly ordered in time. Collecting all noise-off trials then all noise-on
trials would let CPU thermal drift alone separate the conditions at high
accuracy — a pure artefact. Interleaving is why the result means something.

**Trial-level aggregation and grouped CV.** Folds are split by *trial*, never by
batch. The 50 batches within one trial share a thermal and scheduling state;
shuffling them across the train/test boundary leaks the label and inflates
accuracy toward 100%. `features.py` aggregates to one row per trial, and
`attack.py` uses `StratifiedGroupKFold` keyed on `trial_idx` whenever it works
at batch level. This is the single most common way side-channel ML papers
overstate their results — and an examiner who knows the field will ask.

**Shuffled-label control on every fit.** `attack.py` refits each model with
permuted labels and reports both scores side by side in `accuracy.csv`. If the
control is not at ~0.25, the pipeline is leaking and the real score is
meaningless. Quote both numbers in §4.7; it costs two sentences and pre-empts
the hardest question you can be asked.

**No instrumentation in the feature set.** `noise_cpu_s`, `victim_user_s` and
`victim_sys_s` are carried through for RQ2 but are excluded from the predictors
(`features.EXCLUDED_FROM_FEATURES`). They are things *you* can measure, not
things a co-located observer can see; feeding them to the classifier would
inflate accuracy through measurement leakage rather than a real side channel.
Features derive from `ns_per_pkt` alone.
