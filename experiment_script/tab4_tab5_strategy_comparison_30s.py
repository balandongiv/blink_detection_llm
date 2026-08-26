"""Tables 4 and 5 — headline strategy comparison at 30 s, and baseline inversions.

Writes:
  ``writing/e_result/exp4/tab_strategycomparison_30s_epoch.tex``  (tab:exp1_main)
  ``writing/e_result/exp4/tab_exp2_inversions.tex``                (tab:exp2_inversions)

Every condition is summarised at its best-channel-per-session operating point, and the
same rule is applied to all four conditions so none is given a private advantage.
Significance is a paired Wilcoxon signed-rank test on session-level F1, Bonferroni
corrected over the six condition pairs.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402

SCRIPT = "tab4_tab5_strategy_comparison_30s.py"


def _p_phrase(p: float) -> str:
    """Render a Bonferroni-corrected p-value for the caption."""
    if p < 1e-9:
        return r"$p<10^{-9}$"
    if p < 0.001:
        return r"$p<0.001$"
    return f"$p={p:.2f}$"


def build_main(best: dict, sig: dict) -> list[str]:
    vs_blinker = sig[("BLINKER-concat", "Proposed-Med")]
    vs_mne = sig[("MNE-annot", "Proposed-Med")]
    vs_mean = sig[("Proposed-Mean", "Proposed-Med")]
    caption = (
        r"  \caption{Strategy comparison on the Internal and Cao2018 driving-EEG corpora at "
        r"30\,s epochs. Each condition is summarised at its best-channel-per-session "
        r"operating point (for every session the single channel or frontal sub-montage with "
        r"the highest $F_1$ is selected, then averaged over sessions); the same rule is "
        r"applied to all four conditions. Macro-averaged precision, recall and $F_1$ are "
        r"reported as percentages, per dataset and pooled over all 104 sessions. Best $F_1$ per block in "
        r"\textbf{bold}. By paired Wilcoxon signed-rank tests on session-level $F_1$ "
        r"(Bonferroni-corrected over six pairs), Proposed-Med significantly exceeds "
        r"BLINKER-concat (" + _p_phrase(vs_blinker) + r") and MNE-annot ("
        + _p_phrase(vs_mne) + r") but not Proposed-Mean (" + _p_phrase(vs_mean) + r").}"
    )
    lines = [
        r"\begin{table*}[ht]", r"  \centering", caption,
        r"  \label{tab:exp1_main}", r"  \begin{tabular}{llccc}", r"    \toprule",
        r"    Dataset & Condition & Precision (\%) & Recall (\%) & $F_1$ (\%) \\", r"    \midrule",
    ]
    for ds in ["raja", "cao"]:
        leader = max(P.CONDS, key=lambda c: P.macro(best, ds, c)[2])
        for i, cond in enumerate(P.CONDS):
            p_, r_, f_ = P.macro(best, ds, cond)
            f_cell = r"\textbf{" + P.fmt(f_) + "}" if cond == leader else P.fmt(f_)
            ds_cell = P.DSN[ds] if i == 0 else ""
            lines.append(f"    {ds_cell} & {cond} & {P.fmt(p_)} & {P.fmt(r_)} & {f_cell} \\\\")
        lines.append(r"    \midrule")

    leader = max(P.CONDS, key=lambda c: P.macro_pooled(best, c)[2])
    for i, cond in enumerate(P.CONDS):
        p_, r_, f_ = P.macro_pooled(best, cond)
        f_cell = r"\textbf{" + P.fmt(f_) + "}" if cond == leader else P.fmt(f_)
        ds_cell = "Pooled" if i == 0 else ""
        lines.append(f"    {ds_cell} & {cond} & {P.fmt(p_)} & {P.fmt(r_)} & {f_cell} \\\\")

    lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table*}"]
    return lines


def build_inversions() -> list[str]:
    lines = [
        r"\begin{table}[ht]", r"  \centering",
        r"  \caption{Channel groups and datasets where a baseline algorithm equals or "
        r"exceeds Proposed-Med in best-channel-per-session macro-$F_1$. Values are "
        r"percentages; $\Delta F_1$ is in percentage points.}",
        r"  \label{tab:exp2_inversions}",
        r"  \begin{tabular}{lllccc}", r"    \toprule",
        r"    Dataset & Selection & Baseline & BL-$F_1$ (\%) & Prop-$F_1$ (\%) & $\Delta F_1$ (pp) \\",
        r"    \midrule",
    ]
    inversions = []
    for ds in ["raja", "cao"]:
        df = P.load("exp2", ds)
        for sel in sorted(df["selection"].unique()):
            prop = (df[(df.condition == "Proposed-Med") & (df.selection == sel)]
                    .groupby("session")["f1"].max().mean())
            for baseline in ["BLINKER-concat", "MNE-annot"]:
                base = (df[(df.condition == baseline) & (df.selection == sel)]
                        .groupby("session")["f1"].max().mean())
                if base >= prop:
                    inversions.append(
                        (P.DSN[ds], P.tex_escape(sel), baseline, base, prop, base - prop)
                    )
    if inversions:
        for ds, sel, baseline, base, prop, delta in sorted(inversions, key=lambda x: -x[5]):
            lines.append(
                f"    {ds} & {sel} & {baseline} & {P.fmt(base)} & {P.fmt(prop)} & "
                f"+{P.fmt(delta)} \\\\"
            )
    else:
        lines.append(
            r"    \multicolumn{6}{c}{No inversions --- Proposed-Med leads on every "
            r"channel group.} \\"
        )
    lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]
    return lines


def main() -> None:
    best = P.load_exp2_best()
    sig = P.bonferroni_wilcoxon(best)
    P.write_tex(P.ER / "exp4" / "tab_strategycomparison_30s_epoch.tex", build_main(best, sig), SCRIPT)
    P.write_tex(P.ER / "exp4" / "tab_exp2_inversions.tex", build_inversions(), SCRIPT)

    print("\n--- Bonferroni-corrected Wilcoxon p-values (two-sided) ---")
    for (a, b), p in sig.items():
        print(f"   {a:16s} vs {b:16s}  p={p:.4g}")


if __name__ == "__main__":
    main()
