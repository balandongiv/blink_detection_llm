from pathlib import Path

from pyblinker._runtime import configure_mne_home

import mne


EDF_PATH = Path(r"D:\dataset\x_murat_2018\9636463\9636463.edf")


def main() -> None:
    configure_mne_home()

    if not EDF_PATH.exists():
        raise FileNotFoundError(f"EDF file not found: {EDF_PATH}")

    raw = mne.io.read_raw_edf(EDF_PATH, preload=False, verbose="ERROR")

    print(f"Loaded EDF: {EDF_PATH}")
    print(f"Duration      : {raw.times[-1]:.2f} s")
    print(f"Sampling rate : {raw.info['sfreq']} Hz")
    print(f"Channel count : {len(raw.ch_names)}")
    print(f"Channels      : {raw.ch_names}")

    raw.plot(block=True)


if __name__ == "__main__":
    main()
