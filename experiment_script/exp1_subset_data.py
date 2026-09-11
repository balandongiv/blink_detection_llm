"""Shared analysis layer for the Experiment 1 channel-subset artifacts.

Experiment 1 runs the complete Stage A->B->C pipeline separately on each channel
subset, so every ``selection`` group in the exp1 results is a self-contained detector
rather than a masked view of the full-montage one. This module turns those rows into
the three quantities the manuscript reports:

``subset_stats``
    Each anatomical subset against the full-montage reference.
``solo_vs_montage``
    Each single-electrode subset against the same electrode running under the
    full-montage gate — the one leave-the-rest-out contrast the data supports.
``fixed_vs_oracle``
    What the best-channel-per-session rule used throughout the manuscript costs
    relative to committing to one electrode in advance.

Aggregation is best-channel-per-session everywhere, matching ``paper_data.bps`` and
the rule stated in the Experimental Setup. Significance is Wilcoxon signed-rank with
Bonferroni correction over the comparisons made within each dataset, reported with the
matched-pairs rank-biserial correlation as the effect size.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402

#: Anatomical subsets in the order the manuscript reports them: the full-montage
#: reference first, then each region with its own hemisphere halves beneath it.
SUBSET_ORDER = [
    "all_channel",
    "frontal", "frontal_left", "frontal_right",
    "central", "central_left", "central_right",
    "parietal", "parietal_left", "parietal_right",
    "occipital", "occipital_left", "occipital_right",
    "posterior",
]

SUBSET_LABEL = {
    "all_channel": "All (full montage)",
    "frontal": "Frontal", "frontal_left": "Frontal-L", "frontal_right": "Frontal-R",
    "central": "Central", "central_left": "Central-L", "central_right": "Central-R",
    "parietal": "Parietal", "parietal_left": "Parietal-L", "parietal_right": "Parietal-R",
    "occipital": "Occipital", "occipital_left": "Occipital-L",
    "occipital_right": "Occipital-R",
    "posterior": "Posterior",
}

REFERENCE = "all_channel"


def load_median(ds: str) -> pd.DataFrame:
    """Exp1 rows for the median centre, with scalp-location channel labels attached."""
    df = P.load("exp1", ds)
    df = df[df["center_method"] == "median"].copy()
    df["display"] = df["channel"].apply(lambda c: P.display_channel(ds, c))
    return df


def bps_series(df: pd.DataFrame) -> pd.DataFrame:
    """Best-channel-per-session rows, indexed by session and sorted."""
    return (df.loc[df.groupby("session")["f1"].idxmax()]
              .set_index("session")[["precision", "recall", "f1", "display"]]
              .sort_index())


def rank_biserial(a: np.ndarray, b: np.ndarray) -> float:
    """Matched-pairs rank-biserial correlation for the Wilcoxon signed-rank test.

    Defined as the signed-rank sums normalised by their total, so it is bounded by
    +/-1 and reports the direction of ``b - a`` independently of the sample size.
    Zero differences are dropped, exactly as the test itself drops them.
    """
    d = np.asarray(b, float) - np.asarray(a, float)
    d = d[d != 0]
    if d.size == 0:
        return 0.0
    ranks = stats.rankdata(np.abs(d))
    pos, neg = ranks[d > 0].sum(), ranks[d < 0].sum()
    return float((pos - neg) / (pos + neg))


def _compare(ref: pd.Series, alt: pd.Series) -> dict:
    """Paired comparison of one subset against the reference, on shared sessions."""
    common = ref.index.intersection(alt.index)
    a, b = ref.loc[common].to_numpy(), alt.loc[common].to_numpy()
    if np.allclose(a, b):
        return {"delta": 0.0, "p_raw": 1.0, "r_rb": 0.0, "n_pairs": len(common),
                "n_better": 0}
    p = stats.wilcoxon(a, b).pvalue
    return {"delta": float(b.mean() - a.mean()), "p_raw": float(p),
            "r_rb": rank_biserial(a, b), "n_pairs": int(len(common)),
            "n_better": int((b > a).sum())}


def subset_stats(ds: str) -> pd.DataFrame:
    """Every anatomical subset against the full-montage reference, one row each.

    ``p_bonf`` is Bonferroni-corrected over the subsets actually compared for this
    dataset (the reference itself is not a comparison), which is what the Evaluation
    and Statistical Analysis subsection states is applied within each experiment.
    """
    d = load_median(ds)
    present = [s for s in SUBSET_ORDER if s in set(d["selection"])]
    per = {s: bps_series(d[d["selection"] == s]) for s in present}
    ref = per[REFERENCE]["f1"]

    rows = []
    for s in present:
        b = per[s]
        row = {"selection": s, "label": SUBSET_LABEL[s],
               "n_ch": int(d.loc[d["selection"] == s, "n_channels_used"].iloc[0]),
               "precision": b["precision"].mean(), "recall": b["recall"].mean(),
               "f1": b["f1"].mean(), "f1_sd": b["f1"].std(ddof=1),
               "f1_median": b["f1"].median(),
               "top_channel": b["display"].value_counts().idxmax()}
        row.update({"delta": 0.0, "p_raw": np.nan, "p_bonf": np.nan, "r_rb": np.nan,
                    "n_pairs": len(b), "n_better": 0} if s == REFERENCE
                   else _compare(ref, b["f1"]))
        rows.append(row)

    out = pd.DataFrame(rows)
    n_comp = (out["selection"] != REFERENCE).sum()
    out["p_bonf"] = (out["p_raw"] * n_comp).clip(upper=1.0)
    out.attrs["n_comparisons"] = int(n_comp)
    return out


def region_channels(ds: str, subset: str) -> list[str]:
    """Electrode display labels belonging to *subset*, from the canonical region map.

    Mirrors the region grouping ``tab3_fig3_region_performance.py`` uses for
    Figure 3 / Table 3: the fine ``_left``/``_right`` groups from ``paper_data.region_map``
    are unioned back into the coarse region, so membership matches Figure 3 exactly.
    ``posterior`` is parietal + occipital (both hemispheres), matching
    ``build_selection_groups`` in ``src/utils/channel_ablation_utils.py``.
    """
    rmap = P.region_map(ds)
    if subset == "posterior":
        fine = {"parietal_left", "parietal_right", "occipital_left", "occipital_right"}
    elif subset.endswith(("_left", "_right")):
        fine = {subset}
    else:
        fine = {f"{subset}_left", f"{subset}_right"}
    chans = sorted(ch for ch, r in rmap.items() if r in fine)
    return [P.display_channel(ds, c) for c in chans]


def region_session_series(df: pd.DataFrame, selection: str, channels_display: set[str]) -> pd.Series:
    """Per-session mean $F_1$ across *channels_display*, for one *selection* run.

    Equal to first averaging each electrode's $F_1$ over sessions and then averaging
    those per-electrode means across the region (the Table 3/Figure 3 aggregation),
    since every electrode in the panel is scored on every session — averaging is
    linear, so the two orders agree.
    """
    g = df[(df["selection"] == selection) & (df["display"].isin(channels_display))]
    return g.groupby("session")["f1"].mean().sort_index()


def subset_stats_region_mean(ds: str) -> pd.DataFrame:
    """Every anatomical subset scored as the mean of its own electrodes, one row each.

    Descriptive $F_1$: for each subset's self-contained rerun, average each electrode's
    session-mean $F_1$ across the electrodes the subset contains — the same aggregation
    Table 3/Figure 3 use for the full montage (``tab3_fig3_region_performance.py``),
    applied here to the subset's own multi-channel rerun instead of the full-montage run.

    Comparison baseline: the SAME region's electrodes scored inside the full-montage run
    (``selection == "all_channel"``), on shared sessions — so the paired test asks whether
    restricting Stage A/B screening to only this region changed how well the region's own
    electrodes detect blinks, not whether the subset matches the full-montage headline
    oracle. Wilcoxon signed-rank, Bonferroni-corrected over the subsets actually compared
    within each dataset, with matched-pairs rank-biserial correlation as effect size.

    The reference row ("All (full montage)") is unchanged: the established
    best-channel-per-session oracle $F_1$ used throughout the manuscript.
    """
    d = load_median(ds)
    present = [s for s in SUBSET_ORDER if s in set(d["selection"])]
    ref_bps = bps_series(d[d["selection"] == REFERENCE])["f1"]

    rows = []
    for s in present:
        n_ch = int(d.loc[d["selection"] == s, "n_channels_used"].iloc[0])
        if s == REFERENCE:
            rows.append({"selection": s, "label": SUBSET_LABEL[s], "n_ch": n_ch,
                         "f1": ref_bps.mean(), "f1_montage": np.nan, "delta": 0.0,
                         "p_raw": np.nan, "p_bonf": np.nan, "r_rb": np.nan,
                         "n_pairs": len(ref_bps), "n_better": 0})
            continue
        chans = set(region_channels(ds, s))
        subset_series = region_session_series(d, s, chans)
        montage_series = region_session_series(d, REFERENCE, chans)
        row = {"selection": s, "label": SUBSET_LABEL[s], "n_ch": n_ch,
               "f1": subset_series.mean(), "f1_montage": montage_series.mean()}
        row.update(_compare(montage_series, subset_series))
        rows.append(row)

    out = pd.DataFrame(rows)
    n_comp = (out["selection"] != REFERENCE).sum()
    out["p_bonf"] = (out["p_raw"] * n_comp).clip(upper=1.0)
    out.attrs["n_comparisons"] = int(n_comp)
    return out


def solo_vs_montage(ds: str) -> pd.DataFrame:
    """Each ``*_only`` electrode run alone versus the same electrode under the gate.

    The single-electrode subsets run Stage A, B and C on one channel, so the contrast
    against that electrode's row inside ``all_channel`` isolates what the remaining
    electrodes of the montage contribute to detection on it, and nothing else.
    """
    d = load_median(ds)
    solos = sorted(s for s in set(d["selection"]) if s.endswith("_only"))
    rows = []
    for sel in solos:
        g = d[d["selection"] == sel]
        ch = g["display"].iloc[0]
        solo = g.set_index("session")[["precision", "recall", "f1"]].sort_index()
        gated = (d[(d["selection"] == REFERENCE) & (d["display"] == ch)]
                 .set_index("session")[["precision", "recall", "f1"]].sort_index())
        common = solo.index.intersection(gated.index)
        solo, gated = solo.loc[common], gated.loc[common]
        cmp = _compare(gated["f1"], solo["f1"])
        rows.append({
            "selection": sel, "channel": ch,
            "solo_p": solo["precision"].mean(), "solo_r": solo["recall"].mean(),
            "solo_f1": solo["f1"].mean(),
            "gated_p": gated["precision"].mean(), "gated_r": gated["recall"].mean(),
            "gated_f1": gated["f1"].mean(),
            "delta": cmp["delta"], "p_raw": cmp["p_raw"], "r_rb": cmp["r_rb"],
            "n_pairs": cmp["n_pairs"],
        })
    out = pd.DataFrame(rows).sort_values("gated_f1", ascending=False).reset_index(drop=True)
    out["p_bonf"] = (out["p_raw"] * len(out)).clip(upper=1.0)
    out.attrs["n_comparisons"] = len(out)
    return out


#: The five scalp regions used throughout the regional-subset analysis
#: (``subset_stats_region_mean``/Table 17), reused here so the single-electrode
#: aggregation is not a new taxonomy — "posterior" is parietal + occipital, matching
#: ``region_channels``.
SOLO_REGION_ORDER = ["frontal", "central", "parietal", "occipital", "posterior"]
SOLO_REGION_LABEL = {"frontal": "Frontal", "central": "Central", "parietal": "Parietal",
                      "occipital": "Occipital", "posterior": "Posterior"}


def solo_channel_region(ds: str) -> dict[str, str]:
    """Coarse scalp region for every ``*_only`` electrode's display label.

    Unlike ``region_channels`` (used for the five-region aggregation below), this
    covers every solo electrode actually present in the data, including the
    midline/edge sites that fall outside the five curated regions — needed to label
    the all-electrode table and figure. Mirrors
    ``tab3_fig3_region_performance.coarse_regions``: fine ``_left``/``_right`` regions
    are folded to their coarse name and the frontopolar pair is folded into "frontal";
    anything else falls back to "midline_or_outside" or "unassigned", exactly as
    ``paper_data.per_channel`` labels it.
    """
    rmap = P.region_map(ds)
    frontopolar = {"E22", "E9"} if ds == "raja" else {"FP1", "FP2"}
    d = load_median(ds)
    solos = sorted(s for s in set(d["selection"]) if s.endswith("_only"))
    out: dict[str, str] = {}
    for sel in solos:
        g = d[d["selection"] == sel]
        ch_raw = str(g["channel"].iloc[0]).upper()
        disp = g["display"].iloc[0]
        region = rmap.get(ch_raw, "unassigned")
        coarse = region.rsplit("_", 1)[0] if region.endswith(("_left", "_right")) else region
        if ch_raw in frontopolar:
            coarse = "frontal"
        out[disp] = coarse
    return out


def solo_region_session_series(ds: str, region: str) -> pd.Series:
    """Per-session mean $F_1$ across a region's independent single-electrode runs.

    Each electrode in *region* (from ``region_channels``, so "posterior" is parietal +
    occipital) is scored by its own self-contained ``*_only`` detector; averaging those
    per-session $F_1$ values gives the session-level mean a bank of independent
    single-electrode detectors covering the region would produce — the single-electrode
    analogue of ``region_session_series`` for a self-contained multi-electrode subset.
    """
    d = load_median(ds)
    chans = set(region_channels(ds, region))
    g = d[d["selection"].str.endswith("_only") & d["display"].isin(chans)]
    return g.groupby("session")["f1"].mean().sort_index()


def solo_stats_region_mean(ds: str) -> pd.DataFrame:
    """Every ``*_only`` single-electrode result aggregated to the five established regions.

    Single-electrode analogue of ``subset_stats_region_mean``: instead of a
    self-contained multi-electrode subset rerun, each electrode here is run completely
    alone. Each region's solo-mean session series is compared, session-paired, against
    the SAME electrodes scored inside the full-montage run — the identical comparison
    target and aggregation ``subset_stats_region_mean`` uses, so the two are directly
    comparable region by region. Bonferroni-corrected over the 5 regions tested within
    each dataset (a family separate from the 32-electrode family in ``solo_vs_montage``).
    """
    d = load_median(ds)
    rows = []
    for region in SOLO_REGION_ORDER:
        chans = set(region_channels(ds, region))
        solo_series = solo_region_session_series(ds, region)
        montage_series = region_session_series(d, REFERENCE, chans)
        row = {"region": region, "label": SOLO_REGION_LABEL[region], "n_ch": len(chans),
               "f1": solo_series.mean(), "f1_montage": montage_series.mean()}
        row.update(_compare(montage_series, solo_series))
        rows.append(row)
    out = pd.DataFrame(rows)
    n_comp = len(out)
    out["p_bonf"] = (out["p_raw"] * n_comp).clip(upper=1.0)
    out.attrs["n_comparisons"] = n_comp
    return out


def three_level_region_stats(ds: str) -> dict[str, dict]:
    """Per region: individual electrode vs. regional subset vs. full montage, matched by session.

    For each of the 5 established regions, builds 3 session-matched series — the
    region's solo-electrode mean (``solo_region_session_series``), its own self-contained
    subset rerun mean (``region_session_series`` on ``selection == region``), and the
    full-montage region mean — restricted to sessions common to all three. Runs a
    Friedman omnibus test (Bonferroni-corrected over the 5 regions tested within the
    dataset) and the 3 pairwise two-tailed Wilcoxon signed-rank contrasts (single-vs-subset,
    single-vs-full, subset-vs-full), Bonferroni-corrected x3 within that region — a family
    separate from both the 5-region family above and the 32-electrode family in
    ``solo_vs_montage``. Pairwise contrasts are computed for every region so the caller has
    them on hand, but per standard omnibus/post-hoc practice they should only be reported
    in the manuscript for a region whose ``friedman_p_bonf`` is itself significant.
    """
    d = load_median(ds)
    out: dict[str, dict] = {}
    raw_omnibus_p: dict[str, float] = {}
    for region in SOLO_REGION_ORDER:
        chans = set(region_channels(ds, region))
        single = solo_region_session_series(ds, region)
        subset = region_session_series(d, region, chans)
        full = region_session_series(d, REFERENCE, chans)
        common = single.index.intersection(subset.index).intersection(full.index)
        s, u, f = single.loc[common].to_numpy(), subset.loc[common].to_numpy(), full.loc[common].to_numpy()
        entry: dict = {"n": int(len(common)),
                        "means": {"single": float(s.mean()) if len(s) else np.nan,
                                  "subset": float(u.mean()) if len(u) else np.nan,
                                  "full": float(f.mean()) if len(f) else np.nan}}
        if len(common) < 3 or (np.allclose(s, u) and np.allclose(u, f)):
            entry["friedman_p"] = np.nan
            entry["pairwise"] = {}
            raw_omnibus_p[region] = np.nan
        else:
            _, p = stats.friedmanchisquare(s, u, f)
            entry["friedman_p"] = float(p)
            raw_omnibus_p[region] = float(p)
            # Sign convention: delta = first-named condition minus second-named condition
            # (e.g. single_vs_full = single - full), matching the delta = single - full
            # convention used everywhere else in this section (solo_vs_montage,
            # solo_stats_region_mean) and the subset - full convention already used by
            # Table 17 (subset_stats_region_mean) for subset_vs_full.
            pairwise = {}
            for name, a, b in (("single_vs_subset", s, u), ("single_vs_full", s, f),
                                ("subset_vs_full", u, f)):
                if np.allclose(a, b):
                    pairwise[name] = {"delta": 0.0, "p_raw": 1.0, "r_rb": 0.0}
                else:
                    pw = float(stats.wilcoxon(a, b, alternative="two-sided").pvalue)
                    pairwise[name] = {"delta": float(a.mean() - b.mean()), "p_raw": pw,
                                       "r_rb": rank_biserial(b, a)}
            for name in pairwise:
                pairwise[name]["p_bonf"] = min(1.0, pairwise[name]["p_raw"] * 3)
            entry["pairwise"] = pairwise
        out[region] = entry

    n_regions = sum(1 for p in raw_omnibus_p.values() if p == p)
    for region, entry in out.items():
        p = entry["friedman_p"]
        entry["friedman_p_bonf"] = min(1.0, p * n_regions) if (p == p and n_regions) else np.nan
    return out


def fixed_vs_oracle(ds: str, electrodes: tuple[str, ...] = ("Fp1", "Fp2")) -> pd.DataFrame:
    """Cost of committing to one electrode instead of the per-session best channel.

    The manuscript reports every condition at its best-channel-per-session operating
    point, which is an oracle. This quantifies its size on the full montage, so the
    headline numbers can be read against a deployable fixed-electrode alternative.
    """
    d = load_median(ds)
    piv = (d[d["selection"] == REFERENCE]
           .pivot_table(index="session", columns="display", values="f1"))
    oracle = piv.max(axis=1)

    rows = []
    for ch in [c for c in electrodes if c in piv.columns]:
        short = oracle - piv[ch]
        rows.append({"channel": ch, "f1": piv[ch].mean(),
                     "shortfall_mean": short.mean(), "shortfall_median": short.median(),
                     "within_002": int((short <= 0.02).sum()), "n": len(short)})
    pair = [c for c in electrodes if c in piv.columns]
    if len(pair) > 1:
        best_pair = piv[pair].max(axis=1)
        short = oracle - best_pair
        rows.append({"channel": "best of " + " / ".join(pair), "f1": best_pair.mean(),
                     "shortfall_mean": short.mean(), "shortfall_median": short.median(),
                     "within_002": int((short <= 0.02).sum()), "n": len(short)})
    out = pd.DataFrame(rows)
    out.attrs["oracle_f1"] = float(oracle.mean())
    return out


def best_channel_frequency(ds: str) -> pd.Series:
    """How often each electrode was the per-session best under the full montage."""
    d = load_median(ds)
    piv = (d[d["selection"] == REFERENCE]
           .pivot_table(index="session", columns="display", values="f1"))
    return piv.idxmax(axis=1).value_counts()


def stage_b_threshold(ds: str) -> pd.DataFrame:
    """Mean Stage-B blink-region threshold per subset, in microvolts.

    The threshold is a sample-level detector parameter, and it is what explains the
    behaviour of the posterior subsets: it is estimated from the amplitude
    distribution of the channels in the subset, so a subset containing no strong
    ocular projection sets it against background activity instead.
    """
    d = load_median(ds)
    g = (d.groupby("selection")
           .agg(thr_uv=("blink_region_threshold", "mean"),
                n_ch=("n_channels_used", "first"))
           .reset_index())
    g["thr_uv"] *= 1e6
    g["label"] = g["selection"].map(SUBSET_LABEL).fillna(g["selection"])
    return g.sort_values("thr_uv", ascending=False).reset_index(drop=True)


def reference_macro(ds: str) -> dict:
    """The full-montage reference operating point, for the opening subsection."""
    b = bps_series(load_median(ds)[lambda x: x["selection"] == REFERENCE])
    return {"precision": b["precision"].mean(), "recall": b["recall"].mean(),
            "f1": b["f1"].mean(), "n_sessions": len(b)}
