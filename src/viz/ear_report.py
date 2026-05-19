"""Helpers for preparing EAR threshold refinement results for visualization."""

from __future__ import annotations

import pandas as pd

__all__ = ["prepare_threshold_report_dataframe"]


def prepare_threshold_report_dataframe(
    features: pd.DataFrame, sfreq: float, threshold_value: float
) -> pd.DataFrame:
    """Return a report-ready DataFrame for a single EAR threshold value."""

    report_df = features.loc[features["threshold_value"] == threshold_value].copy()

    if "onset__refine__ear" not in report_df.columns:
        report_df["onset__refine__ear"] = pd.to_numeric(
            report_df.get(
                "refined_left_threshold", report_df.get("refined_start_sample")
            ),
            errors="coerce",
        )
        report_df["onset__refine__ear"] = report_df["onset__refine__ear"] / sfreq
    else:
        report_df["onset__refine__ear"] = pd.to_numeric(
            report_df["onset__refine__ear"], errors="coerce"
        )

    if "duration__refine__ear" not in report_df.columns:
        right_samples = pd.to_numeric(
            report_df.get(
                "refined_right_threshold", report_df.get("refined_end_sample")
            ),
            errors="coerce",
        )
        left_samples = pd.to_numeric(
            report_df.get(
                "refined_left_threshold", report_df.get("refined_start_sample")
            ),
            errors="coerce",
        )
        report_df["duration__refine__ear"] = (right_samples - left_samples) / sfreq
    else:
        report_df["duration__refine__ear"] = pd.to_numeric(
            report_df["duration__refine__ear"], errors="coerce"
        )

    if "trough__th_point__ear" not in report_df.columns:
        report_df["trough__th_point__ear"] = pd.to_numeric(
            report_df.get("refined_lowest_point_sample"), errors="coerce"
        )
    else:
        report_df["trough__th_point__ear"] = pd.to_numeric(
            report_df["trough__th_point__ear"], errors="coerce"
        )

    if "onset__th_interpolation__ear" not in report_df.columns:
        left_time = pd.to_numeric(
            report_df.get("left_interpolated_threshold", float("nan")), errors="coerce"
        )
        report_df["onset__th_interpolation__ear"] = left_time
    else:
        report_df["onset__th_interpolation__ear"] = pd.to_numeric(
            report_df["onset__th_interpolation__ear"], errors="coerce"
        )

    if "duration__th_interpolation__ear" not in report_df.columns:
        right_time = pd.to_numeric(
            report_df.get("right_interpolated_threshold", float("nan")), errors="coerce"
        )
        report_df["duration__th_interpolation__ear"] = (
            right_time - report_df["onset__th_interpolation__ear"]
        )
    else:
        report_df["duration__th_interpolation__ear"] = pd.to_numeric(
            report_df["duration__th_interpolation__ear"], errors="coerce"
        )

    missing_interp = report_df["onset__th_interpolation__ear"].isna()
    if missing_interp.any():
        left_samples = pd.to_numeric(
            report_df.get("left_interpolated_threshold_sample"), errors="coerce"
        )
        right_samples = pd.to_numeric(
            report_df.get("right_interpolated_threshold_sample"), errors="coerce"
        )
        report_df.loc[missing_interp, "onset__th_interpolation__ear"] = (
            left_samples.loc[missing_interp] / sfreq
        )
        report_df.loc[missing_interp, "duration__th_interpolation__ear"] = (
            right_samples.loc[missing_interp] - left_samples.loc[missing_interp]
        ) / sfreq

    report_df["threshold_crossing_found"] = report_df["refinement_succeeded"].astype(
        bool
    )

    return report_df
