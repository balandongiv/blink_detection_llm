"""Table 10 — why do the worst sessions fail?

Writes ``writing/e_result/exp4/tab_failure_analysis.tex`` and prints the full ranking plus a
mechanism summary.

Sessions are ranked by Proposed-Med best-channel F1 and the bottom five per corpus are
reported with their ground-truth blink count, TP/FP/FN, error regime and best channel.
Reporting GT relative to the dataset median separates the two failure mechanisms: a
session can score badly because the detector genuinely under-performs, or because the
recording carries an atypical number of blinks in the first place.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402

SCRIPT = "tab10_failure_analysis.py"
BOTTOM_N = 5


def ranked_sessions(best: dict, ds: str) -> pd.DataFrame:
    """Proposed-Med sessions ordered worst-first, with GT count and error regime."""
    frame = best[(ds, "Proposed-Med")].copy()
    frame["gt"] = frame["tp"] + frame["fn"]
    frame["regime"] = np.where(frame["fp"] > frame["fn"], "FP-heavy", "FN-heavy")
    frame["best_channel"] = frame["best_channel"].apply(
        lambda c: P.display_channel(ds, c)
    )
    return frame.sort_values("f1").reset_index(drop=True)


def main() -> None:
    best = P.load_exp2_best()
    ranked = {ds: ranked_sessions(best, ds) for ds in ["raja", "cao"]}
    median_gt = {ds: ranked[ds]["gt"].median() for ds in ["raja", "cao"]}

    for ds in ["raja", "cao"]:
        frame = ranked[ds]
        print(f"[{P.DSN[ds]}] n={len(frame)}  median GT={median_gt[ds]:.0f}  "
              f"#sessions F1<0.6: {(frame.f1 < 0.6).sum()}  "
              f"F1<0.7: {(frame.f1 < 0.7).sum()}  min F1={frame.f1.min():.3f}")

    lines = [
        r"\begin{table*}[ht]", r"  \centering", r"  \scriptsize",
        r"  \setlength{\tabcolsep}{4pt}",
        r"  \caption{The " + str(BOTTOM_N) + r" lowest-$F_1$ Proposed-Med sessions per "
        r"corpus (best channel per session). GT is the ground-truth blink count "
        r"($\mathrm{TP}+\mathrm{FN}$) and GT/med is GT relative to the dataset median, "
        r"which separates genuine detector failure from recordings that simply carry an "
        r"atypical number of blinks. $F_1$ is reported as a percentage.}",
        r"  \label{tab:failure_analysis}",
        r"  \begin{tabular}{llrrrrcrrl}", r"    \toprule",
        r"    Dataset & Session & GT & TP & FP & FN & Regime & $F_1$ (\%) & GT/med & "
        r"Best channel \\",
        r"    \midrule",
    ]
    for ds in ["raja", "cao"]:
        first = True
        for _, row in ranked[ds].head(BOTTOM_N).iterrows():
            ds_cell = P.DSN[ds] if first else ""
            lines.append(
                f"    {ds_cell} & {P.tex_escape(row['session'])} & {int(row['gt'])} & "
                f"{int(row['tp'])} & {int(row['fp'])} & {int(row['fn'])} & "
                f"{row['regime']} & {row['f1'] * 100:.2f} & "
                f"{row['gt'] / median_gt[ds]:.2f}$\\times$ & "
                f"{P.tex_escape(row['best_channel'])} \\\\"
            )
            first = False
        lines.append(r"    \midrule" if ds == "raja" else r"    \bottomrule")
    lines += [r"  \end{tabular}", r"\end{table*}"]

    P.write_tex(P.ER / "exp4" / "tab_failure_analysis.tex", lines, SCRIPT)

    print("\n=== MECHANISM SUMMARY ===")
    for ds in ["raja", "cao"]:
        bottom = ranked[ds].head(BOTTOM_N)
        fn_heavy = int((bottom["regime"] == "FN-heavy").sum())
        atypical = int((bottom["gt"] > 1.5 * median_gt[ds]).sum())
        print(f"[{P.DSN[ds]}] bottom-{BOTTOM_N}: {fn_heavy}/{BOTTOM_N} FN-heavy "
              f"(under-detection); {atypical}/{BOTTOM_N} have GT > 1.5x median "
              f"(anomalous blink count); median GT/med ratio of the bottom group = "
              f"{(bottom['gt'] / median_gt[ds]).median():.1f}x")


if __name__ == "__main__":
    main()
