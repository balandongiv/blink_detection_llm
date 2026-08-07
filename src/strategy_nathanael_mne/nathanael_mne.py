"""Strategy B step: MNE EOG-event-based blink candidate detection.

Named after Nathanael's MNE-based approach.  The single important function is
:func:`find_eog_candidate_regions`, which wraps MNE's ``find_eog_events`` to
produce a DataFrame of blink-window candidates in concatenated-signal space.
"""

import mne
import numpy as np
import pandas as pd

# DEFAULT_STRATEGY_NATHANAEL_MNE_CHANNELS = (
#     "EEG X1 - Pz",
#     "EEG Fp1 - Pz",
#     "EEG Fp2 - Pz",
# )


def find_eog_candidate_regions(
    concatenated_signal: np.ndarray,
    *,
    channel: str,
    sfreq: float,
    half_window_s: float = 0.10,
    l_freq: float = 1.0,
    h_freq: float = 20.0,
    thresh: float | None = None,
) -> pd.DataFrame:
    """Convert MNE EOG peak events into candidate blink regions.

    Wraps ``mne.preprocessing.find_eog_events`` on a single-channel
    concatenated signal and expands each peak by ±``half_window_s`` seconds
    to define ``start_blink`` / ``end_blink`` boundaries.

    Parameters
    ----------
    concatenated_signal:
        1-D array of the full concatenated valid-epoch signal for one channel.
    channel:
        Channel name used for labelling the output rows.
    sfreq:
        Sampling frequency in Hz.
    half_window_s:
        Half-window in seconds around each EOG peak.
    l_freq, h_freq:
        Bandpass range passed to ``find_eog_events``.
    thresh:
        Amplitude threshold passed to ``find_eog_events``.  When ``None``
        MNE's automatic threshold is used.

    Returns
    -------
    pd.DataFrame
        Columns: ``start_blink``, ``end_blink``, ``peak_sample``, ``channel``.
        Empty DataFrame (same columns) when no events are found.
    """
    columns = ["start_blink", "end_blink", "peak_sample", "channel"]
    signal = np.asarray(concatenated_signal, dtype=float).reshape(-1)
    if signal.size == 0:
        return pd.DataFrame(columns=columns)

    info = mne.create_info([channel], sfreq=float(sfreq), ch_types=["eeg"])
    raw = mne.io.RawArray(signal[np.newaxis, :], info, verbose="ERROR")

    kwargs: dict[str, object] = {
        "ch_name": channel,
        "l_freq": float(l_freq),
        "h_freq": float(h_freq),
        "reject_by_annotation": False,
        "verbose": "ERROR",
    }
    # if thresh is not None:
    #     kwargs["thresh"] = float(thresh)
    #

    try:
        events = mne.preprocessing.find_eog_events(raw, **kwargs)
    except TypeError as exc:
        # MNE 1.11 has a corner-case in peak_finder: when a filtered signal is
        # monotone and no peak is found, it attempts to multiply an empty list
        # by a float.  For this detector that is simply an empty result.
        if "can't multiply sequence by non-int of type 'float'" not in str(exc):
            raise
        return pd.DataFrame(columns=columns)


    # if len(events) == 0:
    #     return pd.DataFrame(columns=columns)

    peaks = np.asarray(events[:, 0] - raw.first_samp, dtype=int)
    half_window_samples = max(1, int(round(float(half_window_s) * float(sfreq))))
    start_blink = np.clip(peaks - half_window_samples, 0, signal.size - 1)
    end_blink = np.clip(peaks + half_window_samples, 0, signal.size - 1)

    blink_df = pd.DataFrame(
        {
            "start_blink": start_blink.astype(int),
            "end_blink": end_blink.astype(int),
            "peak_sample": peaks.astype(int),
            "channel": channel,
        }
    )
    blink_df = blink_df.drop_duplicates(subset=["start_blink", "end_blink"])
    return blink_df.sort_values(["start_blink", "end_blink"]).reset_index(drop=True)


__all__ = [
    # "DEFAULT_STRATEGY_NATHANAEL_MNE_CHANNELS",
    "find_eog_candidate_regions",
]
