"""Table 18 — single-electrode operation versus the same electrode under the full montage.

Writes ``writing/e_result/exp1/tab_exp1_solo_vs_montage.tex``.

The ``*_only`` subsets run Stage~A, Stage~B and Stage~C on one electrode, so pairing each
against that electrode's row inside the full-montage run isolates what the remaining 31
electrodes contribute to detection on it. It is the one contrast in the data that removes
channels from the complete system rather than testing a subset in isolation.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exp1_subset_data as S  # noqa: E402
import paper_data as P  # noqa: E402

SCRIPT = "tab18_exp1_solo_vs_montage.py"
OUT = P.ER / "exp1" / "tab_exp1_solo_vs_montage.tex"


def fmt_p(p: float) -> str:
    return r"$<0.001$" if p < 0.001 else f"${p:.3f}$"


def dataset_block(ds: str, title: str) -> list[str]:
    t = S.solo_vs_montage(ds)
    lines = [rf"\multicolumn{{9}}{{l}}{{\textit{{{title}}}}} \\[2pt]"]
    for _, r in t.iterrows():
        lines.append(
            f"{r['channel']} & {P.fmt(r['solo_p'])} & {P.fmt(r['solo_r'])} & "
            f"{P.fmt(r['solo_f1'])} & {P.fmt(r['gated_p'])} & {P.fmt(r['gated_r'])} & "
            f"{P.fmt(r['gated_f1'])} & ${P.fmt_pp(-r['delta'])}$ & "
            f"{fmt_p(r['p_bonf'])} \\\\"
        )
    return lines


def main() -> None:
    n_raja = S.solo_vs_montage("raja").attrs["n_comparisons"]
    n_cao = S.solo_vs_montage("cao").attrs["n_comparisons"]
    lines = [
        r"\begin{table}[htbp]", r"\centering", r"\footnotesize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\caption{Contribution of the remaining montage to detection on a single "
        r"electrode (Proposed-Med, median centre). \emph{Single electrode} is the "
        r"complete pipeline run on that electrode alone; \emph{full montage} is the same "
        r"electrode scored inside the 32-channel run, where Stage~A screens epochs using "
        r"every electrode. P, R and $F_1$ are reported as percentages. $\Delta F_1$ is the "
        r"gain from the other 31 electrodes, in percentage points, "
        r"(full montage minus single electrode), tested with a two-tailed Wilcoxon "
        r"signed-rank test on matched sessions and Bonferroni-corrected over the "
        rf"{n_raja} electrodes compared on Internal and {n_cao} on Cao2018. The single-electrode "
        r"columns involve no channel selection and are therefore free of the "
        r"best-channel-per-session oracle used elsewhere.}",
        r"\label{tab:exp1_solo_vs_montage}",
        r"\begin{tabular}{lrrrrrrrr}", r"\toprule",
        r" & \multicolumn{3}{c}{Single electrode} & \multicolumn{3}{c}{Full montage} & & \\",
        r"\cmidrule(lr){2-4}\cmidrule(lr){5-7}",
        r"Electrode & P (\%) & R (\%) & $F_1$ (\%) & P (\%) & R (\%) & $F_1$ (\%) & $\Delta F_1$ (pp) & $p$ \\",
        r"\midrule",
        *dataset_block("raja", f"{P.DSN['raja']} (EGI 128, 46 sessions)"),
        r"\midrule",
        *dataset_block("cao", "Cao2018 (10--20, 58 sessions)"),
        r"\bottomrule", r"\end{tabular}", r"\end{table}",
    ]
    P.write_tex(OUT, lines, SCRIPT)


if __name__ == "__main__":
    main()
