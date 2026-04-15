"""14_strategy_d_ncyoder_first_5_epochs_bayesian_optimization_step1.py

Strategy D Step 1: MNE ``peak_finder`` (Nathanael C. Yoder / ncyoder@purdue.edu)
applied directly to the concatenated epoch signal with a per-channel threshold
learned by autoreject Bayesian optimisation.

Derivation from Strategy B
---------------------------
Strategy B calls ``mne.preprocessing.find_eog_events``, which wraps
``peak_finder`` internally but adds its own Raw-object overhead, its own
band-pass filter pass, automatic channel selection (max RMS energy), and
falls back to the default ``thresh = (max - min) / 4``.

Strategy D removes that wrapper and calls ``peak_finder`` directly:

* x0    = valid epochs concatenated into one long 1D signal per channel
           (the same concatenation used in Strategy B's MNE Raw wrapper).
* thresh = per-channel PTP rejection threshold from
           ``autoreject.compute_thresholds(method='bayesian_optimization')``,
           optionally scaled down by ``STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE``
           before being passed to ``peak_finder`` (same rescale logic as
           Strategy C's ``rescale_threshold`` / ``_get_stage1_scan_threshold_scale``).
* Extrema direction is chosen per channel exactly as ``_find_eog_events`` does:
  if ``|max(x0 - mean)| >= |min(x0 - mean)|`` → look for positive peaks,
  otherwise look for negative peaks.
* Peak → epoch mapping follows the offset arithmetic in ``_find_eog_events``:
      epoch_index  = peak_sample // epoch_length_samples
      local_onset  = (peak_sample %  epoch_length_samples) / sfreq

Rescale flag (``--disable-threshold-rescale``)
-----------------------------------------------
By default (rescale enabled) the raw autoreject PTP rejection threshold is
multiplied by ``STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE`` (0.12) to produce the
scan threshold supplied to ``peak_finder``.  This mirrors
``EpochDetectionStrategyCAutoreject._get_stage1_scan_threshold_scale()`` and
``rescale_threshold()``.

Pass ``--disable-threshold-rescale`` to use the raw autoreject threshold
directly (scale = 1.0), matching Strategy C's ``--disable-threshold-rescale``
option.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys
from time import perf_counter

import mne
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_VENDORED_AUTOREJECT = REPO_ROOT / "autoreject"
if str(_VENDORED_AUTOREJECT) not in sys.path:
    sys.path.insert(0, str(_VENDORED_AUTOREJECT))

from autoreject import compute_thresholds  # noqa: E402
from mne.preprocessing import peak_finder  # noqa: E402

from pyblinker.epoch_detection_strategy_a.bad_epoch_utils import get_valid_epoch_indices
from pyblinker.epoch_detection_strategy_a.epoch_blink_pipeline import (
    prepare_epoch_detection_input,
)
from pyblinker.epoch_detection_strategy_a.epoch_validation import (
    load_reference_blink_table,
    match_blink_tables,
)
from pyblinker.epoch_detection_strategy_c import STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE


DATA_PATH = REPO_ROOT / "sample_data" / "dev_epo.fif"
REFERENCE_PATH = REPO_ROOT / "sample_data" / "dev_epo_annotations_5_epochs.csv"
CHANNELS = ["EEG X1 - Pz", "EEG Fp1 - Pz", "EEG Fp2 - Pz"]

FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None
HALF_WINDOW_S = 0.10
AUTOREJECT_METHOD = "bayesian_optimization"
AUTOREJECT_RANDOM_STATE = 42


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run Strategy D Step 1 on the first 5 epochs using peak_finder "
            "with a Bayesian-optimisation threshold from autoreject."
        ),
        epilog=(
            "Example: python tutorial/14_strategy_d_ncyoder_first_5_epochs_"
            "bayesian_optimization_step1.py --disable-threshold-rescale"
        ),
    )
    parser.add_argument(
        "--disable-threshold-rescale",
        action="store_true",
        help=(
            "Use the raw autoreject PTP threshold directly as the peak_finder "
            "thresh (scale = 1.0).  By default the threshold is multiplied by "
            f"STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE ({STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE}) "
            "before being passed to peak_finder."
        ),
    )
    parser.add_argument(
        "--show-candidates",
        action="store_true",
        help="Print the full candidate table for the best channel.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Python logging level.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def configure_logging(log_level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(levelname)s: %(name)s: %(message)s",
        force=True,
    )


def load_first_5_epochs() -> mne.Epochs:
    epochs = mne.read_epochs(str(DATA_PATH), preload=True, verbose="ERROR")
    epochs = epochs.copy().pick(CHANNELS)
    return epochs[:5].copy()


def get_scan_threshold_scale(rescale_threshold: bool) -> float:
    """Translate the rescale flag into a numeric scale factor.

    Mirrors ``EpochDetectionStrategyCAutoreject._get_stage1_scan_threshold_scale()``:
    * rescale enabled  → ``STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE`` (0.12)
    * rescale disabled → 1.0  (use raw autoreject threshold directly)
    """
    if not rescale_threshold:
        return 1.0
    return STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE


def learn_bayesian_thresholds(
    prepared_data: np.ndarray,
    channel_names: tuple[str, ...],
    sfreq: float,
    valid_epoch_indices: list[int],
) -> dict[str, float]:
    """Learn per-channel PTP rejection thresholds with Bayesian optimisation.

    Replicates the ``per_channel`` branch of Strategy C's
    ``get_channel_rejection_threshold``.

    Returns
    -------
    raw_thresholds
        PTP rejection thresholds as learned by autoreject (in Volts).
        Apply ``get_scan_threshold_scale`` separately to obtain the
        ``peak_finder`` scan threshold.
    """
    valid_indices = np.asarray(valid_epoch_indices, dtype=int)
    stage1_data = prepared_data[valid_indices]  # (n_valid, n_channels, n_samples)
    info = mne.create_info(
        list(channel_names),
        sfreq=float(sfreq),
        ch_types=["eeg"] * len(channel_names),
    )
    stage1_epochs = mne.EpochsArray(stage1_data, info, verbose="ERROR")
    threshes = compute_thresholds(
        stage1_epochs,
        method=AUTOREJECT_METHOD,
        random_state=AUTOREJECT_RANDOM_STATE,
        augment=False,
        verbose=False,
    )
    return {ch: float(threshes[ch]) for ch in channel_names}


def peaks_to_candidates(
    peak_locs: np.ndarray,
    *,
    epoch_length_samples: int,
    sfreq: float,
    valid_epoch_indices: list[int],
    channel: str,
    half_window_s: float = 0.10,
) -> pd.DataFrame:
    """Map sample positions in the concatenated signal back to epoch-local rows.

    Mirrors the offset arithmetic inside MNE's ``_find_eog_events``:
        epoch_index = peak_sample // epoch_length_samples
        local_onset = (peak_sample % epoch_length_samples) / sfreq
    Each peak is expanded into a symmetric half-window region, clipped to the
    epoch boundary, to produce ``blink_onset`` and ``blink_duration``.
    """
    columns = ["epoch_index", "channel", "blink_onset", "blink_duration", "peak_sample"]
    if len(peak_locs) == 0:
        return pd.DataFrame(columns=columns)

    half_win = max(1, int(round(half_window_s * sfreq)))
    rows: list[dict] = []
    for peak in peak_locs:
        offset = int(peak) // epoch_length_samples
        if offset < 0 or offset >= len(valid_epoch_indices):
            continue
        epoch_index = int(valid_epoch_indices[offset])
        local_peak = int(peak) % epoch_length_samples
        start = max(0, local_peak - half_win)
        end = min(epoch_length_samples - 1, local_peak + half_win)
        rows.append(
            {
                "epoch_index": epoch_index,
                "channel": channel,
                "blink_onset": start / float(sfreq),
                "blink_duration": (end - start) / float(sfreq),
                "peak_sample": local_peak,
            }
        )
    if not rows:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(rows)
    return df.sort_values(["epoch_index", "blink_onset"]).reset_index(drop=True)


def print_frame(title: str, frame: pd.DataFrame, columns: list[str] | None = None) -> None:
    print(f"\n=== {title} ===")
    if frame.empty:
        print("<empty>")
        return
    if columns is not None:
        existing = [c for c in columns if c in frame.columns]
        frame = frame.loc[:, existing]
    print(frame.to_string(index=False))


def build_summary(
    channel_results: list[dict],
    *,
    reference: pd.DataFrame,
    n_epochs: int,
) -> pd.DataFrame:
    rows: list[dict] = []
    for result in channel_results:
        metrics = match_blink_tables(
            result["candidates"],
            reference,
            n_epochs=n_epochs,
        )
        rows.append(
            {
                "channel": result["channel"],
                "raw_threshold": result["raw_threshold"],
                "scan_threshold": result["scan_threshold"],
                "extrema": result["extrema"],
                "peak_count": result["peak_count"],
                "candidate_count": int(len(result["candidates"])),
                "tp": int(metrics.true_positives),
                "fp": int(metrics.false_positives),
                "fn": int(metrics.false_negatives),
                "precision": float(metrics.precision),
                "recall": float(metrics.recall),
                "f1": float(metrics.f1),
            }
        )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        ["f1", "tp", "fp", "channel"],
        ascending=[False, False, True, True],
    ).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    configure_logging(args.log_level)
    mne.set_log_level("ERROR")

    rescale_threshold = not args.disable_threshold_rescale
    scan_threshold_scale = get_scan_threshold_scale(rescale_threshold)

    print(f"script={Path(__file__).name}")
    print(f"dataset={DATA_PATH}")
    print("epochs=first 5 only")
    print(f"reference_path={REFERENCE_PATH}")
    print(f"channels={CHANNELS}")
    print(f"filter_low={FILTER_LOW}")
    print(f"filter_high={FILTER_HIGH}")
    print(f"half_window_s={HALF_WINDOW_S}")
    print(f"autoreject_method={AUTOREJECT_METHOD}")
    print(f"autoreject_random_state={AUTOREJECT_RANDOM_STATE}")
    print(f"rescale_threshold={rescale_threshold}")
    print(f"scan_threshold_scale={scan_threshold_scale}")
    print(f"log_level={args.log_level}")

    started = perf_counter()

    epochs = load_first_5_epochs()
    reference = load_reference_blink_table(REFERENCE_PATH)

    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)

    print(f"\nprepared_shape={prepared.data.shape}")
    print(f"prepared_channel_names={prepared.channel_names}")
    print(f"prepared_sfreq={prepared.sfreq}")
    print(f"epoch_length_samples={prepared.epoch_length_samples}")
    print(f"valid_epoch_indices={valid_epoch_indices}")

    # --- Step 1a: learn per-channel thresholds via Bayesian optimisation ----
    print(f"\nLearning thresholds with autoreject(method={AUTOREJECT_METHOD!r})...")
    raw_thresholds = learn_bayesian_thresholds(
        prepared.data,
        channel_names=prepared.channel_names,
        sfreq=prepared.sfreq,
        valid_epoch_indices=valid_epoch_indices,
    )
    scan_thresholds = {
        ch: raw_thresholds[ch] * scan_threshold_scale
        for ch in raw_thresholds
    }
    print(f"raw_thresholds={raw_thresholds}")
    print(f"scan_thresholds={scan_thresholds}")

    # --- Step 1b: run peak_finder per channel on the concatenated signal ----
    # Mirrors Strategy C's rescale_threshold(): for each channel build the
    # concatenated signal (x0) and call peak_finder with scan_threshold.
    epoch_length_samples = int(prepared.epoch_length_samples)
    valid_indices_arr = np.asarray(valid_epoch_indices, dtype=int)
    channel_results: list[dict] = []

    for ch_idx, channel in enumerate(prepared.channel_names):
        # x0: valid epochs concatenated into one long 1D signal
        x0 = prepared.data[valid_indices_arr, ch_idx, :].reshape(-1).astype(float)

        raw_thresh = raw_thresholds[channel]
        scan_thresh = scan_thresholds[channel]

        # Extrema direction: same heuristic as MNE's _find_eog_events
        temp = x0 - np.mean(x0)
        extrema = 1 if np.abs(np.max(temp)) >= np.abs(np.min(temp)) else -1

        # Call peak_finder directly on the concatenated signal with scan_thresh
        peak_locs, _ = peak_finder(x0, thresh=scan_thresh, extrema=extrema, verbose=False)
        peak_locs = np.asarray(peak_locs, dtype=int)

        # Map peaks back to epoch-local candidate rows
        candidates = peaks_to_candidates(
            peak_locs,
            epoch_length_samples=epoch_length_samples,
            sfreq=prepared.sfreq,
            valid_epoch_indices=valid_epoch_indices,
            channel=channel,
            half_window_s=HALF_WINDOW_S,
        )
        channel_results.append(
            {
                "channel": channel,
                "raw_threshold": raw_thresh,
                "scan_threshold": scan_thresh,
                "extrema": extrema,
                "peak_count": int(len(peak_locs)),
                "candidates": candidates,
            }
        )

    elapsed_s = perf_counter() - started
    summary = build_summary(channel_results, reference=reference, n_epochs=len(epochs))

    print(f"\nelapsed_s={elapsed_s:.6f}")
    print_frame(
        "Strategy D Step 1 – Channel Summary",
        summary,
        [
            "channel",
            "raw_threshold",
            "scan_threshold",
            "extrema",
            "peak_count",
            "candidate_count",
            "tp",
            "fp",
            "fn",
            "precision",
            "recall",
            "f1",
        ],
    )

    if args.show_candidates and not summary.empty:
        best_channel = str(summary.loc[0, "channel"])
        best_result = next(
            (r for r in channel_results if r["channel"] == best_channel), None
        )
        if best_result is not None:
            print_frame(
                f"Best Channel Candidates ({best_channel})",
                best_result["candidates"],
                ["epoch_index", "channel", "blink_onset", "blink_duration", "peak_sample"],
            )


if __name__ == "__main__":
    main()
