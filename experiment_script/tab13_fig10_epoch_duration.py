"""Table 13 and Figure 10 — stability of Proposed-Med across epoch durations.

Writes:
  ``writing/e_result/tab_effect_different_epoch_size.tex``
  ``writing/figures/fig_exp3_epoch_duration.{pdf,png}``

Epoch length is chosen for paradigm reasons, not for the detector, so a pipeline that is
sensitive to it is fragile in practice. Both artifacts are built from the same
best-channel-per-session numbers on the exp3 results CSV, so the figure cannot drift away
from the table.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402

SCRIPT = "tab13_fig10_epoch_duration.py"
REFERENCE_S = 30
DS_COLORS = {"raja": "#4C72B0", "cao": "#55A868"}


def _p_cell(p: float) -> str:
    """Render a corrected p-value; never print 0.000, which reads as exactly zero."""
    return r"$<0.001$" if p < 0.001 else f"{p:.3f}"


def f1_by_duration(ds: str, center_method: str) -> dict[int, dict[str, float]]:
    """``duration -> {dataset/session: F1}`` at the best-channel-per-session point."""
    df = P.load("exp3", ds)
    df = df[df.center_method == center_method]
    out = {}
    for duration in P.DURATIONS:
        rows = P.bps(df[df.epoch_duration_s == float(duration)])
        out[duration] = {f"{ds}/{r.session}": r.f1 for r in rows.itertuples()}
    return out


def build_table(per_ds: dict) -> tuple[list[str], dict]:
    n_corrections = len(P.DURATIONS) - 1
    lines = [
        r"\begin{table}[ht]", r"  \centering",
        r"  \caption{Best-channel-per-session macro-$F_1$ of Proposed-Med across epoch "
        r"durations. $p$-values (two-tailed Wilcoxon on session-level $F_1$, "
        r"Bonferroni-corrected over " + str(n_corrections) + r" non-reference durations) "
        r"compare each duration against the " + str(REFERENCE_S) + r"\,s reference. "
        r"\textbf{Bold} marks the best duration within each block.}",
        r"  \label{tab:epoch_duration}", r"  \begin{tabular}{llccc}", r"    \toprule",
        r"    Dataset & Epoch duration & $n$ & Macro $F_1$ & $p$ vs.\ "
        + str(REFERENCE_S) + r"\,s \\",
        r"    \midrule",
    ]
    block_means = {}
    for label, ds_list in [("Raja", ["raja"]), ("Cao2018", ["cao"]),
                           ("Pooled", ["raja", "cao"])]:
        series = {
            d: {k: v for ds in ds_list for k, v in per_ds[ds][d].items()}
            for d in P.DURATIONS
        }
        means = {d: float(np.mean(list(series[d].values()))) for d in P.DURATIONS}
        block_means[label] = means
        best_duration = max(P.DURATIONS, key=lambda d: means[d])
        reference = series[REFERENCE_S]

        for duration in P.DURATIONS:
            n = len(series[duration])
            mean_cell = (r"\textbf{" + f"{means[duration]:.4f}" + "}"
                         if duration == best_duration else f"{means[duration]:.4f}")
            if duration == REFERENCE_S:
                p_cell = "reference"
            else:
                keys = sorted(set(reference) & set(series[duration]))
                a = np.array([series[duration][k] for k in keys])
                b = np.array([reference[k] for k in keys])
                try:
                    _, p = stats.wilcoxon(a, b, alternative="two-sided")
                    p_cell = _p_cell(min(1.0, p * n_corrections))
                except ValueError:
                    p_cell = "n/a"
            ds_cell = label if duration == P.DURATIONS[0] else ""
            lines.append(
                f"    {ds_cell} & {duration}\\,s & {n} & {mean_cell} & {p_cell} \\\\"
            )
        lines.append(r"    \midrule")
    lines[-1] = r"    \bottomrule"
    lines += [r"  \end{tabular}", r"\end{table}"]
    return lines, block_means


def build_figure(block_means: dict) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(len(P.DURATIONS))
    width = 0.38
    for offset, (label, ds) in zip((-width / 2, width / 2),
                                   [("Raja", "raja"), ("Cao2018", "cao")]):
        values = [block_means[label][d] for d in P.DURATIONS]
        ax.bar(x + offset, values, width, label=label, color=DS_COLORS[ds])
    ax.set_xticks(x)
    ax.set_xticklabels([f"{d} s" for d in P.DURATIONS])
    ax.set_xlabel("epoch duration")
    ax.set_ylabel("macro-$F_1$ (best channel per session)")
    ax.set_ylim(0, 1.0)
    ax.legend(frameon=False)
    ax.set_title("Proposed-Med is stable across epoch durations")
    fig.tight_layout()
    P.save_fig(fig, "fig_exp3_epoch_duration")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--center-method", default="median",
                        help="Stage-B centre: median = Proposed-Med, mean = Proposed-Mean "
                             "(default: %(default)s).")
    args = parser.parse_args()

    per_ds = {ds: f1_by_duration(ds, args.center_method) for ds in ["raja", "cao"]}
    lines, block_means = build_table(per_ds)
    P.write_tex(P.ER / "tab_effect_different_epoch_size.tex", lines, SCRIPT)
    build_figure(block_means)

    for label, means in block_means.items():
        spread = max(means.values()) - min(means.values())
        print(f"{label}: F1 range across {len(P.DURATIONS)} durations = {spread:.4f} "
              f"(min {min(means.values()):.4f}, max {max(means.values()):.4f})")


if __name__ == "__main__":
    main()
