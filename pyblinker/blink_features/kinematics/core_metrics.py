"""Kinematic-only blink waveform metrics."""

from __future__ import annotations

from typing import Any, Dict, Sequence

import numpy as np
import pandas as pd

from pyblinker.blink_features._blink_metrics_shared import (
    ALL_METHODS,
    METHODS_BY_MODALITY,
    _method_keys,
    core_nan_dict,
    logger,
    normalize_modality,
)

KINEMATIC_METRIC_STEMS: Sequence[str] = (
    "vel_peak_abs",
    "vel_mean_abs",
    "slope_rise_pos",
    "slope_fall_neg",
    "acc_peak_abs",
    "acc_mean_abs",
    "amp_vel_ratio_base",
    "amp_vel_ratio_tent",
    "amp_vel_ratio_zero_to_max",
    "blink_velocity",
    "inter_blink_max_vel",
)

KINEMATIC_METRICS_NO_STYLE: Sequence[str] = (
    "amp_vel_ratio_base",
    "amp_vel_ratio_tent",
    "amp_vel_ratio_zero_to_max",
    "blink_velocity",
    "inter_blink_max_vel",
)


def compute_blink_velocity(candidate_signal: np.ndarray) -> np.ndarray:
    """Compute blink velocity as the first derivative of the raw signal."""

    return np.diff(candidate_signal)


def _compute_amp_vel_ratio_for_blink(
    candidate_signal: np.ndarray,
    blink_velocity: np.ndarray,
    srate: float,
    *,
    start_idx: int,
    end_idx: int,
    max_blink_idx: int,
    aggregator: str = "max",
) -> tuple[float, int | None]:
    max_vel_idx = blink_velocity.size - 1
    start_idx = max(0, min(start_idx, max_vel_idx))
    end_idx = max(0, min(end_idx, max_vel_idx))
    if end_idx < start_idx:
        return float("nan"), None

    indices = np.arange(start_idx, end_idx + 1, dtype=int)
    if indices.size == 0:
        return float("nan"), None

    velocities = blink_velocity[indices]
    if velocities.size == 0:
        return float("nan"), None

    if aggregator == "max":
        local_idx = int(np.argmax(velocities))
    else:
        local_idx = int(np.argmin(velocities))

    extreme_idx = int(indices[local_idx])
    extreme_vel = velocities[local_idx]
    ratio_val = 100 * abs(candidate_signal[max_blink_idx] / extreme_vel) / srate
    return float(ratio_val), extreme_idx


def compute_amp_vel_ratio_zero_to_max(
    df,
    candidate_signal: np.ndarray,
    blink_velocity: np.ndarray,
    srate: float,
    *,
    modality: str,
) -> None:
    """Compute zero-to-maximum amplitude-velocity ratios."""

    if modality == "ear":
        for idx in df.index:
            df.at[idx, "pos_amp_vel_ratio_zero"] = np.nan
            df.at[idx, "neg_amp_vel_ratio_zero"] = np.nan
            df.at[idx, "peaks_pos_vel_zero"] = np.nan
        return

    for idx, row in df.iterrows():
        pos_ratio, pos_idx = _compute_amp_vel_ratio_for_blink(
            candidate_signal,
            blink_velocity,
            srate,
            start_idx=int(row["left_zero"]),
            end_idx=int(row["max_blink"]),
            max_blink_idx=int(row["max_blink"]),
            aggregator="max",
        )
        df.at[idx, "pos_amp_vel_ratio_zero"] = pos_ratio
        df.at[idx, "peaks_pos_vel_zero"] = pos_idx

        neg_ratio, _ = _compute_amp_vel_ratio_for_blink(
            candidate_signal,
            blink_velocity,
            srate,
            start_idx=int(row["max_blink"]),
            end_idx=int(row["right_zero"]),
            max_blink_idx=int(row["max_blink"]),
            aggregator="min",
        )
        df.at[idx, "neg_amp_vel_ratio_zero"] = neg_ratio


