import numpy as np
import pandas as pd
from tqdm import tqdm

from ..fitutils import mad
from .default_setting import SCALING_FACTOR


def _compute_basic_statistics(
    params: dict,
    blink_component: np.ndarray,
) -> tuple[float, float]:
    """Return MATLAB-equivalent thresholding statistics."""

    mean_value = float(np.mean(blink_component, dtype=np.float64))
    robust_std = float(SCALING_FACTOR * mad(blink_component))
    min_blink_frames = float(params["min_event_len"] * params["sfreq"])
    threshold = float(mean_value + params["std_threshold"] * robust_std)
    return min_blink_frames, threshold


def _scan_threshold_crossings(
    blink_component: np.ndarray,
    threshold: float,
    min_blink_frames: float,
    *,
    progress_bar: bool,
    channel_name: str | None,
) -> tuple[np.ndarray, np.ndarray]:
    """Collect candidate blink onsets/offsets using MATLAB loop semantics."""

    in_blink = False
    start = 0
    start_blinks: list[int] = []
    end_blinks: list[int] = []

    for idx in tqdm(
        range(blink_component.size),
        desc=f"Get blink start and end for channel {channel_name}",
        disable=not progress_bar,
    ):
        value = blink_component[idx]
        if (not in_blink) and (value > threshold):
            start = idx
            in_blink = True

        if in_blink and (value < threshold):
            if (idx - start) > min_blink_frames:
                start_blinks.append(start)
                end_blinks.append(idx)
            in_blink = False

    return np.asarray(start_blinks, dtype=int), np.asarray(end_blinks, dtype=int)


def apply_minimum_separation(
    start_blinks: np.ndarray,
    end_blinks: np.ndarray,
    *,
    sfreq: float,
    min_event_sep: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Remove adjacent blinks that are closer than MATLAB's minEventSep."""

    if end_blinks.size == 0:
        return start_blinks, end_blinks

    position_mask = np.ones(end_blinks.size, dtype=bool)
    delta = (start_blinks[1:] - end_blinks[:-1]) / sfreq
    too_close = np.flatnonzero(delta <= min_event_sep)
    position_mask[too_close] = False
    position_mask[too_close + 1] = False
    return start_blinks[position_mask], end_blinks[position_mask]


def get_blink_position_with_threshold(
    params,
    *,
    blink_component=None,
    threshold: float,
    ch=None,
    progress_bar: bool = True,
    min_blink_frames: float | None = None,
):
    """Detect blink start and end frames using an explicit threshold."""

    assert blink_component.ndim == 1, "blink_component must be a 1D array"

    if min_blink_frames is None:
        min_blink_frames = float(params["min_event_len"] * params["sfreq"])

    start_blinks, end_blinks = _scan_threshold_crossings(
        blink_component,
        float(threshold),
        float(min_blink_frames),
        progress_bar=progress_bar,
        channel_name=ch,
    )

    if start_blinks.size == 0:
        return pd.DataFrame({"start_blink": [], "end_blink": []})

    min_event_sep = float(params.get("min_event_sep", params["min_event_len"]))
    start_blinks, end_blinks = apply_minimum_separation(
        start_blinks,
        end_blinks,
        sfreq=params["sfreq"],
        min_event_sep=min_event_sep,
    )

    return pd.DataFrame(
        {
            "start_blink": start_blinks,
            "end_blink": end_blinks,
        }
    )


def get_blink_position(
    params,
    blink_component=None,
    ch=None,
    *,
    progress_bar: bool = True,
):
    """Detect blink start and end frames using the legacy MATLAB Blinker approach."""

    min_blink_frames, threshold = _compute_basic_statistics(params, blink_component)
    return get_blink_position_with_threshold(
        params,
        blink_component=blink_component,
        threshold=threshold,
        ch=ch,
        progress_bar=progress_bar,
        min_blink_frames=min_blink_frames,
    )

def scan_threshold_crossings_kleifges(
        blink_component: np.ndarray,
        threshold: float,
        min_blink_frames: float,
        *,
        progress_bar: bool,
        channel_name: str | None,
        ) -> tuple[np.ndarray, np.ndarray]:
    """Approach use by kleifges 2017
	Collect candidate blink onsets/offsets using MATLAB loop semantics."""

    in_blink = False
    start = 0
    start_blinks: list[int] = []
    end_blinks: list[int] = []

    for idx in tqdm(
            range(blink_component.size),
            desc=f"Get blink start and end for channel {channel_name}",
            disable=not progress_bar,
            ):
        value = blink_component[idx]
        if (not in_blink) and (value > threshold):
            start = idx
            in_blink = True

        if in_blink and (value < threshold):
            if (idx - start) > min_blink_frames:
                start_blinks.append(start)
                end_blinks.append(idx)
            in_blink = False

    return np.asarray(start_blinks, dtype=int), np.asarray(end_blinks, dtype=int)