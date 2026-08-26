"""Table 17 — Experiment 1 channel-subset summary against the full-montage reference.

Writes ``writing/e_result/exp1/tab_exp1_subset_summary.tex``.

One row per anatomical subset, per dataset: the subset size, its best-channel-per-session
operating point, and the paired test against the full montage. This is the spine of the
channel-subset section — it is what shows that the frontal subset is statistically
indistinguishable from the whole cap while every posterior subset is not.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
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


def dataset_block(ds: str, title: str) -> list[str]:
    t = S.subset_stats(ds)
    lines = [rf"\multicolumn{{6}}{{l}}{{\textit{{{title}}}}} \\[2pt]"]
    for _, r in t.iterrows():
        label = r["label"]
        if r["selection"] == S.REFERENCE:
            label = rf"\textbf{{{label}}}"
        lines.append(
            f"{label} & {r['n_ch']} & "
            f"{P.fmt(r['f1'])} & {fmt_signed(r['delta'])} & {fmt_p(r['p_bonf'])} & "
            + ("--" if r["r_rb"] != r["r_rb"] else f"${r['r_rb']:+.2f}$") + r" \\"
        )
    return lines


def main() -> None:
    raja, cao = S.subset_stats("raja"), S.subset_stats("cao")
    lines = [
        r"\begin{table}[htbp]", r"\centering", r"\footnotesize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\caption{Experiment~1 channel-subset performance of Proposed-Med (median centre) "
        r"against the full-montage reference. Each subset is a self-contained detector: "
        r"Stage~A, Stage~B and Stage~C were all re-run on that channel subset alone. "
        r"$F_1$ is macro-averaged over sessions at the "
        r"best-channel-per-session operating point and reported as a percentage; "
        r"$\Delta F_1$ is the paired difference "
        r"from the full montage in percentage points, tested with a two-tailed Wilcoxon signed-rank test and "
        r"Bonferroni-corrected over the "
        rf"{raja.attrs['n_comparisons']} subsets compared within each dataset, with the "
        r"matched-pairs rank-biserial correlation $r$ as effect size. $n$ is the number of "
        r"electrodes in the subset; the frontal subset contains AF3 and AF4 on Internal but not "
        r"on Cao2018, whose montage lacks them.}",
        r"\label{tab:exp1_subset_summary}",
        r"\begin{tabular}{lrrrrr}", r"\toprule",
        r"Subset & $n$ & $F_1$ (\%) & $\Delta F_1$ (pp) & $p$ & $r$ \\",
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
