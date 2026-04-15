"""Build an annotated seed recording and a single 30-second epochs file.

This script:
1. Loads ``sample_data/1.edf`` and ``sample_data/seed_exp01_pyblinker_results_1.pkl``.
2. Converts pickle blink spans into ``mne.Annotations`` and attaches them to the EDF.
3. Crops the annotated recording to the first 3000 seconds.
4. Saves the cropped recording as ``sample_data/seed_data.raw.fif``.
5. Reloads the saved raw file, slices it into fixed 30-second MNE epochs, and saves them
   into ``sample_data/dev_epo.fif``.
6. Exports a CSV describing the annotations mapped into each epoch.

MNE requires raw files to use FIF-style suffixes, so the saved raw output is
``seed_data.raw.fif`` instead of ``seed_data.raw``.
"""

from __future__ import annotations

import os
import pickle
from pathlib import Path

import pandas as pd

SAMPLE_DIR = Path(r"D:\dataset\epoch_blink_development\normal_blink")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MNE_HOME = PROJECT_ROOT / ".mne_home"
MNE_HOME.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("_MNE_FAKE_HOME_DIR", str(MNE_HOME))

import mne


EDF_PATH = SAMPLE_DIR / "1.edf"
PICKLE_PATH = SAMPLE_DIR / "seed_exp01_pyblinker_results_1.pkl"
OUTPUT_RAW_PATH = SAMPLE_DIR / "seed_data.raw.fif"
OUTPUT_EPOCHS_PATH = SAMPLE_DIR / "dev_epo.fif"
EPOCH_ANNOTATION_CSV = SAMPLE_DIR / "dev_epo_annotations.csv"
EPOCH_LEN_SECONDS = 60.0
CROP_SECONDS = 3000.0
ANNOTATION_LABEL = "blink"


def build_annotations(events: pd.DataFrame, sfreq: float) -> mne.Annotations:
    """Convert blink sample spans into MNE annotations."""

    spans = events[["start_blink", "end_blink"]].dropna().copy()
    spans["start_blink"] = spans["start_blink"].astype(float)
    spans["end_blink"] = spans["end_blink"].astype(float)
    spans = spans[spans["end_blink"] >= spans["start_blink"]]

    onset = ((spans["start_blink"] - 1.0) / sfreq).tolist()
    duration = ((spans["end_blink"] - spans["start_blink"] + 1.0) / sfreq).tolist()
    description = [ANNOTATION_LABEL] * len(spans)

    return mne.Annotations(onset=onset, duration=duration, description=description)


def build_fixed_length_epochs(raw: mne.io.BaseRaw) -> mne.Epochs:
    """Slice a raw recording into fixed-length MNE epochs and preserve blink metadata."""

    sfreq = float(raw.info["sfreq"])
    events = mne.make_fixed_length_events(raw, duration=EPOCH_LEN_SECONDS)
    epochs = mne.Epochs(
        raw,
        events,
        tmin=0.0,
        tmax=EPOCH_LEN_SECONDS - 1.0 / sfreq,
        baseline=None,
        preload=True,
        verbose=False,
    )

    metadata_rows: list[dict[str, object]] = []
    ann = raw.annotations
    blink_mask = ann.description == ANNOTATION_LABEL
    blink_onsets = ann.onset[blink_mask]
    blink_durations = ann.duration[blink_mask]
    blink_descriptions = ann.description[blink_mask]
    epoch_starts = events[:, 0] / sfreq

    for epoch_id, epoch_start_sec in enumerate(epoch_starts):
        epoch_stop_sec = epoch_start_sec + EPOCH_LEN_SECONDS
        in_epoch = (blink_onsets >= epoch_start_sec) & (blink_onsets < epoch_stop_sec)
        rel_onsets = (blink_onsets[in_epoch] - epoch_start_sec).tolist()
        rel_durations = blink_durations[in_epoch].tolist()
        descriptions = blink_descriptions[in_epoch].tolist()
        raw_onsets = blink_onsets[in_epoch].tolist()
        raw_ends = (blink_onsets[in_epoch] + blink_durations[in_epoch]).tolist()

        metadata_rows.append(
            {
                "epoch_id": epoch_id,
                "epoch_start_sec": float(epoch_start_sec),
                "epoch_stop_sec": float(epoch_stop_sec),
                "n_blinks": len(rel_onsets),
                "blink_onset": rel_onsets,
                "blink_duration": rel_durations,
                "blink_description": descriptions,
                "raw_blink_onset": raw_onsets,
                "raw_blink_end": raw_ends,
            }
        )

    epochs.metadata = pd.DataFrame(metadata_rows)
    return epochs


