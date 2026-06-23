"""Channel-selection ablation: run the complete 3-stage pipeline per channel group.

For every channel-selection group (derived from the per-dataset brain-region YAML)
the *entire* Proposed pipeline is executed **on that channel subset only**:

    Stage A — autoreject PTP screening over the subset channels, combined with an
              aggregation rule (any / min2 / min3) to flag suspicious epochs;
    Stage B — robust threshold (median or mean centre) from the flagged epochs;
    Stage C — blink-region detection on the subset channels.

So each (group, rule, centre) condition is a self-contained detector, and
``(all, any, *)`` reproduces the standard Proposed pipeline as a built-in baseline.
The estimator comparison (median vs mean) is run for every group.

Reported per condition:
    * Stage-A epoch metrics vs. epoch-level ground truth (epoch is blink-containing
      iff it holds >=1 annotated blink): precision / recall / F1 / FPR / %flagged.
    * Downstream best-channel event precision / recall / F1.

Optionally, TP/FN/FP blink-region waveforms are collected for the butterfly report
(``butterfly_report.build_channel_selection_report``).
"""

from __future__ import annotations

import csv
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path

import mne
import numpy as np

from blink_evaluation import (
    enrich_absolute_times,
    evaluate_channels,
    load_annotation_as_reference,
)
from src.common.epoch_input import PreparedEpochDetectionInput, prepare_epoch_detection_input
from src.io.eeg_channels import load_brain_region_map, resolve_channel_names
from src.strategy_dbo_drop.autoreject_epoch_screener import screen_epochs_with_autoreject
from src.strategy_dbo_drop.runner import channel_results_strategy_dbo_drop
from tutorial.tutorial_utils import (
    extract_window,
    load_gt_annotations_for_pair,
    make_dataset_loaders,
    match_events,
    valid_epoch_indices_for_pair,
)

logger = logging.getLogger(__name__)

RULE_MIN_VOTES = {"any": 1, "min2": 2, "min3": 3}
DEFAULT_CENTER_METHODS = ("median", "mean")
DEFAULT_RULES = ("any",)
DEFAULT_BUTTERFLY_GROUPS = ("all", "frontal", "posterior")


# ---------------------------------------------------------------------------
# Channel-selection groups
# ---------------------------------------------------------------------------

def build_selection_groups(
    region_map: dict[str, list],
    available_ch_names: list[str],
    *,
    include_single_frontal: bool = True,
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
        ("parietal", parietal),
        ("occipital", occipital),
        ("posterior", union(
            "parietal_left", "parietal_right",
            "temporal_parietal_left", "temporal_parietal_right",
            "occipital_left", "occipital_right",
        )),
    ):
        if chs:
            groups[name] = chs

    if include_single_frontal:
        for ch in frontal:
            groups[f"single:{ch}"] = [ch]

    return {name: chs for name, chs in groups.items() if chs}


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


def _subset_prepared(prepared: PreparedEpochDetectionInput, subset_idx: np.ndarray):
    """Return a copy of *prepared* restricted to *subset_idx* channels."""
    return replace(
        prepared,
        data=prepared.data[:, subset_idx, :],
        channel_names=tuple(prepared.channel_names[i] for i in subset_idx),
    )


def _build_records(df, indices, signal_by_epoch, sfreq, window_s) -> list[dict]:
    records = []
    for idx in indices:
        row = df.loc[idx]
        dur = float(row["blink_duration"])
        w = extract_window(
            signal_by_epoch, int(row["epoch_index"]),
            float(row["blink_onset"]), dur, sfreq, window_s,
        )
        if w is None:
            continue
        records.append({
            "window": w, "duration": dur,
            "amplitude": float(np.max(np.abs(w))) * 1e6,
            "epoch_index": int(row["epoch_index"]),
        })
    return records


# ---------------------------------------------------------------------------
# Per-session driver
# ---------------------------------------------------------------------------

