"""R1 - Precision-recall operating-point scatter for the four conditions.

Per-session (recall, precision) operating points at the best-channel-per-session
row (argmax f1 over selections), pooled over Raja + Cao2018, with the four
condition means and iso-$F_1$ contours overlaid. Visualises why Proposed-Med wins:
it sits in the high-precision/high-recall corner while BLINKER-concat clusters at
high-recall/low-precision and MNE-annot at low/low.

Produces:
  writing/figures/fig_pr_scatter.pdf, .png

Aggregation: best-channel-per-session (see writing/VALUE_AUDIT.md). Source CSVs:
publication_results/exp2_*/. Run inside conda env double_threshold_algo.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as PD  # noqa: E402
import paper_style as S  # noqa: E402

CONDS = ["Proposed-Med", "Proposed-Mean", "BLINKER-concat", "MNE-annot"]
COLORS = S.CONDITION_COLORS
MARKERS = {"Proposed-Med": "o", "Proposed-Mean": "s",
           "BLINKER-concat": "^", "MNE-annot": "D"}

# pooled best-channel rows per condition
best = PD.load_exp2_best()
rows = {c: pd.concat([best[("raja", c)], best[("cao", c)]], ignore_index=True)
        for c in CONDS}
n_sessions = len(rows["Proposed-Med"])

fig, ax = plt.subplots(figsize=(7.2, 6.4))
S.style_fig(fig)

# iso-F1 contours: F1 = 2PR/(P+R) -> P = f*R / (2R - f)
Rgrid = np.linspace(0.001, 1.0, 500)
for f in [0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
    with np.errstate(divide="ignore", invalid="ignore"):
        P = (f * Rgrid) / (2 * Rgrid - f)
    valid = (2 * Rgrid - f) > 0
    P = np.where(valid & (P <= 1.0) & (P >= 0.0), P, np.nan)
    ax.plot(Rgrid, P, color=S.PANEL_BLUE, lw=0.8, ls="--", zorder=1)
    # label near R=0.98
    ri = np.argmin(np.abs(Rgrid - 0.985))
    if not np.isnan(P[ri]):
        ax.text(0.99, P[ri], f"$F_1$={f:g}", color=S.PANEL_BLUE, fontsize=7,
                ha="left", va="center")

# per-session points
for c in CONDS:
    d = rows[c]
    ax.scatter(d.recall, d.precision, s=18, alpha=0.32,
               color=COLORS[c], marker=MARKERS[c], edgecolors="none", zorder=2)

# condition means (large markers)
for c in CONDS:
    d = rows[c]
    mr, mp = d.recall.mean(), d.precision.mean()
    ax.scatter([mr], [mp], s=240, color=COLORS[c], marker=MARKERS[c],
               edgecolors=S.NAVY, linewidths=1.4, zorder=4,
               label=f"{c} (P={mp:.2f}, R={mr:.2f})")

ax.set_xlim(0.0, 1.02)
ax.set_ylim(0.0, 1.02)
ax.set_xlabel("Event-level recall")
ax.set_ylabel("Event-level precision")
ax.set_title(f"Per-session operating points (best channel per session, {n_sessions} sessions)")
S.style_axis(ax, grid_axis="both")
legend = ax.legend(loc="lower left", fontsize=8.5, framealpha=0.92)
for text in legend.get_texts():
    text.set_color(S.NAVY)
fig.tight_layout()
PD.save_fig(fig, "fig_pr_scatter")
for c in CONDS:
    d = rows[c]
    print(f"  {c:15s} mean P={d.precision.mean():.4f} R={d.recall.mean():.4f} "
          f"F1={d.f1.mean():.4f} n={len(d)}")
