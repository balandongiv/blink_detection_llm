"""Regression tests for Kleifges epoch-dropping pipeline (30s / 40s / 60s).

Each test class runs the full tutorial pipeline in-memory and compares the
generated masterlist against the committed CSV fixture in ``tests/``.

The tests are automatically skipped when the EEG dataset is absent so they
do not block CI environments that lack the raw data.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import mne

from blink_evaluation import (
    build_events_masterlist_df,
    evaluate_channels,
    load_ground_truth_annotations,
)
from pyblinker.epoch_detection import (
    assign_epoch_health,
    get_valid_epoch_indices,
    get_valid_epoch_indices_by_health,
    prepare_epoch_detection_input,
)
from pyblinker.strategies import kleifges_strategy

# ---------------------------------------------------------------------------
# Dataset paths
# ---------------------------------------------------------------------------

SUBJECT = "S01"
SESSION = "051017m"
BASE_DIR = Path(r"D:\dataset\sustained_attention_driving") / SUBJECT / SESSION

FIF_PATH = BASE_DIR / f"s01_{SESSION}.fif"
EPOCH_HEALTH_CSV = BASE_DIR / "epoch_health.csv"
CSV_PATH = BASE_DIR / f"s01_{SESSION}.csv"

DATASET_AVAILABLE = FIF_PATH.exists() and EPOCH_HEALTH_CSV.exists() and CSV_PATH.exists()

FIXTURES_DIR = REPO_ROOT / "tests"

# ---------------------------------------------------------------------------
# Pipeline constants (match tutorials)
# ---------------------------------------------------------------------------

FILTER_LOW: float = 1.0
FILTER_HIGH: float = 20.0
MIN_HEALTH: int = 4
CHANNELS: list[str] | None = ["FP1", "FP2"]


# ---------------------------------------------------------------------------
# Shared pipeline helpers
# ---------------------------------------------------------------------------

def _load_epoch_health(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"epoch_start_s", "epoch_end_s", "health"}
    if not required.issubset(df.columns):
        raise ValueError(f"Missing columns in epoch_health CSV: {required - set(df.columns)}")
    return df


def _attach_health_metadata(
    epochs: mne.Epochs, health_df: pd.DataFrame, min_health: int
) -> None:
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
    onset: float, epoch_duration_s: float, health_values: list[int | None]
) -> tuple[int, float, float, int | None]:
    epoch_idx = math.floor(onset / epoch_duration_s)
    epoch_start = epoch_idx * epoch_duration_s
    epoch_end = epoch_start + epoch_duration_s
    health = health_values[epoch_idx] if epoch_idx < len(health_values) else None
    return epoch_idx, epoch_start, epoch_end, health


def _enrich_masterlist(
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


def _run_pipeline(epoch_duration_s: float) -> pd.DataFrame:
    """Run the Kleifges pipeline for a given epoch duration and return the masterlist."""
    raw = mne.io.read_raw_fif(str(FIF_PATH), preload=True, verbose="ERROR")
    eeg_channels = [ch for ch in raw.ch_names if "position" not in ch.lower()]
    if CHANNELS is not None:
        eeg_channels = [ch for ch in eeg_channels if ch in CHANNELS]
    raw.pick(eeg_channels)
    epochs = mne.make_fixed_length_epochs(raw, duration=epoch_duration_s, preload=True, verbose="ERROR")

    health_df = _load_epoch_health(EPOCH_HEALTH_CSV)
    health_values = assign_epoch_health(health_df, epoch_duration_s, len(epochs))
    _attach_health_metadata(epochs, health_df, MIN_HEALTH)

    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=None,
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
    df_masterlist = _enrich_masterlist(df_masterlist, health_df, health_values, epoch_duration_s)
    return df_masterlist


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not DATASET_AVAILABLE, reason="EEG dataset not found at D:/dataset/...")
class TestKleifgesRegression30s:
    EPOCH_DURATION = 30.0
    FIXTURE_CSV = FIXTURES_DIR / "blink_events_masterlist_kleifges_30s.csv"

    @pytest.fixture(scope="class")
    def pipeline_result(self):
        return _run_pipeline(self.EPOCH_DURATION)

    @pytest.fixture(scope="class")
    def fixture_df(self):
        return pd.read_csv(self.FIXTURE_CSV)

    def test_row_count(self, pipeline_result, fixture_df):
        assert len(pipeline_result) == len(fixture_df), (
            f"Row count mismatch: got {len(pipeline_result)}, expected {len(fixture_df)}"
        )

    def test_status_counts(self, pipeline_result, fixture_df):
        got = pipeline_result["status"].value_counts().to_dict()
        expected = fixture_df["status"].value_counts().to_dict()
        assert got == expected, f"Status counts mismatch:\ngot:      {got}\nexpected: {expected}"

    def test_true_positive_onsets(self, pipeline_result, fixture_df):
        got_tp = pipeline_result[pipeline_result["status"] == "tp"]["onset_gt"].dropna().sort_values().reset_index(drop=True)
        exp_tp = fixture_df[fixture_df["status"] == "tp"]["onset_gt"].dropna().sort_values().reset_index(drop=True)
        pd.testing.assert_series_equal(got_tp, exp_tp, check_names=False, rtol=1e-4, atol=1e-4)

    def test_false_negative_onsets(self, pipeline_result, fixture_df):
        got_fn = pipeline_result[pipeline_result["status"] == "fn"]["onset_gt"].dropna().sort_values().reset_index(drop=True)
        exp_fn = fixture_df[fixture_df["status"] == "fn"]["onset_gt"].dropna().sort_values().reset_index(drop=True)
        pd.testing.assert_series_equal(got_fn, exp_fn, check_names=False, rtol=1e-4, atol=1e-4)

    def test_epoch_health_columns_present(self, pipeline_result):
        expected_cols = {
            "epoch_index_original", "health_original",
            "epoch_index_process_algo", "health_process_algo",
        }
        assert expected_cols.issubset(set(pipeline_result.columns))


@pytest.mark.skipif(not DATASET_AVAILABLE, reason="EEG dataset not found at D:/dataset/...")
class TestKleifgesRegression40s:
    EPOCH_DURATION = 40.0
    FIXTURE_CSV = FIXTURES_DIR / "blink_events_masterlist_kleifges_40s.csv"

    @pytest.fixture(scope="class")
    def pipeline_result(self):
        return _run_pipeline(self.EPOCH_DURATION)

    @pytest.fixture(scope="class")
    def fixture_df(self):
        return pd.read_csv(self.FIXTURE_CSV)

    def test_row_count(self, pipeline_result, fixture_df):
        assert len(pipeline_result) == len(fixture_df), (
            f"Row count mismatch: got {len(pipeline_result)}, expected {len(fixture_df)}"
        )

    def test_status_counts(self, pipeline_result, fixture_df):
        got = pipeline_result["status"].value_counts().to_dict()
        expected = fixture_df["status"].value_counts().to_dict()
        assert got == expected, f"Status counts mismatch:\ngot:      {got}\nexpected: {expected}"

    def test_true_positive_onsets(self, pipeline_result, fixture_df):
        got_tp = pipeline_result[pipeline_result["status"] == "tp"]["onset_gt"].dropna().sort_values().reset_index(drop=True)
        exp_tp = fixture_df[fixture_df["status"] == "tp"]["onset_gt"].dropna().sort_values().reset_index(drop=True)
        pd.testing.assert_series_equal(got_tp, exp_tp, check_names=False, rtol=1e-4, atol=1e-4)

    def test_false_negative_onsets(self, pipeline_result, fixture_df):
        got_fn = pipeline_result[pipeline_result["status"] == "fn"]["onset_gt"].dropna().sort_values().reset_index(drop=True)
        exp_fn = fixture_df[fixture_df["status"] == "fn"]["onset_gt"].dropna().sort_values().reset_index(drop=True)
        pd.testing.assert_series_equal(got_fn, exp_fn, check_names=False, rtol=1e-4, atol=1e-4)

    def test_epoch_health_columns_present(self, pipeline_result):
        expected_cols = {
            "epoch_index_original", "health_original",
            "epoch_index_process_algo", "health_process_algo",
        }
        assert expected_cols.issubset(set(pipeline_result.columns))


@pytest.mark.skipif(not DATASET_AVAILABLE, reason="EEG dataset not found at D:/dataset/...")
class TestKleifgesRegression60s:
    EPOCH_DURATION = 60.0
    FIXTURE_CSV = FIXTURES_DIR / "blink_events_masterlist_kleifges_60s.csv"

    @pytest.fixture(scope="class")
    def pipeline_result(self):
        return _run_pipeline(self.EPOCH_DURATION)

    @pytest.fixture(scope="class")
    def fixture_df(self):
        return pd.read_csv(self.FIXTURE_CSV)

    def test_row_count(self, pipeline_result, fixture_df):
        assert len(pipeline_result) == len(fixture_df), (
            f"Row count mismatch: got {len(pipeline_result)}, expected {len(fixture_df)}"
        )

    def test_status_counts(self, pipeline_result, fixture_df):
        got = pipeline_result["status"].value_counts().to_dict()
        expected = fixture_df["status"].value_counts().to_dict()
        assert got == expected, f"Status counts mismatch:\ngot:      {got}\nexpected: {expected}"

    def test_true_positive_onsets(self, pipeline_result, fixture_df):
        got_tp = pipeline_result[pipeline_result["status"] == "tp"]["onset_gt"].dropna().sort_values().reset_index(drop=True)
        exp_tp = fixture_df[fixture_df["status"] == "tp"]["onset_gt"].dropna().sort_values().reset_index(drop=True)
        pd.testing.assert_series_equal(got_tp, exp_tp, check_names=False, rtol=1e-4, atol=1e-4)

    def test_false_negative_onsets(self, pipeline_result, fixture_df):
        got_fn = pipeline_result[pipeline_result["status"] == "fn"]["onset_gt"].dropna().sort_values().reset_index(drop=True)
        exp_fn = fixture_df[fixture_df["status"] == "fn"]["onset_gt"].dropna().sort_values().reset_index(drop=True)
        pd.testing.assert_series_equal(got_fn, exp_fn, check_names=False, rtol=1e-4, atol=1e-4)

    def test_epoch_health_columns_present(self, pipeline_result):
        expected_cols = {
            "epoch_index_original", "health_original",
            "epoch_index_process_algo", "health_process_algo",
        }
        assert expected_cols.issubset(set(pipeline_result.columns))
