"""Independent re-validation of manuscript Experiment 1 (EEG Channel-Subset Analysis).

Manuscript items covered:
  - Figure 3 (fig:exp1_subset_per_electrode)         -- p05_regional/paragraph_per_electrode.tex
  - Figure 4 (fig:exp1_subset_per_electrode_stats)   -- p05_regional/paragraph_electrode_level_stats.tex
  - Figure 5 (fig:exp1_single_channel)               -- exp1/sec.tex + p07_single_channel/paragraph_per_electrode.tex
  - Figure 6 (fig:exp1_single_channel_stats)         -- exp1/sec.tex (figure*) + p07_single_channel/paragraph_electrode_level_stats.tex

None of these four figures are pure unlabelled boxplots: each bar/pair carries a
printed numeric label (bar_label / significance asterisk), and the manuscript prose
paragraphs restate many of those exact bar values and Bonferroni-adjusted-significance
counts/claims in text. "old_value" below is therefore read directly from those .tex
prose files (writing/e_result/exp1/p05_regional/*.tex and
writing/e_result/exp1/p07_single_channel/*.tex), NOT from any generator script's
console output.

Disk-folder gotcha (confirmed by directly inspecting the CSVs before writing this
script): the manuscript's Experiment 1 (channel selection) data lives under
``publication_results/exp1_channel_cao/`` and ``publication_results/exp1_channel_raja/``
on disk -- this is the one case where the disk folder name matches the manuscript's own
experiment number. Columns/values checked directly:

  columns: channel, ..., precision, recall, f1, dataset, session, selection,
           center_method, condition, n_channels_used, ...
  selection includes: all_channel, frontal/central/parietal/occipital (+ _left/_right),
                       posterior, and per-electrode "<ch>_only" groups
  center_method: {"mean", "median"}  (this script uses "median" == Proposed-Med
                                       throughout, matching every live Experiment 1
                                       figure)

This script is fully independent: it does not import experiment_script/paper_data.py,
experiment_script/exp1_subset_data.py, or any experiment_script/*.py generator, and
does not import anything under src/. Region membership is read directly from
brain_region_raja.yaml / brain_region_cao2018.yaml with a fresh, from-scratch
re-implementation of the region-folding rule (documented in
experiment_script/paper_data.py's region_map()/display_channel() docstrings, which were
read only as documentation, not imported).

Run: conda run -n double_threshold_algo python validation/validate_exp1_results.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
RAJA_CSV = REPO / "publication_results" / "exp1_channel_raja" / "exp1_channel_selection_raja_results.csv"
CAO_CSV = REPO / "publication_results" / "exp1_channel_cao" / "exp1_channel_selection_cao2018_results.csv"
DATASETS = {"raja": ("Internal", RAJA_CSV), "cao2018": ("Cao2018", CAO_CSV)}

REGION_ORDER = ["frontal", "central", "parietal", "occipital"]
REGION_LABEL = {"frontal": "Frontal", "central": "Central", "parietal": "Parietal", "occipital": "Occipital"}

_1020_SPELLING = {"FP1": "Fp1", "FP2": "Fp2", "FZ": "Fz", "CZ": "Cz",
                  "PZ": "Pz", "OZ": "Oz", "FCZ": "FCz", "CPZ": "CPz"}


def spell_1020(name: str) -> str:
    upper = str(name).upper()
    return _1020_SPELLING.get(upper, upper)


def load_yaml_regions(ds_key: str) -> dict:
    fname = "brain_region_raja.yaml" if ds_key == "raja" else "brain_region_cao2018.yaml"
    return yaml.safe_load((REPO / fname).read_text())


def fine_region_map(ds_key: str) -> dict[str, str]:
    """channel(raw label) -> fine region (only the _left/_right anatomical groups)."""
    doc = load_yaml_regions(ds_key)

    def label(ch) -> str:
        return (f"E{ch}" if ds_key == "raja" else str(ch)).upper()

    non_region = {"all_channel", "frontal", "central", "parietal", "occipital", "posterior"}
    out = {}
    for group, channels in doc["eeg_regions"].items():
        if group in non_region or group.endswith("_only"):
            continue
        for ch in channels:
            out[label(ch)] = group
    return out


def egi_to_1020(ds_key: str) -> dict[str, str]:
    if ds_key != "raja":
        return {}
    doc = load_yaml_regions("raja")
    out = {}
    for entry in doc.get("egi_pair") or []:
        for name, egi_id in entry.items():
            out[f"E{int(egi_id)}"] = spell_1020(name)
    return out


def display_channel(ds_key: str, channel: str, egi_map: dict) -> str:
    if ds_key == "raja":
        return egi_map.get(str(channel), str(channel))
    return spell_1020(channel)


def coarse_region_for_solo(ds_key: str, raw_channel: str, rmap: dict) -> str:
    """Coarse region for a *_only solo channel, folding frontopolar into 'frontal'."""
    frontopolar = {"E22", "E9"} if ds_key == "raja" else {"FP1", "FP2"}
    raw_upper = str(raw_channel).upper()
    region = rmap.get(raw_upper, "unassigned")
    coarse = region.rsplit("_", 1)[0] if region.endswith(("_left", "_right")) else region
    if raw_upper in frontopolar:
        coarse = "frontal"
    return coarse


def status_for(diff: float, tol_match: float = 0.03, tol_round: float = 0.10) -> str:
    if abs(diff) < tol_match:
        return "MATCH"
    if abs(diff) < tol_round:
        return "ROUNDING_DIFFERENCE"
    return "MISMATCH"


def rank_biserial(a: np.ndarray, b: np.ndarray) -> float:
    d = np.asarray(b, float) - np.asarray(a, float)
    d = d[d != 0]
    if d.size == 0:
        return 0.0
    ranks = stats.rankdata(np.abs(d))
    pos, neg = ranks[d > 0].sum(), ranks[d < 0].sum()
    return float((pos - neg) / (pos + neg))


# ---------------------------------------------------------------------------
# Manuscript prose values (read directly from the .tex sources listed in the module
# docstring, NOT from any generator script output).
# ---------------------------------------------------------------------------

FIG3_CLAIMS = {
    ("Internal", "frontal"): {"Fp2": 85.28, "Fp1": 84.84, "AF4": 77.04, "AF3": 70.70,
                               "F3": 42.68, "F4": 41.00},
    ("Cao2018", "frontal"): {"Fp1": 78.80, "Fp2": 77.05, "F3": 55.97, "F4": 54.64},
    ("Internal", "central"): {"C3": 58.59, "C4": 1.73},
    ("Cao2018", "central"): {"C3": 27.67, "C4": 26.62},
    ("Internal", "parietal_best"): {"CP1": 1.92},
    ("Cao2018", "parietal_best"): {"CP4": 15.63},
    ("Internal", "occipital_best"): {"PO3": 3.35},
    ("Cao2018", "occipital_best"): {"P3": 10.04},
}

FIG4_CLAIMS = {
    "Internal": {"n_tested": 24, "n_sig": 11,
                 "not_sig": ["Fp1", "Fp2"], "sig": ["AF4", "AF3", "C3"], "not_sig_extra": ["C4"]},
    "Cao2018": {"n_tested": 18, "n_sig": 16,
                "not_sig": ["Fp1", "Fp2"], "sig": ["F3", "F4", "C3", "C4"], "not_sig_extra": []},
}

FIG5_CLAIMS = {
    "Internal": {"Fp1": 83.73, "Fp2": 83.37, "AF4": 75.16, "AF3": 67.59, "C3": 54.05,
                 "F4": 39.98, "F3": 39.85, "C4": 1.51},
    "Cao2018": {"Fp1": 77.65, "Fp2": 75.59, "F3": 49.30, "F4": 49.03, "FC3": 38.44,
                "FC4": 36.72, "FT8": 34.99, "FT7": 34.22, "C3": 25.43, "C4": 25.10,
                "O1": 2.28},
}

FIG6_CLAIMS = {
    "Internal": {"n_tested": 24, "n_sig": 14, "delta_min": -7.02, "delta_max": -0.15,
                 "not_sig": ["Fp1", "Fp2"], "sig": ["AF4", "AF3", "C3", "C4"]},
    "Cao2018": {"n_tested": 18, "n_sig": 16,
                "not_sig": ["Fp1", "Fp2"], "sig": ["C3", "C4"],
                "delta_named": {"F3": -10.21, "F4": -8.96}},
}


def main() -> None:
    rows = []

    print("=" * 78)
    print("VALIDATE EXP1 (manuscript Experiment 1: EEG Channel-Subset Analysis)")
    print("Figures 3, 4, 5, 6")
    print("=" * 78)

    for ds_key, (label, csv_path) in DATASETS.items():
        df_all = pd.read_csv(csv_path)
        df = df_all[df_all["center_method"] == "median"].copy()
        egi_map = egi_to_1020(ds_key)
        rmap = fine_region_map(ds_key)
        df["display"] = df["channel"].apply(lambda c: display_channel(ds_key, c, egi_map))

        montage = df[df["selection"] == "all_channel"]

        # =====================================================================
        # Figure 3: per-electrode F1 within each region's own subset rerun
        # =====================================================================
        print(f"\n--- [{label}] Figure 3: regional subset per-electrode F1 ---")
        subset_means = {}
        for region in REGION_ORDER:
            sub = df[df["selection"] == region]
            means = sub.groupby("display")["f1"].mean().sort_values(ascending=False) * 100
            subset_means[region] = means
            print(f"  {region}: " + ", ".join(f"{ch}={v:.2f}" for ch, v in means.items()))

        for region in ["frontal", "central"]:
            claim = FIG3_CLAIMS.get((label, region))
            if not claim:
                continue
            means = subset_means[region]
            for ch, old_v in claim.items():
                new_v = float(means.get(ch, np.nan))
                diff = round(new_v - old_v, 4)
                status = status_for(diff) if new_v == new_v else "NOT_REPRODUCIBLE_FROM_AVAILABLE_CSV"
                rows.append({
                    "experiment": "exp1_channel_selection",
                    "manuscript_location": "Figure 3 (fig:exp1_subset_per_electrode) / p05_regional prose",
                    "metric_or_statistic": f"{label} {region} subset rerun F1 (%) for {ch}",
                    "old_value": f"{old_v:.2f}",
                    "new_value": f"{new_v:.2f}" if new_v == new_v else "channel not found",
                    "difference": f"{diff:+.4f}" if new_v == new_v else "n/a",
                    "match_status": status,
                    "note": f"selection=='{region}', center_method=='median', mean f1 across sessions",
                    "possible_root_cause": "" if status == "MATCH" else "rounding, channel-label mapping, or stale prose",
                })

        for region_key, top_label in [("parietal_best", "parietal"), ("occipital_best", "occipital")]:
            claim = FIG3_CLAIMS.get((label, region_key))
            if not claim:
                continue
            means = subset_means[top_label]
            best_ch, best_v = means.index[0], float(means.iloc[0])
            (claim_ch, claim_v), = claim.items()
            ch_status = "MATCH" if best_ch == claim_ch else "MISMATCH"
            diff = round(best_v - claim_v, 4)
            v_status = status_for(diff)
            overall = "MATCH" if (ch_status == "MATCH" and v_status == "MATCH") else "MISMATCH"
            rows.append({
                "experiment": "exp1_channel_selection",
                "manuscript_location": "Figure 3 (fig:exp1_subset_per_electrode) / p05_regional prose",
                "metric_or_statistic": f"{label} best-performing {top_label} electrode in its own subset rerun",
                "old_value": f"{claim_ch}={claim_v:.2f}",
                "new_value": f"{best_ch}={best_v:.2f}",
                "difference": f"{diff:+.4f}" if ch_status == "MATCH" else "n/a (different electrode identified as best)",
                "match_status": overall,
                "note": f"selection=='{top_label}', center_method=='median'",
                "possible_root_cause": "" if overall == "MATCH" else "different best-electrode identified, or rounding",
            })

        # =====================================================================
        # Figure 4: per-electrode subset vs full-montage significance
        # =====================================================================
        print(f"\n--- [{label}] Figure 4: subset vs montage significance ---")
        pair_rows = []
        for region in REGION_ORDER:
            sub = df[df["selection"] == region]
            for ch, grp in sub.groupby("channel"):
                subset_series = grp.groupby("session")["f1"].mean()
                montage_series = montage[montage["channel"] == ch].groupby("session")["f1"].mean()
                common = subset_series.index.intersection(montage_series.index)
                a = montage_series.loc[common].to_numpy()  # full montage
                b = subset_series.loc[common].to_numpy()   # subset
                if len(common) == 0:
                    continue
                identical = np.allclose(a, b)
                if identical:
                    p_raw = 1.0
                else:
                    p_raw = float(stats.wilcoxon(a, b, alternative="two-sided").pvalue)
                pair_rows.append({
                    "channel": ch, "display": grp["display"].iloc[0], "region": region,
                    "f1_subset": b.mean(), "f1_montage": a.mean(), "p_raw": p_raw,
                })
        pdf = pd.DataFrame(pair_rows)
        n_tests = len(pdf)
        pdf["p_bonf"] = (pdf["p_raw"] * n_tests).clip(upper=1.0)
        n_sig = int((pdf["p_bonf"] < 0.05).sum())
        print(f"  n_tested={n_tests}, n_sig={n_sig}")
        for _, r in pdf.iterrows():
            flag = "SIG" if r["p_bonf"] < 0.05 else "ns"
            print(f"    {r['display']:6s} {r['region']:10s} subset={r['f1_subset']*100:6.2f} "
                  f"montage={r['f1_montage']*100:6.2f} p_bonf={r['p_bonf']:.4g} {flag}")

        claim = FIG4_CLAIMS[label]
        diff_n = n_tested_diff = n_tests - claim["n_tested"]
        status_n = "MATCH" if n_tests == claim["n_tested"] else "MISMATCH"
        rows.append({
            "experiment": "exp1_channel_selection",
            "manuscript_location": "Figure 4 (fig:exp1_subset_per_electrode_stats) / p05_regional prose",
            "metric_or_statistic": f"{label} number of electrodes tested (subset vs montage)",
            "old_value": str(claim["n_tested"]),
            "new_value": str(n_tests),
            "difference": str(diff_n),
            "match_status": status_n,
            "note": "count of electrodes appearing in one of the four curated anatomical subsets",
            "possible_root_cause": "" if status_n == "MATCH" else "different region membership or electrode inclusion rule",
        })
        status_sig = "MATCH" if n_sig == claim["n_sig"] else "MISMATCH"
        rows.append({
            "experiment": "exp1_channel_selection",
            "manuscript_location": "Figure 4 (fig:exp1_subset_per_electrode_stats) / p05_regional prose",
            "metric_or_statistic": f"{label} number of electrodes significant after Bonferroni "
                                    f"(subset vs montage, two-sided Wilcoxon)",
            "old_value": f"{claim['n_sig']} of {claim['n_tested']}",
            "new_value": f"{n_sig} of {n_tests}",
            "difference": str(n_sig - claim["n_sig"]),
            "match_status": status_sig,
            "note": "",
            "possible_root_cause": "" if status_sig == "MATCH" else "different Bonferroni family size, session pairing, or stale prose",
        })
        for ch in claim["not_sig"]:
            row = pdf[pdf["display"] == ch]
            if row.empty:
                rows.append({
                    "experiment": "exp1_channel_selection",
                    "manuscript_location": "Figure 4 (fig:exp1_subset_per_electrode_stats) / p05_regional prose",
                    "metric_or_statistic": f"{label} {ch} subset-vs-montage significance (claimed not significant)",
                    "old_value": "not significant (p=1.000, claimed)",
                    "new_value": "channel not found in subset-tested set",
                    "difference": "n/a", "match_status": "NOT_REPRODUCIBLE_FROM_AVAILABLE_CSV",
                    "note": "", "possible_root_cause": "channel absent from the four curated subsets in this recomputation",
                })
                continue
            p_bonf = float(row["p_bonf"].iloc[0])
            sig = p_bonf < 0.05
            status = "MATCH" if not sig else "MISMATCH"
            rows.append({
                "experiment": "exp1_channel_selection",
                "manuscript_location": "Figure 4 (fig:exp1_subset_per_electrode_stats) / p05_regional prose",
                "metric_or_statistic": f"{label} {ch} subset-vs-montage significance (claimed not significant, p=1.000)",
                "old_value": "not significant (p=1.000)",
                "new_value": f"p_bonf={p_bonf:.4g} ({'sig' if sig else 'ns'})",
                "difference": "n/a", "match_status": status,
                "note": "", "possible_root_cause": "" if status == "MATCH" else "rounding, session mismatch, or stale prose",
            })
        for ch in claim["sig"] + claim.get("not_sig_extra", []):
            row = pdf[pdf["display"] == ch]
            if row.empty:
                continue
            p_bonf = float(row["p_bonf"].iloc[0])
            sig = p_bonf < 0.05
            claimed_sig = ch not in claim.get("not_sig_extra", [])
            status = "MATCH" if sig == claimed_sig else "MISMATCH"
            rows.append({
                "experiment": "exp1_channel_selection",
                "manuscript_location": "Figure 4 (fig:exp1_subset_per_electrode_stats) / p05_regional prose",
                "metric_or_statistic": f"{label} {ch} subset-vs-montage significance "
                                        f"(claimed {'significant' if claimed_sig else 'not significant'})",
                "old_value": "significant" if claimed_sig else "not significant",
                "new_value": f"p_bonf={p_bonf:.4g} ({'sig' if sig else 'ns'})",
                "difference": "n/a", "match_status": status,
                "note": "", "possible_root_cause": "" if status == "MATCH" else "rounding, session mismatch, or stale prose",
            })

        # =====================================================================
        # Figure 5: single-channel (solo) F1 by region
        # =====================================================================
        print(f"\n--- [{label}] Figure 5: single-channel solo F1 ---")
        solo = df[df["selection"].str.endswith("_only")].copy()
        solo_f1 = solo.groupby("channel").agg(f1=("f1", "mean"), display=("display", "first"))
        solo_f1["coarse"] = [coarse_region_for_solo(ds_key, ch, rmap) for ch in solo_f1.index]
        solo_curated = solo_f1[solo_f1["coarse"].isin(REGION_ORDER)].sort_values("f1", ascending=False)
        print(f"  n_curated={len(solo_curated)}")
        for ch, r in solo_curated.iterrows():
            print(f"    {r['display']:6s} {r['coarse']:10s} f1={r['f1']*100:.2f}")

        claim5 = FIG5_CLAIMS[label]
        disp_to_f1 = solo_curated.set_index("display")["f1"] * 100
        for ch, old_v in claim5.items():
            new_v = float(disp_to_f1.get(ch, np.nan))
            diff = round(new_v - old_v, 4) if new_v == new_v else None
            status = status_for(diff) if diff is not None else "NOT_REPRODUCIBLE_FROM_AVAILABLE_CSV"
            rows.append({
                "experiment": "exp1_channel_selection",
                "manuscript_location": "Figure 5 (fig:exp1_single_channel) / p07_single_channel prose",
                "metric_or_statistic": f"{label} single-electrode F1 (%) for {ch}",
                "old_value": f"{old_v:.2f}",
                "new_value": f"{new_v:.2f}" if new_v == new_v else "channel not found",
                "difference": f"{diff:+.4f}" if diff is not None else "n/a",
                "match_status": status,
                "note": "selection=='<ch>_only', center_method=='median', restricted to the four curated regions",
                "possible_root_cause": "" if status == "MATCH" else "rounding, channel-label mapping, or stale prose",
            })

        # =====================================================================
        # Figure 6: single-channel vs full-montage significance
        # =====================================================================
        print(f"\n--- [{label}] Figure 6: single-channel vs montage significance ---")
        pair6 = []
        for ch, r in solo_curated.iterrows():
            solo_series = solo[solo["channel"] == ch].set_index("session")["f1"]
            montage_series = montage[montage["channel"] == ch].set_index("session")["f1"]
            common = solo_series.index.intersection(montage_series.index)
            a = solo_series.loc[common].to_numpy()      # single
            b = montage_series.loc[common].to_numpy()   # montage
            if len(common) == 0:
                continue
            if np.allclose(a, b):
                p_raw = 1.0
            else:
                p_raw = float(stats.wilcoxon(a, b, alternative="two-sided").pvalue)
            pair6.append({"display": r["display"], "solo_f1": a.mean(), "montage_f1": b.mean(),
                          "delta": a.mean() - b.mean(), "p_raw": p_raw})
        pdf6 = pd.DataFrame(pair6)
        n_tests6 = len(pdf6)
        pdf6["p_bonf"] = (pdf6["p_raw"] * n_tests6).clip(upper=1.0)
        n_sig6 = int((pdf6["p_bonf"] < 0.05).sum())
        print(f"  n_tested={n_tests6}, n_sig={n_sig6}, "
              f"delta range=[{pdf6['delta'].min()*100:.2f}, {pdf6['delta'].max()*100:.2f}]")
        for _, r in pdf6.iterrows():
            flag = "SIG" if r["p_bonf"] < 0.05 else "ns"
            print(f"    {r['display']:6s} solo={r['solo_f1']*100:6.2f} montage={r['montage_f1']*100:6.2f} "
                  f"delta={r['delta']*100:+6.2f} p_bonf={r['p_bonf']:.4g} {flag}")

        claim6 = FIG6_CLAIMS[label]
        status_n6 = "MATCH" if n_tests6 == claim6["n_tested"] else "MISMATCH"
        rows.append({
            "experiment": "exp1_channel_selection",
            "manuscript_location": "Figure 6 (fig:exp1_single_channel_stats) / p07_single_channel prose",
            "metric_or_statistic": f"{label} number of electrodes tested (single vs montage)",
            "old_value": str(claim6["n_tested"]), "new_value": str(n_tests6),
            "difference": str(n_tests6 - claim6["n_tested"]), "match_status": status_n6,
            "note": "", "possible_root_cause": "" if status_n6 == "MATCH" else "different region membership or inclusion rule",
        })
        status_sig6 = "MATCH" if n_sig6 == claim6["n_sig"] else "MISMATCH"
        rows.append({
            "experiment": "exp1_channel_selection",
            "manuscript_location": "Figure 6 (fig:exp1_single_channel_stats) / p07_single_channel prose",
            "metric_or_statistic": f"{label} number of electrodes significant after Bonferroni "
                                    f"(single vs montage, two-sided Wilcoxon)",
            "old_value": f"{claim6['n_sig']} of {claim6['n_tested']}",
            "new_value": f"{n_sig6} of {n_tests6}",
            "difference": str(n_sig6 - claim6["n_sig"]), "match_status": status_sig6,
            "note": "", "possible_root_cause": "" if status_sig6 == "MATCH" else "different Bonferroni family size, session pairing, or stale prose",
        })
        if "delta_min" in claim6:
            new_min, new_max = pdf6["delta"].min() * 100, pdf6["delta"].max() * 100
            diff_min = round(new_min - claim6["delta_min"], 4)
            diff_max = round(new_max - claim6["delta_max"], 4)
            status_range = "MATCH" if (abs(diff_min) < 0.05 and abs(diff_max) < 0.05) else "MISMATCH"
            rows.append({
                "experiment": "exp1_channel_selection",
                "manuscript_location": "Figure 6 (fig:exp1_single_channel_stats) / p07_single_channel prose",
                "metric_or_statistic": f"{label} delta-F1 range across all {n_tests6} electrodes "
                                        f"(single minus montage, percentage points)",
                "old_value": f"[{claim6['delta_min']:.2f}, {claim6['delta_max']:.2f}]",
                "new_value": f"[{new_min:.2f}, {new_max:.2f}]",
                "difference": f"min {diff_min:+.4f}, max {diff_max:+.4f}",
                "match_status": status_range,
                "note": "", "possible_root_cause": "" if status_range == "MATCH" else "rounding or different electrode set",
            })
        for ch in claim6["not_sig"]:
            row = pdf6[pdf6["display"] == ch]
            if row.empty:
                continue
            sig = float(row["p_bonf"].iloc[0]) < 0.05
            status = "MATCH" if not sig else "MISMATCH"
            rows.append({
                "experiment": "exp1_channel_selection",
                "manuscript_location": "Figure 6 (fig:exp1_single_channel_stats) / p07_single_channel prose",
                "metric_or_statistic": f"{label} {ch} single-vs-montage significance (claimed not significant, p=1.000)",
                "old_value": "not significant (p=1.000)",
                "new_value": f"p_bonf={float(row['p_bonf'].iloc[0]):.4g} ({'sig' if sig else 'ns'})",
                "difference": "n/a", "match_status": status,
                "note": "", "possible_root_cause": "" if status == "MATCH" else "rounding, session mismatch, or stale prose",
            })
        for ch in claim6["sig"]:
            row = pdf6[pdf6["display"] == ch]
            if row.empty:
                continue
            sig = float(row["p_bonf"].iloc[0]) < 0.05
            status = "MATCH" if sig else "MISMATCH"
            rows.append({
                "experiment": "exp1_channel_selection",
                "manuscript_location": "Figure 6 (fig:exp1_single_channel_stats) / p07_single_channel prose",
                "metric_or_statistic": f"{label} {ch} single-vs-montage significance (claimed significant)",
                "old_value": "significant",
                "new_value": f"p_bonf={float(row['p_bonf'].iloc[0]):.4g} ({'sig' if sig else 'ns'})",
                "difference": "n/a", "match_status": status,
                "note": "", "possible_root_cause": "" if status == "MATCH" else "rounding, session mismatch, or stale prose",
            })
        for ch, old_delta in claim6.get("delta_named", {}).items():
            row = pdf6[pdf6["display"] == ch]
            if row.empty:
                continue
            new_delta = float(row["delta"].iloc[0]) * 100
            diff = round(new_delta - old_delta, 4)
            status = status_for(diff)
            rows.append({
                "experiment": "exp1_channel_selection",
                "manuscript_location": "Figure 6 (fig:exp1_single_channel_stats) / p07_single_channel prose",
                "metric_or_statistic": f"{label} {ch} delta-F1 (single minus montage, percentage points)",
                "old_value": f"{old_delta:+.2f}",
                "new_value": f"{new_delta:+.2f}",
                "difference": f"{diff:+.4f}", "match_status": status,
                "note": "", "possible_root_cause": "" if status == "MATCH" else "rounding or session mismatch",
            })

    # ---- summary ---------------------------------------------------------------
    n_match = sum(1 for r in rows if r["match_status"] == "MATCH")
    n_round = sum(1 for r in rows if r["match_status"] == "ROUNDING_DIFFERENCE")
    n_mismatch = sum(1 for r in rows if r["match_status"] == "MISMATCH")
    n_other = len(rows) - n_match - n_round - n_mismatch
    print("\n" + "=" * 78)
    print(f"SUMMARY: {len(rows)} values checked -- MATCH={n_match} "
          f"ROUNDING_DIFFERENCE={n_round} MISMATCH={n_mismatch} OTHER={n_other}")
    print("=" * 78)

    out_path = REPO / "validation" / "_exp1_validation_rows.json"
    out_path.write_text(json.dumps(rows, indent=2))
    print(f"\nWrote {len(rows)} validation rows to {out_path}")


if __name__ == "__main__":
    main()
