#
# import matplotlib.pyplot as plt
# import numpy as np
# import seaborn as sns
#
# sns.set_style("darkgrid")
#
# def viz_complete_blink_prop(data,row,srate):
#
#
#     """
#
#     TODO Viz
#
#     https://stackoverflow.com/a/51928241/6446053
#
#     :return:
#     """
#
#
#     xLabelString='T'
#     fig, ax = plt.subplots(figsize=(8, 6))
#
#     npad = 20
#     preLimit = row['start_blink'] - npad
#     postLimit = row['end_blink'] + npad
#
#     idx_t = np.arange(preLimit, postLimit + 1)
#
#     bTrace = data[idx_t]
#
#
#     plt.plot(idx_t, bTrace,linestyle='-',marker='o',color='b',
#              label='line with marker',alpha=0.7)
#     plt.plot([idx_t[0], idx_t[-1]], [0, 0], "--", color="gray", lw=2,label='Y0')
#
#
#     # plt.plot([row['xLineCross_l'] , row['x_intersect']], [row['yLineCross_l'],  row['y_intersect']], "--", color="gray", lw=2)
#     # plt.plot([row['x_intersect'],row['xLineCross_r']], [row['y_intersect'],row['yLineCross_r']], "--", color="gray", lw=2)
#
#     # plt.plot([row['left_x_intercept'] , row['x_intersect']], [row['yLineCross_l'],  row['y_intersect']], "--", color="gray", lw=2)
#     # plt.plot([row['x_intersect'],row['right_x_intercept']], [row['y_intersect'],row['yLineCross_r']], "--", color="gray", lw=2)
#
#     ## PLot key point
#     plt.scatter([row['blink_bottom_point_l_x'],row['blink_top_point_l_x']],
#                 [row['blink_bottom_point_l_y'],row['blink_top_point_l_y']],
#                 marker='*', s=200,label='left_top_down_blink')
#
#     plt.scatter([row['blink_bottom_point_r_x'],row['blink_top_point_r_x']],
#                 [row['blink_bottom_point_r_y'],row['blink_top_point_r_y']],
#                 marker='*', s=200,label='right_top_down_blink')
#
#
#
#     plt.scatter(row['x_intersect'], row['y_intersect'],label='tent_point')
#
#
#     plt.scatter([row['left_zero'], row['right_zero']], [0, 0], marker='d', s=100,label='zero crossing')
#     plt.scatter(row['max_blink'], data[row['max_blink']],label='max Frame')
#
#     plt.legend()
#     ylabel='Signal(uv)'
#     plt.xlabel(xLabelString)
#     plt.ylabel(ylabel)
#     bquality= 'Good'
#     max_blink=row['max_blink']
#     d=dict(fig=fig,
#            blink_quality=bquality,
#            maxFrames=max_blink)
#
#     return d

from typing import Dict, Any, Optional, Iterable
import numpy as np
import matplotlib.pyplot as plt


