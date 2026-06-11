"""SVM blink detection pipeline.

Training
--------
``collect_session_data`` extracts labelled feature vectors for one session:
  - Class 1 (normal blink): windows from GT normal-blink events
  - Class 2 (long closure):  windows from GT long-blink events
  - Class 0 (background):    randomly sampled non-event windows

``train_svm_pipeline`` fits a StandardScaler → SVC(RBF) pipeline.

Test-time
---------
``predict_and_build_results`` runs a low-threshold candidate finder on the
concatenated signal, extracts the same 18 features for every candidate, and
applies the trained SVM.  Candidates classified as 1 or 2 are returned in
the standard ``channel_results`` list[dict] format for ``evaluate_channels``.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from scipy.ndimage import uniform_filter1d
from tqdm import tqdm

from src.common.epoch_channel import map_concatenated_blinks_to_epochs
from src.common.epoch_input import PreparedEpochDetectionInput
from src.common.pipeline_utils import build_epoch_boundaries, build_signal_by_epoch
from src.strategy_svm.features import extract_event_features

logger = logging.getLogger(__name__)

# Labels
LABEL_NOISE  = 0
LABEL_NORMAL = 1
LABEL_LONG   = 2


# ---------------------------------------------------------------------------
# Signal helpers (self-contained to avoid private imports)
# ---------------------------------------------------------------------------

def _sliding_rms(signal: np.ndarray, window: int) -> np.ndarray:
    w = max(1, int(window))
    return np.sqrt(np.maximum(
        uniform_filter1d(np.square(signal, dtype=np.float64), size=w, mode="reflect"),
        0.0,
    ))


def _fill_gaps(mask: np.ndarray, max_gap: int) -> np.ndarray:
    if max_gap <= 0:
        return mask.copy()
    out = mask.copy()
    gap_start = None
    for i, v in enumerate(mask):
        if not v:
            if gap_start is None:
                gap_start = i
        else:
            if gap_start is not None:
                if (i - gap_start) <= max_gap:
                    out[gap_start:i] = True
                gap_start = None
    return out


def _contiguous(mask: np.ndarray) -> list[tuple[int, int]]:
    regions, in_r, s = [], False, 0
    for i, v in enumerate(mask):
        if v and not in_r:
            in_r, s = True, i
        elif not v and in_r:
            in_r = False
            regions.append((s, i))
    if in_r:
        regions.append((s, len(mask)))
    return regions


# ---------------------------------------------------------------------------
# Candidate detector (low threshold → high recall)
# ---------------------------------------------------------------------------

def find_candidates(
    signal: np.ndarray,
    sfreq: float,
    *,
    rms_window_ms: float = 50.0,
    threshold_factor: float = 1.5,
    debounce_ms: float = 200.0,
    min_dur_s: float = 0.08,
    max_dur_s: float = 5.0,
) -> list[tuple[int, int]]:
    """Low-threshold amplitude candidate finder.

    Uses a threshold at mean + ``threshold_factor`` × std of the RMS envelope.
    The generous debounce (200 ms default) merges the onset and offset spikes
    of a long closure into one candidate event when they are close enough.

    Parameters
    ----------
    threshold_factor:
        Number of standard deviations above the mean for the threshold.
        Default 1.5 — lower than pyblinker (~3-4 σ) to maximise recall.
    debounce_ms:
        Gap-fill window (ms).  200 ms bridges onset→offset pairs of short
        long closures; increase to 500 ms for very long closures.
    """
    sig = np.asarray(signal, dtype=np.float64).ravel()
    n = len(sig)
    if n == 0:
        return []

    rms_w   = max(1, int(round(rms_window_ms * sfreq / 1000.0)))
    deb_w   = max(0, int(round(debounce_ms   * sfreq / 1000.0)))
    min_smp = max(1, int(round(min_dur_s * sfreq)))
    max_smp = int(round(max_dur_s * sfreq))

    env   = _sliding_rms(np.abs(sig), rms_w)
    thr   = float(np.mean(env)) + threshold_factor * float(np.std(env))
    mask  = env > thr

    if deb_w > 0:
        mask = _fill_gaps(mask, deb_w)

    return [
        (s, e) for s, e in _contiguous(mask)
        if min_smp <= (e - s) <= max_smp
    ]


def find_candidates_combined(
    signal: np.ndarray,
    sfreq: float,
    *,
    threshold_factor: float = 1.5,
    debounce_ms: float = 200.0,
    min_dur_s: float = 0.08,
    max_dur_s: float = 5.0,
) -> list[tuple[int, int]]:
    """Combined candidate finder: threshold crossing + Module B suppression.

    Recommendation #3: the threshold-crossing approach misses very long
    closures (e.g. ≥ 1.5 s) whose onset spikes are too small or too gradual to
    exceed the amplitude threshold.  Module B detects these via the quiet
    plateau that appears in the bandpass-filtered signal after the onset spike.

    The two sets are merged with suppression-based candidates given priority
    over any overlapping threshold-crossing candidate (long events subsume
    short overlap).
    """
    # Stage 1 — amplitude threshold crossing
    cands_thr = find_candidates(
        signal, sfreq,
        threshold_factor=threshold_factor,
        debounce_ms=debounce_ms,
        min_dur_s=min_dur_s,
        max_dur_s=max_dur_s,
    )

    # Stage 2 — Module B suppression (from dual-mode strategy)
    from src.strategy_dual_mode.long_closure import detect_long_closures
    df_long = detect_long_closures(signal, sfreq)  # uses tuned defaults
    cands_sup: list[tuple[int, int]] = [
        (int(r["start_blink"]), int(r["end_blink"]))
        for _, r in df_long.iterrows()
    ]

    if not cands_sup:
        return cands_thr
    if not cands_thr:
        return cands_sup

    # Merge: suppression candidates subsume overlapping threshold candidates
    sup_starts = np.array([s for s, _ in cands_sup], dtype=int)
    sup_ends   = np.array([e for _, e in cands_sup], dtype=int)

    kept_thr = []
    for ts, te in cands_thr:
        subsumed = False
        for ss, se in zip(sup_starts, sup_ends):
            overlap = max(0, min(te, se) - max(ts, ss))
            if overlap > 0.5 * max(1, te - ts):
                subsumed = True
                break
        if not subsumed:
            kept_thr.append((ts, te))

    combined = kept_thr + cands_sup
    combined.sort(key=lambda x: x[0])
    return combined


# ---------------------------------------------------------------------------
# GT-to-concatenated-signal coordinate mapping
# ---------------------------------------------------------------------------

def _gt_to_concat(
    onset_abs_s: float,
    duration_s: float,
    valid_epoch_indices: list[int],
    epoch_duration_s: float,
    sfreq: float,
) -> tuple[int, int] | None:
    """Convert a GT event (absolute time) to concat-signal sample indices.

    Returns None if the event falls in a dropped (unhealthy) epoch.
    """
    epoch_samples = int(round(epoch_duration_s * sfreq))
    epoch_idx = int(onset_abs_s // epoch_duration_s)
    if epoch_idx not in valid_epoch_indices:
        return None
    valid_pos = valid_epoch_indices.index(epoch_idx)
    epoch_local_s = onset_abs_s - epoch_idx * epoch_duration_s
    cs = valid_pos * epoch_samples + int(round(epoch_local_s * sfreq))
    ce = cs + max(1, int(round(duration_s * sfreq)))
    return cs, min(ce, (valid_pos + 1) * epoch_samples - 1)


# ---------------------------------------------------------------------------
# Training data collector
# ---------------------------------------------------------------------------

def collect_session_data(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
    gt_normal_df: pd.DataFrame,
    gt_long_df: pd.DataFrame,
    epoch_duration_s: float,
    *,
    bg_ratio: float = 2.0,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract labelled feature vectors for one session (all channels).

    Parameters
    ----------
    prepared:
        Preprocessed epoch data (already bandpass-filtered).
    valid_epoch_indices:
        Epoch indices that passed the health filter.
    gt_normal_df:
        DataFrame with columns ``onset``, ``duration`` for normal-blink GT.
    gt_long_df:
        Same for long-blink GT.
    epoch_duration_s:
        Epoch duration in seconds.
    bg_ratio:
        Number of background (class-0) samples per positive sample.
    rng:
        Random number generator for reproducibility.

    Returns
    -------
    X: np.ndarray, shape (n_samples, N_FEATURES)
    y: np.ndarray, shape (n_samples,)  — 0/1/2
    """
    if rng is None:
        rng = np.random.default_rng(42)

    sfreq = float(prepared.sfreq)
    epoch_samples = int(prepared.epoch_length_samples)
    n_concat = len(valid_epoch_indices) * epoch_samples

    X_list, y_list = [], []

    for ch_idx in range(len(prepared.channel_names)):
        concat_signal = (
            prepared.data[valid_epoch_indices, ch_idx, :]
            .reshape(-1)
            .astype(np.float64)
        )

        # Positive examples from GT
        gt_windows: list[tuple[int, int, int]] = []  # (start, end, label)
        for df, label in [(gt_normal_df, LABEL_NORMAL), (gt_long_df, LABEL_LONG)]:
            for _, row in df.iterrows():
                result = _gt_to_concat(
                    float(row["onset"]), float(row["duration"]),
                    valid_epoch_indices, epoch_duration_s, sfreq,
                )
                if result is not None:
                    cs, ce = result
                    if ce > cs:
                        gt_windows.append((cs, ce, label))

        for cs, ce, label in gt_windows:
            feats = extract_event_features(concat_signal, sfreq, cs, ce)
            X_list.append(feats)
            y_list.append(label)

        # Background examples (random windows nowhere near GT events)
        n_positive = len(gt_windows)
        n_bg = max(1, int(n_positive * bg_ratio))

        # Build exclusion set: any sample within 1 s of a GT event
        exclusion = np.zeros(n_concat, dtype=bool)
        margin = int(sfreq)
        for cs, ce, _ in gt_windows:
            s = max(0, cs - margin)
            e = min(n_concat, ce + margin)
            exclusion[s:e] = True

        valid_bg_starts = np.where(~exclusion)[0]
        min_bg_dur = int(0.08 * sfreq)
        max_bg_dur = int(0.50 * sfreq)
        if len(valid_bg_starts) > 0:
            sampled = rng.choice(valid_bg_starts, size=min(n_bg * 5, len(valid_bg_starts)),
                                 replace=False)
            count = 0
            for bg_start in sampled:
                dur = int(rng.integers(min_bg_dur, max_bg_dur + 1))
                bg_end = min(n_concat, bg_start + dur)
                if bg_end - bg_start < min_bg_dur:
                    continue
                feats = extract_event_features(concat_signal, sfreq, int(bg_start), bg_end)
                X_list.append(feats)
                y_list.append(LABEL_NOISE)
                count += 1
                if count >= n_bg:
                    break

    if not X_list:
        from src.strategy_svm.features import N_FEATURES
        return np.empty((0, N_FEATURES), dtype=np.float32), np.empty(0, dtype=int)

    return np.stack(X_list), np.asarray(y_list, dtype=int)


