"""High-level helpers for running PyBlinker detectors in tutorials and tests."""

from __future__ import annotations

from dataclasses import dataclass

import mne
import numpy as np
import pandas as pd


@dataclass(slots=True)
class DetectionResult:
    """Container summarising the PyBlinker detection output."""

    events: pd.DataFrame
    signal: np.ndarray
    channel: str
    sampling_rate_hz: float
    annotation: mne.Annotations


def run_pyblinker_detection(
    raw: mne.io.BaseRaw,
    *,
    sampling_rate_hz: float,
    annot_label: str = "eye_blink",
    filter_low: float = 1.0,
    filter_high: float = 20.0,
) -> DetectionResult:
    """Run :class:`BlinkDetector` on ``raw`` and return a structured result."""

    from src.blinker.pyblinker import BlinkDetector

    from . import similarity

    detector = BlinkDetector(
        raw.copy(),
        visualize=False,
        annot_label=annot_label,
        filter_low=filter_low,
        filter_high=filter_high,
        resample_rate=int(sampling_rate_hz),
        n_jobs=1,
        use_multiprocessing=False,
    )

    annot, channel, n_good, blink_details, _fig_data, _ch_selected = (
        detector.get_blink()
    )

    print(f"[detector] Representative channel: {channel}")
    print(f"[detector] Total good blinks: {n_good}")

    detected_df = blink_details.loc[:, ["start_blink", "end_blink"]].copy()
    detected_df["start_blink"] = detected_df["start_blink"].astype(int) + 1
    detected_df["end_blink"] = detected_df["end_blink"].astype(int)
    detected_df = detected_df.sort_values(
        "start_blink", kind="mergesort", ignore_index=True
    )
    similarity.validate_event_table(detected_df)

    processed_raw = detector.raw_data
    sampling_rate = float(processed_raw.info["sfreq"])
    if not np.isclose(sampling_rate, sampling_rate_hz, atol=1e-6):
        raise RuntimeError(
            f"Expected processed sampling rate {sampling_rate_hz} Hz, got {sampling_rate}"
        )

    signal = processed_raw.get_data(picks=channel)[0]

    return DetectionResult(
        events=detected_df,
        signal=signal,
        channel=channel,
        sampling_rate_hz=sampling_rate,
        annotation=annot,
    )
