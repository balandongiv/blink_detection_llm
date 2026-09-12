"""Table — Stage-B threshold-estimator comparison (Proposed-Med vs.\\ Proposed-Mean).

Writes:
  ``writing/e_result/exp3/tab_threshold_estimator_stageb.tex``  (tab:exp3_estimator)

Dedicated to Experiment 3 (Effect of the Threshold Estimator at Stage B): unlike
``exp4/tab_strategycomparison_30s_epoch.tex`` (Experiment 4, all four conditions), this
table isolates the two proposed configurations so the Stage-B estimator contrast is not
read off a table built for a different comparison.

Experiment 1 found Fp1 and Fp2 to be, consistently, the two best-performing electrodes on
both corpora (Table~\ref{tab:channel_selection}). As in Experiment 2's epoch-duration
sweep, this table fixes the operating point to that Fp1/Fp2 pair — reported separately,
not averaged — instead of re-applying a best-channel-per-session oracle: for every
session, Fp1's and Fp2's precision/recall/$F_1$, each scored inside the full 32-channel
montage run (``all_channel`` gate) at the 30 s reference epoch, come straight from the
exp1 channel-selection sweep (the same per-channel-per-center-method rows Experiment 1
and Experiment 2 already draw from), filtered to ``center_method in {mean, median}``.
Proposed-Med and Proposed-Mean are compared within each electrode with a two-tailed
Wilcoxon signed-rank test on session-level $F_1$; since each electrode contributes exactly
one such test, no Bonferroni correction is applied.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402

SCRIPT = "tab19_exp3_threshold_estimator.py"
CONDS = ["Proposed-Mean", "Proposed-Med"]
CENTER_METHOD = {"Proposed-Mean": "mean", "Proposed-Med": "median"}


def load_channel(ds: str, channel: str, condition: str) -> pd.DataFrame:
    """One row per session: precision/recall/F1 for ``channel`` at its Stage-B centre.

    Restricted to the ``all_channel`` gate — Fp1/Fp2 scored inside the full 32-channel
    montage run, not a standalone single-electrode pipeline — at exp1's only epoch
    duration (30 s, the manuscript reference). Indexed by ``dataset/session`` so frames
    from different datasets can be pooled without session-id collisions.
    """
    raw_channel = next(rc for rc, label in P.FP_CHANNELS[ds] if label == channel)
    df = P.load("exp1", ds)
    df = df[(df.selection == P.ALL_CHANNEL) & (df.center_method == CENTER_METHOD[condition])
            & (df.channel == raw_channel)]
    df = df.assign(_k=ds + "/" + df["session"]).set_index("_k")
    return df[["precision", "recall", "f1"]]


def channel_stats(ds_list: list[str], channel: str) -> dict:
    per_cond = {
        cond: pd.concat([load_channel(ds, channel, cond) for ds in ds_list])
        for cond in CONDS
    }
    med, mean = per_cond["Proposed-Med"], per_cond["Proposed-Mean"]
    common = med.index.intersection(mean.index)
    med, mean = med.loc[common], mean.loc[common]
    _, p = stats.wilcoxon(med["f1"], mean["f1"], alternative="two-sided")
    means = {cond: tuple(per_cond[cond][col].mean() for col in ("precision", "recall", "f1"))
             for cond in CONDS}
    return {"means": means, "p": p, "n": len(common)}


def build(stats_by_block: dict) -> list[str]:
    lines = [
        r"\begin{table}[ht]", r"  \centering",
        r"  \caption{Effect of the Stage-B threshold estimator on the Internal and "
        r"Cao2018 driving-EEG corpora at 30\,s epochs, for Fp1 and Fp2 reported "
        r"separately (not averaged). Proposed-approach (median/MAD) and Proposed-Mean "
        r"(mean/SD) are each scored inside the full 32-channel montage run "
        r"(``all\_channel'' gate); Fp1 and Fp2 are the two consistently best-performing "
        r"electrodes identified in Experiment~1 (Table~\ref{tab:channel_selection}), so "
        r"unlike a best-channel-per-session oracle, each is a fixed, deployable "
        r"single-electrode operating point. Macro-averaged $F_1$ is reported as a "
        r"percentage, per dataset and pooled over all sessions. Best "
        r"$F_1$ per block in \textbf{bold}. $p$ is a two-tailed Wilcoxon signed-rank "
        r"test on session-level $F_1$ comparing Proposed-approach against Proposed-Mean "
        r"within that electrode (one test per electrode; not Bonferroni-corrected).}",
        r"  \label{tab:exp3_estimator}", r"  \begin{tabular}{lllc}", r"    \toprule",
        r"    Dataset & Channel & Condition & $F_1$ (\%) \\",
        r"    \midrule",
    ]
    for label in [P.DSN["raja"], "Cao2018", "Pooled"]:
        for channel in P.CHANNEL_LABELS:
            block = stats_by_block[(label, channel)]
            leader = max(CONDS, key=lambda c: block["means"][c][2])
            for i, cond in enumerate(CONDS):
                _, _, f_ = block["means"][cond]
                f_cell = r"\textbf{" + P.fmt(f_) + "}" if cond == leader else P.fmt(f_)
                ds_cell = label if i == 0 else ""
                ch_cell = channel if i == 0 else ""
                lines.append(
                    f"    {ds_cell} & {ch_cell} & {P.display(cond)} & {f_cell} \\\\"
                )
            p = block["p"]
            p_str = r"$<0.001$" if p < 0.001 else f"{p:.3f}"
            lines.append(
                r"    \multicolumn{3}{r}{$p$ vs.\ Proposed-Mean} & "
                + p_str + r" \\"
            )
            lines.append(r"    \midrule")
    lines[-1] = r"    \bottomrule"
    lines += [r"  \end{tabular}", r"\end{table}"]
    return lines


def main() -> None:
    stats_by_block = {}
    for label, ds_list in [(P.DSN["raja"], ["raja"]), ("Cao2018", ["cao"]),
                           ("Pooled", ["raja", "cao"])]:
        for channel in P.CHANNEL_LABELS:
            stats_by_block[(label, channel)] = channel_stats(ds_list, channel)

    P.write_tex(P.ER / "exp3" / "tab_threshold_estimator_stageb.tex", build(stats_by_block),
                SCRIPT)

    for (label, channel), block in stats_by_block.items():
        med = tuple(v * 100 for v in block["means"]["Proposed-Med"])
        mean = tuple(v * 100 for v in block["means"]["Proposed-Mean"])
        print(f"{label}/{channel} (n={block['n']}): Med P/R/F1={med[0]:.2f}/{med[1]:.2f}/"
              f"{med[2]:.2f}  Mean P/R/F1={mean[0]:.2f}/{mean[1]:.2f}/{mean[2]:.2f}  "
              f"p={block['p']:.4f}")


if __name__ == "__main__":
    main()
