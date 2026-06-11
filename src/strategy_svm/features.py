"""Feature extraction for SVM-based blink classification.

For each candidate event [start, end] in a 1-D filtered signal, extracts
a 22-element feature vector:

  Duration   (2)  — primary discriminator (short = normal, long = closure)
  Amplitude  (3)  — peak, fill factor (mean/peak), SNR
  Shape      (9)  — symmetry, slopes, recovery ratios, plateau flatness, pAVR,
                    skewness, kurtosis
  Post-event (2)  — RMS ratios covering the 0-400 ms window after the event
  Context    (4)  — [NEW] 1 s pre/post-event RMS, local 5 s activity ratio,
                    combined duration × post-suppression discriminant
"""

from __future__ import annotations

import numpy as np
from scipy import stats

FEATURE_NAMES: list[str] = [
    # Duration (2)
    "duration_s",          # event end-start in seconds
    "log_dur_ms",          # log1p(duration_ms), linearises skewed distribution
    # Amplitude (3)
    "peak_amp",            # max |signal| within event
    "fill_factor",         # mean|event| / peak_amp  (1=plateau, 0=pure spike)
    "snr",                 # peak_amp / pre-event baseline RMS
    # Shape (9)
    "symmetry",            # time_to_peak / duration  (0.5 = symmetric blink)
    "rise_slope",          # (peak - amp@100ms before peak) / 0.1 s
    "fall_slope_100ms",    # (peak - amp@100ms after peak) / 0.1 s
    "fall_slope_400ms",    # (peak - amp@400ms after peak) / 0.4 s
    "recovery_100ms",      # |signal[peak+100ms]| / peak_amp
    "recovery_200ms",      # |signal[peak+200ms]| / peak_amp
    "recovery_400ms",      # |signal[peak+400ms]| / peak_amp
    "plateau_cv",          # CV of middle 50% of event (low = flat plateau = long closure)
    "pavr",                # peak / max |diff(signal)| * sfreq  (pAVR analogue)
    "skewness",            # temporal skewness of event waveform
    "kurtosis",            # excess kurtosis (low = flat, high = peaky)
    # Post-event (2)
    "post_rms_ratio",      # RMS(event_end to event_end+400ms) / baseline_rms
    "post_early_ratio",    # RMS(event_end+200ms to event_end+600ms) / baseline_rms
    # Context (4) — Recommendation #4
    "pre_rms_1s",          # RMS(1 s before event start) / baseline_rms
    "post_rms_1s",         # RMS(1 s after event end) / baseline_rms
                           #   low when long-closure plateau follows onset spike
    "local_activity",      # RMS(5 s neighbourhood centred on event) / baseline_rms
    "dur_post_product",    # duration_s * max(0, 1 - post_rms_1s/2)
                           #   high for long events followed by quiet = long closure
]

N_FEATURES = len(FEATURE_NAMES)   # 22


def _safe_rms(arr: np.ndarray) -> float:
    if len(arr) == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(arr))))


def _amplitude_at(signal: np.ndarray, sample: int) -> float:
    """Return |signal[sample]|, clipped to valid range."""
    idx = max(0, min(int(sample), len(signal) - 1))
    return float(abs(signal[idx]))


