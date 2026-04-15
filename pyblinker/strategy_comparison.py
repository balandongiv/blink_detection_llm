"""Cross-strategy comparison runner.

Runs a configurable set of blink-detection strategies on the same prepared
epoch data and reports per-strategy scored metrics via the standardized
:func:`~pyblinker.evaluation_runner.score_channel_results` flow.

Replaces the ``tutorial/22_strategy_comparison_batch.py`` batch script with a
clean, reusable interface that works with either the development dataset or the
public sample-data batch dataset.

Usage example (batch dataset)
------------------------------
::

    import mne
    from pyblinker.dataset_config import BATCH_DATASET, EPOCH_DURATION_S
    from pyblinker.common.validation import load_reference_blink_table
    from pyblinker.matching.blink_matching import enrich_absolute_times
    from pyblinker.strategy_comparison import run_strategy_comparison

    epochs = mne.read_epochs(str(BATCH_DATASET.fif_path), preload=True)
    ground_truth_raw = load_reference_blink_table(BATCH_DATASET.csv_path)
    ground_truth = enrich_absolute_times(ground_truth_raw, EPOCH_DURATION_S)

    results = run_strategy_comparison(
        epochs,
        ground_truth,
        epoch_duration=EPOCH_DURATION_S,
        strategies=["strategy_a", "strategy_b", "strategy_d", "e_base", "e6_soft_shrink"],
    )
    print(results.to_string(index=False))
"""

from __future__ import annotations

import traceback
from time import perf_counter

import mne
import pandas as pd

from pyblinker.analysis.lane_evaluation import LaneScoringResult
from pyblinker.dataset_config import EPOCH_DURATION_S, FILTER_HIGH, FILTER_LOW, PEAK_SIDE_TOLERANCE_S
from pyblinker.common.bad_epochs import get_valid_epoch_indices
from pyblinker.common.epoch_input import prepare_epoch_detection_input
from pyblinker.strategy_a.runner import channel_results_strategy_a
from pyblinker.strategy_b.runner import blink_position_strategy_b
from pyblinker.strategy_c.runner import blink_position_strategy_c
from pyblinker.strategy_d.runner import blink_position_strategy_d
from pyblinker.strategy_e.runner import channel_results_strategy_e
from pyblinker.evaluation_runner import score_channel_results

from pyblinker.strategy_c import (
    AUTOREJECT_BAYESIAN_OPTIMIZATION,
    epoch_detection_strategy_c_autoreject,
)

_DISABLE_BACKBONE = ("__NO_BACKBONE__",)

# ── Default strategy list ──────────────────────────────────────────────────────
DEFAULT_STRATEGIES: list[str] = [
    "strategy_a",
    "strategy_b",
    "strategy_c",
    "strategy_d",
    "e_base",
]


def _run_one_strategy(
    strategy: str,
    epochs: mne.Epochs,
    ground_truth: pd.DataFrame,
    *,
    filter_low: float,
    filter_high: float,
    epoch_duration: float,
    peak_side_tolerance_s: float,
) -> LaneScoringResult:
    """Run one named strategy and return its :class:`~pyblinker.analysis.lane_evaluation.LaneScoringResult`."""
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=filter_low,
        filter_high=filter_high,
        resample_rate=None,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)
    n_epochs = len(epochs)
    sfreq = float(prepared.sfreq)

    if strategy == "strategy_a":
        channel_results = channel_results_strategy_a(prepared, valid_epoch_indices)

    elif strategy == "strategy_b":
        channel_results = blink_position_strategy_b(prepared, valid_epoch_indices)

    elif strategy == "strategy_c":
        detector = epoch_detection_strategy_c_autoreject(
            epochs,
            visualize=False,
            filter_low=filter_low,
            filter_high=filter_high,
            resample_rate=None,
            n_jobs=1,
            use_multiprocessing=False,
            stage1_channels=_DISABLE_BACKBONE,
            stage1_threshold_scope="per_channel",
            stage1_rescale_threshold=True,
            autoreject_random_state=42,
            autoreject_method=AUTOREJECT_BAYESIAN_OPTIMIZATION,
            autoreject_augment=False,
        )
        prepared_c = detector.prepare_epoch_data()
        channel_results = blink_position_strategy_c(detector, prepared_c, valid_epoch_indices)
        # Use strategy C's own prepared for sfreq
        sfreq = float(prepared_c.sfreq)

    elif strategy == "strategy_d":
        channel_results = blink_position_strategy_d(prepared, valid_epoch_indices)

    else:
        # All Strategy E variants (e_base, e6_soft_shrink, e1_median, etc.)
        channel_results = channel_results_strategy_e(prepared, valid_epoch_indices, variant=strategy)

    return score_channel_results(
        channel_results,
        ground_truth,
        n_epochs=n_epochs,
        sfreq=sfreq,
        epoch_duration=epoch_duration,
        peak_side_tolerance_s=peak_side_tolerance_s,
    )


