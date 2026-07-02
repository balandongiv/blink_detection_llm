"""Manuscript reproducibility framework.

Single entry point that documents and reproduces EVERY table, figure and frozen-number
file in the manuscript directly from the validated results in `runs_second_iteration/`.

For each artifact the MANIFEST below records:
  - the manuscript LaTeX label (\\label{...}) and the output file(s),
  - the script that generates it,
  - the exact source CSV(s) / data files it is computed from,
  - the aggregation rule used, and a one-line description.

USAGE (run inside conda env `double_threshold_algo`)
  python experiment_script/reproduce_manuscript.py list
        -> print the provenance table (artifact -> script -> source -> aggregation)
  python experiment_script/reproduce_manuscript.py provenance tab:exp1_channel_ablation
        -> full provenance for one artifact (accepts a label, an output filename, or a script)
  python experiment_script/reproduce_manuscript.py build
        -> regenerate ALL artifacts (runs each generating script once)
  python experiment_script/reproduce_manuscript.py build --only regen_paper_tables.py
        -> regenerate only the artifacts produced by the named script(s) (comma separated)
  python experiment_script/reproduce_manuscript.py build --label tab:count_agreement
        -> regenerate only the script(s) that produce the given label(s)
  python experiment_script/reproduce_manuscript.py build --dry-run
        -> show what would run, without running it

CUSTOMISATION
  The helper functions `load()`, `best_per_session()` and `per_channel()` at the bottom
  expose the same extraction primitives the generating scripts use, so you can pull any
  slice of the results yourself. Run
        python experiment_script/reproduce_manuscript.py custom-example
  for a worked example (per-channel Experiment 1 values, the
  proposed_median_<region>_<channel> units). Change CENTER / AGG / DATASETS at the top of
  that function, or import these helpers into your own script:
        from reproduce_manuscript import load, best_per_session, per_channel
"""
from __future__ import annotations
import os
import sys
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
# The whole pipeline keys off BLINK_RUNS_DIR (default: runs_second_iteration).
RUNS_NAME = os.environ.get("BLINK_RUNS_DIR", "runs_second_iteration")
NEW = REPO / RUNS_NAME
SCRIPTS = REPO / "experiment_script"


# ---------------------------------------------------------------------------
# MANIFEST: every manuscript artifact -> generating script + data provenance
# ---------------------------------------------------------------------------
@dataclass
class Artifact:
    label: str                 # LaTeX \label, or a logical id for non-floats
    kind: str                  # "table" | "figure" | "numbers"
    outputs: list[str]         # files written, relative to writing/ (or repo for scripts)
    script: str                # generating script in experiment_script/
    sources: list[str]         # source data files (relative to repo)
    aggregation: str           # how values are aggregated
    desc: str                  # one-line description


_E = RUNS_NAME
def _exp(*names):  # convenience: list source CSVs for given experiments x datasets
    out = []
    fpat = {"exp1": "exp1_channel_{f}/exp1_channel_selection_{n}_results.csv",
            "exp2": "exp2_{f}/exp2_strategy_comparison_{n}_results.csv",
            "exp3": "exp3_{f}/exp3_epoch_duration_{n}_results.csv",
            "exp4": "exp4_{f}/exp4_boundary_tolerance_{n}_results.csv",
            "exp5": "exp5_{f}/exp5_nmin_sensitivity_{n}_results.csv",
            "exp7": "exp7_{f}/exp7_epoch_health_{n}_results.csv",
            "exp8": "exp8_{f}/exp8_long_blink_{n}_results.csv"}
    for e in names:
        for f, n in [("raja", "raja"), ("cao", "cao2018")]:
            out.append(f"{_E}/" + fpat[e].format(f=f, n=n))
    return out


