"""Table 13 and Figure 10 — stability of Proposed-Med across epoch durations.

Writes:
  ``writing/e_result/exp2/tab_effect_different_epoch_size.tex``
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
#: Only the full-montage gate is reported, so the 30 s row matches Experiments 1 and 2.
GATE = "all_channel"
#: Categorical slots 1 and 2. Checked with the palette validator: adjacent-pair CVD
#: separation dE 24.7 (protan) / 32.7 (tritan), normal-vision dE 33.6, both >= 3:1
#: contrast on a light surface — the pair stays distinguishable in print and greyscale.
DS_COLORS = {"raja": "#2a78d6", "cao": "#eb6834"}


def _p_cell(p: float) -> str:
    """Render a corrected p-value; never print 0.000, which reads as exactly zero."""
    return r"$<0.001$" if p < 0.001 else f"{p:.3f}"


def f1_by_duration(ds: str, center_method: str) -> dict[int, dict[str, float]]:
    """``duration -> {dataset/session: F1}`` at the best-channel-per-session point.

    Restricted to the ``all_channel`` gate. The exp3 sweep also runs ``frontal``,
    ``frontal_left`` and ``frontal_right``, and each gate is a self-contained detector:
    Stage A screens epochs using only that gate's channels, so the same electrode gets a
    different score under each. Taking the per-session argmax across gates would select
    over both channel *and* gate, which is a strictly broader oracle than the one
    Experiments 1 and 2 report — and it inflates the mean even though the narrower gates
    are individually worse, because the argmax is taken after the scores are known.
    Restricting here keeps the 30 s row identical to the same condition in those
    experiments.
    """
    df = P.load("exp3", ds)
    df = df[(df.center_method == center_method) & (df.selection == GATE)]
    out = {}
    for duration in P.DURATIONS:
        rows = P.bps(df[df.epoch_duration_s == float(duration)])
        out[duration] = {f"{ds}/{r.session}": r.f1 for r in rows.itertuples()}
    return out


def build_table(per_ds: dict) -> tuple[list[str], dict, dict]:
    n_corrections = len(P.DURATIONS) - 1
    lines = [
        r"\begin{table}[ht]", r"  \centering",
        r"  \caption{Best-channel-per-session macro-$F_1$ of Proposed-Med across epoch "
        r"durations, computed on the full 32-channel montage: for every session the "
        r"single electrode with the highest $F_1$ within that montage run is selected, "
        r"then averaged over sessions. This is the same operating point and channel set "
        r"reported in Experiments~1 and~3, so the "
        + str(REFERENCE_S) + r"\,s row reproduces those values exactly. "
        r"$p$-values (two-tailed Wilcoxon on session-level $F_1$, "
        r"Bonferroni-corrected over " + str(n_corrections) + r" non-reference durations) "
        r"compare each duration against the " + str(REFERENCE_S) + r"\,s reference. "
        r"Macro $F_1$ is reported as a percentage. "
        r"\textbf{Bold} marks the best duration within each block.}",
        r"  \label{tab:epoch_duration}", r"  \begin{tabular}{llccc}", r"    \toprule",
        r"    Dataset & Epoch duration & $n$ & Macro $F_1$ (\%) & $p$ vs.\ "
        + str(REFERENCE_S) + r"\,s \\",
        r"    \midrule",
    ]
    block_means, block_p = {}, {}
    for label, ds_list in [(P.DSN["raja"], ["raja"]), ("Cao2018", ["cao"]),
                           ("Pooled", ["raja", "cao"])]:
        series = {
            d: {k: v for ds in ds_list for k, v in per_ds[ds][d].items()}
            for d in P.DURATIONS
        }
        means = {d: float(np.mean(list(series[d].values()))) for d in P.DURATIONS}
        block_means[label] = means
        block_p[label] = {}
        best_duration = max(P.DURATIONS, key=lambda d: means[d])
        reference = series[REFERENCE_S]

        for duration in P.DURATIONS:
            n = len(series[duration])
            mean_cell = (r"\textbf{" + f"{means[duration] * 100:.2f}" + "}"
                         if duration == best_duration else f"{means[duration] * 100:.2f}")
            if duration == REFERENCE_S:
                p_cell = "reference"
            else:
                keys = sorted(set(reference) & set(series[duration]))
                a = np.array([series[duration][k] for k in keys])
                b = np.array([reference[k] for k in keys])
                try:
                    _, p = stats.wilcoxon(a, b, alternative="two-sided")
                    p_corr = min(1.0, p * n_corrections)
                    block_p[label][duration] = p_corr
                    p_cell = _p_cell(p_corr)
                except ValueError:
                    p_cell = "n/a"
            ds_cell = label if duration == P.DURATIONS[0] else ""
            lines.append(
                f"    {ds_cell} & {duration}\\,s & {n} & {mean_cell} & {p_cell} \\\\"
            )
        lines.append(r"    \midrule")
    lines[-1] = r"    \bottomrule"
    lines += [r"  \end{tabular}", r"\end{table}"]
    return lines, block_means, block_p


def build_figure(block_means: dict, block_p: dict) -> None:
    """Grouped bars on a 0--100 percentage axis.

    The full 0--100 range is kept, so bar length stays proportional to $F_1$ and no
    difference is exaggerated by a truncated baseline. At that range the gaps between
    durations are a fraction of a bar width, so every bar carries its own value label
    and a marker on the durations that differ significantly from the reference — the
    printed numbers, not the bar heights, are what the reader compares.
    """
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = np.arange(len(P.DURATIONS))
    width = 0.38
    for offset, (label, ds) in zip((-width / 2, width / 2),
                                   [(P.DSN["raja"], "raja"), ("Cao2018", "cao")]):
        values = [block_means[label][d] * 100 for d in P.DURATIONS]
        ax.bar(x + offset, values, width, label=label, color=DS_COLORS[ds],
               edgecolor="white", linewidth=0.6, zorder=3)
        for xi, d, v in zip(x, P.DURATIONS, values):
            star = "*" if block_p[label].get(d, 1.0) < 0.05 else ""
            ax.text(xi + offset, v + 1.5, f"{v:.2f}{star}", ha="center", va="bottom",
                    fontsize=6.5, rotation=90, color="#333333", zorder=4)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{d} s" for d in P.DURATIONS])
    ax.set_xlabel("epoch duration")
    ax.set_ylabel("macro-$F_1$ (%)")
    ax.set_ylim(0, 100)
    ax.set_yticks(np.arange(0, 101, 20))
    ax.grid(axis="y", color="#d9d9d9", linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    # Bars span the whole 0--100 axis, so there is no in-plot space for a legend that
    # would not sit on top of the data. It goes above the axes instead; the LaTeX
    # caption carries the title, so no in-figure title is drawn.
    ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.005),
              ncol=2, fontsize=9, handlelength=1.4, columnspacing=1.6)
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
    lines, block_means, block_p = build_table(per_ds)
    P.write_tex(P.ER / "exp2" / "tab_effect_different_epoch_size.tex", lines, SCRIPT)
    build_figure(block_means, block_p)

    for label, means in block_means.items():
        spread = max(means.values()) - min(means.values())
        print(f"{label}: F1 range across {len(P.DURATIONS)} durations = {spread:.4f} "
              f"(min {min(means.values()):.4f}, max {max(means.values()):.4f})")


if __name__ == "__main__":
    main()
