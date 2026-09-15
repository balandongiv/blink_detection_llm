"""Independent re-validation of manuscript Experiment 3 (Strategy Comparison).

Manuscript items covered:
  - Table 1 (tab:f1_significance)        -- writing/e_result/exp4/tab_f1_significance.tex
  - Figure 8 (fig:exp2_pr_scatter)        -- writing/e_result/exp4/sec.tex

UPDATE (2026-09-14): the disk-folder-vs-manuscript-number mismatch noted below has
been resolved for the top-level folder name. The manuscript's Experiment 3 (strategy
comparison) data now lives under ``publication_results/exp3_cao/`` and
``publication_results/exp3_raja/`` (folder renamed to match). One residual, deliberate
inconsistency remains: the CSV file inside still carries its historical filename
(``exp2_strategy_comparison_*_results.csv``) — renaming that would require also
renaming ``paper_data.py``'s internal ``exp2``/``exp3`` keys and ``load_exp2_best()``,
which was evaluated and deliberately deferred as a much larger, higher-risk change
(see ``experiment_script/setup/exp_path.yaml``'s 2026-09-14 note and
``reports/result_inventory.md``'s addendum). Both result CSVs were opened and their
columns/unique values checked directly:

  columns: dataset, session, selection, condition, center_method, n_channels_used,
           best_channel, tp, fp, fn, precision, recall, f1
  selection unique value: {"all_channel"}          (single value -- already the
                                                      full-32-channel gate)
  condition unique values: {"BLINKER-concat", "MNE-annot", "Proposed-Mean",
                             "Proposed-Med"}
  one row per (dataset, session, condition)         -- the raw CSV has ALREADY been
                                                        reduced to one row per session
                                                        per condition (a "best_channel"
                                                        column records which channel was
                                                        used), so the "take the row with
                                                        the highest event-level F1 per
                                                        session" step is a no-op here --
                                                        it is applied anyway below for
                                                        methodological transparency and
                                                        because it is harmless when the
                                                        rule is already satisfied upstream.

This script is fully independent: it does not import experiment_script/paper_data.py
or any experiment_script/*.py generator, and does not import anything under src/. It
reads the CSVs directly with pandas and recomputes precision/recall/F1 means and
Wilcoxon significance from first principles with scipy.

Run: conda run -n double_threshold_algo python validation/validate_exp3_results.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
RAJA_CSV = REPO / "publication_results" / "exp3_raja" / "exp2_strategy_comparison_raja_results.csv"
CAO_CSV = REPO / "publication_results" / "exp3_cao" / "exp2_strategy_comparison_cao2018_results.csv"

DATASETS = {"raja": ("Internal", RAJA_CSV), "cao2018": ("Cao2018", CAO_CSV)}
PROPOSED = "Proposed-Med"
BASELINES = ["BLINKER-concat", "MNE-annot"]
CONDS_ALL = ["BLINKER-concat", "MNE-annot", "Proposed-Mean", "Proposed-Med"]

# Manuscript's printed values, read directly from
# writing/e_result/exp4/tab_f1_significance.tex (NOT from any generator script output).
MANUSCRIPT_TABLE1 = {
    "Internal": {"Proposed": 88.25, "BLINKER": 76.54, "BLINKER_sig": True,
                 "MNE": 66.64, "MNE_sig": True},
    "Cao2018": {"Proposed": 80.68, "BLINKER": 69.40, "BLINKER_sig": True,
                "MNE": 56.27, "MNE_sig": True},
}
# Manuscript prose, read directly from writing/e_result/exp4/par4.tex.
MANUSCRIPT_PAR4 = {"Internal_F1": 88.25, "Cao2018_F1": 80.68}


def load_best_per_session(csv_path: Path) -> pd.DataFrame:
    """Load raw CSV and, per condition, keep the best-F1 row per session.

    Independent re-implementation of the "best-channel-per-session" rule described in
    experiment_script/SCRIPTS_OVERVIEW.md: for each session, take the row with the
    highest event-level F1, then average across sessions. Applied identically to every
    condition. On this particular CSV the raw data is already one row per
    (session, condition) -- confirmed above -- so this is a no-op safety net, not a
    real selection step.
    """
    df = pd.read_csv(csv_path)
    assert set(df["selection"].unique()) == {"all_channel"}, (
        f"unexpected selection values in {csv_path}: {df['selection'].unique()}"
    )
    out = []
    for cond, g in df.groupby("condition"):
        idx = g.groupby("session")["f1"].idxmax()
        out.append(g.loc[idx])
    return pd.concat(out, ignore_index=True)


def macro_f1(df: pd.DataFrame, cond: str) -> tuple[float, float, float, int]:
    sub = df[df["condition"] == cond]
    return sub["precision"].mean(), sub["recall"].mean(), sub["f1"].mean(), len(sub)


def paired_f1(df: pd.DataFrame, cond_a: str, cond_b: str) -> tuple[np.ndarray, np.ndarray]:
    a = df[df["condition"] == cond_a].set_index("session")["f1"]
    b = df[df["condition"] == cond_b].set_index("session")["f1"]
    common = a.index.intersection(b.index)
    return a.loc[common].to_numpy(), b.loc[common].to_numpy()


def main() -> None:
    rows = []  # validation rows: dict per checked value
    n_bonf = len(BASELINES) * 2  # 4 tests total, matching tab4_f1_significance.py's rule

    per_ds_best = {}
    for key, (label, path) in DATASETS.items():
        best = load_best_per_session(path)
        per_ds_best[key] = (label, best)

    print("=" * 78)
    print("VALIDATE EXP3 (manuscript Experiment 3: Strategy Comparison)")
    print("Table 1 (tab:f1_significance) + Figure 8 (fig:exp2_pr_scatter)")
    print("=" * 78)

    # ---- Table 1: macro-F1 + significance -------------------------------------
    for key, (label, best) in per_ds_best.items():
        p_prop, r_prop, f1_prop, n_prop = macro_f1(best, PROPOSED)
        print(f"\n[{label}] Proposed-Med: n_sessions={n_prop} "
              f"P={p_prop*100:.2f}% R={r_prop*100:.2f}% F1={f1_prop*100:.2f}%")

        old_f1_prop = MANUSCRIPT_TABLE1[label]["Proposed"]
        diff = round(f1_prop * 100 - old_f1_prop, 4)
        status = "MATCH" if abs(diff) < 0.005 else ("ROUNDING_DIFFERENCE" if abs(diff) < 0.05 else "MISMATCH")
        rows.append({
            "experiment": "exp3_strategy_comparison",
            "manuscript_location": "Table 1 (tab:f1_significance)",
            "metric_or_statistic": f"{label} Proposed-approach macro-F1 (%)",
            "old_value": f"{old_f1_prop:.2f}",
            "new_value": f"{f1_prop*100:.2f}",
            "difference": f"{diff:+.4f}",
            "match_status": status,
            "note": f"n_sessions={n_prop}; recomputed via best-channel-per-session macro mean of f1",
            "possible_root_cause": "" if status == "MATCH" else "rounding or session-set mismatch",
        })

        for baseline, short in [("BLINKER-concat", "BLINKER"), ("MNE-annot", "MNE")]:
            p_b, r_b, f1_b, n_b = macro_f1(best, baseline)
            a, b = paired_f1(best, PROPOSED, baseline)
            _, p_raw = stats.wilcoxon(a, b, alternative="two-sided")
            p_bonf = min(1.0, p_raw * n_bonf)
            sig = p_bonf < 0.05
            print(f"  vs {short:8s}: F1={f1_b*100:.2f}%  n_pairs={len(a)}  "
                  f"p_raw={p_raw:.4g}  p_bonf={p_bonf:.4g}  sig={sig}")

            old_f1_b = MANUSCRIPT_TABLE1[label][short]
            old_sig = MANUSCRIPT_TABLE1[label][f"{short}_sig"]
            diff_f1 = round(f1_b * 100 - old_f1_b, 4)
            f1_status = "MATCH" if abs(diff_f1) < 0.005 else ("ROUNDING_DIFFERENCE" if abs(diff_f1) < 0.05 else "MISMATCH")
            rows.append({
                "experiment": "exp3_strategy_comparison",
                "manuscript_location": "Table 1 (tab:f1_significance)",
                "metric_or_statistic": f"{label} {short} macro-F1 (%)",
                "old_value": f"{old_f1_b:.2f}",
                "new_value": f"{f1_b*100:.2f}",
                "difference": f"{diff_f1:+.4f}",
                "match_status": f1_status,
                "note": f"n_sessions={n_b}; paired against Proposed-Med, n_pairs={len(a)}",
                "possible_root_cause": "" if f1_status == "MATCH" else "rounding or session-set mismatch",
            })

            sig_status = "MATCH" if sig == old_sig else "MISMATCH"
            rows.append({
                "experiment": "exp3_strategy_comparison",
                "manuscript_location": "Table 1 (tab:f1_significance)",
                "metric_or_statistic": f"{label} Proposed vs {short} significance asterisk "
                                        f"(two-sided Wilcoxon, Bonferroni x{n_bonf})",
                "old_value": "significant (*)" if old_sig else "not significant",
                "new_value": (f"significant (*), p_raw={p_raw:.4g}, p_bonf={p_bonf:.4g}" if sig
                              else f"not significant, p_raw={p_raw:.4g}, p_bonf={p_bonf:.4g}"),
                "difference": "n/a",
                "match_status": sig_status,
                "note": f"n_pairs={len(a)}",
                "possible_root_cause": "" if sig_status == "MATCH"
                    else "different Bonferroni family size, different session pairing, or stale manuscript value",
            })

    # ---- par4.tex prose cross-check (Proposed-approach F1 restated in prose) ---
    for label, key in [("Internal", "raja"), ("Cao2018", "cao2018")]:
        _, best = per_ds_best[key]
        _, _, f1_prop, _ = macro_f1(best, PROPOSED)
        old = MANUSCRIPT_PAR4[f"{label}_F1"]
        diff = round(f1_prop * 100 - old, 4)
        status = "MATCH" if abs(diff) < 0.005 else ("ROUNDING_DIFFERENCE" if abs(diff) < 0.05 else "MISMATCH")
        rows.append({
            "experiment": "exp3_strategy_comparison",
            "manuscript_location": "par4.tex prose (Experiment 3 section)",
            "metric_or_statistic": f"{label} Proposed-approach macro-F1 (%) restated in prose",
            "old_value": f"{old:.2f}",
            "new_value": f"{f1_prop*100:.2f}",
            "difference": f"{diff:+.4f}",
            "match_status": status,
            "note": "prose restates the Table 1 value verbatim",
            "possible_root_cause": "" if status == "MATCH" else "rounding or stale prose",
        })

    # ---- Figure 8: per-condition per-dataset mean P/R/F1 markers --------------
    print("\n--- Figure 8 (fig:exp2_pr_scatter) per-condition mean markers ---")
    marker_summary = {}
    for key, (label, best) in per_ds_best.items():
        marker_summary[label] = {}
        for cond in ["Proposed-Med", "BLINKER-concat", "MNE-annot"]:
            p, r, f1, n = macro_f1(best, cond)
            marker_summary[label][cond] = {"precision": p, "recall": r, "f1": f1, "n": n}
            print(f"  [{label}] {cond:<15} P={p*100:.2f}% R={r*100:.2f}% F1={f1*100:.2f}% n={n}")

        # Figure 8's marker means come from the same underlying CSV/filter as Table 1,
        # so Proposed-Med's F1 mean must equal Table 1's Proposed-approach cell exactly
        # (same data, same aggregation) -- an internal-consistency check, not a
        # cross-reference to a second printed value.
        f1_marker = marker_summary[label]["Proposed-Med"]["f1"] * 100
        old = MANUSCRIPT_TABLE1[label]["Proposed"]
        diff = round(f1_marker - old, 4)
        status = "MATCH" if abs(diff) < 0.005 else ("ROUNDING_DIFFERENCE" if abs(diff) < 0.05 else "MISMATCH")
        rows.append({
            "experiment": "exp3_strategy_comparison",
            "manuscript_location": "Figure 8 (fig:exp2_pr_scatter)",
            "metric_or_statistic": f"{label} Proposed-approach mean marker F1 (%) "
                                    f"(internal consistency vs Table 1)",
            "old_value": f"{old:.2f} (Table 1 cell)",
            "new_value": f"{f1_marker:.2f}",
            "difference": f"{diff:+.4f}",
            "match_status": status,
            "note": "Figure 8 and Table 1 share the same source rows/filter, so this "
                    "checks recomputed Figure 8 marker F1 against the printed Table 1 "
                    "value rather than against a second printed Figure 8 number "
                    "(the figure prints no numeric labels).",
            "possible_root_cause": "" if status == "MATCH" else "different filter/session set used for the figure",
        })

    # ---- par4/par5 qualitative claims: BLINKER favours recall over precision ---
    for label in ("Internal", "Cao2018"):
        p = marker_summary[label]["BLINKER-concat"]["precision"]
        r = marker_summary[label]["BLINKER-concat"]["recall"]
        recall_over_precision = r > p
        status = "MATCH" if recall_over_precision else "MISMATCH"
        rows.append({
            "experiment": "exp3_strategy_comparison",
            "manuscript_location": "par4.tex / Figure 8 prose",
            "metric_or_statistic": f"{label} BLINKER mean recall > mean precision "
                                    f"(qualitative claim: 'favors recall over precision')",
            "old_value": "recall > precision (claimed)",
            "new_value": f"precision={p*100:.2f}%, recall={r*100:.2f}% "
                         f"({'recall > precision' if recall_over_precision else 'precision >= recall'})",
            "difference": f"{(r - p) * 100:+.2f} pp",
            "match_status": status,
            "note": "qualitative directional claim from par4.tex, checked numerically",
            "possible_root_cause": "" if status == "MATCH" else "claim not supported by recomputed means",
        })

    # ---- par5 claim: Proposed-approach separated from both baselines in P and R ---
    for label in ("Internal", "Cao2018"):
        prop = marker_summary[label]["Proposed-Med"]
        blinker = marker_summary[label]["BLINKER-concat"]
        mne = marker_summary[label]["MNE-annot"]
        both_higher = (prop["precision"] > blinker["precision"] and prop["recall"] > blinker["recall"]
                       and prop["precision"] > mne["precision"] and prop["recall"] > mne["recall"])
        status = "MATCH" if both_higher else "MISMATCH"
        rows.append({
            "experiment": "exp3_strategy_comparison",
            "manuscript_location": "par5.tex prose",
            "metric_or_statistic": f"{label} Proposed-approach higher precision AND recall "
                                    f"than both baselines",
            "old_value": "Proposed higher on both axes vs both baselines (claimed)",
            "new_value": f"Proposed P={prop['precision']*100:.2f} R={prop['recall']*100:.2f}; "
                         f"BLINKER P={blinker['precision']*100:.2f} R={blinker['recall']*100:.2f}; "
                         f"MNE P={mne['precision']*100:.2f} R={mne['recall']*100:.2f}",
            "difference": "n/a",
            "match_status": status,
            "note": "qualitative directional claim from par5.tex, checked numerically",
            "possible_root_cause": "" if status == "MATCH" else (
                "prose overstates the precision-recall separation: Proposed-approach has "
                "uniformly higher PRECISION than both baselines on both datasets, but "
                "BLINKER-concat has higher RECALL than Proposed-approach on both datasets "
                "(Internal 95.18% vs 90.14%; Cao2018 97.15% vs 89.09%), which is also "
                "visible in par4.tex's own description of BLINKER as recall-favoring. The "
                "'separated from both baselines in the same direction' wording in par5.tex "
                "is not literally true on the recall axis for the BLINKER comparison."
            ),
        })

    # ---- summary ---------------------------------------------------------------
    n_match = sum(1 for r in rows if r["match_status"] == "MATCH")
    n_round = sum(1 for r in rows if r["match_status"] == "ROUNDING_DIFFERENCE")
    n_mismatch = sum(1 for r in rows if r["match_status"] == "MISMATCH")
    print("\n" + "=" * 78)
    print(f"SUMMARY: {len(rows)} values checked -- MATCH={n_match} "
          f"ROUNDING_DIFFERENCE={n_round} MISMATCH={n_mismatch}")
    print("=" * 78)

    out_path = REPO / "validation" / "_exp3_validation_rows.json"
    out_path.write_text(json.dumps(rows, indent=2))
    print(f"\nWrote {len(rows)} validation rows to {out_path}")


if __name__ == "__main__":
    main()
