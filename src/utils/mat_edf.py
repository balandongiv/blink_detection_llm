"""Utilities for converting MATLAB structures to :mod:`mne` Raw objects."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import mne
import numpy as np
import scipy.io


def print_structure(data: Any, indent: int = 0) -> None:
    """Recursively print the structure of a MATLAB object for debugging."""

    prefix = "  " * indent
    if isinstance(data, Mapping):
        for key, value in data.items():
            if str(key).startswith("__"):
                continue
            print(f"{prefix}Key: {key}, Type: {type(value)}")
            print_structure(value, indent + 1)
    elif isinstance(data, np.ndarray):
        print(f"{prefix}ndarray with dtype: {data.dtype}, shape: {data.shape}")
    elif isinstance(data, (list, tuple)):
        print(f"{prefix}{type(data).__name__} with length: {len(data)}")
        for idx, value in enumerate(data):
            print(f"{prefix}  [{idx}] → {type(value)}")
            print_structure(value, indent + 2)
    else:
        print(f"{prefix}{type(data)}")


def find_numeric_arrays(data: Any, path: str = "") -> dict[str, np.ndarray]:
    """Return a mapping of dotted paths to numeric arrays found within ``data``."""

    found: dict[str, np.ndarray] = {}

    if isinstance(data, Mapping):
        for key, value in data.items():
            if str(key).startswith("__"):
                continue
            new_path = f"{path}/{key}" if path else str(key)
            found.update(find_numeric_arrays(value, new_path))
    elif isinstance(data, (list, tuple)):
        for index, value in enumerate(data):
            new_path = f"{path}[{index}]"
            found.update(find_numeric_arrays(value, new_path))
    elif isinstance(data, np.ndarray) and data.dtype.kind in "fiu" and data.size > 0:
        found[path] = data

    return found


def _resolve_sampling_frequency(container: Any, sfreq_default: float) -> float:
    candidates = (
        "sfreq",
        "srate",
        "fs",
        "sampling_rate",
        "Fs",
        "sampFreq",
    )

    def _try_extract(value: Any) -> float | None:
        if isinstance(value, Mapping):
            for key in candidates:
                if key in value:
                    result = _try_extract(value[key])
                    if result is not None:
                        return result
            for nested in value.values():
                result = _try_extract(nested)
                if result is not None:
                    return result
        elif isinstance(value, (list, tuple)):
            for nested in value:
                result = _try_extract(nested)
                if result is not None:
                    return result
        else:
            array = np.asarray(value)
            if array.size:
                try:
                    candidate = float(array.ravel()[0])
                except (TypeError, ValueError):
                    return None
                else:
                    if np.isfinite(candidate):
                        return candidate
        return None

    extracted = _try_extract(container)
    if extracted is None:
        return float(sfreq_default)
    return float(extracted)


def load_mat_to_mne(mat_path: str, sfreq_default: float = 256.0) -> mne.io.BaseRaw:
    """Load a MATLAB file and coerce its primary array into an :class:`mne.io.RawArray`."""

    mat = scipy.io.loadmat(mat_path, simplify_cells=True)

    data_candidate: np.ndarray | None = None
    if isinstance(mat.get("o"), Mapping) and "data" in mat["o"]:
        data_candidate = np.asarray(mat["o"]["data"])

    if data_candidate is None:
        numeric = find_numeric_arrays(mat)
        if not numeric:
            print("No numeric arrays found in the .mat file after recursive search.")
            print("MAT-file structure:")
            print_structure(mat)
            raise ValueError("No numeric arrays found in the .mat file.")
        data_candidate = np.asarray(
            max(numeric.items(), key=lambda item: item[1].size)[1]
        )

    arr = np.asarray(data_candidate)
    if arr.ndim == 1:
        arr = arr[np.newaxis, :]
    elif arr.ndim == 3:
        if arr.shape[-1] >= max(arr.shape[0], arr.shape[1]):
            arr = arr.reshape(-1, arr.shape[-1])
        else:
            arr = arr[0]
    elif arr.ndim > 3:
        raise ValueError(f"Unsupported array dimensionality: {arr.ndim}")

    if arr.shape[0] > arr.shape[1]:
        arr = arr.T

    data = arr.astype(np.float64, copy=False)
    data[~np.isfinite(data)] = np.nan
    if np.isnan(data).any():
        data = np.nan_to_num(data, nan=0.0)

    sfreq = _resolve_sampling_frequency(mat.get("o", mat), sfreq_default)
    ch_names = [f"CH{i + 1}" for i in range(data.shape[0])]

    scale = 1.0
    meta_str = " ".join(map(str, mat.keys())).lower()
    if any(token in meta_str for token in ("uv", "microv", "microvolt", "micro_volt")):
        scale = 1e6
    elif any(
        token in meta_str for token in ("mv", "milliv", "millivolt", "milli_volt")
    ):
        scale = 1e3

    if scale == 1.0:
        p99 = float(np.percentile(np.abs(data), 99))
        if p99 > 1.0:
            scale = 1e6
        elif 1e-2 < p99 <= 1.0:
            scale = 1e3

    if scale != 1.0:
        print(
            f"[load_mat_to_mne] Detected non-Volt data. Dividing by {scale:g} to convert to Volts."
        )
        data = data / scale

    info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types="eeg")
    return mne.io.RawArray(data, info)
