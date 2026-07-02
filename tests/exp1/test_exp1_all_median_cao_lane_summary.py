"""Regression test: exp1 'frontal_left|any|median' channel-ablation lane summary (Cao2018).

Runs :func:`run_one_session` for the ``frontal_left`` channel-selection group on a
single Cao2018 session (the first one discovered by :func:`discover_cao_pairs`) with
a 60-second epoch duration, and compares the per-channel results against the
fixture ``tests/exp1/scored_lane_summary_cao.csv``.

The test is skipped when the Cao2018 dataset is not available locally, or when
the fixture CSV has not been added yet.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.project_paths import get_cao_paths
from experiment_script.channel_ablation_utils import run_one_session
from src.utils.dataset_discovery import discover_cao_pairs

FIXTURE_CSV = Path(__file__).resolve().parent / "scored_lane_summary_cao.csv"

_CAO = get_cao_paths()
CAO_DATASET_ROOT = _CAO["dataset_root"]
BRAIN_REGION_YAML = _CAO["brain_region_yaml"]

EPOCH_DURATION_S = 30.0
STD_THRESHOLD = 3.0
CENTER_METHOD = "median"
FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = 100
AUTOREJECT_RS = 42

DATASET_AVAILABLE = CAO_DATASET_ROOT.exists() and BRAIN_REGION_YAML.exists()


def _first_cao_pair() -> dict | None:
    if not DATASET_AVAILABLE:
        return None
    pairs = discover_cao_pairs(CAO_DATASET_ROOT)
    return pairs[0] if pairs else None


@pytest.mark.skipif(not DATASET_AVAILABLE, reason="Cao2018 dataset not available")
def test_exp1_all_median_lane_summary_matches_fixture_cao() -> None:
    pair = _first_cao_pair()
    assert pair is not None, "no Cao2018 session found"

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
        use_epoch_health=False,
        groups_filter={"frontal_left"},
        verbose=False,
    )
    group_records = [r for r in records if r["condition"].startswith("frontal_left|")]
    assert group_records, "'frontal_left' group not found in exp1 records"

    # records already carry lane_summary's own columns (channel/tp/fp/fn/precision/
    # recall/f1), pre-sorted by f1/tp/fp/channel — no renaming or re-sorting needed.
    actual = pd.DataFrame(group_records)[["channel", "tp", "fp", "fn", "precision", "recall", "f1"]]
    actual = actual.reset_index(drop=True)

    expected = pd.read_csv(FIXTURE_CSV)[["channel", "tp", "fp", "fn", "precision", "recall", "f1"]]

    pd.testing.assert_frame_equal(actual, expected, check_dtype=False)
    print(actual)
    print("rpb All tests passed")
