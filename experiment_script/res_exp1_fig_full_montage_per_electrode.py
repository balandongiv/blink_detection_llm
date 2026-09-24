"""Per-electrode detection F1 inside the full 32-channel Proposed-Med montage.

Companion to Figure 3 (``res_exp1_fig_regional_subset_per_electrode_f1.py``, i.e.
``fig_exp1_subset_per_electrode``): that figure shows each curated electrode scored
inside its OWN region's self-contained channel-subset rerun. This figure instead shows
the same curated electrodes scored inside the full 32-channel montage run
(``selection == "all_channel"``), the baseline reported in prose in
Section~\\ref{sec:exp1_reference} / ``p04_per_electrode/paragraph_per_electrode.tex``,
which currently has no accompanying figure.

A pre-existing rendered figure (``writing/figures/fig_region_performance.pdf``,
plotted from the exact same underlying values) already exists but is mistitled
"Single-channel detection F1 by electrode and scalp region" -- the data plotted there
is full-montage, not single-channel (compare against Figure 5's single-channel values,
which differ). Its generator script (``experiment_script/tab3_fig3_region_performance.py``)
no longer exists in the repo, so this script regenerates the same figure from source,
correctly titled and captioned, using the shared paper_data/paper_style house style.

Writes: writing/figures/fig_exp1_full_montage_per_electrode.{pdf,png}

Data extraction (for auditing):
  Source CSV : Cao2018 -- publication_results/exp1_channel_cao/sessions/*.csv
               (concatenated directly; the top-level
               exp1_channel_selection_cao2018_results.csv currently on disk is a
               pre-aggregated pivot export, not raw per-session data, so it is
               bypassed here rather than depended on or modified).
               Internal  -- publication_results/exp1_channel_raja/
               exp1_channel_selection_raja_results.csv (already raw per-session data).
  Filter     : center_method == "median" (Proposed-Med) and selection == "all_channel"
               (full 32-channel montage), restricted to the electrodes that also
               appear under selection in {frontal, central, parietal, occipital} for
               that dataset (18 electrodes on Cao2018, 24 on Internal -- the same
               curated set used by Figures 3-6).
  Regions    : coarse region taken directly from each electrode's own
               selection == {frontal,central,parietal,occipital} membership in the
               same results CSV (not brain_region_*.yaml's fine left/right split),
               matching how Figures 3/4 assign region colour.

Independently cross-checked against validation_pivot/exp1_channel_selection_
{cao2018,raja}_results.xlsx, sheet full_montage_per_electrode (genuine Excel
PivotTable, same filters) -- all 42 values (18 Cao2018 + 24 Internal) matched to
6 significant figures.

Run inside conda env double_threshold_algo (or any env with pandas/matplotlib).
"""
from __future__ import annotations

import glob
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

SCRIPT = "res_exp1_fig_full_montage_per_electrode.py"
REPO = Path(__file__).resolve().parents[1]

SUMMARY_REGION_ORDER = ["frontal", "central", "parietal", "occipital"]


def _load_raw(ds: str) -> pd.DataFrame:
    if ds == "cao":
        files = sorted(glob.glob(str(REPO / "publication_results" / "exp1_channel_cao"
                                       / "sessions" / "*.csv")))
        if not files:
            raise SystemExit("no session CSVs found for Cao2018 exp1")
        return pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    path = REPO / "publication_results" / "exp1_channel_raja" \
        / "exp1_channel_selection_raja_results.csv"
    return pd.read_csv(path)


def full_montage_frame(ds: str) -> pd.DataFrame:
    """One row per curated electrode: its mean F1 inside the full 32-channel montage."""
    df = _load_raw(ds)
    m = df[df["center_method"] == "median"]

    sel = m[m["selection"].isin(SUMMARY_REGION_ORDER)]
    region_of = sel.groupby("channel")["selection"].agg(lambda s: sorted(set(s))[0])

    fm = m[(m["selection"] == "all_channel") & (m["channel"].isin(region_of.index))]
    g = fm.groupby("channel")["f1"].mean().rename("f1").reset_index()
    g["coarse"] = g["channel"].map(region_of)
    g["display"] = g["channel"].apply(lambda c: P.display_channel(ds, c))
    return g.sort_values("f1", ascending=False)


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

        S.style_axis(ax)

    handles = [
        Patch(facecolor=REGION_COLORS[r], edgecolor=NAVY, linewidth=0.4, label=r.capitalize())
        for r in SUMMARY_REGION_ORDER
    ]
    fig.legend(handles=handles, loc="upper center", ncol=len(handles), fontsize=S.FONT_CHROME,
               frameon=False, bbox_to_anchor=(0.5, 1.015))

    fig.suptitle(
        r"Per-electrode detection $F_1$ under the full 32-channel montage",
        y=1.055, fontsize=S.FONT_CHROME, fontweight="bold", color=NAVY,
    )

    fig.tight_layout(rect=[0, 0, 1, 0.97])
    P.save_fig(fig, "fig_exp1_full_montage_per_electrode")
    plt.close(fig)


def main() -> None:
    frames = {ds: full_montage_frame(ds) for ds in ["cao", "raja"]}
    build_figure(frames)

    for ds in ["cao", "raja"]:
        g = frames[ds]
        print(f"{P.DSN[ds]}:")
        for region in SUMMARY_REGION_ORDER:
            sub = g[g.coarse == region].sort_values("f1", ascending=False)
            print(f"  {region} (n={len(sub)}):")
            for _, row in sub.iterrows():
                print(f"    {row['display']:6s} F1={row['f1'] * 100:.2f}")


if __name__ == "__main__":
    main()
