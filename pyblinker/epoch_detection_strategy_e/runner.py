"""Strategy E evaluation runner.

Dispatches any E variant by name, producing the standardized
``{channel, df_positions, mapped_candidates, signal_by_epoch}`` format
required by :func:`~pyblinker.evaluation_runner.score_channel_results`.

For pair-level (multi-channel fusion) variants (e_or_fusion, e_vote_2of3,
e11_lane_route, e9_frontal_avg), a single channel result dict is returned
where ``channel`` is the virtual-channel name.
"""

from __future__ import annotations

import mne
import pandas as pd

from pyblinker.analysis.lane_evaluation import LaneScoringResult
from pyblinker.common.bad_epochs import get_valid_epoch_indices
from pyblinker.common.epoch_input import PreparedEpochDetectionInput, prepare_epoch_detection_input
from pyblinker.common.pipeline_utils import build_signal_by_epoch
from pyblinker.evaluation_runner import score_channel_results
from pyblinker.matching.blink_matching import enrich_absolute_times

from .core import run_e_base_channel
from .derivatives import DERIVATIVE_CHANNEL_RUNNERS
from .expand_bridge import EXPAND_BRIDGE_CHANNEL_RUNNERS
from .remaining_rules import PAIR_LEVEL_RUNNERS, PER_CHANNEL_RUNNERS
from .second_derivatives import SECOND_DERIVATIVE_CHANNEL_RUNNERS, run_e9_frontal_avg
from .soft_shrink import run_e6_soft_shrink_channel

# ── Unified dispatch tables ────────────────────────────────────────────────────

_PER_CHANNEL_DISPATCH: dict[str, object] = {
    "e_base": run_e_base_channel,
    "e6_soft_shrink": run_e6_soft_shrink_channel,
    **DERIVATIVE_CHANNEL_RUNNERS,
    **SECOND_DERIVATIVE_CHANNEL_RUNNERS,
    **PER_CHANNEL_RUNNERS,
    **EXPAND_BRIDGE_CHANNEL_RUNNERS,
}

_PAIR_LEVEL_DISPATCH: dict[str, object] = {
    "e9_frontal_avg": run_e9_frontal_avg,
    **PAIR_LEVEL_RUNNERS,
}

ALL_E_VARIANTS: list[str] = sorted(_PER_CHANNEL_DISPATCH) + sorted(_PAIR_LEVEL_DISPATCH)


def channel_results_strategy_e(
    prepared: PreparedEpochDetectionInput,
    valid_epoch_indices: list[int],
    variant: str = "e_base",
) -> list[dict]:
    """Run Strategy E variant ``variant`` and return standardized channel_results.

    Each dict has keys: ``channel``, ``df_positions``,
    ``mapped_candidates``, ``signal_by_epoch``.

    For per-channel variants, one dict per channel is returned.
    For pair-level variants, a single dict with a virtual-channel name is returned.

    Parameters
    ----------
    prepared:
        Prepared epoch detection input.
    valid_epoch_indices:
        Valid epoch indices to process.
    variant:
        Strategy E variant name.  See :data:`ALL_E_VARIANTS` for all options.
    """
    if variant in _PAIR_LEVEL_DISPATCH:
        runner = _PAIR_LEVEL_DISPATCH[variant]
        candidates: pd.DataFrame = runner(prepared, valid_epoch_indices)  # type: ignore[call-arg]
        ch_names = candidates["channel"].unique().tolist() if not candidates.empty else [variant]
        results: list[dict] = []
        for ch_name in ch_names:
            ch_cands = candidates[candidates["channel"] == ch_name].copy()
            results.append(
                {
                    "channel": ch_name,
                    "df_positions": ch_cands,
                    "mapped_candidates": ch_cands,
                    "signal_by_epoch": {},
                }
            )
        return results

    if variant not in _PER_CHANNEL_DISPATCH:
        raise ValueError(
            f"Unknown Strategy E variant {variant!r}.  "
            f"Available: {sorted(_PER_CHANNEL_DISPATCH) + sorted(_PAIR_LEVEL_DISPATCH)}"
        )

    runner = _PER_CHANNEL_DISPATCH[variant]
    results = []
    for ch_idx, channel_name in enumerate(prepared.channel_names):
        candidates = runner(prepared, ch_idx, channel_name, valid_epoch_indices)  # type: ignore[call-arg]
        results.append(
            {
                "channel": channel_name,
                "df_positions": candidates,
                "mapped_candidates": candidates,
                "signal_by_epoch": build_signal_by_epoch(prepared, ch_idx),
            }
        )
    return results


def run_strategy_e(
    epochs: mne.Epochs,
    ground_truth_raw: pd.DataFrame,
    *,
    variant: str = "e_base",
    filter_low: float = 1.0,
    filter_high: float = 20.0,
    resample_rate: float | None = None,
    epoch_duration: float = 60.0,
    peak_side_tolerance_s: float = 0.01,
) -> LaneScoringResult:
    """Run Strategy E variant end-to-end on ``epochs`` and return scored results."""
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=filter_low,
        filter_high=filter_high,
        resample_rate=resample_rate,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)
    channel_results = channel_results_strategy_e(prepared, valid_epoch_indices, variant=variant)
    ground_truth = enrich_absolute_times(ground_truth_raw, epoch_duration)
    return score_channel_results(
        channel_results,
        ground_truth,
        n_epochs=len(epochs),
        sfreq=float(prepared.sfreq),
        epoch_duration=epoch_duration,
        peak_side_tolerance_s=peak_side_tolerance_s,
    )


__all__ = ["ALL_E_VARIANTS", "channel_results_strategy_e", "run_strategy_e"]
