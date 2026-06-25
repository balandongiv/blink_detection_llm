"""Run Exp 1 (Raja) — channel-selection ablation — no argparse needed.

Just press the Play button in IntelliJ IDEA.

Configuration is read from experiment_script/setup/exp1_channel_selection_raja.yaml.
Output CSVs go to runs/exp1_channel_raja/.

Resume support
--------------
Set OVERWRITE = False  (the default) to skip sessions whose per-session CSV
already exists.  Set OVERWRITE = True to re-run everything from scratch.

Choosing which channel groups to run
-------------------------------------
Edit GROUPS_TO_RUN below.  The group names map to the conditions in
experiment_script/extende_experiment.md as follows:

  Group name (code)          Markdown label
  ─────────────────────────  ──────────────────────────────
  "all"                      All channels (baseline)
  "frontal"                  FL_FR  — frontal bilateral
  "frontal_left"             FL     — frontal left
  "frontal_right"            FR     — frontal right
  "central"                  CL_CR  — central bilateral
  "parietal"                 PL_PR  — parietal bilateral
  "occipital"                OR_OL  — occipital bilateral
  "posterior"                PL_PR_OR_OL — posterior bilateral
  "single:Fp1"               Single-channel: Fp1
  "single:Fp2"               Single-channel: Fp2
  "single:AF3"               Single-channel: AF3
  "single:AF4"               Single-channel: AF4
  ... (one entry per frontal electrode present in the recording)

  Note: individual left/right splits for central (CL, CR), parietal (PL, PR),
  and occipital (OL, OR), plus the midline (NA) condition, are not yet built by
  build_selection_groups — they require adding those region keys to
  brain_region_raja.yaml first.

Examples
--------
Run ALL conditions (default):
    GROUPS_TO_RUN = None

Run only the "all channels" baseline:
    GROUPS_TO_RUN = {"all"}

Run the full frontal block (FL, FR, FL_FR):
    GROUPS_TO_RUN = {"frontal_left", "frontal_right", "frontal"}

Run every single-frontal-channel condition only:
    GROUPS_TO_RUN = {"single:Fp1", "single:Fp2", "single:AF3", "single:AF4",
                     "single:F3", "single:F4", "single:F7", "single:F8"}

Run only the regional group conditions (no single-channel sweep):
    GROUPS_TO_RUN = {"all", "frontal", "frontal_left", "frontal_right",
                     "central", "parietal", "occipital", "posterior"}
"""

from __future__ import annotations

import csv
import json
import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# *** User-facing settings — edit these ***
# ---------------------------------------------------------------------------

# Output directory (relative to repo root).
OUT_DIR = Path("runs/exp1_channel_raja")

# Set True to re-run sessions that already have a result CSV;
# set False to skip them (safe resume after interruption).
OVERWRITE = False

# Which channel groups to run.
# None              → run every group (all conditions from extende_experiment.md).
# set of strings   → run only those group names (see docstring mapping table above).
#
# Common recipes (uncomment one):
# GROUPS_TO_RUN = None                                          # ALL conditions
# GROUPS_TO_RUN = {"all"}                                       # baseline only
GROUPS_TO_RUN = {"frontal_left"}                             # FL only
# GROUPS_TO_RUN = {"frontal_left", "frontal_right", "frontal"} # full frontal block
# GROUPS_TO_RUN = {"all", "frontal", "frontal_left", "frontal_right",
#                  "central", "parietal", "occipital", "posterior"}  # regional only (no singles)
# GROUPS_TO_RUN = {"single:Fp1", "single:Fp2"}                 # specific single channels
# GROUPS_TO_RUN: set[str] | None = None

# ---------------------------------------------------------------------------
# Repo root on sys.path
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiment_script.channel_ablation_utils import (
    condition_summary_rows,
    print_condition_summary,
    run_one_session,
    write_csv,
    DEFAULT_CENTER_METHODS,
    DEFAULT_RULES,
)
from src.project_paths import EXP_SETUP_DIR, get_cao_paths, get_raja_paths, load_exp_config
from tutorial.tutorial_utils import discover_raja_pairs, setup_tutorial_logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config from yaml
# ---------------------------------------------------------------------------

_CFG = load_exp_config(EXP_SETUP_DIR / "exp1_channel_selection_raja.yaml")
_RAJA = get_raja_paths()
_CAO  = get_cao_paths()

