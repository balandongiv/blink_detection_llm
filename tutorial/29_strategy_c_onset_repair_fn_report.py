from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import mne
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_RUNNER_SPEC = importlib.util.spec_from_file_location(
    "single_pair_runner",
    REPO_ROOT / "tutorial" / "28_expand_bridge_sw_onset_single_pair_debug.py",
)
_RUNNER_MOD = importlib.util.module_from_spec(_RUNNER_SPEC)  # type: ignore[arg-type]
sys.modules[_RUNNER_SPEC.name] = _RUNNER_MOD
_RUNNER_SPEC.loader.exec_module(_RUNNER_MOD)  # type: ignore[union-attr]

DEFAULT_SUBJECT = "S1"
DEFAULT_SEGMENT = "S01_20170519_043933"
DEFAULT_CHANNEL = "E9"
DEFAULT_PAD_S = 0.75
DEFAULT_MAX_CASES = 50


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", default=DEFAULT_SUBJECT)
    parser.add_argument("--segment", default=DEFAULT_SEGMENT)
    parser.add_argument("--run-dir", default=None)
    parser.add_argument("--channel", default=DEFAULT_CHANNEL)
    parser.add_argument("--pad-s", type=float, default=DEFAULT_PAD_S)
    parser.add_argument("--max-cases", type=int, default=DEFAULT_MAX_CASES)
    return parser.parse_args()


def find_latest_run(segment: str) -> Path:
    root = _RUNNER_MOD.OUTPUT_ROOT / segment
    runs = [path for path in root.iterdir() if path.is_dir()]
    if not runs:
        raise FileNotFoundError(f"No run directories found under {root}")
    return max(runs, key=lambda path: path.stat().st_mtime)


def load_run_dir(run_dir_arg: str | None, segment: str) -> Path:
    if run_dir_arg:
        return Path(run_dir_arg).resolve()
    return find_latest_run(segment)


def load_prepared_signal(subject: str, segment: str, channel: str):
    pair = _RUNNER_MOD.find_target_pair(subject, segment)
    brain_channels = _RUNNER_MOD.load_brain_region_channels(_RUNNER_MOD.BRAIN_REGION_YAML)
    logger = _RUNNER_MOD.logging.getLogger("fn_report")
    logger.handlers.clear()
    logger.addHandler(_RUNNER_MOD.logging.StreamHandler(sys.stdout))
    logger.setLevel(_RUNNER_MOD.logging.INFO)
    raw = _RUNNER_MOD.load_raw_with_brain_channels(Path(pair["fif"]), brain_channels, logger)
    epochs = _RUNNER_MOD.make_fixed_epochs(raw, duration=_RUNNER_MOD.EPOCH_DURATION_S)
    prepared = _RUNNER_MOD.prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=_RUNNER_MOD.FILTER_LOW,
        filter_high=_RUNNER_MOD.FILTER_HIGH,
        resample_rate=_RUNNER_MOD.RESAMPLE_RATE,
    )
    if channel not in prepared.channel_names:
        raise ValueError(f"Channel {channel} not found in prepared data: {prepared.channel_names}")
    ch_idx = prepared.channel_names.index(channel)
    return epochs, prepared, ch_idx, pair


def nearest_candidate(candidates: pd.DataFrame, epoch_index: int, blink_onset: float, blink_duration: float) -> pd.Series | None:
    if candidates.empty:
        return None
    epoch_candidates = candidates[candidates["epoch_index"] == epoch_index].copy()
    if epoch_candidates.empty:
        return None
    epoch_candidates["distance"] = (
        (epoch_candidates["blink_onset"] - blink_onset).abs()
        + (epoch_candidates["blink_duration"] - blink_duration).abs()
    )
    return epoch_candidates.sort_values("distance").iloc[0]


def span_html(label: str, row: pd.Series | None) -> str:
    if row is None:
        return f"<li><b>{label}</b>: none</li>"
    onset = float(row["blink_onset"])
    duration = float(row["blink_duration"])
    abs_onset = float(row.get("absolute_onset_s", np.nan))
    abs_offset = float(row.get("absolute_offset_s", np.nan))
    abs_part = ""
    if np.isfinite(abs_onset) and np.isfinite(abs_offset):
        abs_part = f", absolute={abs_onset:.3f}s-{abs_offset:.3f}s"
    return f"<li><b>{label}</b>: onset={onset:.3f}s, duration={duration:.3f}s{abs_part}</li>"


