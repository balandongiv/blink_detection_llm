"""Strategy A — Stage 1 benchmark on sample data.

Runs Strategy A Step 1 against the bundled dev sample data,
comparing detected blink candidates to human-annotated ground truth.
"""

from __future__ import annotations

from pathlib import Path
import sys

import mne

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pyblinker.common.bad_epochs import get_valid_epoch_indices
from pyblinker.common.epoch_input import prepare_epoch_detection_input
from pyblinker.common.validation import (
    filter_reference_to_valid_epochs,
    load_reference_blink_table,
    match_blink_tables,
)
from pyblinker.strategy_a.kleifges_blinker_2017 import kleifges_strategy_a

DATA_PATH = REPO_ROOT / "sample_data" / "dev_epo.fif"
REFERENCE_PATH = REPO_ROOT / "sample_data" / "dev_epo_annotations_5_epochs.csv"
TARGET_CHANNEL = "EEG X1 - Pz"
N_EPOCHS = 5
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None
EXPECTED_STAGE1_REGIONS = 185


def main() -> None:
    epochs = mne.read_epochs(str(DATA_PATH), preload=True, verbose="ERROR")
    epochs = epochs[:N_EPOCHS].copy().pick([TARGET_CHANNEL])

    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)
    channel_results = kleifges_strategy_a(prepared, valid_epoch_indices)
    result = channel_results[0]
    df_positions = result["df_positions"]
    mapped_positions = result["mapped_candidates"]
    signal_by_epoch = result["signal_by_epoch"]

    reference = load_reference_blink_table(REFERENCE_PATH)
    reference = filter_reference_to_valid_epochs(reference, valid_epoch_indices)
    metrics = match_blink_tables(
        mapped_positions,
        reference,
        n_epochs=len(epochs),
        signal_by_epoch=signal_by_epoch,
        sfreq=float(prepared.sfreq),
    )

    print(f"stage1_candidates={len(df_positions)}  expected={EXPECTED_STAGE1_REGIONS}  delta={len(df_positions) - EXPECTED_STAGE1_REGIONS}")
    print(f"reference_blinks={len(reference)}")
    print(f"tp={metrics.true_positives}  fp={metrics.false_positives}  fn={metrics.false_negatives}")
    print(f"precision={metrics.precision:.4f}  recall={metrics.recall:.4f}  f1={metrics.f1:.4f}")


if __name__ == "__main__":
    main()
