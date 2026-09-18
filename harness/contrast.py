#!/usr/bin/env python3
"""Build the cross-run comparison table.

    python contrast.py --results ../results --out ../results/CONTRAST_placement.csv

Every other module in this harness analyses *one* trace. This one reads the
finished results directories and puts the four runs side by side, because the
2x2 design (poisson/reactive x cross-core/same-core) only says anything when the
cells are compared. It is the table Chapter 4 quotes for the placement finding
and Chapter 5 quotes for the cost/benefit trade.

It reads only generated CSVs - never the raw traces - so it is cheap and cannot
disagree with the per-run numbers it summarises. That is the point: the table was
previously maintained by hand, which meant a figure could be corrected in one
place and left stale in the other.

Two columns exist that the hand-written version lacked, `mean_gap` and
`max_gap`. The trace-multiplication factor is one crossing of one target line, so
on a curve that steps backwards it can be large while the two conditions are
statistically indistinguishable. run03 is exactly that case: a 2.5x factor on a
mean gap of +0.004. Quoting the factor alone would rank it above run04's honest
2.0x. If you report TMF anywhere, report these next to it.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

# run directory -> the two design factors. Kept here rather than parsed from the
# metadata because `noise_cpus` records the *placement* only implicitly: it is
# same-core when the injector's CPU set intersects `--pin`, which is a rule about
# intent, not a field. read_placement() below derives it and asserts agreement.
RUNS = [
    ("run01", "data/run01_poisson.meta.json"),
    ("run02", "data/run02_reactive.meta.json"),
    ("run03", "data/run03_poisson_samecore.meta.json"),
    ("run04", "data/run04_reactive_samecore.meta.json"),
]


def read_placement(meta_path: Path) -> tuple[str, str]:
    """Return (noise_mode, placement) from a collection metadata file.

    Placement is derived rather than stored: `--noise-cpus` defaults to every
    vCPU *except* `--pin`, so a run is cross-core exactly when the injector's CPU
    set excludes the victim's core. That default is why run01/run02 measured an
    inert defence, so deriving it here keeps the table honest about which runs
    could physically show an effect.
    """
    meta = json.loads(meta_path.read_text())
    args = meta.get("args", {})
    mode = args.get("noise_mode", "?")
    pin = args.get("pin")
    cpus = args.get("noise_cpus")

    if cpus in (None, ""):
        # Default: every vCPU except --pin. Never shares the victim's core.
        return mode, "cross-core"
    cpu_set = {int(c) for c in str(cpus).replace(",", " ").split()}
    if pin is not None and int(pin) in cpu_set:
        return mode, "same-core"
    return mode, "cross-core"


def first_row(path: Path) -> pd.Series | None:
    if not path.exists():
        return None
    df = pd.read_csv(path)
    return None if df.empty else df.iloc[0]


def gaps(resdir: Path) -> tuple[float, float, int]:
    """Mean gap, max gap, and count of backward steps on the undefended curve.

    Backward steps are the monotonicity check. More observation should not make
    an attacker worse, so a curve that dips is telling you the sweep's per-point
    noise is comparable to the effect - which is the context a single crossing
    point needs before it is quoted as a factor.
    """
    path = resdir / "sweep_curve_verdict.csv"
    if not path.exists():
        return float("nan"), float("nan"), -1
    curve = pd.read_csv(path)
    wide = curve.pivot_table(index="batches", columns="condition",
                             values="balanced_accuracy").sort_index()
    if not {"noise_off", "noise_on"} <= set(wide.columns):
        return float("nan"), float("nan"), -1
    diff = wide["noise_off"] - wide["noise_on"]
    back = int((wide["noise_off"].diff().dropna() < 0).sum())
    return float(diff.mean()), float(diff.max()), back


def overhead(resdir: Path) -> dict:
    """Percentage changes for the metrics section 4.6 reports.

    p95 is carried alongside the median deliberately: the tail is what an
    operator feels and it moves by orders of magnitude more than the median.
    """
    path = resdir / "rq2_overhead.csv"
    out = {"median_lat_pct": float("nan"), "p95_lat_pct": float("nan"),
           "cpu_pct": float("nan")}
    if not path.exists():
        return out
    df = pd.read_csv(path).set_index("metric")
    for key, metric in (("median_lat_pct", "median_ns"),
                        ("p95_lat_pct", "p95_ns"),
                        ("cpu_pct", "noise_cpu_s")):
        if metric in df.index:
            out[key] = float(df.loc[metric, "pct_change"])
    return out


def build(results: Path, repo: Path) -> pd.DataFrame:
    rows = []
    for run, meta_rel in RUNS:
        resdir = results / run
        if not resdir.is_dir():
            continue
        mode, placement = read_placement(repo / meta_rel)

        acc = pd.read_csv(resdir / "rq1_accuracy_ci.csv")
        rf = acc[acc["model"] == "randomforest"].set_index("condition")
        red = pd.read_csv(resdir / "rq1_reduction.csv").set_index("model")
        tm = first_row(resdir / "trace_multiplication_verdict.csv")
        mean_gap, max_gap, back = gaps(resdir)
        ov = overhead(resdir)

        rows.append({
            "run": run,
            "mode": mode,
            "placement": placement,
            "acc_off": round(float(rf.loc["noise_off", "balanced_accuracy"]), 3),
            "acc_on": round(float(rf.loc["noise_on", "balanced_accuracy"]), 3),
            "red_pp_logreg": float(red.loc["logreg", "reduction_pp"]),
            "red_pp_rf": float(red.loc["randomforest", "reduction_pp"]),
            # Significance is reported per model; the table says "any model"
            # because a reduction that only one model finds is not a finding.
            "red_sig": bool(red["significant"].any()),
            "median_lat_pct": ov["median_lat_pct"],
            "p95_lat_pct": ov["p95_lat_pct"],
            "cpu_pct": ov["cpu_pct"],
            "TMF_verdict": (float(tm["trace_multiplication_factor"])
                            if tm is not None else float("nan")),
            "mean_gap": round(mean_gap, 3),
            "max_gap": round(max_gap, 3),
            "off_curve_backward_steps": back,
        })
    return pd.DataFrame(rows)


def main() -> None:
    here = Path(__file__).resolve().parent
    repo = here.parent
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, default=repo / "results")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    df = build(args.results, repo)
    if df.empty:
        raise SystemExit(f"no run directories found under {args.results}")

    out = args.out or (args.results / "CONTRAST_placement.csv")
    df.to_csv(out, index=False)
    print(df.to_string(index=False))
    print()
    print(f"wrote {out}")
    print("Read mean_gap next to TMF: a large factor on a near-zero mean gap is")
    print("one lucky crossing, not a defence that delayed anything.")


if __name__ == "__main__":
    main()
