"""Table 4 — CECT F1 vs. both baselines, per dataset.

Writes ``writing/e_result/exp3/tab_f1_significance.tex`` (tab:f1_significance).

Replaces the deleted Figure 4/8 (``fig4_fig5_condition_prf.py``'s ``fig_condition_prf``,
which plotted precision/recall/F1 for the proposed approach alone). That figure's own
generator is gone; this table keeps only what a reader actually used from it -- each
condition's F1 and whether CECT differs significantly from it. The
precision/recall operating-point story now lives in Figure~\\ref{fig:exp2_pr_scatter}
instead.

No Pooled row (Internal and Cao2018 only). Both BLINKER-concat and MNE-annot get their
own column (displayed as "BLINKER"/"MNE" via the shared ``DISPLAY_LABEL``/``P.display``
mapping in ``paper_data.py``). Four tests total (two baselines x two datasets),
Bonferroni-corrected as one family; the asterisk sits on each baseline's own cell,
marking that specific baseline as significantly different from CECT (not a
single combined marker on the CECT cell) -- two-sided Wilcoxon signed-rank,
session-level F1. Exact $p$-values are not printed on the table, only the threshold in
the caption, matching the Figure 7/10 asterisk convention used throughout the manuscript.

Column headers are kept short (condition name only, no repeated "$F_1$ (\\%)") because
this table renders inside the double-column ``ieeeaccess`` class
(``writing/ACCESS_latex_template_20260513/access.tex``), where four wordy headers
overflowed the column width; "all values are macro-$F_1$ percentages" is stated once in
the caption instead.

Data extraction (for auditing):
  Source CSV : via ``paper_data.load_exp2_best()`` -> ``paper_data.load("exp2", ds)``,
               which resolves (since the 2026-09-14 folder rename) to
               ``publication_results/exp3_{raja,cao2018}/exp2_strategy_comparison_
               {raja,cao2018}_results.csv`` -- the manuscript's Experiment 3 (Strategy
               Comparison) data, even though the internal key/CSV filename say "exp2"
               (historical; see ``experiment_script/setup/exp_path.yaml``'s inline note).
  Filter     : best-channel-per-session (``paper_data.bps``: argmax session-level F1),
               computed separately per ``condition`` in {BLINKER-concat, MNE-annot,
               Proposed-Mean, Proposed-Med} -- no fixed ``center_method``/``selection``
               filter is applied beyond that per-session argmax, since each condition's
               own best channel is the oracle picked.
  Channels   : not electrode-specific -- best-channel-per-session is a per-session oracle
               over all channels, not a fixed montage subset.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402

SCRIPT = "res_exp3_table_strategy_f1_significance.py"
PROPOSED = "Proposed-Med"
BASELINES = ["BLINKER-concat", "MNE-annot"]


def mean_sd(best: dict, ds: str, cond: str) -> tuple[float, float]:
    """Session-mean and sample SD of F1 for one dataset and condition."""
    f1 = best[(ds, cond)]["f1"]
    return f1.mean(), f1.std()


def cell(m_sd: tuple[float, float], star: str = "") -> str:
    """``mean $\\pm$ SD*`` table cell, in percent."""
    return rf"{P.fmt(m_sd[0])} $\pm$ {P.fmt(m_sd[1])}{star}"


def compute(best: dict) -> list[tuple[str, tuple, dict[str, tuple[tuple, bool]]]]:
    """``(dataset label, CECT (F1, SD), {baseline -> ((F1, SD), significant)})``.

    Significance is Bonferroni-corrected across all four tests (two baselines x two
    datasets) shown in this table, not per dataset alone.
    """
    n_corrections = len(BASELINES) * 2
    rows = []
    for ds, label in [("raja", P.DSN["raja"]), ("cao", "Cao2018")]:
        f1_prop = mean_sd(best, ds, PROPOSED)
        per_baseline = {}
        for baseline in BASELINES:
            f1_base = mean_sd(best, ds, baseline)
            a, b = P.paired_f1(best, PROPOSED, baseline, ds_list=(ds,))
            _, p = stats.wilcoxon(a, b, alternative="two-sided")
            per_baseline[baseline] = (f1_base, min(1.0, p * n_corrections) < 0.05)
        rows.append((label, f1_prop, per_baseline))
    return rows


def build_table(rows: list[tuple[str, tuple, dict[str, tuple[tuple, bool]]]]) -> list[str]:
    lines = [
        r"\begin{table}[ht]", r"  \centering",
        r"  \caption{Session-mean $F_1$ (\%, mean $\pm$ SD) of CECT, "
        r"the BLINKER-threshold baseline, and MNE on Internal and Cao2018. All conditions are evaluated "
        r"at the retrospective best-channel-per-session operating point. An asterisk marks a "
        r"baseline whose session-level $F_1$ differs significantly from that of CECT "
        r"(two-tailed Wilcoxon signed-rank test paired by session, Bonferroni-corrected "
        r"over the four comparisons shown, adjusted $p < 0.05$).}",
        r"  \label{tab:f1_significance}",
        r"  \begin{tabular}{lccc}", r"    \toprule", "",
        r"    Dataset & CECT & BLINKER-threshold & MNE \\", r"    \midrule",
    ]
    for label, f1_prop, per_baseline in rows:
        f1_blinker, sig_blinker = per_baseline["BLINKER-concat"]
        f1_mne, sig_mne = per_baseline["MNE-annot"]
        star_blinker = "*" if sig_blinker else ""
        star_mne = "*" if sig_mne else ""
        lines.append(
            rf"    {label} & {cell(f1_prop)} & {cell(f1_blinker, star_blinker)} & "
            rf"{cell(f1_mne, star_mne)} \\"
        )
    lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]
    return lines


def main() -> None:
    best = P.load_exp2_best()
    rows = compute(best)
    P.write_tex(P.ER / "exp3" / "tab_f1_significance.tex", build_table(rows), SCRIPT)
    for label, f1_prop, per_baseline in rows:
        f1_blinker, sig_blinker = per_baseline["BLINKER-concat"]
        f1_mne, sig_mne = per_baseline["MNE-annot"]
        print(f"{label}: CECT={f1_prop[0]*100:.2f}%  "
              f"BLINKER={f1_blinker[0]*100:.2f}% (sig={sig_blinker})  "
              f"MNE={f1_mne[0]*100:.2f}% (sig={sig_mne})")


if __name__ == "__main__":
    main()
