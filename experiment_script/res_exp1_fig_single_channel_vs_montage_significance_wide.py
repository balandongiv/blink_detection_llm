"""Full-width (7.16 in, IEEE figure*) variant of the per-electrode single vs. montage figure.

Reuses ``ordered`` (data + Bonferroni family) and ``fmt_sig`` from
``res_exp1_fig_single_channel_vs_montage_significance`` unchanged; only the layout differs
(panels side by side, 7 pt fonts, bold Fp1/Fp2 ticks, shared legend on top).

Writes ``writing/figures/fig_exp1_single_channel_stats_wide.pdf`` only.
Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402
import paper_style as S  # noqa: E402
import res_exp1_fig_single_channel_vs_montage_significance as O  # noqa: E402

FS = 7  # minimum font size at final print size


def build_figure(data) -> None:
    NAVY, PAGE_BG, PANEL_BLUE = S.NAVY, S.PAGE_BG, S.PANEL_BLUE
    fig, axes = plt.subplots(1, 2, figsize=(7.16, 2.6), gridspec_kw={"wspace": 0.12})
    S.style_fig(fig)
    letters = {"raja": "A", "cao": "B"}

    for ax, ds in zip(axes, ["raja", "cao"]):
        df, _ = data[ds]
        n = len(df)
        x = np.arange(n)
        colors = [S.REGION_COLORS[r] for r in df["region"]]
        montage = df["gated_f1"].to_numpy() * 100
        single = df["solo_f1"].to_numpy() * 100

        regions = df["region"].tolist()
        boundaries, start = [], 0
        for i in range(1, n + 1):
            if i == n or regions[i] != regions[start]:
                boundaries.append((start, i, regions[start]))
                start = i
        for gi, (s0, e0, region) in enumerate(boundaries):
            if gi % 2 == 1:
                ax.axvspan(s0 - 0.5, e0 - 0.5, color=PAGE_BG, zorder=0)
            if s0 > 0:
                ax.axvline(s0 - 0.5, color=PANEL_BLUE, linewidth=0.7, zorder=1)
            ax.text((s0 + e0 - 1) / 2, 107, O.REGION_LABEL[region], ha="center",
                    va="bottom", fontsize=FS, fontweight="bold",
                    color=S.REGION_COLORS[region])

        ax.bar(x, montage, width=0.84, color=colors, alpha=0.35,
               edgecolor=NAVY, linewidth=0.4, zorder=2)
        ax.bar(x, single, width=0.46, color=colors, alpha=1.0,
               edgecolor=NAVY, linewidth=0.5, zorder=3)

        for i, row in df.iterrows():
            star = O.fmt_sig(row)
            if star:
                ax.text(i, max(montage[i], single[i]) + 0.5, star, ha="center",
                        va="bottom", fontsize=FS + 1, color=NAVY, fontweight="bold")

        ax.set_xlim(-0.7, n - 0.3)
        ax.set_xticks(x)
        ax.set_xticklabels(df["channel"], rotation=90, color=NAVY)
        ax.set_ylim(0, 114)
        ax.set_yticks([0, 20, 40, 60, 80, 100])
        ax.set_title(f"({letters[ds]}) {P.DSN[ds]}", fontweight="bold", color=NAVY, pad=12)
        S.style_axis(ax, grid_axis="y")
        ax.title.set_size(FS + 1)
        ax.tick_params(axis="both", labelsize=FS, length=2, pad=1.5)
        for lab in ax.get_xticklabels():
            if lab.get_text() in ("Fp1", "Fp2"):
                lab.set_fontweight("bold")

    axes[0].set_ylabel(r"$F_1$ (%)", color=NAVY, fontsize=FS)
    axes[1].tick_params(axis="y", labelleft=False)

    handles = [
        Patch(facecolor=S.EEG_BLUE, alpha=1.0, edgecolor=NAVY, linewidth=0.5, label="Single"),
        Patch(facecolor=S.EEG_BLUE, alpha=0.35, edgecolor=NAVY, linewidth=0.5, label="Montage"),
    ]
    fig.legend(handles=handles, loc="upper center", ncol=2, fontsize=FS, frameon=False,
               bbox_to_anchor=(0.5, 1.03))
    fig.subplots_adjust(left=0.065, right=0.995, bottom=0.17, top=0.80)
    fig.savefig(P.FIGDIR / "fig_exp1_single_channel_stats_wide.pdf", bbox_inches="tight")
    print("wrote figures/fig_exp1_single_channel_stats_wide.pdf")
    plt.close(fig)


def main() -> None:
    build_figure({ds: O.ordered(ds) for ds in ["raja", "cao"]})


if __name__ == "__main__":
    main()
