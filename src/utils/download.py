import urllib.request
from pathlib import Path
import mne


# ---------------------------------------------------------------------
# 2. Download helper
# ---------------------------------------------------------------------
def download_once(url: str, dest_path: Path):
    if dest_path.exists():
        print(f"File already exists: {dest_path}")
        return
    print(f"Downloading {url} ...")
    urllib.request.urlretrieve(url, dest_path)
    print("Download complete.")


# ---------------------------------------------------------------------
# 3. Simple save helpers
# ---------------------------------------------------------------------
def save_edf_once(raw: mne.io.Raw, edf_path: Path):
    if edf_path.exists():
        print(f"EDF already exists: {edf_path}")
        return
    print(f"Saving EDF file: {edf_path}")
    from mne.export import export_raw

    export_raw(edf_path.as_posix(), raw, fmt="edf")
    print("EDF saved.")


def save_fif_once(raw: mne.io.Raw, fif_path: Path):
    if fif_path.exists():
        print(f"FIF already exists: {fif_path}")
        return
    print(f"Saving FIF cache: {fif_path}")
    raw.save(fif_path.as_posix(), overwrite=True)
    print("FIF saved.")
