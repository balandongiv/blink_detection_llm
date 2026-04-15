"""Strategy C full-run, Step 1, batch, and Strategy D variant runner.

Merges all tutorial/14_strategy_c_* and tutorial/14_strategy_d_* scripts into
a single entry-point.  Select a mode with the first positional argument:

  full-run    Complete Strategy C pipeline (full detector run, default: bayesian / per-channel)
  step1       Strategy C Step 1 lane scan only — no FitBlinks pass
  batch       Run multiple Step 1 variants sequentially, saving outputs to disk
  strategy-d  Strategy D: MNE peak_finder with Bayesian-optimisation thresholds

Examples
--------
  python tutorial/14_strategy_c_all_variants.py full-run
  python tutorial/14_strategy_c_all_variants.py full-run --method random_search
  python tutorial/14_strategy_c_all_variants.py full-run --scope global
  python tutorial/14_strategy_c_all_variants.py full-run --no-backbone
  python tutorial/14_strategy_c_all_variants.py step1
  python tutorial/14_strategy_c_all_variants.py step1 --with-backbone --show-candidates
  python tutorial/14_strategy_c_all_variants.py batch --skip-existing
  python tutorial/14_strategy_c_all_variants.py strategy-d
  python tutorial/14_strategy_c_all_variants.py strategy-d --disable-threshold-rescale
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime, timezone
import io
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter

import mne
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_VENDORED_AUTOREJECT = REPO_ROOT / "autoreject"
if str(_VENDORED_AUTOREJECT) not in sys.path:
    sys.path.insert(0, str(_VENDORED_AUTOREJECT))

from autoreject import compute_thresholds  # noqa: E402
from mne.preprocessing import peak_finder  # noqa: E402

from pyblinker.common.bad_epochs import get_valid_epoch_indices
from pyblinker.common.epoch_channel import map_concatenated_blinks_to_epochs
from pyblinker.common.epoch_input import prepare_epoch_detection_input
from pyblinker.common.validation import (
    filter_reference_to_valid_epochs,
    load_reference_blink_table,
    match_blink_tables,
)
from pyblinker.common.epoch_input import prepare_epoch_detection_input as prepare_b_detection_input
from pyblinker.strategy_b.nathanael_mne import find_eog_candidate_regions
from pyblinker.strategy_c import (
    AUTOREJECT_BAYESIAN_OPTIMIZATION,
    AUTOREJECT_RANDOM_SEARCH,
    DEFAULT_STAGE1_THRESHOLD_SCOPE,
    DEFAULT_STRATEGY_C_CHANNELS,
    REFERENCE_BENCHMARK,
    STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE,
    THRESHOLD_SCOPE_GLOBAL,
    THRESHOLD_SCOPE_PER_CHANNEL,
    compare_with_reference_benchmark,
    epoch_detection_strategy_c_autoreject,
)
from tutorial.strategy_c_autoreject_first_5_epochs_common import (
    REFERENCE_PATH,
    load_first_5_epochs as _load_first_5_epochs_common,
    run_single_method_debug,
)


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

SELF_SCRIPT = Path(__file__).resolve()
DATA_PATH = REPO_ROOT / "sample_data" / "dev_epo.fif"
DISABLE_BACKBONE_CHANNELS = ("__NO_BACKBONE__",)

FILTER_LOW = 1.0
FILTER_HIGH = 20.0
RESAMPLE_RATE = None
N_JOBS = 1
USE_MULTIPROCESSING = False
AUTOREJECT_RANDOM_STATE = 42
AUTOREJECT_AUGMENT = False
HALF_WINDOW_S = 0.10

# batch mode
OUTPUT_DIR = REPO_ROOT / "development_strategy" / "strategy_C" / "output"
STRATEGY_A_BASELINE = REPO_ROOT / "tutorial" / "11_strategy_a_stage1_benchmark.py"
TARGET_CHANNEL = "EEG X1 - Pz"
MNE_LOW_FREQ = 1.0
MNE_HIGH_FREQ = 20.0
MNE_THRESH = None
MNE_HALF_WINDOW_S = 0.10
FILTERED_SECTION_TITLES = {
    "=== Stage 1 Candidate Regions ===",
    "=== Stage 1 Candidate Regions Mapped To Epochs ===",
    "=== Reference Blinks ===",
}

# strategy-d
STRATEGY_D_CHANNELS = ["EEG X1 - Pz", "EEG Fp1 - Pz", "EEG Fp2 - Pz"]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def print_frame(title: str, frame: pd.DataFrame, columns: list[str] | None = None) -> None:
    print(f"\n=== {title} ===")
    if frame.empty:
        print("<empty>")
        return
    if columns is not None:
        existing = [c for c in columns if c in frame.columns]
        frame = frame.loc[:, existing]
    print(frame.to_string(index=False))


def configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(levelname)s: %(name)s: %(message)s",
        force=True,
    )


def load_first_5_epochs(channels: list[str] | None = None) -> mne.Epochs:
    epochs = mne.read_epochs(str(DATA_PATH), preload=True, verbose="ERROR")
    if channels is not None:
        epochs = epochs.copy().pick(channels)
    return epochs[:5].copy()


# ---------------------------------------------------------------------------
# Mode: full-run
# ---------------------------------------------------------------------------

def _run_full_no_backbone(method: str, scope: str) -> None:
    """Full Strategy C pipeline with backbone disabled (no __NO_BACKBONE__ sentinel)."""
    print(f"script={SELF_SCRIPT.name}")
    print(f"variant=All EEG channels + no weighted frontal backbone / {method}")
    print(f"reference_path={REFERENCE_PATH}")
    print(f"stage1_channels={DISABLE_BACKBONE_CHANNELS}")
    print(f"autoreject_method={method}")
    print(f"stage1_threshold_scope={scope}")

    epochs = _load_first_5_epochs_common()
    reference = load_reference_blink_table(REFERENCE_PATH)

    started = perf_counter()
    detector = epoch_detection_strategy_c_autoreject(
        epochs,
        visualize=False,
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
        n_jobs=N_JOBS,
        use_multiprocessing=USE_MULTIPROCESSING,
        stage1_channels=DISABLE_BACKBONE_CHANNELS,
        stage1_threshold_scope=scope,
        autoreject_random_state=AUTOREJECT_RANDOM_STATE,
        autoreject_method=method,
        autoreject_augment=AUTOREJECT_AUGMENT,
    )
    annotations, channel, n_good_blinks, blink_table, _fig_data, selected_channel, _epochs = (
        detector.get_blink()
    )
    elapsed_s = perf_counter() - started
    metrics = match_blink_tables(blink_table, reference, n_epochs=len(epochs))

    print("\n=== Run Result ===")
    print(f"elapsed_s={elapsed_s:.6f}")
    print(f"selected_channel={channel}")
    print(f"n_good_blinks={n_good_blinks}")
    print(f"annotation_count={len(annotations)}")
    print(f"stage1_threshold_scope={detector.stage1_threshold_scope_}")
    print(f"stage1_threshold_learning_api={detector.stage1_threshold_learning_api_}")
    print(f"stage1_autoreject_method={detector.stage1_autoreject_method_}")
    print(f"stage1_channels={detector.stage1_channel_names_}")
    print(f"stage1_backbone_built={detector.stage1_backbone_signal_ is not None}")
    print(f"stage1_backbone_channels={detector.stage1_backbone_channels_}")
    print(f"stage1_thresholds={detector.stage1_thresholds_}")
    print(f"stage1_scan_threshold_scale={detector._get_stage1_scan_threshold_scale()}")
    print(f"stage1_candidate_count={len(detector.stage1_candidates_)}")
    print(f"stage1_rescue_candidate_count={len(detector.stage1_rescue_candidates_)}")

    print_frame("Representative Stage 1 Lanes", detector.stage1_representative_channels_)
    print_frame("Selected Channel Summary", selected_channel)
    print_frame(
        "Predicted Blinks",
        blink_table,
        ["epoch_index", "channel", "blink_onset", "blink_duration", "epoch_selection"],
    )
    print("\n=== Metrics Against Reference ===")
    print(
        {
            "true_positives": metrics.true_positives,
            "false_positives": metrics.false_positives,
            "false_negatives": metrics.false_negatives,
            "precision": metrics.precision,
            "recall": metrics.recall,
            "f1": metrics.f1,
            "epoch_blink_agreement": metrics.epoch_blink_agreement,
            "blink_count_agreement": metrics.blink_count_agreement,
        }
    )


def run_full(args: argparse.Namespace) -> None:
    """Dispatch to full-run variant based on CLI args."""
    if args.no_backbone:
        _run_full_no_backbone(method=args.method, scope=args.scope)
    else:
        run_single_method_debug(
            method=args.method,
            script_name=SELF_SCRIPT.name,
            stage1_threshold_scope=args.scope,
        )


# ---------------------------------------------------------------------------
# Mode: step1
# ---------------------------------------------------------------------------

def _build_step1_summary(
    detections: list[object],
    *,
    reference: pd.DataFrame,
    n_epochs: int,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for detection in detections:
        metrics = match_blink_tables(
            detection.mapped_candidates,
            reference,
            n_epochs=n_epochs,
        )
        rows.append(
            {
                "channel": detection.channel,
                "candidate_source": detection.candidate_source,
                "threshold": float(detection.threshold),
                "raw_candidate_count": int(len(detection.positions)),
                "mapped_candidate_count": int(len(detection.mapped_candidates)),
                "tp": int(metrics.true_positives),
                "fp": int(metrics.false_positives),
                "fn": int(metrics.false_negatives),
                "precision": float(metrics.precision),
                "recall": float(metrics.recall),
                "f1": float(metrics.f1),
            }
        )
    if not rows:
        return pd.DataFrame()
    return (
        pd.DataFrame(rows)
        .sort_values(["f1", "tp", "fp", "channel"], ascending=[False, False, True, True])
        .reset_index(drop=True)
    )


def _get_detection_by_channel(detections: list[object], channel: str):
    for detection in detections:
        if detection.channel == channel:
            return detection
    return None


def run_step1(args: argparse.Namespace) -> None:
    """Strategy C Step 1 lane scan — no FitBlinks pass."""
    configure_logging(args.log_level)
    stage1_channels = (
        DEFAULT_STRATEGY_C_CHANNELS if args.with_backbone else DISABLE_BACKBONE_CHANNELS
    )

    print(f"script={SELF_SCRIPT.name}")
    print("mode=step1")
    print("dataset=sample_data/dev_epo.fif")
    print("epochs=first 5 only")
    print(f"reference_path={REFERENCE_PATH}")
    print(f"autoreject_method={args.method}")
    print(f"stage1_threshold_scope={args.scope}")
    print(f"stage1_rescale_threshold={not args.disable_threshold_rescale}")
    print(f"stage1_channels={stage1_channels}")
    print(f"weighted_frontal_backbone_enabled={args.with_backbone}")
    print(f"log_level={args.log_level}")

    started = perf_counter()
    epochs: mne.Epochs = _load_first_5_epochs_common()
    reference = load_reference_blink_table(REFERENCE_PATH)

    detector = epoch_detection_strategy_c_autoreject(
        epochs,
        visualize=False,
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
        n_jobs=N_JOBS,
        use_multiprocessing=USE_MULTIPROCESSING,
        stage1_channels=stage1_channels,
        stage1_threshold_scope=args.scope,
        stage1_rescale_threshold=not args.disable_threshold_rescale,
        autoreject_random_state=AUTOREJECT_RANDOM_STATE,
        autoreject_method=args.method,
        autoreject_augment=AUTOREJECT_AUGMENT,
    )

    prepared = detector.prepare_epoch_data()
    valid_epoch_indices = get_valid_epoch_indices(epochs)
    stage1 = detector.run_stage1_candidate_scan(
        prepared=prepared,
        valid_epoch_indices=valid_epoch_indices,
    )
    elapsed_s = perf_counter() - started
    summary = _build_step1_summary(
        stage1.detections,
        reference=reference,
        n_epochs=len(epochs),
    )

    print("\n=== Run Result ===")
    print(f"elapsed_s={elapsed_s:.6f}")
    print(f"valid_epoch_indices={valid_epoch_indices}")
    print(f"stage1_threshold_scope={detector.stage1_threshold_scope}")
    print(f"stage1_threshold_learning_api={stage1.threshold_learning_api}")
    print(f"stage1_autoreject_method={detector.autoreject_method}")
    print(f"stage1_rescale_threshold={detector.stage1_rescale_threshold}")
    print(f"stage1_eeg_channels={stage1.channel_names}")
    print(f"stage1_backbone_built={stage1.backbone_signal is not None}")
    print(f"stage1_backbone_channels={detector.stage1_backbone_channels_}")
    print(f"stage1_global_threshold={stage1.global_threshold}")
    print(f"stage1_scan_threshold_scale={detector._get_stage1_scan_threshold_scale()}")
    print(f"candidate_lane_count={len(stage1.candidate_lanes)}")

    print_frame("Stage 1 Lane Summary", summary)

    if args.show_candidates:
        if summary.empty:
            print_frame("Best Lane Mapped Candidates", pd.DataFrame())
        else:
            best_channel = str(summary.loc[0, "channel"])
            best_detection = _get_detection_by_channel(stage1.detections, best_channel)
            best_candidates = (
                best_detection.mapped_candidates
                if best_detection is not None
                else pd.DataFrame()
            )
            print_frame(
                "Best Lane Mapped Candidates",
                best_candidates,
                ["epoch_index", "channel", "blink_onset", "blink_duration", "candidate_source"],
            )


# ---------------------------------------------------------------------------
# Mode: batch
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RunSpec:
    name: str
    output_name: str
    kind: str
    script_path: Path | None = None
    args: tuple[str, ...] = ()


RUN_SPECS: tuple[RunSpec, ...] = (
    # RunSpec(
    #     name="strategy_a_step1_baseline",
    #     output_name="strategy_a_step1_baseline.txt",
    #     kind="subprocess",
    #     script_path=STRATEGY_A_BASELINE,
    # ),
    # RunSpec(
    #     name="strategy_b_step1_baseline",
    #     output_name="strategy_b_step1_baseline.txt",
    #     kind="callable",
    # ),
    # RunSpec(
    #     name="strategy_c_random_search_per_channel_no_backbone",
    #     output_name="strategy_c_random_search_per_channel_no_backbone.txt",
    #     kind="subprocess",
    #     script_path=SELF_SCRIPT,
    #     args=("step1", "--method", AUTOREJECT_RANDOM_SEARCH, "--scope", THRESHOLD_SCOPE_PER_CHANNEL, "--no-backbone"),
    # ),
    RunSpec(
        name="strategy_c_bayesian_optimization_per_channel_no_backbone",
        output_name="strategy_c_bayesian_optimization_per_channel_no_backbone.txt",
        kind="subprocess",
        script_path=SELF_SCRIPT,
        args=(
            "step1",
            "--method",
            AUTOREJECT_BAYESIAN_OPTIMIZATION,
            "--scope",
            THRESHOLD_SCOPE_PER_CHANNEL,
            "--no-backbone",
        ),
    ),
    # RunSpec(
    #     name="strategy_c_global_threshold_no_backbone",
    #     output_name="strategy_c_global_threshold_no_backbone.txt",
    #     kind="subprocess",
    #     script_path=SELF_SCRIPT,
    #     args=("step1", "--method", AUTOREJECT_RANDOM_SEARCH, "--scope", THRESHOLD_SCOPE_GLOBAL, "--no-backbone"),
    # ),
    # RunSpec(
    #     name="strategy_c_random_search_per_channel_with_backbone",
    #     output_name="strategy_c_random_search_per_channel_with_backbone.txt",
    #     kind="subprocess",
    #     script_path=SELF_SCRIPT,
    #     args=("step1", "--method", AUTOREJECT_RANDOM_SEARCH, "--scope", THRESHOLD_SCOPE_PER_CHANNEL, "--with-backbone"),
    # ),
    # RunSpec(
    #     name="strategy_c_bayesian_optimization_per_channel_with_backbone",
    #     output_name="strategy_c_bayesian_optimization_per_channel_with_backbone.txt",
    #     kind="subprocess",
    #     script_path=SELF_SCRIPT,
    #     args=("step1", "--method", AUTOREJECT_BAYESIAN_OPTIMIZATION, "--scope", THRESHOLD_SCOPE_PER_CHANNEL, "--with-backbone"),
    # ),
    # RunSpec(
    #     name="strategy_c_global_threshold_with_backbone",
    #     output_name="strategy_c_global_threshold_with_backbone.txt",
    #     kind="subprocess",
    #     script_path=SELF_SCRIPT,
    #     args=("step1", "--method", AUTOREJECT_RANDOM_SEARCH, "--scope", THRESHOLD_SCOPE_GLOBAL, "--with-backbone"),
    # ),
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_manifest(manifest_path: Path, entry: dict[str, object]) -> None:
    with manifest_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def _build_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    repo_root = str(REPO_ROOT)
    env["PYTHONPATH"] = repo_root if not existing else f"{repo_root}{os.pathsep}{existing}"
    return env


def _strip_verbose_tables(text: str) -> str:
    """Remove bulky per-blink tables from saved benchmark reports."""
    kept_lines: list[str] = []
    skipping = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("==="):
            skipping = stripped in FILTERED_SECTION_TITLES
            if skipping:
                continue
        if skipping:
            continue
        kept_lines.append(line)
    normalized = "\n".join(kept_lines).strip()
    return normalized + "\n" if normalized else ""


def _run_strategy_b_step1_baseline() -> None:
    """Inline Strategy B step 1 baseline for the batch 'callable' RunSpec kind."""
    epochs = _load_first_5_epochs_common().copy().pick([TARGET_CHANNEL])
    prepared = prepare_b_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=MNE_LOW_FREQ,
        filter_high=MNE_HIGH_FREQ,
        resample_rate=None,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)
    epoch_boundaries = [
        (
            idx * prepared.epoch_length_samples,
            (idx + 1) * prepared.epoch_length_samples,
        )
        for idx in range(len(valid_epoch_indices))
    ]
    channel_index = prepared.channel_names.index(TARGET_CHANNEL)
    concatenated_signal = prepared.data[valid_epoch_indices, channel_index, :].reshape(-1)

    df_positions = find_eog_candidate_regions(
        concatenated_signal,
        channel=TARGET_CHANNEL,
        sfreq=float(prepared.sfreq),
        half_window_s=MNE_HALF_WINDOW_S,
        l_freq=MNE_LOW_FREQ,
        h_freq=MNE_HIGH_FREQ,
        thresh=MNE_THRESH,
    )
    mapped_positions = map_concatenated_blinks_to_epochs(
        df_positions,
        channel=TARGET_CHANNEL,
        valid_epoch_indices=valid_epoch_indices,
        epoch_boundaries=epoch_boundaries,
        sfreq=prepared.sfreq,
    )

    reference = load_reference_blink_table(REFERENCE_PATH)
    reference = filter_reference_to_valid_epochs(reference, valid_epoch_indices)
    metrics = match_blink_tables(mapped_positions, reference, n_epochs=len(epochs))

    print("script=strategy_b_step1_baseline_inline")
    print("detector=find_eog_candidate_regions(...)")
    print("stage_boundary=step1_only")
    print(f"dataset={DATA_PATH}")
    print("epochs=first 5 only")
    print(f"reference_path={REFERENCE_PATH}")
    print(f"target_channel={TARGET_CHANNEL}")
    print(f"mne_low_freq={MNE_LOW_FREQ}")
    print(f"mne_high_freq={MNE_HIGH_FREQ}")
    print(f"mne_thresh={MNE_THRESH}")
    print(f"mne_half_window_s={MNE_HALF_WINDOW_S}")
    print(f"valid_epoch_indices={valid_epoch_indices}")
    print(f"prepared_shape={prepared.data.shape}")
    print(f"concatenated_signal_length={len(concatenated_signal)}")
    print(f"stage1_candidate_regions={len(df_positions)}")
    print(f"mapped_candidate_regions={len(mapped_positions)}")
    print(f"reference_blinks={len(reference)}")
    print_frame(
        "Stage 1 Candidate Regions",
        df_positions,
        ["start_blink", "end_blink", "peak_sample"],
    )
    print_frame(
        "Stage 1 Candidate Regions Mapped To Epochs",
        mapped_positions,
        ["epoch_index", "channel", "blink_onset", "blink_duration", "start_blink", "end_blink"],
    )
    print_frame(
        "Reference Blinks",
        reference,
        ["epoch_index", "blink_onset", "blink_duration"],
    )
    print("\n=== Stage 1 Metrics ===")
    print(
        {
            "true_positives": int(metrics.true_positives),
            "false_positives": int(metrics.false_positives),
            "false_negatives": int(metrics.false_negatives),
            "precision": float(metrics.precision),
            "recall": float(metrics.recall),
            "f1": float(metrics.f1),
            "epoch_blink_agreement": float(metrics.epoch_blink_agreement),
            "blink_count_agreement": float(metrics.blink_count_agreement),
        }
    )


def _build_batch_command(spec: RunSpec, disable_threshold_rescale: bool) -> list[str]:
    assert spec.script_path is not None
    command = [sys.executable, str(spec.script_path), *spec.args]
    if (
        disable_threshold_rescale
        and spec.script_path == SELF_SCRIPT
        and "--disable-threshold-rescale" not in command
    ):
        command.append("--disable-threshold-rescale")
    return command


def _write_subprocess_output(
    spec: RunSpec, output_path: Path, disable_threshold_rescale: bool
) -> int:
    command = _build_batch_command(spec, disable_threshold_rescale)
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=_build_subprocess_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    with output_path.open("w", encoding="utf-8") as handle:
        print(f"batch_runner={SELF_SCRIPT.name}", file=handle)
        print(f"run_name={spec.name}", file=handle)
        print(f"python_executable={sys.executable}", file=handle)
        print(f"started_at_utc={_utc_now_iso()}", file=handle)
        print(f"command={command}", file=handle)
        print("", file=handle)
        handle.write(_strip_verbose_tables(result.stdout))
    return int(result.returncode)


def _write_callable_output(spec: RunSpec, output_path: Path) -> int:
    buffer = io.StringIO()
    with redirect_stdout(buffer), redirect_stderr(buffer):
        _run_strategy_b_step1_baseline()
    with output_path.open("w", encoding="utf-8") as handle:
        print(f"batch_runner={SELF_SCRIPT.name}", file=handle)
        print(f"run_name={spec.name}", file=handle)
        print(f"python_executable={sys.executable}", file=handle)
        print(f"started_at_utc={_utc_now_iso()}", file=handle)
        print("", file=handle)
        handle.write(_strip_verbose_tables(buffer.getvalue()))
    return 0


def _execute_batch_run(
    spec: RunSpec, output_path: Path, disable_threshold_rescale: bool
) -> int:
    if spec.kind == "subprocess":
        return _write_subprocess_output(spec, output_path, disable_threshold_rescale)
    if spec.kind == "callable":
        return _write_callable_output(spec, output_path)
    raise ValueError(f"Unsupported run kind: {spec.kind}")


def run_batch(args: argparse.Namespace) -> int:
    """Batch runner: run multiple Step 1 variants sequentially, save outputs to disk."""
    output_dir = Path(args.output_dir).resolve()
    manifest_path = output_dir / "step1_batch_manifest.jsonl"
    output_dir.mkdir(parents=True, exist_ok=True)

    failed = False

    print(f"output_dir={output_dir}")
    print(f"manifest_path={manifest_path}")
    print(f"python_executable={sys.executable}")
    print(f"repo_root={REPO_ROOT}")
    print(f"disable_threshold_rescale={args.disable_threshold_rescale}")

    for index, spec in enumerate(RUN_SPECS, start=1):
        output_path = output_dir / spec.output_name
        if args.skip_existing and output_path.exists() and output_path.stat().st_size > 0:
            print(f"[{index}/{len(RUN_SPECS)}] skip {spec.name} -> {output_path.name}")
            _append_manifest(
                manifest_path,
                {
                    "elapsed_s": 0.0,
                    "finished_at_utc": _utc_now_iso(),
                    "output_path": str(output_path),
                    "returncode": None,
                    "run_name": spec.name,
                    "started_at_utc": _utc_now_iso(),
                    "status": "skipped_existing",
                },
            )
            continue

        print(f"[{index}/{len(RUN_SPECS)}] start {spec.name} -> {output_path.name}")
        started = perf_counter()
        started_at = _utc_now_iso()
        returncode = _execute_batch_run(spec, output_path, args.disable_threshold_rescale)
        elapsed_s = perf_counter() - started
        status = "ok" if returncode == 0 else "failed"
        print(
            f"[{index}/{len(RUN_SPECS)}] done {spec.name} "
            f"status={status} returncode={returncode} elapsed_s={elapsed_s:.3f}"
        )
        _append_manifest(
            manifest_path,
            {
                "elapsed_s": round(elapsed_s, 6),
                "finished_at_utc": _utc_now_iso(),
                "output_path": str(output_path),
                "returncode": returncode,
                "run_name": spec.name,
                "started_at_utc": started_at,
                "status": status,
            },
        )
        if returncode != 0:
            failed = True
            if args.stop_on_failure:
                print("Stopping because --stop-on-failure was requested.")
                break

    return 1 if failed else 0


# ---------------------------------------------------------------------------
# Mode: strategy-d
# ---------------------------------------------------------------------------

def _get_scan_threshold_scale(rescale_threshold: bool) -> float:
    """Translate the rescale flag into a numeric scale factor.

    Mirrors EpochDetectionStrategyCAutoreject._get_stage1_scan_threshold_scale():
    - rescale enabled  -> STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE (0.12)
    - rescale disabled -> 1.0 (use raw autoreject threshold directly)
    """
    return STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE if rescale_threshold else 1.0


def _learn_bayesian_thresholds(
    prepared_data: np.ndarray,
    channel_names: tuple[str, ...],
    sfreq: float,
    valid_epoch_indices: list[int],
) -> dict[str, float]:
    """Learn per-channel PTP rejection thresholds with Bayesian optimisation.

    Replicates the per_channel branch of Strategy C's get_channel_rejection_threshold.
    """
    valid_indices = np.asarray(valid_epoch_indices, dtype=int)
    stage1_data = prepared_data[valid_indices]
    info = mne.create_info(
        list(channel_names),
        sfreq=float(sfreq),
        ch_types=["eeg"] * len(channel_names),
    )
    stage1_epochs = mne.EpochsArray(stage1_data, info, verbose="ERROR")
    threshes = compute_thresholds(
        stage1_epochs,
        method="bayesian_optimization",
        random_state=AUTOREJECT_RANDOM_STATE,
        augment=False,
        verbose=False,
    )
    return {ch: float(threshes[ch]) for ch in channel_names}


def _peaks_to_candidates(
    peak_locs: np.ndarray,
    *,
    epoch_length_samples: int,
    sfreq: float,
    valid_epoch_indices: list[int],
    channel: str,
    half_window_s: float = 0.10,
) -> pd.DataFrame:
    """Map concatenated-signal sample positions back to epoch-local candidate rows.

    Mirrors the offset arithmetic inside MNE's _find_eog_events:
        epoch_index = peak_sample // epoch_length_samples
        local_onset = (peak_sample % epoch_length_samples) / sfreq
    """
    columns = ["epoch_index", "channel", "blink_onset", "blink_duration", "peak_sample"]
    if len(peak_locs) == 0:
        return pd.DataFrame(columns=columns)

    half_win = max(1, int(round(half_window_s * sfreq)))
    rows: list[dict] = []
    for peak in peak_locs:
        offset = int(peak) // epoch_length_samples
        if offset < 0 or offset >= len(valid_epoch_indices):
            continue
        epoch_index = int(valid_epoch_indices[offset])
        local_peak = int(peak) % epoch_length_samples
        start = max(0, local_peak - half_win)
        end = min(epoch_length_samples - 1, local_peak + half_win)
        rows.append(
            {
                "epoch_index": epoch_index,
                "channel": channel,
                "blink_onset": start / float(sfreq),
                "blink_duration": (end - start) / float(sfreq),
                "peak_sample": local_peak,
            }
        )
    if not rows:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(rows)
    return df.sort_values(["epoch_index", "blink_onset"]).reset_index(drop=True)


def _build_strategy_d_summary(
    channel_results: list[dict],
    *,
    reference: pd.DataFrame,
    n_epochs: int,
) -> pd.DataFrame:
    rows: list[dict] = []
    for result in channel_results:
        metrics = match_blink_tables(result["candidates"], reference, n_epochs=n_epochs)
        rows.append(
            {
                "channel": result["channel"],
                "raw_threshold": result["raw_threshold"],
                "scan_threshold": result["scan_threshold"],
                "extrema": result["extrema"],
                "peak_count": result["peak_count"],
                "candidate_count": int(len(result["candidates"])),
                "tp": int(metrics.true_positives),
                "fp": int(metrics.false_positives),
                "fn": int(metrics.false_negatives),
                "precision": float(metrics.precision),
                "recall": float(metrics.recall),
                "f1": float(metrics.f1),
            }
        )
    if not rows:
        return pd.DataFrame()
    return (
        pd.DataFrame(rows)
        .sort_values(["f1", "tp", "fp", "channel"], ascending=[False, False, True, True])
        .reset_index(drop=True)
    )


def run_strategy_d(args: argparse.Namespace) -> None:
    """Strategy D Step 1: MNE peak_finder with Bayesian-optimisation thresholds.

    Derivation from Strategy B — calls peak_finder directly instead of going
    through mne.preprocessing.find_eog_events, using per-channel autoreject
    thresholds for the scan threshold.
    """
    configure_logging(args.log_level)
    mne.set_log_level("ERROR")

    rescale_threshold = not args.disable_threshold_rescale
    scan_threshold_scale = _get_scan_threshold_scale(rescale_threshold)

    print(f"script={SELF_SCRIPT.name}")
    print("mode=strategy-d")
    print(f"dataset={DATA_PATH}")
    print("epochs=first 5 only")
    print(f"reference_path={REFERENCE_PATH}")
    print(f"channels={STRATEGY_D_CHANNELS}")
    print(f"filter_low={FILTER_LOW}")
    print(f"filter_high={FILTER_HIGH}")
    print(f"half_window_s={HALF_WINDOW_S}")
    print("autoreject_method=bayesian_optimization")
    print(f"autoreject_random_state={AUTOREJECT_RANDOM_STATE}")
    print(f"rescale_threshold={rescale_threshold}")
    print(f"scan_threshold_scale={scan_threshold_scale}")
    print(f"log_level={args.log_level}")

    started = perf_counter()

    epochs = load_first_5_epochs(channels=STRATEGY_D_CHANNELS)
    reference = load_reference_blink_table(REFERENCE_PATH)

    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )
    valid_epoch_indices = get_valid_epoch_indices(epochs)

    print(f"\nprepared_shape={prepared.data.shape}")
    print(f"prepared_channel_names={prepared.channel_names}")
    print(f"prepared_sfreq={prepared.sfreq}")
    print(f"epoch_length_samples={prepared.epoch_length_samples}")
    print(f"valid_epoch_indices={valid_epoch_indices}")

    print(f"\nLearning thresholds with autoreject(method='bayesian_optimization')...")
    raw_thresholds = _learn_bayesian_thresholds(
        prepared.data,
        channel_names=prepared.channel_names,
        sfreq=prepared.sfreq,
        valid_epoch_indices=valid_epoch_indices,
    )
    scan_thresholds = {ch: raw_thresholds[ch] * scan_threshold_scale for ch in raw_thresholds}
    print(f"raw_thresholds={raw_thresholds}")
    print(f"scan_thresholds={scan_thresholds}")

    epoch_length_samples = int(prepared.epoch_length_samples)
    valid_indices_arr = np.asarray(valid_epoch_indices, dtype=int)
    channel_results: list[dict] = []

    for ch_idx, channel in enumerate(prepared.channel_names):
        x0 = prepared.data[valid_indices_arr, ch_idx, :].reshape(-1).astype(float)
        raw_thresh = raw_thresholds[channel]
        scan_thresh = scan_thresholds[channel]

        temp = x0 - np.mean(x0)
        extrema = 1 if np.abs(np.max(temp)) >= np.abs(np.min(temp)) else -1

        peak_locs, _ = peak_finder(x0, thresh=scan_thresh, extrema=extrema, verbose=False)
        peak_locs = np.asarray(peak_locs, dtype=int)

        candidates = _peaks_to_candidates(
            peak_locs,
            epoch_length_samples=epoch_length_samples,
            sfreq=prepared.sfreq,
            valid_epoch_indices=valid_epoch_indices,
            channel=channel,
            half_window_s=HALF_WINDOW_S,
        )
        channel_results.append(
            {
                "channel": channel,
                "raw_threshold": raw_thresh,
                "scan_threshold": scan_thresh,
                "extrema": extrema,
                "peak_count": int(len(peak_locs)),
                "candidates": candidates,
            }
        )

    elapsed_s = perf_counter() - started
    summary = _build_strategy_d_summary(
        channel_results, reference=reference, n_epochs=len(epochs)
    )

    print(f"\nelapsed_s={elapsed_s:.6f}")
    print_frame(
        "Strategy D Step 1 – Channel Summary",
        summary,
        [
            "channel",
            "raw_threshold",
            "scan_threshold",
            "extrema",
            "peak_count",
            "candidate_count",
            "tp",
            "fp",
            "fn",
            "precision",
            "recall",
            "f1",
        ],
    )

    if args.show_candidates and not summary.empty:
        best_channel = str(summary.loc[0, "channel"])
        best_result = next((r for r in channel_results if r["channel"] == best_channel), None)
        if best_result is not None:
            print_frame(
                f"Best Channel Candidates ({best_channel})",
                best_result["candidates"],
                ["epoch_index", "channel", "blink_onset", "blink_duration", "peak_sample"],
            )


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Strategy C full-run, Step 1, batch, and Strategy D variant runner. "
            "Select a mode with the first positional argument."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s full-run\n"
            "  %(prog)s full-run --method random_search\n"
            "  %(prog)s full-run --scope global\n"
            "  %(prog)s full-run --no-backbone\n"
            "  %(prog)s step1\n"
            "  %(prog)s step1 --with-backbone --show-candidates\n"
            "  %(prog)s batch --skip-existing\n"
            "  %(prog)s strategy-d\n"
        ),
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    # -- full-run --------------------------------------------------------------
    p_full = subparsers.add_parser(
        "full-run",
        help="Complete Strategy C pipeline (default: bayesian / per-channel / with backbone).",
    )
    p_full.add_argument(
        "--method",
        default=AUTOREJECT_BAYESIAN_OPTIMIZATION,
        choices=[AUTOREJECT_RANDOM_SEARCH, AUTOREJECT_BAYESIAN_OPTIMIZATION],
        help="Autoreject threshold search method.",
    )
    p_full.add_argument(
        "--scope",
        default=DEFAULT_STAGE1_THRESHOLD_SCOPE,
        choices=[THRESHOLD_SCOPE_PER_CHANNEL, THRESHOLD_SCOPE_GLOBAL],
        help="Stage 1 threshold scope.",
    )
    backbone_group = p_full.add_mutually_exclusive_group()
    backbone_group.add_argument(
        "--no-backbone",
        dest="no_backbone",
        action="store_true",
        help="Disable the weighted frontal backbone (all EEG channels only).",
    )
    backbone_group.add_argument(
        "--with-backbone",
        dest="no_backbone",
        action="store_false",
        help="Enable the weighted frontal backbone (default).",
    )
    p_full.set_defaults(no_backbone=False)

    # -- step1 -----------------------------------------------------------------
    p_step1 = subparsers.add_parser(
        "step1",
        help="Strategy C Step 1 lane scan only — no FitBlinks pass.",
    )
    p_step1.add_argument(
        "--method",
        default=AUTOREJECT_BAYESIAN_OPTIMIZATION,
        choices=[AUTOREJECT_BAYESIAN_OPTIMIZATION],
        help="Autoreject threshold search method.",
    )
    p_step1.add_argument(
        "--scope",
        default=THRESHOLD_SCOPE_PER_CHANNEL,
        choices=[THRESHOLD_SCOPE_PER_CHANNEL, THRESHOLD_SCOPE_GLOBAL],
        help="Stage 1 threshold scope.",
    )
    backbone_group_s1 = p_step1.add_mutually_exclusive_group()
    backbone_group_s1.add_argument(
        "--with-backbone",
        dest="with_backbone",
        action="store_true",
        help="Enable the weighted frontal backbone.",
    )
    backbone_group_s1.add_argument(
        "--no-backbone",
        dest="with_backbone",
        action="store_false",
        help="Disable the weighted frontal backbone (default).",
    )
    p_step1.set_defaults(with_backbone=False)
    p_step1.add_argument(
        "--show-candidates",
        action="store_true",
        help="Print the full mapped Stage 1 candidate table for the best lane.",
    )
    p_step1.add_argument(
        "--disable-threshold-rescale",
        action="store_true",
        help=(
            "Use the raw autoreject threshold for Stage 1 lane scanning "
            "instead of multiplying by the fixed scan-threshold scale."
        ),
    )
    p_step1.add_argument(
        "--log-level",
        default="DEBUG",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Python logging level.",
    )

    # -- batch -----------------------------------------------------------------
    p_batch = subparsers.add_parser(
        "batch",
        help="Run multiple Step 1 variants sequentially, saving outputs to disk.",
    )
    p_batch.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help="Directory where per-run output files and the manifest are written.",
    )
    p_batch.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip runs whose output file already exists and is non-empty.",
    )
    p_batch.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="Stop immediately if any run fails.",
    )
    p_batch.add_argument(
        "--disable-threshold-rescale",
        action="store_true",
        help=(
            "Pass through to Step 1 subprocess runs so Stage 1 scanning uses the raw "
            "autoreject threshold instead of the fixed scan-threshold scale."
        ),
    )

    # -- strategy-d ------------------------------------------------------------
    p_sd = subparsers.add_parser(
        "strategy-d",
        help="Strategy D: MNE peak_finder with per-channel Bayesian-optimisation thresholds.",
    )
    p_sd.add_argument(
        "--disable-threshold-rescale",
        action="store_true",
        help=(
            f"Use the raw autoreject PTP threshold directly (scale = 1.0). "
            f"By default the threshold is multiplied by "
            f"STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE ({STAGE1_BAYESIAN_SCAN_THRESHOLD_SCALE})."
        ),
    )
    p_sd.add_argument(
        "--show-candidates",
        action="store_true",
        help="Print the full candidate table for the best channel.",
    )
    p_sd.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Python logging level.",
    )

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int | None:
    args = build_parser().parse_args()
    if args.mode == "full-run":
        run_full(args)
    elif args.mode == "step1":
        run_step1(args)
    elif args.mode == "batch":
        return run_batch(args)
    elif args.mode == "strategy-d":
        run_strategy_d(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
