#!/usr/bin/env bash
# Run the full analysis pipeline on one trace.
#
#     bash run_analysis.sh ../data/run01_poisson.csv ../results/run01
#
# Needs no root and no kernel access, so it runs on the host as happily as in
# the guest. Stops at the first failure rather than producing half a chapter's
# worth of numbers from a broken stage.
set -euo pipefail

DATA="${1:-}"
OUT="${2:-}"

if [[ -z "$DATA" || -z "$OUT" ]]; then
    echo "usage: bash run_analysis.sh <trace.csv> <results-dir>" >&2
    echo "example: bash run_analysis.sh ../data/run01_poisson.csv ../results/run01" >&2
    exit 2
fi

if [[ ! -f "$DATA" ]]; then
    echo "error: $DATA not found" >&2
    exit 1
fi

# Resolve both paths against the invocation directory *before* moving into
# harness/, so relative arguments mean what the caller expects wherever they
# ran this from.
DATA="$(cd "$(dirname "$DATA")" && pwd)/$(basename "$DATA")"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"

cd "$(dirname "$0")"

# Pick an interpreter that can actually import the stack. On Windows `python3`
# often resolves to a bare install or a Store stub while `python` is the one
# with the packages, so probe rather than assume. Override with PYTHON=...
PY=""
for candidate in ${PYTHON:-} python3 python py; do
    [[ -z "$candidate" ]] && continue
    command -v "$candidate" >/dev/null 2>&1 || continue
    if "$candidate" -c "import numpy, pandas, sklearn, scipy" >/dev/null 2>&1; then
        PY="$candidate"
        break
    fi
done

if [[ -z "$PY" ]]; then
    echo "error: no interpreter found with numpy, pandas, scikit-learn and scipy." >&2
    echo "Activate the venv first (source ~/cst4990-venv/bin/activate), or set" >&2
    echo "PYTHON=/path/to/python and re-run." >&2
    exit 1
fi

echo "=============================================================="
echo " data    $DATA"
echo " out     $OUT"
echo " python  $("$PY" --version 2>&1) ($PY)"
echo "=============================================================="

echo
echo "--- 1/4  attack.py: classify the configuration -----------------"
"$PY" attack.py --data "$DATA" --out "$OUT"

echo
echo "--- 2/4  stats.py: CIs, significance, overhead -----------------"
"$PY" stats.py --data "$DATA" --results "$OUT"

echo
echo "--- 3/5  sweep.py: observation-budget curve (4 classes) --------"
"$PY" sweep.py --data "$DATA" --out "$OUT"

echo
echo "--- 4/5  sweep.py: observation-budget curve (verdict axis) -----"
# The 4-class sweep above saturates on this system: chain depth separates from
# roughly a single packet, so that curve opens past its own half-way target and
# the trace-multiplication factor degenerates to 1.0. The verdict axis (accept
# vs drop within the deep configs, chance 0.5) is the one with the dynamic range
# the factor needs, and it is what section 4.5 charts. Writes *_verdict.csv
# alongside the 4-class outputs rather than replacing them - report both.
"$PY" sweep.py --data "$DATA" --out "$OUT" --target verdict

echo
echo "--- 5/5  figures.py: render PNGs -------------------------------"
"$PY" figures.py --results "$OUT"

echo
echo "=============================================================="
echo " done. Read these in order:"
echo "   $OUT/STATS_SUMMARY.md                    <- Chapter 4 in draft"
echo "   $OUT/trace_multiplication_verdict.csv    <- the 4.5 headline"
echo "   $OUT/figures/fig3b_sweep_curve_verdict.png"
echo "   $OUT/figures/                            <- charts + captions"
echo "=============================================================="

# Sanity gate: the shuffled-label controls must sit at chance. If they do not,
# every other number in that directory is uninterpretable, so say so loudly
# here rather than letting it reach a chapter.
"$PY" - "$OUT/accuracy.csv" <<'PYEOF'
import sys
import pandas as pd
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    sys.exit(0)

df = pd.read_csv(path)
ctrl = df[df["labels"] == "shuffled"]
if ctrl.empty:
    sys.exit(0)

chance = float(ctrl["chance"].iloc[0])
bad = ctrl[(ctrl["balanced_accuracy"] - chance).abs() > 0.08]
if bad.empty:
    print(f"control check PASSED - all shuffled-label fits within "
          f"0.08 of chance ({chance:.2f})")
else:
    print()
    print("*** CONTROL CHECK FAILED ***")
    print(bad[["condition", "model", "balanced_accuracy"]].to_string(index=False))
    print(f"A shuffled-label fit should score at chance ({chance:.2f}). Above it")
    print("means the pipeline is leaking - most likely batches from one trial")
    print("landing on both sides of a cross-validation split. Do not report any")
    print("accuracy from this run until that is found.")
    sys.exit(3)
PYEOF
