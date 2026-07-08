"""Channel-selection ablation: run the complete 3-stage pipeline per channel group.

For every channel-selection group (derived from the per-dataset brain-region YAML)
the *entire* Proposed pipeline is executed **on that channel subset only**:

    Stage A — autoreject PTP screening over the subset channels;
    Stage B — robust threshold (median or mean centre) from the flagged epochs;
    Stage C — blink-region detection on the subset channels.

So each (group, centre) condition is a self-contained detector, and
``(all, median)`` reproduces the standard Proposed pipeline as a built-in baseline.

Reported per condition:
    * Stage-A epoch metrics vs. epoch-level ground truth (epoch is blink-containing
      iff it holds >=1 annotated blink): precision / recall / F1 / FPR / %flagged.
    * Downstream best-channel event precision / recall / F1.
"""

from __future__ import annotations

import csv
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mne

from blink_evaluation import (
    evaluate_channels,
    load_annotation_as_reference,
)
from src.common.epoch_input import prepare_epoch_detection_input
from src.io.eeg_channels import (
    load_brain_region_channels,
    load_brain_region_map,
    load_raw_with_brain_channels,
    resolve_channel_names,
)
from pyblinker.double_thresholding import blink_position_strategy_dbo
from src.utils.experiment_utils import load_gt_annotations_for_pair, valid_epoch_indices_for_pair


logger = logging.getLogger(__name__)

DEFAULT_CENTER_METHODS = ("median", "mean")
DEFAULT_RULES = ("any",)


# ---------------------------------------------------------------------------
# Channel-selection groups
# ---------------------------------------------------------------------------

def build_selection_groups(
    region_map: dict[str, list],
    available_ch_names: list[str],
    # include_single_frontal: bool = True,
) -> dict[str, list[str]]:
    """Return ``{group_name: [actual_channel_name, ...]}`` selection groups."""
    resolved = {
        region: resolve_channel_names(entries, available_ch_names)
        for region, entries in region_map.items()
    }

    def union(*regions: str) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for region in regions:
            for ch in resolved.get(region, []):
                if ch not in seen:
                    out.append(ch)
                    seen.add(ch)
        return out

    frontal = union("frontal_left", "frontal_right")
    central = union("central_left", "central_right")
    parietal = union(
        "parietal_left", "parietal_right",
        "temporal_parietal_left", "temporal_parietal_right",
    )
    occipital = union("occipital_left", "occipital_right")

    groups: dict[str, list[str]] = {"all": union(*resolved.keys())}
    for name, chs in (
        ("frontal", frontal),
        ("frontal_left", resolved.get("frontal_left", [])),
        ("frontal_right", resolved.get("frontal_right", [])),
        ("central", central),
        ("central_left", resolved.get("central_left", [])),
        ("central_right", resolved.get("central_right", [])),
        ("parietal", parietal),
        ("parietal_left", resolved.get("parietal_left", [])),
        ("parietal_right", resolved.get("parietal_right", [])),
        ("occipital", occipital),
        ("occipital_left", resolved.get("occipital_left", [])),
        ("occipital_right", resolved.get("occipital_right", [])),
        ("posterior", union(
            "parietal_left", "parietal_right",
            "temporal_parietal_left", "temporal_parietal_right",
            "occipital_left", "occipital_right",
        )),
    ):
        if chs:
            groups[name] = chs

    return {name: chs for name, chs in groups.items() if chs}


def selection_group_names(
    pair: dict,
    *,
    region_yaml: Path,
    # include_single_frontal: bool = True,
    groups_filter: set[str] | None = None,
) -> list[str]:
    """List the selection-group names available for *pair* (cheap: no data load).

    Reads only the recording's channel names (``preload=False``) so a caller can
    enumerate the groups and then invoke :func:`run_one_session` once per group.
    ``groups_filter`` restricts the result to the requested names (preserving order).
    """
    region_map = load_brain_region_map(region_yaml)
    brain_channels = load_brain_region_channels(region_yaml)
    raw = mne.io.read_raw_fif(str(pair["fif"]), preload=False, verbose="ERROR")
    available = resolve_channel_names(brain_channels, raw.ch_names)
    groups = build_selection_groups(
        region_map, available,
        # include_single_frontal=include_single_frontal,
    )
    names = list(groups)

    # names = list(groups)
    if groups_filter == {"all"}:
        return names
    if groups_filter is not None:
        if isinstance(groups_filter, str):
            groups_filter = {groups_filter}
        else:
            groups_filter = set(groups_filter)

        names = [name for name in names if name in groups_filter]

    return names