def enrich_absolute_times(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    out = frame.copy()
    out["absolute_onset_s"] = out["epoch_index"].astype(float) * float(_RUNNER_MOD.EPOCH_DURATION_S) + out["blink_onset"].astype(float)
    out["absolute_offset_s"] = out["absolute_onset_s"] + out["blink_duration"].astype(float)
    return out


def build_case_figure(
    signal: np.ndarray,
    sfreq: float,
    fn_row: pd.Series,
    overlay_row: pd.Series | None,
    overlay_label: str,
    overlay_color: str,
    pad_s: float,
) -> plt.Figure:
    ref_onset = float(fn_row["blink_onset"])
    ref_duration = float(fn_row["blink_duration"])
    ref_end = ref_onset + ref_duration

    start_s = max(0.0, ref_onset - pad_s)
    end_s = min(len(signal) / sfreq, ref_end + pad_s)
    if overlay_row is not None:
        cand_onset = float(overlay_row["blink_onset"])
        cand_end = cand_onset + float(overlay_row["blink_duration"])
        start_s = min(start_s, max(0.0, cand_onset - pad_s / 2.0))
        end_s = max(end_s, min(len(signal) / sfreq, cand_end + pad_s / 2.0))

    start_idx = max(0, int(np.floor(start_s * sfreq)))
    end_idx = min(len(signal) - 1, int(np.ceil(end_s * sfreq)))
    t = np.arange(start_idx, end_idx + 1) / sfreq
    y = signal[start_idx : end_idx + 1]

    fig, ax = plt.subplots(figsize=(11, 3.8))
    ax.plot(t, y, color="black", linewidth=1.0, alpha=0.8)
    ax.axvspan(ref_onset, ref_end, color="#d62728", alpha=0.18, label="Reference FN")
    ax.axvline(ref_onset, color="#d62728", linestyle="--", linewidth=1.0)
    ax.axvline(ref_end, color="#d62728", linestyle="--", linewidth=1.0)

    if overlay_row is not None:
        overlay_onset = float(overlay_row["blink_onset"])
        overlay_end = overlay_onset + float(overlay_row["blink_duration"])
        ax.axvspan(overlay_onset, overlay_end, color=overlay_color, alpha=0.16, label=overlay_label)
        ax.axvline(overlay_onset, color=overlay_color, linestyle=":", linewidth=1.0)
        ax.axvline(overlay_end, color=overlay_color, linestyle=":", linewidth=1.0)

    ax.set_title(
        f"Epoch {int(fn_row['epoch_index'])} | {overlay_label} | ref={ref_onset:.3f}-{ref_end:.3f}s | cause={fn_row['likely_cause']}"
    )
    ax.set_xlabel("Time within epoch (s)")
    ax.set_ylabel("Filtered amplitude")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    return fig


def build_report(
    run_dir: Path,
    subject: str,
    segment: str,
    channel: str,
    pad_s: float,
    max_cases: int,
) -> Path:
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    fn_table = enrich_absolute_times(pd.read_csv(run_dir / "strategy_c_boundary_repair_missed_references.csv"))
    baseline_candidates = enrich_absolute_times(pd.read_csv(run_dir / "strategy_c_best_candidates.csv"))
    repaired_candidates = enrich_absolute_times(pd.read_csv(run_dir / "strategy_c_boundary_repair_best_candidates.csv"))

    epochs, prepared, ch_idx, pair = load_prepared_signal(subject, segment, channel)
    sfreq = float(prepared.sfreq)

    report = mne.Report(
        title=f"Strategy C Onset-Repair False Negatives | {subject} / {segment} / {channel}",
        verbose=False,
    )

    best_repair = summary["strategy_c_boundary_repair_best"]
    summary_html = f"""
    <h3>Strategy C Onset-Repair Residual False Negatives</h3>
    <ul>
      <li><b>Subject / Segment</b>: {subject} / {segment}</li>
      <li><b>Channel</b>: {channel}</li>
      <li><b>Run directory</b>: {run_dir}</li>
      <li><b>FIF</b>: {pair['fif']}</li>
      <li><b>Strategy C baseline</b>: F1={summary['strategy_c_baseline']['f1']:.4f}, TP={summary['strategy_c_baseline']['tp']}, FP={summary['strategy_c_baseline']['fp']}, FN={summary['strategy_c_baseline']['fn']}</li>
      <li><b>Best repaired rule</b>: F1={best_repair['f1']:.4f}, TP={best_repair['tp']}, FP={best_repair['fp']}, FN={best_repair['fn']}</li>
      <li><b>Repair params</b>: short_thr={best_repair['short_event_threshold_s']:.2f}, short_pre={best_repair['short_pre_pad_s']:.2f}, short_post={best_repair['short_post_pad_s']:.2f}, long_post={best_repair['long_post_pad_s']:.2f}, gap={best_repair['merge_gap_s']:.2f}</li>
      <li><b>Residual FN count in report</b>: {min(len(fn_table), max_cases)}</li>
      <li><b>Absolute timing convention</b>: absolute_onset_s = epoch_index * {float(_RUNNER_MOD.EPOCH_DURATION_S):.1f}s + blink_onset</li>
    </ul>
    """
    report.add_html(summary_html, title="Summary", section="Overview")
    if not fn_table.empty:
        report.add_html(fn_table.head(max_cases).to_html(index=False), title="Residual FN Table", section="Overview")

    for i, fn_row in enumerate(fn_table.head(max_cases).itertuples(index=False), start=1):
        fn_series = pd.Series(fn_row._asdict())
        epoch_index = int(fn_series["epoch_index"])
        baseline_row = nearest_candidate(
            baseline_candidates,
            epoch_index,
            float(fn_series["blink_onset"]),
            float(fn_series["blink_duration"]),
        )
        repaired_row = nearest_candidate(
            repaired_candidates,
            epoch_index,
            float(fn_series["blink_onset"]),
            float(fn_series["blink_duration"]),
        )
        if epoch_index < 0 or epoch_index >= prepared.data.shape[0]:
            html = (
                f"<p>Epoch index {epoch_index} is outside the prepared epoch range "
                f"(0-{prepared.data.shape[0] - 1}).</p>"
                f"<ul>"
                f"<li><b>Likely cause</b>: {fn_series['likely_cause']}</li>"
                f"<li><b>Reference absolute onset</b>: {float(fn_series['absolute_onset_s']):.3f}s</li>"
                f"{span_html('Reference', fn_series)}"
                f"{span_html('Nearest strategy_c baseline', baseline_row)}"
                f"{span_html('Nearest repaired candidate', repaired_row)}"
                f"</ul>"
            )
            report.add_html(
                html,
                title=f"FN {i:02d} | Epoch {epoch_index} | metadata only",
                section="Residual False Negatives",
            )
            continue
        signal = prepared.data[epoch_index, ch_idx, :].astype(float)
        caption = (
            f"<ul>"
            f"<li><b>Likely cause</b>: {fn_series['likely_cause']}</li>"
            f"<li><b>Reference absolute onset</b>: {float(fn_series['absolute_onset_s']):.3f}s</li>"
            f"<li><b>Reference absolute offset</b>: {float(fn_series['absolute_offset_s']):.3f}s</li>"
            f"<li><b>Nearest onset diff</b>: {float(fn_series['nearest_onset_diff_s']) if pd.notna(fn_series['nearest_onset_diff_s']) else float('nan'):.3f}s</li>"
            f"<li><b>Nearest overlap ratio</b>: {float(fn_series['nearest_overlap_ratio']) if pd.notna(fn_series['nearest_overlap_ratio']) else float('nan'):.3f}</li>"
            f"{span_html('Reference', fn_series)}"
            f"{span_html('Nearest strategy_c baseline', baseline_row)}"
            f"{span_html('Nearest repaired candidate', repaired_row)}"
            f"</ul>"
        )
        figure_specs = [
            ("Reference FN", fn_series, "#d62728"),
            ("Nearest strategy_c baseline", baseline_row, "#1f77b4"),
            ("Nearest repaired candidate", repaired_row, "#ff7f0e"),
        ]
        for label, overlay_row, color in figure_specs:
            fig = build_case_figure(signal, sfreq, fn_series, overlay_row, label, color, pad_s)
            report.add_figure(
                fig,
                title=f"FN {i:02d} | abs {float(fn_series['absolute_onset_s']):.3f}s | Epoch {epoch_index} | {label}",
                caption=caption,
                section="Residual False Negatives",
                tags=("strategy_c", "onset_repair", "false_negative", channel),
            )
            plt.close(fig)

    output_path = run_dir / "strategy_c_onset_repair_false_negative_report.html"
    report.save(output_path, overwrite=True, open_browser=False)
    return output_path


def main() -> None:
    args = parse_args()
    run_dir = load_run_dir(args.run_dir, args.segment)
    output_path = build_report(
        run_dir=run_dir,
        subject=args.subject,
        segment=args.segment,
        channel=args.channel,
        pad_s=args.pad_s,
        max_cases=args.max_cases,
    )
    print(f"Saved MNE report -> {output_path}")


if __name__ == "__main__":
    main()
