"""Module B: Long-closure detector for sustained eye closures ≥ 500 ms.

After 1–20 Hz bandpass filtering a long eye closure appears as two short
blink-like spikes (onset + offset) surrounding a QUIET PLATEAU where the
DC shift is filtered away.  Module B finds these quiet plateaus via a
suppression test on the rectified RMS envelope and pads each detection to
capture the flanking onset/offset spikes.

Algorithm
---------
1. Sliding RMS envelope  (50 ms window) → E[t]
2. Rolling mean baseline (10 s window)  → B[t]
3. Suppression mask: E[t] < alpha * B[t]
4. Fill short gaps (debounce_ms) in the mask
5. Keep regions lasting ≥ suppress_min_s
6. Pad each region by pad_s on each side to include onset/offset spikes
7. Filter: min_duration_s ≤ event duration ≤ max_duration_s
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.ndimage import uniform_filter1d


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sliding_rms(signal: np.ndarray, window_samples: int) -> np.ndarray:
    """Sliding RMS via uniform_filter1d on squared signal."""
    w = max(1, int(window_samples))
    smoothed = uniform_filter1d(np.square(signal, dtype=np.float64), size=w, mode="reflect")
    return np.sqrt(np.maximum(smoothed, 0.0))


def _rolling_mean(arr: np.ndarray, window_samples: int) -> np.ndarray:
    """Causal rolling mean; first window_samples positions use expanding window."""
    w = max(1, int(window_samples))
    return uniform_filter1d(arr, size=w, mode="reflect")


def _fill_short_gaps(mask: np.ndarray, max_gap: int) -> np.ndarray:
    """Fill False gaps of length ≤ max_gap inside a boolean array."""
    if max_gap <= 0:
        return mask.copy()
    filled = mask.copy()
    gap_start: int | None = None
    for i in range(len(mask)):
        if not mask[i]:
            if gap_start is None:
                gap_start = i
        else:
            if gap_start is not None:
                if (i - gap_start) <= max_gap:
                    filled[gap_start:i] = True
                gap_start = None
    return filled


def _contiguous_regions(mask: np.ndarray) -> list[tuple[int, int]]:
    """Return list of (start, end) sample pairs for contiguous True runs."""
    regions: list[tuple[int, int]] = []
    n = len(mask)
    in_region = False
    start = 0
    for i in range(n):
        if mask[i] and not in_region:
            in_region = True
            start = i
        elif not mask[i] and in_region:
            in_region = False
            regions.append((start, i))
    if in_region:
        regions.append((start, n))
    return regions


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_long_closures(
    signal: np.ndarray,
    sfreq: float,
    *,
    rms_window_ms: float = 50.0,
    baseline_window_s: float = 5.0,
    alpha: float = 0.3,
    debounce_ms: float = 150.0,
    suppress_min_s: float = 0.10,
    pad_s: float = 0.20,
    min_duration_s: float = 0.5,
    max_duration_s: float = 15.0,
    noise_floor: float = 1e-10,
) -> pd.DataFrame:
    """Detect long eye closures (≥ min_duration_s) in a filtered signal.

    Parameters
    ----------
    signal:
        1-D bandpass-filtered signal (concatenated valid epochs) for one channel.
    sfreq:
        Sampling frequency in Hz.
    rms_window_ms:
        Sliding RMS window width in ms (default 50 ms).
    baseline_window_s:
        Rolling mean baseline window in seconds (default 5 s — local window
        is more sensitive to the quiet plateau than a 10 s global average).
    alpha:
        Suppression ratio: flag when RMS < alpha × baseline (default 0.3 —
        validated on 5 Raja sessions; lower = more selective).
    debounce_ms:
        Maximum gap (ms) in the suppression mask to bridge (default 150 ms —
        bridges brief fluctuations within the long-closure plateau).
    suppress_min_s:
        Minimum suppression duration (s) to trigger a candidate (default 0.10 s).
        Shorter quiet periods are noise, not genuine closure plateaus.
    pad_s:
        Padding (s) added on each side to include the flanking onset/offset spikes.
    min_duration_s:
        Minimum final event duration in seconds (PERCLOS standard: 0.5 s).
    max_duration_s:
        Maximum final event duration in seconds (default 15 s — beyond is artefact).
    noise_floor:
        Minimum baseline value to prevent division-by-near-zero (default 1e-10).

    Returns
    -------
    pd.DataFrame
        Columns: ``start_blink``, ``end_blink``  (integer sample indices).
        Empty DataFrame with same columns when no events are found.
    """
    columns = ["start_blink", "end_blink"]
    sig = np.asarray(signal, dtype=np.float64).ravel()
    n = len(sig)
    if n == 0:
        return pd.DataFrame(columns=columns)

    fs = float(sfreq)
    rms_w   = max(1, int(round(rms_window_ms * fs / 1000.0)))
    base_w  = max(1, int(round(baseline_window_s * fs)))
    deb_w   = max(0, int(round(debounce_ms * fs / 1000.0)))
    sup_min = max(1, int(round(suppress_min_s * fs)))
    pad_smp = max(0, int(round(pad_s * fs)))
    min_smp = max(1, int(round(min_duration_s * fs)))
    max_smp = int(round(max_duration_s * fs))

    # 1. RMS envelope of rectified signal
    envelope = _sliding_rms(np.abs(sig), rms_w)

    # 2. Rolling mean baseline
    baseline = _rolling_mean(envelope, base_w)
    baseline = np.maximum(baseline, noise_floor)

    # 3. Suppression mask
    mask = envelope < (alpha * baseline)

    # 4. Debounce
    if deb_w > 0:
        mask = _fill_short_gaps(mask, deb_w)

    # 5. Find suppression regions ≥ suppress_min_s
    candidates = [
        (s, e) for s, e in _contiguous_regions(mask) if (e - s) >= sup_min
    ]
    if not candidates:
        return pd.DataFrame(columns=columns)

    # 6. Pad each suppression region to include onset/offset spikes
    events: list[tuple[int, int]] = []
    for s, e in candidates:
        ev_start = max(0, s - pad_smp)
        ev_end   = min(n, e + pad_smp)
        events.append((ev_start, ev_end))

    # 7. Merge overlapping padded events
    events.sort()
    merged: list[tuple[int, int]] = []
    cur_s, cur_e = events[0]
    for s, e in events[1:]:
        if s <= cur_e:
            cur_e = max(cur_e, e)
        else:
            merged.append((cur_s, cur_e))
            cur_s, cur_e = s, e
    merged.append((cur_s, cur_e))

    # 8. Filter by duration
    filtered = [(s, e) for s, e in merged if min_smp <= (e - s) <= max_smp]
    if not filtered:
        return pd.DataFrame(columns=columns)

    starts, ends = zip(*filtered)
    return pd.DataFrame({"start_blink": list(starts), "end_blink": list(ends)})


__all__ = ["detect_long_closures"]
