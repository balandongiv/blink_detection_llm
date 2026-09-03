"""Table 11 and Figure 9 — how often each electrode wins the best-channel selection.

Writes:
  ``writing/e_result/exp1/tab_channel_selection.tex``
  ``writing/figures/fig_channel_selection.{pdf,png}``

Experiment 1 says which channel is best on average; this says how concentrated that choice
is in practice. Pooling the per-session winners over the four conditions shows whether the
frontopolar advantage is a stable per-session fact or an artefact of averaging.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402
import paper_style as S  # noqa: E402

SCRIPT = "tab11_fig9_channel_selection_frequency.py"
TOP_N = 5


def winners(best: dict, ds: str) -> pd.Series:
    """Best channel per session, pooled over the four conditions, by scalp location."""
    series = pd.concat([best[(ds, cond)].set_index("session")["best_channel"]
                        for cond in P.CONDS])
    return series.apply(lambda c: P.display_channel(ds, c))


def main() -> None:
    best = P.load_exp2_best()
    freq = {ds: winners(best, ds).value_counts() for ds in ["raja", "cao"]}

    lines = [
        r"\begin{table}[ht]", r"  \centering", r"  \scriptsize",
        r"  \setlength{\tabcolsep}{3pt}",
        r"  \caption{Best-channel selection frequencies pooled over the four conditions "
        r"(best-channel-per-session). The " + str(TOP_N) + r" most frequently selected "
        r"electrodes are listed per dataset, with the count and the fraction of all "
        r"session $\times$ condition selections.}",
        r"  \label{tab:channel_selection}",
        r"  \begin{tabular}{llp{0.66\linewidth}}", r"    \toprule",
        r"    Dataset & Summary & Frequencies \\", r"    \midrule",
    ]
    for ds in ["raja", "cao"]:
        counts = freq[ds]
        total = int(counts.sum())
        items = "; ".join(
            f"{ch} {n}/{total} ({n / total:.2f})" for ch, n in counts.head(TOP_N).items()
        )
        lines.append(f"    {P.DSN[ds]} & Channels & {items} \\\\")
    lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]
    P.write_tex(P.ER / "exp1" / "tab_channel_selection.tex", lines, SCRIPT)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    S.style_fig(fig)
    for ax, ds in zip(axes, ["raja", "cao"]):
        counts = freq[ds].head(10)
        total = int(freq[ds].sum())
        ax.bar(range(len(counts)), counts.to_numpy() / total,
               color=S.DATASET_COLORS[P.DSN[ds]], edgecolor=S.NAVY)
        ax.set_xticks(range(len(counts)))
        ax.set_xticklabels(counts.index, rotation=45, ha="right", fontsize=8)
        ax.set_title(P.DSN[ds])
        ax.set_ylim(0, 1.0)
        ax.set_ylabel("fraction of selections" if ds == "raja" else "")
        S.style_axis(ax)
    fig.suptitle("Best-channel selection frequency, pooled over the four conditions",
                 color=S.NAVY)
    fig.tight_layout()
    P.save_fig(fig, "fig_channel_selection")
    plt.close(fig)

    for ds in ["raja", "cao"]:
        counts = freq[ds]
        total = int(counts.sum())
        top = counts.index[0]
        print(f"{P.DSN[ds]}: {top} wins {counts.iloc[0]}/{total} "
              f"({counts.iloc[0] / total:.3f}) of selections; "
              f"{counts.size} distinct channels ever selected")


if __name__ == "__main__":
    main()
