"""Figure 10 — stability of Proposed-Med across epoch durations.

Writes:
  ``writing/figures/fig_exp3_epoch_duration.{pdf,png}``

There is no accompanying LaTeX table: the manuscript reports this comparison through the
figure alone (see the exp2/sec.tex figure caption), so the per-duration macro-$F_1$ and
significance markers are computed here only to drive the plot.

Epoch length is chosen for paradigm reasons, not for the detector, so a pipeline that is
sensitive to it is fragile in practice.

Experiment 1 found Fp1 and Fp2 to be, consistently, the two best-performing electrodes on
both corpora, together accounting for the large majority of best-channel-per-session picks
(Table~\ref{tab:channel_selection}). Rather than re-applying a per-session, per-duration
oracle over all 32 channels, this sweep is fixed to that Fp1/Fp2 pair — a deployable
two-electrode operating point instead of a channel oracle — while keeping every other
condition (the ``all_channel`` Stage-A gate, i.e. Fp1/Fp2 scored inside the full 32-channel
montage run) identical to the previous version. Fp1 and Fp2 are reported as two separate
series throughout (not averaged together), so each electrode's own stability across
durations remains visible.

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
import paper_style as S  # noqa: E402

REFERENCE_S = 30
#: Only the full-montage gate is reported, so the 30 s row matches Experiments 1 and 2.
GATE = "all_channel"
#: Fp1/Fp2 raw channel labels and canonical ordering — see paper_data.FP_CHANNELS.
FP_CHANNELS = P.FP_CHANNELS
CHANNEL_LABELS = P.CHANNEL_LABELS
#: Shared manuscript palette (see paper_style.py). Fp1/Fp2 sit side by side within every
#: dataset panel, so they get the same two colours used for the Proposed-Mean/Proposed-Med
#: pair (navy vs. lavender) rather than the two dataset colours, which are reserved for
#: telling the two corpora apart.
CHANNEL_COLORS = {"Fp1": S.NAVY, "Fp2": S.LAVENDER}


def f1_by_duration(ds: str, center_method: str) -> dict[str, dict[int, dict[str, float]]]:
    """``channel -> duration -> {dataset/session: F1}`` for Fp1 and Fp2, kept separate.

    Restricted to the ``all_channel`` gate, so each Fp1/Fp2 row is that electrode's score
    inside the full 32-channel montage run (Stage A screens epochs using every channel),
    not a standalone single-electrode pipeline. Fp1 and Fp2 are returned as two independent
    per-session series rather than being averaged together, so each electrode's own
    epoch-duration stability can be read on its own; both replace the previous per-session,
    per-duration argmax over all 32 channels with a fixed operating point, motivated by
    Experiment 1 finding Fp1 and Fp2 to be consistently the two best-performing electrodes
    on both corpora. The exp3 sweep also runs the ``frontal``, ``frontal_left`` and
    ``frontal_right`` gates; those are excluded here for the same reason as before — each
    gate is a self-contained detector, so mixing gates would compare Fp1/Fp2 scored under
    different Stage-A screening.
    """
    df = P.load("exp3", ds)
    df = df[(df.center_method == center_method) & (df.selection == GATE)]
    out = {}
    for raw_channel, label in FP_CHANNELS[ds]:
        sub_ch = df[df.channel == raw_channel]
        per_duration = {}
        for duration in P.DURATIONS:
            sub = sub_ch[sub_ch.epoch_duration_s == float(duration)]
            per_duration[duration] = {f"{ds}/{r.session}": r.f1 for r in sub.itertuples()}
        out[label] = per_duration
    return out


def compute_stats(per_ds: dict) -> tuple[dict, dict]:
    """``(label, channel) -> duration -> mean F1`` and the matching corrected $p$-values.

    ``label`` ranges over Internal and Cao2018; ``channel`` over Fp1 and Fp2. Feeds
    ``build_figure`` only — there is no LaTeX table for this comparison.
    """
    n_corrections = len(P.DURATIONS) - 1
    block_means, block_p = {}, {}
    for label, ds_list in [(P.DSN["raja"], ["raja"]), ("Cao2018", ["cao"])]:
        for channel in CHANNEL_LABELS:
            key = (label, channel)
            series = {
                d: {k: v for ds in ds_list for k, v in per_ds[ds][channel][d].items()}
                for d in P.DURATIONS
            }
            means = {d: float(np.mean(list(series[d].values()))) for d in P.DURATIONS}
            block_means[key] = means
            block_p[key] = {}
            reference = series[REFERENCE_S]

            for duration in P.DURATIONS:
                if duration == REFERENCE_S:
                    continue
                keys = sorted(set(reference) & set(series[duration]))
                a = np.array([series[duration][k] for k in keys])
                b = np.array([reference[k] for k in keys])
                try:
                    _, p = stats.wilcoxon(a, b, alternative="two-sided")
                    block_p[key][duration] = min(1.0, p * n_corrections)
                except ValueError:
                    pass
    return block_means, block_p


#: Every value in this table is above 75%, so the axis is clipped to 70--100% rather than
#: starting at 0. This is a deliberate departure from the zero-baseline convention used
#: elsewhere in the manuscript: clipping exaggerates the *visual* size of the differences
#: between bars, so the in-plot value labels and significance asterisks — not the bar
#: heights — remain what the reader is meant to compare.
Y_MIN, Y_MAX = 70, 100


def build_figure(block_means: dict, block_p: dict) -> None:
    """Grouped Fp1/Fp2 bars on a 70--100 percentage axis, one row per dataset.

    Internal is the top row and Cao2018 the bottom row, sharing one duration axis. Every
    bar carries its own value label, and a durations that differ significantly from the
    reference after Bonferroni correction additionally get a "*" drawn above the label --
    the same significance-marker convention as Figure 6/16 (``fmt_sig`` in
    ``fig16_exp1_single_channel_stats.py``): a plain, unrotated, bold asterisk, with the
    exact adjusted $p$-values left to the caption/prose rather than printed on the bars.
    Fp1 and Fp2 are drawn as separate bars rather than averaged.
    """
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 7.6), sharex=True)
    S.style_fig(fig)
    x = np.arange(len(P.DURATIONS))
    width = 0.38
    label_offset = 0.4
    star_offset = 6.0
    for ax, label in zip(axes, [P.DSN["raja"], "Cao2018"]):
        for offset, channel in zip((-width / 2, width / 2), CHANNEL_LABELS):
            means = block_means[(label, channel)]
            values = [means[d] * 100 for d in P.DURATIONS]
            ax.bar(x + offset, values, width, label=channel, color=CHANNEL_COLORS[channel],
                   edgecolor=S.NAVY, linewidth=0.6, zorder=3)
            for xi, d, v in zip(x, P.DURATIONS, values):
                ax.text(xi + offset, v + label_offset, f"{v:.2f}", ha="center",
                        va="bottom", fontsize=S.FONT_INPLOT, rotation=90, color=S.NAVY,
                        zorder=4)
                if block_p[(label, channel)].get(d, 1.0) < 0.05:
                    ax.text(xi + offset, v + star_offset, "*", ha="center", va="bottom",
                            fontsize=S.FONT_INPLOT, color=S.NAVY, fontweight="bold",
                            zorder=4)
        ax.set_ylim(Y_MIN, Y_MAX)
        ax.set_yticks(np.arange(Y_MIN, Y_MAX + 1, 5))
        ax.set_ylabel("macro-$F_1$ (%)")
        ax.set_title(label)
        S.style_axis(ax)
    axes[-1].set_xticks(x)
    axes[-1].set_xticklabels([f"{d} s" for d in P.DURATIONS])
    axes[-1].set_xlabel("epoch duration")
    # The axis is clipped rather than zero-based, so there is no in-plot space for a
    # legend that would not sit on top of the data. It goes above the top panel instead;
    # the LaTeX caption carries the title, so no in-figure title is drawn.
    legend = axes[0].legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.08),
                             ncol=2, fontsize=S.FONT_CHROME, handlelength=1.4,
                             columnspacing=1.6)
    for text in legend.get_texts():
        text.set_color(S.NAVY)
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
    block_means, block_p = compute_stats(per_ds)
    build_figure(block_means, block_p)

    for key, means in block_means.items():
        label, channel = key
        spread = max(means.values()) - min(means.values())
        print(f"{label}/{channel}: F1 range across {len(P.DURATIONS)} durations = "
              f"{spread:.4f} (min {min(means.values()):.4f}, max {max(means.values()):.4f})")


if __name__ == "__main__":
    main()
