"""Table 4 — Proposed-approach F1 vs. both baselines, per dataset.

Writes ``writing/e_result/exp4/tab_f1_significance.tex`` (tab:f1_significance).

Replaces the deleted Figure 4/8 (``fig4_fig5_condition_prf.py``'s ``fig_condition_prf``,
which plotted precision/recall/F1 for the proposed approach alone). That figure's own
generator is gone; this table keeps only what a reader actually used from it -- each
condition's F1 and whether Proposed-approach differs significantly from it. The
precision/recall operating-point story now lives in Figure~\\ref{fig:exp2_pr_scatter}
instead.

No Pooled row (Internal and Cao2018 only). Both BLINKER-concat and MNE-annot get their
own column (displayed as "BLINKER"/"MNE" via the shared ``DISPLAY_LABEL``/``P.display``
mapping in ``paper_data.py``). Four tests total (two baselines x two datasets),
Bonferroni-corrected as one family; the asterisk sits on each baseline's own cell,
marking that specific baseline as significantly different from Proposed-approach (not a
single combined marker on the Proposed-approach cell) -- two-sided Wilcoxon signed-rank,
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


def compute(best: dict) -> list[tuple[str, float, dict[str, tuple[float, bool]]]]:
    """``(dataset label, Proposed-approach F1, {baseline -> (F1, significant)})``.

    Significance is Bonferroni-corrected across all four tests (two baselines x two
    datasets) shown in this table, not per dataset alone.
    """
    n_corrections = len(BASELINES) * 2
    rows = []
    for ds, label in [("raja", P.DSN["raja"]), ("cao", "Cao2018")]:
        f1_prop = P.macro(best, ds, PROPOSED)[2]
        per_baseline = {}
        for baseline in BASELINES:
            f1_base = P.macro(best, ds, baseline)[2]
            a, b = P.paired_f1(best, PROPOSED, baseline, ds_list=(ds,))
            _, p = stats.wilcoxon(a, b, alternative="two-sided")
            per_baseline[baseline] = (f1_base, min(1.0, p * n_corrections) < 0.05)
        rows.append((label, f1_prop, per_baseline))
    return rows


def build_table(rows: list[tuple[str, float, dict[str, tuple[float, bool]]]]) -> list[str]:
    blinker, mne = (P.display(b) for b in BASELINES)
    lines = [
        r"\begin{table}[ht]", r"  \centering",
        rf"  \caption{{Macro-$F_1$ (\%) for Proposed-approach and both baselines on "
        rf"Internal and Cao2018. An asterisk marks a baseline as significantly "
        rf"different from Proposed-approach (two-sided Wilcoxon signed-rank test on "
        rf"session-level $F_1$, $p<0.05$, Bonferroni-corrected across the four tests "
        rf"shown).}}",
        r"  \label{tab:f1_significance}",
        r"  \begin{tabular}{lccc}", r"    \toprule",
        rf"    Dataset & Proposed & {blinker} & {mne} \\", r"    \midrule",
    ]
    for label, f1_prop, per_baseline in rows:
        f1_blinker, sig_blinker = per_baseline["BLINKER-concat"]
        f1_mne, sig_mne = per_baseline["MNE-annot"]
        star_blinker = "*" if sig_blinker else ""
        star_mne = "*" if sig_mne else ""
        lines.append(
            f"    {label} & {P.fmt(f1_prop)} & {P.fmt(f1_blinker)}{star_blinker} & "
            f"{P.fmt(f1_mne)}{star_mne} \\\\"
        )
    lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]
    return lines


def main() -> None:
    best = P.load_exp2_best()
    rows = compute(best)
    P.write_tex(P.ER / "exp4" / "tab_f1_significance.tex", build_table(rows), SCRIPT)
    for label, f1_prop, per_baseline in rows:
        f1_blinker, sig_blinker = per_baseline["BLINKER-concat"]
        f1_mne, sig_mne = per_baseline["MNE-annot"]
        print(f"{label}: Proposed={f1_prop*100:.2f}%  "
              f"BLINKER={f1_blinker*100:.2f}% (sig={sig_blinker})  "
              f"MNE={f1_mne*100:.2f}% (sig={sig_mne})")


if __name__ == "__main__":
    main()
