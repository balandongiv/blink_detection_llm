"""Figure 12 — detection performance against the number of electrodes in the subset.

Writes ``writing/figures/fig_exp1_coverage_curve.{pdf,png}``.

Every Experiment 1 channel subset is one point: how many electrodes the complete
pipeline was given, against the macro $F_1$ it reached. The point of the figure is that
the vertical spread at any given subset size dwarfs the effect of subset size itself —
where the electrodes sit matters, how many there are does not.

Region colours are the ones ``tab3_fig3_region_performance.py`` already uses, so a colour
means the same scalp region in both figures.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exp1_subset_data as S  # noqa: E402
import paper_data as P  # noqa: E402

SCRIPT = "fig12_exp1_coverage_curve.py"
STEM = "fig_exp1_coverage_curve"

#: Shared with tab3_fig3_region_performance.py — one colour, one scalp region.
FAMILY_COLOR = {
    "frontopolar": "#C44E52", "frontal": "#DD8452", "central": "#4C72B0",
    "parietal": "#8172B3", "occipital": "#55A868", "posterior": "#937860",
    "full montage": "#000000",
}
FAMILY_ORDER = ["frontopolar", "frontal", "central", "parietal", "occipital", "posterior"]

#: Subsets the manuscript plots: the anatomical ones plus every single-electrode probe.
EXTRA_SINGLES = ["fp1_only", "fp2_only", "af3_only", "af4_only", "f3_only", "f4_only"]


def family(selection: str) -> str:
    """Scalp family a subset belongs to, collapsing the hemisphere halves."""
    if selection == S.REFERENCE:
        return "full montage"
    if selection in ("fp1_only", "fp2_only"):
        return "frontopolar"
    base = selection.replace("_only", "").replace("_left", "").replace("_right", "")
    return {"f3": "frontal", "f4": "frontal", "af3": "frontal", "af4": "frontal"}.get(
        base, base)


def points(ds: str):
    """(n_channels, F1, family, label, is_single) for every plotted subset."""
    d = S.load_median(ds)
    wanted = [s for s in S.SUBSET_ORDER + EXTRA_SINGLES if s in set(d["selection"])]
    out = []
    for sel in wanted:
        sub = d[d["selection"] == sel]
        f1 = S.bps_series(sub)["f1"].mean()
        n_ch = int(sub["n_channels_used"].iloc[0])
        label = (S.SUBSET_LABEL.get(sel)
                 or P.spell_1020(sel.replace("_only", "")) + " only")
        out.append((n_ch, f1, family(sel), label, n_ch == 1))
    return out


def draw_panel(ax, ds: str, title: str) -> None:
    pts = points(ds)
    reference = next(f1 for n, f1, fam, _, _ in pts if fam == "full montage")
    ax.axhline(reference, ls="--", lw=1.2, color="#555555", zorder=1)

    for n_ch, f1, fam, label, is_single in pts:
        ax.scatter(n_ch, f1, s=110 if fam == "full montage" else 70,
                   marker="*" if fam == "full montage" else ("D" if is_single else "o"),
                   color=FAMILY_COLOR[fam], edgecolor="white", linewidth=1.0, zorder=3)

    # Label only the points the text argues about; labelling all of them collides.
    # Offsets are per-label because the neighbours differ: the frontopolar diamonds sit
    # under the reference line, and the full-montage star sits against the right frame.
    offsets = {"All (full montage)": ((-10, 9), "right"), "Frontal": ((0, 10), "center"),
               "Fp1 only": ((12, -13), "left"), "Posterior": ((10, 4), "left")}
    for n_ch, f1, fam, label, _ in pts:
        if label in offsets:
            xytext, ha = offsets[label]
            ax.annotate(label, (n_ch, f1), textcoords="offset points", xytext=xytext,
                        ha=ha, fontsize=8.5, color="#222222")

    ax.set_xscale("log", base=2)
    ax.set_xticks([1, 2, 3, 4, 6, 8, 12, 32])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_xlim(0.8, 48)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("Electrodes given to the pipeline")
    ax.set_title(f"{title}  (reference $F_1$ = {reference:.4f})", fontsize=10.5)


def main() -> None:
    sns.set_style("whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
    draw_panel(axes[0], "raja", "Internal")
    draw_panel(axes[1], "cao", "Cao2018")
    axes[0].set_ylabel("Session-level macro $F_1$")

    # One legend below both panels: in-axes legends collided with the posterior points,
    # which sit in the only corner an in-axes legend can occupy.
    handles = [
        Line2D([], [], marker="o", ls="", color=FAMILY_COLOR[f], label=f.capitalize(),
               markersize=7, markeredgecolor="white")
        for f in FAMILY_ORDER
    ] + [
        Line2D([], [], marker="*", ls="", color="k", label="Full montage", markersize=11),
        Line2D([], [], marker="o", ls="", color="#777777", label="Anatomical subset",
               markersize=7),
        Line2D([], [], marker="D", ls="", color="#777777", label="Single electrode",
               markersize=6),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=5, fontsize=8.5,
               frameon=False, bbox_to_anchor=(0.5, -0.02))

    fig.suptitle("Detection $F_1$ against the number of electrodes available to the "
                 "pipeline (Proposed-Med, median centre)", fontsize=11.5)
    fig.tight_layout(rect=(0, 0.09, 1, 0.95))
    P.save_fig(fig, STEM)
    plt.close(fig)


if __name__ == "__main__":
    main()
