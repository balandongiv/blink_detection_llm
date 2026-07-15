"""Precision-recall operating-point scatter for exp2 (strategy comparison).

Per-session (recall, precision) points for the four visible conditions
(BLINKER-concat, MNE-annot, Proposed-Mean, Proposed-Med), pooled over Raja +
Cao2018, with condition means and iso-F1 contours overlaid.

Source: runs/exp41_cao_30s/exp41_strategy_comparison_results.csv
        (written by experiment_script/exp2_strategy_comparison.py --out-dir runs/exp41_cao_30s)

Produces: writing/figures/fig_exp2_pr_scatter_frontal.pdf, .png

Run inside conda env double_threshold_algo.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "runs" / "exp41_frontal_30s" / "exp41_strategy_comparison_results.csv"
FIGDIR = REPO / "writing" / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)

CONDS = ["Proposed-Med", "Proposed-Mean", "BLINKER-concat", "MNE-annot"]
COLORS = {"Proposed-Med": "#4C72B0", "Proposed-Mean": "#55A868",
          "BLINKER-concat": "#C44E52", "MNE-annot": "#8172B3"}
MARKERS = {"Proposed-Med": "o", "Proposed-Mean": "s",
           "BLINKER-concat": "^", "MNE-annot": "D"}
DSN = {"raja": "Raja", "cao2018": "Cao2018"}


def main() -> None:
    df = pd.read_csv(SRC)

    fig, ax = plt.subplots(figsize=(7.5, 6.5))

    # iso-F1 contours
    r = np.linspace(0.01, 1.0, 200)
    for f1 in (0.2, 0.4, 0.6, 0.8):
        with np.errstate(divide="ignore", invalid="ignore"):
            p = (f1 * r) / (2 * r - f1)
        p = np.where((p > 0) & (p <= 1.0), p, np.nan)
        ax.plot(r, p, color="#bbbbbb", lw=0.8, ls=":", zorder=0)
        valid = ~np.isnan(p)
        if valid.any():
            xi = np.argmax(valid & (r > 0.55))
            if xi:
                ax.annotate(f"F1={f1}", (r[xi], p[xi]), fontsize=7, color="#999999",
                            ha="left", va="bottom")

    summary_lines = []
    for cond in CONDS:
        sub = df[df.condition == cond]
        if sub.empty:
            continue
        ax.scatter(sub["recall"], sub["precision"], s=22, alpha=0.45,
                   color=COLORS[cond], marker=MARKERS[cond], linewidths=0,
                   label=None, zorder=2)
        mean_r, mean_p = sub["recall"].mean(), sub["precision"].mean()
        mean_f1 = sub["f1"].mean()
        ax.scatter([mean_r], [mean_p], s=220, color=COLORS[cond], marker=MARKERS[cond],
                   edgecolor="black", linewidths=1.3, zorder=3,
                   label=f"{cond} (P={mean_p:.3f}, R={mean_r:.3f}, F1={mean_f1:.3f})")
        summary_lines.append((cond, mean_p, mean_r, mean_f1, len(sub)))

    ax.set_xlim(0, 1.02)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Per-session precision-recall operating points (Raja + Cao2018 pooled)\n"
                  "exp2 strategy comparison")
    ax.legend(loc="lower left", fontsize=8, framealpha=0.9)
    fig.tight_layout()
    fig.savefig(FIGDIR / "fig_exp2_pr_scatter_frontal.pdf", bbox_inches="tight")
    fig.savefig(FIGDIR / "fig_exp2_pr_scatter_frontal.png", dpi=150, bbox_inches="tight")
    print("wrote fig_exp2_pr_scatter_frontal.pdf/.png")

    print("\npooled (Raja+Cao2018, frontal-gated) condition means:")
    for cond, p, r, f1, n in summary_lines:
        print(f"  {cond:<15} P={p:.4f}  R={r:.4f}  F1={f1:.4f}  n={n}")

    print("\nper-dataset condition means:")
    for ds in ("raja", "cao2018"):
        sub_ds = df[df.dataset == ds]
        print(f"  [{DSN[ds]}]")
        for cond in CONDS:
            sub = sub_ds[sub_ds.condition == cond]
            if sub.empty:
                continue
            print(f"    {cond:<15} P={sub['precision'].mean():.4f}  "
                  f"R={sub['recall'].mean():.4f}  F1={sub['f1'].mean():.4f}  n={len(sub)}")


if __name__ == "__main__":
    main()
