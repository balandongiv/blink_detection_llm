"""Table 3 and Figure 3 — region-level performance and the whole-scalp single-channel map.

Writes:
  ``writing/e_result/tab_region_performance.tex``
  ``writing/figures/fig_region_performance.{pdf,png}``

Both are built from the per-channel Experiment 1 rows (``selection == "all_channel"``,
median centre). The table collapses electrodes to coarse scalp regions with the
frontopolar pair (Raja E22/E9, Cao2018 FP1/FP2) broken out separately, because that pair
is the whole story of the ablation. The figure keeps every electrode visible.

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

SCRIPT = "tab3_fig3_region_performance.py"

FRONTOPOLAR = {"raja": {"E22", "E9"}, "cao": {"FP1", "FP2"}}
REGION_COLORS = {
    "frontopolar": "#C44E52", "frontal": "#DD8452", "central": "#4C72B0",
    "parietal": "#8172B3", "occipital": "#55A868",
    "midline_or_outside": "#937860", "unassigned": "#BBBBBB",
}
REGION_ORDER = ["frontopolar", "frontal", "central", "parietal", "occipital",
                "midline_or_outside", "unassigned"]


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
        r"  \caption{Experiment~1 single-channel detection performance collapsed to coarse "
        r"scalp regions (Proposed-Med, median centre). Each region row averages the "
        r"per-channel macro precision, recall and $F_1$ over the electrodes it contains; "
        r"the frontopolar pair (Raja E22/E9, Cao2018 FP1/FP2) is reported separately from "
        r"the remaining frontal sites. $n$ is the number of electrodes in the region.}",
        r"  \label{tab:region_performance}",
        r"  \begin{tabular}{llcccc}", r"    \toprule",
        r"    Dataset & Region & $n$ & Precision & Recall & $F_1$ \\", r"    \midrule",
    ]

    for ds in ["raja", "cao"]:
        g = frames[ds]
        first = True
        for region in REGION_ORDER:
            sub = g[g.coarse == region]
            if sub.empty:
                continue
            ds_cell = P.DSN[ds] if first else ""
            lines.append(
                f"    {ds_cell} & {P.tex_escape(region)} & {len(sub)} & "
                f"{sub.p.mean():.4f} & {sub.r.mean():.4f} & {sub.f1.mean():.4f} \\\\"
            )
            first = False
        lines.append(r"    \midrule")
    lines[-1] = r"    \bottomrule"
    lines += [r"  \end{tabular}", r"\end{table}"]
    return lines


def build_figure(frames: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for ax, ds in zip(axes, ["raja", "cao"]):
        g = frames[ds]
        colors = [REGION_COLORS.get(r, "#cccccc") for r in g["coarse"]]
        ax.bar(range(len(g)), g["f1"].to_numpy(), color=colors)
        ax.set_xticks(range(len(g)))
        ax.set_xticklabels(g["display"], rotation=90, fontsize=7)
        ax.set_title(P.DSN[ds])
        ax.set_ylim(0, 1.0)
        ax.set_ylabel("macro-$F_1$ (single channel)" if ds == "raja" else "")

    handles = [Patch(color=REGION_COLORS[r], label=r.replace("_", " "))
               for r in REGION_ORDER if r in REGION_COLORS]
    fig.legend(handles=handles, loc="upper center", ncol=len(handles), fontsize=8,
               frameon=False, bbox_to_anchor=(0.5, 1.04))
    fig.suptitle("Single-channel detection $F_1$ by electrode and scalp region",
                 y=1.10, fontsize=12)
    fig.tight_layout()
    P.save_fig(fig, "fig_region_performance")
    plt.close(fig)


def main() -> None:
    frames = {ds: coarse_regions(ds) for ds in ["raja", "cao"]}
    P.write_tex(P.ER / "tab_region_performance.tex", build_table(frames), SCRIPT)
    build_figure(frames)

    for ds in ["raja", "cao"]:
        g = frames[ds]
        front = g[g.coarse.isin(["frontal", "frontopolar"])]["f1"].mean()
        non_front = g[~g.coarse.isin(["frontal", "frontopolar"])]
        print(f"{P.DSN[ds]}: frontal+frontopolar mean F1 = {front:.3f}; "
              f"non-frontal mean F1 = {non_front['f1'].mean():.3f} "
              f"(n={len(non_front)} channels)")


if __name__ == "__main__":
    main()
