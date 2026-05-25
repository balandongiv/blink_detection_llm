from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="Collect per-experiment outputs into a single summary.json/csv.")
    ap.add_argument("--logdir", type=Path, required=True, help="Root orchestration log directory.")
    args = ap.parse_args()

    root: Path = args.logdir
    exp1_dir = root / "exp1_epoch_duration"
    exp41_dir = root / "exp41_strategy_comparison"
    exp42_dir = root / "exp42_boundary_tolerance"
    exp45_dir = root / "exp45_morphological_detailed"

    summary: dict = {
        "logdir": str(root),
        "artifacts": {},
    }

    rows: list[dict] = []

    # EXP1
    exp1_summary_path = exp1_dir / "summary.json"
    if exp1_summary_path.exists():
        exp1 = _read_json(exp1_summary_path)
        summary["exp1_epoch_duration"] = exp1
        summary["best_epoch_duration_s"] = exp1.get("best_epoch_duration_s")
        summary["metric_used_for_epoch_selection"] = exp1.get("metric_primary")
        summary["artifacts"]["exp1_summary_json"] = str(exp1_summary_path)
        summary["artifacts"]["exp1_results_csv"] = str(exp1_dir / "exp1_epoch_duration_results.csv")
        summary["artifacts"]["exp1_summary_csv"] = str(exp1_dir / "exp1_epoch_duration_summary.csv")

        rows.append({
            "experiment": "exp1_epoch_duration",
            "key": "best_epoch_duration_s",
            "value": str(exp1.get("best_epoch_duration_s")),
        })
        best_row = exp1.get("best_row") or {}
        for k in ("macro_f1", "macro_recall", "macro_precision", "n_sessions"):
            if k in best_row:
                rows.append({"experiment": "exp1_epoch_duration", "key": f"best_{k}", "value": str(best_row[k])})
    else:
        summary["exp1_epoch_duration"] = {"status": "missing", "expected": str(exp1_summary_path)}

    # EXP41
    exp41_summary_csv = exp41_dir / "exp41_strategy_comparison_summary.csv"
    if exp41_summary_csv.exists():
        exp41_rows = _read_csv(exp41_summary_csv)
        exp41_summary_json = exp41_dir / "summary.json"
        exp41_meta = _read_json(exp41_summary_json) if exp41_summary_json.exists() else {}
        summary["exp41_strategy_comparison"] = {
            "epoch_duration_s": exp41_meta.get("epoch_duration_s"),
            "summary_rows": exp41_rows,
        }
        summary["artifacts"]["exp41_results_csv"] = str(exp41_dir / "exp41_strategy_comparison_results.csv")
        summary["artifacts"]["exp41_summary_csv"] = str(exp41_summary_csv)
        summary["artifacts"]["exp41_summary_json"] = str(exp41_summary_json)

        # Extract Proposed-Med macro-F1 on dataset=all for convenience.
        for r in exp41_rows:
            if r.get("dataset") == "all" and r.get("condition") == "Proposed-Med":
                rows.append({"experiment": "exp41_strategy_comparison", "key": "all_macro_f1_proposed_med", "value": r.get("macro_f1")})
    else:
        summary["exp41_strategy_comparison"] = {"status": "missing", "expected": str(exp41_summary_csv)}

    # EXP42
    exp42_summary_csv = exp42_dir / "exp42_boundary_tolerance_summary.csv"
    if exp42_summary_csv.exists():
        exp42_rows = _read_csv(exp42_summary_csv)
        summary["exp42_boundary_tolerance"] = {"summary_rows": exp42_rows}
        summary["artifacts"]["exp42_results_csv"] = str(exp42_dir / "exp42_boundary_tolerance_results.csv")
        summary["artifacts"]["exp42_summary_csv"] = str(exp42_summary_csv)
        summary["artifacts"]["exp42_summary_json"] = str(exp42_dir / "summary.json")

        # Extract stability range for dataset=all.
        for r in exp42_rows:
            if r.get("dataset") == "all" and "macro_f1_range_all_thresholds" in r:
                rows.append({"experiment": "exp42_boundary_tolerance", "key": "all_macro_f1_range", "value": r["macro_f1_range_all_thresholds"]})
                break
    else:
        summary["exp42_boundary_tolerance"] = {"status": "missing", "expected": str(exp42_summary_csv)}

    # EXP45
    exp45_summary_json = exp45_dir / "summary.json"
    if exp45_summary_json.exists():
        exp45 = _read_json(exp45_summary_json)
        summary["exp45_morphological_detailed"] = exp45
        summary["artifacts"]["exp45_event_counts_csv"] = str(exp45_dir / "exp45_morphological_event_counts.csv")
        summary["artifacts"]["exp45_report_path"] = exp45.get("report_path")
        summary["artifacts"]["exp45_summary_json"] = str(exp45_summary_json)

        rows.append({"experiment": "exp45_morphological_detailed", "key": "report_path", "value": str(exp45.get("report_path"))})
    else:
        summary["exp45_morphological_detailed"] = {"status": "missing", "expected": str(exp45_summary_json)}

    (root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_csv(root / "summary.csv", rows)


if __name__ == "__main__":
    main()
