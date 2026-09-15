"""Figure 2 — every full-montage electrode operating as its own self-contained detector.

Companion to Figure 3 (``tab3_fig3_region_performance.py``): Figure 3 shows every
electrode scored inside the full 32-channel Proposed-Med run. This figure instead shows
every electrode scored by its OWN independent single-electrode ("*_only") detector —
Stage~A, Stage~B and Stage~C all rerun on that one channel alone — so each bar answers
"which electrode performs best when the entire detector is restricted to it?", not
"which electrode contributes most inside the full montage?".

Restricted to the same four curated anatomical regions Figure 3/Table 3 report (frontal,
central, parietal, occipital; frontopolar folded into frontal) via the same
``SUMMARY_REGION_ORDER`` filter ``tab3_fig3_region_performance._figure_frame`` applies, so
this figure's electrode set is identical to "the full-montage analysis" it is a companion
to (24 electrodes on Internal, 18 on Cao2018). Electrodes outside those four regions
(midline/edge sites, and on Cao2018 the A1/A2 mastoid references) are excluded from the
figure entirely rather than shown as extra "Midline/edge"/"Unassigned" categories.

Writes: writing/figures/fig_exp1_single_channel_boxplot.{pdf,png}
(filename kept from the retired boxplot version so `sec.tex`'s \\includegraphics and
`fig:exp1_single_channel` need no change.)

Data extraction (for auditing):
  Source CSV : publication_results/exp1_channel_{raja,cao2018}/exp1_channel_selection_
               {raja,cao2018}_results.csv, via ``exp1_subset_data.solo_vs_montage()``
               (internally ``load_median()`` -> ``paper_data.load("exp1", ds)``).
  Filter     : ``center_method == "median"`` only (Proposed-Med). Restricted to
               single-electrode ("``*_only``") self-contained runs -- Stage A/B/C all
               rerun on one channel alone -- not the full-montage run.
  Regions    : frontal, central, parietal, occipital (``REGION_ORDER``); 24 electrodes on
               Internal, 18 on Cao2018. Midline/edge sites and (Cao2018) A1/A2 mastoid
               references are excluded entirely.

Run inside conda env double_threshold_algo.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402
import paper_style as S  # noqa: E402
import exp1_subset_data as SD  # noqa: E402

SCRIPT = "res_exp1_fig_single_channel_boxplot_by_region.py"

#: Region display order -- the same four curated anatomical regions Figure 3/Table 3
#: report (frontopolar folded into "frontal" by solo_channel_region), so this figure's
#: electrode set matches "the full-montage analysis" exactly. Electrodes outside these
#: four regions (midline/edge sites, unassigned/mastoid references) are dropped rather
#: than shown as extra categories.
REGION_ORDER = ["frontal", "central", "parietal", "occipital"]
REGION_LABEL = {
    "frontal": "Frontal", "central": "Central", "parietal": "Parietal",
    "occipital": "Occipital",
}


def solo_frame(ds: str) -> pd.DataFrame:
    """One row per electrode: its own single-electrode mean $F_1$, region-coloured.

    Restricted to the four curated regions in ``REGION_ORDER`` -- matches
    ``tab3_fig3_region_performance._figure_frame``'s own
    ``d[d["coarse"].isin(SUMMARY_REGION_ORDER)]`` filter for the full-montage analysis.
    """
    t = SD.solo_vs_montage(ds)
    regions = SD.solo_channel_region(ds)
    t = t.copy()
    t["region"] = t["channel"].map(regions)
    t = t[t["region"].isin(REGION_ORDER)]
    blocks = [t[t.region == r].sort_values("solo_f1", ascending=False) for r in REGION_ORDER]
    return pd.concat(blocks, ignore_index=True)


def build_figure(frames: dict) -> None:
    NAVY = S.NAVY
    REGION_COLORS = S.REGION_COLORS

    fig, axes = plt.subplots(2, 1, figsize=(12, 9), sharex=False)
    S.style_fig(fig)

    present_regions: list[str] = []
    for ax, ds in zip(axes, ["raja", "cao"]):
        g = frames[ds]
        present_regions = [r for r in REGION_ORDER if (g["region"] == r).any()] or present_regions
        colors = [REGION_COLORS[r] for r in g["region"]]
        pct = g["solo_f1"].to_numpy() * 100

        bars = ax.bar(range(len(g)), pct, color=colors, edgecolor=NAVY,
                       linewidth=0.45, width=0.78)
        ax.bar_label(bars, fmt="%.1f", rotation=90, padding=2, fontsize=S.FONT_INPLOT,
                     color=NAVY)

        ax.set_xticks(range(len(g)))
        ax.set_xticklabels(g["channel"], rotation=90, color=NAVY)
        ax.set_title(P.DSN[ds], fontweight="bold", color=NAVY, pad=8)

        ax.set_ylim(0, 100)
        ax.margins(y=0.14)
        ax.set_ylabel(r"Single-electrode macro-$F_1$ (%)", color=NAVY)

        # style_axis applies the shared chrome font size (S.FONT_CHROME) to the title,
        # axis label and tick labels set above.
        S.style_axis(ax)

    handles = [
        Patch(facecolor=REGION_COLORS[r], edgecolor=NAVY, linewidth=0.4, label=REGION_LABEL[r])
        for r in REGION_ORDER
        if r in set(frames["raja"]["region"]) | set(frames["cao"]["region"])
    ]
    fig.legend(handles=handles, loc="upper center", ncol=len(handles), fontsize=S.FONT_CHROME,
               frameon=False, bbox_to_anchor=(0.5, 1.02))

    fig.suptitle(
        r"Detection $F_1$ of every full-montage electrode operating as its own "
        r"self-contained detector",
        y=1.06, fontsize=S.FONT_CHROME, fontweight="bold", color=NAVY,
    )

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    P.save_fig(fig, "fig_exp1_single_channel_boxplot")
    plt.close(fig)


def main() -> None:
    frames = {ds: solo_frame(ds) for ds in ["raja", "cao"]}
    build_figure(frames)

    for ds in ["raja", "cao"]:
        g = frames[ds]
        print(f"{P.DSN[ds]}: {len(g)} electrodes tested")
        for region in REGION_ORDER:
            sub = g[g.region == region]
            if sub.empty:
                continue
            print(f"  {REGION_LABEL[region]} (n={len(sub)}):")
            for _, row in sub.iterrows():
                print(f"    {row['channel']:6s} F1={row['solo_f1'] * 100:.2f}")


if __name__ == "__main__":
    main()
