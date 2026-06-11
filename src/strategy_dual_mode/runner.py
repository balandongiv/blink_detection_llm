"""Dual-mode epoch blink detector runner.

For each channel in a session:
  1. Concatenate valid (health ≥ MIN_HEALTH) epochs into one signal.
  2. Module A — full pyblinker 6-step pipeline → normal blink detections.
  3. Module B — sustained-suppression detector → long closure detections.
  4. Merge: long events have priority; Module A detections that overlap > 50 %
     with a Module B event are removed (onset blink subsumed by long closure).
  5. Map results back to epoch-relative timing via
     ``map_concatenated_blinks_to_epochs``.

Returns the standard ``list[dict]`` format consumed by ``evaluate_channels``:
  {channel, df_positions, mapped_candidates, signal_by_epoch}
"""

from __future__ import annotations

import logging

import mne
import numpy as np
import pandas as pd
from tqdm import tqdm

from src.common.epoch_channel import map_concatenated_blinks_to_epochs
from src.common.epoch_input import PreparedEpochDetectionInput
from src.common.pipeline_utils import build_epoch_boundaries, build_signal_by_epoch
from src.strategy_dual_mode.long_closure import detect_long_closures

from pyblinker.blinker.default_setting import build_blink_params
from pyblinker.pipeline_steps import process_channel_data as _pyblinker_process_channel_data

logger = logging.getLogger(__name__)

LONG_THRESHOLD_S: float = 0.5


# ---------------------------------------------------------------------------
# Module A helpers
# ---------------------------------------------------------------------------

class _MinimalDetector:
    """Minimal pyblinker.pipeline_steps interface for a single-channel RawArray."""

    def __init__(self, raw_array: mne.io.RawArray, sfreq: float) -> None:
        self.raw_data = raw_array
        self.params = build_blink_params({"sfreq": sfreq})
        self.all_data_info: list[dict] = []
        self.all_data: list[dict] = []

    @staticmethod
    def filter_point(ch: str, all_data_info: list[dict]) -> dict:
        return next(d for d in all_data_info if d["ch"] == ch)

    def filter_bad_blink(self, df: pd.DataFrame) -> pd.DataFrame:
        return df


def _run_module_a(
    concat_signal: np.ndarray,
    ch_name: str,
    sfreq: float,
) -> pd.DataFrame:
    """Run full pyblinker 6-step pipeline; return all detected events.

    Pyblinker's quality filters already tend to reject events > 500 ms, so the
    output is predominantly normal blinks.  The caller (``_merge_results``)
    removes any overlap with Module B long-closure events.
    """
    _empty = pd.DataFrame(columns=["start_blink", "end_blink"])
    info = mne.create_info(ch_names=[ch_name], sfreq=sfreq,
                           ch_types=["eeg"], verbose=False)
    raw_array = mne.io.RawArray(concat_signal[np.newaxis, :], info, verbose=False)
    detector = _MinimalDetector(raw_array, sfreq)
    try:
        _pyblinker_process_channel_data(detector, ch_name, verbose=False)
    except Exception as exc:
        logger.debug("Module A ch=%s: %s", ch_name, exc)
        return _empty

    if not detector.all_data_info or detector.all_data_info[0]["df"].empty:
        return _empty

    df = detector.all_data_info[0]["df"].copy()
    return df[["start_blink", "end_blink"]].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Event merger
# ---------------------------------------------------------------------------

