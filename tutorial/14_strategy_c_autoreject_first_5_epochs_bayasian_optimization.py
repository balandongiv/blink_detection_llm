"""Bayesian-optimization tutorial entrypoint for multi-lane Strategy C autoreject detection."""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tutorial.strategy_c_autoreject_first_5_epochs_common import (
    AUTOREJECT_BAYESIAN_OPTIMIZATION,
    print_method_alias_note,
    run_single_method_debug,
)


def main() -> None:
    print_method_alias_note()
    run_single_method_debug(
        method=AUTOREJECT_BAYESIAN_OPTIMIZATION,
        script_name=Path(__file__).name,
    )


if __name__ == "__main__":
    main()
