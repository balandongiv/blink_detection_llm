"""Regression test: exp1 'all|any|median' channel-ablation lane summary.

Runs :func:`run_one_session` for the ``all`` channel-selection group on session
S01_20170519_043933 (same parameters as ``experiment_script/check_exp1_vs_10d.py``)
and compares the per-channel results against the committed fixture
``tests/exp1/scored_lane_summary_raja.csv``.

The test is skipped when the raw EEG dataset is not available locally.

| Channel |  TP |  FP |  FN | Precision | Recall |         F1 |
| ------- | --: | --: | --: | --------: | -----: | ---------: |
| E22     | 136 |  35 |   2 |    0.7953 | 0.9855 | **0.8803** |
| E23     | 112 |  43 |  26 |    0.7226 | 0.8116 | **0.7645** |
| E24     |  62 |  15 |  76 |    0.8052 | 0.4493 | **0.5767** |
| E33     |   0 | 101 | 138 |    0.0000 | 0.0000 | **0.0000** |


"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.project_paths import get_raja_paths
from src.utils.channel_ablation_utils import run_one_session

FIXTURE_CSV = Path(__file__).resolve().parent / "scored_lane_summary_raja.csv"

_RAJA = get_raja_paths()
_SESSION = "S1/S01_20170519_043933"
FIF_PATH = _RAJA["processed_base"] / _SESSION / "seg_data_raw" / "eeg_eog_raw.fif"
CSV_PATH = _RAJA["annotation_base"] / _SESSION / "ear_eog.csv"
BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"

EPOCH_DURATION_S = 30.0
STD_THRESHOLD = 3.0  # matches experiment_script/setup/exp1_channel_selection_raja_std30.yaml
CENTER_METHOD = "median"
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = 100
AUTOREJECT_RS = 42

DATASET_AVAILABLE = FIF_PATH.exists() and CSV_PATH.exists() and BRAIN_REGION_YAML.exists()


@pytest.mark.skipif(not DATASET_AVAILABLE, reason="raja S01_20170519_043933 dataset not available")
def test_exp1_all_median_lane_summary_matches_fixture_raja() -> None:
    pair = {
        "dataset": "raja",
        "name": "S01_20170519_043933",
        "fif": FIF_PATH,
        "csv": CSV_PATH,
    }
    records = run_one_session(
        pair,
        region_yaml=BRAIN_REGION_YAML,
        epoch_duration_s=EPOCH_DURATION_S,
        std_threshold=STD_THRESHOLD,
        center_methods=(CENTER_METHOD,),
        autoreject_random_state=AUTOREJECT_RS,
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
        # No epoch_health.csv for raja pairs, so this is a no-op here (falls back to
        # the generic epoch-validity check either way) — kept False to match production.
        use_epoch_health=False,
        groups_filter={"all"},
        verbose=False,
    )
    group_records = [r for r in records if r["condition"].startswith("all|")]
    assert group_records, "'all' group not found in exp1 records"

    # records carry the renamed lane_summary columns (channel_in_group/det_tp/det_fp/
    # det_fn/det_precision/det_recall/det_f1); map back to the fixture's plain names.
    actual = pd.DataFrame(group_records)[
        ["channel_in_group", "det_tp", "det_fp", "det_fn", "det_precision", "det_recall", "det_f1"]
    ].rename(columns={
        "channel_in_group": "channel", "det_tp": "tp", "det_fp": "fp", "det_fn": "fn",
        "det_precision": "precision", "det_recall": "recall", "det_f1": "f1",
    })
    actual = actual.reset_index(drop=True)

    expected = pd.read_csv(FIXTURE_CSV)[["channel", "tp", "fp", "fn", "precision", "recall", "f1"]]

    pd.testing.assert_frame_equal(actual, expected, check_dtype=False)
    print(actual)
    print("rpb All tests passed")