# ---------------------------------------------------------------------------
# SVM training  (Recommendation #1: optional grid search)
# ---------------------------------------------------------------------------

def train_svm_pipeline(
    X: np.ndarray,
    y: np.ndarray,
    *,
    C: float = 1.0,
    gamma: str | float = "scale",
    kernel: str = "rbf",
    use_grid_search: bool = False,
    cv_folds: int = 3,
    n_jobs: int = -1,
) -> Pipeline:
    """Fit StandardScaler → SVC.

    Parameters
    ----------
    C, gamma, kernel:
        SVC hyperparameters used when ``use_grid_search=False``.
    use_grid_search:
        When True, performs a 3-fold stratified grid search over
        C=[0.3, 1, 5, 10] × kernel=['rbf','linear'] and returns the
        best-performing pipeline (Recommendation #1).
    cv_folds:
        Number of CV folds for the grid search.
    n_jobs:
        Parallel jobs for grid search (-1 = use all cores).
    """
    base_pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("svc", SVC(
            class_weight="balanced",
            decision_function_shape="ovr",
            random_state=42,
        )),
    ])

    if use_grid_search:
        param_grid = [
            {"svc__kernel": ["rbf"],    "svc__C": [0.3, 1, 5, 10], "svc__gamma": ["scale"]},
            {"svc__kernel": ["linear"], "svc__C": [0.1, 0.3, 1, 5]},
        ]
        search = GridSearchCV(
            base_pipe, param_grid,
            cv=cv_folds,
            scoring="balanced_accuracy",
            n_jobs=n_jobs,
            refit=True,
        )
        search.fit(X, y)
        model = search.best_estimator_
        logger.info(
            "Grid search done: best params=%s  score=%.4f",
            search.best_params_, search.best_score_,
        )
    else:
        base_pipe.set_params(svc__kernel=kernel, svc__C=C, svc__gamma=gamma)
        base_pipe.fit(X, y)
        model = base_pipe

    n_classes = np.unique(y)
    logger.info(
        "SVM trained: %d samples, %d features, %d classes  dist=%s",
        len(y), X.shape[1], len(n_classes),
        {int(c): int(np.sum(y == c)) for c in n_classes},
    )
    return model


