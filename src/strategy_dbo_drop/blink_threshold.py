"""Stage B: Per-channel blink region threshold from flagged epochs.

Computes a robust sample-level threshold using median + k * MAD,
estimated from the epochs flagged as suspicious in Stage A.
When no flagged epochs exist the computation uses all valid epochs.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from src.common.epoch_input import PreparedEpochDetectionInput
from pyblinker.fitutils import mad


_SUPPORTED_CENTER_METHODS = ("median", "mean")


def compute_threshold_from_samples(
    samples: np.ndarray,
    std_threshold: float,
    *,
    center_method: str = "median",
    scaling_factor: float = 1.4826, # This value is the same as what use in matlab-blinker
) -> tuple[float, float, float]:
    """Compute robust threshold statistics from a 1D sample array.

    Both strategies compute a threshold as::

        threshold = center + std_threshold * dispersion

    where ``dispersion = 1.4826 * MAD(samples)`` in both cases.
    The only difference is how the **center** is calculated.

    Parameters
    ----------
    samples:
        1D array of signal amplitude samples from the flagged (or all valid)
        epochs for a single channel.
    std_threshold:
        Multiplier ``k`` applied to the MAD dispersion term.  Typical value
        is 3.5 (i.e. the threshold is set 3.5 robust-standard-deviations above
        the center).
    center_method:
        Strategy for computing the center value.  Allowed values:

        ``"median"`` (default)
            Uses ``np.median(samples)``.  The median is largely unaffected by
            large blink peaks because it depends only on the rank of the values,
            not their magnitude.  Combined with MAD (which is also rank-based)
            this yields a threshold that is **stable and robust** even when the
            flagged epochs contain extreme outliers.  Recommended when
            robustness is more important than strict sensitivity.

        ``"mean"``
            Uses ``np.mean(samples, dtype=np.float64)``.  The arithmetic mean
            is pulled upward by large blink peaks; on blink-heavy flagged data
            the center is therefore higher than the median, which in turn raises
            the threshold.  This makes the detector **more conservative**
            (fewer, larger detections).  Useful when comparing against older
            MATLAB-like behaviour or as an upper-bound experiment.

    Returns
    -------
    center : float
        The central tendency of the sample distribution (median or mean).
    dispersion : float
        Robust standard deviation estimate: ``1.4826 * MAD(samples)``.
    threshold : float
        ``center + std_threshold * dispersion``.

    Raises
    ------
    ValueError
        If ``center_method`` is not one of the supported values.

    Notes
    -----
    Why ``1.4826 * MAD``?
        For a normal distribution ``MAD ≈ 0.6745 * std``, so multiplying by
        ``1/0.6745 ≈ 1.4826`` normalises MAD to the same scale as the standard
        deviation.  This mirrors the BLINKER paper convention.

    Why prefer median over mean?
        Flagged epochs are selected *because* they contain blink-like events.
        Their amplitude distribution is therefore right-skewed.  The mean is
        sensitive to this skew and systematically overestimates the central
        level, which raises the threshold and may cause the detector to miss
        smaller blinks.  The median is unaffected by the skew and gives a more
        representative center.

    Why might mean be useful?
        When comparing results against an older pipeline that used mean-based
        thresholds, or when you want a deliberately conservative detector that
        only captures the most prominent blink events.
    """
    if center_method not in _SUPPORTED_CENTER_METHODS:
        raise ValueError(
            f"center_method={center_method!r} is not supported. "
            f"Choose one of {_SUPPORTED_CENTER_METHODS}."
        )

    if center_method == "median":
        center = float(np.median(samples))
    else:  # "mean"
        center = float(np.mean(samples, dtype=np.float64))

    dispersion = float(scaling_factor * mad(samples)) # Other name of dispersion is robust_std
    threshold = center + float(std_threshold) * dispersion
    return center, dispersion, threshold


def compute_flagged_epoch_threshold(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
    flagged_valid_epoch_indices: list[int],
    *,
    std_threshold: float = 3.0,
    center_method: str = "median",
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
    center_method:
        Strategy for computing the center of the sample distribution.
        ``"median"`` (default) or ``"mean"``.  See
        :func:`compute_threshold_from_samples` for details.
    verbose:
        When True, print diagnostic information about which epochs and
        thresholds were used.

    Returns
    -------
    SimpleNamespace with fields:
        - ``thresholds``: dict mapping channel_name -> threshold float
        - ``centers``: dict mapping channel_name -> center float
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
        center, dispersion, threshold = compute_threshold_from_samples(
            samples,
            std_threshold,
            center_method=center_method,
        )
        thresholds[channel_name] = threshold
        centers[channel_name] = center
        dispersions[channel_name] = dispersion

    if verbose:
        lines = "\n".join(
            f"  {ch}: threshold={thresholds[ch]:.6f}  center={centers[ch]:.6f}"
            f"  dispersion={dispersions[ch]:.6f}"
            for ch in channel_names
        )
        print(
            f"[Stage B] per-channel thresholds "
            f"(center_method={center_method!r}, {std_threshold} * 1.4826*MAD):\n{lines}"
        )

    return SimpleNamespace(
        thresholds=thresholds,
        centers=centers,
        dispersions=dispersions,
        n_flagged_epochs=len(flagged_valid_epoch_indices),
        n_total_valid=len(valid_epoch_indices),
        used_all_epochs=used_all_epochs,
    )


__all__ = ["compute_threshold_from_samples", "compute_flagged_epoch_threshold"]