# ---------------------------------------------------------------------------
# Stage-A flagging + epoch-level metrics
# ---------------------------------------------------------------------------

def _stage_a_metrics(
    flagged_global: set[int],
    blink_global: set[int],
    valid_global: list[int],
) -> dict:
    """Epoch-level precision/recall/F1/FPR of Stage-A selection over valid epochs."""
    valid_set = set(valid_global)
    blink = blink_global & valid_set
    flagged = flagged_global & valid_set
    tp = len(flagged & blink)
    fp = len(flagged - blink)
    fn = len(blink - flagged)
    tn = len(valid_set) - tp - fp - fn
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    pct_flagged = len(flagged) / len(valid_set) if valid_set else 0.0
    return {
        "stageA_tp": tp, "stageA_fp": fp, "stageA_fn": fn, "stageA_tn": tn,
        "stageA_precision": precision, "stageA_recall": recall, "stageA_f1": f1,
        "stageA_fpr": fpr, "pct_flagged": pct_flagged,
        "n_flagged": len(flagged), "n_blink_epochs": len(blink),
    }


# ---------------------------------------------------------------------------
# Per-session driver
# ---------------------------------------------------------------------------
def build_condition(group_name, center, channel):
    return f"{center}__{group_name}__{channel}"

def run_one_session(
    pair: dict,
    *,
    region_yaml: Path,
    epoch_duration_s: float,
    std_threshold: float,
    center_methods: tuple[str, ...],
    autoreject_random_state: int,
    filter_low: float,
    filter_high: float,
    resample_rate: float,
    use_epoch_health: bool,
    groups_filter: set[str] | None,
    verbose: bool,
    min_flagged_epochs: int = 1,
) -> list[dict]:
    """Run blink_position_strategy_dbo for every (group, centre) in a session.

    Flow: load raw → pick union of needed channels → epoch → prepare (once) →
    for each (rule, centre), detect and record metrics.

    groups_filter
        When not None, only groups whose name is in this set are evaluated.
        ``None`` runs all groups built by :func:`build_selection_groups`.
    """
    region_map = load_brain_region_map(region_yaml)

    brain_channels = load_brain_region_channels(region_yaml)
    raw = load_raw_with_brain_channels(pair["fif"], brain_channels)

    groups = build_selection_groups(
        region_map, list(raw.ch_names),
        # include_single_frontal=include_single_frontal,
    )
    if groups_filter is not None:
        groups = {name: chs for name, chs in groups.items() if name in groups_filter}
    if not groups:
        return []
    if len(groups) != 1:
        raise ValueError(
            "run_one_session processes exactly ONE selection group/channel per call "
            f"(got {sorted(groups)}). Pass a single-group groups_filter and loop over "
            "groups in the caller (see exp1_channel_selection_raja.py)."
        )

    # Pick only this group's channels — the whole pipeline runs on this subset only.
    needed = sorted({ch for chs in groups.values() for ch in chs})
    raw.pick(needed)

    epochs = mne.make_fixed_length_epochs(
        raw, duration=epoch_duration_s, preload=True, verbose="ERROR"
    )
    if use_epoch_health:
        logger.info("using epoch health to filter valid epochs for %s", pair["name"])
        valid_epoch_indices = valid_epoch_indices_for_pair(pair, epochs, epoch_duration_s)
    else:
        valid_epoch_indices = list(range(len(epochs)))
    if not valid_epoch_indices:
        return []

    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=filter_low, filter_high=filter_high, resample_rate=resample_rate,
    )

    gt_annotations = load_gt_annotations_for_pair(pair, epoch_duration_s, valid_epoch_indices)

    # prepared already contains exactly this group's picked channels — no subsetting.
    group_name = next(iter(groups))
    n_channels = len(prepared.channel_names)
    metric_records: list[dict] = []

    for center in center_methods:
        setting = {
                "autoreject_random_state": autoreject_random_state,
                "std_threshold": std_threshold,
                "center_method": center,
                "min_flagged_epochs": min_flagged_epochs,
                "verbose": True,
            }

        # The blink_position_strategy_dbo will return per channel result
        channel_results = blink_position_strategy_dbo(
                prepared, valid_epoch_indices, setting=setting
            )
        # Stage A+B threshold is shared across ALL channels in the group and Stage C
        # (detection) runs per-channel, so evaluate_channels scores every channel in
        # one pass and its lane_summary already has one row per channel.
        scored = evaluate_channels(
                channel_results, gt_annotations, epoch_duration=epoch_duration_s
            )
        # lane_summary has one row per channel with channel/tp/fp/fn/precision/recall/f1.
        # This is the schema used downstream by exp1_write_results()/
        # exp1_step_b_get_best_region_channel.py — no renaming here.
        lane = scored.lane_summary.assign(
            dataset=pair["dataset"],
            session=pair["name"],
            selection=group_name,
            center_method=center,
            condition=scored.lane_summary["channel"].map(
                lambda ch: build_condition(group_name, center, ch)
            ),
            n_channels_used=n_channels,
            n_valid=len(valid_epoch_indices),
        )

        metric_records.extend(lane.to_dict("records"))

    if verbose:
        logger.info("done  %s  (%d conditions)", pair["name"], len(metric_records))
        logger.info(lane.to_dict("records"))
        best = max(metric_records, key=lambda r: r["f1"])
        logger.info(
            "best  %s  channel=%s center=%s f1=%.3f precision=%.3f recall=%.3f",
            pair["name"], best["channel"], best["center_method"],
            best["f1"], best["precision"], best["recall"],
        )
    return metric_records


