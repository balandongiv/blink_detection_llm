"""Strategy F core: two-stage threshold blink detection.

Stage A — Autoreject epoch-level screening identifies which epochs are suspicious.
Stage B — A robust median+MAD threshold is estimated from those flagged epochs.
Stage C — Blink regions are found via scan_threshold_crossings_kleifges using the
           Stage B threshold.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.blinker.get_blink_positions import scan_threshold_crossings_kleifges
from src.blinker.pyblinker import BlinkDetector
from src.common.epoch_channel import map_concatenated_blinks_to_epochs
from src.common.epoch_input import PreparedEpochDetectionInput
from src.common.pipeline_utils import build_epoch_boundaries, build_signal_by_epoch

from .autoreject_epoch_screener import screen_epochs_with_autoreject
from .blink_threshold import compute_flagged_epoch_threshold


def blink_position_strategy_f(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
    *,
    setting: dict | None = None,
    **kwargs,
) -> list[dict]:
    """Run Strategy F blink detection on each channel and return standard results.

    Parameters
    ----------
    prepared:
        Pre-processed epoch data.
    valid_epoch_indices:
        Indices of valid (non-dropped) epochs.
    setting:
        Optional configuration dict.  Supported keys:

        - ``autoreject_random_state`` (int, default 42)
        - ``std_threshold`` (float, default 3.5)
        - ``center_method`` (str, default ``"median"``) — ``"median"`` or ``"mean"``
        - ``min_flagged_epochs`` (int, default 1)
        - ``verbose`` (bool, default False)
        - ``k_confirm`` (float or None, default None) — if given, Stage D peak
          confirmation: each detected event is kept only if its peak amplitude
          satisfies ``peak >= center + k_confirm * dispersion``.  Decouples
          candidate generation (permissive, k=1.5) from acceptance (strict).
        - ``k_flagged`` (float or None, default None) — G3 mode: threshold
          multiplier for autoreject-flagged (blink-heavy) epochs.  Must be set
          together with ``k_nonflagged`` to activate per-epoch split scanning.
        - ``k_nonflagged`` (float or None, default None) — G3 mode: threshold
          multiplier for non-flagged (possibly quiet) epochs.  The threshold is
          estimated from ALL valid epochs (permissive baseline).
    **kwargs:
        Additional blink parameter overrides forwarded to BlinkDetector.

    Returns
    -------
    list of dict, one per channel, each with standard keys:
        ``channel``, ``df_positions``, ``mapped_candidates``, ``signal_by_epoch``
    and strategy-F diagnostic keys:
        ``flagged_valid_epoch_indices``, ``n_flagged``, ``used_all_epochs``,
        ``blink_region_threshold``, ``threshold_center``, ``threshold_dispersion``.
    """
    options = dict(setting or {})
    options.update(kwargs)

    autoreject_random_state = int(options.get("autoreject_random_state", 42))
    # std_threshold: multiplier for the MAD dispersion term in Stage B.
    # 1.5 matches Strategy A's original Kleifges/BLINKER detection multiplier,
    # giving recall that meets or exceeds Strategy A while keeping FP well
    # below A's level. (The old default of 3.5 was borrowed from BLINKER's
    # blink-quality classification context and was too conservative for detection.)
    std_threshold = float(options.get("std_threshold", 1.5))
    center_method = str(options.get("center_method", "median"))
    min_flagged_epochs = int(options.get("min_flagged_epochs", 1))
    verbose = bool(options.get("verbose", False))
    max_event_len = options.get("max_event_len", None)  # seconds; None = no cap
    k_confirm = options.get("k_confirm", None)  # float or None; if None, no confirmation step
    # G3: per-epoch split threshold.  Both keys must be present to activate.
    k_flagged    = options.get("k_flagged",    None)  # k for autoreject-flagged epochs
    k_nonflagged = options.get("k_nonflagged", None)  # k for non-flagged epochs
    use_epoch_split = k_flagged is not None and k_nonflagged is not None

    params = BlinkDetector._build_detector_params(None, {})
    params["sfreq"] = float(prepared.sfreq)
    sfreq = params["sfreq"]
    min_blink_frames = float(params["min_event_len"] * sfreq)
    max_blink_frames = float(max_event_len * sfreq) if max_event_len is not None else None

    # ------------------------------------------------------------------ Stage A
    screen_result = screen_epochs_with_autoreject(
        prepared,
        valid_epoch_indices,
        random_state=autoreject_random_state,
        min_flagged_epochs=min_flagged_epochs,
        verbose=verbose,
    )

    # ------------------------------------------------------------------ Stage B
    threshold_result = compute_flagged_epoch_threshold(
        prepared,
        valid_epoch_indices,
        screen_result.flagged_valid_epoch_indices,
        std_threshold=std_threshold,
        center_method=center_method,
        verbose=verbose,
    )

    epoch_boundaries = build_epoch_boundaries(
        len(valid_epoch_indices), prepared.epoch_length_samples
    )
    valid_indices = np.asarray(valid_epoch_indices, dtype=int)

    # ------------------------------------------------------------------ G3 pre-computation
    # Compute the two per-epoch-type thresholds once (outside channel loop).
    # thresh_g3_flagged  : from flagged epochs, k=k_flagged  (strict gate)
    # thresh_g3_nonflagged: from ALL valid epochs, k=k_nonflagged (permissive gate)
    if use_epoch_split:
        flagged_set = set(screen_result.flagged_valid_epoch_indices)
        thresh_g3_flagged = compute_flagged_epoch_threshold(
            prepared,
            valid_epoch_indices,
            screen_result.flagged_valid_epoch_indices,
            std_threshold=float(k_flagged),
            center_method=center_method,
            verbose=verbose,
        )
        thresh_g3_nonflagged = compute_flagged_epoch_threshold(
            prepared,
            valid_epoch_indices,
            [],  # empty → falls back to all valid epochs
            std_threshold=float(k_nonflagged),
            center_method=center_method,
            verbose=verbose,
        )

    # ------------------------------------------------------------------ Stage C
    results: list[dict] = []
    for channel_idx, channel_name in enumerate(prepared.channel_names):
        concatenated_signal = prepared.data[valid_indices, channel_idx, :].reshape(-1)

        if use_epoch_split:
            # G3: scan each epoch individually with its type-specific threshold.
            # Indices are shifted to the concatenated-signal frame of reference.
            start_list: list[int] = []
            end_list:   list[int] = []
            offset = 0
            for ep_global_idx in valid_epoch_indices:
                ep_signal = prepared.data[ep_global_idx, channel_idx, :]
                if ep_global_idx in flagged_set:
                    ep_thresh = float(thresh_g3_flagged.thresholds[channel_name])
                else:
                    ep_thresh = float(thresh_g3_nonflagged.thresholds[channel_name])
                ep_starts, ep_ends = scan_threshold_crossings_kleifges(
                    ep_signal,
                    ep_thresh,
                    min_blink_frames,
                    progress_bar=False,
                    channel_name=channel_name,
                )
                if len(ep_starts) > 0:
                    start_list.extend((ep_starts + offset).tolist())
                    end_list.extend((ep_ends   + offset).tolist())
                offset += prepared.epoch_length_samples
            start_blinks  = np.array(start_list, dtype=int)
            end_blinks    = np.array(end_list,   dtype=int)
            blink_threshold = float(thresh_g3_flagged.thresholds[channel_name])  # for diag
        else:
            blink_threshold = float(threshold_result.thresholds[channel_name])
            start_blinks, end_blinks = scan_threshold_crossings_kleifges(
                concatenated_signal,
                blink_threshold,
                min_blink_frames,
                progress_bar=False,
                channel_name=channel_name,
            )

        # --------------------------------------------------------- Stage D
        # Peak confirmation filter (only when k_confirm is set).
        # Each candidate event is kept only if its peak amplitude satisfies:
        #   peak >= center + k_confirm * dispersion
        # This decouples permissive candidate generation (k=1.5) from strict
        # acceptance without introducing new statistics.
        if k_confirm is not None and len(start_blinks) > 0:
            center_val     = float(threshold_result.centers[channel_name])
            dispersion_val = float(threshold_result.dispersions[channel_name])
            confirm_level  = center_val + float(k_confirm) * dispersion_val
            keep_mask = np.array(
                [
                    float(concatenated_signal[s:e].max()) >= confirm_level
                    for s, e in zip(start_blinks, end_blinks)
                ],
                dtype=bool,
            )
            start_blinks = start_blinks[keep_mask]
            end_blinks   = end_blinks[keep_mask]

        # Optional: discard events longer than max_blink_frames (removes slow
        # drifts and muscle artifacts that are not physiological blinks).
        if max_blink_frames is not None and len(start_blinks) > 0:
            durations = end_blinks - start_blinks
            keep = durations <= max_blink_frames
            start_blinks = start_blinks[keep]
            end_blinks = end_blinks[keep]

        df_positions = pd.DataFrame({"start_blink": start_blinks, "end_blink": end_blinks})
        mapped_candidates = map_concatenated_blinks_to_epochs(
            df_positions,
            channel=channel_name,
            valid_epoch_indices=valid_epoch_indices,
            epoch_boundaries=epoch_boundaries,
            sfreq=prepared.sfreq,
        )

        results.append(
            {
                "channel": channel_name,
                "df_positions": df_positions,
                "mapped_candidates": mapped_candidates,
                "signal_by_epoch": build_signal_by_epoch(prepared, channel_idx),
                "flagged_valid_epoch_indices": screen_result.flagged_valid_epoch_indices,
                "n_flagged": screen_result.n_flagged,
                "used_all_epochs": threshold_result.used_all_epochs,
                "blink_region_threshold": blink_threshold,
                "threshold_center": float(threshold_result.centers[channel_name]),
                "threshold_dispersion": float(threshold_result.dispersions[channel_name]),
                "k_confirm": k_confirm,
                "k_flagged": k_flagged,
                "k_nonflagged": k_nonflagged,
            }
        )
    return results


__all__ = ["blink_position_strategy_f"]
