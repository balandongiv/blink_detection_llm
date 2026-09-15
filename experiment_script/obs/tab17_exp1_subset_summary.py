"""Table 17 — Experiment 1 channel-subset summary against the full-montage reference.

Writes ``writing/e_result/exp1/tab_exp1_subset_summary.tex``.

One row per anatomical subset, per dataset: the subset size, its region-mean $F_1$
(each electrode's own macro $F_1$ averaged over sessions, then averaged across the
electrodes the subset contains — the same aggregation Table 3/Figure 3 use for the
full montage, ``tab3_fig3_region_performance.py``), and the paired test against the
same region's electrodes scored inside the full-montage run. This is the spine of the
channel-subset section — it is what shows how much restricting Stage A/B screening to
a single region changes that region's own detection performance.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import exp1_subset_data as S  # noqa: E402
import paper_data as P  # noqa: E402

SCRIPT = "tab17_exp1_subset_summary.py"
OUT = P.ER / "exp1" / "tab_exp1_subset_summary.tex"


def fmt_p(p: float) -> str:
    """Bonferroni-corrected p-value. ``0.000`` reads as exactly zero, so never print it."""
    if p != p:  # NaN — the reference row has no comparison against itself
        return "--"
    return r"$<0.001$" if p < 0.001 else f"${p:.3f}$"


def fmt_signed(x: float) -> str:
    return "--" if x != x else f"${P.fmt_pp(x)}$"


def fmt_f1_montage(x: float) -> str:
    return "--" if x != x else P.fmt(x)


def dataset_block(ds: str, title: str) -> list[str]:
    t = S.subset_stats_region_mean(ds)
    lines = [rf"\multicolumn{{7}}{{l}}{{\textit{{{title}}}}} \\[2pt]"]
    for _, r in t.iterrows():
        label = r["label"]
        if r["selection"] == S.REFERENCE:
            label = rf"\textbf{{{label}}}"
        lines.append(
            f"{label} & {r['n_ch']} & "
            f"{P.fmt(r['f1'])} & {fmt_f1_montage(r['f1_montage'])} & "
            f"{fmt_signed(r['delta'])} & {fmt_p(r['p_bonf'])} & "
            + ("--" if r["r_rb"] != r["r_rb"] else f"${r['r_rb']:+.2f}$") + r" \\"
        )
    return lines


def main() -> None:
    raja, cao = S.subset_stats_region_mean("raja"), S.subset_stats_region_mean("cao")
    lines = [
        r"\begin{table}[htbp]", r"\centering", r"\footnotesize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\caption{Experiment~1 channel-subset performance of Proposed-approach (median centre). "
        r"Each subset is a self-contained detector: Stage~A, Stage~B and Stage~C were all "
        r"re-run on that channel subset alone. $F_1$ (Subset) is the region-mean $F_1$: each "
        r"electrode's own macro $F_1$ is averaged over sessions and those per-electrode means "
        r"are then averaged across the electrodes the subset contains, the same aggregation "
        r"Table~\ref{tab:region_performance}/Figure~\ref{fig:region_performance} use for the "
        r"full montage, applied here to the subset's own rerun. $F_1$ (Montage) reports the "
        r"same region's electrodes scored inside the full-montage run instead, on the same "
        r"sessions. $\Delta F_1$ is the paired difference, Subset minus Montage, in percentage "
        r"points, tested with a two-tailed Wilcoxon signed-rank test and Bonferroni-corrected "
        rf"over the {raja.attrs['n_comparisons']} subsets compared within each dataset, with "
        r"the matched-pairs rank-biserial correlation $r$ as effect size. The "
        r"\textbf{All (full montage)} row instead reports the best-channel-per-session oracle "
        r"$F_1$ used as the headline full-montage figure throughout the manuscript, shown for "
        r"reference only; it is not the $\Delta F_1$ baseline for the rows below it. $n$ is the "
        r"number of electrodes in the subset; the frontal subset contains AF3 and AF4 on "
        r"Internal but not on Cao2018, whose montage lacks them.}",
        r"\label{tab:exp1_subset_summary}",
        r"\begin{tabular}{lrrrrrr}", r"\toprule",
        r"Subset & $n$ & $F_1$ Subset (\%) & $F_1$ Montage (\%) & $\Delta F_1$ (pp) & $p$ & $r$ \\",
        r"\midrule",
        *dataset_block("raja", f"{P.DSN['raja']} (EGI 128, {len(P.bps(P.load('exp1', 'raja')))} sessions)"),
        r"\midrule",
        *dataset_block("cao", f"Cao2018 (10--20, {len(P.bps(P.load('exp1', 'cao')))} sessions)"),
        r"\bottomrule", r"\end{tabular}", r"\end{table}",
    ]
    P.write_tex(OUT, lines, SCRIPT)
    for ds, t in (("raja", raja), ("cao", cao)):
        ref = t[t.selection == S.REFERENCE].iloc[0]
        print(f"  {ds}: reference F1={ref.f1:.4f}  n_comparisons={t.attrs['n_comparisons']}")


if __name__ == "__main__":
    main()
