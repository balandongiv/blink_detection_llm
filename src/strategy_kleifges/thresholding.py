import numpy as np
import pandas as pd
from tqdm import tqdm

from ..fitutils import mad



def compute_basic_statistics(
		params: dict,
		blink_component: np.ndarray,
		) -> tuple[float, float]:
	"""Return MATLAB-equivalent thresholding statistics."""
	SCALING_FACTOR = 1.4826  # From original paper: by default, BLINKER eliminates
	mean_value = float(np.mean(blink_component, dtype=np.float64))
	robust_std = float(SCALING_FACTOR * mad(blink_component))
	min_blink_frames = float(params["min_event_len"] * params["sfreq"])
	threshold = float(mean_value + params["std_threshold"] * robust_std)
	return min_blink_frames, threshold


def scan_threshold_crossings(
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




