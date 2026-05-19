"""Load ``sample_data/dev_epo.fif`` and plot selected channels."""

from __future__ import annotations

import os
from pathlib import Path

SAMPLE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SAMPLE_DIR.parent
MNE_HOME = PROJECT_ROOT / ".mne_home"
MNE_HOME.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("_MNE_FAKE_HOME_DIR", str(MNE_HOME))

import mne


EPOCHS_PATH = SAMPLE_DIR / "dev_epo.fif"
PLOT_CHANNELS = [
    "EEG P3 - Pz",
    "EEG C3 - Pz",
]
N_EPOCHS_TO_PLOT = 5
# Full channel list for quick comment/decomment later.
# ch = [
#     "EEG P3 - Pz",
#     "EEG C3 - Pz",
#     "EEG F3 - Pz",
#     "EEG Fz - Pz",
#     "EEG F4 - Pz",
#     "EEG C4 - Pz",
#     "EEG P4 - Pz",
#     "EEG Cz - Pz",
#     "EEG CM - Pz",
#     "EEG A1 - Pz",
#     "EEG Fp1 - Pz",
#     "EEG Fp2 - Pz",
#     "EEG T3 - Pz",
#     "EEG T5 - Pz",
#     "EEG O1 - Pz",
#     "EEG O2 - Pz",
#     "EEG X3 - Pz",
#     "EEG X2 - Pz",
#     "EEG F7 - Pz",
#     "EEG F8 - Pz",
#     "EEG X1 - Pz",
#     "EEG A2 - Pz",
#     "EEG T6 - Pz",
#     "EEG T4 - Pz",
# ]


def main() -> None:
    """Load the epochs file and plot selected channels."""

    if not EPOCHS_PATH.exists():
        raise FileNotFoundError(f"Epochs file not found: {EPOCHS_PATH}")

    epochs = mne.read_epochs(str(EPOCHS_PATH), preload=True, verbose=False)
    epochs = epochs[:N_EPOCHS_TO_PLOT].copy()
    epochs.pick(PLOT_CHANNELS)
    epochs.plot(
        block=True,
        title=f"dev_epo.fif first {N_EPOCHS_TO_PLOT} epochs",
    )


if __name__ == "__main__":
    main()
