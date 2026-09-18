"""Simulated attacker: recover the live firewall configuration from timing.

    python attack.py --data ../data/run01_poisson.csv --out ../results

Runs the classifier separately on noise-off and noise-on trials, so the two
accuracies are directly comparable - that difference is the answer to RQ1.

Three deliberate methodological choices, all defensible at the viva:

1. **Balanced accuracy** is the headline metric, not raw accuracy. With four
   classes, raw accuracy on a slightly imbalanced test fold can drift upward
   for free; balanced accuracy averages per-class recall and cannot.
2. **A shuffled-label control** runs alongside every real fit. If the pipeline
   is sound it must score at chance (~0.25) on permuted labels. A control that
   scores above chance means leakage somewhere in the pipeline, and any real
   result would be uninterpretable until it is found.
3. **StratifiedGroupKFold in per-batch mode**, grouped by trial. Batches from
   one trial share a thermal and scheduling state; splitting them across the
   train/test boundary is the single most common way side-channel ML results
   get overstated.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import (
    StratifiedGroupKFold,
    StratifiedKFold,
    cross_val_predict,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import features as F
from config import CHANCE_ACCURACY, RANDOM_SEED

N_SPLITS = 5


def build_models(seed: int) -> dict[str, object]:
    """Two classifiers: a linear baseline and a non-linear workhorse.

    Reporting both guards against a reviewer's obvious question - whether the
    result is an artefact of one model's inductive bias.
    """
    return {
        "logreg": make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=2000, random_state=seed),
        ),
        "randomforest": RandomForestClassifier(
            n_estimators=300,
            min_samples_leaf=2,
            random_state=seed,
            n_jobs=-1,
        ),
    }


def evaluate(
    X: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray | None,
    model,
    seed: int,
    shuffle_labels: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """Cross-validated out-of-fold predictions. Returns (y_used, y_pred)."""
    rng = np.random.default_rng(seed)
    y_used = y.copy()
    if shuffle_labels:
        y_used = rng.permutation(y_used)

    # Never fewer folds than the rarest class can support.
    min_class = int(pd.Series(y_used).value_counts().min())
    n_splits = max(2, min(N_SPLITS, min_class))

    if groups is not None:
        cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        pred = cross_val_predict(model, X, y_used, cv=cv, groups=groups, n_jobs=1)
    else:
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        pred = cross_val_predict(model, X, y_used, cv=cv, n_jobs=1)
    return y_used, pred


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", required=True, help="collector CSV")
    ap.add_argument("--out", default="../results", help="output directory")
    ap.add_argument("--mode", choices=("trial", "batch"), default="trial",
                    help="trial: rich aggregate features (default). "
                         "batch: one raw latency per sample, a minimal attacker")
    ap.add_argument("--seed", type=int, default=RANDOM_SEED)
    args = ap.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    raw = F.load_raw(args.data)

    if args.mode == "trial":
        table = F.build(raw)
        names = F.feature_names()
        group_col = None
    else:
        table = raw.rename(columns={F.SOURCE_COLUMN: "ns"})
        names = ["ns"]
        group_col = "trial_idx"

    print(f"{args.data}: {len(table)} samples, mode={args.mode}, "
          f"{len(names)} feature(s)")
    print(table.groupby(["config", "noise"]).size().to_string())
    print()

    models = build_models(args.seed)
    summary_rows: list[dict] = []
    prediction_rows: list[pd.DataFrame] = []
    labels = sorted(table["config"].unique())

    for noise_on in sorted(table["noise"].unique()):
        subset = table[table["noise"] == noise_on]
        X = subset[names].to_numpy(dtype=float)
        y = subset["config"].to_numpy()
        groups = subset[group_col].to_numpy() if group_col else None
        condition = "noise_on" if int(noise_on) == 1 else "noise_off"

        for model_name, model in models.items():
            for shuffled in (False, True):
                y_used, pred = evaluate(
                    X, y, groups, model, args.seed, shuffle_labels=shuffled
                )
                bal = balanced_accuracy_score(y_used, pred)
                raw_acc = float((y_used == pred).mean())

                summary_rows.append({
                    "condition": condition,
                    "model": model_name,
                    "labels": "shuffled" if shuffled else "real",
                    "n_samples": len(y_used),
                    "balanced_accuracy": round(bal, 4),
                    "accuracy": round(raw_acc, 4),
                    "chance": CHANCE_ACCURACY,
                    "lift_over_chance": round(bal - CHANCE_ACCURACY, 4),
                })

                tag = "shuffled" if shuffled else "real"
                print(f"  {condition:9s} {model_name:13s} {tag:8s} "
                      f"balanced_acc = {bal:.4f}  (chance {CHANCE_ACCURACY:.2f})")

                if not shuffled:
                    prediction_rows.append(pd.DataFrame({
                        "condition": condition,
                        "model": model_name,
                        "y_true": y_used,
                        "y_pred": pred,
                    }))

                    cm = confusion_matrix(y_used, pred, labels=labels)
                    pd.DataFrame(cm, index=labels, columns=labels).to_csv(
                        outdir / f"confusion_{model_name}_{condition}.csv"
                    )

                    report = classification_report(
                        y_used, pred, labels=labels, output_dict=True,
                        zero_division=0,
                    )
                    pd.DataFrame(report).transpose().to_csv(
                        outdir / f"per_class_{model_name}_{condition}.csv"
                    )

            # Which distribution statistic leaks most? Chapter 4 material.
            if model_name == "randomforest" and args.mode == "trial":
                fitted = RandomForestClassifier(
                    n_estimators=300, min_samples_leaf=2,
                    random_state=args.seed, n_jobs=-1,
                ).fit(X, y)
                pd.DataFrame({
                    "feature": names,
                    "importance": fitted.feature_importances_,
                }).sort_values("importance", ascending=False).to_csv(
                    outdir / f"feature_importance_{condition}.csv", index=False
                )

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(outdir / "accuracy.csv", index=False)
    pd.concat(prediction_rows, ignore_index=True).to_csv(
        outdir / "predictions.csv", index=False
    )

    # Headline RQ1 numbers, for stats.py and for the results chapter.
    real = summary[summary["labels"] == "real"]
    headline = {}
    for model_name in models:
        m = real[real["model"] == model_name].set_index("condition")
        if {"noise_off", "noise_on"}.issubset(m.index):
            off = float(m.loc["noise_off", "balanced_accuracy"])
            on = float(m.loc["noise_on", "balanced_accuracy"])
            headline[model_name] = {
                "balanced_accuracy_noise_off": off,
                "balanced_accuracy_noise_on": on,
                "absolute_reduction": round(off - on, 4),
                "relative_reduction_pct": (
                    round(100 * (off - on) / (off - CHANCE_ACCURACY), 2)
                    if off > CHANCE_ACCURACY else None
                ),
            }
    (outdir / "headline.json").write_text(json.dumps(headline, indent=2))

    print(f"\nControl check - shuffled labels should sit near "
          f"{CHANCE_ACCURACY:.2f}:")
    for _, r in summary[summary["labels"] == "shuffled"].iterrows():
        flag = "OK" if abs(r["balanced_accuracy"] - CHANCE_ACCURACY) < 0.08 else "SUSPECT"
        print(f"  {r['condition']:9s} {r['model']:13s} "
              f"{r['balanced_accuracy']:.4f}  {flag}")

    print(f"\nheadline: {json.dumps(headline, indent=2)}")
    print(f"\nwritten to {outdir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
