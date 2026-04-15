"""
Tutorial 16 – MNE report of human-annotated blinks on frontal EEG channels.

Pipeline
--------
1. Load eeg_eog_raw.fif and keep only the frontal EEG channels defined in
   brain_region.yaml (frontal_left + frontal_right regions).
2. Load the human-annotation CSV (absolute onset / duration in seconds).
3. Assign each annotation to a 60-second epoch:
       epoch_index  = floor(onset / 60)
       epoch_onset  = onset - epoch_index * 60
4. For each annotated blink extract a signal window padded by 0.1 s on both
   sides and build one matplotlib figure per blink.
5. Write a single MNE HTML report with figures grouped by epoch section and
   each figure titled "Blink <N> Epoch <M>".
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mne
import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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
REPORT_PATH = Path(__file__).with_suffix(".html")

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
EPOCH_DURATION_S = 60.0
PAD_S = 0.05               # seconds of context before onset and after offset
FIGSIZE = (8, 3)           # width × height per blink figure

# Colour cycle for the frontal channel overlay
_COLOURS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_frontal_channels(yaml_path: Path) -> dict[str, list[str]]:
    """Return {'frontal_left': [...], 'frontal_right': [...]} from the YAML."""
    with yaml_path.open() as fh:
        config = yaml.safe_load(fh)
    regions = config.get("eeg_regions", {})
    return {
        k: list(v)
        for k, v in regions.items()
        if k.startswith("frontal")
    }


def _load_raw_frontal(
    fif_path: Path,
    frontal_regions: dict[str, list[str]],
) -> tuple[mne.io.BaseRaw, dict[str, list[str]]]:
    """Load the raw FIF and pick only available frontal channels.

    Returns
    -------
    raw : mne.io.BaseRaw
        Preloaded raw object restricted to frontal channels.
    resolved : dict[str, list[str]]
        Region → list of channels actually found in the file.
    """
    raw = mne.io.read_raw_fif(str(fif_path), preload=True, verbose="ERROR")
    raw.resample(sfreq=20)   # downsample to 20 Hz
    # raw.plot(block=True)
    all_frontal = [ch for chs in frontal_regions.values() for ch in chs]
    available = [ch for ch in all_frontal if ch in raw.ch_names]
    missing = [ch for ch in all_frontal if ch not in raw.ch_names]
    if missing:
        print(f"[warn] frontal channels absent in file: {missing}")
    raw.pick(available)

    resolved: dict[str, list[str]] = {
        region: [ch for ch in chs if ch in raw.ch_names]
        for region, chs in frontal_regions.items()
    }
    return raw, resolved


def _load_annotations(csv_path: Path) -> pd.DataFrame:
    """Load the annotation CSV and return a tidy DataFrame.

    Columns returned: ``onset``, ``duration``, ``description`` (if present).
    """
    df = pd.read_csv(csv_path).dropna(subset=["onset", "duration"])
    df = df.reset_index(drop=True)
    df=df.head(10)
    return df


def _assign_epochs(
    annotations: pd.DataFrame,
    epoch_duration: float = EPOCH_DURATION_S,
) -> pd.DataFrame:
    """Add ``epoch_index`` and ``epoch_onset`` columns to an annotation table.

    ``epoch_onset`` is the blink onset expressed relative to the start of its
    assigned epoch.
    """
    annotations = annotations.copy()
    annotations["epoch_index"] = (annotations["onset"] // epoch_duration).astype(int)
    annotations["epoch_onset"] = annotations["onset"] - annotations["epoch_index"] * epoch_duration
    # sequential blink counter *within each epoch* (1-based)
    annotations["blink_in_epoch"] = (
        annotations.groupby("epoch_index").cumcount() + 1
    )
    return annotations


# ---------------------------------------------------------------------------
# Figure builder
# ---------------------------------------------------------------------------

def _blink_figure(
    raw: mne.io.BaseRaw,
    ch_names: list[str],
    *,
    onset_abs_s: float,
    duration_s: float,
    epoch_onset_s: float,
    epoch_index: int,
    blink_in_epoch: int,
    pad_s: float = PAD_S,
) -> plt.Figure:
    """Render one blink window from the raw signal (all frontal channels overlaid).

    Parameters
    ----------
    raw:
        The preloaded raw object (frontal channels only).
    ch_names:
        Channel names to plot (must be a subset of ``raw.ch_names``).
    onset_abs_s:
        Absolute onset of the blink in the recording (seconds).
    duration_s:
        Blink duration (seconds).
    epoch_onset_s:
        Blink onset relative to the start of the enclosing epoch (seconds).
    epoch_index:
        Zero-based epoch index.
    blink_in_epoch:
        1-based blink counter within the epoch (used in the figure title).
    pad_s:
        Padding before / after the blink in seconds.
    """
    sfreq = raw.info["sfreq"]
    n_times = raw.n_times

    t_start = max(0.0, onset_abs_s - pad_s)
    t_end = min(n_times / sfreq, onset_abs_s + duration_s + pad_s)

    start_sample = int(t_start * sfreq)
    end_sample = int(t_end * sfreq)

    # Extract data for all frontal channels in one call
    picks = [raw.ch_names.index(ch) for ch in ch_names if ch in raw.ch_names]
    data = raw.get_data(picks=picks, start=start_sample, stop=end_sample)  # (n_ch, n_t)

    # Time axis relative to epoch start so the x-axis mirrors epoch coordinates
    times = (
        np.arange(start_sample, end_sample) / sfreq
        - epoch_index * EPOCH_DURATION_S
    )

    fig, ax = plt.subplots(figsize=FIGSIZE, constrained_layout=True)

    for i, (ch, trace) in enumerate(zip(ch_names, data)):
        ax.plot(
            times,
            trace * 1e6,
            linewidth=0.85,
            color=_COLOURS[i % len(_COLOURS)],
            label=ch,
            alpha=0.85,
        )

    # Annotate blink interval in epoch-relative coordinates
    ax.axvline(epoch_onset_s, color="red", linestyle="--", linewidth=1.1, label="onset")
    ax.axvline(
        epoch_onset_s + duration_s,
        color="darkorange",
        linestyle="--",
        linewidth=1.1,
        label="offset",
    )
    ax.axvspan(
        epoch_onset_s,
        epoch_onset_s + duration_s,
        alpha=0.15,
        color="red",
        zorder=0,
    )

    ax.set_xlabel("Time within epoch (s)")
    ax.set_ylabel("Amplitude (µV)")
    ax.set_title(
        f"Blink {blink_in_epoch}  Epoch {epoch_index}"
        f"  |  onset={epoch_onset_s:.3f} s   dur={duration_s:.3f} s"
    )
    ax.legend(
        fontsize=7,
        loc="upper right",
        ncol=max(1, len(ch_names) // 4),
        framealpha=0.6,
    )
    return fig


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def build_annotation_report(
    raw: mne.io.BaseRaw,
    frontal_regions: dict[str, list[str]],
    annotations: pd.DataFrame,
    *,
    pad_s: float = PAD_S,
) -> mne.Report:
    """Build the MNE HTML report for all annotated blinks.

    Parameters
    ----------
    raw:
        Preloaded raw object with frontal channels only.
    frontal_regions:
        Mapping of region name → list of channel names (as resolved from YAML).
    annotations:
        DataFrame with columns ``onset``, ``duration``, ``epoch_index``,
        ``epoch_onset``, ``blink_in_epoch`` (output of ``_assign_epochs``).
    pad_s:
        Padding before / after each blink window.

    Returns
    -------
    mne.Report
    """
    all_frontal_chs = [ch for chs in frontal_regions.values() for ch in chs]

    report = mne.Report(title="Tutorial 16 – Human-Annotated Blinks (Frontal)", verbose=False)

    # --- Summary -----------------------------------------------------------
    region_html = "".join(
        f"<li><b>{region}:</b> {', '.join(chs) if chs else '(none found)'}</li>"
        for region, chs in frontal_regions.items()
    )
    summary_html = (
        f"<h2>Human-Annotation Blink Visualisation</h2>"
        f"<ul>"
        f"<li><b>FIF:</b> {FIF_PATH}</li>"
        f"<li><b>Annotation CSV:</b> {ANNOTATION_PATH}</li>"
        f"<li><b>Epoch duration:</b> {EPOCH_DURATION_S:.0f} s</li>"
        f"<li><b>Pad:</b> ±{pad_s:.2f} s</li>"
        f"<li><b>Total annotated blinks:</b> {len(annotations)}</li>"
        f"</ul>"
        f"<h3>Frontal channels plotted</h3><ul>{region_html}</ul>"
    )
    report.add_html(summary_html, title="Summary", section="Overview")

    # --- Annotation table --------------------------------------------------
    display_cols = [c for c in ["onset", "duration", "description", "epoch_index", "epoch_onset", "blink_in_epoch"] if c in annotations.columns]
    table_html = annotations[display_cols].to_html(index=False, float_format="{:.4f}".format)
    report.add_html(
        f"<h3>All annotated blinks</h3>{table_html}",
        title="Annotation Table",
        section="Overview",
    )

    # --- Per-epoch blink figures -------------------------------------------
    total = len(annotations)
    for row_num, (_, row) in enumerate(annotations.iterrows(), start=1):
        epoch_index = int(row["epoch_index"])
        blink_in_epoch = int(row["blink_in_epoch"])
        onset_abs = float(row["onset"])
        duration_s = float(row["duration"])
        epoch_onset = float(row["epoch_onset"])

        print(
            f"    [{row_num}/{total}] epoch={epoch_index}  "
            f"blink={blink_in_epoch}  onset={onset_abs:.3f}s"
        )

        fig = _blink_figure(
            raw,
            all_frontal_chs,
            onset_abs_s=onset_abs,
            duration_s=duration_s,
            epoch_onset_s=epoch_onset,
            epoch_index=epoch_index,
            blink_in_epoch=blink_in_epoch,
            pad_s=pad_s,
        )

        section_title = f"Epoch {epoch_index:03d}"
        fig_title = f"Blink {blink_in_epoch} Epoch {epoch_index}"

        report.add_figure(
            fig,
            title=fig_title,
            section=section_title,
            image_format="png",
        )
        plt.close(fig)

    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"script={Path(__file__).name}")
    print(f"fif_path={FIF_PATH}")
    print(f"annotation_path={ANNOTATION_PATH}")
    print(f"epoch_duration_s={EPOCH_DURATION_S}")
    print(f"pad_s={PAD_S}")
    print(f"report_path={REPORT_PATH}")

    # Step 1 – frontal channel definitions from YAML
    print("\n[1] Loading frontal channel definitions …")
    frontal_regions = _load_frontal_channels(BRAIN_REGION_YAML)
    for region, chs in frontal_regions.items():
        print(f"    {region}: {chs}")

    # Step 2 – raw FIF (frontal channels only)
    print("\n[2] Loading raw FIF …")
    raw, resolved_regions = _load_raw_frontal(FIF_PATH, frontal_regions)
    print(f"    duration : {raw.times[-1]:.2f} s   sfreq={raw.info['sfreq']} Hz")
    for region, chs in resolved_regions.items():
        print(f"    {region} (available): {chs}")

    raw.plot(block=True)
    # Step 3 – annotation CSV → epoch-relative table
    print("\n[3] Loading annotations …")
    raw_annots = _load_annotations(ANNOTATION_PATH)
    annotations = _assign_epochs(raw_annots, epoch_duration=EPOCH_DURATION_S)
    print(f"    total blinks: {len(annotations)}")
    print(f"    epochs spanned: {sorted(annotations['epoch_index'].unique())}")

    # Step 4 – build report
    print(f"\n[4] Building MNE report …")
    report = build_annotation_report(
        raw,
        resolved_regions,
        annotations,
        pad_s=PAD_S,
    )

    report.save(str(REPORT_PATH), overwrite=True, open_browser=False)
    print(f"\nReport saved → {REPORT_PATH}")


if __name__ == "__main__":
    main()
