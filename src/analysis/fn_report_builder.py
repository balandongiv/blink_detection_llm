"""Reusable MNE Report builder for false-negative case analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import mne

from src.analysis.case_figure_builder import build_case_figure
from src.analysis.false_negative_analysis import nearest_row


def _fmt(value: object) -> str:
    """Format a potentially-NaN float to 3 decimal places, else return 'nan'."""
    try:
        v = float(value)  # type: ignore[arg-type]
        return f"{v:.3f}" if v == v else "nan"
    except (TypeError, ValueError):
        return "nan"


def build_false_negative_report(
    *,
    title: str,
    summary_items: dict[str, str],
    lane_summary: pd.DataFrame,
    false_negatives: pd.DataFrame,
    predicted: pd.DataFrame,
    signal_by_epoch: dict[int, np.ndarray],
    sfreq: float,
    tags: tuple[str, ...] = (),
    pad_s: float = 0.75,
) -> mne.Report:
    """Build an MNE Report visualising false-negative blink cases.

    Parameters
    ----------
    title:
        Report title string.
    summary_items:
        Ordered dict of label → value pairs rendered as an HTML ``<ul>`` in the
        Overview section.
    lane_summary:
        Per-channel scoring DataFrame (top 5 rows shown in Overview).
    false_negatives:
        False-negative DataFrame as returned by
        :func:`~pyblinker.analysis.false_negative_analysis.collect_false_negatives`.
    predicted:
        Enriched predicted blink DataFrame for the representative channel.
    signal_by_epoch:
        Dict mapping epoch_index → 1-D filtered signal array for the representative channel.
    sfreq:
        Sampling frequency in Hz.
    tags:
        Extra MNE report tags attached to every figure section entry.
    pad_s:
        Signal padding passed to :func:`~pyblinker.analysis.case_figure_builder.build_case_figure`.

    Returns
    -------
    mne.Report
        Populated report object.  Call ``.save(path, overwrite=True)`` on the result.
    """
    report = mne.Report(title=title, verbose=False)

    items_html = "\n".join(
        f"      <li><b>{label}</b>: {value}</li>"
        for label, value in summary_items.items()
    )
    summary_html = f"<h3>{title}</h3>\n    <ul>\n{items_html}\n    </ul>"
    report.add_html(summary_html, title="Summary", section="Overview")
    report.add_html(lane_summary.head(5).to_html(index=False), title="Top Lanes", section="Overview")
    if not false_negatives.empty:
        report.add_html(
            false_negatives.to_html(index=False),
            title="False Negative Table",
            section="Overview",
        )

    for idx, fn_row in enumerate(false_negatives.itertuples(index=False), start=1):
        fn_series = pd.Series(fn_row._asdict())
        pred_row = nearest_row(
            predicted,
            int(fn_series["epoch_index"]),
            float(fn_series["blink_onset"]),
            float(fn_series["blink_duration"]),
        )
        epoch_index = int(fn_series["epoch_index"])
        abs_onset = float(fn_series["absolute_onset_s"])

        if epoch_index not in signal_by_epoch:
            metadata_html = (
                "<ul>"
                f"<li><b>Reference</b>: onset={_fmt(fn_series['blink_onset'])}s,"
                f" duration={_fmt(fn_series['blink_duration'])}s,"
                f" absolute={_fmt(fn_series['absolute_onset_s'])}s-{_fmt(fn_series['absolute_offset_s'])}s</li>"
                f"<li><b>Nearest prediction</b>: onset={_fmt(fn_series['nearest_pred_onset_s']) if pd.notna(fn_series['nearest_pred_onset_s']) else 'nan'}s,"
                f" duration={_fmt(fn_series['nearest_pred_duration_s']) if pd.notna(fn_series['nearest_pred_duration_s']) else 'nan'}s</li>"
                f"<li><b>Nearest overlap ratio</b>: {_fmt(fn_series['nearest_overlap_ratio']) if pd.notna(fn_series['nearest_overlap_ratio']) else 'nan'}</li>"
                f"<li><b>Nearest onset diff</b>: {_fmt(fn_series['nearest_onset_diff_s']) if pd.notna(fn_series['nearest_onset_diff_s']) else 'nan'}s</li>"
                f"<li><b>Note</b>: epoch index {epoch_index} is outside the prepared epoch range.</li>"
                "</ul>"
            )
            report.add_html(
                metadata_html,
                title=f"FN {idx:02d} | abs {abs_onset:.3f}s | epoch {epoch_index} | metadata only",
                section="False Negatives",
            )
            continue

        signal = signal_by_epoch[epoch_index]
        fig = build_case_figure(signal, sfreq, fn_series, pred_row, pad_s=pad_s)
        caption = (
            "<ul>"
            f"<li><b>Reference</b>: onset={_fmt(fn_series['blink_onset'])}s,"
            f" duration={_fmt(fn_series['blink_duration'])}s,"
            f" absolute={_fmt(fn_series['absolute_onset_s'])}s-{_fmt(fn_series['absolute_offset_s'])}s</li>"
            f"<li><b>Nearest prediction</b>: onset={_fmt(fn_series['nearest_pred_onset_s']) if pd.notna(fn_series['nearest_pred_onset_s']) else 'nan'}s,"
            f" duration={_fmt(fn_series['nearest_pred_duration_s']) if pd.notna(fn_series['nearest_pred_duration_s']) else 'nan'}s</li>"
            f"<li><b>Nearest prediction absolute onset</b>: {_fmt(fn_series['nearest_pred_absolute_onset_s']) if pd.notna(fn_series['nearest_pred_absolute_onset_s']) else 'nan'}s</li>"
            f"<li><b>Nearest overlap ratio</b>: {_fmt(fn_series['nearest_overlap_ratio']) if pd.notna(fn_series['nearest_overlap_ratio']) else 'nan'}</li>"
            f"<li><b>Nearest onset diff</b>: {_fmt(fn_series['nearest_onset_diff_s']) if pd.notna(fn_series['nearest_onset_diff_s']) else 'nan'}s</li>"
            "</ul>"
        )
        report.add_figure(
            fig,
            title=f"FN {idx:02d} | abs {abs_onset:.3f}s | epoch {epoch_index}",
            caption=caption,
            section="False Negatives",
            tags=tags,
        )
        plt.close(fig)

    return report


__all__ = ["build_false_negative_report"]