def run_one_session(
    pair: dict,
    *,
    region_yaml: Path,
    raja_region_yaml: Path,
    cao_region_yaml: Path,
    epoch_duration_s: float,
    std_threshold: float,
    center_methods: tuple[str, ...],
    rules: tuple[str, ...],
    autoreject_random_state: int,
    filter_low: float,
    filter_high: float,
    n_epochs: int | None,
    include_single_frontal: bool,
    butterfly_groups: tuple[str, ...] | None,
    window_s: float,
    peak_side_tolerance_s: float,
    verbose: bool,
) -> tuple[list[dict], list[dict]]:
    """Load a session once; run the full pipeline for every (group, rule, centre)."""
    dataset_loaders = make_dataset_loaders(
        raja_region_yaml=raja_region_yaml, cao_region_yaml=cao_region_yaml
    )
    raw = dataset_loaders[pair["dataset"]](pair["fif"])
    epochs = mne.make_fixed_length_epochs(
        raw, duration=epoch_duration_s, preload=True, verbose="ERROR"
    )
    if n_epochs is not None:
        epochs = epochs[:n_epochs]

    prepared = prepare_epoch_detection_input(
        epochs, pick_types_options={"eeg": True},
        filter_low=filter_low, filter_high=filter_high, resample_rate=100,
    )
    valid_epoch_indices = valid_epoch_indices_for_pair(pair, epochs, epoch_duration_s)
    if len(valid_epoch_indices) == 0:
        return [], []

    channel_names = list(prepared.channel_names)
    name_to_idx = {ch: i for i, ch in enumerate(channel_names)}
    valid_idx = np.asarray(valid_epoch_indices, dtype=int)

    # NOTE: Stage A (autoreject) is recomputed for EACH channel group on that
    # group's own channels (see the loop below), mirroring the straightforward
    # tutorial/10d approach. We deliberately do NOT learn thresholds once over the
    # full montage and reuse them per subset — that is more efficient but confusing.

    # Epoch-level ground truth + downstream evaluator annotations + morphology df.
    gt_raw = load_annotation_as_reference(pair["csv"], epoch_duration_s)
    if pair["dataset"] == "cao2018":
        gt_raw = gt_raw[gt_raw["epoch_index"].isin(valid_epoch_indices)].reset_index(drop=True)
    blink_global = {int(i) for i in gt_raw["epoch_index"].unique()}
    gt_annotations = load_gt_annotations_for_pair(pair, epoch_duration_s, valid_epoch_indices)
    ground_truth_df = enrich_absolute_times(gt_raw, epoch_duration_s)

    groups = build_selection_groups(
        load_brain_region_map(region_yaml), channel_names,
        include_single_frontal=include_single_frontal,
    )
    butterfly_set = set(butterfly_groups or ())

    metric_records: list[dict] = []
    morph_records: list[dict] = []

    for group_name, chs in groups.items():
        subset_idx = np.array([name_to_idx[c] for c in chs if c in name_to_idx], dtype=int)
        if subset_idx.size == 0:
            continue
        subset_prepared = _subset_prepared(prepared, subset_idx)

        for rule in rules:
            min_votes = RULE_MIN_VOTES[rule]
            if min_votes > subset_idx.size:
                continue

            for center in center_methods:
                if rule == "any":
                    # tutorial/10d style: the core recomputes Stage A (autoreject)
                    # on THIS group's channels, then Stage B/C — no threshold sharing.
                    setting = {
                        "autoreject_random_state": autoreject_random_state,
                        "std_threshold": std_threshold,
                        "center_method": center,
                        "min_flagged_epochs": 1,
                        "verbose": False,
                    }
                    channel_results = channel_results_strategy_dbo_drop(
                        subset_prepared, valid_epoch_indices, setting=setting
                    )
                    flagged_global = (
                        list(channel_results[0]["flagged_valid_epoch_indices"])
                        if channel_results else []
                    )
                else:
                    # Multi-vote rule: recompute this group's autoreject thresholds,
                    # require >= min_votes channels to exceed, then run Stage B/C on
                    # that flagged set via the override.
                    grp_screen = screen_epochs_with_autoreject(
                        subset_prepared, valid_epoch_indices,
                        random_state=autoreject_random_state, verbose=False,
                    )
                    grp_thr = np.array(
                        [grp_screen.channel_thresholds[ch]
                         for ch in subset_prepared.channel_names],
                        dtype=float,
                    )
                    grp_ptp = (subset_prepared.data[valid_idx, :, :].max(axis=-1)
                               - subset_prepared.data[valid_idx, :, :].min(axis=-1))
                    mask = (grp_ptp > grp_thr[np.newaxis, :]).sum(axis=1) >= min_votes
                    flagged_global = [int(valid_idx[i]) for i in np.where(mask)[0]]
                    setting = {
                        "autoreject_random_state": autoreject_random_state,
                        "std_threshold": std_threshold,
                        "center_method": center,
                        "min_flagged_epochs": 1,
                        "flagged_valid_epoch_indices_override": flagged_global,
                        "verbose": False,
                    }
                    channel_results = channel_results_strategy_dbo_drop(
                        subset_prepared, valid_epoch_indices, setting=setting
                    )

                stage_a = _stage_a_metrics(
                    set(flagged_global), blink_global, valid_epoch_indices
                )
                scored = evaluate_channels(
                    channel_results, gt_annotations, epoch_duration=epoch_duration_s
                )
                em = scored.best_eval_result.event_metrics
                metric_records.append({
                    "dataset": pair["dataset"], "session": pair["name"],
                    "selection": group_name, "rule": rule, "center_method": center,
                    "condition": f"{group_name}|{rule}|{center}",
                    "n_channels_used": int(subset_idx.size),
                    "n_valid": len(valid_epoch_indices),
                    **stage_a,
                    "best_channel": scored.best_channel,
                    "det_tp": em.tp, "det_fp": em.fp, "det_fn": em.fn,
                    "det_precision": em.precision, "det_recall": em.recall, "det_f1": em.f1,
                })

                # Butterfly morphology: representative config (rule=any, median).
                if (group_name in butterfly_set and rule == "any" and center == "median"):
                    sfreq = float(subset_prepared.sfreq)
                    signal_by_epoch = scored.best_channel_result["signal_by_epoch"]
                    best_predicted = scored.best_predicted
                    tp_i, fp_i, fn_i = match_events(
                        best_predicted, ground_truth_df, signal_by_epoch, sfreq,
                        peak_side_tolerance_s=peak_side_tolerance_s,
                    )
                    morph_records.append({
                        "dataset": pair["dataset"], "session": pair["name"],
                        "group": group_name, "center_method": center,
                        "best_channel": scored.best_channel, "sfreq": sfreq,
                        "n_tp": em.tp, "n_fp": em.fp, "n_fn": em.fn,
                        "tp_records": _build_records(best_predicted, tp_i, signal_by_epoch, sfreq, window_s),
                        "fp_records": _build_records(best_predicted, fp_i, signal_by_epoch, sfreq, window_s),
                        "fn_records": _build_records(ground_truth_df, fn_i, signal_by_epoch, sfreq, window_s),
                    })

    if verbose:
        logger.info("done  %s  (%d conditions)", pair["name"], len(metric_records))
    return metric_records, morph_records


