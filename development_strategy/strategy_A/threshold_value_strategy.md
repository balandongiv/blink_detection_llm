
```python
def _compute_basic_statistics(
params: dict,
blink_component: np.ndarray,
) -> tuple[float, float]:
"""Return MATLAB-equivalent thresholding statistics."""

    mean_value = float(np.mean(blink_component, dtype=np.float64))
    robust_std = float(SCALING_FACTOR * mad(blink_component))
    min_blink_frames = float(params["min_event_len"] * params["sfreq"])
    threshold = float(mean_value + params["std_threshold"] * robust_std)
    return min_blink_frames, threshold
```

# MAD
```python
def mad(arr: np.ndarray, axis: int | None = None, keepdims: bool = True) -> np.ndarray:
    """Compute median absolute deviation using the MATLAB approach."""
    median = np.median(arr, axis=axis, keepdims=True)
    mad = np.median(np.abs(arr - median), axis=axis, keepdims=keepdims)[0]
    return mad

```
