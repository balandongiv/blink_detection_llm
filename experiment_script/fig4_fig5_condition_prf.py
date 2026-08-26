"""Figures 4 and 5 — headline strategy-comparison figures.

Writes:
  ``writing/figures/fig_condition_prf.{pdf,png}``   pooled precision/recall/F1 per condition
  ``writing/figures/fig_f1_by_dataset.{pdf,png}``   per-condition F1, Raja vs Cao2018

Both read the same best-channel-per-session rows as Table 4, so figure and table cannot
disagree. The epoch-duration curve that used to live here is now produced by
``tab13_fig10_epoch_duration.py`` alongside its table.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402

COLORS = {"BLINKER-concat": "#C44E52", "MNE-annot": "#8172B3",
          "Proposed-Mean": "#DD8452", "Proposed-Med": "#4C72B0"}
METRICS = [("precision", "Precision"), ("recall", "Recall"), ("f1", "$F_1$")]


def main() -> None:
    best = P.load_exp2_best()
    n_sessions = sum(len(best[(ds, "Proposed-Med")]) for ds in ["raja", "cao"])

    def pooled(cond, column):
        return pd.concat([best[("raja", cond)], best[("cao", cond)]])[column].mean()

    # --- Figure 4: pooled precision / recall / F1 grouped bars ---
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(METRICS))
    width = 0.2
    for i, cond in enumerate(P.CONDS):
        values = [pooled(cond, col) for col, _ in METRICS]
        ax.bar(x + (i - 1.5) * width, values, width, label=cond, color=COLORS[cond])
    ax.set_xticks(x)
    ax.set_xticklabels([label for _, label in METRICS])
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Macro-averaged score")
    ax.legend(fontsize=8, ncol=2)
    ax.set_title(f"Pooled performance over all {n_sessions} sessions")
    fig.tight_layout()
    P.save_fig(fig, "fig_condition_prf")
    plt.close(fig)

    # --- Figure 5: F1 per condition, split by dataset ---
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(P.CONDS))
    width = 0.38
    ax.bar(x - width / 2, [P.macro(best, "raja", c)[2] for c in P.CONDS], width,
           label=P.DSN["raja"], color="#4C72B0")
    ax.bar(x + width / 2, [P.macro(best, "cao", c)[2] for c in P.CONDS], width,
           label="Cao2018", color="#55A868")
    ax.set_xticks(x)
    ax.set_xticklabels(P.CONDS, rotation=15, fontsize=9)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Macro-averaged $F_1$")
    ax.legend()
    ax.set_title("Per-condition $F_1$ by dataset")
    fig.tight_layout()
    P.save_fig(fig, "fig_f1_by_dataset")
    plt.close(fig)


if __name__ == "__main__":
    main()
