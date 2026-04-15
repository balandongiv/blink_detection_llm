from __future__ import annotations

import argparse
import importlib.util
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

from pyblinker.epoch_detection_strategy_a.epoch_validation import (
    match_blink_tables,
)
from pyblinker.utils.peak_overlap_metric import (
    calculate_interval_overlap_ratio,
    is_peak_overlap_match,
)

DEFAULT_SUBJECT = "S1"
DEFAULT_SEGMENT = "S01_20170519_043933"
DEFAULT_CHANNEL = "E9"
DEFAULT_PEAK_SIDE_TOLERANCE_S = 0.01


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", default=DEFAULT_SUBJECT)
    parser.add_argument("--segment", default=DEFAULT_SEGMENT)
    parser.add_argument("--channel", default=DEFAULT_CHANNEL)
    parser.add_argument("--run-dir", default=None)
    parser.add_argument("--peak-side-tolerance-s", type=float, default=DEFAULT_PEAK_SIDE_TOLERANCE_S)
    return parser.parse_args()


def latest_run_dir(segment: str) -> Path:
    root = _RUNNER_MOD.OUTPUT_ROOT / segment
    return max([path for path in root.iterdir() if path.is_dir()], key=lambda path: path.stat().st_mtime)


def enrich_absolute_times(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    out = frame.copy()
    out["absolute_onset_s"] = (
        out["epoch_index"].astype(float) * float(_RUNNER_MOD.EPOCH_DURATION_S)
        + out["blink_onset"].astype(float)
    )
    out["absolute_offset_s"] = out["absolute_onset_s"] + out["blink_duration"].astype(float)
    return out


def load_pair_signal(subject: str, segment: str, channel: str):
    pair = _RUNNER_MOD.find_target_pair(subject, segment)
    brain_channels = _RUNNER_MOD.load_brain_region_channels(_RUNNER_MOD.BRAIN_REGION_YAML)
    logger = _RUNNER_MOD.logging.getLogger("peak_overlap_tutorial")
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
    ch_idx = prepared.channel_names.index(channel)
    signal_by_epoch = {
        epoch_index: prepared.data[epoch_index, ch_idx, :].astype(float)
        for epoch_index in range(prepared.data.shape[0])
    }
    return pair, epochs, prepared, signal_by_epoch, float(prepared.sfreq)


def nearest_row(table: pd.DataFrame, epoch_index: int, onset: float, duration: float) -> pd.Series | None:
    if table.empty:
        return None
    epoch_rows = table[table["epoch_index"] == epoch_index].copy()
    if epoch_rows.empty:
        return None
    epoch_rows["distance"] = (
        (epoch_rows["blink_onset"] - onset).abs()
        + (epoch_rows["blink_duration"] - duration).abs()
    )
    return epoch_rows.sort_values("distance").iloc[0]


def make_case_record(
    *,
    case_id: str,
    case_type: str,
    description: str,
    ref_row: pd.Series | None,
    pred_row: pd.Series | None,
    epoch_signal: np.ndarray | None,
    sfreq: float,
    peak_side_tolerance_s: float,
) -> dict:
    peak_match = False
    overlap_ratio = np.nan
    if ref_row is not None and pred_row is not None:
        if epoch_signal is not None:
            peak_match = is_peak_overlap_match(
                pred_row,
                ref_row,
                epoch_signal=epoch_signal,
                sfreq=sfreq,
                peak_side_tolerance_s=peak_side_tolerance_s,
            )
        overlap_ratio = calculate_interval_overlap_ratio(
            float(pred_row["blink_onset"]),
            float(pred_row["blink_duration"]),
            float(ref_row["blink_onset"]),
            float(ref_row["blink_duration"]),
        )
    return {
        "case_id": case_id,
        "case_type": case_type,
        "description": description,
        "epoch_index": int(ref_row["epoch_index"] if ref_row is not None else pred_row["epoch_index"]),
        "reference_onset_s": float(ref_row["blink_onset"]) if ref_row is not None else np.nan,
        "reference_duration_s": float(ref_row["blink_duration"]) if ref_row is not None else np.nan,
        "reference_abs_onset_s": float(ref_row["absolute_onset_s"]) if ref_row is not None and "absolute_onset_s" in ref_row else np.nan,
        "predicted_onset_s": float(pred_row["blink_onset"]) if pred_row is not None else np.nan,
        "predicted_duration_s": float(pred_row["blink_duration"]) if pred_row is not None else np.nan,
        "predicted_abs_onset_s": float(pred_row["absolute_onset_s"]) if pred_row is not None and "absolute_onset_s" in pred_row else np.nan,
        "peak_overlap_match": bool(peak_match),
        "overlap_ratio": float(overlap_ratio) if overlap_ratio == overlap_ratio else np.nan,
    }


def plot_case(epoch_signal: np.ndarray, sfreq: float, case: dict, ref_row: pd.Series | None, pred_row: pd.Series | None) -> plt.Figure:
    focus_times = []
    if ref_row is not None:
        focus_times.extend([float(ref_row["blink_onset"]), float(ref_row["blink_onset"]) + float(ref_row["blink_duration"])])
    if pred_row is not None:
        focus_times.extend([float(pred_row["blink_onset"]), float(pred_row["blink_onset"]) + float(pred_row["blink_duration"])])
    start_s = max(0.0, min(focus_times) - 0.8) if focus_times else 0.0
    end_s = min(len(epoch_signal) / sfreq, max(focus_times) + 0.8) if focus_times else min(len(epoch_signal) / sfreq, 2.0)
    start_idx = max(0, int(np.floor(start_s * sfreq)))
    end_idx = min(len(epoch_signal) - 1, int(np.ceil(end_s * sfreq)))
    t = np.arange(start_idx, end_idx + 1) / sfreq
    y = epoch_signal[start_idx : end_idx + 1]

    fig, ax = plt.subplots(figsize=(11, 3.5))
    ax.plot(t, y, color="black", linewidth=1.0)
    if ref_row is not None:
        r_on = float(ref_row["blink_onset"])
        r_off = r_on + float(ref_row["blink_duration"])
        ax.axvspan(r_on, r_off, color="#d62728", alpha=0.18, label="Reference")
        ax.axvline(r_on, color="#d62728", linestyle="--", linewidth=1.0)
        ax.axvline(r_off, color="#d62728", linestyle="--", linewidth=1.0)
    if pred_row is not None:
        p_on = float(pred_row["blink_onset"])
        p_off = p_on + float(pred_row["blink_duration"])
        ax.axvspan(p_on, p_off, color="#1f77b4", alpha=0.16, label="Predicted")
        ax.axvline(p_on, color="#1f77b4", linestyle=":", linewidth=1.0)
        ax.axvline(p_off, color="#1f77b4", linestyle=":", linewidth=1.0)
    ax.set_title(
        f"{case['case_id']} | epoch {case['epoch_index']} | peak_overlap={case['peak_overlap_match']}"
    )
    ax.set_xlabel("Time within epoch (s)")
    ax.set_ylabel("Amplitude")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    return fig


def build_tutorial_report(
    run_dir: Path,
    subject: str,
    segment: str,
    channel: str,
    peak_side_tolerance_s: float,
) -> Path:
    pair, epochs, prepared, signal_by_epoch, sfreq = load_pair_signal(subject, segment, channel)
    reference = enrich_absolute_times(
        _RUNNER_MOD.load_annotation_as_reference(
            Path(pair["csv"]),
            epoch_duration=_RUNNER_MOD.EPOCH_DURATION_S,
        )
    )
    baseline_candidates = enrich_absolute_times(pd.read_csv(run_dir / "strategy_c_best_candidates.csv"))
    repaired_candidates = enrich_absolute_times(pd.read_csv(run_dir / "strategy_c_boundary_repair_best_candidates.csv"))
    repaired_matches = pd.read_csv(run_dir / "strategy_c_boundary_repair_best_matches.csv")
    repaired_pred_status = pd.read_csv(run_dir / "strategy_c_boundary_repair_best_pred_status.csv")

    baseline_metrics = match_blink_tables(
        baseline_candidates,
        reference,
        n_epochs=len(epochs),
        signal_by_epoch=signal_by_epoch,
        sfreq=sfreq,
        peak_side_tolerance_s=peak_side_tolerance_s,
    )
    repaired_metrics = match_blink_tables(
        repaired_candidates,
        reference,
        n_epochs=len(epochs),
        signal_by_epoch=signal_by_epoch,
        sfreq=sfreq,
        peak_side_tolerance_s=peak_side_tolerance_s,
    )

    cases: list[tuple[dict, pd.Series | None, pd.Series | None]] = []
    target_refs = [
        (5, 33.04722199999998, "Visual containment: clipped onset still covers the blink peak."),
        (17, 12.166666999999961, "Visual containment: prediction sits inside the broad human drag label."),
        (20, 54.700000000000045, "Long blink: prediction starts late but still overlaps the dominant peak."),
    ]
    for idx, (epoch_index, onset, description) in enumerate(target_refs, start=1):
        ref_row = reference[
            (reference["epoch_index"] == epoch_index)
            & ((reference["blink_onset"] - onset).abs() < 1e-6)
        ].iloc[0]
        pred_row = nearest_row(
            repaired_candidates,
            epoch_index,
            float(ref_row["blink_onset"]),
            float(ref_row["blink_duration"]),
        )
        case = make_case_record(
            case_id=f"Case {idx}",
            case_type="visual_match",
            description=description,
            ref_row=ref_row,
            pred_row=pred_row,
            epoch_signal=signal_by_epoch.get(epoch_index),
            sfreq=sfreq,
            peak_side_tolerance_s=peak_side_tolerance_s,
        )
        cases.append((case, ref_row, pred_row))

    if not repaired_matches.empty:
        match_row = repaired_matches.iloc[0]
        ref_row = reference.iloc[int(match_row["ref_index"])]
        pred_row = repaired_candidates.iloc[int(match_row["pred_index"])]
        case = make_case_record(
            case_id="Case 4",
            case_type="standard_match",
            description="A standard matched blink under the current peak-overlap definition.",
            ref_row=ref_row,
            pred_row=pred_row,
            epoch_signal=signal_by_epoch.get(int(ref_row["epoch_index"])),
            sfreq=sfreq,
            peak_side_tolerance_s=peak_side_tolerance_s,
        )
        cases.append((case, ref_row, pred_row))

    fp_rows = repaired_pred_status[repaired_pred_status["match_status"] == "fp"].copy()
    if not fp_rows.empty:
        pred_row = enrich_absolute_times(fp_rows).iloc[0]
        ref_row = nearest_row(
            reference,
            int(pred_row["epoch_index"]),
            float(pred_row["blink_onset"]),
            float(pred_row["blink_duration"]),
        )
        case = make_case_record(
            case_id="Case 5",
            case_type="clear_non_match",
            description="A false positive example that should remain unmatched.",
            ref_row=ref_row,
            pred_row=pred_row,
            epoch_signal=signal_by_epoch.get(int(pred_row["epoch_index"])),
            sfreq=sfreq,
            peak_side_tolerance_s=peak_side_tolerance_s,
        )
        cases.append((case, ref_row, pred_row))

    report = mne.Report(
        title=f"Peak-Overlap Evaluation Tutorial | {subject} / {segment} / {channel}",
        verbose=False,
    )
    summary_html = f"""
    <h3>Peak-Overlap Evaluation Tutorial</h3>
    <p>This report uses the current evaluation definition only. There is no legacy fallback.</p>
    <ul>
      <li><b>FIF</b>: {pair['fif']}</li>
      <li><b>CSV</b>: {pair['csv']}</li>
      <li><b>Channel</b>: {channel}</li>
      <li><b>Definition</b>: prediction and ground_truth must overlap in time, the maximum-amplitude sample in their union must lie inside the overlap interval, and the overlap must also cover about &plusmn;{peak_side_tolerance_s:.2f}s around that peak.</li>
      <li><b>Sampling rate</b>: {sfreq:.1f} Hz</li>
    </ul>
    """
    report.add_html(summary_html, title="Definition", section="Overview")

    metric_rows = pd.DataFrame(
        [
            {
                "candidate_set": "strategy_c_baseline",
                "tp": baseline_metrics.true_positives,
                "fp": baseline_metrics.false_positives,
                "fn": baseline_metrics.false_negatives,
                "precision": baseline_metrics.precision,
                "recall": baseline_metrics.recall,
                "f1": baseline_metrics.f1,
            },
            {
                "candidate_set": "strategy_c_repaired",
                "tp": repaired_metrics.true_positives,
                "fp": repaired_metrics.false_positives,
                "fn": repaired_metrics.false_negatives,
                "precision": repaired_metrics.precision,
                "recall": repaired_metrics.recall,
                "f1": repaired_metrics.f1,
            },
        ]
    )
    metric_rows.to_csv(run_dir / "peak_overlap_metric_comparison.csv", index=False)
    report.add_html(metric_rows.to_html(index=False), title="Metric Summary", section="Overview")

    case_rows = pd.DataFrame([case for case, _, _ in cases])
    case_rows.to_csv(run_dir / "peak_overlap_tutorial_cases.csv", index=False)
    report.add_html(case_rows.to_html(index=False), title="Case Summary", section="Overview")

    for case, ref_row, pred_row in cases:
        epoch_index = int(case["epoch_index"])
        epoch_signal = signal_by_epoch.get(epoch_index, np.array([], dtype=float))
        fig = plot_case(epoch_signal, sfreq, case, ref_row, pred_row)
        caption = (
            f"<ul>"
            f"<li><b>Description</b>: {case['description']}</li>"
            f"<li><b>Reference absolute onset</b>: {case['reference_abs_onset_s']:.3f}s</li>"
            f"<li><b>Predicted absolute onset</b>: {case['predicted_abs_onset_s']:.3f}s</li>"
            f"<li><b>Peak-overlap match</b>: {case['peak_overlap_match']}</li>"
            f"<li><b>Overlap ratio</b>: {case['overlap_ratio']:.3f}</li>"
            f"</ul>"
        )
        report.add_figure(
            fig,
            title=f"{case['case_id']} | {case['case_type']}",
            caption=caption,
            section="Example Cases",
            tags=("evaluation", "peak_overlap", channel),
        )
        plt.close(fig)

    tutorial_path = run_dir / "peak_overlap_evaluation_tutorial.html"
    report.save(tutorial_path, overwrite=True, open_browser=False)
    return tutorial_path


def main() -> None:
    args = parse_args()
    run_dir = Path(args.run_dir).resolve() if args.run_dir else latest_run_dir(args.segment)
    tutorial_path = build_tutorial_report(
        run_dir,
        args.subject,
        args.segment,
        args.channel,
        args.peak_side_tolerance_s,
    )
    print(f"Saved tutorial report -> {tutorial_path}")


if __name__ == "__main__":
    main()
