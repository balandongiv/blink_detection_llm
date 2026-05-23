"""dbo_drop recall improvement experiments — drowsy_driving_raja_processed.

Approach G1: Two-Tier Peak Confirmation
-----------------------------------------
Detection gate (Stage C) uses std_threshold=1.5.  Stage D applies a stricter confirmation gate: each event is kept only if its peak >=
  center + k_confirm * dispersion
(center/dispersion from Stage B — no new data needed).

Approach G3: Epoch-Type Split Threshold
-----------------------------------------
Autoreject's flagging signal is used to apply two different thresholds:
  - Flagged epochs (blink-heavy): center + k_flagged * dispersion  (strict)
  - Non-flagged epochs (possibly quiet): center + k_nonflagged * dispersion  (permissive)
The non-flagged threshold is estimated from ALL valid epochs (more inclusive).

Hypothesis: flagged epochs already contain strong blinks (strict gate is safe);
non-flagged epochs may contain weak blinks that a permissive gate can catch.

Baselines (drowsy_driving_raja_processed, 11 pairs, from G1 run):
  kleifges:      micro_R=0.9350  micro_F1=0.5960  TP=2746  FP=3531  FN=191
  G1_kc_none:    micro_R=0.9353  micro_F1=0.6497  TP=2747  FP=2772  FN=190
  G1_kc2.0:      micro_R=0.9350  micro_F1=0.6683  TP=2746  FP=2535  FN=191

Success criteria (any variant must satisfy ALL three):
  1. micro_R  > kleifges micro_R = 0.9350   (must not regress below kleifges)
  2. micro_F1 > G1_kc_none = 0.6497         (must improve on dbo_drop baseline)
  3. micro_F1 > kleifges micro_F1 = 0.5960  (must beat kleifges on F1)
"""

from __future__ import annotations

import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mne

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blink_evaluation import evaluate_channels, load_ground_truth_annotations
from src.common.bad_epochs import get_valid_epoch_indices
from src.common.epoch_input import prepare_epoch_detection_input
from src.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels
from pyblinker.strategies import kleifges_strategy
from src.strategy_dbo_drop.runner import channel_results_strategy_dbo_drop
from tutorial.tutorial_utils import discover_raja_pairs, setup_tutorial_logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dataset root paths (same as tutorial 20)
# ---------------------------------------------------------------------------
ANNOTATION_BASE_DIR = Path(r"D:\dataset\drowsy_driving_raja\human_label_annotation_eeg")
PROCESSED_BASE_DIR  = Path(r"D:\dataset\drowsy_driving_raja_processed")
BRAIN_REGION_YAML   = REPO_ROOT / "brain_region.yaml"


# ---------------------------------------------------------------------------
# Shared parameters (same as tutorial 20)
# ---------------------------------------------------------------------------
EPOCH_DURATION_S      = 60.0
FILTER_LOW            = 1.0
FILTER_HIGH           = 20.0
RESAMPLE_RATE         = None
N_EPOCHS: int | None  = None   # set to small int for quick debugging

# ---------------------------------------------------------------------------
# Strategy F fixed settings
# ---------------------------------------------------------------------------
AUTOREJECT_RANDOM_STATE = 42
CENTER_METHOD           = "median"
MIN_FLAGGED_EPOCHS      = 1
VERBOSE                 = False   # set True for per-pair threshold diagnostics

# ---------------------------------------------------------------------------
# G1: Two-Tier Peak Confirmation (kept as reference, detection gate k=1.5)
# ---------------------------------------------------------------------------
STD_THRESHOLD   = 1.5
K_CONFIRM_SWEEP = [None, 2.0]   # baseline + best G1 variant for context

# ---------------------------------------------------------------------------
# G3: Epoch-Type Split Threshold experiment
#
# k_flagged    ∈ {3.5, 3.0, 2.5}  — strict gate for autoreject-flagged epochs
# k_nonflagged ∈ {1.5, 1.0}       — permissive gate for non-flagged epochs
# All 6 combinations are tested; focus on k_flagged=3.5 + k_nonflagged=1.5 first.
# ---------------------------------------------------------------------------
K_FLAGGED_SWEEP    = [3.5, 3.0, 2.5]
K_NONFLAGGED_SWEEP = [1.5, 1.0]

