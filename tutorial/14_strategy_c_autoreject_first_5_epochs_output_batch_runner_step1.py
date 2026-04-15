"""Run Step 1 baselines and Strategy C variants, saving each output to disk.

This script is intended for long manual benchmark sessions where each run should
leave a visible artifact on disk before the next run starts.

Outputs are written under:

    development_strategy/strategy_C/output

Each completed run also appends one JSON line to:

    development_strategy/strategy_C/output/step1_batch_manifest.jsonl
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pyblinker.epoch_detection_strategy_a.bad_epoch_utils import get_valid_epoch_indices
from pyblinker.epoch_detection_strategy_a.epoch_channel_processor import (
    map_concatenated_blinks_to_epochs,
)
from pyblinker.epoch_detection_strategy_a.epoch_validation import (
    filter_reference_to_valid_epochs,
    load_reference_blink_table,
    match_blink_tables,
)
from pyblinker.epoch_detection_strategy_b import (
    find_eog_candidate_regions,
    prepare_epoch_detection_input,
)
from pyblinker.epoch_detection_strategy_c import (
    AUTOREJECT_BAYESIAN_OPTIMIZATION,
    AUTOREJECT_RANDOM_SEARCH,
    THRESHOLD_SCOPE_GLOBAL,
    THRESHOLD_SCOPE_PER_CHANNEL,
)
from tutorial.strategy_c_autoreject_first_5_epochs_common import (
    REFERENCE_PATH,
    load_first_5_epochs,
)


OUTPUT_DIR = REPO_ROOT / "development_strategy" / "strategy_C" / "output"
MANIFEST_PATH = OUTPUT_DIR / "step1_batch_manifest.jsonl"
VARIANT_RUNNER = (
    REPO_ROOT / "tutorial" / "14_strategy_c_autoreject_first_5_epochs_variant_runner_step1.py"
)
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
    #     script_path=VARIANT_RUNNER,
    #     args=(
    #         "--method",
    #         AUTOREJECT_RANDOM_SEARCH,
    #         "--scope",
    #         THRESHOLD_SCOPE_PER_CHANNEL,
    #         "--no-backbone",
    #     ),
    # ),
    RunSpec(
        name="strategy_c_bayesian_optimization_per_channel_no_backbone",
        output_name="strategy_c_bayesian_optimization_per_channel_no_backbone.txt",
        kind="subprocess",
        script_path=VARIANT_RUNNER,
        args=(
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
    #     script_path=VARIANT_RUNNER,
    #     args=(
    #         "--method",
    #         AUTOREJECT_RANDOM_SEARCH,
    #         "--scope",
    #         THRESHOLD_SCOPE_GLOBAL,
    #         "--no-backbone",
    #     ),
    # ),
    # RunSpec(
    #     name="strategy_c_random_search_per_channel_with_backbone",
    #     output_name="strategy_c_random_search_per_channel_with_backbone.txt",
    #     kind="subprocess",
    #     script_path=VARIANT_RUNNER,
    #     args=(
    #         "--method",
    #         AUTOREJECT_RANDOM_SEARCH,
    #         "--scope",
    #         THRESHOLD_SCOPE_PER_CHANNEL,
    #         "--with-backbone",
    #     ),
    # ),
    # RunSpec(
    #     name="strategy_c_bayesian_optimization_per_channel_with_backbone",
    #     output_name="strategy_c_bayesian_optimization_per_channel_with_backbone.txt",
    #     kind="subprocess",
    #     script_path=VARIANT_RUNNER,
    #     args=(
    #         "--method",
    #         AUTOREJECT_BAYESIAN_OPTIMIZATION,
    #         "--scope",
    #         THRESHOLD_SCOPE_PER_CHANNEL,
    #         "--with-backbone",
    #     ),
    # ),
    # RunSpec(
    #     name="strategy_c_global_threshold_with_backbone",
    #     output_name="strategy_c_global_threshold_with_backbone.txt",
    #     kind="subprocess",
    #     script_path=VARIANT_RUNNER,
    #     args=(
    #         "--method",
    #         AUTOREJECT_RANDOM_SEARCH,
    #         "--scope",
    #         THRESHOLD_SCOPE_GLOBAL,
    #         "--with-backbone",
    #     ),
    # ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Step 1 baselines and Strategy C Step 1 variants one at a "
            "time, saving each output to development_strategy/strategy_C/output."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help="Directory where per-run output files and the manifest are written.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip runs whose output file already exists and is non-empty.",
    )
    parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="Stop immediately if any run fails.",
    )
    parser.add_argument(
        "--disable-threshold-rescale",
        action="store_true",
        help=(
            "Pass through to Strategy C variant runs so Stage 1 scanning uses the raw "
            "autoreject threshold instead of the fixed scan-threshold scale."
        ),
    )
    return parser.parse_args()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_manifest(manifest_path: Path, entry: dict[str, object]) -> None:
    with manifest_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def build_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    repo_root = str(REPO_ROOT)
    env["PYTHONPATH"] = repo_root if not existing else f"{repo_root}{os.pathsep}{existing}"
    return env


def print_frame(title: str, frame: pd.DataFrame, columns: list[str] | None = None) -> None:
    print(f"\n=== {title} ===")
    if frame.empty:
        print("<empty>")
        return
    if columns is not None:
        selected_columns = [column for column in columns if column in frame.columns]
        frame = frame.loc[:, selected_columns]
    print(frame.to_string(index=False))


def strip_verbose_tables(text: str) -> str:
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


def run_strategy_b_step1_baseline() -> None:
    epochs = load_first_5_epochs().copy().pick([TARGET_CHANNEL])
    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=1.0,
        filter_high=20.0,
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
    metrics = match_blink_tables(
        mapped_positions,
        reference,
        n_epochs=len(epochs),
    )

    print("script=strategy_b_step1_baseline_inline")
    print("detector=find_eog_candidate_regions(...)")
    print("stage_boundary=step1_only")
    print(f"dataset={REPO_ROOT / 'sample_data' / 'dev_epo.fif'}")
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


def build_run_command(spec: RunSpec, args: argparse.Namespace) -> list[str]:
    assert spec.script_path is not None
    command = [sys.executable, str(spec.script_path), *spec.args]
    if (
        args.disable_threshold_rescale
        and spec.script_path == VARIANT_RUNNER
        and "--disable-threshold-rescale" not in command
    ):
        command.append("--disable-threshold-rescale")
    return command


def write_subprocess_output(spec: RunSpec, output_path: Path, args: argparse.Namespace) -> int:
    assert spec.script_path is not None
    command = build_run_command(spec, args)
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=build_subprocess_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    with output_path.open("w", encoding="utf-8") as handle:
        print(f"batch_runner={Path(__file__).name}", file=handle)
        print(f"run_name={spec.name}", file=handle)
        print(f"python_executable={sys.executable}", file=handle)
        print(f"started_at_utc={utc_now_iso()}", file=handle)
        print(f"command={command}", file=handle)
        print("", file=handle)
        handle.write(strip_verbose_tables(result.stdout))
    return int(result.returncode)


def write_callable_output(spec: RunSpec, output_path: Path) -> int:
    buffer = io.StringIO()
    with redirect_stdout(buffer), redirect_stderr(buffer):
        run_strategy_b_step1_baseline()
    with output_path.open("w", encoding="utf-8") as handle:
        print(f"batch_runner={Path(__file__).name}", file=handle)
        print(f"run_name={spec.name}", file=handle)
        print(f"python_executable={sys.executable}", file=handle)
        print(f"started_at_utc={utc_now_iso()}", file=handle)
        print("", file=handle)
        handle.write(strip_verbose_tables(buffer.getvalue()))
    return 0


def execute_run(spec: RunSpec, output_path: Path, args: argparse.Namespace) -> int:
    if spec.kind == "subprocess":
        return write_subprocess_output(spec, output_path, args)
    if spec.kind == "callable":
        return write_callable_output(spec, output_path)
    raise ValueError(f"Unsupported run kind: {spec.kind}")


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    manifest_path = output_dir / MANIFEST_PATH.name
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
            append_manifest(
                manifest_path,
                {
                    "elapsed_s": 0.0,
                    "finished_at_utc": utc_now_iso(),
                    "output_path": str(output_path),
                    "returncode": None,
                    "run_name": spec.name,
                    "started_at_utc": utc_now_iso(),
                    "status": "skipped_existing",
                },
            )
            continue

        print(f"[{index}/{len(RUN_SPECS)}] start {spec.name} -> {output_path.name}")
        started = perf_counter()
        started_at = utc_now_iso()
        returncode = execute_run(spec, output_path, args)
        elapsed_s = perf_counter() - started
        status = "ok" if returncode == 0 else "failed"
        print(
            f"[{index}/{len(RUN_SPECS)}] done {spec.name} "
            f"status={status} returncode={returncode} elapsed_s={elapsed_s:.3f}"
        )
        append_manifest(
            manifest_path,
            {
                "elapsed_s": round(elapsed_s, 6),
                "finished_at_utc": utc_now_iso(),
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


if __name__ == "__main__":
    raise SystemExit(main())
