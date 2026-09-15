"""Figure 16 -- every full-montage electrode as its own self-contained detector, paired
against the same electrode scored inside the full-montage run.

Replaces the former Table 18 (``tab18_exp1_solo_vs_montage.py``, now removed) with an
overlaid bar-chart figure showing the same per-electrode comparison instead of a
64-row longtable, in the same style as Figure 15 (``res_exp1_fig_regional_subset_vs_montage_significance.py``,
the companion figure for the regional-subset section). Each ``*_only`` subset runs Stage~A,
Stage~B and Stage~C on one electrode, so pairing each against that electrode's row inside the
full-montage run isolates what the remaining electrodes of the montage contribute to
detection on it. It is the one contrast in the data that removes channels from the complete
system rather than testing a subset in isolation.

Restricted to the same four curated anatomical regions Figure 3/Table 3 report (frontal,
central, parietal, occipital; frontopolar folded into frontal) -- the same electrode set
Figure 2/Figure 7 now use, 24 electrodes on Internal and 18 on Cao2018, matching "the
full-montage analysis" this figure is one of the companions to. Electrodes outside those four
regions (midline/edge sites, and on Cao2018 the A1/A2 mastoid references) are excluded from
the figure and from the Bonferroni family entirely, rather than kept as extra
"Midline/edge"/"Unassigned" categories -- the Bonferroni correction below is therefore over
24 (Internal) / 18 (Cao2018) electrodes, not 32, and adjusted $p$-values differ from the
former table accordingly.

The underlying per-electrode statistics (``exp1_subset_data.solo_vs_montage``/
``solo_channel_region``) are unchanged; only the electrode set entering the Bonferroni family
and the display grouping/ordering are new here.

$\\Delta F_1$ follows the sign convention used throughout this section: single minus full
montage, so a negative value means the electrode performed worse operating alone.

Writes ``writing/figures/fig_exp1_single_channel_stats.{pdf,png}``.

Data extraction (for auditing):
  Source CSV : publication_results/exp1_channel_{raja,cao2018}/exp1_channel_selection_
               {raja,cao2018}_results.csv, via ``exp1_subset_data.solo_vs_montage()``
               (internally ``load_median()`` -> ``paper_data.load("exp1", ds)``).
  Filter     : ``center_method == "median"`` only (Proposed-Med). Each electrode's own
               single-electrode ("``*_only``") run paired session-by-session against the
               same electrode's row inside the full-montage (``all_channel``) run.
  Regions    : frontal, central, parietal, occipital (``REGION_ORDER``); 24 electrodes on
               Internal, 18 on Cao2018 -- the Bonferroni family size, not 32.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402
import paper_style as S  # noqa: E402
import exp1_subset_data as SD  # noqa: E402

SCRIPT = "res_exp1_fig_single_channel_vs_montage_significance.py"

#: Display order for the region grouping -- the same four curated anatomical regions
#: Figure 3/Table 3 report (frontopolar folded into "Frontal" by ``solo_channel_region``),
#: matching Figure 2/Figure 7's own restriction to "the full-montage analysis" electrode
#: set. Electrodes outside these four regions (midline/edge sites, unassigned/mastoid
#: references) are dropped rather than shown as extra categories.
REGION_ORDER = ["frontal", "central", "parietal", "occipital"]
REGION_LABEL = {
    "frontal": "Frontal", "central": "Central", "parietal": "Parietal",
    "occipital": "Occipital",
}


def ordered(ds: str) -> tuple[pd.DataFrame, int]:
    """Electrode rows grouped by region, descending single-electrode $F_1$ within each
    region -- the same order the per-electrode prose reports them in.

    Restricted to ``REGION_ORDER``'s four curated regions before the Bonferroni
    correction is (re)computed, so the correction family is the same 24/18 electrodes
    actually shown, not the full 32-electrode montage ``solo_vs_montage`` returns.
    """
    t = SD.solo_vs_montage(ds)
    regions = SD.solo_channel_region(ds)
    t = t.copy()
    t["region"] = t["channel"].map(regions)
    t = t[t["region"].isin(REGION_ORDER)].copy()
    n_tests = int(t["p_raw"].notna().sum())
    t["p_bonf"] = (t["p_raw"] * n_tests).clip(upper=1.0)
    blocks = [t[t.region == r].sort_values("solo_f1", ascending=False) for r in REGION_ORDER]
    return pd.concat(blocks, ignore_index=True).reset_index(drop=True), n_tests


def fmt_sig(row: pd.Series) -> str:
    """"*" above an electrode with Bonferroni-adjusted $p<0.05$, else blank -- matches
    Figure 15's convention. Exact adjusted $p$-values are reported in the caption/prose
    wherever an individual electrode is discussed, not printed on the bars."""
    if row["p_bonf"] != row["p_bonf"]:
        return ""
    return "*" if row["p_bonf"] < 0.05 else ""


def build_figure(data: dict[str, tuple[pd.DataFrame, int]], n_sessions: dict[str, int]) -> None:
    NAVY = S.NAVY
    REGION_COLORS = S.REGION_COLORS
    PANEL_BLUE = S.PANEL_BLUE
    PAGE_BG = S.PAGE_BG
    COND_COLOR = S.EEG_BLUE  # neutral swatch colour for the Single/Montage legend

    # Same electrode-set size (24/18) and figsize-to-embed-width ratio as Figure 15
    # (10in figure at \includegraphics[width=\linewidth], i.e. 0.1 linewidth per inch)
    # so this figure's chrome text prints at the same size as its per-electrode sibling.
    fig, axes = plt.subplots(2, 1, figsize=(10, 9), gridspec_kw={"hspace": 0.42})
    S.style_fig(fig)

    panel_letter = {"raja": "A", "cao": "B"}
    dataset_detail = {"raja": "EGI 128", "cao": "10–20"}

    for ax, ds in zip(axes, ["raja", "cao"]):
        df, n_tests = data[ds]
        n = len(df)
        x = np.arange(n)
        colors = [REGION_COLORS[r] for r in df["region"]]
        montage = df["gated_f1"].to_numpy() * 100
        single = df["solo_f1"].to_numpy() * 100

        # region group shading + separators + header labels, alternating like Figure 15
        boundaries = []
        start = 0
        regions = df["region"].tolist()
        for i in range(1, n + 1):
            if i == n or regions[i] != regions[start]:
                boundaries.append((start, i, regions[start]))
                start = i
        for gi, (s0, e0, region) in enumerate(boundaries):
            if gi % 2 == 1:
                ax.axvspan(s0 - 0.5, e0 - 0.5, color=PAGE_BG, zorder=0)
            if s0 > 0:
                ax.axvline(s0 - 0.5, color=PANEL_BLUE, linewidth=0.9, zorder=1)
            cx = (s0 + e0 - 1) / 2
            ax.text(cx, 108, REGION_LABEL[region], ha="center", va="bottom",
                    fontsize=S.FONT_INPLOT, fontweight="bold", color=REGION_COLORS[region])

        # Montage: wider, translucent background bar. Single: narrower, opaque foreground
        # bar -- both centred on the same electrode position so nearby values stay
        # distinguishable rather than one hiding the other.
        ax.bar(x, montage, width=0.84, color=colors, alpha=0.35,
               edgecolor=NAVY, linewidth=0.5, zorder=2)
        ax.bar(x, single, width=0.46, color=colors, alpha=1.0,
               edgecolor=NAVY, linewidth=0.6, zorder=3)

        # Significance marker only (no printed p-value -- see caption): a single "*"
        # centred just above the taller of the two bars for electrodes with adjusted
        # p<0.05; nothing is drawn for a non-significant electrode.
        for i, row in df.iterrows():
            star = fmt_sig(row)
            if not star:
                continue
            top = max(montage[i], single[i])
            ax.text(i, top + 1.0, star, ha="center", va="bottom",
                    fontsize=S.FONT_INPLOT, color=NAVY, fontweight="bold")

        ax.set_xlim(-0.7, n - 0.3)
        ax.set_xticks(x)
        ax.set_xticklabels(df["channel"], rotation=90, color=NAVY)
        # Data plotted on 0-100; the axis extends a bit further so the significance
        # asterisks and region-group headers have room without truncating or rescaling
        # the 0-100 scale.
        ax.set_ylim(0, 114)
        ax.set_yticks([0, 20, 40, 60, 80, 100])
        ax.set_ylabel(r"$F_1$ (%)", color=NAVY)

        title = (f"{panel_letter[ds]}. {P.DSN[ds]} ({dataset_detail[ds]}, "
                 f"{n_sessions[ds]} sessions)")
        ax.set_title(title, fontweight="bold", color=NAVY, pad=10)

        # style_axis applies the shared chrome font size (S.FONT_CHROME) to the title,
        # axis label and tick labels set above.
        S.style_axis(ax, grid_axis="y")

    handles = [
        Patch(facecolor=COND_COLOR, alpha=1.0, edgecolor=NAVY, linewidth=0.6, label="Single"),
        Patch(facecolor=COND_COLOR, alpha=0.35, edgecolor=NAVY, linewidth=0.5, label="Montage"),
    ]
    fig.legend(handles=handles, loc="upper center", ncol=2, fontsize=S.FONT_CHROME,
               frameon=False, bbox_to_anchor=(0.5, 0.96))

    fig.suptitle(
        r"Per-electrode $F_1$: single-electrode operation vs. full montage",
        y=1.015, fontsize=S.FONT_CHROME, fontweight="bold", color=NAVY,
    )

    fig.tight_layout(rect=[0, 0, 1, 0.90])
    P.save_fig(fig, "fig_exp1_single_channel_stats")
    plt.close(fig)


def main() -> None:
    n_sessions = {ds: len(P.bps(P.load("exp1", ds))) for ds in ["raja", "cao"]}
    data = {ds: ordered(ds) for ds in ["raja", "cao"]}
    build_figure(data, n_sessions)

    for ds, title in (("raja", "Internal"), ("cao", "Cao2018")):
        df, n_tests = data[ds]
        n_sig = int((df["p_bonf"] < 0.05).sum())
        n_neg_sig = int(((df["p_bonf"] < 0.05) & (df["delta"] < 0)).sum())
        print(f"{title}: {n_tests} electrodes tested, {n_sig} significant after Bonferroni "
              f"({n_neg_sig} of those negative)")
        for _, r in df.iterrows():
            flag = "SIG" if r["p_bonf"] < 0.05 else "ns"
            print(f"  {r['channel']:6s} {REGION_LABEL[r['region']]:12s} "
                  f"single={r['solo_f1']*100:6.2f} montage={r['gated_f1']*100:6.2f} "
                  f"delta={r['delta']*100:+6.2f} p_raw={r['p_raw']:.4g} "
                  f"p_bonf={r['p_bonf']:.4g} r_rb={r['r_rb']:+.3f} n={r['n_pairs']:2d} {flag}")


if __name__ == "__main__":
    main()