MANIFEST: list[Artifact] = [
    # ----- Experiment 1: channel-by-channel (the refactored, per-channel analysis) -----
    Artifact("tab:exp1_channel_ablation", "table", ["e_result/tab_exp1_channel_ablation.tex"],
             "regen_paper_tables.py", _exp("exp1") + ["brain_region_raja.yaml", "brain_region_cao2018.yaml", "32_ch.csv"],
             "per-channel mean over sessions (selection=='all', center_method=='median'); NO region aggregation",
             "Channel-by-channel detection (proposed_median_<region>_<channel>) for every electrode."),
    Artifact("tab:egi_map", "table", ["e_result/tab_egi_channel_map.tex"],
             "regen_paper_tables.py", ["32_ch.csv", "brain_region_raja.yaml"],
             "static mapping (Raja EGI hardware only; Cao2018 is native 10-20)",
             "Raja EGI-128 to 10-20 channel-name mapping used to label the per-channel results."),
    Artifact("fig:region_performance", "figure", ["figures/fig_region_performance.pdf", "figures/fig_region_performance.png"],
             "plot_region_performance.py", _exp("exp1"),
             "per-channel mean over sessions (selection=='all', median)",
             "Single-channel F1 bar chart for every electrode, grouped by scalp region."),
    # ----- Strategy comparison / headline -----
    Artifact("tab:exp1_main", "table", ["e_result/tab_comparison_30s_epoch.tex"],
             "regen_paper_tables.py", _exp("exp2"), "best-channel-per-session, four conditions",
             "Headline four-condition P/R/F1 per dataset and pooled."),
    Artifact("tab:exp2_inversions", "table", ["e_result/tab_exp2_inversions.tex"],
             "regen_paper_tables.py", _exp("exp2"), "best-channel-per-session per selection",
             "Channel groups where a baseline equals/exceeds Proposed-Med."),
    Artifact("tab:cross_dataset_gap", "table", ["e_result/tab_cross_dataset_gap.tex"],
             "regen_paper_tables.py", _exp("exp2"), "best-channel-per-session; gap = Raja - Cao",
             "Cross-dataset generalisation gap per condition."),
    Artifact("tab:error-structure", "table", ["e_result/tab_error_structure.tex"],
             "regen_paper_tables.py", _exp("exp2"), "mean FP/FN per session at best-channel row",
             "FP/FN error-regime decomposition per condition."),
    Artifact("tab:best-session", "table", ["e_result/tab_best_session.tex"],
             "regen_paper_tables.py", _exp("exp2"), "best-channel-per-session (Proposed-Med)",
             "Best/worst session and subject summary."),
    Artifact("tab:channel-robustness", "table", ["e_result/tab_channel_robustness.tex"],
             "regen_paper_tables.py", _exp("exp2"), "argmax-F1 channel agreement across conditions",
             "Best-channel ranking stability across the four methods."),
    Artifact("tab:channel_selection", "table", ["e_result/tab_channel_selection.tex"],
             "regen_paper_tables.py", _exp("exp2"), "argmax-F1 channel frequency pooled over conditions",
             "Best-channel selection frequencies."),
    # ----- Other ablations -----
    Artifact("tab:epoch_duration", "table", ["e_result/tab_effect_different_epoch_size.tex"],
             "regen_paper_tables.py", _exp("exp3"), "best-channel-per-session by duration; Wilcoxon vs 30 s",
             "Epoch-duration stability of Proposed-Med."),
    Artifact("tab:boundary_tolerance", "table", ["e_result/tab_boundary_tolerance.tex"],
             "regen_paper_tables.py", _exp("exp4"), "best-channel-per-session by IoU",
             "Boundary-tolerance (event-overlap) sensitivity."),
    Artifact("tab:blink_type_recall", "table", ["e_result/tab_blink_type_recall.tex"],
             "regen_paper_tables.py", _exp("exp8"), "best-channel-per-session recall by blink category",
             "Normal vs long-blink recall (Proposed-Med)."),
    # ----- Cross-experiment summary -----
    Artifact("tab:exp_summary", "table", ["e_result/tab_exp_summary.tex"],
             "plot_exp_boxplot.py", _exp("exp1", "exp2", "exp3", "exp4", "exp5", "exp7", "exp8"),
             "best-channel-per-session, Proposed-Med primary config per experiment",
             "Proposed-Med F1 across all ablation experiments."),
    Artifact("tab:exp_stats", "table", ["e_result/tab_exp_stats.tex"],
             "plot_exp_boxplot.py", _exp("exp1", "exp2", "exp3", "exp4", "exp5", "exp7", "exp8"),
             "paired Wilcoxon PM vs BLINKER-concat, Bonferroni x14, bootstrap CI",
             "Per-experiment significance of Proposed-Med vs best competitor."),
    Artifact("fig:exp_boxplot", "figure", ["figures/fig_exp_boxplot.pdf", "figures/fig_exp_boxplot.png"],
             "plot_exp_boxplot.py", _exp("exp1", "exp2", "exp3", "exp4", "exp5", "exp7", "exp8"),
             "session-level best-channel F1 distributions",
             "Box plot of Proposed-Med session F1 across experiments."),
    # ----- Round-2 additions -----
    Artifact("fig:pr_scatter", "figure", ["figures/fig_pr_scatter.pdf", "figures/fig_pr_scatter.png"],
             "plot_pr_operating_points.py", _exp("exp2"), "best-channel-per-session P/R points",
             "Precision-recall operating-point scatter for the four conditions."),
    Artifact("fig:count_agreement", "figure", ["figures/fig_count_agreement.pdf", "figures/fig_count_agreement.png"],
             "plot_count_agreement.py", _exp("exp2"), "best-channel-per-session predicted vs true count",
             "Predicted-vs-true blink-count agreement + Bland-Altman."),
    Artifact("tab:count_agreement", "table", ["e_result/tab_count_agreement.tex"],
             "plot_count_agreement.py", _exp("exp2"), "best-channel-per-session; Pearson r, Lin CCC, ratio",
             "Count-agreement statistics per condition."),
    Artifact("tab:literature_comparison", "table", ["c_literature_review/tab_literature_comparison.tex"],
             "build_literature_comparison.py", ["writing/references_from_csv.bib"],
             "qualitative; prior-work metrics 'n/r' (not in repo); only our row carries numbers",
             "Qualitative positioning vs prior threshold detectors."),
    Artifact("tab:failure_analysis", "table", ["e_result/tab_failure_analysis.tex"],
             "analyse_failure_sessions.py", _exp("exp2"), "best-channel-per-session; bottom-5 sessions",
             "Worst-session failure analysis (GT count, FP/FN, health effect)."),
    # ----- Three displayed figures regenerated from the std=3.0 run -----
    Artifact("fig:condition_prf", "figure", ["e_result/figures/fig_condition_prf.pdf"],
             "regen_simple_figs.py", _exp("exp2"), "best-channel-per-session pooled P/R/F1",
             "Grouped P/R/F1 bars for the four conditions."),
    Artifact("fig:f1_by_dataset", "figure", ["e_result/figures/fig_f1_by_dataset.pdf"],
             "regen_simple_figs.py", _exp("exp2"), "best-channel-per-session per dataset",
             "Per-condition F1 on Raja vs Cao2018."),
    Artifact("fig:f1_by_epoch", "figure", ["e_result/figures/fig_f1_by_epoch.pdf"],
             "regen_simple_figs.py", _exp("exp3"), "best-channel-per-session by epoch duration",
             "Proposed-Med F1 across epoch durations."),
    # ----- Frozen numbers -----
    Artifact("numbers:std30", "numbers", ["NUMBERS_std30.md"],
             "compute_paper_numbers.py", _exp("exp1", "exp2", "exp3", "exp4", "exp5", "exp7", "exp8"),
             "best-channel-per-session throughout",
             "All frozen headline numbers cited in the prose."),
    Artifact("numbers:round2", "numbers", ["NUMBERS_round2.md"],
             "compute_round2_addendum.py", _exp("exp2", "exp7"),
             "best-channel-per-session; R3 hemisphere, R4 ICC, R5 health benefit",
             "Round-2 additional numbers (hemisphere, within-subject, health benefit)."),
]

