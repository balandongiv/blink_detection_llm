"""R1 - Precision-recall operating-point scatter for the four conditions.

Per-session (recall, precision) operating points at the best-channel-per-session
row (argmax det_f1 over selections), pooled over Raja + Cao2018, with the four
condition means and iso-$F_1$ contours overlaid. Visualises why Proposed-Med wins:
it sits in the high-precision/high-recall corner while BLINKER-concat clusters at
high-recall/low-precision and MNE-annot at low/low.

Produces:
  writing/figures/fig_pr_scatter.pdf, .png

Aggregation: best-channel-per-session (see writing/VALUE_AUDIT.md). Source CSVs:
runs_second_iteration/exp2_*/. Run inside conda env double_threshold_algo.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
import os
NEW = REPO / os.environ.get("BLINK_RUNS_DIR", "runs_second_iteration")
FIGDIR = REPO / "writing" / "figures"; FIGDIR.mkdir(parents=True, exist_ok=True)

CONDS = ["Proposed-Med", "Proposed-Mean", "BLINKER-concat", "MNE-annot"]
COLORS = {"Proposed-Med": "#4C72B0", "Proposed-Mean": "#55A868",
          "BLINKER-concat": "#C44E52", "MNE-annot": "#8172B3"}
MARKERS = {"Proposed-Med": "o", "Proposed-Mean": "s",
           "BLINKER-concat": "^", "MNE-annot": "D"}


def load(ds):
    fold = "raja" if ds == "raja" else "cao"
    fil = "raja" if ds == "raja" else "cao2018"
    return pd.read_csv(NEW / f"exp2_{fold}" / f"exp2_strategy_comparison_{fil}_results.csv")


def best_per_session(df):
    return df.loc[df.groupby("session")["det_f1"].idxmax()].copy()


# pooled best-channel rows per condition
rows = {c: [] for c in CONDS}
for ds in ["raja", "cao"]:
    df = load(ds)
    for c in CONDS:
        rows[c].append(best_per_session(df[df.condition == c]))
rows = {c: pd.concat(v, ignore_index=True) for c, v in rows.items()}

sns_grey = "0.75"
fig, ax = plt.subplots(figsize=(7.2, 6.4))

# iso-F1 contours: F1 = 2PR/(P+R) -> P = f*R / (2R - f)
Rgrid = np.linspace(0.001, 1.0, 500)
for f in [0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
    with np.errstate(divide="ignore", invalid="ignore"):
        P = (f * Rgrid) / (2 * Rgrid - f)
    valid = (2 * Rgrid - f) > 0
    P = np.where(valid & (P <= 1.0) & (P >= 0.0), P, np.nan)
    ax.plot(Rgrid, P, color=sns_grey, lw=0.8, ls="--", zorder=1)
    # label near R=0.98
    ri = np.argmin(np.abs(Rgrid - 0.985))
    if not np.isnan(P[ri]):
        ax.text(0.99, P[ri], f"$F_1$={f:g}", color="0.45", fontsize=7,
                ha="left", va="center")

# per-session points
for c in CONDS:
    d = rows[c]
    ax.scatter(d.det_recall, d.det_precision, s=18, alpha=0.32,
               color=COLORS[c], marker=MARKERS[c], edgecolors="none", zorder=2)

# condition means (large markers)
for c in CONDS:
    d = rows[c]
    mr, mp = d.det_recall.mean(), d.det_precision.mean()
    ax.scatter([mr], [mp], s=240, color=COLORS[c], marker=MARKERS[c],
               edgecolors="black", linewidths=1.4, zorder=4,
               label=f"{c} (P={mp:.2f}, R={mr:.2f})")

ax.set_xlim(0.0, 1.02)
ax.set_ylim(0.0, 1.02)
ax.set_xlabel("Event-level recall")
ax.set_ylabel("Event-level precision")
ax.set_title("Per-session operating points (best channel per session, 104 sessions)")
ax.legend(loc="lower left", fontsize=8.5, framealpha=0.92)
ax.grid(True, color="0.92", lw=0.6)
fig.tight_layout()
fig.savefig(FIGDIR / "fig_pr_scatter.pdf", bbox_inches="tight")
fig.savefig(FIGDIR / "fig_pr_scatter.png", dpi=150, bbox_inches="tight")
print("wrote fig_pr_scatter.pdf/.png")
for c in CONDS:
    d = rows[c]
    print(f"  {c:15s} mean P={d.det_precision.mean():.4f} R={d.det_recall.mean():.4f} "
          f"F1={d.det_f1.mean():.4f} n={len(d)}")