def _merge_results(
    module_a: pd.DataFrame,
    module_b: pd.DataFrame,
) -> pd.DataFrame:
    """Combine Module A and Module B events additively.

    Module A (pyblinker normal blinks) is kept entirely intact — removing any
    Module A events caused false-negative regressions for normal blinks near
    long closures.  Module B (long closures) is appended without deduplication
    because the two modules target different duration ranges and the evaluation
    framework's temporal matching handles any overlap cleanly.
    """
    frames = []
    if not module_a.empty:
        frames.append(module_a[["start_blink", "end_blink"]])
    if not module_b.empty:
        frames.append(module_b[["start_blink", "end_blink"]])
    if not frames:
        return pd.DataFrame(columns=["start_blink", "end_blink"])

    merged = pd.concat(frames, ignore_index=True)
    merged = merged.drop_duplicates(subset=["start_blink", "end_blink"])
    return merged.sort_values("start_blink").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_dual_mode_epoch_pipeline(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
    *,
    # Module B parameters
    rms_window_ms: float = 50.0,
    baseline_window_s: float = 5.0,
    alpha: float = 0.3,
    debounce_ms: float = 150.0,
    suppress_min_s: float = 0.10,
    pad_s: float = 0.20,
    min_long_duration_s: float = 0.5,
    max_long_duration_s: float = 15.0,
) -> list[dict]:
    """Run the dual-mode pipeline on all channels.

    Parameters
    ----------
    prepared:
        Preprocessed, bandpass-filtered epoch data from
        ``prepare_epoch_detection_input``.
    valid_epoch_indices:
        Epoch indices that passed the epoch-health filter.
    rms_window_ms:
        Module B: sliding RMS window in ms.
    baseline_window_s:
        Module B: rolling mean baseline window in seconds.
    alpha:
        Module B: suppression ratio — flag when RMS < alpha × baseline.
    debounce_ms:
        Module B: gap-filling debounce in ms.
    suppress_min_s:
        Module B: minimum suppression period to trigger a candidate (seconds).
    pad_s:
        Module B: onset/offset padding in seconds.
    min_long_duration_s:
        Module B: minimum long-closure duration (PERCLOS standard: 0.5 s).
    max_long_duration_s:
        Module B: maximum long-closure duration (default 15 s).

    Returns
    -------
    list[dict]
        One dict per channel:
          ``channel``, ``df_positions``, ``mapped_candidates``, ``signal_by_epoch``.
        Compatible with ``evaluate_channels``.
    """
    sfreq = float(prepared.sfreq)
    n_valid = len(valid_epoch_indices)
    epoch_length_samples = prepared.epoch_length_samples
    epoch_boundaries = build_epoch_boundaries(n_valid, epoch_length_samples)

    logger.info(
        "Dual-mode pipeline: %d ch, %d epochs [sfreq=%.1f Hz, concat=%.1f s]",
        len(prepared.channel_names), n_valid, sfreq,
        n_valid * epoch_length_samples / sfreq,
    )

    _empty_mapped = pd.DataFrame(
        columns=["epoch_index", "channel", "blink_onset",
                 "blink_duration", "start_blink", "end_blink"]
    )
    results: list[dict] = []

    for ch_idx, ch_name in enumerate(
        tqdm(prepared.channel_names, desc="Dual-mode", unit="ch")
    ):
        concat_signal = (
            prepared.data[valid_epoch_indices, ch_idx, :]
            .reshape(-1)
            .astype(np.float64)
        )

        # Module A: pyblinker 6-step pipeline
        df_a = _run_module_a(concat_signal, ch_name, sfreq)
        logger.debug("ch=%s  Module A: %d events", ch_name, len(df_a))

        # Module B: sustained-suppression long-closure detector
        df_b = detect_long_closures(
            concat_signal,
            sfreq,
            rms_window_ms=rms_window_ms,
            baseline_window_s=baseline_window_s,
            alpha=alpha,
            debounce_ms=debounce_ms,
            suppress_min_s=suppress_min_s,
            pad_s=pad_s,
            min_duration_s=min_long_duration_s,
            max_duration_s=max_long_duration_s,
        )
        logger.debug("ch=%s  Module B: %d long-closure events", ch_name, len(df_b))

        # Merge
        merged = _merge_results(df_a, df_b)

        signal_by_epoch = build_signal_by_epoch(prepared, ch_idx)

        if merged.empty:
            results.append({
                "channel": ch_name,
                "df_positions": pd.DataFrame(),
                "mapped_candidates": _empty_mapped.copy(),
                "signal_by_epoch": signal_by_epoch,
            })
            continue

        mapped_candidates = map_concatenated_blinks_to_epochs(
            merged,
            channel=ch_name,
            valid_epoch_indices=valid_epoch_indices,
            epoch_boundaries=epoch_boundaries,
            sfreq=sfreq,
        )

        results.append({
            "channel": ch_name,
            "df_positions": merged.copy(),
            "mapped_candidates": mapped_candidates,
            "signal_by_epoch": signal_by_epoch,
        })

    return results


__all__ = ["run_dual_mode_epoch_pipeline", "LONG_THRESHOLD_S"]
