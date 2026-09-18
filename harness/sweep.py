"""Observation-budget sweep: how much data does the attacker need?

    python sweep.py --data ../data/run01_poisson.csv --out ../results

This is the figure that answers RQ1's "to what mathematical extent". A single
accuracy number cannot distinguish two very different outcomes:

  * a defence that **defeats** the attacker - accuracy stays near chance no
    matter how long they observe;
  * a defence that merely **delays** the attacker - accuracy climbs back as the
    observation budget grows, because zero-mean noise averages away while the
    signal does not.

Chari et al. (1999) predicted the second outcome for noise-based countermeasures:
noise multiplies the number of traces an attack needs, it does not remove the
leak. If your curve shows recovery, you have reproduced a known theoretical
result on your own system - that is a finding worth a section, not a failure.

The headline number to extract is the **trace-multiplication factor**: how many
more batches the attacker needs, with the defence active, to reach the same
accuracy they reached without it.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score

import features as F
from attack import build_models, evaluate
from config import CHANCE_ACCURACY, PACKETS_PER_BATCH, RANDOM_SEED

DEFAULT_BUDGETS = (1, 2, 3, 5, 8, 12, 20, 32, 50)

# Two axes the budget curve can be swept along.
#
# "config" is the headline 4-class problem (chance 0.25). On this system it
# saturates: chain depth is separable from roughly a single packet, so the
# curve starts near its ceiling and there is no room left to measure a
# *delay*. Depth being that visible is a finding in itself, but it makes the
# 4-class factor uninformative.
#
# "verdict" restricts to the deep configurations and asks only accept vs drop
# (chance 0.5) - the axis snr_check.py reports as marginal (AUC ~0.65). That is
# precisely where a noise defence can plausibly act, so it is the axis with the
# dynamic range the trace-multiplication factor needs.
TARGETS = {
    "config": {
        "label": "config",
        "chance": CHANCE_ACCURACY,
        "filter": None,
        "suffix": "",
    },
    "verdict": {
        "label": "verdict",
        "chance": 0.5,
        "filter": lambda df: df[df["depth"] == "deep"],
        "suffix": "_verdict",
    },
}


def sweep(
    raw: pd.DataFrame,
    budgets: tuple[int, ...],
    model_name: str,
    seed: int,
    target: str = "config",
) -> pd.DataFrame:
    spec = TARGETS[target]
    model = build_models(seed)[model_name]
    if spec["filter"] is not None:
        raw = spec["filter"](raw)
    available = int(raw["batch_idx"].max()) + 1
    rows = []

    for budget in budgets:
        if budget > available:
            print(f"  skipping budget {budget}: only {available} batches collected")
            continue

        table = F.build(raw, max_batches=budget)
        names = F.feature_names()

        for noise_on in sorted(table["noise"].unique()):
            subset = table[table["noise"] == noise_on]
            X = subset[names].to_numpy(dtype=float)
            y = subset[spec["label"]].to_numpy()

            y_used, pred = evaluate(X, y, None, model, seed)
            bal = balanced_accuracy_score(y_used, pred)
            condition = "noise_on" if int(noise_on) == 1 else "noise_off"

            rows.append({
                "batches": budget,
                "packets_observed": budget * PACKETS_PER_BATCH,
                "condition": condition,
                "n_trials": len(y_used),
                "balanced_accuracy": round(bal, 4),
                "chance": spec["chance"],
            })
            print(f"  budget {budget:3d} batches  {condition:9s} "
                  f"balanced_acc = {bal:.4f}")

    return pd.DataFrame(rows)


def null_standard_error(n_trials: int, chance: float = CHANCE_ACCURACY) -> float:
    """Standard error of balanced accuracy under the null, K balanced classes.

    For K classes with n/K trials each, Var(balanced accuracy) reduces to
    p(1-p)/n with p = 1/K. Three of these is the bar the undefended attacker has
    to clear before "how much more observation does the defence force?" is a
    meaningful question at all - on chance-level data the curve still wobbles,
    and any two wobbles have a ratio.
    """
    if n_trials <= 0:
        return float("inf")
    return float(np.sqrt(chance * (1.0 - chance) / n_trials))


def trace_multiplication(curve: pd.DataFrame,
                         chance: float = CHANCE_ACCURACY) -> dict:
    """How many more batches does the defence force the attacker to collect?

    Defined at the accuracy halfway between chance and the undefended
    attacker's ceiling. If the defended attacker never reaches it within the
    collected range, the factor is reported as unbounded - which is the strong
    result for the defence.

    Guarded: if the *undefended* attacker never gets reliably above chance there
    is no leak to delay, and the factor is left undefined rather than computed
    from noise. Without this guard a dataset with no signal at all still yields
    a confident-looking multiplication factor, because both curves drift around
    chance and one crosses an arbitrary target before the other.
    """
    off = curve[curve["condition"] == "noise_off"].sort_values("batches")
    on = curve[curve["condition"] == "noise_on"].sort_values("batches")
    if off.empty or on.empty:
        return {}

    ceiling = float(off["balanced_accuracy"].max())
    n_trials = int(off["n_trials"].max()) if "n_trials" in off else 0
    se = null_standard_error(n_trials, chance)
    threshold = chance + 3.0 * se

    if ceiling < threshold:
        return {
            "undefended_ceiling": round(ceiling, 4),
            "chance": chance,
            "significance_threshold": round(threshold, 4),
            "undefended_above_chance": False,
            "target_accuracy": None,
            "batches_needed_noise_off": None,
            "batches_needed_noise_on": None,
            "trace_multiplication_factor": None,
            "defended_reached_target": None,
            "interpretation": (
                "undefended attacker never got reliably above chance - there is "
                "no leak to delay, so trace multiplication is undefined"
            ),
        }

    # Target: halfway between chance and the undefended attacker's ceiling.
    target = chance + 0.5 * (ceiling - chance)

    def first_reaching(df: pd.DataFrame) -> int | None:
        hit = df[df["balanced_accuracy"] >= target]
        return int(hit["batches"].iloc[0]) if not hit.empty else None

    b_off, b_on = first_reaching(off), first_reaching(on)
    return {
        "undefended_ceiling": round(ceiling, 4),
        "chance": chance,
        "significance_threshold": round(threshold, 4),
        "undefended_above_chance": True,
        "target_accuracy": round(target, 4),
        "batches_needed_noise_off": b_off,
        "batches_needed_noise_on": b_on,
        "trace_multiplication_factor": (
            round(b_on / b_off, 2) if b_off and b_on else None
        ),
        "defended_reached_target": b_on is not None,
        "interpretation": (
            "defence delays the attacker" if b_on
            else "defence defeats the attacker within the collected budget"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default="../results")
    ap.add_argument("--model", default="randomforest",
                    choices=("randomforest", "logreg"))
    ap.add_argument("--budgets", default=",".join(str(b) for b in DEFAULT_BUDGETS))
    ap.add_argument("--target", default="config", choices=tuple(TARGETS),
                    help="axis to sweep: 'config' = the 4-class problem "
                         "(chance 0.25); 'verdict' = accept vs drop within the "
                         "deep configs (chance 0.5), which is where the defence "
                         "has room to act")
    ap.add_argument("--seed", type=int, default=RANDOM_SEED)
    args = ap.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    spec = TARGETS[args.target]
    suffix = spec["suffix"]
    chance = spec["chance"]

    budgets = tuple(int(b) for b in args.budgets.split(","))
    raw = F.load_raw(args.data)
    if "batch_idx" not in raw.columns:
        print("error: dataset has no batch_idx column - cannot sweep")
        return 1
    if args.target == "verdict" and "depth" not in raw.columns:
        print("error: dataset has no depth column - cannot sweep verdict only")
        return 1

    print(f"sweeping {args.model} over budgets {budgets} "
          f"(target={args.target}, chance={chance})")
    curve = sweep(raw, budgets, args.model, args.seed, args.target)
    if curve.empty:
        print("error: no budgets were runnable")
        return 1

    curve.to_csv(outdir / f"sweep_curve{suffix}.csv", index=False)

    # Wide form, ready to select and chart directly in Excel.
    wide = curve.pivot(index="batches", columns="condition",
                       values="balanced_accuracy")
    wide["chance"] = chance
    wide.to_csv(outdir / f"figure_sweep_curve{suffix}.csv")

    tm = trace_multiplication(curve, chance)
    tm["target"] = args.target
    pd.DataFrame([tm]).to_csv(outdir / f"trace_multiplication{suffix}.csv",
                              index=False)

    print("\nlearning curve (balanced accuracy):")
    print(wide.to_string())
    print("\ntrace multiplication:")
    for k, v in tm.items():
        print(f"  {k:34s} {v}")

    if tm.get("undefended_above_chance") is False:
        print(f"\nThe undefended attacker never exceeded "
              f"{tm['significance_threshold']:.3f} (chance + 3 SE), so there is "
              f"no leak for the defence to delay and no trace-multiplication "
              f"factor to report. Either the channel is not present in this "
              f"dataset or the attacker cannot see it - check snr_check.py and "
              f"README section 6 before writing anything up.")
    elif tm.get("trace_multiplication_factor"):
        print(f"\nThe defence forces the attacker to observe "
              f"{tm['trace_multiplication_factor']}x more batches to reach "
              f"{tm['target_accuracy']:.3f} balanced accuracy.")
    elif tm.get("defended_reached_target") is False:
        print(f"\nThe defended attacker never reached "
              f"{tm.get('target_accuracy')} within the collected budget. Report "
              f"this as a lower bound, not as proof of immunity - a larger "
              f"budget might still succeed.")

    print(f"\nwritten to {outdir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