USE_MULTITHREAD: bool = True




# ---------------------------------------------------------------------------
# Build the list of experiment variants
#
# Each variant is a dict with:
#   label         - display string (used as "strategy" in result rows)
#   std_threshold - float
#   center_method - "median" or "mean"
# ---------------------------------------------------------------------------

def _build_variants() -> list[dict]:
    """Build the experiment grid: G1 reference variants + G3 epoch-split variants."""
    variants = []

    # --- G1 reference (baseline + best prior result for comparison) ---
    for k_c in K_CONFIRM_SWEEP:
        lbl = f"G1_kc{k_c:.1f}" if k_c is not None else "G1_kc_none"
        variants.append({
            "label": lbl,
            "std_threshold": STD_THRESHOLD,
            "center_method": CENTER_METHOD,
            "max_event_len": None,
            "k_confirm": k_c,
            "k_flagged": None,
            "k_nonflagged": None,
        })

    # --- G3: epoch-type split threshold ---
    for k_f in K_FLAGGED_SWEEP:
        for k_nf in K_NONFLAGGED_SWEEP:
            variants.append({
                "label": f"G3_kf{k_f:.1f}_knf{k_nf:.1f}",
                "std_threshold": STD_THRESHOLD,  # fallback only (unused in G3 mode)
                "center_method": CENTER_METHOD,
                "max_event_len": None,
                "k_confirm": None,
                "k_flagged": k_f,
                "k_nonflagged": k_nf,
            })

    return variants


VARIANTS = _build_variants()


# ---------------------------------------------------------------------------
# Per-pair runner
# ---------------------------------------------------------------------------

def run_one(pair_name: str, fif_path: Path, csv_path: Path, variant_label: str,
            std_threshold: float, center_method: str,
            max_event_len=None, k_confirm=None,
            k_flagged=None, k_nonflagged=None) -> dict:
    """Run one strategy variant on one dataset pair and return metrics."""
    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    raw = load_raw_with_brain_channels(fif_path, brain_channels)
    epochs = mne.make_fixed_length_epochs(raw, duration=EPOCH_DURATION_S, preload=True,
                                          verbose="ERROR")
    if N_EPOCHS is not None:
        epochs = epochs[:N_EPOCHS]

    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)
    gt_annotations = load_ground_truth_annotations(csv_path, EPOCH_DURATION_S)

    if variant_label == "kleifges":
        channel_results = kleifges_strategy(prepared, valid_epoch_indices)
    else:
        setting = {
            "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
            "std_threshold": std_threshold,
            "center_method": center_method,
            "min_flagged_epochs": MIN_FLAGGED_EPOCHS,
            "verbose": VERBOSE,
            "max_event_len": max_event_len,
            "k_confirm": k_confirm,
            "k_flagged": k_flagged,
            "k_nonflagged": k_nonflagged,
        }
        channel_results = channel_results_strategy_dbo_drop(prepared, valid_epoch_indices,
                                                     setting=setting)

    scored = evaluate_channels(
        channel_results,
        gt_annotations,
        epoch_duration=EPOCH_DURATION_S,
    )
    em = scored.best_eval_result.event_metrics
    return {
        "pair": pair_name,
        "variant": variant_label,
        "tp": em.tp,
        "fp": em.fp,
        "fn": em.fn,
        "precision": em.precision,
        "recall": em.recall,
        "f1": em.f1,
    }


# ---------------------------------------------------------------------------
# Printing helpers
# ---------------------------------------------------------------------------