def viz_complete_blink_prop(
    data: np.ndarray,
    row: dict,
    srate: Optional[float] = None,
    *,
    pad: int = 20,
    show: bool = False,
    ax: Optional[plt.Axes] = None,
) -> Dict[str, Any]:
    """
    Visualize a blink segment and keypoints without auto-displaying the figure.

    Parameters
    ----------
    data : np.ndarray
        1D signal array.
    row : dict
        Dict-like with required keys:
          'start_blink', 'end_blink', 'max_blink'
        Missing/NaN keypoint values are skipped gracefully for the following optional keys:
          'blink_bottom_point_l_x', 'blink_top_point_l_x', 'blink_bottom_point_l_y',
          'blink_top_point_l_y', 'blink_bottom_point_r_x', 'blink_top_point_r_x',
          'blink_bottom_point_r_y', 'blink_top_point_r_y', 'x_intersect', 'y_intersect',
          'left_zero', 'right_zero'
    srate : float, optional
        Sampling rate in Hz. If provided, x-axis is in samples (label shows both samples and seconds).
    pad : int, default 20
        Number of samples to pad before start_blink and after end_blink.
    show : bool, default False
        If True, displays the plot. By default the figure is closed (no display).
    ax : matplotlib.axes.Axes, optional
        If provided, draw onto this axes; otherwise a new figure/axes is created.

    Returns
    -------
    dict
        {
          'fig': matplotlib.figure.Figure,
          'blink_quality': str,
          'maxFrames': int,
          'idx_window': np.ndarray,  # indices used
        }
    """
    # ---- Basic validation ----------------------------------------------------
    data = np.asarray(data).ravel()
    n = data.size

    def _is_missing(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, float) and np.isnan(value):
            return True
        return False

    def _get_required_int(key: str) -> int:
        if key not in row:
            raise KeyError(f"Missing required key '{key}' in row data.")
        value = row[key]
        if _is_missing(value):
            raise ValueError(f"Missing value for required key '{key}'.")
        return int(value)

    def _get_optional_int(key: str) -> Optional[int]:
        value = row.get(key)
        if _is_missing(value):
            return None
        return int(value)

    def _get_optional_float(key: str) -> Optional[float]:
        value = row.get(key)
        if _is_missing(value):
            return None
        return float(value)

    start_blink = _get_required_int("start_blink")
    end_blink = _get_required_int("end_blink")

    if start_blink > end_blink:
        start_blink, end_blink = end_blink, start_blink  # swap if out of order

    # Clamp window to data bounds
    pre = max(0, start_blink - pad)
    post = min(n - 1, end_blink + pad)

    # If window collapses, bail gracefully
    if post <= pre:
        fig = plt.figure() if ax is None else ax.figure
        if not show:
            plt.close(fig)
        max_blink = _get_optional_int("max_blink")
        return {
            "fig": fig,
            "blink_quality": "Unknown",
            "maxFrames": max_blink if max_blink is not None else -1,
            "idx_window": np.array([], dtype=int),
        }

    idx_t = np.arange(pre, post + 1, dtype=int)
    bTrace = data[idx_t]

    # ---- Prepare axes --------------------------------------------------------
    created_fig = False
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))
        created_fig = True
    else:
        fig = ax.figure

    # ---- Axis labels ---------------------------------------------------------
    if srate and srate > 0:
        # We keep sample indices for plotting (as requested behavior),
        # but annotate axis label with seconds info for readability.
        x_label = f"Samples (≈ {(idx_t[-1] - idx_t[0] + 1) / srate:.3f} s shown)"
    else:
        x_label = "Samples"

    y_label = "Signal (µV)"

    # ---- Plot main trace & zero line ----------------------------------------
    ax.plot(idx_t, bTrace, linestyle="-", marker="o", alpha=0.7, label="blink trace")
    ax.plot([idx_t[0], idx_t[-1]], [0, 0], "--", lw=2, label="y=0")

    # ---- Helpers to safely plot keypoints -----------------------------------
    def _in_window(x: int) -> bool:
        return pre <= x <= post

    def _finite(y: Optional[float]) -> bool:
        if y is None:
            return False
        return np.isfinite(y)

    def _scatter(xs: Iterable[int], ys: Iterable[float], **kwargs):
        xs = list(xs)
        ys = list(ys)
        keep = []
        for i, (x, y) in enumerate(zip(xs, ys)):
            if not isinstance(x, (int, np.integer)):
                continue
            if not _in_window(int(x)):
                continue
            if _is_missing(y):
                continue
            y_val = float(y)
            if not _finite(y_val):
                continue
            keep.append(i)
        if keep:
            ax.scatter([xs[i] for i in keep], [ys[i] for i in keep], **kwargs)

    # Left eye keypoints
    left_bottom_x = _get_optional_int("blink_bottom_point_l_x")
    left_top_x = _get_optional_int("blink_top_point_l_x")
    left_bottom_y = _get_optional_float("blink_bottom_point_l_y")
    left_top_y = _get_optional_float("blink_top_point_l_y")
    if left_bottom_x is not None and left_top_x is not None:
        _scatter(
            [left_bottom_x, left_top_x],
            [left_bottom_y, left_top_y],
            marker="*",
            s=200,
            label="left top/bottom",
        )

    # Right eye keypoints
    right_bottom_x = _get_optional_int("blink_bottom_point_r_x")
    right_top_x = _get_optional_int("blink_top_point_r_x")
    right_bottom_y = _get_optional_float("blink_bottom_point_r_y")
    right_top_y = _get_optional_float("blink_top_point_r_y")
    if right_bottom_x is not None and right_top_x is not None:
        _scatter(
            [right_bottom_x, right_top_x],
            [right_bottom_y, right_top_y],
            marker="*",
            s=200,
            label="right top/bottom",
        )

    # Tent point (intersection)
    xi = _get_optional_int("x_intersect")
    yi = _get_optional_float("y_intersect")
    if xi is not None and yi is not None and _in_window(xi) and _finite(yi):
        ax.scatter(xi, yi, label="tent point")

    # Zero crossings
    lz = _get_optional_int("left_zero")
    rz = _get_optional_int("right_zero")
    zero_xs = [value for value in (lz, rz) if value is not None]
    if zero_xs:
        _scatter(
            zero_xs, [0.0] * len(zero_xs), marker="d", s=100, label="zero crossings"
        )

    # Max frame
    max_blink = _get_required_int("max_blink")
    if 0 <= max_blink < n and _in_window(max_blink) and _finite(float(data[max_blink])):
        ax.scatter(max_blink, float(data[max_blink]), label="max frame")

    # ---- Cosmetics -----------------------------------------------------------
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.legend(loc="best")
    ax.set_xlim(idx_t[0], idx_t[-1])
    ax.margins(x=0.02, y=0.1)
    ax.grid(True, which="both", linestyle="--", alpha=0.3)
    fig.tight_layout()

    # ---- Do not display ------------------------------------------------------
    # By default, do not display the figure (prevents auto-display in notebooks).
    if not show and created_fig:
        plt.close(fig)

    # Stubbed quality (replace with your actual logic if available)
    bquality = "Good"

    return {
        "fig": fig,
        "blink_quality": bquality,
        "maxFrames": max_blink,
        "idx_window": idx_t,
    }
