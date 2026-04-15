"""
Blink-fit reporting utilities.

Creates an interactive HTML report (mne.Report) where each blink is plotted
individually with landmark annotations and a dedicated legend panel.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import mne
import numpy as np
import pandas as pd


# -----------------------------------------------------------------------------
# Constants: landmark mapping + excluded columns
# -----------------------------------------------------------------------------
LANDMARKS_ORDER = [
    "max_blink",
    "max_value",
    "left_zero",
    "right_zero",
    "left_base",
    "right_base",
    "left_base_half_height",
    "right_base_half_height",
    "left_zero_half_height",
    "right_zero_half_height",
    "left_range",
    "right_range",
    "left_slope",
    "right_slope",
    "aver_left_velocity",
    "aver_right_velocity",
    "leftR2",
    "rightR2",
    "x_intersect",
    "y_intersect",
    "left_x_intercept",
    "right_x_intercept",
]

EXCLUDED_COLUMNS = {"outer_start", "outer_end"}


# -----------------------------------------------------------------------------
# Small helpers
# -----------------------------------------------------------------------------
def _as_int_or_none(x: Any) -> int | None:
    """Convert a value to int safely; return None if not finite."""
    if x is None:
        return None
    try:
        xf = float(x)
    except Exception:
        return None
    if not np.isfinite(xf):
        return None
    return int(round(xf))


def _as_float_or_none(x: Any) -> float | None:
    """Convert a value to float safely; return None if not finite."""
    if x is None:
        return None
    try:
        xf = float(x)
    except Exception:
        return None
    if not np.isfinite(xf):
        return None
    return xf


def _as_list(x: Any) -> list[int]:
    """Convert list-like blink range cell into a clean list of ints."""
    if x is None:
        return []
    if isinstance(x, float) and np.isnan(x):
        return []
    if isinstance(x, (list, tuple, np.ndarray)):
        out = []
        for v in x:
            iv = _as_int_or_none(v)
            if iv is not None:
                out.append(iv)
        return out
    iv = _as_int_or_none(x)
    return [] if iv is None else [iv]


def _sample_value(signal: np.ndarray, idx: int | None) -> float | None:
    """Return signal[idx] safely."""
    if idx is None:
        return None
    if idx < 0 or idx >= len(signal):
        return None
    y = float(signal[idx])
    return y if np.isfinite(y) else None


def _blink_window_from_row(row: pd.Series, *, n_samples: int) -> tuple[int, int]:
    """
    Determine plot window [start, end] for a blink.

    Requirement: pad +10 samples AFTER the last point of the selected blink region.

    NOTE:
    - Your authoritative window selection rule is in test_b_fitblink.py.
    - This default uses the earliest plausible left landmark and latest plausible right landmark.
      If test_b_fitblink.py uses a different “choose-left-candidate” rule, replace this helper
      with that exact logic.
    """
    left_candidates = []

    # left candidates (prefer earliest)
    for key in ("left_base", "left_zero", "max_blink"):
        if key in row:
            v = _as_int_or_none(row[key])
            if v is not None:
                left_candidates.append(v)

    left_range = _as_list(row.get("left_range"))
    if left_range:
        left_candidates.append(min(left_range))

    # right candidates (prefer latest)
    right_candidates = []
    for key in ("right_base", "right_zero", "max_blink"):
        if key in row:
            v = _as_int_or_none(row[key])
            if v is not None:
                right_candidates.append(v)

    right_range = _as_list(row.get("right_range"))
    if right_range:
        right_candidates.append(max(right_range))

    if not left_candidates:
        start = 0
    else:
        start = max(0, min(left_candidates) - 10)

    if not right_candidates:
        end = min(n_samples - 1, start + 50)
    else:
        end = min(n_samples - 1, max(right_candidates) + 10)  # ✅ required +10 padding

    if end < start:
        end = start

    return start, end


def _build_caption(row: pd.Series, *, signal: np.ndarray) -> str:
    """
    Build a caption that spells out EVERY required landmark and its value(s).
    """
    lines = []
    lines.append("Landmarks (index and/or value):")

    # index-like landmarks (we show index + amplitude when possible)
    index_landmarks = {
        "max_blink",
        "left_zero",
        "right_zero",
        "left_base",
        "right_base",
        "left_base_half_height",
        "right_base_half_height",
        "left_zero_half_height",
        "right_zero_half_height",
        "left_x_intercept",
        "right_x_intercept",
    }

    # fields that are numeric but not necessarily indices
    numeric_fields = {
        "max_value",
        "left_slope",
        "right_slope",
        "aver_left_velocity",
        "aver_right_velocity",
        "leftR2",
        "rightR2",
        "x_intersect",
        "y_intersect",
    }

    # ranges
    range_fields = {"left_range", "right_range"}

    for key in LANDMARKS_ORDER:
        if key in EXCLUDED_COLUMNS:
            continue

        if key in range_fields:
            r = _as_list(row.get(key))
            if r:
                lines.append(f"- {key}: {r} (min={min(r)}, max={max(r)})")
            else:
                lines.append(f"- {key}: []")
            continue

        if key in index_landmarks:
            idx = _as_int_or_none(row.get(key))
            amp = _sample_value(signal, idx) if idx is not None else None
            if idx is None:
                lines.append(f"- {key}: None")
            else:
                if amp is None:
                    lines.append(f"- {key}: {idx} (amp=N/A)")
                else:
                    lines.append(f"- {key}: {idx} (amp={amp:.6f})")
            continue

        if key in numeric_fields:
            val = row.get(key)
            fv = _as_float_or_none(val)
            if fv is None:
                lines.append(f"- {key}: None")
            else:
                lines.append(f"- {key}: {fv:.6f}")
            continue

        # fallback
        lines.append(f"- {key}: {row.get(key)}")

    return "\n".join(lines)


# -----------------------------------------------------------------------------
# Main: make_report()
# -----------------------------------------------------------------------------
def make_report(
    df: pd.DataFrame,
    report_name: str,
    *,
    candidate_signal: np.ndarray,
    sfreq: float = 100.0,
    report_title: str | None = None,
    output_dir: Path | None = Path("tutorial_outputs"),
    max_plots: int | None = None,
) -> mne.Report:
    """
    Create an interactive MNE report that plots each blink individually with landmarks.

    Parameters
    ----------
    df : pd.DataFrame
            Blink landmark outputs (either MATLAB output or Python-derived output).
            Must contain columns listed in LANDMARKS_ORDER (some may be missing, but required ones should exist).
            Must NOT display outer_start/outer_end (excluded even if present).
    report_name : str
            File-stem / identifier e.g. "plot_matlab_base" or "plot_python_base".
    candidate_signal : np.ndarray
            1D blink channel time series (same indexing used by landmark frames).
    sfreq : float
            Sampling frequency (Hz). Included for completeness and future time-based labeling.
    report_title : str | None
            Title shown inside the HTML report.
    output_dir : Path | None
            If provided, saves report as output_dir / f"{report_name}.html".
    max_plots : int | None
            Optional cap on number of blinks to plot.

    Returns
    -------
    mne.Report
            The created report (also saved if output_dir is provided).
    """
    if candidate_signal is None or len(candidate_signal) == 0:
        raise ValueError("candidate_signal is required for plotting blink waveforms.")

    # Sanitize DF: drop excluded columns from any display logic
    df = df.copy()
    for col in EXCLUDED_COLUMNS:
        if col in df.columns:
            df.drop(columns=[col], inplace=True)

    title = report_title if report_title else report_name
    report = mne.Report(title=title)

    rows = list(df.iterrows())
    if max_plots is not None:
        rows = rows[: int(max_plots)]

    for i, (_, row) in enumerate(rows):
        row = row if isinstance(row, pd.Series) else pd.Series(row)
        n_samples = len(candidate_signal)

        # Determine window + required +10 right padding
        start, end = _blink_window_from_row(row, n_samples=n_samples)

        x = np.arange(start, end + 1)
        y = candidate_signal[start : end + 1]

        # --- create the two-column figure layout (plot + legend panel) ---
        fig, (ax, legend_ax) = plt.subplots(
            1,
            2,
            figsize=(11, 3.5),
            gridspec_kw={"width_ratios": [5, 1]},
        )
        legend_ax.axis("off")

        # waveform: faint continuous line behind a scatter plot
        ax.plot(x, y, lw=1.0, alpha=0.3, label="_nolegend_")
        ax.scatter(
            x,
            y,
            s=50,
            alpha=0.8,
            label="blink waveform",
            zorder=3,
        )

        # styles for landmark markers
        marker_style = {
            "max_blink": dict(marker="o", s=55),
            "left_zero": dict(marker="^", s=55),
            "right_zero": dict(marker="v", s=55),
            "left_base": dict(marker="s", s=55),
            "right_base": dict(marker="s", s=55),
            "left_base_half_height": dict(marker="D", s=55),
            "right_base_half_height": dict(marker="D", s=55),
            "left_zero_half_height": dict(marker="P", s=55),
            "right_zero_half_height": dict(marker="P", s=55),
            "left_x_intercept": dict(marker="X", s=55),
            "right_x_intercept": dict(marker="X", s=55),
        }

        # plot index-based landmarks as points on the waveform
        for key, style in marker_style.items():
            idx = _as_int_or_none(row.get(key))
            if idx is None:
                continue
            if idx < start or idx > end:
                continue
            yv = _sample_value(candidate_signal, idx)
            if yv is None:
                continue
            ax.scatter([idx], [yv], zorder=5, label=key, **style)

        # x_intersect might be a float sample index
        x_intersect = _as_float_or_none(row.get("x_intersect"))
        y_intersect = _as_float_or_none(row.get("y_intersect"))
        if x_intersect is not None and start <= x_intersect <= end:
            ax.axvline(
                x_intersect,
                linestyle="--",
                lw=1.0,
                alpha=0.8,
                label="x_intersect",
            )
        if y_intersect is not None:
            ax.axhline(
                y_intersect,
                linestyle=":",
                lw=1.0,
                alpha=0.7,
                label="y_intersect",
            )

        # left_range / right_range as highlighted spans
        left_range = _as_list(row.get("left_range"))
        right_range = _as_list(row.get("right_range"))
        if left_range:
            lo, hi = min(left_range), max(left_range)
            lo = max(lo, start)
            hi = min(hi, end)
            if lo <= hi:
                ax.axvspan(lo, hi, alpha=0.12, label="left_range")
        if right_range:
            lo, hi = min(right_range), max(right_range)
            lo = max(lo, start)
            hi = min(hi, end)
            if lo <= hi:
                ax.axvspan(lo, hi, alpha=0.12, label="right_range")

        # axes formatting
        ax.set_title(f"Blink {i} • window [{start}, {end}] (right padded +10)")
        ax.set_xlabel("Sample index (frame)")
        ax.set_ylabel("Amplitude")
        ax.grid(alpha=0.25)

        # legend in the right panel (not overlaid)
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            # de-duplicate labels
            seen = set()
            uniq_h, uniq_l = [], []
            for handle, label in zip(handles, labels):
                if label in seen:
                    continue
                seen.add(label)
                uniq_h.append(handle)
                uniq_l.append(label)

            legend_ax.legend(
                uniq_h,
                uniq_l,
                loc="upper left",
                fontsize=8,
                frameon=True,
                borderpad=0.6,
                labelspacing=0.3,
            )

        caption = _build_caption(row, signal=candidate_signal)

        report.add_figure(
            fig=fig,
            title=f"Blink {i}",
            caption=caption,
            section=title,
            tags=("blink", report_name),
        )
        plt.close(fig)

    # Save HTML report
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        html_path = output_dir / f"{report_name}.html"
        report.save(html_path, overwrite=True, open_browser=False)

    return report
