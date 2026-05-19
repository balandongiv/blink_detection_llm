"""Repository-local Python startup customizations for development.

This ensures MNE uses a workspace-local config directory instead of the
user-profile ``.mne`` directory, which can be locked by other processes on
Windows and cause slow imports or permission failures.
"""

from __future__ import annotations

import os
from pathlib import Path


def _configure_workspace_mne_home() -> None:
    if os.environ.get("_MNE_FAKE_HOME_DIR"):
        return

    repo_root = Path(__file__).resolve().parent
    fake_home = repo_root / ".tmp_mne_home"
    mne_dir = fake_home / ".mne"
    mne_dir.mkdir(parents=True, exist_ok=True)

    config_path = mne_dir / "mne-python.json"
    if not config_path.exists():
        config_path.write_text("{}", encoding="utf-8")

    os.environ["_MNE_FAKE_HOME_DIR"] = str(fake_home)


_configure_workspace_mne_home()
