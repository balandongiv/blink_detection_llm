from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tutorial.strategy_c_autoreject_first_5_epochs_common import (
    AUTOREJECT_RANDOM_SEARCH,
    THRESHOLD_SCOPE_GLOBAL,
    run_single_method_debug,
)


def main() -> None:
    run_single_method_debug(
        method=AUTOREJECT_RANDOM_SEARCH,
        script_name=Path(__file__).name,
        stage1_threshold_scope=THRESHOLD_SCOPE_GLOBAL,
    )


if __name__ == "__main__":
    main()
