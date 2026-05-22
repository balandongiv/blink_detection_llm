"""Kleifges blink detection with epoch health-based dropping.

Runs the full pipeline for each epoch duration in EPOCH_SIZES (20 / 30 / 40 / 60 s).
For each duration the script:

1. Loads the raw FIF and creates fixed-length epochs.
2. Loads ``epoch_health.csv`` (30-second baseline windows) and assigns a health
   score to every new epoch (minimum of all overlapping baseline windows).
3. Attaches health flags to ``epochs.metadata`` so ``get_valid_epoch_indices``
   returns only healthy epoch indices.
4. Runs Kleifges detection, evaluates against ground truth, and saves:
   - masterlist CSV  (``blink_events_masterlist_kleifges_<N>s.csv``)
   - scored-annotations CSV  (``ear_eog_predicted_kleifges_<N>s.csv``)
   - HTML blink-epoch report  (``blink_epoch_report_kleifges_<N>s.html``)
"""

from __future__ import annotations

import math
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
from pyblinker.epoch_detection import (
    assign_epoch_health,
    get_valid_epoch_indices,
    get_valid_epoch_indices_by_health,
    prepare_epoch_detection_input,
)
from pyblinker.strategies import kleifges_strategy

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SUBJECT = "S01"
SESSION = "051017m"
BASE_DIR = Path(r"D:\dataset\sustained_attention_driving") / SUBJECT / SESSION

FIF_PATH = BASE_DIR / f"s01_{SESSION}.fif"
EPOCH_HEALTH_CSV = BASE_DIR / "epoch_health.csv"
CSV_PATH = BASE_DIR / f"s01_{SESSION}.csv"

OUT_DIR = BASE_DIR / "annotation_prediction"

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
EPOCH_SIZES: list[float] = [
                            # 20.0,
                            30.0,
                            # 40.0,
                            # 60.0
                            ]

MIN_HEALTH: int = 4
FILTER_LOW: float = 1.0
FILTER_HIGH: float = 20.0
RESAMPLE_RATE = None
N_EPOCHS: int | None = None
CHANNELS: list[str] | None = ["FP1", "FP2"]
MAX_REPORT_BLINKS: int | None = 30


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
    n = len(epochs)
    health_values = assign_epoch_health(health_df, float(epochs.tmax - epochs.tmin), n)
    valid_set = set(get_valid_epoch_indices_by_health(health_values, min_health))
    meta = epochs.metadata.copy() if epochs.metadata is not None else pd.DataFrame(index=range(n))
    meta = meta.reset_index(drop=True).reindex(range(n))
    meta["epoch_health"] = [h if h is not None else 0 for h in health_values]
    meta["is_bad_epoch"] = [i not in valid_set for i in range(n)]
    epochs.metadata = meta


def _find_original_epoch(
    onset: float, health_df: pd.DataFrame
) -> tuple[int | None, float | None, float | None, int | None]:
    mask = (health_df["epoch_start_s"] <= onset) & (health_df["epoch_end_s"] > onset)
    matching = health_df[mask]
    if matching.empty:
        return None, None, None, None
    row = matching.iloc[0]
    idx = int(matching.index[0])
    return idx, float(row["epoch_start_s"]), float(row["epoch_end_s"]), int(row["health"])


def _find_algo_epoch(
    onset: float,
    epoch_duration_s: float,
    health_values: list[int | None],
) -> tuple[int, float, float, int | None]:
    epoch_idx = math.floor(onset / epoch_duration_s)
    epoch_start = epoch_idx * epoch_duration_s
    epoch_end = epoch_start + epoch_duration_s
    health = health_values[epoch_idx] if epoch_idx < len(health_values) else None
    return epoch_idx, epoch_start, epoch_end, health


