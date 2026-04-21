"""Experiment 6: Morphological analysis of missed and spurious blinks.

Examines which blink morphologies Proposed-Med consistently misses (false
negatives) or misidentifies (false positives) by visualising overlay waveforms
(butterfly plots) for true-positive, false-negative, and false-positive events.

Design
------
For the Proposed-Med condition a 500-millisecond waveform window is extracted
centred on the peak of each blink event.  Events are categorised as:
    TP  — detected interval that overlaps at least one unmatched ground-truth blink.
    FN  — ground-truth blink not matched by any detection.
    FP  — detected blink not matched by any ground-truth blink.

Waveforms are drawn from the frontal channel with the highest mean peak amplitude
across TP events.  Butterfly plots (one panel per category) overlay all single-
trial waveforms for that channel, with the category mean highlighted.

Output
------
Prints per-session event counts (TP / FN / FP) and saves one butterfly-plot
figure per dataset to the working directory.

Datasets
--------
Drowsy Driving Raja corpus and murat_2018.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend; change to "TkAgg" for interactive
import matplotlib.pyplot as plt
import mne
import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analysis.lane_evaluation import evaluate_channel_lanes
from src.common.bad_epochs import get_valid_epoch_indices
from src.common.epoch_input import prepare_epoch_detection_input
from src.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels
from src.matching.blink_matching import enrich_absolute_times, load_annotation_as_reference
from src.strategy_f.runner import channel_results_strategy_f
from src.utils.peak_overlap_metric import is_peak_overlap_match

# ---------------------------------------------------------------------------
# Toggles
# ---------------------------------------------------------------------------
USE_MULTITHREAD: bool = True
VERBOSE: bool = True

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BRAIN_REGION_YAML    = REPO_ROOT / "brain_region.yaml"
RAJA_ANNOTATION_BASE = Path(r"D:\dataset\drowsy_driving_raja\human_label_annotation_eeg")
RAJA_PROCESSED_BASE  = Path(r"D:\dataset\drowsy_driving_raja_processed")
MURAT_DATASET_ROOT   = Path(r"D:\dataset\murat_2018")

OUTPUT_DIR = Path(__file__).resolve().parent  # save figures next to this script

# ---------------------------------------------------------------------------
# Experiment parameters
# ---------------------------------------------------------------------------
EPOCH_DURATION_S        = 60.0
PEAK_SIDE_TOLERANCE_S   = 0.01
WINDOW_S                = 0.25   # ± 250 ms around peak → 500 ms total window
FILTER_LOW              = 1.0
FILTER_HIGH             = 20.0
RESAMPLE_RATE           = None
N_EPOCHS: int | None    = None

# Strategy F (Proposed-Med) parameters
AUTOREJECT_RANDOM_STATE = 42
STD_THRESHOLD           = 3.5
CENTER_METHOD           = "median"
MIN_FLAGGED_EPOCHS      = 1


# ---------------------------------------------------------------------------
# Dataset discovery
# ---------------------------------------------------------------------------

def _discover_raja_pairs() -> list[dict]:
    pairs: list[dict] = []
    for yaml_path in sorted(RAJA_ANNOTATION_BASE.rglob("VideoFrameViewers.yaml")):
        with yaml_path.open("r", encoding="utf-8") as fh:
            info = yaml.safe_load(fh)
        if (info or {}).get("status") != "complete_eeg":
            continue
        session_dir = yaml_path.parent
        rel = session_dir.relative_to(RAJA_ANNOTATION_BASE)
        csv_path = session_dir / "ear_eog.csv"
        fif_path = RAJA_PROCESSED_BASE / rel / "seg_data_raw" / "eeg_eog_raw.fif"
        if not csv_path.exists() or not fif_path.exists():
            continue
        pairs.append({
            "dataset": "raja",
            "name":    str(rel).replace("\\", "/"),
            "fif":     fif_path,
            "csv":     csv_path,
        })
    return pairs


def _discover_murat_pairs() -> list[dict]:
    pairs: list[dict] = []
    for subject_dir in sorted(MURAT_DATASET_ROOT.iterdir()):
        if not subject_dir.is_dir():
            continue
        sid = subject_dir.name
        fif = subject_dir / f"{sid}.fif"
        csv = subject_dir / f"{sid}.csv"
        if fif.is_file() and csv.is_file():
            pairs.append({"dataset": "murat2018", "name": sid, "fif": fif, "csv": csv})
    return pairs


# ---------------------------------------------------------------------------
# Raw loading helpers
# ---------------------------------------------------------------------------

def _load_raja_raw(fif_path: Path) -> mne.io.BaseRaw:
    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    return load_raw_with_brain_channels(fif_path, brain_channels)


def _load_murat_raw(fif_path: Path) -> mne.io.BaseRaw:
    return mne.io.read_raw_fif(str(fif_path), preload=True, verbose="ERROR")


_DATASET_LOADERS = {"raja": _load_raja_raw, "murat2018": _load_murat_raw}


# ---------------------------------------------------------------------------
# Greedy overlap matching — returns (tp_pred_indices, fp_pred_indices, fn_gt_indices)
# ---------------------------------------------------------------------------

def _match_events(
    predicted,
    ground_truth,
    signal_by_epoch: dict,
    sfreq: float,
) -> tuple[list[int], list[int], list[int]]:
    """Greedy overlap matching (same algorithm as match_blink_tables).

    Returns indices into *predicted* and *ground_truth* DataFrames.
    """
    predicted   = predicted.reset_index(drop=True)
    ground_truth = ground_truth.reset_index(drop=True)

    matched_pred: set[int] = set()
    matched_gt:   set[int] = set()

    epoch_indices = sorted(
        set(predicted["epoch_index"].tolist())
        | set(ground_truth["epoch_index"].tolist())
    )

    for ep in epoch_indices:
        pred_group = predicted[predicted["epoch_index"] == ep]
        gt_group   = ground_truth[ground_truth["epoch_index"] == ep]
        unmatched_gt = set(gt_group.index.tolist())
        epoch_signal = np.asarray(signal_by_epoch.get(int(ep), []), dtype=float)

        for pi, pred_row in pred_group.sort_values("blink_onset").iterrows():
            best_gi = None
            for gi in list(unmatched_gt):
                gt_row = gt_group.loc[gi]
                if is_peak_overlap_match(
                    pred_row, gt_row,
                    epoch_signal=epoch_signal,
                    sfreq=sfreq,
                    peak_side_tolerance_s=PEAK_SIDE_TOLERANCE_S,
                ):
                    best_gi = gi
                    break
            if best_gi is not None:
                matched_pred.add(pi)
                matched_gt.add(best_gi)
                unmatched_gt.remove(best_gi)

    tp_pred = list(matched_pred)
    fp_pred = [i for i in predicted.index if i not in matched_pred]
    fn_gt   = [i for i in ground_truth.index if i not in matched_gt]
    return tp_pred, fp_pred, fn_gt


# ---------------------------------------------------------------------------
# Waveform extraction
# ---------------------------------------------------------------------------

def _extract_window(
    signal_by_epoch: dict,
    epoch_index: int,
    onset_s: float,
    duration_s: float,
    sfreq: float,
    window_s: float,
) -> np.ndarray | None:
    """Extract a symmetric window centred on the peak of the blink event.

    Returns a 1D array of length ``2 * int(window_s * sfreq)``, or None if
    the epoch signal is unavailable or the window falls out of bounds.
    """
    epoch_signal = signal_by_epoch.get(int(epoch_index))
    if epoch_signal is None or len(epoch_signal) == 0:
        return None

    start_samp = int(round(onset_s * sfreq))
    end_samp   = int(round((onset_s + duration_s) * sfreq))
    start_samp = max(0, min(start_samp, len(epoch_signal) - 1))
    end_samp   = max(start_samp, min(end_samp, len(epoch_signal)))

    if end_samp <= start_samp:
        return None

    event_signal = epoch_signal[start_samp:end_samp]
    peak_local   = int(np.argmax(np.abs(event_signal)))
    peak_samp    = start_samp + peak_local

    half = int(round(window_s * sfreq))
    win_start = peak_samp - half
    win_end   = peak_samp + half

    if win_start < 0 or win_end > len(epoch_signal):
        return None
    return epoch_signal[win_start:win_end].copy()


# ---------------------------------------------------------------------------
# Single session processing
# ---------------------------------------------------------------------------

def run_one_session(pair: dict) -> dict:
    """Run Proposed-Med and collect TP / FN / FP waveforms per channel.

    Returns
    -------
    dict with keys: dataset, session, channel_windows
    where channel_windows maps channel_name → {"TP": [...], "FN": [...], "FP": [...]}
    and each list contains 1D numpy arrays (waveform windows).
    Also includes counts: n_tp, n_fp, n_fn, best_channel.
    """
    load_fn = _DATASET_LOADERS[pair["dataset"]]
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
    valid_epoch_indices = get_valid_epoch_indices(epochs)
    sfreq = float(prepared.sfreq)

    setting = {
        "autoreject_random_state": AUTOREJECT_RANDOM_STATE,
        "std_threshold":      STD_THRESHOLD,
        "center_method":      CENTER_METHOD,
        "min_flagged_epochs": MIN_FLAGGED_EPOCHS,
        "verbose":            VERBOSE,
    }
    channel_results = channel_results_strategy_f(prepared, valid_epoch_indices, setting=setting)

    ground_truth = enrich_absolute_times(
        load_annotation_as_reference(pair["csv"], EPOCH_DURATION_S),
        EPOCH_DURATION_S,
    )
    scored = evaluate_channel_lanes(
        channel_results,
        ground_truth,
        n_epochs=len(epochs),
        sfreq=sfreq,
        epoch_duration=EPOCH_DURATION_S,
        peak_side_tolerance_s=PEAK_SIDE_TOLERANCE_S,
    )
    best_result  = scored.best_result
    best_channel = best_result["channel"]
    best_predicted = scored.best_predicted
    signal_by_epoch = best_result["signal_by_epoch"]

    tp_pred_idx, fp_pred_idx, fn_gt_idx = _match_events(
        best_predicted, ground_truth, signal_by_epoch, sfreq
    )

    def _windows_from_df(df, indices: list[int]) -> list[np.ndarray]:
        windows = []
        for idx in indices:
            row = df.loc[idx]
            w = _extract_window(
                signal_by_epoch,
                int(row["epoch_index"]),
                float(row["blink_onset"]),
                float(row["blink_duration"]),
                sfreq,
                WINDOW_S,
            )
            if w is not None:
                windows.append(w)
        return windows

    tp_windows = _windows_from_df(best_predicted, tp_pred_idx)
    fp_windows = _windows_from_df(best_predicted, fp_pred_idx)
    fn_windows = _windows_from_df(ground_truth,   fn_gt_idx)

    m = scored.best_metrics
    return {
        "dataset":      pair["dataset"],
        "session":      pair["name"],
        "best_channel": best_channel,
        "n_tp":         m.true_positives,
        "n_fp":         m.false_positives,
        "n_fn":         m.false_negatives,
        "tp_windows":   tp_windows,
        "fp_windows":   fp_windows,
        "fn_windows":   fn_windows,
        "sfreq":        sfreq,
    }


# ---------------------------------------------------------------------------
# Butterfly plot
# ---------------------------------------------------------------------------

def _butterfly_plot(
    sessions: list[dict],
    dataset_name: str,
    output_path: Path,
) -> None:
    """Concatenate waveforms across sessions and draw butterfly plots."""
    all_tp: list[np.ndarray] = []
    all_fp: list[np.ndarray] = []
    all_fn: list[np.ndarray] = []

    for s in sessions:
        if s["dataset"] != dataset_name:
            continue
        all_tp.extend(s["tp_windows"])
        all_fp.extend(s["fp_windows"])
        all_fn.extend(s["fn_windows"])

    # Use the sfreq from the first session (all sessions share the same sfreq)
    sfreq = next((s["sfreq"] for s in sessions if s["dataset"] == dataset_name), 256.0)
    half_samples = int(round(WINDOW_S * sfreq))
    t_ms = np.linspace(-WINDOW_S * 1000, WINDOW_S * 1000, 2 * half_samples)

    categories = [
        ("TP", all_tp, "steelblue"),
        ("FN", all_fn, "tomato"),
        ("FP", all_fp, "darkorange"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharey=False)
    fig.suptitle(
        f"Exp 6 — Morphological analysis  |  {dataset_name}  "
        f"(window ±{int(WINDOW_S * 1000)} ms around blink peak)",
        fontsize=11,
    )

    for ax, (label, windows, colour) in zip(axes, categories):
        if not windows:
            ax.set_title(f"{label}  (n=0)")
            ax.set_xlabel("Time from peak (ms)")
            continue

        # Pad or trim windows to uniform length
        target_len = 2 * half_samples
        trimmed = []
        for w in windows:
            if len(w) >= target_len:
                trimmed.append(w[:target_len])
            else:
                padded = np.zeros(target_len)
                padded[:len(w)] = w
                trimmed.append(padded)

        mat = np.stack(trimmed, axis=0)  # (n_events, n_samples)
        t_plot = t_ms[:target_len]

        for row in mat:
            ax.plot(t_plot, row * 1e6, color=colour, alpha=0.15, linewidth=0.5)

        mean_wave = mat.mean(axis=0)
        ax.plot(t_plot, mean_wave * 1e6, color="black", linewidth=2.0, label="mean")
        ax.axvline(0, color="grey", linestyle="--", linewidth=0.8)
        ax.set_title(f"{label}  (n={len(trimmed)})")
        ax.set_xlabel("Time from peak (ms)")
        ax.set_ylabel("Amplitude (µV)")
        ax.legend(fontsize=8)

    plt.tight_layout()
    fig.savefig(str(output_path), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved butterfly plot → {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _print_event_counts(sessions: list[dict], dataset_name: str) -> None:
    rows = [s for s in sessions if s["dataset"] == dataset_name]
    if not rows:
        return
    rows.sort(key=lambda r: r["session"])

    W_sess = max(len(r["session"]) for r in rows)
    W_sess = max(W_sess, 8)
    header = (
        f"{'session':<{W_sess}}  {'best_ch':<14}  "
        f"{'TP':>5}  {'FP':>5}  {'FN':>5}  "
        f"{'TP_wins':>7}  {'FP_wins':>7}  {'FN_wins':>7}"
    )
    sep = "-" * len(header)

    print(f"\n{'=' * len(header)}")
    print(f"EXP 6 — EVENT COUNTS  —  {dataset_name.upper()}")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    for r in rows:
        print(
            f"{r['session']:<{W_sess}}  {str(r['best_channel']):<14}  "
            f"{r['n_tp']:>5}  {r['n_fp']:>5}  {r['n_fn']:>5}  "
            f"{len(r['tp_windows']):>7}  {len(r['fp_windows']):>7}  "
            f"{len(r['fn_windows']):>7}"
        )

    total_tp  = sum(r["n_tp"] for r in rows)
    total_fp  = sum(r["n_fp"] for r in rows)
    total_fn  = sum(r["n_fn"] for r in rows)
    total_tpw = sum(len(r["tp_windows"]) for r in rows)
    total_fpw = sum(len(r["fp_windows"]) for r in rows)
    total_fnw = sum(len(r["fn_windows"]) for r in rows)
    print(sep)
    print(
        f"{'TOTAL':<{W_sess}}  {'':14}  "
        f"{total_tp:>5}  {total_fp:>5}  {total_fn:>5}  "
        f"{total_tpw:>7}  {total_fpw:>7}  {total_fnw:>7}"
    )
    print(f"{'=' * len(header)}\n")


def main() -> None:
    raja_pairs  = _discover_raja_pairs()
    murat_pairs = _discover_murat_pairs()
    all_pairs   = raja_pairs + murat_pairs

    print(f"Raja sessions  : {len(raja_pairs)}")
    print(f"Murat subjects : {len(murat_pairs)}")
    print(f"Window         : ±{int(WINDOW_S * 1000)} ms (= {int(WINDOW_S * 2 * 1000)} ms total)")

    sessions: list[dict] = []
    errors:   list[str]  = []

    if USE_MULTITHREAD:
        print(f"\nRunning {len(all_pairs)} sessions with ThreadPoolExecutor …")
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
                    print(
                        f"  done  {name}  "
                        f"TP={sess['n_tp']}  FP={sess['n_fp']}  FN={sess['n_fn']}"
                    )
                except Exception as exc:
                    msg = f"  ERROR  {name}: {exc}"
                    print(msg)
                    errors.append(msg)
    else:
        print(f"\nRunning {len(all_pairs)} sessions sequentially …")
        for pair in all_pairs:
            print(f"  running  {pair['name']} …")
            try:
                sess = run_one_session(pair)
                sessions.append(sess)
                print(
                    f"  done     {pair['name']}  "
                    f"TP={sess['n_tp']}  FP={sess['n_fp']}  FN={sess['n_fn']}"
                )
            except Exception as exc:
                msg = f"  ERROR  {pair['name']}: {exc}"
                print(msg)
                errors.append(msg)

    if not sessions:
        print("No sessions processed.")
        return

    for ds in ("raja", "murat2018"):
        _print_event_counts(sessions, ds)
        fig_path = OUTPUT_DIR / f"exp6_butterfly_{ds}.png"
        _butterfly_plot(sessions, ds, fig_path)

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
