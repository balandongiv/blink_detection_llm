"""Manuscript reproducibility framework.

Single entry point that documents and reproduces EVERY table and figure in the manuscript
directly from `publication_results/`.

For each artifact the MANIFEST below records:
  - the manuscript LaTeX label (\\label{...}) and the output file(s),
  - the script that generates it,
  - the exact source CSV(s) / data files it is computed from,
  - the aggregation rule used, and a one-line description.

The manifest is the machine-checkable twin of `writing/FIGURE_TABLE_MAP.md`: every artifact
in the manuscript must appear here with a live generator, and `check` fails if a generator,
a source file, or a generated output is missing.

USAGE (run inside conda env `double_threshold_algo`)
  python experiment_script/reproduce_manuscript.py list
        -> print the provenance table (artifact -> script -> source -> aggregation)
  python experiment_script/reproduce_manuscript.py provenance tab:exp1_channel_ablation
        -> full provenance for one artifact (accepts a label, an output filename, or a script)
  python experiment_script/reproduce_manuscript.py check
        -> verify every generator, source file and generated output is present
  python experiment_script/reproduce_manuscript.py build
        -> regenerate ALL artifacts (runs each generating script once)
  python experiment_script/reproduce_manuscript.py build --only tab8_error_structure.py
        -> regenerate only the artifacts produced by the named script(s) (comma separated)
  python experiment_script/reproduce_manuscript.py build --label tab:count_agreement
        -> regenerate only the script(s) that produce the given label(s)
  python experiment_script/reproduce_manuscript.py build --dry-run
        -> show what would run, without running it

For arbitrary slices of the results, import the primitives the generators themselves use:
      import paper_data as P
      P.load("exp1", "raja"); P.bps(df); P.per_channel("cao")
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "experiment_script"
WRITING = REPO / "writing"

#: Every manuscript artifact is generated from this directory and nothing else.
#: runs/, runs0/ and runs_second_iteration/ are working directories whose contents do
#: not match the published manuscript.
RESULTS = "publication_results"


@dataclass
class Artifact:
    label: str                 # LaTeX \label, or a logical id for non-floats
    kind: str                  # "table" | "figure" | "table+figure"
    outputs: list[str]         # files written, relative to writing/
    script: str                # generating script in experiment_script/
    sources: list[str]         # input files, relative to the repo root
    aggregation: str           # how values are aggregated
    desc: str                  # one-line description


def _exp(*names: str) -> list[str]:
    """Source CSVs for the given experiments across both datasets."""
    pattern = {
        "exp1": "exp1_channel_{f}/exp1_channel_selection_{n}_results.csv",
        "exp2": "exp2_{f}/exp2_strategy_comparison_{n}_results.csv",
        "exp3": "exp3_{f}/exp3_epoch_duration_{n}_results.csv",
    }
    return [
        f"{RESULTS}/" + pattern[e].format(f=f, n=n)
        for e in names
        for f, n in (("raja", "raja"), ("cao", "cao2018"))
    ]


BPS = "best-channel-per-session (argmax F1 per session, then mean across sessions)"
REGIONS = ["brain_region_raja.yaml", "brain_region_cao2018.yaml"]

MANIFEST: list[Artifact] = [
    # ---------------- Experiment 1: channel selection ----------------
    Artifact("tab:egi_map", "table", ["e_result/exp1/tab_egi_channel_map.tex"],
             "tab1_egi_channel_map.py", ["brain_region_raja.yaml"],
             "static mapping (Raja EGI hardware only; Cao2018 is native 10-20)",
             "Raja EGI-128 to 10-20 scalp-location mapping, from the egi_pair block."),
    Artifact("tab:region_performance", "table+figure",
             ["e_result/exp1/tab_region_performance.tex",
              "figures/fig_region_performance.pdf", "figures/fig_region_performance.png"],
             "tab3_fig3_region_performance.py", _exp("exp1") + REGIONS,
             "per-channel values collapsed to coarse regions; frontopolar folded into frontal, "
             "midline/outside and unassigned electrodes dropped",
             "Region-level means and the whole-scalp single-channel map, Internal on top and "
             "Cao2018 on bottom."),
    Artifact("fig:exp1_region_boxplot", "figure",
             ["figures/fig_exp1_region_boxplot.pdf", "figures/fig_exp1_region_boxplot.png"],
             "fig1_exp1_region_boxplot.py", _exp("exp1"),
             "best channel per session within each selection group",
             "Session-level F1 by channel-selection group, Raja vs Cao2018."),
    Artifact("fig:exp1_single_channel", "figure",
             ["figures/fig_exp1_single_channel_boxplot.pdf",
              "figures/fig_exp1_single_channel_boxplot.png"],
             "fig2_exp1_single_channel_boxplot.py", _exp("exp1"),
             "one channel per '*_only' selection group",
             "Session-level F1 for the single-channel selection groups."),

    # ---------------- Experiment 4: strategy comparison ----------------
    Artifact("tab:exp1_main", "table", ["e_result/exp4/tab_strategycomparison_30s_epoch.tex"],
             "tab4_tab5_strategy_comparison_30s.py", _exp("exp2"),
             BPS + "; Wilcoxon two-sided, Bonferroni x6",
             "Headline four-condition comparison at 30 s epochs."),
    Artifact("tab:exp2_inversions", "table", ["e_result/exp4/tab_exp2_inversions.tex"],
             "tab4_tab5_strategy_comparison_30s.py", _exp("exp2"),
             "per-selection mean of per-session max F1",
             "Channel groups where a baseline equals or exceeds Proposed-Med."),
    Artifact("fig:condition_prf", "figure",
             ["figures/fig_condition_prf.pdf", "figures/fig_condition_prf.png"],
             "fig4_fig5_condition_prf.py", _exp("exp2"), BPS,
             "Pooled macro precision, recall and F1 for the four conditions."),
    Artifact("fig:f1_by_dataset", "figure",
             ["figures/fig_f1_by_dataset.pdf", "figures/fig_f1_by_dataset.png"],
             "fig4_fig5_condition_prf.py", _exp("exp2"), BPS,
             "Per-condition macro F1 on Raja and Cao2018."),
    Artifact("tab:cross_dataset_gap", "table", ["e_result/exp4/tab_cross_dataset_gap.tex"],
             "tab6_cross_dataset_gap.py", _exp("exp2"), BPS,
             "Cross-dataset generalisation gap (Raja minus Cao2018)."),
    Artifact("fig:exp2_pr_scatter", "figure",
             ["figures/fig_exp2_pr_scatter.pdf", "figures/fig_exp2_pr_scatter.png"],
             "fig6_exp2_pr_scatter.py", _exp("exp2"),
             "per-session rows on the all_channel gate",
             "Per-session precision-recall scatter, corpora shown separately."),
    Artifact("fig:pr_scatter", "figure",
             ["figures/fig_pr_scatter.pdf", "figures/fig_pr_scatter.png"],
             "fig7_pr_operating_points.py", _exp("exp2"), BPS,
             "Pooled operating points with condition means and iso-F1 contours."),
    Artifact("tab:count_agreement", "table+figure",
             ["e_result/exp4/tab_count_agreement.tex",
              "figures/fig_count_agreement.pdf", "figures/fig_count_agreement.png"],
             "tab7_fig8_count_agreement.py", _exp("exp2"),
             BPS + "; predicted = TP+FP, true = TP+FN",
             "Blink-count agreement: ratio, Pearson r, Lin's CCC, Bland-Altman."),
    Artifact("tab:error-structure", "table", ["e_result/exp4/tab_error_structure.tex"],
             "tab8_error_structure.py", _exp("exp2"), BPS,
             "FP:FN decomposition per condition."),
    Artifact("tab:best-session", "table", ["e_result/exp4/tab_best_session.tex"],
             "tab9_best_session.py", _exp("exp2"), BPS,
             "Best, worst and median Proposed-Med session and subject."),
    Artifact("tab:failure_analysis", "table", ["e_result/exp4/tab_failure_analysis.tex"],
             "tab10_failure_analysis.py", _exp("exp2") + REGIONS, BPS,
             "The five lowest-F1 Proposed-Med sessions per corpus."),
    Artifact("tab:channel_selection", "table+figure",
             ["e_result/exp1/tab_channel_selection.tex",
              "figures/fig_channel_selection.pdf", "figures/fig_channel_selection.png"],
             "tab11_fig9_channel_selection_frequency.py", _exp("exp2") + REGIONS,
             "per-session winner pooled over the four conditions",
             "Best-channel selection frequency by scalp location."),
    Artifact("tab:channel-robustness", "table", ["e_result/exp1/tab_channel_robustness.tex"],
             "tab12_channel_robustness.py", _exp("exp2"),
             "agreement of the per-session best channel across conditions",
             "Stability of the best-channel choice between the four conditions."),

    # ---------------- Experiment 3: Stage-B threshold estimator ----------------
    Artifact("tab:exp3_estimator", "table", ["e_result/exp3/tab_threshold_estimator_stageb.tex"],
             "tab19_exp3_threshold_estimator.py", _exp("exp2"),
             BPS + "; Wilcoxon two-sided, Bonferroni x6",
             "Proposed-Med vs Proposed-Mean comparison isolated from the four-condition table."),

    # ---------------- Experiment 2: epoch-duration stability, and summary ----------------
    Artifact("tab:epoch_duration", "table+figure",
             ["e_result/exp2/tab_effect_different_epoch_size.tex",
              "figures/fig_exp3_epoch_duration.pdf", "figures/fig_exp3_epoch_duration.png"],
             "tab13_fig10_epoch_duration.py", _exp("exp3"),
             BPS + "; Wilcoxon two-sided vs 30 s, Bonferroni x6",
             "Macro F1 of Proposed-Med across the seven epoch durations."),
    Artifact("tab:exp_summary", "table", ["e_result/exp_summary/tab_exp_summary.tex"],
             "tab14_tab15_fig11_exp_summary.py", _exp("exp1", "exp2", "exp3"), BPS,
             "Proposed-Med across the three experiments vs the best competitor."),
    Artifact("tab:exp_stats", "table", ["e_result/exp_summary/tab_exp_stats.tex"],
             "tab14_tab15_fig11_exp_summary.py", _exp("exp1", "exp2", "exp3"),
             BPS + "; one-sided Wilcoxon, Bonferroni x6, 10k bootstrap CI",
             "Paired tests of Proposed-Med against BLINKER-concat."),
    Artifact("fig:exp_boxplot", "figure",
             ["figures/fig_exp_boxplot.pdf", "figures/fig_exp_boxplot.png"],
             "tab14_tab15_fig11_exp_summary.py", _exp("exp1", "exp2", "exp3"), BPS,
             "Session-level F1 distributions across the three experiments."),

    # ---------------- Literature ----------------
    Artifact("tab:literature_comparison", "table",
             ["c_literature_review/tab_literature_comparison.tex"],
             "tab16_literature_comparison.py", [],
             "hand-curated from the bibliography; not experiment-backed",
             "Comparison of the present detector against prior work."),
]

#: Floats that are not data-driven and are therefore not regenerated by this tool.
LEGACY = [
    ("fig:pipeline", "tikz in d_method/", "hand-drawn TikZ flow chart"),
]


def _print_table() -> None:
    print(f"\n{len(MANIFEST)} data-driven manuscript artifacts (all from {RESULTS}/):\n")
    by_script: dict[str, list[Artifact]] = {}
    for a in MANIFEST:
        by_script.setdefault(a.script, []).append(a)
    for script in sorted(by_script):
        print(f"== {script} ==")
        for a in by_script[script]:
            print(f"   [{a.kind:13}] {a.label:28} -> {', '.join(a.outputs)}")
            print(f"                   agg: {a.aggregation}")
        print()
    print("Non-data-driven floats (not regenerated here):")
    for label, out, note in LEGACY:
        print(f"   {label:28} {out:42} {note}")


def _match(query: str) -> list[Artifact]:
    q = query.strip()
    hits = [a for a in MANIFEST if q == a.label or q in a.outputs or q == a.script]
    if not hits:
        hits = [a for a in MANIFEST
                if q.lower() in a.label.lower()
                or any(q.lower() in o.lower() for o in a.outputs)
                or q.lower() in a.script.lower()]
    return hits


def _provenance(query: str) -> None:
    hits = _match(query)
    if not hits:
        print(f"No artifact matches '{query}'. Try 'list'.")
        return
    for a in hits:
        print(f"\nlabel       : {a.label}")
        print(f"kind        : {a.kind}")
        print(f"output(s)   : {', '.join(a.outputs)}")
        print(f"script      : experiment_script/{a.script}")
        print(f"aggregation : {a.aggregation}")
        print(f"description : {a.desc}")
        print("source data :")
        for s in a.sources:
            print(f"   {'OK     ' if (REPO / s).exists() else 'MISSING'} {s}")


def _check() -> int:
    problems = 0
    for a in MANIFEST:
        if not (SCRIPTS / a.script).exists():
            print(f"MISSING GENERATOR  {a.label}: experiment_script/{a.script}")
            problems += 1
        for s in a.sources:
            if not (REPO / s).exists():
                print(f"MISSING SOURCE     {a.label}: {s}")
                problems += 1
        for o in a.outputs:
            if not (WRITING / o).exists():
                print(f"MISSING OUTPUT     {a.label}: writing/{o}  (run 'build')")
                problems += 1
    print("\nAll artifacts accounted for." if not problems
          else f"\n{problems} problem(s) found.")
    return problems


def _build(only_scripts=None, only_labels=None, dry=False) -> int:
    scripts: list[str] = []
    for a in MANIFEST:
        if only_labels and a.label not in only_labels:
            continue
        if only_scripts and a.script not in only_scripts:
            continue
        if a.script not in scripts:
            scripts.append(a.script)
    if not scripts:
        print("Nothing matched the filter.")
        return 0
    print(f"Will run {len(scripts)} generating script(s): {', '.join(scripts)}\n")
    failed = []
    for s in scripts:
        if dry:
            print(f"[dry-run] python experiment_script/{s}")
            continue
        print(f"\n>>> running {s}")
        r = subprocess.run([sys.executable, str(SCRIPTS / s)], cwd=REPO)
        if r.returncode != 0:
            print(f"!!! {s} exited with code {r.returncode}")
            failed.append(s)
    if failed:
        print(f"\nFAILED: {', '.join(failed)}")
    elif not dry:
        print("\nAll requested artifacts regenerated. Recompile the manuscript "
              "(pdflatex x2 + biber) to embed them.")
    return len(failed)


def main() -> None:
    args = sys.argv[1:]
    cmd = args[0] if args else "list"
    if cmd == "list":
        _print_table()
    elif cmd == "provenance" and len(args) > 1:
        _provenance(args[1])
    elif cmd == "check":
        sys.exit(1 if _check() else 0)
    elif cmd == "build":
        only = labels = None
        if "--only" in args:
            only = args[args.index("--only") + 1].split(",")
        if "--label" in args:
            labels = args[args.index("--label") + 1].split(",")
        sys.exit(1 if _build(only, labels, "--dry-run" in args) else 0)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
