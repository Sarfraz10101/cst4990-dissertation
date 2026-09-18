"""Feature extraction: raw batch latencies -> one feature vector per trial.

Runs on Windows or Linux - the analysis half of the project needs no kernel
access, so you can collect in the VM and analyse on the host.

What the attacker is allowed to see
-----------------------------------
Features are derived *only* from `ns_per_pkt`. The CPU columns in the dataset
(`noise_cpu_s`, `victim_user_s`, `victim_sys_s`) are deliberately excluded:
they are instrumentation for the overhead analysis (RQ2), not signals a
co-located observer could read. Feeding them to the classifier would inflate
accuracy through measurement leakage rather than a real side channel.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sps

SOURCE_COLUMN = "ns_per_pkt"

# Carried through to the output but never used as predictors.
LABEL_COLUMNS = ("config", "verdict", "depth", "noise")
EXCLUDED_FROM_FEATURES = ("noise_cpu_s", "victim_user_s", "victim_sys_s")

QUANTILES = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)


def _vector(ns: np.ndarray) -> dict[str, float]:
    """Summarise one trial's batch latencies.

    The distribution is deliberately described from several angles: central
    tendency, spread, tail shape, and temporal texture. A defence might flatten
    the mean while leaving the tails or the autocorrelation informative, and a
    feature set built only on the mean would miss that.
    """
    q = np.quantile(ns, QUANTILES)
    diffs = np.diff(ns)

    feats: dict[str, float] = {
        # central tendency
        "mean": float(np.mean(ns)),
        "median": float(np.median(ns)),
        "trimmed_mean_10": float(sps.trim_mean(ns, 0.10)),
        # spread
        "std": float(np.std(ns, ddof=1)) if ns.size > 1 else 0.0,
        "iqr": float(np.quantile(ns, 0.75) - np.quantile(ns, 0.25)),
        "mad": float(np.median(np.abs(ns - np.median(ns)))),
        "range": float(np.ptp(ns)),
        # tail shape - a noise defence often changes these before the mean
        "skew": float(sps.skew(ns)) if ns.size > 2 else 0.0,
        "kurtosis": float(sps.kurtosis(ns)) if ns.size > 3 else 0.0,
        # temporal texture within the trial
        "mean_abs_diff": float(np.mean(np.abs(diffs))) if diffs.size else 0.0,
        "std_diff": float(np.std(diffs, ddof=1)) if diffs.size > 1 else 0.0,
    }

    for p, v in zip(QUANTILES, q):
        feats[f"q{int(p * 100):02d}"] = float(v)

    # Within-trial drift: slope of latency against batch index. Captures
    # thermal or scheduling ramp that a single summary statistic would hide.
    if ns.size > 2:
        x = np.arange(ns.size, dtype=float)
        feats["slope"] = float(np.polyfit(x, ns, 1)[0])
    else:
        feats["slope"] = 0.0

    return feats


def feature_names() -> list[str]:
    """Feature column order, for reporting and for Chapter 3's feature table."""
    return list(_vector(np.arange(10, dtype=float) + 1000.0).keys())


def load_raw(path: str) -> pd.DataFrame:
    """Read a collector CSV, validating the columns we depend on."""
    df = pd.read_csv(path)
    required = {"trial_idx", SOURCE_COLUMN, *LABEL_COLUMNS}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {sorted(missing)}")
    return df


def build(df: pd.DataFrame, max_batches: int | None = None) -> pd.DataFrame:
    """Aggregate a long-format trace into one row per trial.

    Aggregating to trial level is itself a leakage control: the 50 batches
    inside a trial share a thermal and scheduling state, so if they were used
    as independent samples, a random train/test split would put near-duplicate
    rows on both sides of the boundary and inflate accuracy toward 100%.

    `max_batches` caps how many batches per trial the attacker is allowed to
    average over. Sweeping it (see sweep.py) measures how the attack scales with
    observation budget - the difference between a defence that defeats an
    attacker and one that merely makes them wait.
    """
    rows = []
    for trial_idx, g in df.groupby("trial_idx", sort=True):
        if max_batches is not None:
            g = g.nsmallest(max_batches, "batch_idx") if "batch_idx" in g else g.head(max_batches)
        ns = g[SOURCE_COLUMN].to_numpy(dtype=float)
        if ns.size == 0:
            continue
        row = {"trial_idx": int(trial_idx)}
        row.update(_vector(ns))
        for col in LABEL_COLUMNS:
            row[col] = g[col].iloc[0]
        # Instrumentation, carried for RQ2 but never a predictor.
        for col in EXCLUDED_FROM_FEATURES:
            if col in g.columns:
                row[col] = float(g[col].iloc[0])
        row["n_batches"] = int(ns.size)
        row["send_errors"] = int(g["send_errors"].sum()) if "send_errors" in g else 0
        rows.append(row)

    out = pd.DataFrame(rows)
    if out.empty:
        raise ValueError("no trials found in input")
    return out


def matrix(trials: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (X, y, trial_ids) for a set of trials."""
    names = feature_names()
    X = trials[names].to_numpy(dtype=float)
    y = trials["config"].to_numpy()
    ids = trials["trial_idx"].to_numpy()
    return X, y, ids


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Summarise a trace into trial features")
    ap.add_argument("--data", required=True, help="collector CSV")
    ap.add_argument("--out", default=None, help="write trial-level CSV here")
    args = ap.parse_args()

    trials = build(load_raw(args.data))
    print(f"{len(trials)} trials, {len(feature_names())} features")
    print(trials.groupby(["config", "noise"]).size().to_string())
    if args.out:
        trials.to_csv(args.out, index=False)
        print(f"-> {args.out}")
