"""Unit tests for epoch health assignment across epoch-duration scenarios.

Baseline health data (30-second windows, 210-second coverage):

  epoch_index  epoch_start_s  epoch_end_s  health
  0             0              30           5
  1             30             60           5
  2             60             90           5
  3             90             120          1
  4             120            150          5
  5             150            180          5
  6             180            210          2

Signal assumed to be 240 seconds; final epoch(s) that extend beyond 210 s
have no baseline coverage and receive None.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pyblinker.epoch_detection import assign_epoch_health, get_valid_epoch_indices_by_health

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

BASELINE_ROWS = [
    {"epoch_start_s": 0,   "epoch_end_s": 30,  "health": 5},
    {"epoch_start_s": 30,  "epoch_end_s": 60,  "health": 5},
    {"epoch_start_s": 60,  "epoch_end_s": 90,  "health": 5},
    {"epoch_start_s": 90,  "epoch_end_s": 120, "health": 1},
    {"epoch_start_s": 120, "epoch_end_s": 150, "health": 5},
    {"epoch_start_s": 150, "epoch_end_s": 180, "health": 5},
    {"epoch_start_s": 180, "epoch_end_s": 210, "health": 2},
]

SIGNAL_DURATION_S = 240.0


@pytest.fixture()
def health_df() -> pd.DataFrame:
    return pd.DataFrame(BASELINE_ROWS)


def _n_epochs(epoch_duration_s: float) -> int:
    import math
    return math.floor(SIGNAL_DURATION_S / epoch_duration_s)


# ---------------------------------------------------------------------------
# Scenario 1 – 20-second epochs
# ---------------------------------------------------------------------------

class TestScenario1_20s:
    DURATION = 20.0

    def test_health_values(self, health_df):
        n = _n_epochs(self.DURATION)  # 12
        health = assign_epoch_health(health_df, self.DURATION, n)
        # Epochs 0-9 overlap baseline; epoch 11 ([220,240]) has no coverage
        expected = [5, 5, 5, 5, 1, 1, 5, 5, 5, 2, 2, None]
        assert health == expected

    def test_epoch_count(self, health_df):
        n = _n_epochs(self.DURATION)
        health = assign_epoch_health(health_df, self.DURATION, n)
        assert len(health) == 12

    def test_boundary_overlap_epoch4(self, health_df):
        # epoch [80, 100] overlaps baseline [60,90]=5 AND [90,120]=1 → min=1
        health = assign_epoch_health(health_df, self.DURATION, 5)
        assert health[4] == 1

    def test_boundary_overlap_epoch7(self, health_df):
        # epoch [140, 160] overlaps [120,150]=5 AND [150,180]=5 → min=5
        health = assign_epoch_health(health_df, self.DURATION, 8)
        assert health[7] == 5

    def test_valid_indices_min3(self, health_df):
        n = _n_epochs(self.DURATION)
        health = assign_epoch_health(health_df, self.DURATION, n)
        valid = get_valid_epoch_indices_by_health(health, min_health=3)
        # health >= 3 at indices 0,1,2,3,6,7,8 (health=5 for all)
        assert valid == [0, 1, 2, 3, 6, 7, 8]

    def test_valid_indices_min1(self, health_df):
        n = _n_epochs(self.DURATION)
        health = assign_epoch_health(health_df, self.DURATION, n)
        valid = get_valid_epoch_indices_by_health(health, min_health=1)
        # all epochs with coverage are valid (index 11 has None → excluded)
        assert valid == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    def test_valid_indices_min5(self, health_df):
        n = _n_epochs(self.DURATION)
        health = assign_epoch_health(health_df, self.DURATION, n)
        valid = get_valid_epoch_indices_by_health(health, min_health=5)
        # only epochs with health=5 pass
        assert valid == [0, 1, 2, 3, 6, 7, 8]


# ---------------------------------------------------------------------------
# Scenario 2 – 30-second epochs (baseline window size)
# ---------------------------------------------------------------------------

class TestScenario2_30s:
    DURATION = 30.0

    def test_health_values(self, health_df):
        n = _n_epochs(self.DURATION)  # 8
        health = assign_epoch_health(health_df, self.DURATION, n)
        # epoch 7 = [210, 240]: no baseline coverage
        expected = [5, 5, 5, 1, 5, 5, 2, None]
        assert health == expected

    def test_exact_alignment_no_mixing(self, health_df):
        # When epoch duration equals baseline duration, each epoch maps to exactly one baseline
        health = assign_epoch_health(health_df, self.DURATION, 7)
        assert health == [5, 5, 5, 1, 5, 5, 2]

    def test_bad_epoch_index3(self, health_df):
        health = assign_epoch_health(health_df, self.DURATION, 4)
        assert health[3] == 1

    def test_valid_indices_min3(self, health_df):
        n = _n_epochs(self.DURATION)
        health = assign_epoch_health(health_df, self.DURATION, n)
        valid = get_valid_epoch_indices_by_health(health, min_health=3)
        assert valid == [0, 1, 2, 4, 5]


# ---------------------------------------------------------------------------
# Scenario 3 – 40-second epochs
# ---------------------------------------------------------------------------

class TestScenario3_40s:
    DURATION = 40.0

    def test_health_values(self, health_df):
        n = _n_epochs(self.DURATION)  # 6
        health = assign_epoch_health(health_df, self.DURATION, n)
        expected = [5, 5, 1, 5, 2, 2]
        assert health == expected

    def test_epoch_count(self, health_df):
        n = _n_epochs(self.DURATION)
        health = assign_epoch_health(health_df, self.DURATION, n)
        assert len(health) == 6

    def test_bad_epoch_index2(self, health_df):
        # epoch [80, 120] overlaps [60,90]=5 AND [90,120]=1 → min=1
        health = assign_epoch_health(health_df, self.DURATION, 3)
        assert health[2] == 1

    def test_mixed_overlap_epoch4(self, health_df):
        # epoch [160, 200] overlaps [150,180]=5 AND [180,210]=2 → min=2
        health = assign_epoch_health(health_df, self.DURATION, 5)
        assert health[4] == 2

    def test_valid_indices_min3(self, health_df):
        n = _n_epochs(self.DURATION)
        health = assign_epoch_health(health_df, self.DURATION, n)
        valid = get_valid_epoch_indices_by_health(health, min_health=3)
        assert valid == [0, 1, 3]


# ---------------------------------------------------------------------------
# Scenario 4 – 60-second epochs
# ---------------------------------------------------------------------------

class TestScenario4_60s:
    DURATION = 60.0

    def test_health_values(self, health_df):
        n = _n_epochs(self.DURATION)  # 4
        health = assign_epoch_health(health_df, self.DURATION, n)
        expected = [5, 1, 5, 2]
        assert health == expected

    def test_epoch_count(self, health_df):
        n = _n_epochs(self.DURATION)
        health = assign_epoch_health(health_df, self.DURATION, n)
        assert len(health) == 4

    def test_bad_epoch_index1(self, health_df):
        # epoch [60, 120] overlaps [60,90]=5 AND [90,120]=1 → min=1
        health = assign_epoch_health(health_df, self.DURATION, 2)
        assert health[1] == 1

    def test_good_epoch_index2(self, health_df):
        # epoch [120, 180] overlaps [120,150]=5 AND [150,180]=5 → min=5
        health = assign_epoch_health(health_df, self.DURATION, 3)
        assert health[2] == 5

    def test_valid_indices_min3(self, health_df):
        n = _n_epochs(self.DURATION)
        health = assign_epoch_health(health_df, self.DURATION, n)
        valid = get_valid_epoch_indices_by_health(health, min_health=3)
        assert valid == [0, 2]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_health_df(self):
        df = pd.DataFrame(columns=["epoch_start_s", "epoch_end_s", "health"])
        health = assign_epoch_health(df, 30.0, 5)
        assert health == [None, None, None, None, None]

    def test_zero_epochs_requested(self, health_df):
        health = assign_epoch_health(health_df, 30.0, 0)
        assert health == []

    def test_single_epoch_full_coverage(self, health_df):
        # one epoch spanning the entire baseline → min of all healths
        health = assign_epoch_health(health_df, 210.0, 1)
        assert health == [1]  # min(5,5,5,1,5,5,2)=1

    def test_no_coverage_returns_none(self, health_df):
        # epoch entirely beyond baseline coverage
        df_extra = pd.DataFrame([
            {"epoch_start_s": 0, "epoch_end_s": 30, "health": 4}
        ])
        health = assign_epoch_health(df_extra, 30.0, 3)
        # [0,30]=4, [30,60]=None, [60,90]=None
        assert health[0] == 4
        assert health[1] is None
        assert health[2] is None

    def test_valid_indices_all_none(self):
        health = [None, None, None]
        valid = get_valid_epoch_indices_by_health(health, min_health=3)
        assert valid == []

    def test_valid_indices_empty_list(self):
        valid = get_valid_epoch_indices_by_health([], min_health=3)
        assert valid == []

    def test_valid_indices_all_pass(self):
        health = [5, 4, 3]
        valid = get_valid_epoch_indices_by_health(health, min_health=3)
        assert valid == [0, 1, 2]

    def test_valid_indices_threshold_boundary(self):
        health = [3, 2, 3]
        assert get_valid_epoch_indices_by_health(health, min_health=3) == [0, 2]
        assert get_valid_epoch_indices_by_health(health, min_health=4) == []

    def test_partial_overlap_uses_min(self, health_df):
        # epoch [85, 95] straddles the boundary between health=5 and health=1
        health = assign_epoch_health(health_df, 10.0, 10)
        epoch_8_5 = health[8]  # [80, 90] → [60,90]=5 AND [90,120]=1 → wait, [80,90] only overlaps [60,90]=5
        epoch_9 = health[9]    # [90, 100] → only [90,120]=1
        assert epoch_8_5 == 5
        assert epoch_9 == 1
