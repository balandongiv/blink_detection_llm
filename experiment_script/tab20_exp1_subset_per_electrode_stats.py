"""Table 20 -- Experiment 1 per-electrode paired comparison: subset rerun vs full montage.

Companion to Table 17 (``tab17_exp1_subset_summary.py``): Table 17 tests each anatomical
subset's REGION MEAN against the same region's electrodes scored inside the full-montage
run. This table tests each INDIVIDUAL ELECTRODE the same way: for every electrode that
appears in one of the four anatomical subsets shown in Figure 13
(``fig13_exp1_subset_per_electrode.py``), the session-level $F_1$ of that electrode inside
its own subset rerun is paired, session by session, against the session-level $F_1$ of the
SAME electrode inside the full-montage run (``selection == "all_channel"``). This is the
electrode-level analogue of Table 17's region-level test, and answers a different question:
which individual electrodes, not which regions, changed when their region operated as an
independent detector.

Test: two-tailed Wilcoxon signed-rank, paired by session, matching ``exp1_subset_data``'s
``rank_biserial`` sign convention (subset minus montage). Bonferroni correction is applied
separately within each dataset, over every electrode tested in that dataset (24 for
Internal, 18 for Cao2018) -- a separate family from Table 17's 13 region-level tests.

If every matched session has an (near-)identical subset and montage $F_1$ for an electrode,
no Wilcoxon statistic exists (there is nothing to rank); this is flagged explicitly in the
table rather than reporting an invented $p$-value.

Writes ``writing/e_result/exp1/tab_exp1_subset_per_electrode_stats.tex``.

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
import exp1_subset_data as SD  # noqa: E402

SCRIPT = "tab20_exp1_subset_per_electrode_stats.py"
OUT = P.ER / "exp1" / "tab_exp1_subset_per_electrode_stats.tex"

#: Matches Figure 13's SUMMARY_REGION_ORDER exactly -- the four self-contained anatomical
#: subsets that retain more than one electrode. ``posterior`` is a union of parietal and
#: occipital and would duplicate electrodes already tested there, so it is not repeated.
REGION_ORDER = ["frontal", "central", "parietal", "occipital"]
REGION_LABEL = {"frontal": "Frontal", "central": "Central", "parietal": "Parietal",
                "occipital": "Occipital"}


def electrode_pairs(ds: str) -> pd.DataFrame:
    """One row per electrode: subset vs full-montage session-level $F_1$, paired by session."""
    d = SD.load_median(ds)
    montage = d[d["selection"] == SD.REFERENCE]
    rows = []
    for region in REGION_ORDER:
        sub = d[d["selection"] == region]
        for ch, grp in sub.groupby("channel"):
            subset_series = grp.groupby("session")["f1"].mean().sort_index()
            montage_series = (montage[montage["channel"] == ch]
                               .groupby("session")["f1"].mean().sort_index())
            common = subset_series.index.intersection(montage_series.index)
            a = montage_series.loc[common].to_numpy()  # full montage
            b = subset_series.loc[common].to_numpy()   # subset
            diffs = b - a
            identical = bool(len(diffs)) and bool(np.allclose(diffs, 0))
            if len(common) == 0:
                p_raw, r_rb = np.nan, np.nan
            elif identical:
                p_raw, r_rb = 1.0, 0.0
            else:
                p_raw = float(stats.wilcoxon(a, b, alternative="two-sided").pvalue)
                r_rb = SD.rank_biserial(a, b)
            rows.append({
                "dataset": ds, "region": region, "channel": ch,
                "display": grp["display"].iloc[0],
                "n_pairs": int(len(common)),
                "f1_subset": float(b.mean()) if len(common) else np.nan,
                "f1_montage": float(a.mean()) if len(common) else np.nan,
                "delta_mean": float(b.mean() - a.mean()) if len(common) else np.nan,
                "delta_median": float(np.median(diffs)) if len(common) else np.nan,
                "p_raw": p_raw, "r_rb": r_rb, "identical": identical,
            })
    out = pd.DataFrame(rows)
    n_tests = int(out["p_raw"].notna().sum())
    out["p_bonf"] = (out["p_raw"] * n_tests).clip(upper=1.0)
    out.attrs["n_tests"] = n_tests
    return out


def ordered(ds: str) -> pd.DataFrame:
    """Electrode rows grouped by region (Figure 13's order), descending subset $F_1$ within
    each region -- the same order the per-electrode prose reports them in."""
    df = electrode_pairs(ds)
    blocks = [df[df.region == r].sort_values("f1_subset", ascending=False) for r in REGION_ORDER]
    return pd.concat(blocks, ignore_index=True), df.attrs["n_tests"]


def fmt_p(row) -> str:
    if row["identical"]:
        return r"n/a$^{\dagger}$"
    p = row["p_bonf"]
    if p != p:
        return "--"
    core = r"<0.001" if p < 0.001 else f"{p:.3f}"
    # \textbf has no effect on digits inside math mode; \mathbf does.
    return rf"$\mathbf{{{core}}}$" if p < 0.05 else f"${core}$"


def fmt_r(row) -> str:
    if row["identical"]:
        return r"n/a$^{\dagger}$"
    r = row["r_rb"]
    return "--" if r != r else f"${r:+.2f}$"


def dataset_block(ds: str, title: str) -> tuple[list[str], bool, int]:
    df, n_tests = ordered(ds)
    lines = [rf"\multicolumn{{8}}{{l}}{{\textit{{{title}, {n_tests} electrodes tested}}}} \\[2pt]"]
    used_dagger = False
    for region in REGION_ORDER:
        sub = df[df.region == region]
        for _, r in sub.iterrows():
            used_dagger = used_dagger or r["identical"]
            lines.append(
                f"{r['display']} & {REGION_LABEL[region]} & {r['n_pairs']} & "
                f"{P.fmt(r['f1_subset'])} & {P.fmt(r['f1_montage'])} & "
                f"${P.fmt_pp(r['delta_mean'])}$ & {fmt_p(r)} & {fmt_r(r)} \\\\"
            )
    return lines, used_dagger, n_tests


def main() -> None:
    raja_lines, raja_dagger, raja_n = dataset_block(
        "raja", f"{P.DSN['raja']} (EGI 128, {len(P.bps(P.load('exp1', 'raja')))} sessions)")
    cao_lines, cao_dagger, cao_n = dataset_block(
        "cao", f"Cao2018 (10--20, {len(P.bps(P.load('exp1', 'cao')))} sessions)")
    dagger_note = (
        r" $^{\dagger}$No Wilcoxon statistic exists: every matched session had an "
        r"identical subset and full-montage $F_1$ for this electrode."
        if (raja_dagger or cao_dagger) else ""
    )

    caption = (
        r"\caption{Experiment~1 per-electrode paired comparison of Proposed-Med (median "
        r"centre): each electrode scored inside its own region's self-contained subset "
        r"rerun against the same electrode scored inside the full-montage run, paired by "
        r"session. $F_1$ (Subset) and $F_1$ (Montage) are session means; $\Delta F_1$ is "
        r"the paired difference, Subset minus Montage, in percentage points, so a negative "
        r"value indicates lower performance in the subset rerun. Significance is a "
        r"two-tailed Wilcoxon signed-rank test, paired by session, with $p$ "
        rf"Bonferroni-corrected over every electrode tested within each dataset ({raja_n} for "
        rf"Internal, {cao_n} for Cao2018); $r_{{\mathrm{{rb}}}}$ is the matched-pairs rank-biserial "
        r"correlation, signed to match $\Delta F_1$. Adjusted $p<0.05$ is shown in bold. "
        r"Electrodes are grouped by the anatomical subset in Figure~\ref{fig:exp1_subset_per_electrode} "
        r"and ordered by descending subset $F_1$ within each region." + dagger_note + "}"
    )
    header = (r"Electrode & Region & $n$ & $F_1$ Subset (\%) & $F_1$ Montage (\%) & "
              r"$\Delta F_1$ (pp) & adjusted $p$ & $r_{\mathrm{rb}}$ \\")

    # A longtable, not a floating table: 42 electrode rows do not fit on one page, and
    # this table's exact per-electrode p-values/effect sizes are the primary result, so
    # they must appear in full rather than being cut by a float that is too tall for the
    # page.
    lines = [
        r"\begingroup", r"\footnotesize", r"\setlength{\tabcolsep}{4pt}",
        r"\begin{longtable}{llrrrrrr}",
        caption, r"\label{tab:exp1_subset_per_electrode_stats} \\",
        r"\toprule", header, r"\midrule", r"\endfirsthead",
        r"\multicolumn{8}{l}{\textit{(Table~\ref{tab:exp1_subset_per_electrode_stats} continued)}} \\",
        r"\toprule", header, r"\midrule", r"\endhead",
        r"\midrule", r"\multicolumn{8}{r}{\textit{continued on next page}} \\", r"\endfoot",
        r"\bottomrule", r"\endlastfoot",
        *raja_lines,
        r"\midrule",
        *cao_lines,
        r"\end{longtable}",
        r"\endgroup",
    ]
    P.write_tex(OUT, lines, SCRIPT)

    for ds, title in (("raja", "Internal"), ("cao", "Cao2018")):
        df, n_tests = ordered(ds)
        n_sig = int((df["p_bonf"] < 0.05).sum())
        print(f"{title}: {n_tests} electrodes tested, {n_sig} significant after Bonferroni correction")
        for _, r in df.iterrows():
            flag = "IDENTICAL" if r["identical"] else ("SIG" if r["p_bonf"] < 0.05 else "ns")
            print(f"  {r['display']:6s} {REGION_LABEL[r['region']]:9s} n={r['n_pairs']:2d} "
                  f"subset={r['f1_subset']*100:6.2f} montage={r['f1_montage']*100:6.2f} "
                  f"delta={r['delta_mean']*100:+6.2f} median_delta={r['delta_median']*100:+6.2f} "
                  f"p_raw={r['p_raw']:.4g} p_bonf={r['p_bonf']:.4g} r_rb={r['r_rb']:+.3f} {flag}")


if __name__ == "__main__":
    main()