def run_channel_ablation(
    pairs: list[dict],
    *,
    region_yaml: Path,
    raja_region_yaml: Path,
    cao_region_yaml: Path,
    epoch_duration_s: float = 30.0,
    std_threshold: float = 1.5,
    center_methods: tuple[str, ...] = DEFAULT_CENTER_METHODS,
    rules: tuple[str, ...] = DEFAULT_RULES,
    autoreject_random_state: int = 42,
    filter_low: float = 1.0,
    filter_high: float = 20.0,
    n_epochs: int | None = None,
    include_single_frontal: bool = True,
    butterfly_groups: tuple[str, ...] | None = DEFAULT_BUTTERFLY_GROUPS,
    window_s: float = 0.25,
    peak_side_tolerance_s: float = 0.01,
    use_multithread: bool = False,
    verbose: bool = False,
) -> tuple[list[dict], list[dict], list[str]]:
    """Run the channel ablation across *pairs*; return (metrics, morphology, errors)."""
    kwargs = dict(
        region_yaml=region_yaml,
        raja_region_yaml=raja_region_yaml, cao_region_yaml=cao_region_yaml,
        epoch_duration_s=epoch_duration_s, std_threshold=std_threshold,
        center_methods=center_methods, rules=rules,
        autoreject_random_state=autoreject_random_state,
        filter_low=filter_low, filter_high=filter_high, n_epochs=n_epochs,
        include_single_frontal=include_single_frontal,
        butterfly_groups=butterfly_groups, window_s=window_s,
        peak_side_tolerance_s=peak_side_tolerance_s, verbose=verbose,
    )

    metrics: list[dict] = []
    morph: list[dict] = []
    errors: list[str] = []

    if use_multithread:
        with ThreadPoolExecutor() as executor:
            future_map = {
                executor.submit(run_one_session, pair, **kwargs): pair["name"]
                for pair in pairs
            }
            for future in as_completed(future_map):
                name = future_map[future]
                try:
                    m_rec, mo_rec = future.result()
                    metrics.extend(m_rec)
                    morph.extend(mo_rec)
                    logger.info("done  %s", name)
                except Exception as exc:  # noqa: BLE001
                    logger.error("%s: %s", name, exc)
                    errors.append(f"ERROR  {name}: {exc}")
    else:
        for pair in pairs:
            logger.info("running  %s …", pair["name"])
            try:
                m_rec, mo_rec = run_one_session(pair, **kwargs)
                metrics.extend(m_rec)
                morph.extend(mo_rec)
            except Exception as exc:  # noqa: BLE001
                logger.error("%s: %s", pair["name"], exc)
                errors.append(f"ERROR  {pair['name']}: {exc}")
    return metrics, morph, errors


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def condition_summary_rows(records: list[dict], dataset_label: str) -> list[dict]:
    """Macro-average Stage-A and downstream metrics per (selection, rule, centre)."""
    buckets: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for r in records:
        buckets[(r["selection"], r["rule"], r["center_method"])].append(r)

    out: list[dict] = []
    for (selection, rule, center), bucket in buckets.items():
        def m(key: str) -> float:
            return float(np.mean([b[key] for b in bucket]))
        out.append({
            "dataset": dataset_label,
            "selection": selection, "rule": rule, "center_method": center,
            "n_sessions": len(bucket),
            "mean_n_channels": m("n_channels_used"),
            "stageA_precision": m("stageA_precision"),
            "stageA_recall": m("stageA_recall"),
            "stageA_f1": m("stageA_f1"),
            "stageA_fpr": m("stageA_fpr"),
            "pct_flagged": m("pct_flagged"),
            "det_precision": m("det_precision"),
            "det_recall": m("det_recall"),
            "det_f1": m("det_f1"),
        })
    out.sort(key=lambda r: (r["selection"].startswith("single:"),
                            r["selection"], r["rule"], -r["det_f1"]))
    return out


