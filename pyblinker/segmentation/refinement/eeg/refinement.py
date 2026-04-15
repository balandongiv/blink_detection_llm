"""EEG/EOG blink refinement helpers."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

import mne
import numpy as np
import pandas as pd

from pyblinker.blinker.default_setting import DEFAULT_PARAMS
from pyblinker.segmentation.geometry import (
    compute_fit_range,
    create_left_right_base,
    get_half_height,
    get_max_blink,
    left_right_zero_crossing,
    lines_intersection,
)

from .bounds import compute_outer_bounds


def refine_local_maximum_stub(
    signal_segment: np.ndarray,
    start_rel: int,
    end_rel: int,
    peak_rel_cvat: int | None = None,
) -> Tuple[int, int, int]:
    """Return a crude refinement for local maxima in a signal segment."""

    n = len(signal_segment)
    if n == 0:
        return 0, 0, 0

    rs_stub = max(0, min(start_rel, n - 1))
    re_stub = max(0, min(end_rel, n - 1))
    if rs_stub > re_stub:
        rs_stub = re_stub = min(rs_stub, re_stub)

    if peak_rel_cvat is not None and rs_stub <= peak_rel_cvat <= re_stub:
        valid_peak = peak_rel_cvat
    else:
        segment = signal_segment[rs_stub : re_stub + 1]
        max_idx_local = int(np.argmax(segment))
        valid_peak = rs_stub + max_idx_local

    return rs_stub, valid_peak, re_stub


def _append_peak_refinements(
    row_data: Dict[str, Any],
    segment: np.ndarray,
    blink_starts: Sequence[int],
    blink_ends: Sequence[int],
    sfreq: float,
    modality: str,
    n_samp_epoch: int,
    modality_config: Dict[str, Any] | None = None,
) -> None:
    if segment.size == 0 or not blink_starts:
        return

    peaks: List[int] = []
    blink_entries: List[Dict[str, Any]] = []
    for start, end in zip(blink_starts, blink_ends):
        refined_start, peak, refined_end = refine_local_maximum_stub(
            segment, start, end, peak_rel_cvat=None
        )
        peaks.append(int(peak))
        blink_entries.append(
            {
                f"start__refine__{modality}": refined_start,
                f"end__refine__{modality}": refined_end,
            }
        )

    if not blink_entries:
        return

    seg_type = (modality_config or {}).get("seg_type")
    compute_outer = False
    if isinstance(seg_type, str):
        compute_outer = seg_type
    elif isinstance(seg_type, Sequence) and not isinstance(seg_type, str):
        compute_outer = "outer" in seg_type

    if compute_outer:
        bounds = compute_outer_bounds(peaks, n_samp_epoch)
        blink_data: dict[str, Any]
        for blink_data, (outer_start, outer_end) in zip(blink_entries, bounds):
            blink_data[f"start__outer__{modality}"] = outer_start
            blink_data[f"end__outer__{modality}"] = outer_end

    keys = blink_entries[0].keys()
    transposed = {key: [entry[key] for entry in blink_entries] for key in keys}
    row_data.update(transposed)

    base_fraction = float(
        (modality_config or {}).get("base_fraction", DEFAULT_PARAMS["base_fraction"])
    )

    # TODO: Do not use the blink_start and blink_end indices since this can be from manual annotatioons. Consider to use the refined start and end indices instead for computing landmarks, or at least make this configurable.refined_start and refined_end
    landmarks = _compute_epoch_landmarks(
        segment=segment,
        blink_starts=blink_starts,
        blink_ends=blink_ends,
        n_samp_epoch=n_samp_epoch,
        modality=modality,
        base_fraction=base_fraction,
    )
    row_data.update(landmarks)


def _compute_epoch_landmarks(
    *,
    segment: np.ndarray,
    blink_starts: Sequence[int],
    blink_ends: Sequence[int],
    n_samp_epoch: int,
    modality: str,
    base_fraction: float,
) -> Dict[str, List[float]]:
    n_blinks = len(blink_starts)
    landmark_columns = [
        f"start__left_base__{modality}",
        f"end__right_base__{modality}",
        f"start__left_zero__{modality}",
        f"end__right_zero__{modality}",
        f"start__left_x_intercept__{modality}",
        f"end__right_x_intercept__{modality}",
        f"start__left_base_half_height__{modality}",
        f"end__right_base_half_height__{modality}",
        f"start__left_zero_half_height__{modality}",
        f"end__right_zero_half_height__{modality}",
        f"x_intersect__{modality}",
        f"y_intersect__{modality}",
    ]

    results: Dict[str, List[float]] = {
        col: [float("nan")] * n_blinks for col in landmark_columns
    }
    if n_blinks == 0 or segment.size == 0:
        return results

    max_blinks: List[int] = []
    for start, end in zip(blink_starts, blink_ends):
        _, max_blink = get_max_blink(segment, start, end)
        max_blinks.append(int(max_blink))

    outer_bounds = compute_outer_bounds(max_blinks, n_samp_epoch)
    df = pd.DataFrame(
        {
            "blink_index": np.arange(n_blinks, dtype=int),
            "start_blink": blink_starts,
            "end_blink": blink_ends,
            "max_blink": max_blinks,
            "outer_start": [bounds[0] for bounds in outer_bounds],
            "outer_end": [bounds[1] for bounds in outer_bounds],
        }
    )

    df[["left_zero", "right_zero"]] = df.apply(
        lambda row: left_right_zero_crossing(
            segment,
            row["max_blink"],
            row["outer_start"],
            row["outer_end"],
            signal_type=modality,
        ),
        axis=1,
        result_type="expand",
    )

    for row in df.itertuples():
        idx = int(row.blink_index)
        results[f"start__left_zero__{modality}"][idx] = float(row.left_zero)
        results[f"end__right_zero__{modality}"][idx] = float(row.right_zero)

    try:
        df_base = create_left_right_base(segment, df)
    except ValueError:
        return results

    for row in df_base.itertuples():
        idx = int(row.blink_index)
        results[f"start__left_base__{modality}"][idx] = float(row.left_base)
        results[f"end__right_base__{modality}"][idx] = float(row.right_base)

        (
            left_zero_half_height,
            right_zero_half_height,
            left_base_half_height,
            right_base_half_height,
        ) = get_half_height(
            segment,
            row.max_blink,
            row.left_zero,
            row.right_zero,
            row.left_base,
            row.outer_end,
        )

        results[f"start__left_base_half_height__{modality}"][idx] = float(
            left_base_half_height
        )
        results[f"end__right_base_half_height__{modality}"][idx] = float(
            right_base_half_height
        )
        results[f"start__left_zero_half_height__{modality}"][idx] = float(
            left_zero_half_height
        )
        results[f"end__right_zero_half_height__{modality}"][idx] = float(
            right_zero_half_height
        )

        if int(row.left_zero) >= int(row.max_blink) or int(row.right_zero) <= int(
            row.max_blink
        ):
            continue

        try:
            x_left, x_right, *_ = compute_fit_range(
                segment,
                row.max_blink,
                row.left_zero,
                row.right_zero,
                base_fraction,
                top_bottom=True,
            )
        except (IndexError, ValueError):
            continue

        if (
            isinstance(x_left, np.ndarray)
            and isinstance(x_right, np.ndarray)
            and x_left.size > 1
            and x_right.size > 1
        ):
            (
                _left_slope,
                _right_slope,
                _aver_left_velocity,
                _aver_right_velocity,
                _right_r2,
                _left_r2,
                x_intersect,
                y_intersect,
                left_x_intercept,
                right_x_intercept,
            ) = lines_intersection(signal=segment, x_right=x_right, x_left=x_left)

            results[f"start__left_x_intercept__{modality}"][idx] = float(
                left_x_intercept
            )
            results[f"end__right_x_intercept__{modality}"][idx] = float(
                right_x_intercept
            )
            results[f"x_intersect__{modality}"][idx] = float(x_intersect)
            results[f"y_intersect__{modality}"][idx] = float(y_intersect)

    return results


def refine_blinks_from_epochs(
    segments: Sequence[mne.io.BaseRaw],
    channel: str,
    *,
    local_max_prominence: float = 0.01,
    search_expansion_frames: int | None = None,
    value_threshold: float | None = None,
) -> List[Dict[str, Any]]:
    """Refine blink annotations within pre-sliced raw segments."""

    refined: List[Dict[str, Any]] = []
    if not segments:
        return refined

    sfreq = float(segments[0].info["sfreq"])
    if search_expansion_frames is None:
        search_expansion_frames = int(0.1 * sfreq)

    for epoch_index, segment in enumerate(segments):
        data = segment.get_data(picks=[channel])
        if data.size == 0:
            continue
        signal = data[0]
        ann = segment.annotations
        for ann_idx in range(len(ann)):
            onset = ann.onset[ann_idx]
            duration = ann.duration[ann_idx]
            start_rel = int(max(0, round(onset * sfreq) - search_expansion_frames))
            end_rel = int(round((onset + duration) * sfreq) + search_expansion_frames)
            end_rel = min(end_rel, len(signal) - 1)
            if end_rel < start_rel:
                end_rel = start_rel
            rs, peak, re = refine_local_maximum_stub(
                signal, start_rel, end_rel, peak_rel_cvat=None
            )
            refined.append(
                {
                    "epoch_index": epoch_index,
                    "refined_start_frame": rs,
                    "refined_peak_frame": peak,
                    "refined_end_frame": re,
                    "epoch_signal": signal,
                }
            )

    return refined


__all__ = [
    "_append_peak_refinements",
    "refine_local_maximum_stub",
    "refine_blinks_from_epochs",
]
