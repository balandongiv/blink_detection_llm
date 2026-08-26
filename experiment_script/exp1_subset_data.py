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
