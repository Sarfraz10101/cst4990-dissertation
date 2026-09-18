#!/usr/bin/env python3
"""Why the defence does not reduce single-shot accuracy: the low-tail channel.

    python tails.py --data ../data/run04_reactive_samecore.csv --out ../results/run04

All eight run x model reduction confidence intervals cross zero, which on its own
reads as "the defence did nothing". It is not. The defence works hard - p95
latency rises 149% in run04 and 432% in run03 - but it works on the wrong part of
the distribution.

Injected noise is *additive*. A competing burst can only ever make a send take
longer; nothing the injector does can make the victim's fastest packets faster.
So the upper quantiles inflate enormously while the lower ones barely move, and a
classifier that reads the lower quantiles is left with a nearly clean channel.
This module measures that in three ways:

1.  Raw quantile inflation, defended vs undefended, on the deep configurations.
2.  Where the random forest's importance mass moves between conditions.
3.  The decisive test - train on the low quantiles alone, then on the upper
    quantiles alone, and compare how much accuracy each loses to the defence.

Test 3 is the one to quote. If the low-tail classifier holds its accuracy while
the upper-tail classifier collapses toward chance, the null result in section 4.4
is explained rather than merely reported, and section 5.5 gets a concrete
recommendation: a noise defence must raise the *floor* of the timing
distribution, not its tail. Padding to a constant-time minimum would do that;
random bursts cannot.

Reads the raw trace because it needs per-packet quantiles, so it is slower than
the other analysis stages. Not part of run_analysis.sh for that reason - run it
once per trace when writing chapters 4 and 5.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score

sys.path.insert(0, str(Path(__file__).resolve().parent))

import features as F  # noqa: E402
from attack import build_models, evaluate  # noqa: E402

# The two feature groups the argument rests on. LOW is the part of the
# distribution additive noise cannot reach; UPPER is the part it floods. `mean`
# belongs with UPPER rather than in the middle because it is dominated by the
# inflated tail once bursts land - which is itself worth a sentence in 4.2.
LOW = ["q05", "q10", "q25"]
UPPER = ["q75", "q90", "q95", "mean"]
QUANTILES = [5, 10, 25, 50, 75, 90, 95]

SEED = 12345


def quantile_inflation(raw: pd.DataFrame) -> pd.DataFrame:
    """Per-quantile percentage change from defended vs undefended packets.

    Restricted to the deep configurations, matching the verdict-axis sweep: the
    shallow ones are separable from a single packet and would dilute the
    comparison with an effect the defence was never contesting.
    """
    deep = raw[raw["depth"] == "deep"]
    off = deep[deep["noise"] == 0]["ns_per_pkt"].to_numpy(float)
    on = deep[deep["noise"] == 1]["ns_per_pkt"].to_numpy(float)
    if off.size == 0 or on.size == 0:
        return pd.DataFrame()

    v_off = np.percentile(off, QUANTILES)
    v_on = np.percentile(on, QUANTILES)
    return pd.DataFrame({
        "quantile": [f"q{q:02d}" for q in QUANTILES],
        "ns_noise_off": np.round(v_off, 1),
        "ns_noise_on": np.round(v_on, 1),
        "pct_change": np.round((v_on - v_off) / v_off * 100, 2),
    })


def importance_shift(resdir: Path) -> pd.DataFrame:
    """How the forest's importance mass redistributes when the defence runs.

    Uses the already-generated per-condition importance files rather than
    refitting, so this cannot disagree with figure 5.
    """
    off_p = resdir / "feature_importance_noise_off.csv"
    on_p = resdir / "feature_importance_noise_on.csv"
    if not (off_p.exists() and on_p.exists()):
        return pd.DataFrame()

    off = pd.read_csv(off_p).set_index("feature")["importance"]
    on = pd.read_csv(on_p).set_index("feature")["importance"]
    rows = []
    for name, cols in (("low_tail", LOW), ("upper_tail", UPPER)):
        present = [c for c in cols if c in off.index and c in on.index]
        rows.append({
            "group": name,
            "features": " ".join(present),
            "importance_noise_off": round(float(off[present].sum()), 4),
            "importance_noise_on": round(float(on[present].sum()), 4),
            "change": round(float(on[present].sum() - off[present].sum()), 4),
        })
    return pd.DataFrame(rows)


def tail_ablation(raw: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    """The decisive test: how much accuracy each feature group loses to noise.

    Verdict axis (accept vs drop within the deep configurations, chance 0.5),
    because that is the axis with dynamic range - the four-class problem is
    already saturated by depth. Grouped CV on `trial_idx` throughout, so a
    trial's batches cannot straddle a fold.
    """
    trials = F.build(raw)
    deep = trials[trials["config"].str.endswith("deep")].copy()
    if deep.empty:
        return pd.DataFrame()
    deep["label"] = deep["config"].str.split("_").str[0]

    groups = [("low_tail", LOW), ("upper_tail", UPPER),
              ("all_features", F.feature_names())]
    rows = []
    for name, cols in groups:
        cols = [c for c in cols if c in deep.columns]
        scores = {}
        for cond, key in ((0, "noise_off"), (1, "noise_on")):
            sub = deep[deep["noise"] == cond]
            if sub.empty:
                scores[key] = float("nan")
                continue
            model = build_models(seed)["randomforest"]
            y_used, pred = evaluate(
                sub[cols].to_numpy(float), sub["label"].to_numpy(),
                sub["trial_idx"].to_numpy(), model, seed,
            )
            scores[key] = float(balanced_accuracy_score(y_used, pred))
        rows.append({
            "feature_group": name,
            "n_features": len(cols),
            "balanced_accuracy_noise_off": round(scores["noise_off"], 3),
            "balanced_accuracy_noise_on": round(scores["noise_on"], 3),
            "accuracy_lost_to_defence":
                round(scores["noise_off"] - scores["noise_on"], 3),
            "chance": 0.5,
        })
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True, help="collector CSV")
    ap.add_argument("--out", required=True, type=Path, help="results directory")
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    raw = F.load_raw(args.data)

    infl = quantile_inflation(raw)
    if not infl.empty:
        infl.to_csv(args.out / "tail_quantile_inflation.csv", index=False)
        print("--- what the defence actually moves (deep configs, per packet)")
        print(infl.to_string(index=False))
        print()

    shift = importance_shift(args.out)
    if not shift.empty:
        shift.to_csv(args.out / "tail_importance_shift.csv", index=False)
        print("--- where the forest's importance mass goes")
        print(shift.to_string(index=False))
        print()

    abl = tail_ablation(raw, args.seed)
    if not abl.empty:
        abl.to_csv(args.out / "tail_ablation.csv", index=False)
        print("--- the decisive test: accuracy lost to the defence, by group")
        print(abl.to_string(index=False))
        print()

        low = abl[abl["feature_group"] == "low_tail"]
        up = abl[abl["feature_group"] == "upper_tail"]
        if not low.empty and not up.empty:
            l_loss = float(low["accuracy_lost_to_defence"].iloc[0])
            u_loss = float(up["accuracy_lost_to_defence"].iloc[0])
            print(f"Low quantiles lose {l_loss:+.3f} balanced accuracy to the "
                  f"defence; upper quantiles lose {u_loss:+.3f}.")
            if u_loss > l_loss + 0.05:
                print("The defence floods the tail and leaves the floor "
                      "intact, so an attacker reading the low quantiles keeps "
                      "its channel. That is why section 4.4's reduction "
                      "intervals cross zero.")
            else:
                print("No clear tail asymmetry in this run. Check the "
                      "placement: if the injector never shared the victim's "
                      "core it had no mechanism to inflate any quantile "
                      "(README section 9), so there is no tail effect to find.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
