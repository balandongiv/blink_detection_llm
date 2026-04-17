"""Stage B: Per-channel blink region threshold from flagged epochs.

Computes a robust sample-level threshold using median + k * MAD,
estimated from the epochs flagged as suspicious in Stage A.
When no flagged epochs exist the computation uses all valid epochs.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from pyblinker.common.epoch_input import PreparedEpochDetectionInput
from pyblinker.fitutils import mad

SCALING_FACTOR = 1.4826  # normalises MAD to be consistent with std for Gaussian data


def compute_flagged_epoch_threshold(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
    flagged_valid_epoch_indices: list[int],
    *,
    std_threshold: float = 3.5,
    verbose: bool = False,
) -> SimpleNamespace:
    """Compute per-channel thresholds from flagged epochs (Stage B).

    Parameters
    ----------
    prepared:
        Pre-processed epoch data.
    valid_epoch_indices:
        Indices of all valid (non-dropped) epochs.
    flagged_valid_epoch_indices:
        Original epoch indices identified as suspicious in Stage A.
        When empty, all valid epochs are used instead.
    std_threshold:
        Multiplier ``k`` applied to the MAD dispersion term.

    Returns
    -------
    SimpleNamespace with fields:
        - ``thresholds``: dict mapping channel_name -> threshold float
        - ``centers``: dict mapping channel_name -> median float
        - ``dispersions``: dict mapping channel_name -> robust_std float
        - ``n_flagged_epochs``: number of flagged epochs used
        - ``n_total_valid``: total number of valid epochs
        - ``used_all_epochs``: True when all valid epochs were used (no flagged epochs)
    """
    channel_names = tuple(prepared.channel_names)

    if flagged_valid_epoch_indices:
        source_indices = np.asarray(flagged_valid_epoch_indices, dtype=int)
        used_all_epochs = False
        if verbose:
            print(
                f"[Stage B] using {len(flagged_valid_epoch_indices)} flagged epoch(s) "
                f"for threshold (indices: {flagged_valid_epoch_indices})"
            )
    else:
        source_indices = np.asarray(valid_epoch_indices, dtype=int)
        used_all_epochs = True
        if verbose:
            print(
                f"[Stage B] no flagged epochs — using all {len(valid_epoch_indices)} "
                f"valid epoch(s) for threshold"
            )

    thresholds: dict[str, float] = {}
    centers: dict[str, float] = {}
    dispersions: dict[str, float] = {}

    for channel_idx, channel_name in enumerate(channel_names):
        samples = prepared.data[source_indices, channel_idx, :].reshape(-1)
        center = float(np.median(samples))
        dispersion = float(SCALING_FACTOR * mad(samples))
        thresholds[channel_name] = center + float(std_threshold) * dispersion
        centers[channel_name] = center
        dispersions[channel_name] = dispersion

    if verbose:
        lines = "\n".join(
            f"  {ch}: threshold={thresholds[ch]:.6f}  center={centers[ch]:.6f}"
            f"  dispersion={dispersions[ch]:.6f}"
            for ch in channel_names
        )
        print(f"[Stage B] per-channel thresholds (center + {std_threshold} * 1.4826*MAD):\n{lines}")

    return SimpleNamespace(
        thresholds=thresholds,
        centers=centers,
        dispersions=dispersions,
        n_flagged_epochs=len(flagged_valid_epoch_indices),
        n_total_valid=len(valid_epoch_indices),
        used_all_epochs=used_all_epochs,
    )


__all__ = ["compute_flagged_epoch_threshold"]
