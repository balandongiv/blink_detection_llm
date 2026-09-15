"""Figure 15 -- Experiment 1 per-electrode paired comparison: subset rerun vs full montage.

Replaces the former Table 20 (``tab20_exp1_subset_per_electrode_stats.py``, now removed)
with an overlaid bar-chart figure showing the same per-electrode comparison instead of a
42-row longtable. Companion to Table 17 (``tab17_exp1_subset_summary.py``): Table 17 tests
each anatomical subset's REGION MEAN against the same region's electrodes scored inside the
full-montage run. This figure tests each INDIVIDUAL ELECTRODE the same way: for every
electrode that appears in one of the four anatomical subsets shown in Figure 13
(``res_exp1_fig_regional_subset_per_electrode_f1.py``), the session-level $F_1$ of that electrode inside
its own subset rerun is paired, session by session, against the session-level $F_1$ of the
SAME electrode inside the full-montage run (``selection == "all_channel"``). This is the
electrode-level analogue of Table 17's region-level test, and answers a different question:
which individual electrodes, not which regions, changed when their region operated as an
independent detector.

Test: two-tailed Wilcoxon signed-rank, paired by session, matching ``exp1_subset_data``'s
``rank_biserial`` sign convention (subset minus montage). Bonferroni correction is applied
separately within each dataset, over every electrode tested in that dataset (24 for
Internal, 18 for Cao2018) -- a separate family from Table 17's 13 region-level tests. The
underlying statistical logic (``electrode_pairs``/``ordered`` below) is unchanged from the
former table script.

If every matched session has an (near-)identical subset and montage $F_1$ for an electrode,
no Wilcoxon statistic exists (there is nothing to rank); this is flagged in the console
summary rather than reporting an invented $p$-value.

Writes ``writing/figures/fig_exp1_subset_per_electrode_stats.{pdf,png}``.

Data extraction (for auditing):
  Source CSV : publication_results/exp1_channel_{raja,cao2018}/exp1_channel_selection_
               {raja,cao2018}_results.csv, via ``exp1_subset_data.load_median()`` ->
               ``paper_data.load("exp1", ds)``.
  Filter     : ``center_method == "median"`` only (Proposed-Med). Each electrode's own
               region-subset rows (``selection`` in {frontal, central, parietal,
               occipital}) paired session-by-session against the same electrode's row at
               ``selection == "all_channel"`` (full 32-channel montage).
  Regions    : frontal, central, parietal, occipital (``REGION_ORDER``); 24 electrodes on
               Internal, 18 on Cao2018.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402
import paper_style as S  # noqa: E402
import exp1_subset_data as SD  # noqa: E402

SCRIPT = "res_exp1_fig_regional_subset_vs_montage_significance.py"

#: Matches Figure 13's SUMMARY_REGION_ORDER exactly -- the four self-contained anatomical
#: subsets that retain more than one electrode. ``posterior`` is a union of parietal and
#: occipital and would duplicate electrodes already tested there, so it is not repeated.
REGION_ORDER = ["frontal", "central", "parietal", "occipital"]
REGION_LABEL = {"frontal": "Frontal", "central": "Central", "parietal": "Parietal",
                "occipital": "Occipital"}


def electrode_pairs(ds: str) -> pd.DataFrame:
    """One row per electrode: subset vs full-montage session-level $F_1$, paired by session."""
    d = SD.load_median(ds)
    montage = d[d["selection"] == SD.REFERENCE]
    rows = []
    for region in REGION_ORDER:
        sub = d[d["selection"] == region]
        for ch, grp in sub.groupby("channel"):
            subset_series = grp.groupby("session")["f1"].mean().sort_index()
            montage_series = (montage[montage["channel"] == ch]
                               .groupby("session")["f1"].mean().sort_index())
            common = subset_series.index.intersection(montage_series.index)
            a = montage_series.loc[common].to_numpy()  # full montage
            b = subset_series.loc[common].to_numpy()   # subset
            diffs = b - a
            identical = bool(len(diffs)) and bool(np.allclose(diffs, 0))
            if len(common) == 0:
                p_raw, r_rb = np.nan, np.nan
            elif identical:
                p_raw, r_rb = 1.0, 0.0
            else:
                p_raw = float(stats.wilcoxon(a, b, alternative="two-sided").pvalue)
                r_rb = SD.rank_biserial(a, b)
            rows.append({
                "dataset": ds, "region": region, "channel": ch,
                "display": grp["display"].iloc[0],
                "n_pairs": int(len(common)),
                "f1_subset": float(b.mean()) if len(common) else np.nan,
                "f1_montage": float(a.mean()) if len(common) else np.nan,
                "delta_mean": float(b.mean() - a.mean()) if len(common) else np.nan,
                "delta_median": float(np.median(diffs)) if len(common) else np.nan,
                "p_raw": p_raw, "r_rb": r_rb, "identical": identical,
            })
    out = pd.DataFrame(rows)
    n_tests = int(out["p_raw"].notna().sum())
    out["p_bonf"] = (out["p_raw"] * n_tests).clip(upper=1.0)
    out.attrs["n_tests"] = n_tests
    return out


def ordered(ds: str) -> tuple[pd.DataFrame, int]:
    """Electrode rows grouped by region (Figure 13's order), descending subset $F_1$ within
    each region -- the same order the per-electrode prose reports them in."""
    df = electrode_pairs(ds)
    blocks = [df[df.region == r].sort_values("f1_subset", ascending=False) for r in REGION_ORDER]
    return pd.concat(blocks, ignore_index=True).reset_index(drop=True), df.attrs["n_tests"]


def fmt_sig(row: pd.Series) -> str:
    """"*" above an electrode with Bonferroni-adjusted $p<0.05$, else blank.

    Exact adjusted $p$-values are not printed on the bars (font-size budget); they are
    reported in the caption/prose wherever an individual electrode is discussed.
    """
    if row["identical"] or row["p_bonf"] != row["p_bonf"]:
        return ""
    return "*" if row["p_bonf"] < 0.05 else ""


def build_figure(data: dict[str, tuple[pd.DataFrame, int]], n_sessions: dict[str, int]) -> None:
    NAVY = S.NAVY
    REGION_COLORS = S.REGION_COLORS
    PANEL_BLUE = S.PANEL_BLUE
    PAGE_BG = S.PAGE_BG
    COND_COLOR = S.EEG_BLUE  # neutral swatch colour for the Subset/Montage legend

    # Matched to Figure 13/tab3_fig3_region_performance's own figsize-to-embed-width
    # ratio (9in figure at \includegraphics[width=0.9\linewidth], i.e. 0.1 linewidth per
    # inch) so this figure's chrome text prints at the same size as its sibling
    # per-electrode bar charts once placed in the manuscript at width=\linewidth --
    # matplotlib's `fontsize=` is only a fraction of the SAVED figure's width, so a much
    # wider native figure (this one used to be 15in) renders its text visibly smaller on
    # the page even at the same nominal font size.
    fig, axes = plt.subplots(2, 1, figsize=(10, 9), gridspec_kw={"hspace": 0.42})
    S.style_fig(fig)

    panel_letter = {"raja": "A", "cao": "B"}
    dataset_detail = {"raja": "EGI 128", "cao": "10–20"}

    for ax, ds in zip(axes, ["raja", "cao"]):
        df, n_tests = data[ds]
        n = len(df)
        x = np.arange(n)
        colors = [REGION_COLORS[r] for r in df["region"]]
        montage = df["f1_montage"].to_numpy() * 100
        subset = df["f1_subset"].to_numpy() * 100

        # region group shading + separators + header labels, alternating like fig1's
        # region-family bands
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

        # Montage: wider, translucent background bar. Subset: narrower, opaque foreground
        # bar -- both centred on the same electrode position so nearby values stay
        # distinguishable rather than one hiding the other. Widths match Figure 13's
        # single-bar column fill (0.78) as closely as the two overlaid bars allow, so
        # adjacent electrodes sit close together instead of leaving a wide gap.
        ax.bar(x, montage, width=0.84, color=colors, alpha=0.35,
               edgecolor=NAVY, linewidth=0.5, zorder=2)
        ax.bar(x, subset, width=0.46, color=colors, alpha=1.0,
               edgecolor=NAVY, linewidth=0.6, zorder=3)

        # Significance marker only (no printed p-value -- see caption): a single "*"
        # centred just above the taller of the two bars for electrodes with adjusted
        # p<0.05; nothing is drawn for a non-significant electrode.
        for i, row in df.iterrows():
            star = fmt_sig(row)
            if not star:
                continue
            top = max(montage[i], subset[i])
            ax.text(i, top + 1.0, star, ha="center", va="bottom",
                    fontsize=S.FONT_INPLOT, color=NAVY, fontweight="bold")

        ax.set_xlim(-0.7, n - 0.3)
        ax.set_xticks(x)
        ax.set_xticklabels(df["display"], rotation=90, color=NAVY)
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
        Patch(facecolor=COND_COLOR, alpha=1.0, edgecolor=NAVY, linewidth=0.6, label="Subset"),
        Patch(facecolor=COND_COLOR, alpha=0.35, edgecolor=NAVY, linewidth=0.5, label="Montage"),
    ]
    fig.legend(handles=handles, loc="upper center", ncol=2, fontsize=S.FONT_CHROME,
               frameon=False, bbox_to_anchor=(0.5, 0.96))

    fig.suptitle(
        r"Per-electrode $F_1$: self-contained anatomical subset vs. "
        r"full montage",
        y=1.015, fontsize=S.FONT_CHROME, fontweight="bold", color=NAVY,
    )

    fig.tight_layout(rect=[0, 0, 1, 0.90])
    P.save_fig(fig, "fig_exp1_subset_per_electrode_stats")
    plt.close(fig)


def main() -> None:
    n_sessions = {ds: len(P.bps(P.load("exp1", ds))) for ds in ["raja", "cao"]}
    data = {ds: ordered(ds) for ds in ["raja", "cao"]}
    build_figure(data, n_sessions)

    for ds, title in (("raja", "Internal"), ("cao", "Cao2018")):
        df, n_tests = data[ds]
        n_sig = int((df["p_bonf"] < 0.05).sum())
        print(f"{title}: {n_tests} electrodes tested, {n_sig} significant after Bonferroni correction")
        for _, r in df.iterrows():
            flag = "IDENTICAL" if r["identical"] else ("SIG" if r["p_bonf"] < 0.05 else "ns")
            print(f"  {r['display']:6s} {REGION_LABEL[r['region']]:9s} n={r['n_pairs']:2d} "
                  f"subset={r['f1_subset']*100:6.2f} montage={r['f1_montage']*100:6.2f} "
                  f"delta={r['delta_mean']*100:+6.2f} median_delta={r['delta_median']*100:+6.2f} "
                  f"p_raw={r['p_raw']:.4g} p_bonf={r['p_bonf']:.4g} r_rb={r['r_rb']:+.3f} {flag}")


if __name__ == "__main__":
    main()