def _print_per_pair_table(results: list[dict], variant_order: list[str]) -> None:
    results_sorted = sorted(results, key=lambda r: (r["pair"], variant_order.index(r["variant"])))

    col_w = {"pair": 30, "variant": 16, "tp": 5, "fp": 5, "fn": 5,
              "precision": 10, "recall": 8, "f1": 8}
    header = (
        f"{'pair':<{col_w['pair']}}  "
        f"{'variant':<{col_w['variant']}}  "
        f"{'tp':>{col_w['tp']}}  {'fp':>{col_w['fp']}}  {'fn':>{col_w['fn']}}  "
        f"{'precision':>{col_w['precision']}}  {'recall':>{col_w['recall']}}  "
        f"{'f1':>{col_w['f1']}}"
    )
    sep = "-" * len(header)
    print(f"\n{'=' * len(header)}")
    print("PER-PAIR RESULTS  (drowsy_driving_raja_processed)")
    print(f"{'=' * len(header)}")
    print(header)
    prev_pair = None
    for r in results_sorted:
        if prev_pair and r["pair"] != prev_pair:
            print(sep)
        prev_pair = r["pair"]
        print(
            f"{r['pair']:<{col_w['pair']}}  "
            f"{r['variant']:<{col_w['variant']}}  "
            f"{r['tp']:>{col_w['tp']}}  {r['fp']:>{col_w['fp']}}  {r['fn']:>{col_w['fn']}}  "
            f"{r['precision']:>{col_w['precision']}.4f}  "
            f"{r['recall']:>{col_w['recall']}.4f}  "
            f"{r['f1']:>{col_w['f1']}.4f}"
        )
    print(f"{'=' * len(header)}\n")


