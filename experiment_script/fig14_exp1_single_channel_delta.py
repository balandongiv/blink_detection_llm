"""Figure 14 — configuration effect: single-electrode minus full-montage $F_1$ per electrode.

Companion to Figure 2 (``fig2_exp1_single_channel_boxplot.py``) and Figure 16
(``fig16_exp1_single_channel_stats.py``): Figure 2 shows absolute single-electrode
performance; this figure shows the same electrodes' paired difference against their
own full-montage row, $\\Delta F_1 = F_{1,\\mathrm{single}} - F_{1,\\mathrm{full}}$, so a
bar left of zero means the electrode performed worse operating alone. Electrodes are
grouped and ordered exactly as in Figure 2/Figure 16 (region, then descending
single-electrode $F_1$ within region) so the figures can be read side by side.

Writes: writing/figures/fig_exp1_single_channel_delta.{pdf,png}

Run inside conda env double_threshold_algo.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402
import paper_style as S  # noqa: E402
from fig2_exp1_single_channel_boxplot import solo_frame, REGION_ORDER, REGION_LABEL  # noqa: E402


def build_figure(frames: dict) -> None:
    NAVY = S.NAVY
    REGION_COLORS = S.REGION_COLORS

    fig, axes = plt.subplots(1, 2, figsize=(11, 9), sharex=True)
    S.style_fig(fig)

    for ax, ds in zip(axes, ["raja", "cao"]):
        g = frames[ds].iloc[::-1].reset_index(drop=True)  # top-to-bottom = Figure 2 order
        colors = [REGION_COLORS[r] for r in g["region"]]
        pp = g["delta"].to_numpy() * 100

        ax.barh(range(len(g)), pp, color=colors, edgecolor=NAVY, linewidth=0.45, height=0.78)
        ax.axvline(0, color=NAVY, linewidth=0.9)

        ax.set_yticks(range(len(g)))
        ax.set_yticklabels(g["channel"], color=NAVY)
        ax.set_title(P.DSN[ds], fontweight="bold", color=NAVY, pad=8)
        ax.set_xlabel(r"$\Delta F_1$ (pp), single $-$ full montage", color=NAVY)
        ax.set_ylim(-1, len(g))

        # style_axis applies the shared chrome font size (S.FONT_CHROME) to the title,
        # axis label and tick labels set above.
        S.style_axis(ax, grid_axis="x")

    handles = [
        Patch(facecolor=REGION_COLORS[r], edgecolor=NAVY, linewidth=0.4, label=REGION_LABEL[r])
        for r in REGION_ORDER
        if r in set(frames["raja"]["region"]) | set(frames["cao"]["region"])
    ]
    fig.legend(handles=handles, loc="upper center", ncol=len(handles), fontsize=S.FONT_CHROME,
               frameon=False, bbox_to_anchor=(0.5, 1.03))

    fig.suptitle(
        r"Configuration effect: single-electrode $F_1$ minus the same electrode's "
        r"full-montage $F_1$",
        y=1.07, fontsize=S.FONT_CHROME, fontweight="bold", color=NAVY,
    )

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    P.save_fig(fig, "fig_exp1_single_channel_delta")
    plt.close(fig)


def main() -> None:
    frames = {ds: solo_frame(ds) for ds in ["raja", "cao"]}
    build_figure(frames)
    for ds in ["raja", "cao"]:
        g = frames[ds]
        print(f"{P.DSN[ds]}: delta range "
              f"[{g['delta'].min()*100:+.2f}, {g['delta'].max()*100:+.2f}] pp")


if __name__ == "__main__":
    main()
