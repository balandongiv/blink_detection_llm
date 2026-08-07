"""C6 - Literature-positioning table for single-channel / threshold-based blink
and EOG detectors.

This table positions the present detector against prior threshold-centred and
hybrid-threshold detectors that are already cited in the manuscript
(references_from_csv.bib) and described in the Related Work section. Reported
metrics across that literature use different datasets, blink definitions, sampling
rates, and matching criteria (sample-level vs. event-level), so a raw F1-vs-F1
ranking would be misleading. Cells whose value cannot be extracted into a directly
comparable event-level form from the cited source are marked ``n/r'' (not reported
in comparable form); NO numbers are invented or estimated. Only the final row --
this work -- carries quantitative detection figures, recomputed at the
best-channel-per-session event-level operating point.

Produces:
  writing/c_literature_review/tab_literature_comparison.tex

Run inside conda env double_threshold_algo (pure string assembly; no CSV read).
"""
from __future__ import annotations
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "writing" / "c_literature_review" / "tab_literature_comparison.tex"
OUT.parent.mkdir(parents=True, exist_ok=True)

# (citep_key, Method label, Signal / channel, Evaluation data, Matching criterion, Reported metric)
# Qualitative attributes are taken from the Related Work narrative; metric cells for
# prior work are "n/r" because a directly comparable event-level value is not
# available in this repository for those sources.
ROWS = [
    ("chang2016detection",     "Chang et al.",      "Single prefrontal EEG",   "Own EEG",            "n/r", "n/r"),
    ("tran2021detection",      "Tran et al.",       "Single/few-channel EEG",  "Own EEG",            "n/r", "n/r"),
    ("zhang2023method",        "Zhang et al.",      "Frontal EEG (real-time)", "Own EEG",            "n/r", "n/r"),
    ("wang2025sliding",        "Wang et al.",       "Single-channel EEG",      "Own EEG",            "n/r", "n/r"),
    ("kleifges2017blinker",    "BLINKER",           "Single channel (EEG/EOG)","Multiple corpora",   "n/r", "n/r"),
    ("cao2021unsupervised",    "Cao et al.",        "Multi-channel EEG",       "Own EEG",            "n/r", "n/r"),
    ("agarwal2019blink",       "Agarwal \\& Sivakumar", "Single-channel EEG",  "Own EEG",            "n/r", "n/r"),
    ("valderrama2018automatic","Valderrama et al.", "Single-channel EOG/EEG",  "Own recordings",     "n/r", "n/r"),
    ("guttmann2019new",        "Guttmann-Flury et al.", "Multi-channel EEG",   "Own EEG",            "n/r", "n/r"),
]

def _this_work_row():
    """The present detector's row, read from publication_results so it cannot drift."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import paper_data as P

    best = P.load_exp2_best()
    raja = P.macro(best, "raja", "Proposed-Med")[2]
    cao = P.macro(best, "cao", "Proposed-Med")[2]
    return (r"\textbf{This work (Proposed-Med)}", "Single frontopolar EEG",
            "Raja + Cao2018 driving", "Event-level overlap (IoU 0.1)",
            rf"macro-$F_1$ {raja:.2f} / {cao:.2f}")


THIS_WORK = _this_work_row()

SRC = "% Source: publication_results/ + references_from_csv.bib; script experiment_script/tab16_literature_comparison.py"
# Placed with [H] (float package) so the wide comparison table is anchored exactly at its
# discussion reference rather than floating past the bibliography.
L = [SRC, r"\begin{table}[H]", r"  \centering",
     r"  \caption{Qualitative positioning of the present detector against prior single-channel and "
     r"threshold-based blink/EOG detectors cited in this work. Because the prior studies use different "
     r"datasets, blink definitions, sampling rates and especially different matching criteria "
     r"(sample-level versus event-level), their reported metrics are not directly comparable to an "
     r"event-level $F_1$; such cells are marked ``n/r'' (not reported in comparable form) rather than "
     r"populated with non-comparable numbers. Only the final row reports quantitative detection figures, "
     r"recomputed at the best-channel-per-session event-level operating point (macro-$F_1$ on Raja / "
     r"Cao2018). The comparison is therefore qualitative by design.}",
     r"  \label{tab:literature_comparison}",
     r"  \setlength{\tabcolsep}{4pt}",
     r"  \begin{tabular}{p{0.19\linewidth}p{0.16\linewidth}p{0.16\linewidth}p{0.21\linewidth}p{0.12\linewidth}}",
     r"    \toprule",
     r"    Method & Signal / channel & Evaluation data & Matching criterion & Reported metric \\",
     r"    \midrule"]
for key, label, sig, data, match, metric in ROWS:
    L.append(f"    {label}~\\citep{{{key}}} & {sig} & {data} & {match} & {metric} \\\\")
L.append(r"    \midrule")
L.append(f"    {THIS_WORK[0]} & {THIS_WORK[1]} & {THIS_WORK[2]} & {THIS_WORK[3]} & {THIS_WORK[4]} \\\\")
L += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]
OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
print("wrote", OUT)
