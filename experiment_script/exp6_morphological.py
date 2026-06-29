"""Experiment 6 (detailed): Morphological analysis with duration / amplitude stratification.

Extends ``44_exp6_morphological.py`` with:
- Duration-stratified butterfly plots (short / medium / long blinks)
- Amplitude-stratified butterfly plots (low / medium / high, thresholds from TP events)
- Per-subject butterfly plots for the Raja dataset
- All outputs written to a single MNE HTML report

Blink-type bins
---------------
Duration:
    Short   — < 150 ms
    Medium  — 150–300 ms
    Long    — > 300 ms

Amplitude (absolute peak, µV):
    Low / Medium / High — 33rd and 66th percentile of TP-event peak amplitudes
    (computed per dataset so thresholds adapt to the signal scale).

Report structure
----------------
  Overview                    — session counts table + amplitude thresholds
  All Subjects — <dataset>    — combined TP / FN / FP butterfly (one panel per dataset)
  Duration — <dataset>        — 3-row × 3-col grid: row = duration bin, col = TP/FN/FP
  Amplitude — <dataset>       — 3-row × 3-col grid: row = amplitude bin, col = TP/FN/FP
  Per Subject — Raja          — one TP/FN/FP panel per Raja session
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mne
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blink_evaluation import evaluate_channels, load_annotation_as_reference, enrich_absolute_times
from blink_evaluation.io import dataframe_to_annotations
from src.common.epoch_input import prepare_epoch_detection_input
from experiment_script.channel_group_config import apply_stage_a_channel_group
from pyblinker.double_thresholding import blink_position_strategy_dbo
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, get_raja_paths, load_exp_config
from tutorial.tutorial_utils import (
    discover_cao_pairs, discover_raja_pairs, make_dataset_loaders,
    match_events, extract_window, setup_tutorial_logging,
    valid_epoch_indices_for_pair,
)

logger = logging.getLogger(__name__)

_EXP_CFG = load_exp_config(EXP_SETUP_DIR / "exp6_morphological.yaml")
_RAJA    = get_raja_paths()
_CAO     = get_cao_paths()

# ---------------------------------------------------------------------------
# Toggles
# ---------------------------------------------------------------------------
USE_MULTITHREAD: bool = True
VERBOSE: bool = True

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
RAJA_REGION_YAML     = _RAJA["brain_region_yaml"]
CAO_REGION_YAML      = _CAO["brain_region_yaml"]
RAJA_ANNOTATION_BASE = _RAJA["annotation_base"]
RAJA_PROCESSED_BASE  = _RAJA["processed_base"]
CAO_DATASET_ROOT     = _CAO["dataset_root"]

OUTPUT_DIR = Path(__file__).resolve().parent
REPORT_PATH = OUTPUT_DIR / "exp6_morphological_detailed.html"  # Override via --report-path / --out-dir

# ---------------------------------------------------------------------------
# Experiment parameters
# ---------------------------------------------------------------------------
EPOCH_DURATION_S      = float(_EXP_CFG.get("epoch_duration_s", 30.0))
PEAK_SIDE_TOLERANCE_S = 0.01
WINDOW_S              = 0.25   # ± 250 ms around peak
FILTER_LOW            = float(_EXP_CFG.get("filter_low", 1.0))
FILTER_HIGH           = float(_EXP_CFG.get("filter_high", 20.0))
RESAMPLE_RATE         = 100
N_EPOCHS: int | None  = None

# Strategy F (Proposed-Med) parameters
AUTOREJECT_RANDOM_STATE = 42
STD_THRESHOLD           = float(_EXP_CFG.get("std_threshold", 3.5))
CENTER_METHOD           = _EXP_CFG.get("center_method", "median")
MIN_FLAGGED_EPOCHS      = 1

# Duration bin edges (seconds)
DUR_BINS = [
    ("Short (<150 ms)",    0.000, 0.150),
    ("Medium (150–300 ms)", 0.150, 0.300),
    ("Long (>300 ms)",     0.300, 9999.0),
]

CATEGORY_COLORS = {"TP": "steelblue", "FN": "tomato", "FP": "darkorange"}




# ---------------------------------------------------------------------------
# Single session — returns rich records
# ---------------------------------------------------------------------------

def _build_records(df, indices: list[int], signal_by_epoch: dict, sfreq: float) -> list[dict]:
    """Build event records with window, duration, and amplitude."""
    records = []
    for idx in indices:
        row = df.loc[idx]
        dur = float(row["blink_duration"])
        w = extract_window(
            signal_by_epoch,
            int(row["epoch_index"]),
            float(row["blink_onset"]),
            dur,
            sfreq,
            WINDOW_S,
        )
        if w is None:
            continue
        records.append({
            "window":      w,
            "duration":    dur,
            "amplitude":   float(np.max(np.abs(w))) * 1e6,  # µV absolute peak
            "epoch_index": int(row["epoch_index"]),
        })
    return records


def run_one_session(pair: dict) -> dict:
    dataset_loaders = make_dataset_loaders(
        raja_region_yaml=RAJA_REGION_YAML, cao_region_yaml=CAO_REGION_YAML
    )
    load_fn = dataset_loaders[pair["dataset"]]
    raw = load_fn(pair["fif"])
    epochs = mne.make_fixed_length_epochs(
        raw, duration=EPOCH_DURATION_S, preload=True, verbose="ERROR"
    )
    if N_EPOCHS is not None:
        epochs = epochs[:N_EPOCHS]

    prepared = prepare_epoch_detection_input(
        epochs,
        pick_types_options={"eeg": True},
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
    )
    prepared = apply_stage_a_channel_group(prepared, pair["dataset"])
    valid_epoch_indices = valid_epoch_indices_for_pair(pair, epochs, EPOCH_DURATION_S)
    sfreq = float(prepared.sfreq)

    setting = {
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "std_threshold":      STD_THRESHOLD,
        "center_method":      CENTER_METHOD,
        "min_flagged_epochs": MIN_FLAGGED_EPOCHS,
        "verbose":            VERBOSE,
    }
    channel_results = blink_position_strategy_dbo(prepared, valid_epoch_indices, setting=setting)

    ground_truth_raw = load_annotation_as_reference(pair["csv"], EPOCH_DURATION_S)
    if pair["dataset"] == "cao2018":
        # Exclude blinks inside health-dropped epochs from the morphology pools.
        ground_truth_raw = ground_truth_raw[
            ground_truth_raw["epoch_index"].isin(valid_epoch_indices)
        ].reset_index(drop=True)
    ground_truth = enrich_absolute_times(ground_truth_raw, EPOCH_DURATION_S)
    gt_annotations  = dataframe_to_annotations(ground_truth)
    scored          = evaluate_channels(channel_results, gt_annotations, epoch_duration=EPOCH_DURATION_S)
    best_channel    = scored.best_channel
    best_predicted  = scored.best_predicted
    signal_by_epoch = scored.best_channel_result["signal_by_epoch"]

    tp_pred_idx, fp_pred_idx, fn_gt_idx = match_events(
        best_predicted, ground_truth, signal_by_epoch, sfreq,
        peak_side_tolerance_s=PEAK_SIDE_TOLERANCE_S,
    )

    em = scored.best_eval_result.event_metrics
    return {
        "dataset":      pair["dataset"],
        "session":      pair["name"],
        "best_channel": best_channel,
        "n_tp":         em.tp,
        "n_fp":         em.fp,
        "n_fn":         em.fn,
        "tp_records":   _build_records(best_predicted, tp_pred_idx, signal_by_epoch, sfreq),
        "fp_records":   _build_records(best_predicted, fp_pred_idx, signal_by_epoch, sfreq),
        "fn_records":   _build_records(ground_truth,   fn_gt_idx,   signal_by_epoch, sfreq),
        "sfreq":        sfreq,
    }


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------

def _pad_windows(windows: list[np.ndarray], target_len: int) -> np.ndarray | None:
    """Stack windows into a (n, target_len) matrix, padding / trimming as needed."""
    if not windows:
        return None
    rows = []
    for w in windows:
        if len(w) >= target_len:
            rows.append(w[:target_len])
        else:
            padded = np.zeros(target_len)
            padded[:len(w)] = w
            rows.append(padded)
    return np.stack(rows, axis=0)


def _draw_panel(
    ax: plt.Axes,
    windows: list[np.ndarray],
    t_ms: np.ndarray,
    colour: str,
    label: str,
    target_len: int,
) -> None:
    """Draw butterfly + mean onto *ax*."""
    ax.axvline(0, color="grey", linestyle="--", linewidth=0.8)
    if not windows:
        ax.set_title(f"{label}  (n=0)", fontsize=9)
        ax.set_xlabel("Time from peak (ms)", fontsize=8)
        return

    mat = _pad_windows(windows, target_len)
    t_plot = t_ms[:target_len]

    for row in mat:
        ax.plot(t_plot, row * 1e6, color=colour, alpha=0.15, linewidth=0.5)

    mean_wave = mat.mean(axis=0)
    ax.plot(t_plot, mean_wave * 1e6, color="black", linewidth=2.0, label="mean")
    ax.set_title(f"{label}  (n={len(windows)})", fontsize=9)
    ax.set_xlabel("Time from peak (ms)", fontsize=8)
    ax.set_ylabel("Amplitude (µV)", fontsize=8)
    ax.legend(fontsize=7)
    ax.tick_params(labelsize=7)


def _time_axis(sfreq: float) -> tuple[np.ndarray, int]:
    half_samples = int(round(WINDOW_S * sfreq))
    t_ms = np.linspace(-WINDOW_S * 1000, WINDOW_S * 1000, 2 * half_samples)
    return t_ms, 2 * half_samples


def _make_overview_figure(
    tp_records: list[dict],
    fp_records: list[dict],
    fn_records: list[dict],
    sfreq: float,
    title: str,
) -> plt.Figure:
    """Standard 3-panel TP / FN / FP butterfly figure."""
    t_ms, target_len = _time_axis(sfreq)
    categories = [
        ("TP", [r["window"] for r in tp_records], CATEGORY_COLORS["TP"]),
        ("FN", [r["window"] for r in fn_records], CATEGORY_COLORS["FN"]),
        ("FP", [r["window"] for r in fp_records], CATEGORY_COLORS["FP"]),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharey=False)
    fig.suptitle(title, fontsize=11)

    for ax, (label, windows, colour) in zip(axes, categories):
        _draw_panel(ax, windows, t_ms, colour, label, target_len)

    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Duration stratification
# ---------------------------------------------------------------------------

def _duration_bin_label(dur_s: float) -> str:
    for label, lo, hi in DUR_BINS:
        if lo <= dur_s < hi:
            return label
    return DUR_BINS[-1][0]


def _make_duration_figure(
    tp_records: list[dict],
    fp_records: list[dict],
    fn_records: list[dict],
    sfreq: float,
    title: str,
) -> plt.Figure:
    """3-row × 3-col grid: rows = duration bins, cols = TP / FN / FP."""
    t_ms, target_len = _time_axis(sfreq)
    n_bins = len(DUR_BINS)
    fig, axes = plt.subplots(n_bins, 3, figsize=(14, 4 * n_bins), sharey=False)
    fig.suptitle(title, fontsize=12)

    cat_records = [
        ("TP", tp_records, CATEGORY_COLORS["TP"]),
        ("FN", fn_records, CATEGORY_COLORS["FN"]),
        ("FP", fp_records, CATEGORY_COLORS["FP"]),
    ]

    for row_idx, (bin_label, lo, hi) in enumerate(DUR_BINS):
        for col_idx, (cat_label, records, colour) in enumerate(cat_records):
            ax = axes[row_idx, col_idx]
            windows = [
                r["window"] for r in records
                if lo <= r["duration"] < hi
            ]
            panel_title = f"{bin_label} | {cat_label}"
            _draw_panel(ax, windows, t_ms, colour, panel_title, target_len)
            if col_idx == 0:
                ax.set_ylabel(f"{bin_label}\nAmplitude (µV)", fontsize=8)

    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Amplitude stratification
# ---------------------------------------------------------------------------

def _compute_amplitude_thresholds(tp_records: list[dict]) -> tuple[float, float]:
    """Return (p33, p66) percentiles of TP peak amplitudes; fall back to (0, inf)."""
    if len(tp_records) < 3:
        return 0.0, float("inf")
    amps = np.array([r["amplitude"] for r in tp_records])
    return float(np.percentile(amps, 33)), float(np.percentile(amps, 66))


def _amplitude_bin_label(amp_uv: float, p33: float, p66: float) -> str:
    if amp_uv < p33:
        return f"Low (<{p33:.0f} µV)"
    elif amp_uv < p66:
        return f"Medium ({p33:.0f}–{p66:.0f} µV)"
    else:
        return f"High (≥{p66:.0f} µV)"


def _make_amplitude_figure(
    tp_records: list[dict],
    fp_records: list[dict],
    fn_records: list[dict],
    sfreq: float,
    p33: float,
    p66: float,
    title: str,
) -> plt.Figure:
    """3-row × 3-col grid: rows = amplitude bins, cols = TP / FN / FP."""
    t_ms, target_len = _time_axis(sfreq)

    amp_bins = [
        (f"Low (<{p33:.0f} µV)",            0.0, p33),
        (f"Medium ({p33:.0f}–{p66:.0f} µV)", p33, p66),
        (f"High (≥{p66:.0f} µV)",           p66, float("inf")),
    ]

    cat_records = [
        ("TP", tp_records, CATEGORY_COLORS["TP"]),
        ("FN", fn_records, CATEGORY_COLORS["FN"]),
        ("FP", fp_records, CATEGORY_COLORS["FP"]),
    ]

    fig, axes = plt.subplots(3, 3, figsize=(14, 12), sharey=False)
    fig.suptitle(title, fontsize=12)

    for row_idx, (bin_label, lo, hi) in enumerate(amp_bins):
        for col_idx, (cat_label, records, colour) in enumerate(cat_records):
            ax = axes[row_idx, col_idx]
            windows = [
                r["window"] for r in records
                if lo <= r["amplitude"] < hi
            ]
            panel_title = f"{bin_label} | {cat_label}"
            _draw_panel(ax, windows, t_ms, colour, panel_title, target_len)
            if col_idx == 0:
                ax.set_ylabel(f"{bin_label}\nAmplitude (µV)", fontsize=8)

    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Duration × Category distribution bar chart
# ---------------------------------------------------------------------------

def _make_distribution_figure(
    tp_records: list[dict],
    fp_records: list[dict],
    fn_records: list[dict],
    p33: float,
    p66: float,
    title: str,
) -> plt.Figure:
    """Bar charts showing blink-type distributions across TP / FN / FP."""
    dur_bin_labels = [b[0] for b in DUR_BINS]
    amp_bin_labels = [
        f"Low (<{p33:.0f} µV)",
        f"Medium ({p33:.0f}–{p66:.0f} µV)",
        f"High (≥{p66:.0f} µV)",
    ]

    cat_records = {"TP": tp_records, "FN": fn_records, "FP": fp_records}
    colours = [CATEGORY_COLORS[c] for c in ("TP", "FN", "FP")]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(title, fontsize=12)

    # Duration distribution
    ax = axes[0]
    x = np.arange(len(dur_bin_labels))
    width = 0.25
    for i, (cat, records) in enumerate(cat_records.items()):
        counts = []
        for _, lo, hi in DUR_BINS:
            counts.append(sum(1 for r in records if lo <= r["duration"] < hi))
        ax.bar(x + i * width, counts, width, label=cat, color=colours[i])
    ax.set_xticks(x + width)
    ax.set_xticklabels(dur_bin_labels, fontsize=8)
    ax.set_title("Duration distribution", fontsize=10)
    ax.set_ylabel("Count")
    ax.legend(fontsize=8)

    # Amplitude distribution
    ax = axes[1]
    amp_edges = [(0.0, p33), (p33, p66), (p66, float("inf"))]
    x = np.arange(len(amp_bin_labels))
    for i, (cat, records) in enumerate(cat_records.items()):
        counts = []
        for lo, hi in amp_edges:
            counts.append(sum(1 for r in records if lo <= r["amplitude"] < hi))
        ax.bar(x + i * width, counts, width, label=cat, color=colours[i])
    ax.set_xticks(x + width)
    ax.set_xticklabels(amp_bin_labels, fontsize=8)
    ax.set_title("Amplitude distribution", fontsize=10)
    ax.set_ylabel("Count")
    ax.legend(fontsize=8)

    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Summary table helpers
# ---------------------------------------------------------------------------

def _build_summary_df(sessions: list[dict]) -> pd.DataFrame:
    rows = []
    for s in sessions:
        rows.append({
            "dataset":      s["dataset"],
            "session":      s["session"],
            "best_channel": s["best_channel"],
            "TP":           s["n_tp"],
            "FP":           s["n_fp"],
            "FN":           s["n_fn"],
            "TP_windows":   len(s["tp_records"]),
            "FP_windows":   len(s["fp_records"]),
            "FN_windows":   len(s["fn_records"]),
        })
    return pd.DataFrame(rows).sort_values(["dataset", "session"])


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def build_report(all_sessions: list[dict]) -> mne.Report:
    report = mne.Report(
        title="Exp 6 — Detailed Morphological Analysis",
        verbose=False,
    )

    # ---- Overview --------------------------------------------------------
    summary_df = _build_summary_df(all_sessions)
    report.add_html(
        summary_df.to_html(index=False),
        title="Session Summary",
        section="Overview",
    )

    # ---- Per-dataset sections -------------------------------------------
    for dataset_name in ("raja", "cao2018"):
        sessions = [s for s in all_sessions if s["dataset"] == dataset_name]
        if not sessions:
            continue

        sfreq = sessions[0]["sfreq"]

        tp_all = [r for s in sessions for r in s["tp_records"]]
        fp_all = [r for s in sessions for r in s["fp_records"]]
        fn_all = [r for s in sessions for r in s["fn_records"]]

        p33, p66 = _compute_amplitude_thresholds(tp_all)

        # Threshold info
        thresh_html = (
            f"<p>Amplitude thresholds (from TP events): "
            f"p33 = {p33:.1f} µV, p66 = {p66:.1f} µV</p>"
            f"<p>Total events — TP: {len(tp_all)}, FN: {len(fn_all)}, FP: {len(fp_all)}</p>"
        )
        report.add_html(
            thresh_html,
            title=f"Thresholds — {dataset_name}",
            section="Overview",
        )

        # 1. All-subjects overview butterfly
        fig = _make_overview_figure(
            tp_all, fp_all, fn_all, sfreq,
            f"All Subjects — {dataset_name}  |  TP / FN / FP  "
            f"(window ±{int(WINDOW_S * 1000)} ms)",
        )
        report.add_figure(
            fig,
            title="TP / FN / FP — Overview",
            section=f"All Subjects — {dataset_name}",
            caption=(
                "Butterfly plots: each faint line = one blink waveform; "
                "thick black line = category mean."
            ),
        )
        plt.close(fig)

        # 2. Duration distribution bar chart
        fig = _make_distribution_figure(
            tp_all, fp_all, fn_all, p33, p66,
            f"Blink-Type Distribution — {dataset_name}",
        )
        report.add_figure(
            fig,
            title="Duration & Amplitude Distribution",
            section=f"All Subjects — {dataset_name}",
            caption="Bar charts of blink counts per duration bin and amplitude bin.",
        )
        plt.close(fig)

        # 3. Duration-stratified butterfly
        fig = _make_duration_figure(
            tp_all, fp_all, fn_all, sfreq,
            f"Duration-Stratified Butterflies — {dataset_name}",
        )
        report.add_figure(
            fig,
            title="Duration Stratification",
            section=f"Duration — {dataset_name}",
            caption=(
                "Rows: Short (<150 ms), Medium (150–300 ms), Long (>300 ms).  "
                "Columns: TP, FN, FP."
            ),
        )
        plt.close(fig)

        # 4. Amplitude-stratified butterfly
        fig = _make_amplitude_figure(
            tp_all, fp_all, fn_all, sfreq, p33, p66,
            f"Amplitude-Stratified Butterflies — {dataset_name}",
        )
        report.add_figure(
            fig,
            title="Amplitude Stratification",
            section=f"Amplitude — {dataset_name}",
            caption=(
                f"Amplitude thresholds derived from TP events: "
                f"p33={p33:.1f} µV, p66={p66:.1f} µV.  "
                "Rows: Low / Medium / High.  Columns: TP, FN, FP."
            ),
        )
        plt.close(fig)

    # ---- Per-subject section (Raja only) --------------------------------
    raja_sessions = sorted(
        [s for s in all_sessions if s["dataset"] == "raja"],
        key=lambda x: x["session"],
    )

    if raja_sessions:
        sfreq = raja_sessions[0]["sfreq"]
        for sess in raja_sessions:
            session_label = sess["session"].replace("/", " / ")

            # Overview butterfly for this subject
            fig = _make_overview_figure(
                sess["tp_records"], sess["fp_records"], sess["fn_records"],
                sess["sfreq"],
                f"{session_label}  |  TP / FN / FP  (ch: {sess['best_channel']})",
            )
            report.add_figure(
                fig,
                title=f"{session_label} — Overview",
                section="Per Subject — Raja",
                caption=(
                    f"Session: {session_label}  |  best channel: {sess['best_channel']}  |  "
                    f"TP={sess['n_tp']}, FP={sess['n_fp']}, FN={sess['n_fn']}"
                ),
            )
            plt.close(fig)

            # Duration-stratified for this subject
            has_any = any([sess["tp_records"], sess["fp_records"], sess["fn_records"]])
            if has_any:
                fig = _make_duration_figure(
                    sess["tp_records"], sess["fp_records"], sess["fn_records"],
                    sess["sfreq"],
                    f"{session_label}  |  Duration-Stratified",
                )
                report.add_figure(
                    fig,
                    title=f"{session_label} — Duration Bins",
                    section="Per Subject — Raja",
                    caption=(
                        f"Session: {session_label}  |  "
                        "Duration-stratified butterfly plots."
                    ),
                )
                plt.close(fig)

                # Amplitude-stratified for this subject
                p33_s, p66_s = _compute_amplitude_thresholds(sess["tp_records"])
                fig = _make_amplitude_figure(
                    sess["tp_records"], sess["fp_records"], sess["fn_records"],
                    sess["sfreq"], p33_s, p66_s,
                    f"{session_label}  |  Amplitude-Stratified",
                )
                report.add_figure(
                    fig,
                    title=f"{session_label} — Amplitude Bins",
                    section="Per Subject — Raja",
                    caption=(
                        f"Session: {session_label}  |  "
                        f"Amplitude thresholds: p33={p33_s:.1f} µV, p66={p66_s:.1f} µV."
                    ),
                )
                plt.close(fig)

    return report


# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------

def _print_event_counts(sessions: list[dict], dataset_name: str) -> None:
    rows = [s for s in sessions if s["dataset"] == dataset_name]
    if not rows:
        return
    rows.sort(key=lambda r: r["session"])
    W = max((len(r["session"]) for r in rows), default=8)
    W = max(W, 8)
    hdr = (
        f"{'session':<{W}}  {'best_ch':<14}  "
        f"{'TP':>5}  {'FP':>5}  {'FN':>5}  "
        f"{'TP_w':>6}  {'FP_w':>6}  {'FN_w':>6}"
    )
    sep = "-" * len(hdr)
    print(f"\n{'=' * len(hdr)}\nEVENT COUNTS - {dataset_name.upper()}\n{'=' * len(hdr)}")
    print(hdr); print(sep)
    for r in rows:
        print(
            f"{r['session']:<{W}}  {str(r['best_channel']):<14}  "
            f"{r['n_tp']:>5}  {r['n_fp']:>5}  {r['n_fn']:>5}  "
            f"{len(r['tp_records']):>6}  {len(r['fp_records']):>6}  "
            f"{len(r['fn_records']):>6}"
        )
    print(sep)
    print(
        f"{'TOTAL':<{W}}  {'':14}  "
        f"{sum(r['n_tp'] for r in rows):>5}  "
        f"{sum(r['n_fp'] for r in rows):>5}  "
        f"{sum(r['n_fn'] for r in rows):>5}  "
        f"{sum(len(r['tp_records']) for r in rows):>6}  "
        f"{sum(len(r['fp_records']) for r in rows):>6}  "
        f"{sum(len(r['fn_records']) for r in rows):>6}"
    )
    print(f"{'=' * len(hdr)}\n")


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Experiment 6 (detailed): morphological analysis report for Proposed-Med.",
    )
    p.add_argument(
        "--epoch-duration-s",
        type=float,
        default=EPOCH_DURATION_S,
        help="Epoch duration in seconds (should be set to the best duration from Experiment 1).",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="If set, write report and summary artifacts into this directory (prevents overwriting tutorial outputs).",
    )
    p.add_argument(
        "--report-path",
        type=Path,
        default=None,
        help="Explicit report output path (overrides --out-dir default).",
    )
    p.add_argument(
        "--no-multithread",
        action="store_true",
        help="Disable internal ThreadPoolExecutor.",
    )
    p.add_argument(
        "--n-epochs",
        type=int,
        default=None,
        help="Limit epochs per session for quick runs (None = all).",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce strategy verbosity.",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = _parse_args()

    global USE_MULTITHREAD, VERBOSE, EPOCH_DURATION_S, N_EPOCHS, OUTPUT_DIR, REPORT_PATH
    USE_MULTITHREAD = not args.no_multithread
    VERBOSE = not args.quiet
    EPOCH_DURATION_S = float(args.epoch_duration_s)
    N_EPOCHS = args.n_epochs

    if args.out_dir is not None:
        OUTPUT_DIR = Path(args.out_dir)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.report_path is not None:
        REPORT_PATH = Path(args.report_path)
    elif args.out_dir is not None:
        REPORT_PATH = OUTPUT_DIR / "exp6_morphological_detailed.html"

    setup_tutorial_logging()
    raja_pairs = discover_raja_pairs(RAJA_ANNOTATION_BASE, RAJA_PROCESSED_BASE)
    cao_pairs  = discover_cao_pairs(CAO_DATASET_ROOT)
    all_pairs  = raja_pairs + cao_pairs

    logger.info("Raja sessions   : %d", len(raja_pairs))
    logger.info("Cao2018 sessions: %d", len(cao_pairs))
    logger.info("Window          : ±%d ms", int(WINDOW_S * 1000))
    logger.info("Report output  : %s", REPORT_PATH)

    sessions: list[dict] = []
    errors:   list[str]  = []

    if USE_MULTITHREAD:
        logger.info("Running %d sessions with ThreadPoolExecutor …", len(all_pairs))
        with ThreadPoolExecutor() as executor:
            future_map = {
                executor.submit(run_one_session, pair): pair["name"]
                for pair in all_pairs
            }
            for future in as_completed(future_map):
                name = future_map[future]
                try:
                    sess = future.result()
                    sessions.append(sess)
                    logger.info("done  %s  TP=%d  FP=%d  FN=%d",
                                name, sess["n_tp"], sess["n_fp"], sess["n_fn"])
                except Exception as exc:
                    logger.error("%s: %s", name, exc)
                    errors.append(f"ERROR  {name}: {exc}")
    else:
        logger.info("Running %d sessions sequentially …", len(all_pairs))
        for pair in all_pairs:
            logger.info("running  %s …", pair["name"])
            try:
                sess = run_one_session(pair)
                sessions.append(sess)
                logger.info("done     %s  TP=%d  FP=%d  FN=%d",
                             pair["name"], sess["n_tp"], sess["n_fp"], sess["n_fn"])
            except Exception as exc:
                logger.error("%s: %s", pair["name"], exc)
                errors.append(f"ERROR  {pair['name']}: {exc}")

    if not sessions:
        print("No sessions processed - nothing to report.")
        return

    for ds in ("raja", "cao2018"):
        _print_event_counts(sessions, ds)

    print("\nBuilding MNE HTML report …")
    report = build_report(sessions)
    report.save(str(REPORT_PATH), overwrite=True, open_browser=False)
    print(f"  Saved -> {REPORT_PATH}")

    if args.out_dir is not None:
        out_dir: Path = OUTPUT_DIR
        # Keep only light-weight per-session metrics; full morphological windows live in the HTML report.
        session_rows = [{
            "dataset": s["dataset"],
            "session": s["session"],
            "best_channel": s["best_channel"],
            "epoch_duration_s": float(EPOCH_DURATION_S),
            "tp": int(s["n_tp"]),
            "fp": int(s["n_fp"]),
            "fn": int(s["n_fn"]),
            "tp_windows": int(len(s["tp_records"])),
            "fp_windows": int(len(s["fp_records"])),
            "fn_windows": int(len(s["fn_records"])),
        } for s in sessions]
        _write_csv(out_dir / "exp45_morphological_event_counts.csv", session_rows)
        payload = {
            "experiment": "exp45_morphological_detailed",
            "epoch_duration_s": float(EPOCH_DURATION_S),
            "report_path": str(REPORT_PATH),
            "n_sessions": int(len(sessions)),
        }
        (out_dir / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
