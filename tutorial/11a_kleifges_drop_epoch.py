"""Kleifges approach with epoch health-based dropping for sustained-attention dataset.

This tutorial extends ``10a_kleifges.py`` to support variable epoch durations
(20 / 30 / 40 / 60 s) with epoch quality filtering driven by a pre-computed
``epoch_health.csv``.  The health CSV records a per-epoch quality score on a
1–5 scale (derived from 30-second windows); epochs scoring below
``MIN_HEALTH`` are excluded from blink detection.

Workflow
--------
1. Load the raw FIF and epoch it at ``EPOCH_DURATION_S``.
2. Load ``epoch_health.csv`` (30-second baseline) and assign a health score
   to every new epoch (minimum of all overlapping baseline windows).
3. Attach health flags to ``epochs.metadata`` so
   ``get_valid_epoch_indices`` returns only healthy epoch indices.
4. Run Kleifges detection, evaluate, and save masterlist / scored annotations /
   HTML report.
"""

from __future__ import annotations

import sys
from pathlib import Path

import mne
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blink_evaluation import (
    build_annotations_from_events,
    build_events_masterlist_df,
    evaluate_channels,
    load_ground_truth_annotations,
    save_scored_annotations_csv,
)
from blink_evaluation.blink_epoch_report import create_blink_epoch_report
from src.common.bad_epochs import get_valid_epoch_indices
from src.common.epoch_health import assign_epoch_health, get_valid_epoch_indices_by_health
from src.common.epoch_input import prepare_epoch_detection_input
from src.strategy_kleifges.kleifges_blinker_2017 import kleifges_strategy

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SUBJECT = "S01"
SESSION = "051017m"
BASE_DIR = Path(r"D:\dataset\sustained_attention_driving") / SUBJECT / SESSION

FIF_PATH = BASE_DIR / f"s01_{SESSION}.fif"
EPOCH_HEALTH_CSV = BASE_DIR / "epoch_health.csv"
CSV_PATH = BASE_DIR / f"s01_{SESSION}.csv"   # ground-truth annotation

OUT_DIR = BASE_DIR / "annotation_prediction"
ANNOTATION_CSV = OUT_DIR / "ear_eog_predicted_kleifges.csv"
MASTERLIST_CSV = OUT_DIR / "blink_events_masterlist_kleifges.csv"
REPORT_PATH = OUT_DIR / "blink_epoch_report_kleifges.html"

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
# Epoch duration in seconds.  Scenarios:
#   Scenario 1 → 20 s
#   Scenario 2 → 30 s
#   Scenario 3 → 40 s
#   Scenario 4 → 60 s
EPOCH_DURATION_S: float = 30.0

MIN_HEALTH: int = 4      # include epochs with health >= this value
FILTER_LOW: float = 1.0
FILTER_HIGH: float = 20.0
RESAMPLE_RATE = None
N_EPOCHS: int | None = None  # None = use all; set to a small int for quick runs
CHANNELS: list[str] | None = ["FP1", "FP2"]  # None = all EEG; limit for fast debugging
MAX_REPORT_BLINKS: int | None = 30  # None = all blinks in HTML report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_epoch_health(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"epoch_start_s", "epoch_end_s", "health"}
    if not required.issubset(df.columns):
        raise ValueError(f"epoch_health CSV missing columns: {required - set(df.columns)}")
    return df


