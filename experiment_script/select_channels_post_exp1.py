"""Post-Exp1 channel selection — the automatic bridge between Experiment 1 and
the downstream experiments (exp2..exp8).

Reads both Exp1 *summary* CSVs (Raja + Cao2018) and selects, per dataset:
  - Top 4 individual channels   (selection starting with "single:")
  - Top 4 regional groups       (selection NOT "single:" and NOT "all")

Selection criterion: highest det_f1 for the Proposed algorithm
  (center_method="median", rule="any"). The full-montage "all" selection is a
reference, not a region, so it is excluded from the regional ranking.

Usage (run from REPO ROOT, inside conda env double_threshold_algo):
    python experiment_script/select_channels_post_exp1.py                 # reads runs_second_iteration/
    python experiment_script/select_channels_post_exp1.py runs            # reads the runs/ baseline

Outputs (under <runs>/channel_selection/):
  selected_channels.json   — machine-readable detail (P/R/F1 per pick)
  selected_channels.yaml   — the groups_to_run lists consumed by run_exp2..exp8
  selected_channels_report.md — human-readable table

The naming convention used throughout is:
  proposed_<center>_<selection>_<channel>
  e.g. proposed_median_single_e9 ; proposed_median_frontal_left_22
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

TOP_N_INDIVIDUAL = 4
TOP_N_REGIONAL = 4
CENTER_METHOD = "median"
RULE = "any"
EXCLUDE_GROUPS = {"all"}  # the full montage is a reference, not a region group


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
    """Return top individual and regional channel dicts (highest det_f1)."""
    filtered = [
        r for r in rows
        if r.get("center_method") == center_method and r.get("rule") == rule
    ]

    individual = sorted(
        [r for r in filtered if r["selection"].startswith("single:")],
        key=lambda r: _safe_float(r["det_f1"]), reverse=True,
    )
    regional = sorted(
        [r for r in filtered
         if not r["selection"].startswith("single:") and r["selection"] not in EXCLUDE_GROUPS],
        key=lambda r: _safe_float(r["det_f1"]), reverse=True,
    )

    def _to_record(r: dict) -> dict:
        return {
            "label": _label(center_method, r["selection"], r["channel_in_group"]),
            "selection": r["selection"],
            "channel": r["channel_in_group"],
            "center_method": center_method,
            "det_precision": round(_safe_float(r["det_precision"]), 4),
            "det_recall": round(_safe_float(r["det_recall"]), 4),
            "det_f1": round(_safe_float(r["det_f1"]), 4),
            "n_sessions": int(r["n_sessions"]),
        }

    # Keep only the highest-F1 row per regional selection name (diverse regions).
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
    return {"top_individual": top_individual, "top_regional": top_regional}


def groups_to_run(sel: dict) -> list[str]:
    """The flat list of `selection` names that run_exp2..exp8 should evaluate:
    the top regional groups followed by the top single channels."""
    return [r["selection"] for r in sel["top_regional"]] + \
           [r["selection"] for r in sel["top_individual"]]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    import os
    runs_name = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("BLINK_RUNS_DIR", "runs_second_iteration")
    runs_dir = REPO_ROOT / runs_name
    exp1_raja = runs_dir / "exp1_channel_raja" / "exp1_channel_selection_raja_summary.csv"
    exp1_cao = runs_dir / "exp1_channel_cao" / "exp1_channel_selection_cao2018_summary.csv"
    out_dir = runs_dir / "channel_selection"

    for tag, path, runner in [("Raja", exp1_raja, "run_exp1_raja.py"),
                              ("Cao2018", exp1_cao, "run_exp1_cao2018.py")]:
        if not path.exists():
            print(f"ERROR: Exp1 {tag} summary not found: {path}")
            print(f"Run experiment_script/{runner} first (writing into {runs_name}/).")
            return

    raja_sel = select_top_channels(_load_csv(exp1_raja))
    cao_sel = select_top_channels(_load_csv(exp1_cao))
    result = {"raja": raja_sel, "cao2018": cao_sel}
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- JSON (full detail) ---
    (out_dir / "selected_channels.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Written: {out_dir / 'selected_channels.json'}")

    # --- YAML (the groups_to_run lists the runners consume) ---
    def _yaml_list(items): return "[" + ", ".join(items) + "]"
    yaml_lines = [
        "# Auto-generated by experiment_script/select_channels_post_exp1.py",
        f"# Source: {runs_name}/exp1_channel_*/...summary.csv",
        "# Criterion: highest det_f1 for proposed_median (center=median, rule=any).",
        "# Top-4 region groups + top-4 single channels per dataset; 'all' excluded.",
        "# run_exp2..exp8 should use <dataset>.groups_to_run as their GROUPS_TO_RUN set.",
        f"source_runs: {runs_name}",
        "criterion: proposed_median det_f1 (center=median, rule=any)",
    ]
    for ds_key, sel in [("raja", raja_sel), ("cao2018", cao_sel)]:
        yaml_lines.append(f"{ds_key}:")
        yaml_lines.append(f"  groups_to_run: {_yaml_list(groups_to_run(sel))}")
        yaml_lines.append(f"  top_regional: {_yaml_list([r['selection'] for r in sel['top_regional']])}")
        yaml_lines.append(f"  top_individual: {_yaml_list([r['selection'] for r in sel['top_individual']])}")
    (out_dir / "selected_channels.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")
    print(f"Written: {out_dir / 'selected_channels.yaml'}")

    # --- Markdown report ---
    md = [
        "# Post-Exp1 Channel Selection Report\n",
        f"Source runs: `{runs_name}`  ",
        "Criterion: highest `det_f1` using `proposed_median` (center=median, rule=any).  ",
        "Naming convention: `proposed_<center>_<selection>_<channel>`\n",
    ]
    for dataset, sel in [("Raja (EGI-128)", raja_sel), ("Cao2018 (10-20)", cao_sel)]:
        md.append(f"## {dataset}\n")
        md.append(f"`groups_to_run` = `{groups_to_run(sel)}`\n")
        md.append("### Top Individual Channels\n")
        md.append("| Rank | Label | Channel | P | R | F1 | N |")
        md.append("|------|-------|---------|---|---|----|---|")
        for i, rec in enumerate(sel["top_individual"], 1):
            md.append(f"| {i} | `{rec['label']}` | {rec['channel']} | {rec['det_precision']:.4f} "
                      f"| {rec['det_recall']:.4f} | **{rec['det_f1']:.4f}** | {rec['n_sessions']} |")
        md.append("\n### Top Regional Groups (best channel within group)\n")
        md.append("| Rank | Label | Selection | Channel | P | R | F1 | N |")
        md.append("|------|-------|-----------|---------|---|---|----|---|")
        for i, rec in enumerate(sel["top_regional"], 1):
            md.append(f"| {i} | `{rec['label']}` | {rec['selection']} | {rec['channel']} "
                      f"| {rec['det_precision']:.4f} | {rec['det_recall']:.4f} "
                      f"| **{rec['det_f1']:.4f}** | {rec['n_sessions']} |")
        md.append("")
    (out_dir / "selected_channels_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Written: {out_dir / 'selected_channels_report.md'}")

    # --- Console summary ---
    print()
    for dataset, sel in [("RAJA", raja_sel), ("CAO2018", cao_sel)]:
        print(f"=== {dataset} ===")
        print(f"  groups_to_run = {groups_to_run(sel)}")
        print("  Top individual channels:")
        for rec in sel["top_individual"]:
            print(f"    {rec['label']:<40}  F1={rec['det_f1']:.4f}")
        print("  Top regional groups (best channel per group):")
        for rec in sel["top_regional"]:
            print(f"    {rec['label']:<40}  F1={rec['det_f1']:.4f}")
        print()


if __name__ == "__main__":
    main()