# ---------------------------------------------------------------------------
# Test-time prediction and channel_results builder
# ---------------------------------------------------------------------------

def predict_and_build_results(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
    model: Pipeline,
    *,
    threshold_factor: float = 1.5,
    debounce_ms: float = 200.0,
    min_dur_s: float = 0.08,
    max_dur_s: float = 5.0,
    use_combined_candidates: bool = True,
) -> list[dict]:
    """Run SVM-based blink detection for all channels.

    1. Find candidate events (threshold crossing + optional Module B — Rec #3).
    2. Extract 22 features per candidate (incl. 4 context features — Rec #4).
    3. SVM classifies each as normal (1), long (2), or noise (0).
    4. Discard noise; map surviving events to epoch-relative timing.

    Returns
    -------
    list[dict]
        Standard ``{channel, df_positions, mapped_candidates, signal_by_epoch}``
        format for ``evaluate_channels``.
    """
    sfreq = float(prepared.sfreq)
    n_valid = len(valid_epoch_indices)
    epoch_samples = prepared.epoch_length_samples
    epoch_boundaries = build_epoch_boundaries(n_valid, epoch_samples)

    logger.info(
        "SVM predict: %d channels, %d epochs [sfreq=%.1f Hz, concat=%.1f s]",
        len(prepared.channel_names), n_valid, sfreq,
        n_valid * epoch_samples / sfreq,
    )

    _empty = pd.DataFrame(
        columns=["epoch_index", "channel", "blink_onset",
                 "blink_duration", "start_blink", "end_blink"]
    )
    results: list[dict] = []

    for ch_idx, ch_name in enumerate(
        tqdm(prepared.channel_names, desc="SVM-detect", unit="ch")
    ):
        concat_signal = (
            prepared.data[valid_epoch_indices, ch_idx, :]
            .reshape(-1)
            .astype(np.float64)
        )

        _finder = find_candidates_combined if use_combined_candidates else find_candidates
        candidates = _finder(
            concat_signal,
            sfreq,
            threshold_factor=threshold_factor,
            debounce_ms=debounce_ms,
            min_dur_s=min_dur_s,
            max_dur_s=max_dur_s,
        )

        signal_by_epoch = build_signal_by_epoch(prepared, ch_idx)

        if not candidates:
            results.append({
                "channel": ch_name,
                "df_positions": pd.DataFrame(),
                "mapped_candidates": _empty.copy(),
                "signal_by_epoch": signal_by_epoch,
            })
            continue

        # Feature matrix for all candidates
        X_test = np.stack([
            extract_event_features(concat_signal, sfreq, s, e)
            for s, e in candidates
        ])

        # Replace NaN/Inf
        X_test = np.nan_to_num(X_test, nan=0.0, posinf=0.0, neginf=0.0)

        labels = model.predict(X_test)

        # Keep non-noise
        kept = pd.DataFrame(
            [(s, e) for (s, e), lab in zip(candidates, labels) if lab > LABEL_NOISE],
            columns=["start_blink", "end_blink"],
        )

        if kept.empty:
            results.append({
                "channel": ch_name,
                "df_positions": pd.DataFrame(),
                "mapped_candidates": _empty.copy(),
                "signal_by_epoch": signal_by_epoch,
            })
            continue

        mapped = map_concatenated_blinks_to_epochs(
            kept,
            channel=ch_name,
            valid_epoch_indices=valid_epoch_indices,
            epoch_boundaries=epoch_boundaries,
            sfreq=sfreq,
        )

        results.append({
            "channel": ch_name,
            "df_positions": kept.copy(),
            "mapped_candidates": mapped,
            "signal_by_epoch": signal_by_epoch,
        })

    return results


__all__ = [
    "collect_session_data",
    "find_candidates",
    "find_candidates_combined",
    "predict_and_build_results",
    "train_svm_pipeline",
]
