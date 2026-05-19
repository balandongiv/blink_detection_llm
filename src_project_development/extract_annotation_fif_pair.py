"""
Sweep D:\dataset\drowsy_driving_raja_processed and D:\dataset\drowsy_driving_raja\human_label_annotation
to collect matched (eeg_eog_raw.fif, ear_eog.csv) pairs.

Directory layout assumed:
  <processed_root>/<subject>/<segment>/seg_data_raw/eeg_eog_raw.fif
  <annotation_root>/<subject>/<segment>/ear_eog.csv

Outputs a list of dicts and optionally writes a CSV summary.
"""

import csv
import sys
from pathlib import Path

PROCESSED_ROOT = Path(r"D:\dataset\drowsy_driving_raja_processed")
ANNOTATION_ROOT = Path(r"D:\dataset\drowsy_driving_raja\human_label_annotation")

FIF_SUBPATH = Path("seg_data_raw") / "eeg_eog_raw.fif"
CSV_FILENAME = "ear_eog.csv"


def find_pairs() -> list[dict]:
    pairs = []

    for subject_dir in sorted(PROCESSED_ROOT.iterdir()):
        if not subject_dir.is_dir():
            continue
        subject = subject_dir.name  # e.g. S1

        for segment_dir in sorted(subject_dir.iterdir()):
            if not segment_dir.is_dir():
                continue
            segment = segment_dir.name  # e.g. S01_20170519_043933

            fif_path = segment_dir / FIF_SUBPATH
            csv_path = ANNOTATION_ROOT / subject / segment / CSV_FILENAME

            if fif_path.exists() and csv_path.exists():
                pairs.append(
                    {
                        "subject": subject,
                        "segment": segment,
                        "fif": str(fif_path),
                        "csv": str(csv_path),
                    }
                )

    return pairs


def main():
    pairs = find_pairs()

    if not pairs:
        print("No matched pairs found.")
        return

    print(f"Found {len(pairs)} matched pair(s):\n")
    for p in pairs:
        print(f"  [{p['subject']} / {p['segment']}]")
        print(f"    FIF : {p['fif']}")
        print(f"    CSV : {p['csv']}")
        print()

    # Optionally write a summary CSV
    if len(sys.argv) > 1:
        out_path = Path(sys.argv[1])
        with out_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["subject", "segment", "fif", "csv"])
            writer.writeheader()
            writer.writerows(pairs)
        print(f"Summary written to {out_path}")


if __name__ == "__main__":
    main()