DATASET          = _CFG["dataset"]
RAJA_REGION_YAML = _RAJA["brain_region_yaml"]
CAO_REGION_YAML  = _CAO["brain_region_yaml"]
EPOCH_DURATION_S = float(_CFG["epoch_duration_s"])
STD_THRESHOLD    = float(_CFG["std_threshold"])
FILTER_LOW       = float(_CFG.get("filter_low", 1.0))
FILTER_HIGH      = float(_CFG.get("filter_high", 20.0))
RESAMPLE_RATE    = float(_CFG.get("resample_rate", 100.0))


def _session_csv(out_dir: Path, session_name: str) -> Path:
    safe = session_name.replace("/", "__").replace("\\", "__")
    return out_dir / "sessions" / f"{safe}.csv"


def _write_session_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    setup_tutorial_logging()
    out_dir = REPO_ROOT / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    pairs = discover_raja_pairs(_RAJA["annotation_base"], _RAJA["processed_base"])
    if not pairs:
        print("No Raja sessions found — check paths.yaml.")
        return

    logger.info("Raja sessions discovered: %d", len(pairs))

    session_kwargs = dict(
        raja_region_yaml=RAJA_REGION_YAML,
        cao_region_yaml=CAO_REGION_YAML,
        epoch_duration_s=EPOCH_DURATION_S,
        std_threshold=STD_THRESHOLD,
        center_methods=DEFAULT_CENTER_METHODS,
        rules=DEFAULT_RULES,
        autoreject_random_state=42,
        filter_low=FILTER_LOW,
        filter_high=FILTER_HIGH,
        resample_rate=RESAMPLE_RATE,
        include_single_frontal=True,  # always build all groups; GROUPS_TO_RUN filters below
        use_epoch_health=False,
        groups_filter=GROUPS_TO_RUN,
        verbose=True,
    )

    all_metrics: list[dict] = []
    errors: list[str] = []

    for i, pair in enumerate(pairs, 1):
        name = pair["name"]
        csv_path = _session_csv(out_dir, name)

        if not OVERWRITE and csv_path.is_file():
            logger.info("[%d/%d] SKIP (already done): %s", i, len(pairs), name)
            with csv_path.open(encoding="utf-8") as fh:
                all_metrics.extend(list(csv.DictReader(fh)))
            continue

        logger.info("[%d/%d] running: %s", i, len(pairs), name)
        try:
            rows = run_one_session(pair, **session_kwargs)
            _write_session_csv(csv_path, rows)
            all_metrics.extend(rows)
            logger.info("  -> %d condition rows written", len(rows))
        except Exception as exc:  # noqa: BLE001
            msg = f"ERROR  {name}: {exc}"
            logger.error(msg)
            errors.append(msg)

    if not all_metrics:
        print("No metrics collected.")
        for e in errors:
            print(e)
        return

    # Re-cast numeric fields from str when rows were read back from existing CSVs.
    numeric_keys = {
        "stageA_tp", "stageA_fp", "stageA_fn", "stageA_tn",
        "stageA_precision", "stageA_recall", "stageA_f1", "stageA_fpr",
        "pct_flagged", "n_flagged", "n_blink_epochs", "n_channels_used",
        "n_valid", "det_tp", "det_fp", "det_fn",
        "det_precision", "det_recall", "det_f1",
    }
    coerced: list[dict] = []
    for r in all_metrics:
        row = dict(r)
        for k in numeric_keys:
            if k in row and isinstance(row[k], str):
                try:
                    row[k] = float(row[k])
                except ValueError:
                    pass
        coerced.append(row)

    write_csv(out_dir / f"exp1_channel_selection_{DATASET}_results.csv", coerced)
    summary_rows = condition_summary_rows(coerced, DATASET)
    write_csv(out_dir / f"exp1_channel_selection_{DATASET}_summary.csv", summary_rows)
    (out_dir / "summary.json").write_text(json.dumps({
        "experiment": f"exp1_channel_selection_{DATASET}",
        "epoch_duration_s": EPOCH_DURATION_S,
        "resample_rate": RESAMPLE_RATE,
        "groups_run": sorted(GROUPS_TO_RUN) if GROUPS_TO_RUN is not None else "all",
        "metric_primary": "det_f1 + stageA_f1 per (selection, rule, centre)",
        "n_sessions": len(pairs),
        "n_rows": len(coerced),
        "n_errors": len(errors),
    }, indent=2), encoding="utf-8")

    print_condition_summary(coerced, DATASET)

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)

    print(f"\nResults written to: {out_dir}")


if __name__ == "__main__":
    main()