def extract_event_features(
    signal: np.ndarray,
    sfreq: float,
    start: int,
    end: int,
) -> np.ndarray:
    """Compute the 18-element feature vector for one candidate event.

    Parameters
    ----------
    signal:
        Full concatenated 1-D signal (one channel).
    sfreq:
        Sampling frequency in Hz.
    start, end:
        Sample indices (inclusive start, exclusive end) of the candidate event.

    Returns
    -------
    np.ndarray, shape (N_FEATURES,)
    """
    n = len(signal)
    start = max(0, int(start))
    end   = min(n, int(end))
    if end <= start:
        return np.zeros(N_FEATURES, dtype=np.float32)

    sfreq = float(sfreq)
    s100  = max(1, int(round(0.100 * sfreq)))
    s200  = max(1, int(round(0.200 * sfreq)))
    s400  = max(1, int(round(0.400 * sfreq)))
    s600  = max(1, int(round(0.600 * sfreq)))

    event = signal[start:end]
    abs_ev = np.abs(event)
    dur_s  = (end - start) / sfreq
    dur_ms = dur_s * 1000.0

    # --- Duration ---
    f_duration   = dur_s
    f_log_dur_ms = float(np.log1p(dur_ms))

    # --- Amplitude ---
    f_peak_amp  = float(np.max(abs_ev)) if len(abs_ev) > 0 else 0.0
    f_mean_amp  = float(np.mean(abs_ev)) if len(abs_ev) > 0 else 0.0
    f_fill_factor = f_mean_amp / (f_peak_amp + 1e-12)

    # --- Baseline (200 ms before event) ---
    pre_start = max(0, start - s200)
    baseline_rms = _safe_rms(signal[pre_start:start])
    f_snr = f_peak_amp / (baseline_rms + 1e-12)

    # --- Peak position inside event ---
    peak_idx = int(np.argmax(abs_ev)) if len(abs_ev) > 0 else 0
    peak_abs = start + peak_idx

    # --- Symmetry ---
    f_symmetry = peak_idx / max(1, len(abs_ev) - 1)

    # --- Rise / fall slopes ---
    amp_100ms_before = _amplitude_at(signal, peak_abs - s100)
    amp_100ms_after  = _amplitude_at(signal, peak_abs + s100)
    amp_400ms_after  = _amplitude_at(signal, peak_abs + s400)
    f_rise_slope      = (f_peak_amp - amp_100ms_before) / 0.100
    f_fall_slope_100  = (f_peak_amp - amp_100ms_after)  / 0.100
    f_fall_slope_400  = (f_peak_amp - amp_400ms_after)  / 0.400

    # --- Recovery ratios (signal after peak vs peak) ---
    f_rec_100 = amp_100ms_after  / (f_peak_amp + 1e-12)
    f_rec_200 = _amplitude_at(signal, peak_abs + s200) / (f_peak_amp + 1e-12)
    f_rec_400 = amp_400ms_after  / (f_peak_amp + 1e-12)

    # --- Plateau flatness (middle 50 % of event) ---
    n_ev = len(abs_ev)
    mid_s = n_ev // 4
    mid_e = 3 * n_ev // 4
    if (mid_e - mid_s) >= 2:
        mid = abs_ev[mid_s:mid_e]
        f_plateau_cv = float(np.std(mid) / (np.mean(mid) + 1e-12))
    else:
        f_plateau_cv = 1.0

    # --- pAVR analogue ---
    if len(event) > 1:
        max_vel = float(np.max(np.abs(np.diff(event)))) * sfreq
    else:
        max_vel = 1e-12
    f_pavr = f_peak_amp / (max_vel + 1e-12)

    # --- Post-event energy ---
    post_start  = end
    post_end_a  = min(n, end + s400)           # 0 – 400 ms post-event
    post_start2 = min(n, end + s200)           # 200 ms post-event
    post_end_b  = min(n, end + s600)           # 200 – 600 ms post-event
    f_post_rms_ratio  = _safe_rms(signal[post_start:post_end_a])  / (baseline_rms + 1e-12)
    f_post_early_ratio = _safe_rms(signal[post_start2:post_end_b]) / (baseline_rms + 1e-12)

    # --- Higher-order statistics ---
    if len(event) >= 4:
        f_skew = float(stats.skew(event))
        f_kurt = float(stats.kurtosis(event))
    else:
        f_skew = 0.0
        f_kurt = 0.0

    # --- Context features (Recommendation #4) ---
    s1 = max(1, int(round(sfreq)))          # 1 s in samples
    s25 = max(1, int(round(2.5 * sfreq)))   # 2.5 s half-window (→ 5 s total)

    # 1 s before event
    f_pre_rms_1s = _safe_rms(signal[max(0, start - s1):start]) / (baseline_rms + 1e-12)

    # 1 s after event end — captures quiet plateau following a long-closure onset spike
    f_post_rms_1s = _safe_rms(signal[end:min(n, end + s1)]) / (baseline_rms + 1e-12)

    # 5 s neighbourhood (centred on event midpoint) — local activity level
    mid = (start + end) // 2
    f_local_activity = (
        _safe_rms(signal[max(0, mid - s25):min(n, mid + s25)])
        / (baseline_rms + 1e-12)
    )

    # Combined discriminant: long duration × quiet aftermath = long closure
    # Clamp post_rms_1s to [0, 2] so outliers don't dominate
    suppression = max(0.0, 1.0 - min(f_post_rms_1s, 2.0) / 2.0)
    f_dur_post_product = float(f_duration * suppression)

    return np.array([
        f_duration, f_log_dur_ms,
        f_peak_amp, f_fill_factor, f_snr,
        f_symmetry,
        f_rise_slope, f_fall_slope_100, f_fall_slope_400,
        f_rec_100, f_rec_200, f_rec_400,
        f_plateau_cv, f_pavr,
        f_skew, f_kurt,
        f_post_rms_ratio, f_post_early_ratio,
        f_pre_rms_1s, f_post_rms_1s, f_local_activity, f_dur_post_product,
    ], dtype=np.float32)


__all__ = ["FEATURE_NAMES", "N_FEATURES", "extract_event_features"]
