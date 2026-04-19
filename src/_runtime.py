"""Runtime helpers for stable local development behavior."""

from __future__ import annotations

import os
from pathlib import Path


def configure_mne_home(base_dir: str | os.PathLike[str] | None = None) -> str:
    """Point MNE config writes at a workspace-local home directory.

    MNE reads and writes its config under ``<home>/.mne/mne-python.json``.
    On this project, that user-profile location can be locked by other
    processes, which slows imports or raises ``PermissionError`` on Windows.

    This helper redirects MNE to a local workspace directory unless an
    explicit override is already present.
    """
    existing = os.environ.get("_MNE_FAKE_HOME_DIR")
    if existing:
        return existing

    root = Path(base_dir) if base_dir is not None else Path(__file__).resolve().parent.parent
    fake_home = root / ".tmp_mne_home"
    mne_dir = fake_home / ".mne"
    mne_dir.mkdir(parents=True, exist_ok=True)

    config_path = mne_dir / "mne-python.json"
    if not config_path.exists():
        config_path.write_text("{}", encoding="utf-8")

    os.environ["_MNE_FAKE_HOME_DIR"] = str(fake_home)
    return str(fake_home)


__all__ = ["configure_mne_home"]
