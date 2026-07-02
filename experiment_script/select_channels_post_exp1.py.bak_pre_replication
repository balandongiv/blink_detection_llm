"""Post-Exp1 channel selection script.

Reads both Exp1 summary CSVs (Raja + Cao2018) and selects:
  - Top 4 individual channels   (selection starting with "single:")
  - Top 4 regional groups       (selection NOT starting with "single:")

Selection criterion: highest det_f1 for Proposed algorithm
  (center_method="median", rule="any").

Outputs:
  runs/channel_selection/selected_channels.json   — machine-readable
  runs/channel_selection/selected_channels_report.md — human-readable

The naming convention used throughout is:
  proposed_<center>_<selection>_<channel>
  e.g. proposed_median_single_e9
       proposed_median_frontal_fp1
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = REPO_ROOT / "runs"

EXP1_RAJA_SUMMARY = RUNS_DIR / "exp1_channel_raja" / "exp1_channel_selection_raja_summary.csv"
EXP1_CAO_SUMMARY  = RUNS_DIR / "exp1_channel_cao"  / "exp1_channel_selection_cao2018_summary.csv"

OUT_DIR = RUNS_DIR / "channel_selection"

TOP_N_INDIVIDUAL = 4
TOP_N_REGIONAL   = 4

CENTER_METHOD = "median"
RULE          = "any"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _safe_float(val: str) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return float("nan")


def _label(center: str, selection: str, channel: str) -> str:
    """Return proposed_<center>_<selection_slug>_<channel_lower> label."""
    sel_slug = selection.replace("single:", "single_").replace(":", "_").lower()
    ch_lower = channel.lower()
    return f"proposed_{center}_{sel_slug}_{ch_lower}"


def select_top_channels(
    rows: list[dict],
    *,
    n_individual: int = TOP_N_INDIVIDUAL,
    n_regional: int = TOP_N_REGIONAL,
    center_method: str = CENTER_METHOD,
    rule: str = RULE,
) -> dict:
    """Return top individual and regional channel dicts."""
    # Filter to Proposed (no 'condition' column in exp1 summaries — all rows are Proposed)
    filtered = [
        r for r in rows
        if r.get("center_method") == center_method and r.get("rule") == rule
    ]

    individual = sorted(
        [r for r in filtered if r["selection"].startswith("single:")],
        key=lambda r: _safe_float(r["det_f1"]),
        reverse=True,
    )
    regional = sorted(
        [r for r in filtered if not r["selection"].startswith("single:")],
        key=lambda r: _safe_float(r["det_f1"]),
        reverse=True,
    )

    def _to_record(r: dict) -> dict:
        return {
            "label": _label(center_method, r["selection"], r["channel_in_group"]),
            "selection": r["selection"],
            "channel": r["channel_in_group"],
            "center_method": center_method,
            "det_precision": round(_safe_float(r["det_precision"]), 4),
            "det_recall":    round(_safe_float(r["det_recall"]),    4),
            "det_f1":        round(_safe_float(r["det_f1"]),        4),
            "n_sessions":    int(r["n_sessions"]),
        }

    # Deduplicate: keep only the highest-F1 row per selection GROUP name,
    # so we get diverse regions (not 4 rows from the same "all" group).
    seen_sel: set[str] = set()
    top_regional: list[dict] = []
    for r in regional:
        sel = r["selection"]
        if sel not in seen_sel:
            seen_sel.add(sel)
            top_regional.append(_to_record(r))
        if len(top_regional) >= n_regional:
            break

    top_individual = [_to_record(r) for r in individual[:n_individual]]

    return {
        "top_individual": top_individual,
        "top_regional":   top_regional,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not EXP1_RAJA_SUMMARY.exists():
        print(f"ERROR: Exp1 Raja summary not found: {EXP1_RAJA_SUMMARY}")
        print("Run experiment_script/run_exp1_raja.py first.")
        return
    if not EXP1_CAO_SUMMARY.exists():
        print(f"ERROR: Exp1 Cao2018 summary not found: {EXP1_CAO_SUMMARY}")
        print("Run experiment_script/run_exp1_cao2018.py first.")
        return

    rows_raja = _load_csv(EXP1_RAJA_SUMMARY)
    rows_cao  = _load_csv(EXP1_CAO_SUMMARY)

    raja_sel = select_top_channels(rows_raja)
    cao_sel  = select_top_channels(rows_cao)

    result = {
        "raja":    raja_sel,
        "cao2018": cao_sel,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- JSON output ---
    json_path = OUT_DIR / "selected_channels.json"
    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    print(f"Written: {json_path}")

    # --- Markdown report ---
    md_lines = [
        "# Post-Exp1 Channel Selection Report\n",
        "Criterion: highest `det_f1` using `proposed_median` (center=median, rule=any).\n",
        "Naming convention: `proposed_<center>_<selection>_<channel>`\n",
        "",
    ]

    for dataset, sel in [("Raja (EGI-128)", raja_sel), ("Cao2018 (10-20)", cao_sel)]:
        md_lines.append(f"## {dataset}\n")

        md_lines.append("### Top Individual Channels\n")
        md_lines.append("| Rank | Label | Channel | P | R | F1 | N sessions |")
        md_lines.append("|------|-------|---------|---|---|----|-----------|")
        for i, rec in enumerate(sel["top_individual"], 1):
            md_lines.append(
                f"| {i} | `{rec['label']}` | {rec['channel']} "
                f"| {rec['det_precision']:.4f} | {rec['det_recall']:.4f} "
                f"| **{rec['det_f1']:.4f}** | {rec['n_sessions']} |"
            )

        md_lines.append("")
        md_lines.append("### Top Regional Groups (best channel within group)\n")
        md_lines.append("| Rank | Label | Selection | Channel | P | R | F1 | N sessions |")
        md_lines.append("|------|-------|-----------|---------|---|---|----|-----------|")
        for i, rec in enumerate(sel["top_regional"], 1):
            md_lines.append(
                f"| {i} | `{rec['label']}` | {rec['selection']} | {rec['channel']} "
                f"| {rec['det_precision']:.4f} | {rec['det_recall']:.4f} "
                f"| **{rec['det_f1']:.4f}** | {rec['n_sessions']} |"
            )
        md_lines.append("")

    md_path = OUT_DIR / "selected_channels_report.md"
    with md_path.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(md_lines) + "\n")
    print(f"Written: {md_path}")

    # --- Console summary ---
    print()
    for dataset, sel in [("RAJA", raja_sel), ("CAO2018", cao_sel)]:
        print(f"=== {dataset} ===")
        print(f"  Top individual channels (proposed_median):")
        for rec in sel["top_individual"]:
            print(f"    {rec['label']:<45}  F1={rec['det_f1']:.4f}")
        print(f"  Top regional groups (proposed_median, best channel per group):")
        for rec in sel["top_regional"]:
            print(f"    {rec['label']:<45}  F1={rec['det_f1']:.4f}")
        print()


if __name__ == "__main__":
    main()