def _print_summary_table(results: list[dict], variant_order: list[str],
                         a_micro_r: float, a_micro_f1: float,
                         f_baseline_micro_r: float, f_baseline_micro_f1: float) -> None:
    from collections import defaultdict
    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        buckets[r["variant"]].append(r)

    col_w = {"variant": 16, "n": 6, "tp": 7, "fp": 7, "fn": 7,
             "micro_p": 9, "micro_r": 9, "micro_f1": 9,
             "delta_r": 8, "delta_f1": 9, "note": 28}

    header = (
        f"{'variant':<{col_w['variant']}}  "
        f"{'n':>{col_w['n']}}  "
        f"{'TP':>{col_w['tp']}}  {'FP':>{col_w['fp']}}  {'FN':>{col_w['fn']}}  "
        f"{'micro_P':>{col_w['micro_p']}}  "
        f"{'micro_R':>{col_w['micro_r']}}  "
        f"{'micro_F1':>{col_w['micro_f1']}}  "
        f"{'dR_vs_A':>{col_w['delta_r']}}  "
        f"{'dF1_vs_A':>{col_w['delta_f1']}}  "
        f"{'note':<{col_w['note']}}"
    )
    sep = "=" * len(header)
    print(sep)
    print("OVERALL SUMMARY  --  drowsy_driving_raja_processed")
    print(f"Baselines:  A  micro_R={a_micro_r:.4f}  micro_F1={a_micro_f1:.4f}")
    print(f"            F  micro_R={f_baseline_micro_r:.4f}  micro_F1={f_baseline_micro_f1:.4f}")
    print(sep)
    print(header)
    print("-" * len(header))

    for v in variant_order:
        rows = buckets.get(v, [])
        if not rows:
            continue
        total_tp = sum(r["tp"] for r in rows)
        total_fp = sum(r["fp"] for r in rows)
        total_fn = sum(r["fn"] for r in rows)
        micro_p  = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        micro_r  = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        micro_f1 = (2 * micro_p * micro_r / (micro_p + micro_r)
                    if (micro_p + micro_r) > 0 else 0.0)
        delta_r   = micro_r   - a_micro_r
        delta_f1  = micro_f1  - a_micro_f1

        # Note: does this variant beat A on recall? still above F-baseline F1?
        beats_r    = micro_r  > a_micro_r
        beats_f_f1 = micro_f1 > f_baseline_micro_f1
        note = ""
        if beats_r and beats_f_f1:
            note = "BEST: recall>A, F1>F_base"
        elif beats_r and micro_f1 > a_micro_f1:
            note = "recall>A, F1>A"
        elif beats_r:
            note = "recall>A"
        elif micro_r > f_baseline_micro_r:
            note = "recall>F_base"

        print(
            f"{v:<{col_w['variant']}}  "
            f"{len(rows):>{col_w['n']}}  "
            f"{total_tp:>{col_w['tp']}}  {total_fp:>{col_w['fp']}}  {total_fn:>{col_w['fn']}}  "
            f"{micro_p:>{col_w['micro_p']}.4f}  "
            f"{micro_r:>{col_w['micro_r']}.4f}  "
            f"{micro_f1:>{col_w['micro_f1']}.4f}  "
            f"{delta_r:>+{col_w['delta_r']}.4f}  "
            f"{delta_f1:>+{col_w['delta_f1']}.4f}  "
            f"{note}"
        )
    print(sep)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    setup_tutorial_logging()
    pairs = discover_raja_pairs(ANNOTATION_BASE_DIR, PROCESSED_BASE_DIR)
    if not pairs:
        logger.warning("No complete pairs found. Exiting.")
        return

    logger.info("Discovered %d pair(s) in drowsy_driving_raja_processed.", len(pairs))
    logger.info("Testing %d variants (kleifges + %d dbo_drop variants).", 1 + len(VARIANTS), len(VARIANTS))

    # Build task list: kleifges + all dbo_drop variants × all pairs
    # kleifges label is "kleifges"; std_threshold and center_method are ignored for kleifges.
    # Tasks: (name, fif, csv, label, std_threshold, center_method,
    #          max_event_len, k_confirm, k_flagged, k_nonflagged)
    tasks = []
    for pair in pairs:
        tasks.append((pair["name"], pair["fif"], pair["csv"],
                      "kleifges", 0.0, "median", None, None, None, None))
        for v in VARIANTS:
            tasks.append((pair["name"], pair["fif"], pair["csv"],
                          v["label"], v["std_threshold"], v["center_method"],
                          v.get("max_event_len", None), v.get("k_confirm", None),
                          v.get("k_flagged", None), v.get("k_nonflagged", None)))

    variant_order = ["kleifges"] + [v["label"] for v in VARIANTS]

    results: list[dict] = []
    errors: list[str] = []

    if USE_MULTITHREAD:
        logger.info("Running %d tasks with ThreadPoolExecutor …", len(tasks))
        with ThreadPoolExecutor() as executor:
            future_map = {
                executor.submit(run_one, nm, fif, csv, lbl, k, cm, mel, kc, kf, knf): (nm, lbl)
                for nm, fif, csv, lbl, k, cm, mel, kc, kf, knf in tasks
            }
            for future in as_completed(future_map):
                pair_name, label = future_map[future]
                try:
                    r = future.result()
                    results.append(r)
                    logger.info("done  pair=%s  variant=%s  R=%.4f  F1=%.4f",
                                pair_name, label, r["recall"], r["f1"])
                except Exception as exc:
                    logger.error("pair=%s  variant=%s: %s", pair_name, label, exc)
                    errors.append(f"ERROR pair={pair_name}  variant={label}: {exc}")
    else:
        logger.info("Running %d tasks sequentially …", len(tasks))
        for nm, fif, csv, lbl, k, cm, mel, kc, kf, knf in tasks:
            logger.info("running  pair=%s  variant=%s …", nm, lbl)
            try:
                r = run_one(nm, fif, csv, lbl, k, cm, mel, kc, kf, knf)
                results.append(r)
                logger.info("done     pair=%s  variant=%s  R=%.4f  F1=%.4f",
                             nm, lbl, r["recall"], r["f1"])
            except Exception as exc:
                logger.error("pair=%s  variant=%s: %s", nm, lbl, exc)
                errors.append(f"ERROR pair={nm}  variant={lbl}: {exc}")

    if results:
        _print_per_pair_table(results, variant_order)

        # Extract A and F-baseline metrics from results for the delta columns
        from collections import defaultdict
        buckets: dict[str, list[dict]] = defaultdict(list)
        for r in results:
            buckets[r["variant"]].append(r)

        def _micro(rows):
            tp = sum(r["tp"] for r in rows)
            fp = sum(r["fp"] for r in rows)
            fn = sum(r["fn"] for r in rows)
            p  = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rc = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2*p*rc/(p+rc) if (p+rc) > 0 else 0.0
            return rc, f1

        kleifges_r, kleifges_f1 = _micro(buckets.get("kleifges", []))
        # Use the first dbo_drop variant as the "baseline" for delta columns.
        base_label = VARIANTS[0]["label"] if VARIANTS else "kleifges"
        fb_r, fb_f1 = _micro(buckets.get(base_label, buckets.get("kleifges", [])))

        _print_summary_table(results, variant_order,
                             a_micro_r=kleifges_r, a_micro_f1=kleifges_f1,
                             f_baseline_micro_r=fb_r, f_baseline_micro_f1=fb_f1)

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(f"  {e}")


if __name__ == "__main__":
    main()
