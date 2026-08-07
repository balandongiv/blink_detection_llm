"""Table 9 — per-session and per-subject variability of Proposed-Med.

Writes ``writing/e_result/tab_best_session.tex``.

A macro-averaged headline hides how wide the spread across recordings is. This table
reports the best, worst and median session, and the same three points at subject level,
so the reader can see the operating range rather than only its centre.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402

SCRIPT = "tab9_best_session.py"


def main() -> None:
    best = P.load_exp2_best()
    pm = pd.concat(
        [best[(ds, "Proposed-Med")].assign(dataset=ds) for ds in ["raja", "cao"]],
        ignore_index=True,
    )
    pm["subject"] = pm["session"].str.split("/").str[0]

    ranked = pm.sort_values("f1", ascending=False).reset_index(drop=True)
    best_s, worst_s = ranked.iloc[0], ranked.iloc[-1]

    subjects = (pm.groupby(["dataset", "subject"])
                  .agg(n=("session", "nunique"), mean_f1=("f1", "mean"))
                  .reset_index()
                  .sort_values("mean_f1", ascending=False)
                  .reset_index(drop=True))
    best_u, worst_u = subjects.iloc[0], subjects.iloc[-1]
    n_sessions = len(pm)

    lines = [
        r"\begin{table}[ht]", r"  \centering",
        r"  \caption{Best and worst Proposed-Med sessions and subject-level summary across "
        + str(n_sessions) + r" Raja+Cao2018 sessions (best-channel-per-session).}",
        r"  \label{tab:best-session}",
        r"  \begin{tabular}{lllccl}", r"    \toprule",
        r"    Scope & Dataset & Unit & $n$ & Metric & Value \\", r"    \midrule",
        f"    Best session & {P.DSN[best_s['dataset']]} & {P.tex_escape(best_s['session'])} "
        f"& 1 & $F_1$ & {best_s['f1']:.4f} \\\\",
        f"    Worst session & {P.DSN[worst_s['dataset']]} & "
        f"{P.tex_escape(worst_s['session'])} & 1 & $F_1$ & {worst_s['f1']:.4f} \\\\",
        f"    Median session & all & {n_sessions} sessions & {n_sessions} & $F_1$ & "
        f"{pm['f1'].median():.4f} \\\\",
        f"    Best subject & {P.DSN[best_u['dataset']]} & {P.tex_escape(best_u['subject'])} "
        f"& {int(best_u['n'])} & Mean $F_1$ & {best_u['mean_f1']:.4f} \\\\",
        f"    Worst subject & {P.DSN[worst_u['dataset']]} & "
        f"{P.tex_escape(worst_u['subject'])} & {int(worst_u['n'])} & Mean $F_1$ & "
        f"{worst_u['mean_f1']:.4f} \\\\",
        f"    Median subject & all & {len(subjects)} subjects & {len(subjects)} & "
        f"Mean $F_1$ & {subjects['mean_f1'].median():.4f} \\\\",
        r"    \bottomrule", r"  \end{tabular}", r"\end{table}",
    ]
    P.write_tex(P.ER / "tab_best_session.tex", lines, SCRIPT)


if __name__ == "__main__":
    main()