def run_strategy_comparison(
    epochs: mne.Epochs,
    ground_truth: pd.DataFrame,
    *,
    strategies: list[str] | None = None,
    filter_low: float = FILTER_LOW,
    filter_high: float = FILTER_HIGH,
    epoch_duration: float = EPOCH_DURATION_S,
    peak_side_tolerance_s: float = PEAK_SIDE_TOLERANCE_S,
) -> pd.DataFrame:
    """Run multiple strategies on the same epochs and return a comparison summary.

    Parameters
    ----------
    epochs:
        Pre-loaded MNE Epochs object.
    ground_truth:
        Enriched ground-truth DataFrame (must already have ``absolute_onset_s``
        and ``absolute_offset_s`` columns from
        :func:`~pyblinker.matching.blink_matching.enrich_absolute_times`).
    strategies:
        Strategy names to run.  Defaults to :data:`DEFAULT_STRATEGIES`.
        Pass any :data:`~pyblinker.epoch_detection_strategy_e.runner.ALL_E_VARIANTS`
        name for Strategy E variants.
    filter_low:
        Band-pass filter lower edge in Hz.
    filter_high:
        Band-pass filter upper edge in Hz.
    epoch_duration:
        Epoch duration in seconds.
    peak_side_tolerance_s:
        Peak-overlap tolerance in seconds.

    Returns
    -------
    pd.DataFrame
        One row per strategy with columns:
        ``strategy``, ``best_channel``, ``tp``, ``fp``, ``fn``,
        ``precision``, ``recall``, ``f1``, ``elapsed_s``, ``error``.
    """
    if strategies is None:
        strategies = DEFAULT_STRATEGIES

    rows: list[dict] = []
    for strategy in strategies:
        row: dict = {
            "strategy": strategy,
            "best_channel": "",
            "tp": 0,
            "fp": 0,
            "fn": 0,
            "precision": float("nan"),
            "recall": float("nan"),
            "f1": float("nan"),
            "elapsed_s": float("nan"),
            "error": "",
        }
        started = perf_counter()
        try:
            scored = _run_one_strategy(
                strategy,
                epochs,
                ground_truth,
                filter_low=filter_low,
                filter_high=filter_high,
                epoch_duration=epoch_duration,
                peak_side_tolerance_s=peak_side_tolerance_s,
            )
            m = scored.best_metrics
            row.update(
                {
                    "best_channel": scored.best_result["channel"] if scored.best_result else "",
                    "tp": int(m.true_positives),
                    "fp": int(m.false_positives),
                    "fn": int(m.false_negatives),
                    "precision": float(m.precision),
                    "recall": float(m.recall),
                    "f1": float(m.f1),
                }
            )
        except Exception:  # noqa: BLE001
            row["error"] = traceback.format_exc()
        row["elapsed_s"] = perf_counter() - started
        rows.append(row)

    return pd.DataFrame(rows)


def aggregate_comparison(comparison_df: pd.DataFrame) -> pd.DataFrame:
    """Compute micro- and macro-averaged metrics from a comparison DataFrame.

    Parameters
    ----------
    comparison_df:
        Output of :func:`run_strategy_comparison` or a concatenation of
        multiple calls (one row per strategy per pair).  Must have
        ``strategy``, ``tp``, ``fp``, ``fn``, ``precision``, ``recall``,
        ``f1``, ``error`` columns.

    Returns
    -------
    pd.DataFrame
        One row per strategy with pooled micro-averaged and macro-averaged
        precision, recall, and F1.
    """
    agg_rows: list[dict] = []
    for strategy, grp in comparison_df.groupby("strategy"):
        ok = grp[grp["error"].isna() | (grp["error"] == "")]
        total_tp = int(ok["tp"].sum())
        total_fp = int(ok["fp"].sum())
        total_fn = int(ok["fn"].sum())
        micro_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else float("nan")
        micro_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else float("nan")
        micro_f1 = (
            2.0 * micro_p * micro_r / (micro_p + micro_r)
            if (micro_p + micro_r) > 0
            else float("nan")
        )
        agg_rows.append(
            {
                "strategy": strategy,
                "n_pairs_successful": len(ok),
                "n_pairs_failed": len(grp) - len(ok),
                "total_tp": total_tp,
                "total_fp": total_fp,
                "total_fn": total_fn,
                "micro_precision": micro_p,
                "micro_recall": micro_r,
                "micro_f1": micro_f1,
                "macro_precision": float(ok["precision"].mean()) if not ok.empty else float("nan"),
                "macro_recall": float(ok["recall"].mean()) if not ok.empty else float("nan"),
                "macro_f1": float(ok["f1"].mean()) if not ok.empty else float("nan"),
            }
        )
    return pd.DataFrame(agg_rows)


__all__ = [
    "DEFAULT_STRATEGIES",
    "aggregate_comparison",
    "run_strategy_comparison",
]