def attach_health_metadata(epochs: mne.Epochs, health_df: pd.DataFrame, min_health: int) -> None:
    """Attach is_bad_epoch flags derived from baseline health CSV to epochs.metadata."""
    n = len(epochs)
    health_values = assign_epoch_health(health_df, float(epochs.tmax - epochs.tmin), n)
    valid_set = set(get_valid_epoch_indices_by_health(health_values, min_health))

    meta = epochs.metadata.copy() if epochs.metadata is not None else pd.DataFrame(index=range(n))
    meta = meta.reset_index(drop=True).reindex(range(n))
    meta["epoch_health"] = [h if h is not None else 0 for h in health_values]
    meta["is_bad_epoch"] = [i not in valid_set for i in range(n)]
    epochs.metadata = meta


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"\n=== Kleifges with Epoch Health Dropping (epoch_duration={EPOCH_DURATION_S}s, min_health={MIN_HEALTH}) ===")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    raw = mne.io.read_raw_fif(str(FIF_PATH), preload=True, verbose="ERROR")
    # Drop non-EEG channels (e.g. "vehicle position" is mislabelled as EEG in this dataset)
    eeg_channels = [ch for ch in raw.ch_names if "position" not in ch.lower()]
    if CHANNELS is not None:
        eeg_channels = [ch for ch in eeg_channels if ch in CHANNELS]
    raw.pick(eeg_channels)
    epochs = mne.make_fixed_length_epochs(raw, duration=EPOCH_DURATION_S, preload=True, verbose="ERROR")

    if N_EPOCHS is not None:
        epochs = epochs[:N_EPOCHS]

    health_df = load_epoch_health(EPOCH_HEALTH_CSV)
    attach_health_metadata(epochs, health_df, MIN_HEALTH)

    n_bad = int(epochs.metadata["is_bad_epoch"].sum())
    n_total = len(epochs)
    print(f"Epochs total={n_total}  dropped={n_bad}  kept={n_total - n_bad}")

    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)
    predicted_annotations = kleifges_strategy(prepared, valid_epoch_indices)

    gt_annotations = load_ground_truth_annotations(CSV_PATH, EPOCH_DURATION_S)

    scored = evaluate_channels(
        predicted_annotations,
        gt_annotations,
        epoch_duration=EPOCH_DURATION_S,
        peak_required=True,
        peak_tolerance=0.1,
    )

    em = scored.best_eval_result.event_metrics
    print(f"\nbest_channel={scored.best_channel}")
    print(f"tp={em.tp}  fp={em.fp}  fn={em.fn}")
    print(f"precision={em.precision:.4f}  recall={em.recall:.4f}  f1={em.f1:.4f}")
    print(f"\n=== Lane Summary (top 10) ===")
    print(scored.lane_summary.head(10).to_string(index=False))

    # -- Masterlist -----------------------------------------------------------
    result = scored.best_eval_result
    df_masterlist = build_events_masterlist_df(
        result.true_positives, result.false_positives, result.false_negatives
    )
    df_masterlist["onset"] = df_masterlist.apply(
        lambda row: (
            (row["onset_gt"] + row["onset_pred"]) / 2.0
            if pd.notna(row["onset_gt"]) and pd.notna(row["onset_pred"])
            else float(row["onset_gt"]) if pd.notna(row["onset_gt"])
            else float(row["onset_pred"]) if pd.notna(row["onset_pred"])
            else 0.0
        ),
        axis=1,
    )
    df_masterlist = df_masterlist.sort_values("onset").reset_index(drop=True)
    df_masterlist.to_csv(MASTERLIST_CSV, index=False)
    print(f"\nMasterlist CSV saved: {MASTERLIST_CSV}")

    # -- Scored annotations ---------------------------------------------------
    scored_ann = build_annotations_from_events(
        result.true_positives, result.false_positives, result.false_negatives
    )
    save_scored_annotations_csv(scored_ann, ANNOTATION_CSV)
    print(f"Scored annotation CSV saved: {ANNOTATION_CSV}")

    # -- HTML report ----------------------------------------------------------
    df_report = df_masterlist if MAX_REPORT_BLINKS is None else df_masterlist.head(MAX_REPORT_BLINKS)
    saved_reports = create_blink_epoch_report(
        scored,
        df_report,
        epoch_duration=EPOCH_DURATION_S,
        output_path=REPORT_PATH,
        pad_s=0.5,
        csv_path=CSV_PATH,
        sync_offset_s=0.0,
    )
    for p in saved_reports:
        print(f"Blink epoch report saved: {p}")


if __name__ == "__main__":
    main()