def epoch_annotation_table(epochs: mne.Epochs) -> pd.DataFrame:
    """Create one CSV row per annotation described in ``epochs.metadata``."""

    if epochs.metadata is None:
        raise ValueError("epochs.metadata is required to export annotation CSV")

    rows: list[dict[str, object]] = []
    for row in epochs.metadata.itertuples(index=False):
        if row.n_blinks == 0:
            rows.append(
                {
                    "epoch_id": row.epoch_id,
                    "epoch_start_sec": row.epoch_start_sec,
                    "epoch_stop_sec": row.epoch_stop_sec,
                    "annotation_index": None,
                    "description": None,
                    "epoch_onset_sec": None,
                    "epoch_duration_sec": None,
                    "raw_onset_sec": None,
                    "raw_end_sec": None,
                }
            )
            continue

        for ann_idx, (description, epoch_onset, epoch_duration, raw_onset, raw_end) in enumerate(
            zip(
                row.blink_description,
                row.blink_onset,
                row.blink_duration,
                row.raw_blink_onset,
                row.raw_blink_end,
            )
        ):
            rows.append(
                {
                    "epoch_id": row.epoch_id,
                    "epoch_start_sec": row.epoch_start_sec,
                    "epoch_stop_sec": row.epoch_stop_sec,
                    "annotation_index": ann_idx,
                    "description": description,
                    "epoch_onset_sec": epoch_onset,
                    "epoch_duration_sec": epoch_duration,
                    "raw_onset_sec": raw_onset,
                    "raw_end_sec": raw_end,
                }
            )

    return pd.DataFrame(rows)


def main() -> None:
    """Create cropped annotated raw data, a single epochs file, and annotation CSV."""

    if not EDF_PATH.exists():
        raise FileNotFoundError(f"EDF file not found: {EDF_PATH}")
    if not PICKLE_PATH.exists():
        raise FileNotFoundError(f"Pickle file not found: {PICKLE_PATH}")

    with PICKLE_PATH.open("rb") as f:
        payload = pickle.load(f)

    events = payload["events"]
    if not isinstance(events, pd.DataFrame):
        raise TypeError("Expected payload['events'] to be a pandas DataFrame")

    raw = mne.io.read_raw_edf(str(EDF_PATH), preload=True, verbose=False)
    sfreq = float(raw.info["sfreq"])
    annotations = build_annotations(events, sfreq)
    raw.set_annotations(annotations)

    crop_stop = min(CROP_SECONDS, float(raw.times[-1]))
    raw.crop(tmin=0.0, tmax=crop_stop, include_tmax=False)
    raw.save(str(OUTPUT_RAW_PATH), overwrite=True, verbose=False)

    cropped_raw = mne.io.read_raw_fif(str(OUTPUT_RAW_PATH), preload=True, verbose=False)
    epochs = build_fixed_length_epochs(cropped_raw)
    epochs.save(str(OUTPUT_EPOCHS_PATH), overwrite=True, verbose=False)

    annotation_df = epoch_annotation_table(epochs)
    annotation_df.to_csv(EPOCH_ANNOTATION_CSV, index=False)

    print(f"Saved cropped annotated raw to: {OUTPUT_RAW_PATH}")
    print(f"Saved {len(epochs)} epochs to: {OUTPUT_EPOCHS_PATH}")
    print(f"Saved epoch annotation CSV to: {EPOCH_ANNOTATION_CSV}")


if __name__ == "__main__":
    main()
