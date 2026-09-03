"""Table 3 and Figure 3 — region-level performance and the whole-scalp single-channel map.

Writes:
  ``writing/e_result/exp1/tab_region_performance.tex``
  ``writing/figures/fig_region_performance.{pdf,png}``

Both are built from the per-channel Experiment 1 rows (``selection == "all_channel"``,
median centre). The table collapses electrodes to coarse scalp regions and drops the
frontopolar, midline/outside, and unassigned groups, showing only frontal, central,
parietal and occipital.

The figure is stacked as two rows (Internal on top, Cao2018 on bottom). Only electrodes
assigned to frontal, central, parietal or occipital are plotted: frontopolar electrodes
are folded into frontal for colour/legend purposes, and midline/outside and unassigned
electrodes are dropped, so the figure surfaces the same four region terms as the table.
Bars are percentages (0-100) with the value labelled above each bar.

Run inside conda env ``double_threshold_algo``.
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

SCRIPT = "tab3_fig3_region_performance.py"

FRONTOPOLAR = {"raja": {"E22", "E9"}, "cao": {"FP1", "FP2"}}
REGION_COLORS = {
    "frontopolar": "#C44E52", "frontal": "#DD8452", "central": "#4C72B0",
    "parietal": "#8172B3", "occipital": "#55A868",
    "midline_or_outside": "#937860", "unassigned": "#BBBBBB",
}
#: The only four terms shown in the figure and the console summary. Frontopolar
#: electrodes are folded into "frontal" and midline/outside and unassigned electrodes
#: are dropped (same as the retired collapsed table).
SUMMARY_REGION_ORDER = ["frontal", "central", "parietal", "occipital"]


def coarse_regions(ds: str):
    """Per-channel frame with a coarse region label and frontopolar broken out."""
    g = P.per_channel(ds).copy()
    g["coarse"] = g.region.apply(
        lambda r: r.rsplit("_", 1)[0] if r.endswith(("_left", "_right")) else r
    )
    g.loc[g.ch.str.upper().isin(FRONTOPOLAR[ds]), "coarse"] = "frontopolar"
    return g.sort_values("f1", ascending=False)


def build_table(frames: dict) -> list[str]:
    lines = [
        r"\begin{table}[ht]", r"  \centering",
        r"  \caption{Experiment~1 per-electrode detection performance collapsed to coarse "
        r"scalp regions (Proposed-Med, median centre), each electrode scored inside the "
        r"full-montage run rather than as a standalone single-electrode pipeline. Each "
        r"region row averages the per-channel macro $F_1$ over the electrodes it contains; "
        r"regions follow the \texttt{brain\_region\_raja.yaml}/\texttt{brain\_region\_cao2018.yaml} "
        r"assignment, so the frontopolar pair is included within frontal. The midline/outside "
        r"and unassigned groups are omitted; only the frontal, central, parietal, and "
        r"occipital regions are shown. $n$ is the number of electrodes in the region. "
        r"$F_1$ is reported as a percentage.}",
        r"  \label{tab:region_performance}",
        r"  \begin{tabular}{llcc}", r"    \toprule",
        r"    Dataset & Region & $n$ & $F_1$ (\%) \\", r"    \midrule",
    ]

    for ds in ["raja", "cao"]:
        g = _figure_frame(frames[ds])
        first = True
        for region in SUMMARY_REGION_ORDER:
            sub = g[g.coarse == region]
            if sub.empty:
                continue
            ds_cell = P.DSN[ds] if first else ""
            lines.append(
                f"    {ds_cell} & {P.tex_escape(region)} & {len(sub)} & "
                f"{sub.f1.mean() * 100:.2f} \\\\"
            )
            first = False
        lines.append(r"    \midrule")
    lines[-1] = r"    \bottomrule"
    lines += [r"  \end{tabular}", r"\end{table}"]
    return lines


def _figure_frame(g):
    """Electrodes shown in the figure: frontopolar folded into frontal, midline/outside
    and unassigned electrodes dropped, so only frontal/central/parietal/occipital appear
    (same four terms as the region-collapsed prose)."""
    d = g.copy()
    d["coarse"] = d["coarse"].replace({"frontopolar": "frontal"})
    d = d[d["coarse"].isin(SUMMARY_REGION_ORDER)]
    return d.sort_values("f1", ascending=False)


def build_figure(frames: dict) -> None:
    # Colour scheme matched to the processing-pipeline flowchart (see paper_style.py)
    NAVY = S.NAVY
    REGION_COLORS = S.REGION_COLORS

    fig, axes = plt.subplots(
        2, 1,
        figsize=(9, 8),
        sharex=False,
    )
    S.style_fig(fig)

    for ax, ds in zip(axes, ["raja", "cao"]):
        g = _figure_frame(frames[ds])

        colors = [REGION_COLORS[r] for r in g["coarse"]]
        pct = g["f1"].to_numpy() * 100

        bars = ax.bar(
            range(len(g)),
            pct,
            color=colors,
            edgecolor=NAVY,
            linewidth=0.45,
            width=0.78,
        )

        ax.bar_label(
            bars,
            fmt="%.2f",
            rotation=45,
            padding=2,
            fontsize=7.5,
            color=NAVY,
        )

        ax.set_xticks(range(len(g)))
        ax.set_xticklabels(
            g["display"],
            rotation=90,
            fontsize=8,
            color=NAVY,
        )

        ax.set_title(
            P.DSN[ds],
            fontsize=11,
            fontweight="bold",
            color=NAVY,
            pad=8,
        )

        ax.set_ylim(0, 100)
        ax.margins(y=0.12)

        ax.set_ylabel(
            r"Macro-$F_1$ (%)",
            fontsize=10,
            color=NAVY,
        )

        S.style_axis(ax)
        ax.tick_params(axis="y", labelsize=8)

    # Legend
    handles = [
        Patch(
            facecolor=REGION_COLORS[r],
            edgecolor=NAVY,
            linewidth=0.4,
            label=r.capitalize(),
        )
        for r in SUMMARY_REGION_ORDER
    ]

    fig.legend(
        handles=handles,
        loc="upper center",
        ncol=len(handles),
        fontsize=8.5,
        frameon=False,
        bbox_to_anchor=(0.5, 1.015),
    )

    fig.suptitle(
        r"Single-channel detection $F_1$ by electrode and scalp region",
        y=1.055,
        fontsize=12,
        fontweight="bold",
        color=NAVY,
    )

    fig.tight_layout(rect=[0, 0, 1, 0.97])

    P.save_fig(fig, "fig_region_performance")
    plt.close(fig)


def main() -> None:
    frames = {ds: coarse_regions(ds) for ds in ["raja", "cao"]}
    P.write_tex(P.ER / "exp1" / "tab_region_performance.tex", build_table(frames), SCRIPT)
    build_figure(frames)

    for ds in ["raja", "cao"]:
        g = frames[ds]
        front = g[g.coarse.isin(["frontal", "frontopolar"])]["f1"].mean()
        non_front = g[~g.coarse.isin(["frontal", "frontopolar"])]
        print(f"{P.DSN[ds]}: frontal+frontopolar mean F1 = {front:.3f}; "
              f"non-frontal mean F1 = {non_front['f1'].mean():.3f} "
              f"(n={len(non_front)} channels)")
        print(f"{P.DSN[ds]} region-collapsed macro P/R/F1 (%), frontopolar folded into frontal:")
        folded = _figure_frame(g)
        for region in SUMMARY_REGION_ORDER:
            sub = folded[folded.coarse == region]
            if sub.empty:
                continue
            print(f"  {region} (n={len(sub)}): "
                  f"P={sub.p.mean() * 100:.2f} R={sub.r.mean() * 100:.2f} "
                  f"F1={sub.f1.mean() * 100:.2f}")


if __name__ == "__main__":
    main()
