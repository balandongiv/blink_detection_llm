"""
Tutorial 15 – Strategy C (Autoreject / Bayesian Optimisation) on a full recording.

Pipeline
--------
1. Load eeg_eog_raw.fif and keep only the channels defined in brain_region.yaml.
2. Slice the continuous recording into non-overlapping 60-second epochs.
3. Run the Strategy-C autoreject detector (no frontal backbone, per-channel
   thresholds, Bayesian optimisation) over ALL epochs.
4. Load the human-annotated blink table (absolute onset/duration in seconds).
5. Re-index annotations into epoch-relative coordinates so they can be compared
   with the detector output using the standard match_blink_tables helper.
6. Print detection metrics.
7. Build an MNE HTML report with one plot per Stage 1 candidate blink,
   each windowed to [onset − 0.3 s, onset + duration + 0.3 s].
"""

from __future__ import annotations

from pathlib import Path
import sys
from time import perf_counter

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — safe for report generation
import matplotlib.pyplot as plt
import mne
import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pyblinker.common.validation import match_blink_tables
from pyblinker.strategy_c import (
    AUTOREJECT_BAYESIAN_OPTIMIZATION,
    epoch_detection_strategy_c_autoreject,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
FIF_PATH = Path(
    r"D:\dataset\drowsy_driving_raja_processed\S1\S01_20170519_043933\seg_data_raw\eeg_eog_raw.fif"
)
ANNOTATION_PATH = Path(
    r"D:\dataset\drowsy_driving_raja\human_label_annotation"
    r"\S1\S01_20170519_043933\ear_eog.csv"
)
BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"

# HTML report written next to this script
REPORT_PATH = Path(__file__).with_suffix(".html")

# ---------------------------------------------------------------------------
# Detection settings
# ---------------------------------------------------------------------------
EPOCH_DURATION_S = 60.0
DISABLE_BACKBONE_CHANNELS = ("__NO_BACKBONE__",)
BLINK_PAD_S = 0.1  # seconds of context before / after each blink


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def load_brain_region_channels(yaml_path: Path) -> list[str]:
    """Return a flat list of channel names from all regions in brain_region.yaml."""
    with yaml_path.open() as fh:
        config = yaml.safe_load(fh)
    channels: list[str] = []
    for region_channels in config["eeg_regions"].values():
        channels.extend(region_channels)
    return channels


def load_raw_with_brain_channels(
    fif_path: Path,
    brain_channels: list[str],
) -> mne.io.BaseRaw:
    """Load raw FIF and retain only the requested brain-region channels."""
    raw = mne.io.read_raw_fif(str(fif_path), preload=True, verbose="ERROR")
    available = [ch for ch in brain_channels if ch in raw.ch_names]
    missing = [ch for ch in brain_channels if ch not in raw.ch_names]
    if missing:
        print(f"[warn] channels in yaml but absent in file: {missing}")
    raw.pick(available)
    return raw


def make_fixed_epochs(raw: mne.io.BaseRaw, duration: float = EPOCH_DURATION_S) -> mne.Epochs:
    """Slice a continuous Raw object into fixed-length epochs."""
    return mne.make_fixed_length_epochs(
        raw,
        duration=duration,
        preload=True,
        verbose="ERROR",
    )


def load_annotation_as_reference(
    csv_path: Path,
    epoch_duration: float = EPOCH_DURATION_S,
    blink_description: str | None = None,
) -> pd.DataFrame:
    """Convert an absolute-time annotation CSV to an epoch-relative ground_truth table.

    Each row is mapped via::

        epoch_index = floor(onset / epoch_duration)
        blink_onset = onset - epoch_index * epoch_duration

    Returns a DataFrame with columns ``epoch_index``, ``blink_onset``,
    ``blink_duration``.
    """
    df = pd.read_csv(csv_path).dropna(subset=["onset", "duration"])
    if blink_description is not None and "description" in df.columns:
        df = df[df["description"] == blink_description].copy()

    rows: list[dict] = []
    for _, row in df.iterrows():
        onset_abs = float(row["onset"])
        duration = float(row["duration"])
        epoch_index = int(onset_abs // epoch_duration)
        rows.append(
            {
                "epoch_index": epoch_index,
                "blink_onset": onset_abs - epoch_index * epoch_duration,
                "blink_duration": duration,
            }
        )
    return pd.DataFrame(rows, columns=["epoch_index", "blink_onset", "blink_duration"])


# ---------------------------------------------------------------------------
# MNE report
# ---------------------------------------------------------------------------

def _blink_figure(
    signal: np.ndarray,
    times: np.ndarray,
    *,
    onset_s: float,
    duration_s: float,
    channel: str,
    epoch_index: int,
    blink_index: int,
    threshold: float | None = None,
) -> plt.Figure:
    """Return a single blink-window figure."""
    fig, ax = plt.subplots(figsize=(7, 2.5), constrained_layout=True)
    ax.plot(times, signal * 1e6, color="steelblue", linewidth=0.9)
    ax.axvline(onset_s, color="red", linestyle="--", linewidth=1.0, label="onset")
    ax.axvline(
        onset_s + duration_s,
        color="darkorange",
        linestyle="--",
        linewidth=1.0,
        label="offset",
    )
    ax.axvspan(onset_s, onset_s + duration_s, alpha=0.12, color="red", label="blink")
    if threshold is not None:
        ax.axhline(
            threshold * 1e6,
            color="purple",
            linestyle=":",
            linewidth=0.8,
            label=f"threshold ({threshold * 1e6:.1f} µV)",
        )
        ax.axhline(
            -threshold * 1e6,
            color="purple",
            linestyle=":",
            linewidth=0.8,
        )
    ax.set_xlabel("Time within epoch (s)")
    ax.set_ylabel("Amplitude (µV)")
    ax.set_title(f"Epoch {epoch_index}  |  Blink {blink_index}  |  ch={channel}")
    ax.legend(fontsize=7, loc="upper right")
    return fig


def build_stage1_report(
    epochs: mne.Epochs,
    stage1_candidates: pd.DataFrame,
    stage1_thresholds: dict[str, float],
    *,
    pad_s: float = BLINK_PAD_S,
) -> mne.Report:
    """Build an MNE HTML report from Stage 1 candidate blinks.

    Each candidate is plotted in a window ``[onset - pad_s, onset + duration + pad_s]``
    on the channel that produced the candidate.  Plots are grouped by epoch in the
    report.

    Parameters
    ----------
    epochs:
        The 60-second MNE Epochs object (preloaded).
    stage1_candidates:
        ``detector.stage1_candidates_`` DataFrame with columns
        ``epoch_index``, ``channel``, ``blink_onset``, ``blink_duration``.
    stage1_thresholds:
        ``detector.stage1_thresholds_`` — maps channel name → threshold (V).
    pad_s:
        Seconds of context to include before onset and after offset.

    Returns
    -------
    mne.Report
    """
    if stage1_candidates.empty:
        report = mne.Report(title="Stage 1 Blink Report")
        report.add_html("<p>No Stage 1 candidates detected.</p>", title="Summary")
        return report

    sfreq = epochs.info["sfreq"]
    epoch_data = epochs.get_data()          # (n_epochs, n_channels, n_times)
    epoch_times = epochs.times              # time axis relative to epoch start (s)
    ch_names = list(epochs.ch_names)

    n_epochs_total = len(epochs)
    n_candidates = len(stage1_candidates)

    report = mne.Report(
        title="Tutorial 15 – Stage 1 Blink Report",
        verbose=False,
    )

    # --- Summary section ---------------------------------------------------
    summary_html = (
        f"<h2>Stage 1 Blink Detection Summary</h2>"
        f"<ul>"
        f"<li><b>FIF path:</b> {FIF_PATH}</li>"
        f"<li><b>Epoch duration:</b> {EPOCH_DURATION_S:.0f} s</li>"
        f"<li><b>Total epochs:</b> {n_epochs_total}</li>"
        f"<li><b>Stage 1 candidates:</b> {n_candidates}</li>"
        f"<li><b>Pad:</b> ±{pad_s:.2f} s</li>"
        f"<li><b>Autoreject method:</b> {AUTOREJECT_BAYESIAN_OPTIMIZATION}</li>"
        f"</ul>"
    )
    report.add_html(summary_html, title="Summary", section="Overview")

    # --- Per-epoch blink figures -------------------------------------------
    pad_samples = int(pad_s * sfreq)

    for epoch_index, group in stage1_candidates.groupby("epoch_index"):
        epoch_index = int(epoch_index)
        if epoch_index >= n_epochs_total:
            continue  # guard against out-of-range indices

        for blink_index, (_, row) in enumerate(
            group.sort_values("blink_onset").iterrows()
        ):
            ch_name = str(row["channel"])
            onset_s = float(row["blink_onset"])
            duration_s = float(row["blink_duration"])

            # Resolve channel index; fall back to channel 0 if not found
            if ch_name in ch_names:
                ch_idx = ch_names.index(ch_name)
            else:
                ch_idx = 0
                ch_name = ch_names[0]

            signal_epoch = epoch_data[epoch_index, ch_idx, :]  # (n_times,)

            # Clamp window to valid sample range
            onset_sample = int(onset_s * sfreq)
            offset_sample = int((onset_s + duration_s) * sfreq)
            start_sample = max(0, onset_sample - pad_samples)
            end_sample = min(signal_epoch.shape[-1], offset_sample + pad_samples)

            signal_win = signal_epoch[start_sample:end_sample]
            times_win = epoch_times[start_sample:end_sample]

            threshold = stage1_thresholds.get(ch_name)

            fig = _blink_figure(
                signal_win,
                times_win,
                onset_s=onset_s,
                duration_s=duration_s,
                channel=ch_name,
                epoch_index=epoch_index,
                blink_index=blink_index,
                threshold=threshold,
            )

            section_title = f"Epoch {epoch_index:03d}"
            report.add_figure(
                fig,
                title=f"Blink {blink_index}  ch={ch_name}  "
                      f"onset={onset_s:.3f}s  dur={duration_s:.3f}s",
                section=section_title,
                image_format="png",
            )
            plt.close(fig)

    return report


# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------

def print_frame(title: str, frame: pd.DataFrame, columns: list[str] | None = None) -> None:
    print(f"\n=== {title} ===")
    if frame.empty:
        print("<empty>")
        return
    if columns is not None:
        existing = [col for col in columns if col in frame.columns]
        frame = frame.loc[:, existing]
    print(frame.to_string(index=False))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"script={Path(__file__).name}")
    print("variant=Brain-region channels / no weighted frontal backbone / Bayesian Optimisation")
    print(f"fif_path={FIF_PATH}")
    print(f"annotation_path={ANNOTATION_PATH}")
    print(f"brain_region_yaml={BRAIN_REGION_YAML}")
    print(f"epoch_duration_s={EPOCH_DURATION_S}")
    print(f"pad_s={BLINK_PAD_S}")
    print(f"stage1_channels={DISABLE_BACKBONE_CHANNELS}")
    print(f"autoreject_method={AUTOREJECT_BAYESIAN_OPTIMIZATION}")
    print(f"report_path={REPORT_PATH}")

    # ------------------------------------------------------------------
    # Step 1 – Load raw and keep brain-region channels
    # ------------------------------------------------------------------
    print("\n[1] Loading raw data …")
    brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
    print(f"    brain_region channels ({len(brain_channels)}): {brain_channels}")

    raw = load_raw_with_brain_channels(FIF_PATH, brain_channels)
    print(f"    recording duration : {raw.times[-1]:.2f} s")
    print(f"    sampling rate      : {raw.info['sfreq']} Hz")
    print(f"    channels retained  : {len(raw.ch_names)} → {raw.ch_names}")

    # ------------------------------------------------------------------
    # Step 2 – Slice into 60-second epochs
    # ------------------------------------------------------------------
    print(f"\n[2] Slicing into {EPOCH_DURATION_S:.0f}-second epochs …")
    epochs = make_fixed_epochs(raw, duration=EPOCH_DURATION_S)
    print(f"    total epochs: {len(epochs)}")

    # ------------------------------------------------------------------
    # Step 3 – Load human annotation → epoch-relative ground_truth
    # ------------------------------------------------------------------
    print("\n[3] Loading human annotation …")
    reference = load_annotation_as_reference(ANNOTATION_PATH, epoch_duration=EPOCH_DURATION_S)
    print(f"    annotation rows: {len(reference)}")
    print_frame("Annotation (first 10 rows)", reference.head(10))

    # ------------------------------------------------------------------
    # Step 4 – Run Strategy-C detector (Bayesian optimisation)
    # ------------------------------------------------------------------
    print("\n[4] Running Strategy-C autoreject detector (Bayesian optimisation) …")
    started = perf_counter()

    detector = epoch_detection_strategy_c_autoreject(
        epochs,
        visualize=False,
        filter_low=1.0,
        filter_high=20.0,
        resample_rate=None,
        n_jobs=1,
        use_multiprocessing=False,
        stage1_channels=DISABLE_BACKBONE_CHANNELS,
        stage1_threshold_scope="per_channel",
        autoreject_random_state=42,
        autoreject_method=AUTOREJECT_BAYESIAN_OPTIMIZATION,
        autoreject_augment=False,
    )

    annotations, channel, n_good_blinks, blink_table, _fig_data, selected_channel, _epochs = (
        detector.get_blink()
    )
    elapsed_s = perf_counter() - started

    # ------------------------------------------------------------------
    # Step 5 – Metrics
    # ------------------------------------------------------------------
    metrics = match_blink_tables(blink_table, reference, n_epochs=len(epochs))

    # ------------------------------------------------------------------
    # Step 6 – Console report
    # ------------------------------------------------------------------
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
        "Predicted Blinks (first 20 rows)",
        blink_table.head(20),
        ["epoch_index", "channel", "blink_onset", "blink_duration", "epoch_selection"],
    )

    print("\n=== Metrics Against Human Annotation ===")
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

    # ------------------------------------------------------------------
    # Step 7 – MNE HTML report of Stage 1 blink regions
    # ------------------------------------------------------------------
    print(f"\n[7] Building MNE HTML report ({len(detector.stage1_candidates_)} candidates) …")
    report = build_stage1_report(
        epochs,
        detector.stage1_candidates_,
        detector.stage1_thresholds_,
        pad_s=BLINK_PAD_S,
    )
    report.save(str(REPORT_PATH), overwrite=True, open_browser=False)
    print(f"    report saved → {REPORT_PATH}")


if __name__ == "__main__":
    main()
