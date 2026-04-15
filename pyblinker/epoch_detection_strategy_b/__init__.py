"""Strategy B epoch-aware helpers."""

from .epoch_blink_pipeline_b import (
    BlinkDetectorEpochStrategyB,
    prepare_epoch_detection_input,
    run_epoch_blink_pipeline_mne,
)
from .epoch_channel_processor_b import process_concatenated_epoch_channel_mne
from .mne_step1 import (
    DEFAULT_STRATEGY_B_CHANNELS,
    find_eog_candidate_regions,
    summarize_candidate_regions,
)

__all__ = [
    "BlinkDetectorEpochStrategyB",
    "DEFAULT_STRATEGY_B_CHANNELS",
    "find_eog_candidate_regions",
    "prepare_epoch_detection_input",
    "process_concatenated_epoch_channel_mne",
    "run_epoch_blink_pipeline_mne",
    "summarize_candidate_regions",
]
