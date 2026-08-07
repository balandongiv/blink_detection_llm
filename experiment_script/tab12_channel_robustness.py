"""Table 12 — do the four conditions agree on which channel is best?

Writes ``writing/e_result/tab_channel_robustness.tex``.

If the best channel were an artefact of one detector's quirks, the four conditions would
disagree session by session. Full agreement is the fraction of sessions where all four
pick the same electrode; per-condition agreement is how often the other three follow a
given condition's choice.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402

SCRIPT = "tab12_channel_robustness.py"


def choice_matrix(best: dict, ds_list) -> pd.DataFrame:
    """Rows = ``dataset/session``, columns = condition, values = chosen best channel."""
    frames = []
    for ds in ds_list:
        cols = {cond: best[(ds, cond)].set_index("session")["best_channel"]
                for cond in P.CONDS}
        frames.append(pd.DataFrame(cols).rename(index=lambda s, d=ds: f"{d}/{s}"))
    return pd.concat(frames)


def main() -> None:
    best = P.load_exp2_best()
    rows = []
    for label, ds_list in [("Raja", ["raja"]), ("Cao2018", ["cao"]),
                           ("Pooled", ["raja", "cao"])]:
        mat = choice_matrix(best, ds_list)
        n_total = len(mat)
        n_full = int((mat.nunique(axis=1) == 1).sum())
        pairwise = np.mean([(mat[a] == mat[b]).mean() for a, b in combinations(P.CONDS, 2)])
        per_cond = {
            cond: np.mean([(mat[cond] == mat[other]).mean()
                           for other in P.CONDS if other != cond])
            for cond in P.CONDS
        }
        rows.append((label, n_total, n_full, pairwise, per_cond))

    lines = [
        r"\begin{table}[ht]", r"  \centering", r"  \scriptsize",
        r"  \setlength{\tabcolsep}{3pt}",
        r"  \caption{Stability of the best-channel choice across the four conditions. "
        r"Full agreement is the fraction of sessions where all four conditions select the "
        r"same best channel; per-condition agreement is the mean fraction of the other "
        r"three conditions selecting the same best channel.}",
        r"  \label{tab:channel-robustness}",
        r"  \begin{tabular}{lccccccc}", r"    \toprule",
        r"    Dataset & Sessions & Full agreement & Mean pairwise & BLINKER-concat & "
        r"MNE-annot & Proposed-Mean & Proposed-Med \\",
        r"    \midrule",
    ]
    for label, n_total, n_full, pairwise, per_cond in rows:
        lines.append(
            f"    {label} & {n_total} & {n_full}/{n_total} ({n_full / n_total:.3f}) & "
            f"{pairwise:.3f} & {per_cond['BLINKER-concat']:.3f} & "
            f"{per_cond['MNE-annot']:.3f} & {per_cond['Proposed-Mean']:.3f} & "
            f"{per_cond['Proposed-Med']:.3f} \\\\"
        )
    lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]

    P.write_tex(P.ER / "tab_channel_robustness.tex", lines, SCRIPT)


if __name__ == "__main__":
    main()