def print_condition_summary(records: list[dict], dataset_label: str) -> None:
    rows = condition_summary_rows(records, dataset_label)
    if not rows:
        print(f"\nNo records for {dataset_label}.")
        return
    header = (
        f"{'selection':<16}  {'rule':<5}  {'centre':<6}  {'nCh':>3}  "
        f"{'A_prec':>7}  {'A_rec':>7}  {'A_F1':>7}  {'A_FPR':>7}  {'%flag':>6}  "
        f"{'det_P':>7}  {'det_R':>7}  {'det_F1':>7}"
    )
    sep = "-" * len(header)
    print(f"\n{'=' * len(header)}")
    print(f"CHANNEL ABLATION SUMMARY — {dataset_label.upper()}  "
          f"(macro over {rows[0]['n_sessions']} sessions)")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)
    for r in rows:
        print(
            f"{r['selection']:<16}  {r['rule']:<5}  {r['center_method']:<6}  "
            f"{r['mean_n_channels']:>3.0f}  "
            f"{r['stageA_precision']:>7.4f}  {r['stageA_recall']:>7.4f}  "
            f"{r['stageA_f1']:>7.4f}  {r['stageA_fpr']:>7.4f}  {r['pct_flagged']:>6.2f}  "
            f"{r['det_precision']:>7.4f}  {r['det_recall']:>7.4f}  {r['det_f1']:>7.4f}"
        )
    print(f"{'=' * len(header)}\n")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


__all__ = [
    "RULE_MIN_VOTES",
    "DEFAULT_CENTER_METHODS",
    "DEFAULT_RULES",
    "DEFAULT_BUTTERFLY_GROUPS",
    "build_selection_groups",
    "run_one_session",
    "run_channel_ablation",
    "condition_summary_rows",
    "print_condition_summary",
    "write_csv",
]
