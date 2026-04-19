"""Helpers used by blink-position comparison tutorials."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import mne
import numpy as np
import pandas as pd
from mne.io import read_raw_edf

from .blink_detection import DetectionResult


def detect_blinks_from_edf(
    edf_path: Path,
    *,
    sampling_rate_hz: float,
    preferred_channel_names: Sequence[str],
    detector_params: dict[str, float] | None = None,
) -> DetectionResult:
    """Load EDF data, run ``get_blink_position``, and return a detection result."""

    from src.blinker.get_blink_positions import get_blink_position

    if not edf_path.exists():
        raise FileNotFoundError(f"EDF file not found: {edf_path}")

    print(f"[info] using mne version: {mne.__version__}")
    print(f"[info] reading EDF: {edf_path}")

    raw = read_raw_edf(edf_path.as_posix(), preload=True, verbose="ERROR")
    raw.filter(1.0, 30.0, fir_design="firwin", n_jobs=1, verbose="ERROR")
    raw.resample(sampling_rate_hz, n_jobs=1, verbose="ERROR")

    srate = float(raw.info["sfreq"])
    if not np.isclose(srate, sampling_rate_hz, atol=1e-6):
        raise RuntimeError(
            f"Expected {sampling_rate_hz} Hz after resample, got {srate}"
        )

    picks = next(
        ([name] for name in preferred_channel_names if name in raw.ch_names), None
    )
    if picks is None:
        if len(raw.ch_names) < 3:
            raise RuntimeError(
                "Need ≥3 channels to pick the representative EEG channel"
            )
        picks = [raw.ch_names[2]]

    data, _ = raw.get_data(picks=picks, return_times=True)
    python_blink_signal = np.squeeze(data)
    if python_blink_signal.ndim != 1:
        raise RuntimeError("Expected 1-D blink component after squeeze")

    print(f"[info] python_blink_signal samples: {python_blink_signal.shape[0]}")

    params = detector_params or {
        "sfreq": srate,
        "std_threshold": 1.5,
        "min_event_len": 0.05,
    }

    result = get_blink_position(
        params=params,
        blink_component=python_blink_signal,
        ch=picks[0],
        progress_bar=False,
    )

    if not isinstance(result, pd.DataFrame) or list(result.columns) != [
        "start_blink",
        "end_blink",
    ]:
        raise RuntimeError("Unexpected result structure from get_blink_position")

    py_df_1based = result.copy()
    py_df_1based[["start_blink", "end_blink"]] += 1
    py_df_1based = py_df_1based.sort_values(
        "start_blink", kind="mergesort", ignore_index=True
    )

    print("\n[detected] first 5 rows:")
    print(py_df_1based.head())
    print(f"[detected] total detected blinks: {len(py_df_1based)}")

    return DetectionResult(
        events=py_df_1based,
        signal=python_blink_signal,
        channel=picks[0],
        sampling_rate_hz=srate,
        annotation=mne.Annotations([], [], [], orig_time=None),
    )


def load_ground_truth_from_matlab(
    mat_input_path: Path,
    mat_output_path: Path,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Load MATLAB input/output tables for blink positions."""

    if not mat_input_path.exists():
        raise FileNotFoundError(f"MAT input file not found: {mat_input_path}")
    if not mat_output_path.exists():
        raise FileNotFoundError(f"MAT output file not found: {mat_output_path}")

    from test.blinker_migration.obs.debugging_tools import load_matlab_data

    input_data, output_data = load_matlab_data(
        str(mat_input_path), str(mat_output_path)
    )
    blink_positions_mat = output_data["blinkPositions"]
    matlab_blink_signal = input_data["blinkComp"]

    if blink_positions_mat.shape[0] != 2:
        raise RuntimeError("MATLAB blinkPositions should have two rows (start/end)")

    ground_truth_df = pd.DataFrame(
        {
            "start_blink": blink_positions_mat[0, :],
            "end_blink": blink_positions_mat[1, :],
        }
    )
    ground_truth_df = ground_truth_df.sort_values(
        "start_blink", kind="mergesort", ignore_index=True
    )

    return ground_truth_df, matlab_blink_signal
