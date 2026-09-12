"""Precision-recall operating-point scatter for exp2 (strategy comparison).

Per-session (recall, precision) points for the three reported conditions
(BLINKER-concat, MNE-annot, Proposed-Med), Raja and Cao2018 shown SEPARATELY
(not pooled) in the same figure. Marker shape encodes the condition, color
encodes the dataset, so the two datasets can be compared side by side per
condition. Proposed-Mean's results are not reported in this section, so it is
excluded here too.

Source: runs/exp2_raja/exp2_strategy_comparison_raja_results.csv
        runs/exp2_cao/exp2_strategy_comparison_cao2018_results.csv
        (written by experiment_script/exp2_a_strategy_comparison_raja.py /
        exp2_a_strategy_comparison_cao2018.py), filtered to the "all_channel" selection
        group — one row per (session, condition) there, i.e. one PR operating point.

Produces: writing/figures/fig_exp2_pr_scatter.pdf, .png

Run inside conda env double_threshold_algo.
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.project_paths import EXP_SETUP_DIR, load_exp_config  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402
import paper_style as S  # noqa: E402

_PATH_CFG = load_exp_config(EXP_SETUP_DIR / "exp_path.yaml")
RAJA_SRC = REPO / Path(_PATH_CFG["out_dirs"]["exp2"]["raja"]) / "exp2_strategy_comparison_raja_results.csv"
CAO_SRC  = REPO / Path(_PATH_CFG["out_dirs"]["exp2"]["cao2018"]) / "exp2_strategy_comparison_cao2018_results.csv"
SELECTION = "all_channel"
FIGDIR = REPO / "writing" / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)

CONDS = ["Proposed-Med", "BLINKER-concat", "MNE-annot"]
MARKERS = {"Proposed-Med": "o", "BLINKER-concat": "^", "MNE-annot": "D"}
DSN = {"raja": "Internal", "cao2018": "Cao2018"}
DS_COLORS = {"raja": S.DATASET_COLORS["Internal"], "cao2018": S.DATASET_COLORS["Cao2018"]}


def main() -> None:
    df = pd.concat([pd.read_csv(RAJA_SRC), pd.read_csv(CAO_SRC)], ignore_index=True)
    df = df[df["selection"] == SELECTION]

    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    S.style_fig(fig)

    summary_lines = []
    for ds in ("raja", "cao2018"):
        sub_ds = df[df.dataset == ds]
        for cond in CONDS:
            sub = sub_ds[sub_ds.condition == cond]
            if sub.empty:
                continue
            ax.scatter(sub["recall"] * 100, sub["precision"] * 100, s=22, alpha=0.4,
                       color=DS_COLORS[ds], marker=MARKERS[cond], linewidths=0,
                       zorder=2)
            mean_r, mean_p = sub["recall"].mean(), sub["precision"].mean()
            mean_f1 = sub["f1"].mean()
            ax.scatter([mean_r * 100], [mean_p * 100], s=200, color=DS_COLORS[ds],
                       marker=MARKERS[cond], edgecolor=S.NAVY, linewidths=1.3, zorder=3)
            summary_lines.append((ds, cond, mean_p, mean_r, mean_f1, len(sub)))

    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xlabel("Recall (%)")
    ax.set_ylabel("Precision (%)")
    # No in-plot title: the LaTeX caption carries it, and an F1=80 contour label sitting
    # near the top of a 0-100 axis would otherwise crowd a title drawn just above the axes.
    S.style_axis(ax, grid_axis="both")

    # two-part legend: marker shape -> condition, color -> dataset. Labels go through
    # P.display() so they match Table 1's naming (BLINKER, MNE, Proposed-approach), not
    # the raw CONDS/data-key strings (BLINKER-concat, MNE-annot, Proposed-Med).
    cond_handles = [
        Line2D([0], [0], marker=MARKERS[c], color="none", markerfacecolor=S.PANEL_BLUE,
               markeredgecolor=S.NAVY, markersize=9, label=P.display(c))
        for c in CONDS
    ]
    ds_handles = [Patch(facecolor=DS_COLORS[ds], edgecolor=S.NAVY, label=DSN[ds])
                  for ds in ("raja", "cao2018")]
    legend1 = ax.legend(handles=cond_handles, title="Condition (shape)",
                         loc="lower left", fontsize=S.FONT_CHROME,
                         title_fontsize=S.FONT_CHROME, framealpha=0.9)
    ax.add_artist(legend1)
    legend2 = ax.legend(handles=ds_handles, title="Dataset (color)",
                         loc="lower right", fontsize=S.FONT_CHROME,
                         title_fontsize=S.FONT_CHROME, framealpha=0.9)
    for legend in (legend1, legend2):
        legend.get_title().set_color(S.NAVY)
        for text in legend.get_texts():
            text.set_color(S.NAVY)

    fig.tight_layout()
    fig.savefig(FIGDIR / "fig_exp2_pr_scatter.pdf", bbox_inches="tight")
    fig.savefig(FIGDIR / "fig_exp2_pr_scatter.png", dpi=150, bbox_inches="tight")
    print("wrote fig_exp2_pr_scatter.pdf/.png")

    print("\nper-dataset condition means:")
    for ds in ("raja", "cao2018"):
        print(f"  [{DSN[ds]}]")
        for _ds, cond, p, r, f1, n in summary_lines:
            if _ds != ds:
                continue
            print(f"    {cond:<15} P={p:.4f}  R={r:.4f}  F1={f1:.4f}  n={n}")


if __name__ == "__main__":
    main()
