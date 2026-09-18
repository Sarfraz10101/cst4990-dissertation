"""Render the dissertation's figures as PNG from the analysis CSVs.

    python figures.py --results ../results/run01

Reads whatever `attack.py`, `stats.py` and `sweep.py` have produced in that
directory and writes `<results>/figures/*.png` plus a captions file. Missing
inputs are skipped with a warning rather than treated as errors, so this is safe
to run part-way through the pipeline.

Every figure is built to survive submission: 300 dpi, sized to the 16 cm text
width left by 2 cm margins, and readable in greyscale. Markers and hatching
carry the distinction between conditions as well as colour, because a marker
printing your PDF in black and white must still be able to read it.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no display in a VM or over SSH

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from config import CHANCE_ACCURACY

# 16 cm of usable width at 2 cm margins on A4 = 6.3 in.
FIG_W = 6.3
DPI = 300

# Greyscale-distinguishable pairing: fill, edge, hatch, marker, linestyle.
OFF = {"color": "#3b3b3b", "marker": "o", "ls": "-", "hatch": ""}
ON = {"color": "#9a9a9a", "marker": "s", "ls": "--", "hatch": "///"}
STYLE = {"noise_off": OFF, "noise_on": ON}
LABEL = {"noise_off": "Defence inactive", "noise_on": "Defence active"}

plt.rcParams.update({
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "legend.fontsize": 8,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linewidth": 0.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.constrained_layout.use": True,
})

CAPTIONS: list[tuple[str, str, str]] = []


def save(fig, outdir: Path, name: str, section: str, caption: str) -> None:
    path = outdir / name
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    CAPTIONS.append((name, section, caption))
    print(f"  {name}")


def read(resdir: Path, name: str) -> pd.DataFrame | None:
    path = resdir / name
    if not path.exists():
        print(f"  skipping {name}: not found")
        return None
    return pd.read_csv(path)


# ---------------------------------------------------------------------------
# Figure 1 - the leak, and what the defence costs (sections 4.2 and 4.6)
# ---------------------------------------------------------------------------
def fig_latency(resdir: Path, outdir: Path) -> None:
    trials = read(resdir, "figure_trial_level.csv")
    if trials is None:
        return

    configs = sorted(trials["config"].unique())
    fig, ax = plt.subplots(figsize=(FIG_W, 3.0))

    width = 0.34
    for offset, noise_val, key in ((-width / 2 - 0.02, 0, "noise_off"),
                                   (+width / 2 + 0.02, 1, "noise_on")):
        data = [
            trials[(trials["config"] == c) & (trials["noise"] == noise_val)]
            ["median_ns"].to_numpy(dtype=float)
            for c in configs
        ]
        if all(d.size == 0 for d in data):
            continue
        positions = np.arange(len(configs)) + offset
        st = STYLE[key]
        bp = ax.boxplot(
            data, positions=positions, widths=width, patch_artist=True,
            showfliers=False, medianprops={"color": "black", "linewidth": 1.2},
        )
        for box in bp["boxes"]:
            box.set_facecolor(st["color"])
            box.set_alpha(0.75)
            box.set_hatch(st["hatch"])
            box.set_edgecolor("black")
            box.set_linewidth(0.6)
        for part in ("whiskers", "caps"):
            for artist in bp[part]:
                artist.set_linewidth(0.6)
        # Proxy artist so the legend picks up fill and hatch together.
        ax.bar(np.nan, np.nan, color=st["color"], alpha=0.75, hatch=st["hatch"],
               edgecolor="black", linewidth=0.6, label=LABEL[key])

    ax.set_xticks(np.arange(len(configs)))
    ax.set_xticklabels([c.replace("_", "\n") for c in configs])
    ax.set_ylabel("Median latency (ns per packet)")
    ax.set_xlabel("Firewall configuration")
    ax.set_title("Per-packet send latency by firewall configuration")
    # Legend outside the axes: an in-axes legend collides with whichever
    # configuration happens to be both leftmost and slowest.
    fig.legend(loc="outside lower center", ncol=2, frameon=False)

    save(fig, outdir, "fig1_latency_by_config.png", "4.2 / 4.6",
         "Distribution of per-trial median send latency for each firewall "
         "configuration, with the noise-injection defence inactive and active. "
         "Separation between configurations is the side channel; the upward "
         "shift under the defence is the latency cost paid by legitimate "
         "traffic. Boxes span the interquartile range, whiskers 1.5 IQR; "
         "outliers omitted for legibility.")


# ---------------------------------------------------------------------------
# Figure 2 - attacker accuracy and the validity controls (4.3, 4.4, 4.7)
# ---------------------------------------------------------------------------
def fig_accuracy(resdir: Path, outdir: Path) -> None:
    acc = read(resdir, "accuracy.csv")
    if acc is None:
        return

    models = sorted(acc["model"].unique())
    conditions = [c for c in ("noise_off", "noise_on")
                  if c in set(acc["condition"])]
    if not conditions:
        return

    fig, axes = plt.subplots(1, len(models), figsize=(FIG_W, 3.1), sharey=True)
    axes = np.atleast_1d(axes)

    for ax, model in zip(axes, models):
        sub = acc[acc["model"] == model]
        x = np.arange(len(conditions))
        width = 0.36

        for i, (labels_kind, hatch, colour) in enumerate(
            (("real", "", "#3b3b3b"), ("shuffled", "xxx", "#d9d9d9"))
        ):
            vals = [
                float(sub[(sub["condition"] == c)
                          & (sub["labels"] == labels_kind)]
                      ["balanced_accuracy"].iloc[0])
                if not sub[(sub["condition"] == c)
                           & (sub["labels"] == labels_kind)].empty else np.nan
                for c in conditions
            ]
            pos = x + (i - 0.5) * width
            ax.bar(pos, vals, width, color=colour, hatch=hatch,
                   edgecolor="black", linewidth=0.6,
                   label="Real labels" if labels_kind == "real"
                   else "Shuffled-label control")
            for px, v in zip(pos, vals):
                if np.isnan(v):
                    continue
                # A label just above a bar that ends near the chance line would
                # sit on top of it; drop those inside the bar instead. Inside the
                # bar the dense hatch runs straight through the digits, so give
                # those a flat white patch to sit on - without it the control
                # values are unreadable, which is exactly the number a sceptical
                # examiner wants to check.
                if abs(v - CHANCE_ACCURACY) < 0.06:
                    ax.text(px, v - 0.03, f"{v:.3f}", ha="center", va="top",
                            fontsize=7, zorder=5,
                            bbox={"boxstyle": "square,pad=0.15",
                                  "facecolor": "white", "edgecolor": "none"})
                else:
                    ax.text(px, v + 0.02, f"{v:.3f}", ha="center", fontsize=7)

        # Chance goes in the legend rather than as inline text, which would
        # collide with the control bars' value labels - they sit at chance too.
        ax.axhline(CHANCE_ACCURACY, color="black", ls=":", linewidth=1.0)
        ax.set_xticks(x)
        ax.set_xticklabels([LABEL[c] for c in conditions])
        ax.set_ylim(0, 1.12)
        ax.set_title(model)

    axes[0].set_ylabel("Balanced accuracy")

    handles, labels = axes[0].get_legend_handles_labels()
    handles.append(plt.Line2D([], [], color="black", ls=":", linewidth=1.0))
    labels.append(f"Chance ({CHANCE_ACCURACY:.2f})")
    fig.legend(handles, labels, loc="outside lower center", ncol=3,
               frameon=False)
    fig.suptitle("Attacker accuracy, with shuffled-label controls", fontsize=10)

    save(fig, outdir, "fig2_accuracy_and_controls.png", "4.3 / 4.4 / 4.7",
         "Attacker balanced accuracy by condition and model. The "
         "shuffled-label control refits the identical pipeline on permuted "
         "labels and must sit at the chance baseline; that it does is evidence "
         "the real scores reflect a side channel rather than leakage in the "
         "cross-validation.")


# ---------------------------------------------------------------------------
# Figure 3 - the centrepiece: does the defence defeat or merely delay? (4.5)
# ---------------------------------------------------------------------------
def fig_sweep(resdir: Path, outdir: Path, target: str = "config") -> None:
    """Render one budget curve.

    `target="config"` is the 4-class problem (chance 0.25) and writes
    `fig3_sweep_curve.png`. `target="verdict"` is accept vs drop within the deep
    configurations (chance 0.5) and writes `fig3b_sweep_curve_verdict.png`.

    Both exist because the 4-class curve saturates on this system - depth is
    separable from roughly a single packet, so it opens above its own target and
    the trace-multiplication factor degenerates to 1.0. The verdict axis is the
    one with the dynamic range the factor needs. Chance is read from the CSV
    rather than from config.CHANCE_ACCURACY, which is 0.25 and would mislabel
    the verdict figure.
    """
    suffix = "_verdict" if target == "verdict" else ""
    curve = read(resdir, f"sweep_curve{suffix}.csv")
    if curve is None:
        return

    chance = (float(curve["chance"].iloc[0]) if "chance" in curve.columns
              else CHANCE_ACCURACY)

    fig, ax = plt.subplots(figsize=(FIG_W, 3.4))

    for key in ("noise_off", "noise_on"):
        sub = curve[curve["condition"] == key].sort_values("batches")
        if sub.empty:
            continue
        st = STYLE[key]
        ax.plot(sub["batches"], sub["balanced_accuracy"],
                marker=st["marker"], ls=st["ls"], color=st["color"],
                markersize=4.5, linewidth=1.4, label=LABEL[key],
                markeredgecolor="black", markeredgewidth=0.5)

    ax.set_xscale("log")
    ax.set_xticks(sorted(curve["batches"].unique()))
    ax.get_xaxis().set_major_formatter(mticker.ScalarFormatter())
    ax.set_xlabel("Observation budget (timed batches per trial, log scale)")
    ax.set_ylabel("Balanced accuracy")
    # Zoom to the occupied band. With chance at 0.5 a 0-1 axis wastes over half
    # the panel and flattens the very separation the figure exists to show; the
    # chance line stays visible so the zoom cannot mislead.
    lo = min(chance, float(curve["balanced_accuracy"].min()))
    ax.set_ylim(max(0.0, lo - 0.08), 1.02)
    if target == "verdict":
        ax.set_title("Attacker accuracy against observation budget\n"
                     "(accept vs drop, deep configurations only)")
    else:
        ax.set_title("Attacker accuracy against observation budget")

    # Blended transform: x in axes fraction, y in data units. Keeps the labels
    # anchored to the reference lines regardless of the log x-axis limits.
    blend = ax.get_yaxis_transform()
    ax.axhline(chance, color="black", ls=":", linewidth=1.0)
    ax.text(0.985, chance + 0.015, f"chance = {chance:.2f}",
            transform=blend, ha="right", fontsize=7)

    # Annotate the trace-multiplication factor if sweep.py established one.
    # sweep.py leaves it undefined when the undefended attacker never got
    # reliably above chance; drawing a target line in that case would imply a
    # leak the data does not support.
    tm = read(resdir, f"trace_multiplication{suffix}.csv")
    if tm is not None and not tm.empty:
        row = tm.iloc[0]
        established = row.get("undefended_above_chance", True)
        # CSV round-trip gives numpy.bool_ or the string "False" depending on
        # pandas' inference, so neither `is False` nor a bare truth test is safe.
        if isinstance(established, str):
            established = established.strip().lower() not in ("false", "", "nan")
        else:
            established = bool(established) if pd.notna(established) else True

        target_acc = row.get("target_accuracy")
        b_off = row.get("batches_needed_noise_off")
        b_on = row.get("batches_needed_noise_on")
        factor = row.get("trace_multiplication_factor")

        if not established:
            ax.text(0.5, 0.62,
                    "No leak established:\nthe undefended attacker never rose\n"
                    "reliably above chance",
                    transform=ax.transAxes, ha="center", va="center",
                    fontsize=8.5, color="#444444",
                    bbox={"boxstyle": "round,pad=0.4", "facecolor": "white",
                          "edgecolor": "#999999", "linewidth": 0.6})
        elif pd.notna(target_acc):
            target_acc = float(target_acc)
            ax.axhline(target_acc, color="#666666", ls="-.", linewidth=0.8)
            # Right-align the target label. The arrow below starts at the
            # undefended curve's crossing, which is usually within the first few
            # batches - i.e. hard against the left edge, where this label used
            # to sit.
            ax.text(0.985, target_acc + 0.015, f"target = {target_acc:.3f}",
                    transform=blend, ha="right", fontsize=7)
            if pd.notna(b_off) and pd.notna(b_on) and pd.notna(factor):
                b_off, b_on = float(b_off), float(b_on)
                factor = float(factor)
                bmin = float(curve["batches"].min())
                if b_off == b_on:
                    # Degenerate: both conditions cross at the same budget, so
                    # the arrow would have zero length and the "1x" label would
                    # float unanchored - which reads as a measurement rather
                    # than as the absence of one. Name the saturation instead.
                    where = ("the smallest budget tested"
                             if b_off <= bmin else f"{b_off:g} batches")
                    ax.text(0.5, 0.5,
                            "Saturated: both conditions clear the target at\n"
                            f"{where}, so the factor is 1.0 by construction",
                            transform=ax.transAxes, ha="center", va="center",
                            fontsize=8.5, color="#444444",
                            bbox={"boxstyle": "round,pad=0.4",
                                  "facecolor": "white",
                                  "edgecolor": "#999999", "linewidth": 0.6})
                    return _finish_sweep(fig, ax, curve, outdir, target)
                ax.annotate(
                    "", xy=(b_on, target_acc), xytext=(b_off, target_acc),
                    arrowprops={"arrowstyle": "<->", "linewidth": 0.9,
                                "color": "black"},
                )
                # Label beside the arrow head, not under its span. Both
                # crossings fall in the first few batches, so on a log axis the
                # span is narrow while the text is wide - a centred label lands
                # on the markers at either end. Flip to the tail side when the
                # head is already near the right edge.
                bmax = float(curve["batches"].max())
                if b_on * 3.0 <= bmax:
                    x_lab, align = b_on * 1.15, "left"
                else:
                    x_lab, align = b_off / 1.15, "right"
                ax.text(x_lab, target_acc - 0.012,
                        f"{factor:g}x more observation", ha=align,
                        va="top", fontsize=8)

    return _finish_sweep(fig, ax, curve, outdir, target)


def _finish_sweep(fig, ax, curve, outdir, target):
    """Legend, caption and save. Split out so the saturated branch above can
    return early without duplicating any of it."""
    # Lower left: the curves rise left-to-right and the reference-line labels
    # sit on the right, so this is the only corner nothing else wants.
    ax.legend(loc="lower left", framealpha=0.9)

    if target == "verdict":
        gap = _mean_gap(curve)
        save(fig, outdir, "fig3b_sweep_curve_verdict.png", "4.5",
             "Attacker balanced accuracy against observation budget on the "
             "verdict axis (accept vs drop within the deep configurations, "
             "chance 0.5). This axis rather than the four-class problem, "
             "because chain depth is separable from roughly a single packet: "
             "the four-class curve opens above its own half-way target, so its "
             "trace-multiplication factor degenerates to 1.0 and measures "
             "nothing. Separation between the curves is the cost the defence "
             "imposes; convergence at the largest budgets is the attacker "
             "recovering, which is the outcome Chari et al. (1999) predict for "
             "noise countermeasures. Mean separation across the swept budgets "
             f"is {gap:+.3f} balanced accuracy.")
    else:
        save(fig, outdir, "fig3_sweep_curve.png", "4.5",
             "Attacker balanced accuracy as a function of observation budget. If "
             "the defended curve recovers toward the undefended one, the defence "
             "raises the cost of the attack rather than preventing it; the "
             "horizontal separation at the target accuracy is the "
             "trace-multiplication factor. A defended curve that stays flat at "
             "chance would instead indicate the leak had been removed within the "
             "budget tested. On this dataset the four-class curve saturates - see "
             "the verdict-axis figure for the measurement that resolves.")


def _mean_gap(curve: pd.DataFrame) -> float:
    """Mean undefended-minus-defended accuracy across the swept budgets.

    Reported next to the trace-multiplication factor because the factor is a
    single crossing of a single target line: on a curve that steps backwards it
    can be large while the two conditions are statistically indistinguishable.
    The mean gap is what says whether the separation is real.
    """
    wide = curve.pivot_table(index="batches", columns="condition",
                             values="balanced_accuracy")
    if not {"noise_off", "noise_on"} <= set(wide.columns):
        return float("nan")
    return float((wide["noise_off"] - wide["noise_on"]).mean())


# ---------------------------------------------------------------------------
# Figure 4 - which configurations get confused (4.3, 4.4)
# ---------------------------------------------------------------------------
def fig_confusion(resdir: Path, outdir: Path, model: str) -> None:
    frames = {}
    for key in ("noise_off", "noise_on"):
        df = read(resdir, f"confusion_{model}_{key}.csv")
        if df is not None:
            frames[key] = df.set_index(df.columns[0])
    if not frames:
        return

    fig, axes = plt.subplots(1, len(frames), figsize=(FIG_W, 3.1))
    axes = np.atleast_1d(axes)

    for ax, (key, cm) in zip(axes, frames.items()):
        counts = cm.to_numpy(dtype=float)
        totals = counts.sum(axis=1, keepdims=True)
        # Row-normalised: each row is recall for that true class, so the
        # diagonal is directly comparable between conditions with different n.
        norm = np.divide(counts, totals, out=np.zeros_like(counts),
                         where=totals > 0)
        im = ax.imshow(norm, cmap="Greys", vmin=0, vmax=1)

        for i in range(norm.shape[0]):
            for j in range(norm.shape[1]):
                ax.text(j, i, f"{norm[i, j]:.2f}", ha="center", va="center",
                        fontsize=7,
                        color="white" if norm[i, j] > 0.55 else "black")

        ticks = [c.replace("_", "\n") for c in cm.columns]
        ax.set_xticks(range(len(ticks)))
        ax.set_xticklabels(ticks, fontsize=7)
        ax.set_yticks(range(len(cm.index)))
        ax.set_yticklabels([c.replace("_", "\n") for c in cm.index], fontsize=7)
        ax.set_title(LABEL[key])
        ax.set_xlabel("Predicted")
        ax.grid(False)

    axes[0].set_ylabel("True configuration")
    fig.colorbar(im, ax=axes.tolist(), fraction=0.035, pad=0.02,
                 label="Proportion of true class")
    fig.suptitle(f"Confusion matrices, {model}", fontsize=10)

    save(fig, outdir, f"fig4_confusion_{model}.png", "4.3 / 4.4",
         f"Row-normalised confusion matrices for the {model} attacker. Rows "
         "sum to one, so the diagonal is per-class recall and off-diagonal "
         "mass shows which configurations the attacker cannot separate. "
         "Whether errors concentrate along verdict or along rule depth "
         "indicates which of the two secrets the channel actually carries.")


# ---------------------------------------------------------------------------
# Figure 5 - which statistic carries the leak (4.2)
# ---------------------------------------------------------------------------
def fig_importance(resdir: Path, outdir: Path, top_n: int = 10) -> None:
    frames = {}
    for key in ("noise_off", "noise_on"):
        df = read(resdir, f"feature_importance_{key}.csv")
        if df is not None:
            frames[key] = df
    if not frames:
        return

    # Rank by the undefended condition so both panels share an ordering, which
    # makes the shift under the defence readable.
    ref = frames.get("noise_off", next(iter(frames.values())))
    order = ref.sort_values("importance", ascending=False)["feature"].head(top_n).tolist()

    fig, ax = plt.subplots(figsize=(FIG_W, 3.2))
    y = np.arange(len(order))
    height = 0.38

    for i, key in enumerate(k for k in ("noise_off", "noise_on") if k in frames):
        lookup = dict(zip(frames[key]["feature"], frames[key]["importance"]))
        vals = [float(lookup.get(f, 0.0)) for f in order]
        st = STYLE[key]
        ax.barh(y + (0.5 - i) * height, vals, height, color=st["color"],
                hatch=st["hatch"], edgecolor="black", linewidth=0.6,
                label=LABEL[key])

    ax.set_yticks(y)
    ax.set_yticklabels(order)
    ax.invert_yaxis()
    ax.set_xlabel("Random forest importance (mean decrease in impurity)")
    ax.set_title(f"Top {len(order)} timing features by attacker importance")
    ax.legend(loc="lower right", framealpha=0.9)

    save(fig, outdir, "fig5_feature_importance.png", "4.2",
         "Random forest feature importances, ordered by the undefended "
         "condition. Which statistic dominates says what the channel is: "
         "central-tendency features indicate a deterministic cost difference, "
         "while spread or tail features indicate the leak is carried by "
         "variability. Impurity-based importance is biased toward "
         "high-cardinality features and is used here descriptively, not as "
         "inference.")


def write_captions(outdir: Path) -> None:
    lines = [
        "# Figure captions",
        "",
        "Generated by `figures.py`. Numbers in the captions are described, not",
        "asserted - fill in the actual values from `STATS_SUMMARY.md` when you",
        "place each figure, and delete any hedging that no longer applies once",
        "you can see which way the result went.",
        "",
        "Word will not renumber these for you. If you reorder the figures,",
        "renumber them here first.",
        "",
    ]
    for name, section, caption in CAPTIONS:
        lines += [
            f"## {name}",
            "",
            f"*Goes in section {section}.*",
            "",
            caption,
            "",
        ]
    (outdir / "FIGURE_CAPTIONS.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", required=True,
                    help="directory written by attack.py / stats.py / sweep.py")
    ap.add_argument("--out", default=None,
                    help="figure directory (default: <results>/figures)")
    ap.add_argument("--top-features", type=int, default=10)
    args = ap.parse_args()

    resdir = Path(args.results)
    if not resdir.is_dir():
        print(f"error: {resdir} is not a directory")
        return 1

    outdir = Path(args.out) if args.out else resdir / "figures"
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"rendering figures from {resdir}/")
    fig_latency(resdir, outdir)
    fig_accuracy(resdir, outdir)
    fig_sweep(resdir, outdir)
    fig_sweep(resdir, outdir, target="verdict")
    for model in ("randomforest", "logreg"):
        fig_confusion(resdir, outdir, model)
    fig_importance(resdir, outdir, args.top_features)

    if not CAPTIONS:
        print("no figures produced - run attack.py, stats.py and sweep.py first")
        return 1

    write_captions(outdir)
    print(f"\n{len(CAPTIONS)} figures + FIGURE_CAPTIONS.md in {outdir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
