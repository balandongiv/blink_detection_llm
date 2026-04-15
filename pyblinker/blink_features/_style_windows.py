"""Shared style-window resolution for frame-indexed blink metadata."""

from __future__ import annotations

from typing import Dict, List, Mapping, Set

from .utils.style_windows import extract_windows


def style_windows_from_metadata(
    metadata_row: Mapping[str, object],
    modality: str,
    available_styles: Set[str],
    n_times: int,
    *,
    include_half: bool = True,
    include_peak: bool = True,
    ear_mode: str = "keep",
    ear_priority: str = "th_point_first",
) -> Dict[str, List[tuple[int, int]]]:
    """Resolve output style names to frame windows for one modality.

    Parameters
    ----------
    ear_mode:
        ``"keep"`` keeps ``th_interpolation`` as key.
        ``"map_to_th_point"`` maps EAR interpolation windows to ``th_point``.
    ear_priority:
        ``"th_point_first"`` checks ``th_point`` before ``th_interpolation``.
        ``"th_interpolation_first"`` checks ``th_interpolation`` before ``th_point``.
    """

    style_windows: Dict[str, List[tuple[int, int]]] = {}
    if modality in {"eeg", "eog"}:
        if "zero" in available_styles:
            style_windows["zero"] = extract_windows(
                metadata_row, modality, "zero", n_times
            )
        if "base" in available_styles:
            style_windows["base"] = extract_windows(
                metadata_row, modality, "base", n_times
            )
        if "tent" in available_styles:
            style_windows["tent"] = extract_windows(
                metadata_row, modality, "tent", n_times
            )

        if include_half:
            if "half_base" in available_styles:
                style_windows["half"] = extract_windows(
                    metadata_row, modality, "half_base", n_times
                )
            elif "half_zero" in available_styles:
                style_windows["half"] = extract_windows(
                    metadata_row, modality, "half_zero", n_times
                )

        if include_peak:
            if "tent" in style_windows:
                style_windows["peak"] = style_windows["tent"]
            elif "base" in style_windows:
                style_windows["peak"] = style_windows["base"]

    elif modality == "ear":
        ordered_ear_styles = ("th_point", "th_interpolation")
        if ear_priority == "th_interpolation_first":
            ordered_ear_styles = ("th_interpolation", "th_point")

        selected_style = next(
            (s for s in ordered_ear_styles if s in available_styles), None
        )
        if selected_style is not None:
            out_key = selected_style
            if selected_style == "th_interpolation" and ear_mode == "map_to_th_point":
                out_key = "th_point"
            style_windows[out_key] = extract_windows(
                metadata_row, modality, selected_style, n_times
            )

    return style_windows