def run_channel_ablation(
    pairs: list[dict],
    *,
    region_yaml: Path,
    epoch_duration_s: float = 30.0,
    std_threshold: float = 1.5,
    center_methods: tuple[str, ...] = DEFAULT_CENTER_METHODS,
    autoreject_random_state: int = 42,
    filter_low: float = 1.0,
    filter_high: float = 20.0,
    resample_rate: float = 100.0,
    use_epoch_health: bool = False,
    groups_filter: set[str] | None = None,
    use_multithread: bool = False,
    verbose: bool = False,
) -> tuple[list[dict], list[str]]:
    """Run the channel ablation across *pairs*; return (metrics, errors).

    Each pair is expanded into its selection groups (filtered by ``groups_filter``)
    and :func:`run_one_session` is invoked once per group, so every group is a
    self-contained detector on its own channel subset.
    """
    run_kwargs = dict(
        region_yaml=region_yaml,
        epoch_duration_s=epoch_duration_s,
        std_threshold=std_threshold,
        center_methods=center_methods,
        groups_filter=groups_filter,
        autoreject_random_state=autoreject_random_state,
        filter_low=filter_low,
        filter_high=filter_high,
        resample_rate=resample_rate,
        use_epoch_health=use_epoch_health, verbose=verbose,
    )

    def _run_pair(pair: dict) -> list[dict]:
        names = selection_group_names(
            pair, region_yaml=region_yaml,
            groups_filter=groups_filter,
        )
        rows: list[dict] = []

        # For experiment 1, we usually select `all`, and this loop will process all the possible channel combination, or selected individual channel to the proposed algorith
        for group in names:
            logger.info(f"Processing group: {group}, as we subject it into the 3 stages algorithm")
            group_run_kwargs = {
                **run_kwargs,
                "groups_filter": {group},  # replaces any old value in run_kwargs
            }
            rows.extend(
                run_one_session(
                    pair,
                    **group_run_kwargs,
                )
            )
        return rows

    metrics: list[dict] = []
    errors: list[str] = []

    if use_multithread:
        with ThreadPoolExecutor() as executor:
            future_map = {
                executor.submit(_run_pair, pair): pair["name"]
                for pair in pairs
            }
            for future in as_completed(future_map):
                name = future_map[future]
                try:
                    metrics.extend(future.result())
                    logger.info("done  %s", name)
                except Exception as exc:  # noqa: BLE001
                    logger.error("%s: %s", name, exc)
                    errors.append(f"ERROR  {name}: {exc}")
    else:
        for pair in pairs:
            logger.info("running  %s …", pair["name"])
            try:
                metrics.extend(_run_pair(pair))
            except Exception as exc:  # noqa: BLE001
                logger.error("%s: %s", pair["name"], exc)
                errors.append(f"ERROR  {pair['name']}: {exc}")
    return metrics, errors


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    # Build union of all keys so mixed-schema rows (e.g. baseline vs. proposed)
    # don't cause DictWriter to raise on extra fields.
    all_keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for k in row.keys():
            if k not in seen:
                all_keys.append(k)
                seen.add(k)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=all_keys, extrasaction="ignore", restval="")
        writer.writeheader()
        writer.writerows(rows)


__all__ = [
    "DEFAULT_CENTER_METHODS",
    "DEFAULT_RULES",
    "build_selection_groups",
    "selection_group_names",
    "run_one_session",
    "run_channel_ablation",
    "write_csv",
]
