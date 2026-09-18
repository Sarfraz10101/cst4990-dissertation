"""Statistical analysis: confidence intervals, significance, and overhead.

    python stats.py --data ../data/run01_poisson.csv --results ../results

Consumes `predictions.csv` from attack.py plus the raw trace, and produces the
numbers that go directly into Chapter 4:

  RQ1  attacker balanced accuracy per condition, with bootstrap 95% CIs, a
       permutation p-value against chance, and a CI on the *reduction* the
       defence achieves
  RQ2  CPU cost of the defence, and the latency penalty paid by legitimate
       traffic

Two notes on the permutation test. The version here permutes the fitted
predictions, which tests whether predicted and true labels are associated. It is
cheap and it is a valid test of that hypothesis. The stronger version - permute
labels *before* cross-validation, so the whole pipeline is re-fitted on noise -
is what attack.py already runs as its shuffled-label control. Cite both: the
control rules out pipeline leakage, this test puts a p-value on the result.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sps
from sklearn.metrics import balanced_accuracy_score

from config import CHANCE_ACCURACY

N_BOOT = 2000
N_PERM = 10000
ALPHA = 0.05


# ---------------------------------------------------------------------------
# Resampling helpers
# ---------------------------------------------------------------------------
def bootstrap_balanced_accuracy(
    y_true: np.ndarray, y_pred: np.ndarray, n_boot: int, rng: np.random.Generator
) -> tuple[float, float, float]:
    """Point estimate and percentile bootstrap CI for balanced accuracy."""
    observed = balanced_accuracy_score(y_true, y_pred)
    n = len(y_true)
    labels = np.unique(y_true)

    draws = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        yt, yp = y_true[idx], y_pred[idx]
        # A resample missing a class makes per-class recall undefined; skip it
        # rather than let sklearn substitute a zero and bias the interval down.
        if len(np.unique(yt)) < len(labels):
            continue
        draws.append(balanced_accuracy_score(yt, yp))

    if not draws:
        return float(observed), float("nan"), float("nan")
    lo, hi = np.percentile(draws, [100 * ALPHA / 2, 100 * (1 - ALPHA / 2)])
    return float(observed), float(lo), float(hi)


def permutation_p_value(
    y_true: np.ndarray, y_pred: np.ndarray, n_perm: int, rng: np.random.Generator
) -> float:
    """One-sided p: how often does shuffling predictions match the observed score?

    The +1 in numerator and denominator is the standard add-one correction; it
    prevents reporting p = 0, which no finite permutation test can justify.
    """
    observed = balanced_accuracy_score(y_true, y_pred)
    count = 0
    for _ in range(n_perm):
        if balanced_accuracy_score(y_true, rng.permutation(y_pred)) >= observed:
            count += 1
    return (count + 1) / (n_perm + 1)


def bootstrap_difference(
    y_true_a: np.ndarray, y_pred_a: np.ndarray,
    y_true_b: np.ndarray, y_pred_b: np.ndarray,
    n_boot: int, rng: np.random.Generator,
) -> tuple[float, float, float]:
    """CI on (accuracy_a - accuracy_b), resampling each condition independently."""
    observed = (
        balanced_accuracy_score(y_true_a, y_pred_a)
        - balanced_accuracy_score(y_true_b, y_pred_b)
    )
    na, nb = len(y_true_a), len(y_true_b)
    la, lb = np.unique(y_true_a), np.unique(y_true_b)

    draws = []
    for _ in range(n_boot):
        ia = rng.integers(0, na, size=na)
        ib = rng.integers(0, nb, size=nb)
        if (len(np.unique(y_true_a[ia])) < len(la)
                or len(np.unique(y_true_b[ib])) < len(lb)):
            continue
        draws.append(
            balanced_accuracy_score(y_true_a[ia], y_pred_a[ia])
            - balanced_accuracy_score(y_true_b[ib], y_pred_b[ib])
        )

    if not draws:
        return float(observed), float("nan"), float("nan")
    lo, hi = np.percentile(draws, [100 * ALPHA / 2, 100 * (1 - ALPHA / 2)])
    return float(observed), float(lo), float(hi)


def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    """Standardised mean difference (b - a), pooled SD."""
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    va, vb = np.var(a, ddof=1), np.var(b, ddof=1)
    pooled = np.sqrt(((len(a) - 1) * va + (len(b) - 1) * vb) / (len(a) + len(b) - 2))
    return float("inf") if pooled == 0 else float((np.mean(b) - np.mean(a)) / pooled)


# ---------------------------------------------------------------------------
# RQ1 - did the defence reduce attacker accuracy?
# ---------------------------------------------------------------------------
def analyse_rq1(preds: pd.DataFrame, rng: np.random.Generator,
                n_boot: int, n_perm: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    per_condition, reductions = [], []

    for model, g_model in preds.groupby("model"):
        by_cond = {}
        ci_low = {}
        for condition, g in g_model.groupby("condition"):
            yt = g["y_true"].to_numpy()
            yp = g["y_pred"].to_numpy()
            by_cond[condition] = (yt, yp)

            acc, lo, hi = bootstrap_balanced_accuracy(yt, yp, n_boot, rng)
            ci_low[condition] = lo
            p = permutation_p_value(yt, yp, n_perm, rng)
            per_condition.append({
                "model": model,
                "condition": condition,
                "n": len(yt),
                "balanced_accuracy": round(acc, 4),
                "ci95_low": round(lo, 4),
                "ci95_high": round(hi, 4),
                "chance": CHANCE_ACCURACY,
                "above_chance": bool(lo > CHANCE_ACCURACY),
                "p_vs_chance": p,
                "p_reported": f"< {1/(n_perm+1):.1e}" if p <= 1/(n_perm+1) else f"{p:.4g}",
            })

        if {"noise_off", "noise_on"}.issubset(by_cond):
            (yt_off, yp_off) = by_cond["noise_off"]
            (yt_on, yp_on) = by_cond["noise_on"]
            diff, lo, hi = bootstrap_difference(
                yt_off, yp_off, yt_on, yp_on, n_boot, rng
            )
            acc_off = balanced_accuracy_score(yt_off, yp_off)
            headroom = acc_off - CHANCE_ACCURACY

            # "Percentage of the leak removed" only means something if there was
            # a leak. If the undefended attacker's own CI includes chance, the
            # denominator is noise and the ratio would be a fabricated headline.
            leak_established = bool(ci_low.get("noise_off", -1) > CHANCE_ACCURACY)

            reductions.append({
                "model": model,
                "accuracy_noise_off": round(acc_off, 4),
                "accuracy_noise_on": round(
                    balanced_accuracy_score(yt_on, yp_on), 4),
                "reduction_pp": round(100 * diff, 2),
                "reduction_ci95_low_pp": round(100 * lo, 2),
                "reduction_ci95_high_pp": round(100 * hi, 2),
                "undefended_above_chance": leak_established,
                # Share of the *recoverable* leak that the defence removed.
                # Measured against the chance floor, not zero: an attacker can
                # never be driven below 25% on a balanced 4-class problem.
                "pct_of_leak_removed": (
                    round(100 * diff / headroom, 2)
                    if leak_established and headroom > 0 else None
                ),
                "significant": bool(lo > 0),
            })

    return pd.DataFrame(per_condition), pd.DataFrame(reductions)


# ---------------------------------------------------------------------------
# RQ2 - what did the defence cost?
# ---------------------------------------------------------------------------
def analyse_rq2(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    trial = raw.groupby(["trial_idx", "config", "noise"], as_index=False).agg(
        median_ns=("ns_per_pkt", "median"),
        mean_ns=("ns_per_pkt", "mean"),
        p95_ns=("ns_per_pkt", lambda s: s.quantile(0.95)),
        noise_cpu_s=("noise_cpu_s", "first"),
        victim_user_s=("victim_user_s", "first"),
        victim_sys_s=("victim_sys_s", "first"),
    )

    off = trial[trial["noise"] == 0]
    on = trial[trial["noise"] == 1]
    rows = []

    for metric in ("median_ns", "mean_ns", "p95_ns", "noise_cpu_s",
                   "victim_user_s", "victim_sys_s"):
        a = off[metric].to_numpy(dtype=float)
        b = on[metric].to_numpy(dtype=float)
        if len(a) == 0 or len(b) == 0:
            continue
        mean_off, mean_on = float(np.mean(a)), float(np.mean(b))

        # Mann-Whitney rather than a t-test: latency distributions are
        # right-skewed by scheduling spikes, so a rank test is the honest choice.
        try:
            u = sps.mannwhitneyu(a, b, alternative="two-sided")
            p = float(u.pvalue)
        except ValueError:
            p = float("nan")

        rows.append({
            "metric": metric,
            "noise_off_mean": round(mean_off, 6),
            "noise_on_mean": round(mean_on, 6),
            "absolute_change": round(mean_on - mean_off, 6),
            "pct_change": (
                round(100 * (mean_on - mean_off) / mean_off, 2)
                if mean_off else None
            ),
            "cohens_d": round(cohens_d(a, b), 3),
            "mannwhitney_p": p,
        })

    return pd.DataFrame(rows), trial


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def write_summary(
    path: Path, per_cond: pd.DataFrame, reductions: pd.DataFrame,
    overhead: pd.DataFrame, source: str, n_boot: int, n_perm: int,
) -> None:
    lines = [
        "# Statistical summary",
        "",
        f"Source: `{source}`",
        f"Bootstrap resamples: {n_boot}. Permutations: {n_perm}. "
        f"Confidence level: {int((1-ALPHA)*100)}%.",
        f"Chance baseline: {CHANCE_ACCURACY:.2f} (4 balanced classes).",
        "",
        "## RQ1 - attacker classification accuracy",
        "",
        per_cond.to_markdown(index=False),
        "",
        "### Reduction achieved by the defence",
        "",
        reductions.to_markdown(index=False) if not reductions.empty
        else "_Both conditions not present in the dataset._",
        "",
        "## RQ2 - cost of the defence",
        "",
        overhead.to_markdown(index=False),
        "",
        "### Reading this table",
        "",
        "- `noise_cpu_s` is CPU seconds the injector's worker processes",
        "  consumed per trial, read from `/proc/<pid>/stat`. This is the",
        "  direct CPU price of the defence.",
        "- `median_ns` / `mean_ns` / `p95_ns` are per-packet latency. Their",
        "  increase is the price paid by legitimate traffic - the figure an",
        "  operator would actually care about.",
        "- `p95_ns` matters more than the mean for a latency-sensitive service:",
        "  tail latency is what users experience.",
        "",
    ]

    if not reductions.empty:
        r = reductions.iloc[0]
        if not r["undefended_above_chance"]:
            lines += [
                "## No leak was established",
                "",
                "The undefended attacker's 95% confidence interval includes the "
                f"chance baseline ({CHANCE_ACCURACY:.2f}), so there is no "
                "demonstrated side channel in this dataset and no reduction to "
                "attribute to the defence.",
                "",
                "That is a reportable outcome, not a failed experiment - but it "
                "must be reported as a null result on RQ1, and the RQ2 overhead "
                "figures above stand on their own. Work through README section 6 "
                "before concluding the channel does not exist.",
                "",
            ]
        else:
            cost = ""
            if "median_ns" in set(overhead["metric"]):
                pct = overhead.loc[overhead["metric"] == "median_ns",
                                   "pct_change"].iloc[0]
                cost = f" at a cost of {pct:.1f}% median packet latency"
            leak = ""
            if r["pct_of_leak_removed"] is not None:
                leak = f", removing {r['pct_of_leak_removed']}% of the recoverable leak"
            lines += [
                "## Sentence for the abstract",
                "",
                f"> Attacker balanced accuracy fell from "
                f"{r['accuracy_noise_off']:.3f} to {r['accuracy_noise_on']:.3f} "
                f"when the noise-injection defence was active, a reduction of "
                f"{r['reduction_pp']:.1f} percentage points (95% CI "
                f"[{r['reduction_ci95_low_pp']:.1f}, "
                f"{r['reduction_ci95_high_pp']:.1f}]){leak}{cost}.",
                "",
                "Replace with your own wording - but keep the CI and the cost. A",
                "reduction quoted without its cost is not an evaluation. Check",
                "`trace_multiplication.csv` before calling the defence effective:",
                "a reduction that vanishes as the observation budget grows is a",
                "delay, not a mitigation.",
                "",
            ]

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", required=True, help="collector CSV (for RQ2)")
    ap.add_argument("--results", default="../results",
                    help="directory holding predictions.csv from attack.py")
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--n-perm", type=int, default=N_PERM)
    ap.add_argument("--seed", type=int, default=12345)
    args = ap.parse_args()

    resdir = Path(args.results)
    pred_path = resdir / "predictions.csv"
    if not pred_path.exists():
        print(f"error: {pred_path} not found - run attack.py first")
        return 1

    rng = np.random.default_rng(args.seed)
    preds = pd.read_csv(pred_path)
    raw = pd.read_csv(args.data)

    print("RQ1 - attacker accuracy")
    per_cond, reductions = analyse_rq1(preds, rng, args.n_boot, args.n_perm)
    print(per_cond.to_string(index=False))
    print()
    if not reductions.empty:
        print("Reduction achieved by the defence")
        print(reductions.to_string(index=False))
        print()

    print("RQ2 - cost of the defence")
    overhead, trial = analyse_rq2(raw)
    print(overhead.to_string(index=False))

    per_cond.to_csv(resdir / "rq1_accuracy_ci.csv", index=False)
    reductions.to_csv(resdir / "rq1_reduction.csv", index=False)
    overhead.to_csv(resdir / "rq2_overhead.csv", index=False)

    # Excel-ready: one row per trial, for box plots and scatter charts.
    trial.to_csv(resdir / "figure_trial_level.csv", index=False)
    trial.pivot_table(
        index="config", columns="noise", values="median_ns", aggfunc="median"
    ).to_csv(resdir / "figure_latency_by_config.csv")

    write_summary(
        resdir / "STATS_SUMMARY.md", per_cond, reductions, overhead,
        args.data, args.n_boot, args.n_perm,
    )
    (resdir / "stats_meta.json").write_text(json.dumps({
        "source_data": args.data,
        "n_bootstrap": args.n_boot,
        "n_permutations": args.n_perm,
        "alpha": ALPHA,
        "chance_accuracy": CHANCE_ACCURACY,
        "seed": args.seed,
    }, indent=2))

    print(f"\nwritten to {resdir}/  (see STATS_SUMMARY.md)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
