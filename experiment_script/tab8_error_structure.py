"""Table 8 — error-structure decomposition by condition.

Writes ``writing/e_result/exp4/tab_error_structure.tex``.

Two detectors can reach the same F1 by opposite routes: one floods the session with false
positives, the other misses blinks. The FP:FN ratio separates those regimes, which matters
because a downstream blink-rate estimate degrades very differently under each.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402

SCRIPT = "tab8_error_structure.py"


def main() -> None:
    best = P.load_exp2_best()
    n_sessions = sum(len(best[(ds, "Proposed-Med")]) for ds in ["raja", "cao"])

    lines = [
        r"\begin{table}[ht]", r"  \centering",
        r"  \caption{Error-structure decomposition by condition "
        r"(best-channel-per-session). Mean false positives (FP) and false negatives (FN) "
        r"per session, pooled over " + str(n_sessions) + r" sessions. The regime column "
        r"records which error type dominates.}",
        r"  \label{tab:error-structure}",
        r"  \begin{tabular}{lcccl}", r"    \toprule",
        r"    Condition & Mean FP/session & Mean FN/session & FP:FN & Regime \\",
        r"    \midrule",
    ]
    for cond in P.CONDS:
        frame = pd.concat([best[("raja", cond)], best[("cao", cond)]])
        mean_fp, mean_fn = frame["fp"].mean(), frame["fn"].mean()
        ratio = mean_fp / mean_fn if mean_fn else float("inf")
        regime = "FP-heavy" if mean_fp > mean_fn else "FN-heavy"
        lines.append(
            f"    {cond} & {mean_fp:.2f} & {mean_fn:.2f} & {ratio:.2f} & {regime} \\\\"
        )
    lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]

    P.write_tex(P.ER / "exp4" / "tab_error_structure.tex", lines, SCRIPT)


if __name__ == "__main__":
    main()
