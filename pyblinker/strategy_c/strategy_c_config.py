"""Configuration for Strategy C: autoreject-based blink region detection."""

from __future__ import annotations

from dataclasses import dataclass, field


# Frontal channels typically associated with blink artifacts.
# These are the standard 10-20 positions that capture vertical EOG deflections.
DEFAULT_FRONTAL_CHANNEL_PATTERNS = (
    "Fp1", "Fp2", "Fpz",
    "AF3", "AF4", "AFz", "AF7", "AF8",
    "F7", "F8",
)


@dataclass
class StrategyCConfig:
    """Parameters controlling Strategy C region detection."""

    # --- Sub-window settings ---
    mini_window_duration_s: float = 0.5
    """Duration of each mini-window in seconds (default 500 ms for normal blinks)."""

    long_closure_window_duration_s: float = 1.0
    """Duration of mini-windows for the long eye-closure track (default 1000 ms)."""

    # --- Spatial filtering ---
    frontal_channel_patterns: tuple[str, ...] = DEFAULT_FRONTAL_CHANNEL_PATTERNS
    """Substrings matched (case-insensitive) against channel names to identify
    blink-relevant channels.  A mini-window is a blink candidate only when the
    flagged channels overlap with this set."""

    frontal_ratio_threshold: float = 0.5
    """Minimum fraction of flagged channels that must be frontal for a
    mini-window to qualify as a blink candidate."""

    # --- AutoReject parameters ---
    autoreject_cv: int = 5
    """Cross-validation folds for AutoReject threshold learning."""

    autoreject_n_jobs: int = 1
    """Number of parallel jobs for AutoReject."""

    autoreject_random_state: int = 42
    """Random seed for reproducibility."""

    autoreject_verbose: bool = False
    """Whether AutoReject prints progress messages."""

    # --- Long eye-closure classification ---
    ambiguous_min_duration_s: float = 0.3
    """Lower boundary of the ambiguous blink/closure zone (seconds)."""

    ambiguous_max_duration_s: float = 0.6
    """Upper boundary of the ambiguous blink/closure zone (seconds)."""

    closure_min_duration_s: float = 0.6
    """Minimum duration for an event to be classified as a definite long closure."""

    strong_closure_duration_s: float = 2.0
    """Duration above which an event is treated as closure-like even if
    morphology is only weakly informative."""

    plateau_symmetry_threshold: float = 0.6
    """Symmetry ratio threshold: events with closing/opening speed ratio below this
    are considered closure-like (strong asymmetry)."""

    # --- Pipeline control ---
    required_steps: tuple[str, ...] = (
        "fit_blinks",
        "blink_statistics",
        "good_blink_mask",
        "blink_properties",
        "pavr_filter",
    )
    """Downstream pipeline steps required by Strategy C (all by default)."""

    supports_closure_detection: bool = True
    """Strategy C supports parallel long eye-closure detection."""


__all__ = [
    "DEFAULT_FRONTAL_CHANNEL_PATTERNS",
    "StrategyCConfig",
]