def enrich_masterlist_with_epoch_health(
    df: pd.DataFrame,
    health_df: pd.DataFrame,
    health_values: list[int | None],
    epoch_duration_s: float,
) -> pd.DataFrame:
    orig_idx, orig_start, orig_end, orig_health = [], [], [], []
    algo_idx, algo_start, algo_end, algo_health = [], [], [], []

    for onset in df["onset"]:
        oi, os, oe, oh = _find_original_epoch(float(onset), health_df)
        orig_idx.append(oi); orig_start.append(os); orig_end.append(oe); orig_health.append(oh)
        ai, as_, ae, ah = _find_algo_epoch(float(onset), epoch_duration_s, health_values)
        algo_idx.append(ai); algo_start.append(as_); algo_end.append(ae); algo_health.append(ah)

    df = df.copy()
    df["epoch_index_original"] = orig_idx
    df["epoch_start_s_original"] = orig_start
    df["epoch_end_s_original"] = orig_end
    df["health_original"] = orig_health
    df["epoch_index_process_algo"] = algo_idx
    df["epoch_start_s_process_algo"] = algo_start
    df["epoch_end_s_process_algo"] = algo_end
    df["health_process_algo"] = algo_health
    return df


# ---------------------------------------------------------------------------
# Per-duration pipeline
# ---------------------------------------------------------------------------

def run_one_epoch_size(
    epoch_duration_s: float,
    raw: mne.io.BaseRaw,
    health_df: pd.DataFrame,
) -> None:
    tag = f"{int(epoch_duration_s)}s"
    annotation_csv = OUT_DIR / f"ear_eog_predicted_kleifges_{tag}.csv"
    masterlist_csv = REPO_ROOT / "tests" / f"blink_events_masterlist_kleifges_{tag}.csv"
    report_path = OUT_DIR / f"blink_epoch_report_kleifges_{tag}.html"

    print(f"\n=== Kleifges  epoch_duration={epoch_duration_s}s  min_health={MIN_HEALTH} ===")

    # Work on a copy so the original raw is reusable across epoch sizes
    raw_copy = raw.copy()
    epochs = mne.make_fixed_length_epochs(raw_copy, duration=epoch_duration_s, preload=True, verbose="ERROR")

    if N_EPOCHS is not None:
        epochs = epochs[:N_EPOCHS]

    health_values = assign_epoch_health(health_df, epoch_duration_s, len(epochs))
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

    gt_annotations = load_ground_truth_annotations(CSV_PATH, epoch_duration_s)

    scored = evaluate_channels(
        predicted_annotations,
        gt_annotations,
        epoch_duration=epoch_duration_s,
        peak_required=True,
        peak_tolerance=0.1,
    )

    em = scored.best_eval_result.event_metrics
    print(f"best_channel={scored.best_channel}")
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
    df_masterlist = enrich_masterlist_with_epoch_health(
        df_masterlist, health_df, health_values, epoch_duration_s
    )
    masterlist_csv.parent.mkdir(parents=True, exist_ok=True)
    df_masterlist.to_csv(masterlist_csv, index=False)
    print(f"\nMasterlist CSV saved: {masterlist_csv}")

    # -- Scored annotations ---------------------------------------------------
    scored_ann = build_annotations_from_events(
        result.true_positives, result.false_positives, result.false_negatives
    )
    save_scored_annotations_csv(scored_ann, annotation_csv)
    print(f"Scored annotation CSV saved: {annotation_csv}")

    # -- HTML report ----------------------------------------------------------
    df_report = df_masterlist if MAX_REPORT_BLINKS is None else df_masterlist.head(MAX_REPORT_BLINKS)
    saved_reports = create_blink_epoch_report(
        scored,
        df_report,
        epoch_duration=epoch_duration_s,
        output_path=report_path,
        pad_s=0.5,
        csv_path=CSV_PATH,
        sync_offset_s=0.0,
    )
    for p in saved_reports:
        print(f"Blink epoch report saved: {p}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    raw = mne.io.read_raw_fif(str(FIF_PATH), preload=True, verbose="ERROR")
    eeg_channels = [ch for ch in raw.ch_names if "position" not in ch.lower()]
    if CHANNELS is not None:
        eeg_channels = [ch for ch in eeg_channels if ch in CHANNELS]
    raw.pick(eeg_channels)

    health_df = load_epoch_health(EPOCH_HEALTH_CSV)

    for epoch_duration_s in EPOCH_SIZES:
        run_one_epoch_size(epoch_duration_s, raw, health_df)


if __name__ == "__main__":
    main()
