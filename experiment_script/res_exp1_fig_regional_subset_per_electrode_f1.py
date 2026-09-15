"""Figure 13 — per-electrode detection F1 within each region's own channel-subset rerun.

Companion to Figure 3 (``tab3_fig3_region_performance.py``): Figure 3 shows every electrode scored inside the full 32-channel Proposed-Med run, coloured by scalp region.
This figure shows the same coarse regions' electrodes instead scored inside their OWN
self-contained channel-subset rerun (``selection == "frontal"/"central"/"parietal"/
"occipital"`` in the exp1 results, the same rows Table 17 / ``exp1_subset_data.py``
use), so each bar is one electrode inside its region's own restricted-montage run, not
inside the 32-channel run and not a single-electrode pipeline. Frontopolar electrodes
are already part of the "frontal" subset at the selection level (matching Table 17's
Frontal row), so no separate folding step is needed here, unlike Figure 3.

Writes: writing/figures/fig_exp1_subset_per_electrode.{pdf,png}

Data extraction (for auditing):
  Source CSV : publication_results/exp1_channel_{raja,cao2018}/exp1_channel_selection_
               {raja,cao2018}_results.csv, via ``exp1_subset_data.load_median()`` ->
               ``paper_data.load("exp1", ds)``.
  Filter     : ``center_method == "median"`` only (Proposed-Med; Proposed-Mean rows are
               dropped). Rows further restricted to ``selection`` in
               {frontal, central, parietal, occipital} -- each region's own self-contained
               channel-subset rerun, not the full 32-channel montage.
  Regions    : frontal, central, parietal, occipital (``SUMMARY_REGION_ORDER``);
               frontopolar electrodes are already inside "frontal" at the selection level.

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

SCRIPT = "res_exp1_fig_regional_subset_per_electrode_f1.py"

#: The only four coarse regions shown, matching Figure 3/Table 3 exactly.
SUMMARY_REGION_ORDER = ["frontal", "central", "parietal", "occipital"]


def subset_frame(ds: str) -> pd.DataFrame:
    """One row per electrode: its own mean F1 inside its region's own subset rerun."""
    d = SD.load_median(ds)
    egi_names = P.egi_to_1020() if ds == "raja" else None
    rows = []
    for region in SUMMARY_REGION_ORDER:
        sub = d[d["selection"] == region]
        for ch, grp in sub.groupby("channel"):
            display = egi_names.get(str(ch), "--") if ds == "raja" else P.spell_1020(ch)
            rows.append({"ch": ch, "display": display, "coarse": region,
                         "f1": grp["f1"].mean()})
    return pd.DataFrame(rows).sort_values("f1", ascending=False)


def build_figure(frames: dict) -> None:
    NAVY = S.NAVY
    REGION_COLORS = S.REGION_COLORS

    fig, axes = plt.subplots(2, 1, figsize=(9, 8), sharex=False)
    S.style_fig(fig)

    for ax, ds in zip(axes, ["raja", "cao"]):
        g = frames[ds]
        colors = [REGION_COLORS[r] for r in g["coarse"]]
        pct = g["f1"].to_numpy() * 100

        bars = ax.bar(range(len(g)), pct, color=colors, edgecolor=NAVY,
                       linewidth=0.45, width=0.78)
        ax.bar_label(bars, fmt="%.2f", rotation=45, padding=2, fontsize=S.FONT_INPLOT,
                     color=NAVY)

        ax.set_xticks(range(len(g)))
        ax.set_xticklabels(g["display"], rotation=90, color=NAVY)
        ax.set_title(P.DSN[ds], fontweight="bold", color=NAVY, pad=8)

        ax.set_ylim(0, 100)
        ax.margins(y=0.12)
        ax.set_ylabel(r"Macro-$F_1$ (%)", color=NAVY)

        # style_axis applies the shared chrome font size (S.FONT_CHROME) to the title,
        # axis label and tick labels set above.
        S.style_axis(ax)

    handles = [
        Patch(facecolor=REGION_COLORS[r], edgecolor=NAVY, linewidth=0.4, label=r.capitalize())
        for r in SUMMARY_REGION_ORDER
    ]
    fig.legend(handles=handles, loc="upper center", ncol=len(handles), fontsize=S.FONT_CHROME,
               frameon=False, bbox_to_anchor=(0.5, 1.015))

    fig.suptitle(
        r"Per-electrode detection $F_1$ within each region's own channel-subset rerun",
        y=1.055, fontsize=S.FONT_CHROME, fontweight="bold", color=NAVY,
    )

    fig.tight_layout(rect=[0, 0, 1, 0.97])
    P.save_fig(fig, "fig_exp1_subset_per_electrode")
    plt.close(fig)


def main() -> None:
    frames = {ds: subset_frame(ds) for ds in ["cao","raja"]}
    build_figure(frames)

    for ds in ["cao","raja"]:
        g = frames[ds]
        print(f"{P.DSN[ds]}:")
        for region in SUMMARY_REGION_ORDER:
            sub = g[g.coarse == region].sort_values("f1", ascending=False)
            print(f"  {region} (n={len(sub)}):")
            for _, row in sub.iterrows():
                print(f"    {row['display']:6s} F1={row['f1'] * 100:.2f}")


if __name__ == "__main__":
    main()