# Figures that are NOT regenerated from runs_second_iteration/ (declared for completeness).
LEGACY = [
    ("fig:pipeline (Fig. 1)", "tikz in d_method/", "hand-drawn TikZ flow chart, not data-driven"),
    ("tab:experiment_code_summary", "e_result/tab_experiment_code_summary.tex", "static, hand-maintained"),
]

# Scripts that must NOT be run for the current std=3.0 manuscript (they point at
# deleted older runs, e.g. runs/exp41_cao_30s, or are superseded). Documented so a
# future agent does not run them by mistake.
DO_NOT_RUN = {
    "paper_result_figures.py":              "points at deleted runs/exp41_* (old run)",
    "paper_channel_selection_frequency.py": "points at deleted runs/exp41_* (old run)",
    "paper_error_structure_session.py":     "points at deleted runs/exp41_* (old run)",
    "paper_epoch_duration_figure.py":       "points at deleted runs/exp40_* (old run)",
    "paper_blink_type_recall.py":           "points at deleted runs/extra_blink_type (old run)",
    "update_exp2_latex.py":                 "superseded by regen_paper_tables.py",
    "compute_paper_numbers_addendum.py":    "exploratory; superseded by compute_round2_addendum.py",
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _print_table():
    print(f"\n{len(MANIFEST)} data-driven manuscript artifacts "
          f"(all from {RUNS_NAME}/ unless noted):\n")
    by_script: dict[str, list[Artifact]] = {}
    for a in MANIFEST:
        by_script.setdefault(a.script, []).append(a)
    for script in sorted(by_script):
        print(f"== {script} ==")
        for a in by_script[script]:
            outs = ", ".join(a.outputs)
            print(f"   [{a.kind:7}] {a.label:28} -> {outs}")
            print(f"             agg: {a.aggregation}")
        print()
    print("Legacy / non-data-driven floats (not regenerated by this tool):")
    for label, out, note in LEGACY:
        print(f"   {label:28} {out:42} {note}")
    print("\nDO NOT RUN these scripts (point at deleted older runs / superseded):")
    for s, why in DO_NOT_RUN.items():
        print(f"   {s:38} {why}")
    print("\nRun 'provenance <label>' for full source CSVs of one artifact, "
          "or 'build' to regenerate.")


def _match(query: str) -> list[Artifact]:
    q = query.strip()
    hits = [a for a in MANIFEST if q == a.label or q in a.outputs or q == a.script]
    if not hits:  # fuzzy
        hits = [a for a in MANIFEST if q.lower() in a.label.lower()
                or any(q.lower() in o.lower() for o in a.outputs) or q.lower() in a.script.lower()]
    return hits


def _provenance(query: str):
    hits = _match(query)
    if not hits:
        print(f"No artifact matches '{query}'. Try 'list'."); return
    for a in hits:
        print(f"\nlabel       : {a.label}")
        print(f"kind        : {a.kind}")
        print(f"output(s)   : {', '.join(a.outputs)}")
        print(f"script      : experiment_script/{a.script}")
        print(f"aggregation : {a.aggregation}")
        print(f"description : {a.desc}")
        print(f"source data :")
        for s in a.sources:
            exists = (REPO / s).exists()
            print(f"   {'OK ' if exists else 'MISSING '} {s}")


def _build(only_scripts=None, only_labels=None, dry=False):
    scripts = []
    for a in MANIFEST:
        if only_labels and a.label not in only_labels:
            continue
        if only_scripts and a.script not in only_scripts:
            continue
        if a.script not in scripts:
            scripts.append(a.script)
    if not scripts:
        print("Nothing matched the filter."); return
    print(f"Will run {len(scripts)} generating script(s): {', '.join(scripts)}\n")
    for s in scripts:
        path = SCRIPTS / s
        if dry:
            print(f"[dry-run] python {path}"); continue
        print(f"\n>>> running {s}")
        r = subprocess.run([sys.executable, str(path)])
        if r.returncode != 0:
            print(f"!!! {s} exited with code {r.returncode}"); sys.exit(r.returncode)
    if not dry:
        print("\nAll requested artifacts regenerated. Recompile the manuscript "
              "(pdflatex x2 + biber) to embed them.")


def _custom_example():
    """Worked customisation example: per-channel Experiment 1 (proposed_median_<region>_<channel>)."""
    import yaml
    CENTER = "median"          # change to "mean" for the Proposed-Mean variant
    DATASETS = ["raja", "cao"]
    print(f"Per-channel Experiment 1 (center_method='{CENTER}', selection='all'):\n")
    for ds in DATASETS:
        g = per_channel(ds, center=CENTER)
        g = g.sort_values(["region", "f1"], ascending=[True, False])
        print(f"[{ds}]")
        for _, r in g.iterrows():
            cid = r.ch[1:] if ds == "raja" else r.ch
            print(f"   proposed_{CENTER}_{r.region}_{cid:<5} ({r.ch}/{r.name1020})  F1={r.f1:.3f}")
        print()
    print("Edit CENTER / DATASETS above, or import load()/best_per_session()/per_channel() "
          "into your own script for arbitrary slices.")


# ---------------------------------------------------------------------------
# Shared extraction primitives (importable for custom queries)
# ---------------------------------------------------------------------------
def load(exp: str, ds: str):
    """Load a results CSV. exp in {exp1..exp8}; ds in {raja, cao}."""
    import pandas as pd
    fpat = {"exp1": ("exp1_channel_{f}", "exp1_channel_selection_{n}_results.csv"),
            "exp2": ("exp2_{f}", "exp2_strategy_comparison_{n}_results.csv"),
            "exp3": ("exp3_{f}", "exp3_epoch_duration_{n}_results.csv"),
            "exp4": ("exp4_{f}", "exp4_boundary_tolerance_{n}_results.csv"),
            "exp5": ("exp5_{f}", "exp5_nmin_sensitivity_{n}_results.csv"),
            "exp7": ("exp7_{f}", "exp7_epoch_health_{n}_results.csv"),
            "exp8": ("exp8_{f}", "exp8_long_blink_{n}_results.csv")}
    f = "raja" if ds == "raja" else "cao"
    n = "raja" if ds == "raja" else "cao2018"
    fold, name = fpat[exp]
    return pd.read_csv(NEW / fold.format(f=f) / name.format(n=n))


def best_per_session(df):
    """best-channel-per-session: the argmax det_f1 row per session (the headline aggregation)."""
    return df.loc[df.groupby("session")["det_f1"].idxmax()].copy()


def per_channel(ds: str, center: str = "median"):
    """Channel-by-channel Experiment-1 result: one row per channel, mean over sessions,
    with region (brain_region_*.yaml) and 10-20 name (32_ch.csv for Raja). No aggregation
    across channels. This is the data behind tab:exp1_channel_ablation."""
    import pandas as pd, yaml
    df = load("exp1", ds)
    df = df[(df.center_method == center) & (df.selection == "all")]
    g = (df.groupby("channel_in_group")
           .agg(p=("det_precision", "mean"), r=("det_recall", "mean"),
                f1=("det_f1", "mean"), n=("session", "nunique"))
           .reset_index().rename(columns={"channel_in_group": "ch"}))
    yml = REPO / ("brain_region_raja.yaml" if ds == "raja" else "brain_region_cao2018.yaml")
    data = yaml.safe_load(yml.read_text())["eeg_regions"]
    rmap = {}
    for grp, chans in data.items():
        for c in chans:
            rmap[(("E" + str(c)) if ds == "raja" else str(c)).upper()] = grp
    g["region"] = g.ch.apply(lambda c: rmap.get(str(c).upper(), "unmapped"))
    if ds == "raja":
        m = pd.read_csv(REPO / "32_ch.csv")
        e2n = {f"E{int(r.egi_id)}": str(r["10_20_mapping"]) for _, r in m.iterrows()}
        g["name1020"] = g.ch.apply(lambda c: e2n.get(str(c), "--"))
    else:
        g["name1020"] = g.ch
    return g


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__); return
    cmd = argv[0]
    if cmd == "list":
        _print_table()
    elif cmd == "provenance":
        if len(argv) < 2:
            print("usage: provenance <label|file|script>"); return
        _provenance(argv[1])
    elif cmd == "custom-example":
        _custom_example()
    elif cmd == "build":
        only_scripts = only_labels = None
        dry = "--dry-run" in argv
        if "--only" in argv:
            only_scripts = argv[argv.index("--only") + 1].split(",")
        if "--label" in argv:
            only_labels = argv[argv.index("--label") + 1].split(",")
        _build(only_scripts, only_labels, dry)
    else:
        print(f"unknown command '{cmd}'. See --help.")


if __name__ == "__main__":
    main(sys.argv[1:])