def compute_amp_vel_ratio_base(
    df,
    candidate_signal: np.ndarray,
    blink_velocity: np.ndarray,
    srate: float,
) -> None:
    """Compute base-to-maximum amplitude-velocity ratios."""

    # Drop rows with NaN boundary indices before starting to avoid crash in int()
    required_initial = ["max_blink", "left_base", "right_base"]
    df.dropna(subset=required_initial, inplace=True)

    for idx, row in df.iterrows():
        pos_ratio, pos_idx = _compute_amp_vel_ratio_for_blink(
            candidate_signal,
            blink_velocity,
            srate,
            start_idx=int(row["left_base"]),
            end_idx=int(row["max_blink"]),
            max_blink_idx=int(row["max_blink"]),
            aggregator="max",
        )
        df.at[idx, "pos_amp_vel_ratio_base"] = pos_ratio
        df.at[idx, "peaks_pos_vel_base"] = pos_idx

        # Skip negative ratio if positive ratio calculation failed or peak index is NaN
        if pd.isna(pos_idx):
            continue

        neg_ratio, _ = _compute_amp_vel_ratio_for_blink(
            candidate_signal,
            blink_velocity,
            srate,
            start_idx=int(row["max_blink"]),
            end_idx=int(row["right_base"]),
            max_blink_idx=int(row["max_blink"]),
            aggregator="min",
        )
        df.at[idx, "neg_amp_vel_ratio_base"] = neg_ratio

    # Final cleanup: drop rows where any required boundary or index is NaN
    required_cols = ["max_blink", "left_base", "right_base", "peaks_pos_vel_base"]
    df.dropna(subset=required_cols, inplace=True)


def compute_amp_vel_ratio_tent(
    df,
    candidate_signal: np.ndarray,
    srate: float,
) -> None:
    """Compute tent-slope amplitude-velocity ratios."""

    for idx, row in df.iterrows():
        max_blink_idx = int(row["max_blink"])
        neg_ratio = (
            100
            * abs(candidate_signal[max_blink_idx] / row["aver_right_velocity"])
            / srate
        )
        pos_ratio = (
            100
            * abs(candidate_signal[max_blink_idx] / row["aver_left_velocity"])
            / srate
        )
        df.at[idx, "neg_amp_vel_ratio_tent"] = neg_ratio
        df.at[idx, "pos_amp_vel_ratio_tent"] = pos_ratio


def compute_inter_blink_max_vel(
    df,
    srate: float,
    *,
    modality: str,
    signal_len: int | None = None,
) -> None:
    """Compute inter-blink maximum velocity timing features."""

    del signal_len  # kept for backward-compatible signature

    for idx in df.index:
        row_pos = df.index.get_loc(idx)

        if row_pos == len(df) - 1:
            df.at[idx, "inter_blink_max_vel_base"] = np.nan
        else:
            df.at[idx, "inter_blink_max_vel_base"] = (
                df.at[idx, "peaks_pos_vel_base"] * -1
            ) / srate

        if modality == "ear":
            df.at[idx, "inter_blink_max_vel_zero"] = np.nan
            continue

        if row_pos == len(df) - 1:
            df.at[idx, "inter_blink_max_vel_zero"] = np.nan
        else:
            df.at[idx, "inter_blink_max_vel_zero"] = (
                df.at[idx, "peaks_pos_vel_zero"] * -1
            ) / srate


def compute_blink_kinematic_properties(
    df,
    candidate_signal: np.ndarray,
    srate: float,
    *,
    modality: str | None = None,
    fitted: bool = True,
) -> Any:
    """Compute per-blink kinematic properties used by BlinkProperties."""

    modality_key = normalize_modality(modality)
    blink_velocity = compute_blink_velocity(candidate_signal)

    compute_amp_vel_ratio_zero_to_max(
        df,
        candidate_signal,
        blink_velocity,
        srate,
        modality=modality_key,
    )
    compute_amp_vel_ratio_base(df, candidate_signal, blink_velocity, srate)
    if fitted:
        compute_amp_vel_ratio_tent(df, candidate_signal, srate)
    compute_inter_blink_max_vel(
        df,
        srate,
        modality=modality_key,
        signal_len=len(candidate_signal),
    )
    return df


