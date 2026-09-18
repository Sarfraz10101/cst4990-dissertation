import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(9.5, 5.2), dpi=200)
ax.set_xlim(0, 10)
ax.set_ylim(0, 5.6)
ax.axis("off")

def box(x, y, w, h, text, fc="#eef2f8", ec="#334155", fontsize=9.5, weight="normal"):
    b = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08,rounding_size=0.08",
                        linewidth=1.2, edgecolor=ec, facecolor=fc)
    ax.add_patch(b)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
             fontsize=fontsize, weight=weight, color="#1e293b", wrap=True)
    return b

def arrow(x1, y1, x2, y2, style="-|>", color="#334155", lw=1.3, connectionstyle="arc3,rad=0"):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=14,
                         linewidth=lw, color=color, connectionstyle=connectionstyle)
    ax.add_patch(a)

# Outer VM boundary
vm = FancyBboxPatch((0.25, 1.55), 9.5, 3.85, boxstyle="round,pad=0.05,rounding_size=0.1",
                     linewidth=1.5, edgecolor="#94a3b8", facecolor="none", linestyle="--")
ax.add_patch(vm)
ax.text(0.5, 5.15, "Lubuntu guest (4 vCPU, pinned to host performance cores)",
        fontsize=9, style="italic", color="#475569")

# Victim side
box(0.7, 3.3, 3.0, 1.3, "collect.py\n(victim)\npinned to vCPU 0\nsendto() over loopback", fc="#e0f2fe", fontsize=9)
box(4.2, 3.3, 2.6, 1.3, "nftables INPUT\nchain\n(verdict + rule\ndepth evaluated)", fc="#e0f2fe", fontsize=9)
arrow(3.7, 3.95, 4.2, 3.95)
arrow(6.8, 3.95, 6.8, 3.6, connectionstyle="arc3,rad=-0.4")

box(6.8, 3.3, 2.5, 1.3, "ns_per_pkt\nrecorded per\npacket, per batch", fc="#e0f2fe", fontsize=9)

# Noise injector
box(0.7, 1.8, 3.0, 1.2, "noise.py\n(defence)\n3 worker processes\nPoisson / reactive bursts", fc="#fef3c7", fontsize=9)
arrow(2.2, 3.0, 2.2, 3.3, style="-|>", color="#b45309")
ax.text(2.2, 3.13, "same core\n(--noise-cpus 0)\nor other vCPUs\n(default)",
        fontsize=7, ha="center", color="#b45309", style="italic")

box(4.2, 1.8, 5.1, 1.2, "firewall.py — generates/applies one of 4 nftables\nconfigurations per trial (accept/drop x shallow/deep)",
    fc="#f1f5f9", fontsize=8.7)

# Downstream pipeline
ax.text(5.0, 1.35, "run*.csv (tidy long format)", fontsize=8.5, ha="center", color="#1e293b")
arrow(6.85, 3.3, 5.0, 1.6, connectionstyle="arc3,rad=0.25", color="#64748b")
arrow(5.0, 1.5, 5.0, 1.05)

pipeline_x = [0.4, 2.05, 3.7, 5.35, 7.0]
labels = ["features.py", "attack.py", "stats.py", "sweep.py", "figures.py"]
for i, (x, lab) in enumerate(zip(pipeline_x, labels)):
    box(x, 0.15, 1.5, 0.7, lab, fc="#dcfce7", fontsize=8.3, ec="#166534")
    if i > 0:
        arrow(pipeline_x[i-1] + 1.5, 0.5, x, 0.5, color="#166534")

ax.text(9.6, 0.5, "results/*/\nSTATS_SUMMARY.md\n+ figures/", fontsize=7.5, ha="left", va="center", color="#166534")
arrow(8.5, 0.5, 9.15, 0.5, color="#166534")

plt.tight_layout()
plt.savefig(r"C:\Users\abdul\CST4990-dissertation\build\assets\ch3_architecture.png",
            dpi=200, bbox_inches="tight", facecolor="white")
print("saved")
