"""Load ``sample_data/1.edf`` and plot its channels.

This script loads the full EDF recording, crops it to the first 60 seconds
for efficient visualization, and opens an MNE plot window.
"""

from __future__ import annotations

import os
from pathlib import Path

import mne

SAMPLE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SAMPLE_DIR.parent
MNE_HOME = PROJECT_ROOT / ".mne_home"
MNE_HOME.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("_MNE_FAKE_HOME_DIR", str(MNE_HOME))

EDF_PATH = SAMPLE_DIR / "1.edf"
CROP_SECONDS = 60.0


def main() -> None:
    """Load and plot the EDF file."""

    if not EDF_PATH.exists():
        raise FileNotFoundError(f"EDF file not found: {EDF_PATH}")

    print(f"Loading {EDF_PATH}...")
    raw = mne.io.read_raw_edf(str(EDF_PATH), preload=True, verbose=False)

    # Crop for visualization
    crop_stop = min(CROP_SECONDS, float(raw.times[-1]))
    print(f"Cropping to first {crop_stop} seconds...")
    raw.crop(tmin=0.0, tmax=crop_stop, include_tmax=False)

    print("Plotting channels...")
    # By default raw.plot() is interactive.
    # Set block=True to keep the window open.
    # You can pick specific channels if needed:
    # raw.pick(["EEG Fp1 - Pz", "EEG Fp2 - Pz"])

    fig = raw.plot(
        block=True,
        title=f"1.edf - First {crop_stop}s",
        show=True,
    )

    # To save the plot to a file, you can use matplotlib.pyplot or fig.savefig()
    # Note: fig.savefig() might require a call to plt.show() or it might work directly
    # depending on the backend.
    plot_image = SAMPLE_DIR / "1_edf_plot.png"
    fig.savefig(str(plot_image))
    print(f"Plot saved to: {plot_image}")


if __name__ == "__main__":
    main()