def compute_blink_kinematic_metrics(
    segment: np.ndarray,
    sfreq: float,
    *,
    start_end_method: str,
    modality: str,
    include_second_derivative: bool = True,
    dx1: np.ndarray | None = None,
    dx2: np.ndarray | None = None,
) -> Dict[str, float]:
    """Compute kinematic metrics for a segmented blink waveform."""

    method = start_end_method
    modality_key = modality.lower()
    if modality_key not in METHODS_BY_MODALITY:
        raise ValueError(f"Unsupported modality '{modality}'")

    keys = _method_keys(method, KINEMATIC_METRIC_STEMS)
    if method in ALL_METHODS and method not in METHODS_BY_MODALITY[modality_key]:
        return core_nan_dict(keys)

    if sfreq <= 0:
        logger.warning("Non-positive sampling frequency %s; returning NaNs", sfreq)
        return core_nan_dict(keys)

    seg = np.asarray(segment, dtype=float).reshape(-1)
    if seg.size == 0:
        logger.debug("Empty blink segment provided for method '%s'", method)
        return core_nan_dict(keys)

    velocity = (
        np.diff(seg) * sfreq
        if dx1 is None
        else np.asarray(dx1, dtype=float).reshape(-1)
    )
    if velocity.size == 0:
        vel_peak_abs = float("nan")
        vel_mean_abs = float("nan")
        slope_rise_pos = float("nan")
        slope_fall_neg = float("nan")
    else:
        abs_vel = np.abs(velocity)
        vel_peak_abs = float(np.max(abs_vel))
        vel_mean_abs = float(np.mean(abs_vel))
        slope_rise_pos = float(np.max(velocity))
        slope_fall_neg = float(np.min(velocity))

    if velocity.size == 0 or seg.size == 0:
        blink_velocity = float("nan")
        amp_vel_ratio_base = float("nan")
        amp_vel_ratio_zero_to_max = float("nan")
        amp_vel_ratio_tent = float("nan")
        inter_blink_max_vel = float("nan")
    else:
        max_idx = int(np.argmax(seg))
        vel_end = velocity.size - 1
        blink_velocity = float(np.mean(np.abs(velocity)))

        def ratio_from_velocity(
            start_idx: int, end_idx: int, *, aggregator: str
        ) -> float:
            start_idx = max(0, start_idx)
            end_idx = min(end_idx, vel_end)
            if end_idx < start_idx:
                return float("nan")
            velocities = velocity[start_idx : end_idx + 1]
            if velocities.size == 0:
                return float("nan")
            local_idx = (
                int(np.argmax(velocities))
                if aggregator == "max"
                else int(np.argmin(velocities))
            )
            extreme_vel = velocities[local_idx]
            if extreme_vel == 0:
                return float("nan")
            return float(100 * abs(seg[max_idx] / extreme_vel) / sfreq)

        pos_ratio = ratio_from_velocity(0, max_idx, aggregator="max")
        neg_ratio = ratio_from_velocity(max_idx, seg.size - 1, aggregator="min")
        amp_vel_ratio_base = float(np.nanmean([pos_ratio, neg_ratio]))
        amp_vel_ratio_zero_to_max = float(np.nanmean([pos_ratio, neg_ratio]))

        left_vel = velocity[:max_idx]
        right_vel = velocity[max_idx:]
        left_mean = float(np.mean(left_vel)) if left_vel.size > 0 else float("nan")
        right_mean = float(np.mean(right_vel)) if right_vel.size > 0 else float("nan")
        tent_vals = []
        if left_mean != 0 and not np.isnan(left_mean):
            tent_vals.append(float(100 * abs(seg[max_idx] / left_mean) / sfreq))
        if right_mean != 0 and not np.isnan(right_mean):
            tent_vals.append(float(100 * abs(seg[max_idx] / right_mean) / sfreq))
        amp_vel_ratio_tent = float(np.nanmean(tent_vals)) if tent_vals else float("nan")

        pos_peak_idx = int(np.argmax(velocity))
        inter_blink_max_vel = float((pos_peak_idx * -1) / sfreq)

    if include_second_derivative:
        if dx2 is not None:
            acceleration = np.asarray(dx2, dtype=float).reshape(-1)
        elif velocity.size > 1:
            acceleration = np.diff(velocity) * sfreq
        else:
            acceleration = np.asarray([], dtype=float)

        if acceleration.size > 0:
            abs_acc = np.abs(acceleration)
            acc_peak_abs = float(np.max(abs_acc))
            acc_mean_abs = float(np.mean(abs_acc))
        else:
            acc_peak_abs = float("nan")
            acc_mean_abs = float("nan")
    else:
        acc_peak_abs = float("nan")
        acc_mean_abs = float("nan")

    return {
        f"vel_peak_abs_{method}": vel_peak_abs,
        f"vel_mean_abs_{method}": vel_mean_abs,
        f"slope_rise_pos_{method}": slope_rise_pos,
        f"slope_fall_neg_{method}": slope_fall_neg,
        f"acc_peak_abs_{method}": acc_peak_abs,
        f"acc_mean_abs_{method}": acc_mean_abs,
        f"amp_vel_ratio_base_{method}": amp_vel_ratio_base,
        f"amp_vel_ratio_tent_{method}": amp_vel_ratio_tent,
        f"amp_vel_ratio_zero_to_max_{method}": amp_vel_ratio_zero_to_max,
        f"blink_velocity_{method}": blink_velocity,
        f"inter_blink_max_vel_{method}": inter_blink_max_vel,
    }


__all__ = [
    "compute_amp_vel_ratio_base",
    "compute_amp_vel_ratio_tent",
    "compute_amp_vel_ratio_zero_to_max",
    "compute_blink_kinematic_metrics",
    "compute_blink_kinematic_properties",
    "compute_blink_velocity",
    "compute_inter_blink_max_vel",
    "KINEMATIC_METRICS_NO_STYLE",
]
