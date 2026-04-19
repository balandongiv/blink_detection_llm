"""Reusable visualization helper for false-negative case figures."""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def build_case_figure(
    signal: np.ndarray,
    sfreq: float,
    fn_row: pd.Series,
    pred_row: pd.Series | None,
    *,
    pad_s: float = 0.75,
) -> plt.Figure:
    """Build a figure comparing a false-negative ground_truth against its nearest prediction.

    Draws the filtered signal in a time window centered on the ground_truth blink,
    with red shading for the ground_truth interval and blue shading for the nearest
    prediction (when provided).

    Parameters
    ----------
    signal:
        1-D filtered signal array for the epoch.
    sfreq:
        Sampling frequency in Hz.
    fn_row:
        A single row from a false-negative DataFrame.  Must contain
        ``blink_onset``, ``blink_duration``, ``absolute_onset_s``, and
        ``epoch_index``.
    pred_row:
        Nearest predicted blink row, or None.  Must contain ``blink_onset``
        and ``blink_duration`` when provided.
    pad_s:
        Padding in seconds added around the ground_truth window. Default 0.75.
    """
    ref_onset = float(fn_row["blink_onset"])
    ref_end = ref_onset + float(fn_row["blink_duration"])
    start_s = max(0.0, ref_onset - pad_s)
    end_s = min(len(signal) / sfreq, ref_end + pad_s)
    if pred_row is not None:
        pred_onset = float(pred_row["blink_onset"])
        pred_end = pred_onset + float(pred_row["blink_duration"])
        start_s = min(start_s, max(0.0, pred_onset - pad_s / 2.0))
        end_s = max(end_s, min(len(signal) / sfreq, pred_end + pad_s / 2.0))

    start_idx = max(0, int(np.floor(start_s * sfreq)))
    end_idx = min(len(signal) - 1, int(np.ceil(end_s * sfreq)))
    t = np.arange(start_idx, end_idx + 1) / sfreq
    y = signal[start_idx : end_idx + 1]

    fig, ax = plt.subplots(figsize=(11, 3.8))
    ax.plot(t, y, color="black", linewidth=1.0)
    ax.axvspan(ref_onset, ref_end, color="#d62728", alpha=0.18, label="Reference FN")
    ax.axvline(ref_onset, color="#d62728", linestyle="--", linewidth=1.0)
    ax.axvline(ref_end, color="#d62728", linestyle="--", linewidth=1.0)
    if pred_row is not None:
        pred_onset = float(pred_row["blink_onset"])
        pred_end = pred_onset + float(pred_row["blink_duration"])
        ax.axvspan(pred_onset, pred_end, color="#1f77b4", alpha=0.16, label="Nearest prediction")
        ax.axvline(pred_onset, color="#1f77b4", linestyle=":", linewidth=1.0)
        ax.axvline(pred_end, color="#1f77b4", linestyle=":", linewidth=1.0)
    ax.set_title(
        f"FN | abs {float(fn_row['absolute_onset_s']):.3f}s | epoch {int(fn_row['epoch_index'])}"
    )
    ax.set_xlabel("Time within epoch (s)")
    ax.set_ylabel("Filtered amplitude")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    return fig


__all__ = ["build_case_figure"]
