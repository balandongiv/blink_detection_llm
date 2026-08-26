"""Table 6 — cross-dataset generalisation gap.

Writes ``writing/e_result/exp4/tab_cross_dataset_gap.tex``.

The gap is Raja minus Cao2018 in best-channel-per-session macro-F1 at 30 s epochs. A
condition that generalises well has a gap near zero; a large positive gap means the
condition is carried by the closed corpus.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402

SCRIPT = "tab6_cross_dataset_gap.py"


def main() -> None:
    best = P.load_exp2_best()
    lines = [
        r"\begin{table}[ht]", r"  \centering",
        r"  \caption{Cross-dataset generalisation gap (best-channel-per-session "
        r"macro-$F_1$, 30\,s epochs), reported as percentages. Gap $=$ Internal $-$ Cao2018, "
        r"in percentage points.}",
        r"  \label{tab:cross_dataset_gap}",
        r"  \begin{tabular}{lccc}", r"    \toprule",
        r"    Condition & Internal (\%) & Cao2018 (\%) & Gap (pp) \\", r"    \midrule",
    ]
    for cond in P.CONDS:
        raja = P.macro(best, "raja", cond)[2]
        cao = P.macro(best, "cao", cond)[2]
        lines.append(f"    {cond} & {P.fmt(raja)} & {P.fmt(cao)} & {(raja - cao) * 100:+.2f} \\\\")
    lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]

    P.write_tex(P.ER / "exp4" / "tab_cross_dataset_gap.tex", lines, SCRIPT)


if __name__ == "__main__":
    main()
