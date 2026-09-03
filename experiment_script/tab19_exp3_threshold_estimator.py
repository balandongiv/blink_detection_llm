"""Table — Stage-B threshold-estimator comparison (Proposed-Med vs.\\ Proposed-Mean).

Writes:
  ``writing/e_result/exp3/tab_threshold_estimator_stageb.tex``  (tab:exp3_estimator)

Dedicated to Experiment 3 (Effect of the Threshold Estimator at Stage B): unlike
``exp4/tab_strategycomparison_30s_epoch.tex`` (Experiment 4, all four conditions), this table
isolates the two proposed configurations so the Stage-B estimator contrast is not read
off a table built for a different comparison.

Same underlying data and aggregation rule as the Experiment 4 table (best-channel-per-
session macro P/R/F1 at 30 s, ``all_channel`` gate): only the row selection differs.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402

SCRIPT = "tab19_exp3_threshold_estimator.py"
CONDS = ["Proposed-Mean", "Proposed-Med"]


def build(best: dict, sig: dict) -> list[str]:
    p_med_vs_mean = sig[("Proposed-Mean", "Proposed-Med")]
    caption = (
        r"  \caption{Effect of the Stage-B threshold estimator on the Internal and "
        r"Cao2018 driving-EEG corpora at 30\,s epochs. Proposed-Med (median/MAD) and "
        r"Proposed-Mean (mean/SD) are summarised at the best-channel-per-session "
        r"operating point (for every session the single channel or frontal sub-montage "
        r"with the highest $F_1$ is selected, then averaged over sessions). "
        r"Macro-averaged $F_1$ is reported as a percentage, per "
        r"dataset and pooled over all 104 sessions. Best $F_1$ per block in "
        r"\textbf{bold}. By a paired Wilcoxon signed-rank test on session-level $F_1$ "
        r"(Bonferroni-corrected over six condition pairs), Proposed-Med and "
        r"Proposed-Mean are statistically indistinguishable ($p="
        + f"{p_med_vs_mean:.2f}" + r"$).}"
    )
    lines = [
        r"\begin{table}[ht]", r"  \centering", caption,
        r"  \label{tab:exp3_estimator}", r"  \begin{tabular}{llc}", r"    \toprule",
        r"    Dataset & Condition & $F_1$ (\%) \\", r"    \midrule",
    ]
    for ds in ["raja", "cao"]:
        leader = max(CONDS, key=lambda c: P.macro(best, ds, c)[2])
        for i, cond in enumerate(CONDS):
            _, _, f_ = P.macro(best, ds, cond)
            f_cell = r"\textbf{" + P.fmt(f_) + "}" if cond == leader else P.fmt(f_)
            ds_cell = P.DSN[ds] if i == 0 else ""
            lines.append(f"    {ds_cell} & {cond} & {f_cell} \\\\")
        lines.append(r"    \midrule")

    leader = max(CONDS, key=lambda c: P.macro_pooled(best, c)[2])
    for i, cond in enumerate(CONDS):
        _, _, f_ = P.macro_pooled(best, cond)
        f_cell = r"\textbf{" + P.fmt(f_) + "}" if cond == leader else P.fmt(f_)
        ds_cell = "Pooled" if i == 0 else ""
        lines.append(f"    {ds_cell} & {cond} & {f_cell} \\\\")

    lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]
    return lines


def main() -> None:
    best = P.load_exp2_best()
    sig = P.bonferroni_wilcoxon(best)
    P.write_tex(P.ER / "exp3" / "tab_threshold_estimator_stageb.tex", build(best, sig), SCRIPT)


if __name__ == "__main__":
    main()
