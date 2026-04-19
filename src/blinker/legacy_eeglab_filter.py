"""Legacy EEGLAB-style FIR preprocessing for Blinker-compatible detection."""

from __future__ import annotations

import numpy as np
from scipy.signal import lfilter


TRANSITION_WIDTH_RATIO = 0.25


def _spectral_inversion(kernel: np.ndarray) -> np.ndarray:
    inverted = -kernel.copy()
    inverted[len(inverted) // 2] += 1.0
    return inverted


def _windowed_sinc_kernel(
    order: int,
    normalized_cutoff: float,
    window: np.ndarray,
) -> np.ndarray:
    # MATLAB firws() converts cutoff values to cycles/sample before building
    # the windowed-sinc kernel.
    cutoff = float(normalized_cutoff) / 2.0
    samples = np.arange(-(order // 2), (order // 2) + 1, dtype=np.float64)

    kernel = np.empty_like(samples)
    zero_mask = samples == 0
    kernel[zero_mask] = 2.0 * np.pi * cutoff
    kernel[~zero_mask] = (
        np.sin(2.0 * np.pi * cutoff * samples[~zero_mask]) / samples[~zero_mask]
    )
    kernel *= window
    kernel /= np.sum(kernel)
    return kernel


def design_bandpass_coefficients(
    sfreq: float,
    low_cutoff_hz: float,
    high_cutoff_hz: float,
) -> np.ndarray:
    """Return the exact Hamming FIR coefficients used by legacy Blinker."""

    if sfreq <= 0:
        raise ValueError("Sampling rate must be positive.")
    if low_cutoff_hz <= 0 or high_cutoff_hz <= 0:
        raise ValueError("Bandpass cutoffs must be positive.")
    if low_cutoff_hz >= high_cutoff_hz:
        raise ValueError("Expected low_cutoff_hz < high_cutoff_hz for bandpass.")

    f_nyquist = sfreq / 2.0
    edge = np.sort(np.asarray([low_cutoff_hz, high_cutoff_hz], dtype=np.float64))
    max_transition = np.asarray([edge[0], f_nyquist - edge[1]], dtype=np.float64)
    max_df = float(np.min(max_transition))

    transition_width = min(max(edge[0] * TRANSITION_WIDTH_RATIO, 2.0), max_df)
    order = int(np.ceil((3.3 / (transition_width / sfreq)) / 2.0) * 2.0)
    cutoff = edge + np.asarray([-transition_width, transition_width]) / 2.0

    window = np.hamming(order + 1).astype(np.float64, copy=False)
    lowpass = _windowed_sinc_kernel(order, cutoff[0] / f_nyquist, window)
    highpass = _spectral_inversion(
        _windowed_sinc_kernel(order, cutoff[1] / f_nyquist, window)
    )
    return _spectral_inversion(lowpass + highpass)


def apply_zero_phase_dc_padded(data: np.ndarray, coeffs: np.ndarray) -> np.ndarray:
    """Match MATLAB firfilt() for continuous data with no boundary events."""

    data = np.asarray(data, dtype=np.float64)
    original_ndim = data.ndim
    if original_ndim == 1:
        data = data[np.newaxis, :]
    elif original_ndim != 2:
        raise ValueError("Expected a 1D or 2D array of channel data.")

    coeffs = np.asarray(coeffs, dtype=np.float64).reshape(-1)
    if coeffs.size % 2 != 1:
        raise ValueError("Expected an odd filter length from an even FIR order.")

    group_delay = (coeffs.size - 1) // 2
    start_pad = np.repeat(data[:, :1], group_delay, axis=1)
    end_pad = np.repeat(data[:, -1:], group_delay, axis=1)
    padded = np.concatenate([start_pad, data, end_pad], axis=1)
    filtered = lfilter(coeffs, [1.0], padded, axis=1)
    filtered = filtered[:, 2 * group_delay :]

    if original_ndim == 1:
        return filtered[0]
    return filtered


def legacy_blinker_bandpass(
    data: np.ndarray,
    *,
    sfreq: float,
    low_cutoff_hz: float,
    high_cutoff_hz: float,
) -> np.ndarray:
    """Filter data using the same FIR design/application path as MATLAB Blinker."""

    coeffs = design_bandpass_coefficients(
        sfreq=sfreq,
        low_cutoff_hz=low_cutoff_hz,
        high_cutoff_hz=high_cutoff_hz,
    )
    return apply_zero_phase_dc_padded(data, coeffs)
