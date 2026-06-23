"""Butterfly-plot reporting for detected blink regions (TP / FN / FP).

Used by the channel-selection experiment (``exp1_channel_selection_*``) to render,
for each channel-selection group, an overlay ("butterfly") of every detected /
missed blink waveform, separated into:

    TP  — detected region that matched a ground-truth blink
    FN  — ground-truth blink with no matching detection
    FP  — detected region with no matching ground-truth blink

(There is no waveform for a true negative — an epoch with no blink and no
detection — so TN is not plotted.)

Both an *all-subject* panel and *per-subject* panels are produced per group, so a
reader can visually compare how cleanly each channel group separates real blinks
from false detections and decide which spatial selection is most trustworthy.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mne  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

CATEGORY_COLORS = {"TP": "steelblue", "FN": "tomato", "FP": "darkorange"}


# ---------------------------------------------------------------------------
# Low-level drawing
# ---------------------------------------------------------------------------

def time_axis(sfreq: float, window_s: float) -> tuple[np.ndarray, int]:
    half = int(round(window_s * sfreq))
    t_ms = np.linspace(-window_s * 1000, window_s * 1000, 2 * half)
    return t_ms, 2 * half


def _pad_windows(windows: list[np.ndarray], target_len: int) -> np.ndarray | None:
    if not windows:
        return None
    rows = []
    for w in windows:
        if len(w) >= target_len:
            rows.append(w[:target_len])
        else:
            padded = np.zeros(target_len)
            padded[: len(w)] = w
            rows.append(padded)
    return np.stack(rows, axis=0)


def draw_panel(ax, windows, t_ms, colour, label, target_len) -> None:
    ax.axvline(0, color="grey", linestyle="--", linewidth=0.8)
    if not windows:
        ax.set_title(f"{label}  (n=0)", fontsize=9)
        ax.set_xlabel("Time from peak (ms)", fontsize=8)
        return
    mat = _pad_windows(windows, target_len)
    t_plot = t_ms[:target_len]
    for row in mat:
        ax.plot(t_plot, row * 1e6, color=colour, alpha=0.15, linewidth=0.5)
    ax.plot(t_plot, mat.mean(axis=0) * 1e6, color="black", linewidth=2.0, label="mean")
    ax.set_title(f"{label}  (n={len(windows)})", fontsize=9)
    ax.set_xlabel("Time from peak (ms)", fontsize=8)
    ax.set_ylabel("Amplitude (µV)", fontsize=8)
    ax.legend(fontsize=7)
    ax.tick_params(labelsize=7)


def make_overview_figure(tp_records, fp_records, fn_records, sfreq, window_s, title):
    """Standard 3-panel TP / FN / FP butterfly figure."""
    t_ms, target_len = time_axis(sfreq, window_s)
    categories = [
        ("TP", [r["window"] for r in tp_records], CATEGORY_COLORS["TP"]),
        ("FN", [r["window"] for r in fn_records], CATEGORY_COLORS["FN"]),
        ("FP", [r["window"] for r in fp_records], CATEGORY_COLORS["FP"]),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharey=False)
    fig.suptitle(title, fontsize=11)
    for ax, (label, windows, colour) in zip(axes, categories):
        draw_panel(ax, windows, t_ms, colour, label, target_len)
    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def _summary_table(morph_records: list[dict]) -> pd.DataFrame:
    rows = []
    for m in morph_records:
        rows.append({
            "dataset": m["dataset"],
            "group": m["group"],
            "session": m["session"],
            "best_channel": m["best_channel"],
            "TP": m["n_tp"], "FP": m["n_fp"], "FN": m["n_fn"],
        })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["dataset", "group", "session"])


def build_channel_selection_report(
    morph_records: list[dict],
    *,
    window_s: float,
    title: str = "Channel-Selection — Blink-Region Butterfly",
) -> mne.Report:
    """Build an MNE HTML report of TP/FN/FP butterflies per group and subject."""
    report = mne.Report(title=title, verbose=False)

    summary_df = _summary_table(morph_records)
    if not summary_df.empty:
        report.add_html(summary_df.to_html(index=False),
                        title="Event counts (session × group)", section="Overview")

    datasets = sorted({m["dataset"] for m in morph_records})
    for dataset in datasets:
        groups = sorted({m["group"] for m in morph_records if m["dataset"] == dataset})
        for group in groups:
            recs = [m for m in morph_records
                    if m["dataset"] == dataset and m["group"] == group]
            if not recs:
                continue
            sfreq = recs[0]["sfreq"]
            tp_all = [r for m in recs for r in m["tp_records"]]
            fp_all = [r for m in recs for r in m["fp_records"]]
            fn_all = [r for m in recs for r in m["fn_records"]]

            section = f"{dataset} — group: {group}"
            fig = make_overview_figure(
                tp_all, fp_all, fn_all, sfreq, window_s,
                f"All subjects — {dataset} — group '{group}'  |  TP / FN / FP",
            )
            report.add_figure(
                fig, title="All subjects — TP / FN / FP", section=section,
                caption=("Each faint line = one blink-region waveform; thick black "
                         "line = category mean."),
            )
            plt.close(fig)

            for m in sorted(recs, key=lambda x: x["session"]):
                if not (m["tp_records"] or m["fp_records"] or m["fn_records"]):
                    continue
                fig = make_overview_figure(
                    m["tp_records"], m["fp_records"], m["fn_records"],
                    m["sfreq"], window_s,
                    f"{m['session']} — group '{group}'  (ch: {m['best_channel']})",
                )
                report.add_figure(
                    fig, title=f"{m['session']} — TP / FN / FP", section=section,
                    caption=(f"TP={m['n_tp']}  FP={m['n_fp']}  FN={m['n_fn']}  "
                             f"best channel={m['best_channel']}"),
                )
                plt.close(fig)

    return report


__all__ = [
    "CATEGORY_COLORS",
    "time_axis",
    "draw_panel",
    "make_overview_figure",
    "build_channel_selection_report",
]
