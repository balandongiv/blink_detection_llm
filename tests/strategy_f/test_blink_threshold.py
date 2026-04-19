"""Tests for pyblinker.strategy_f.blink_threshold."""

import numpy as np
import pytest

from src.fitutils import mad
from src.strategy_f.blink_threshold import (
    SCALING_FACTOR,
    compute_threshold_from_samples,
)

# Toy skewed dataset where mean and median differ clearly
SKEWED_SAMPLES = np.array([0, 0, 1, 1, 2, 2, 10, 12], dtype=float)
STD_THRESHOLD = 3.5


class TestComputeThresholdFromSamples:
    def test_median_center_value(self):
        center, _, _ = compute_threshold_from_samples(
            SKEWED_SAMPLES, STD_THRESHOLD, center_method="median"
        )
        assert center == pytest.approx(float(np.median(SKEWED_SAMPLES)))

    def test_mean_center_value(self):
        center, _, _ = compute_threshold_from_samples(
            SKEWED_SAMPLES, STD_THRESHOLD, center_method="mean"
        )
        assert center == pytest.approx(float(np.mean(SKEWED_SAMPLES, dtype=np.float64)))

    def test_dispersion_is_scaling_factor_times_mad(self):
        expected_dispersion = float(SCALING_FACTOR * mad(SKEWED_SAMPLES))
        _, disp_median, _ = compute_threshold_from_samples(
            SKEWED_SAMPLES, STD_THRESHOLD, center_method="median"
        )
        _, disp_mean, _ = compute_threshold_from_samples(
            SKEWED_SAMPLES, STD_THRESHOLD, center_method="mean"
        )
        assert disp_median == pytest.approx(expected_dispersion)
        assert disp_mean == pytest.approx(expected_dispersion)

    def test_threshold_equals_center_plus_k_times_dispersion(self):
        center, dispersion, threshold = compute_threshold_from_samples(
            SKEWED_SAMPLES, STD_THRESHOLD, center_method="median"
        )
        assert threshold == pytest.approx(center + STD_THRESHOLD * dispersion)

    def test_mean_threshold_also_follows_formula(self):
        center, dispersion, threshold = compute_threshold_from_samples(
            SKEWED_SAMPLES, STD_THRESHOLD, center_method="mean"
        )
        assert threshold == pytest.approx(center + STD_THRESHOLD * dispersion)

    def test_invalid_center_method_raises_value_error(self):
        with pytest.raises(ValueError, match="center_method"):
            compute_threshold_from_samples(SKEWED_SAMPLES, STD_THRESHOLD, center_method="mode")

    def test_median_and_mean_produce_different_thresholds_on_skewed_data(self):
        _, _, threshold_median = compute_threshold_from_samples(
            SKEWED_SAMPLES, STD_THRESHOLD, center_method="median"
        )
        _, _, threshold_mean = compute_threshold_from_samples(
            SKEWED_SAMPLES, STD_THRESHOLD, center_method="mean"
        )
        # On right-skewed data mean > median, so mean-based threshold is higher
        assert threshold_mean > threshold_median

    def test_default_center_method_is_median(self):
        center_default, _, _ = compute_threshold_from_samples(SKEWED_SAMPLES, STD_THRESHOLD)
        center_median, _, _ = compute_threshold_from_samples(
            SKEWED_SAMPLES, STD_THRESHOLD, center_method="median"
        )
        assert center_default == pytest.approx(center_median)
