"""Utility functions for pyblinker."""

from .annotation_utils import create_annotation
from .channel_utils import (
    normalize_picks,
    pick_ear_channels_from_info,
    pick_ear_channels_from_raw,
    require_channels,
)
from .epoch_utils import (
    slice_into_mini_raws,
    slice_raw_into_epochs,
    slice_raw_into_mne_epochs,
    slice_raw_to_segments,
)
from .feature_dataframe import to_epoch_indexed
from .io_utils import prepare_refined_segments, save_epoch_raws
from .metadata_utils import onset_entry_to_blinks
from .modality import infer_modality
from .ear import select_auto_threshold
from .peak_overlap_metric import (
    calculate_interval_overlap_ratio,
    interval_to_samples,
    is_peak_overlap_match,
)
from .report_utils import add_blink_plots_to_report, generate_epoch_report
from .velocity_utils import average_velocity

__all__ = [
    "create_annotation",
    "normalize_picks",
    "pick_ear_channels_from_info",
    "pick_ear_channels_from_raw",
    "require_channels",
    "slice_raw_to_segments",
    "slice_raw_into_mne_epochs",
    "slice_raw_into_epochs",
    "slice_into_mini_raws",
    "save_epoch_raws",
    "prepare_refined_segments",
    "to_epoch_indexed",
    "generate_epoch_report",
    "add_blink_plots_to_report",
    "onset_entry_to_blinks",
    "calculate_within_range",
    "calculate_good_ratio",
    "get_blink_statistic",
    "get_good_blink_mask",
    "get_max_blink",
    "average_velocity",
    "infer_modality",
    "calculate_interval_overlap_ratio",
    "interval_to_samples",
    "is_peak_overlap_match",
    "select_auto_threshold",
    "refine_local_maximum_stub",
    "refine_blinks_from_epochs",
    "slice_raw_into_mne_epochs_refine_annot",
]


def __getattr__(name: str):
    if name in {
        "calculate_good_ratio",
        "calculate_within_range",
        "get_blink_statistic",
        "get_good_blink_mask",
        "get_max_blink",
    }:
        from . import statistics_utils

        lookup = {
            "calculate_good_ratio": statistics_utils.calculate_good_ratio,
            "calculate_within_range": statistics_utils.calculate_within_range,
            "get_blink_statistic": statistics_utils.get_blink_statistic,
            "get_good_blink_mask": statistics_utils.get_good_blink_mask,
            "get_max_blink": statistics_utils.get_max_blink,
        }
        return lookup[name]
    if name == "slice_raw_into_mne_epochs_refine_annot":
        from pyblinker.segmentation.refinement import (
            slice_raw_into_mne_epochs_refine_annot,
        )

        return slice_raw_into_mne_epochs_refine_annot
    if name in {"refine_blinks_from_epochs", "refine_local_maximum_stub"}:
        from pyblinker.segmentation.refinement.eeg import (
            refine_blinks_from_epochs,
            refine_local_maximum_stub,
        )

        lookup = {
            "refine_blinks_from_epochs": refine_blinks_from_epochs,
            "refine_local_maximum_stub": refine_local_maximum_stub,
        }
        return lookup[name]
    raise AttributeError(f"module 'pyblinker.utils' has no attribute {name!r}")
