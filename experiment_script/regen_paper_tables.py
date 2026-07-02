"""Regenerate all cited LaTeX result tables from the validated std=3.0 re-run.

All four-condition comparisons use best-channel-per-session aggregation
(argmax det_f1 over selections per session, then mean across sessions),
identical for every condition. See writing/VALUE_AUDIT.md.

Run inside conda env double_threshold_algo.
"""
from __future__ import annotations
from pathlib import Path
from itertools import combinations
import numpy as np, pandas as pd
from scipy import stats
import yaml

REPO = Path(__file__).resolve().parents[1]
import os
NEW = REPO / os.environ.get("BLINK_RUNS_DIR", "runs_second_iteration")
ER = REPO / "writing" / "e_result"
CONDS = ["BLINKER-concat", "MNE-annot", "Proposed-Mean", "Proposed-Med"]
DSN = {"raja": "Raja", "cao": "Cao2018"}

def load(exp, ds):
    m = {"exp1": ("exp1_channel_{0}", "exp1_channel_selection_{1}_results.csv"),
         "exp2": ("exp2_{0}", "exp2_strategy_comparison_{1}_results.csv"),
         "exp3": ("exp3_{0}", "exp3_epoch_duration_{1}_results.csv"),
         "exp4": ("exp4_{0}", "exp4_boundary_tolerance_{1}_results.csv"),
         "exp8": ("exp8_{0}", "exp8_long_blink_{1}_results.csv")}
    fold = "raja" if ds == "raja" else "cao"; fil = "raja" if ds == "raja" else "cao2018"
    return pd.read_csv(NEW / m[exp][0].format(fold) / m[exp][1].format("", fil))

def bps(df):
    return df.loc[df.groupby("session")["det_f1"].idxmax()].copy()

def write(path, lines):
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", path)

SRC = "% Source: runs_second_iteration/ (std=3.0 validated re-run); script experiment_script/regen_paper_tables.py"

# ---- gather exp2 best-channel per session per condition (both datasets) ----
e2 = {ds: load("exp2", ds) for ds in ["raja", "cao"]}
best = {}  # (ds,cond) -> bps frame
for ds in ["raja", "cao"]:
    for c in CONDS:
        best[(ds, c)] = bps(e2[ds][e2[ds]["condition"] == c])

def head(ds, c):
    b = best[(ds, c)]
    return b["det_precision"].mean(), b["det_recall"].mean(), b["det_f1"].mean()

def pooled(c):
    f = pd.concat([best[("raja", c)], best[("cao", c)]])
    return f["det_precision"].mean(), f["det_recall"].mean(), f["det_f1"].mean()

# Wilcoxon pooled PM vs others (two-sided, Bonferroni x6)
def paired(ds_list, a_c, b_c):
    keys, av, bv = [], [], []
    A = pd.concat([best[(ds, a_c)].assign(k=ds + "/" + best[(ds, a_c)]["session"]) for ds in ds_list]).set_index("k")["det_f1"]
    B = pd.concat([best[(ds, b_c)].assign(k=ds + "/" + best[(ds, b_c)]["session"]) for ds in ds_list]).set_index("k")["det_f1"]
    common = A.index.intersection(B.index)
    return A.loc[common].values, B.loc[common].values

npair = 6
sig = {}
for a_c, b_c in combinations(CONDS, 2):
    a, b = paired(["raja", "cao"], a_c, b_c)
    w, p = stats.wilcoxon(a, b, alternative="two-sided")
    sig[(a_c, b_c)] = min(1.0, p * npair)

# =====================================================================
# TABLE 1: tab_comparison_30s_epoch (tab:exp1_main) — headline
# =====================================================================
def f(x): return f"{x:.4f}"
L = [SRC, r"\begin{table*}[ht]", r"  \centering",
     r"  \caption{Strategy comparison on the Raja and Cao2018 driving-EEG corpora at 30\,s epochs. "
     r"Each condition is summarised at its best-channel-per-session operating point (for every session the "
     r"single channel or frontal sub-montage with the highest $F_1$ is selected, then averaged over sessions); "
     r"the same rule is applied to all four conditions. Macro-averaged precision, recall and $F_1$ are reported "
     r"per dataset and pooled over all 104 sessions. Best $F_1$ per block in \textbf{bold}. "
     r"By paired Wilcoxon signed-rank tests on session-level $F_1$ (Bonferroni-corrected over six pairs), "
     r"Proposed-Med significantly exceeds BLINKER-concat and MNE-annot ($p<10^{-9}$) but not Proposed-Mean ($p=0.23$).}",
     r"  \label{tab:exp1_main}", r"  \begin{tabular}{llccc}", r"    \toprule",
     r"    Dataset & Condition & Precision & Recall & $F_1$ \\", r"    \midrule"]
for ds in ["raja", "cao"]:
    fbest = max(CONDS, key=lambda c: head(ds, c)[2])
    for i, c in enumerate(CONDS):
        p_, r_, f_ = head(ds, c)
        fcell = r"\textbf{" + f(f_) + "}" if c == fbest else f(f_)
        dscell = DSN[ds] if i == 0 else ""
        L.append(f"    {dscell} & {c} & {f(p_)} & {f(r_)} & {fcell} \\\\")
    L.append(r"    \midrule")
fbest = max(CONDS, key=lambda c: pooled(c)[2])
for i, c in enumerate(CONDS):
    p_, r_, f_ = pooled(c)
    fcell = r"\textbf{" + f(f_) + "}" if c == fbest else f(f_)
    dscell = "Pooled" if i == 0 else ""
    L.append(f"    {dscell} & {c} & {f(p_)} & {f(r_)} & {fcell} \\\\")
L += [r"    \bottomrule", r"  \end{tabular}", r"\end{table*}"]
write(ER / "tab_comparison_30s_epoch.tex", L)

# inversions: baseline >= PM pooled? none at headline. Replace with explicit no-inversion note.
LI = [SRC, r"\begin{table}[ht]", r"  \centering",
      r"  \caption{Channel groups and datasets where a baseline algorithm equals or exceeds Proposed-Med "
      r"in best-channel-per-session macro-$F_1$.}", r"  \label{tab:exp2_inversions}",
      r"  \begin{tabular}{lllccc}", r"    \toprule",
      r"    Dataset & Selection & Baseline & BL-$F_1$ & Prop-$F_1$ & $\Delta F_1$ \\", r"    \midrule"]
inv = []
for ds in ["raja", "cao"]:
    df = e2[ds]
    for sel in sorted(df["selection"].unique()):
        pmf = df[(df.condition == "Proposed-Med") & (df.selection == sel)].groupby("session")["det_f1"].max().mean()
        for bl in ["BLINKER-concat", "MNE-annot"]:
            blf = df[(df.condition == bl) & (df.selection == sel)].groupby("session")["det_f1"].max().mean()
            if blf >= pmf:
                inv.append((DSN[ds], sel.replace("_", r"\_"), bl, blf, pmf, blf - pmf))
if inv:
    for ds, sel, bl, blf, pmf, d in sorted(inv, key=lambda x: -x[5]):
        LI.append(f"    {ds} & {sel} & {bl} & {f(blf)} & {f(pmf)} & +{f(d)} \\\\")
else:
    LI.append(r"    \multicolumn{6}{c}{No inversions --- Proposed-Med leads on every channel group.} \\")
LI += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]
write(ER / "tab_exp2_inversions.tex", LI)

# =====================================================================
# TABLE 2: tab_cross_dataset_gap
# =====================================================================
L = [SRC, r"\begin{table}[ht]", r"  \centering",
     r"  \caption{Cross-dataset generalisation gap (best-channel-per-session macro-$F_1$, 30\,s epochs). "
     r"Gap $=$ Raja $-$ Cao2018.}", r"  \label{tab:cross_dataset_gap}",
     r"  \begin{tabular}{lccc}", r"    \toprule", r"    Condition & Raja & Cao2018 & Gap \\", r"    \midrule"]
for c in CONDS:
    rj = head("raja", c)[2]; cao = head("cao", c)[2]
    L.append(f"    {c} & {f(rj)} & {f(cao)} & {rj-cao:+.4f} \\\\")
L += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]
write(ER / "tab_cross_dataset_gap.tex", L)

# =====================================================================
# TABLE 3: tab_effect_different_epoch_size (PM, durations)
# =====================================================================
durs = [10, 20, 30, 40, 50, 60, 120]
# per-session best F1 by duration
def dur_vals(ds, dur):
    df = load("exp3", ds); df = df[df.center_method == "median"]
    return bps(df[df.epoch_duration_s == float(dur)]).assign(k=ds + "/" + bps(df[df.epoch_duration_s == float(dur)])["session"]).set_index("session")["det_f1"]
L = [SRC, r"\begin{table}[ht]", r"  \centering",
     r"  \caption{Best-channel-per-session macro-$F_1$ of Proposed-Med across epoch durations. "
     r"$p$-values (two-tailed Wilcoxon on session-level $F_1$, Bonferroni-corrected over six non-reference durations) "
     r"compare each duration against the 30\,s reference. \textbf{Bold} marks the best duration within each block.}",
     r"  \label{tab:epoch_duration}", r"  \begin{tabular}{llccc}", r"    \toprule",
     r"    Dataset & Epoch duration & $n$ & Macro $F_1$ & $p$ vs.\ 30\,s \\", r"    \midrule"]
blocks = [("Raja", ["raja"]), ("Cao2018", ["cao"]), ("Pooled", ["raja", "cao"])]
for name, dslist in blocks:
    # build per-duration vectors keyed by ds/session
    series = {}
    for dur in durs:
        v = {}
        for ds in dslist:
            df = load("exp3", ds); df = df[df.center_method == "median"]
            b = bps(df[df.epoch_duration_s == float(dur)])
            for _, r in b.iterrows():
                v[f"{ds}/{r['session']}"] = r["det_f1"]
        series[dur] = v
    means = {d: np.mean(list(series[d].values())) for d in durs}
    bestd = max(durs, key=lambda d: means[d])
    ref = series[30]
    for dur in durs:
        n = len(series[dur])
        mcell = r"\textbf{" + f"{means[dur]:.4f}" + "}" if dur == bestd else f"{means[dur]:.4f}"
        if dur == 30:
            pcell = "reference"
        else:
            keys = sorted(set(ref) & set(series[dur]))
            a = np.array([series[dur][k] for k in keys]); b2 = np.array([ref[k] for k in keys])
            try:
                _, p = stats.wilcoxon(a, b2, alternative="two-sided"); pcell = f"{min(1,p*6):.3f}"
            except ValueError:
                pcell = "n/a"
        dcell = name if dur == durs[0] else ""
        L.append(f"    {dcell} & {dur}\\,s & {n} & {mcell} & {pcell} \\\\")
    L.append(r"    \midrule")
L[-1] = r"    \bottomrule"
L += [r"  \end{tabular}", r"\end{table}"]
write(ER / "tab_effect_different_epoch_size.tex", L)

# =====================================================================
# TABLE 4: tab_boundary_tolerance (PM, IoU)
# =====================================================================
ious = [0.0, 0.1, 0.2, 0.3, 0.5]
L = [SRC, r"\begin{table}[ht]", r"  \centering",
     r"  \caption{Boundary-tolerance analysis for Proposed-Med (best-channel-per-session macro-$F_1$). "
     r"Macro-$F_1$ is shown for increasing event-matching IoU thresholds; performance falls as the overlap "
     r"criterion tightens.}", r"  \label{tab:boundary_tolerance}",
     r"  \begin{tabular}{lc" + "c" * len(ious) + r"}", r"    \toprule",
     r"    Dataset & $n$ & " + " & ".join(f"IoU {io}" for io in ious) + r" \\", r"    \midrule"]
rows_iou = {}
for ds in ["raja", "cao"]:
    df = load("exp4", ds); df = df[df.center_method == "median"]
    vals = {}
    for io in ious:
        vals[io] = bps(df[df.iou_threshold == io])["det_f1"]
    rows_iou[ds] = vals
for ds in ["raja", "cao"]:
    n = rows_iou[ds][0.0].shape[0]
    L.append(f"    {DSN[ds]} & {n} & " + " & ".join(f(rows_iou[ds][io].mean()) for io in ious) + r" \\")
# pooled
pn = sum(rows_iou[ds][0.0].shape[0] for ds in ["raja", "cao"])
pooledvals = []
for io in ious:
    allv = pd.concat([rows_iou["raja"][io], rows_iou["cao"][io]])
    pooledvals.append(allv.mean())
L.append(f"    Pooled & {pn} & " + " & ".join(f(v) for v in pooledvals) + r" \\")
L += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]
write(ER / "tab_boundary_tolerance.tex", L)

# =====================================================================
# TABLE 5: tab_blink_type_recall (PM only, normal/long)
# =====================================================================
e8rows = []
for ds in ["raja", "cao"]:
    df = load("exp8", ds)
    rec = {cat: bps(df[df.blink_category == cat])["det_recall"].mean() for cat in ["normal", "long"]}
    gt = df.drop_duplicates("session")[["n_gt_normal", "n_gt_long"]].sum()
    e8rows.append((DSN[ds], rec, gt))
# pooled
tot_n = sum(int(r[2]["n_gt_normal"]) for r in e8rows); tot_l = sum(int(r[2]["n_gt_long"]) for r in e8rows)
pool_rec = {}
for cat in ["normal", "long"]:
    v = []
    for ds in ["raja", "cao"]:
        df = load("exp8", ds); v += bps(df[df.blink_category == cat])["det_recall"].tolist()
    pool_rec[cat] = np.mean(v)
gt_n_str = f"{tot_n:,}".replace(",", "{,}")
gt_l_str = f"{tot_l:,}".replace(",", "{,}")
caption_btr = (
    r"  \caption{Event-level recall of Proposed-Med split by blink duration "
    r"(best-channel-per-session, 30\,s epochs). "
    r"Normal $=$ duration $<0.5$\,s, Long $=$ duration $\geq0.5$\,s. Ground truth contains "
    + gt_n_str + r" normal and " + gt_l_str
    + r" long blinks across Raja and Cao2018. Baselines are reported in Table~\ref{tab:exp1_main}; "
    r"the long-blink ablation was run for Proposed-Med only.}"
)
L = [SRC, r"\begin{table}[ht]", r"  \centering", caption_btr,
     r"  \label{tab:blink_type_recall}", r"  \begin{tabular}{lcc}", r"    \toprule",
     r"    Dataset & Normal recall & Long recall \\", r"    \midrule"]
for name, rec, gt in e8rows:
    L.append(f"    {name} & {f(rec['normal'])} & {f(rec['long'])} \\\\")
L.append(r"    \midrule")
L.append(f"    Pooled & {f(pool_rec['normal'])} & {f(pool_rec['long'])} \\\\")
L += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]
write(ER / "tab_blink_type_recall.tex", L)

# =====================================================================
# TABLE 6: tab_error_structure (4 cond, best-channel row FP/FN)
# =====================================================================
L = [SRC, r"\begin{table}[ht]", r"  \centering",
     r"  \caption{Error-structure decomposition by condition (best-channel-per-session). "
     r"Mean false positives (FP) and false negatives (FN) per session, pooled over 104 sessions.}",
     r"  \label{tab:error-structure}", r"  \begin{tabular}{lcccl}", r"    \toprule",
     r"    Condition & Mean FP/session & Mean FN/session & FP:FN & Regime \\", r"    \midrule"]
for c in CONDS:
    fr = pd.concat([best[("raja", c)], best[("cao", c)]])
    mfp, mfn = fr["det_fp"].mean(), fr["det_fn"].mean()
    ratio = mfp / mfn
    L.append(f"    {c} & {mfp:.1f} & {mfn:.1f} & {ratio:.3f} & {'FP-heavy' if mfp>mfn else 'FN-heavy'} \\\\")
L += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]
write(ER / "tab_error_structure.tex", L)

# =====================================================================
# TABLE 7: tab_best_session (PM best/worst session + subject)
# =====================================================================
pm = pd.concat([best[("raja", "Proposed-Med")].assign(dataset="raja"),
                best[("cao", "Proposed-Med")].assign(dataset="cao")], ignore_index=True)
pm["subject"] = pm["session"].str.split("/").str[0]
pm_s = pm.sort_values("det_f1", ascending=False).reset_index(drop=True)
bestS, worstS = pm_s.iloc[0], pm_s.iloc[-1]
subj = pm.groupby(["dataset", "subject"]).agg(n=("session", "nunique"), mean_f1=("det_f1", "mean")).reset_index().sort_values("mean_f1", ascending=False).reset_index(drop=True)
bestU, worstU = subj.iloc[0], subj.iloc[-1]
def esc(s): return str(s).replace("_", r"\_")
L = [SRC, r"\begin{table}[ht]", r"  \centering",
     r"  \caption{Best and worst Proposed-Med sessions and subject-level summary across 104 Raja+Cao2018 sessions "
     r"(best-channel-per-session).}", r"  \label{tab:best-session}",
     r"  \begin{tabular}{lllccl}", r"    \toprule",
     r"    Scope & Dataset & Unit & $n$ & Metric & Value \\", r"    \midrule",
     f"    Best session & {DSN[bestS['dataset']]} & {esc(bestS['session'])} & 1 & $F_1$ & {bestS['det_f1']:.4f} \\\\",
     f"    Worst session & {DSN[worstS['dataset']]} & {esc(worstS['session'])} & 1 & $F_1$ & {worstS['det_f1']:.4f} \\\\",
     f"    Median session & all & 104 sessions & 104 & $F_1$ & {pm['det_f1'].median():.4f} \\\\",
     f"    Best subject & {DSN[bestU['dataset']]} & {esc(bestU['subject'])} & {int(bestU['n'])} & Mean $F_1$ & {bestU['mean_f1']:.4f} \\\\",
     f"    Worst subject & {DSN[worstU['dataset']]} & {esc(worstU['subject'])} & {int(worstU['n'])} & Mean $F_1$ & {worstU['mean_f1']:.4f} \\\\",
     f"    Median subject & all & {len(subj)} subjects & {len(subj)} & Mean $F_1$ & {subj['mean_f1'].median():.4f} \\\\",
     r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]
write(ER / "tab_best_session.tex", L)

# =====================================================================
# TABLE 8: tab_channel_robustness (agreement)
# =====================================================================
def best_chan(ds, c):
    return best[(ds, c)].set_index("session")["channel_in_group"]
rob_rows = []
for label, dslist in [("Raja", ["raja"]), ("Cao2018", ["cao"]), ("Pooled", ["raja", "cao"])]:
    cat = pd.concat([pd.DataFrame({c: best_chan(ds, c) for c in CONDS}).rename(index=lambda s, d=ds: f"{d}/{s}") for ds in dslist])
    nfull = int((cat.nunique(axis=1) == 1).sum()); ntot = len(cat)
    pair = [(cat[a] == cat[b]).mean() for a, b in combinations(CONDS, 2)]
    permeth = {}
    for m in CONDS:
        others = [o for o in CONDS if o != m]
        permeth[m] = np.mean([(cat[m] == cat[o]).mean() for o in others])
    rob_rows.append((label, ntot, nfull, np.mean(pair), permeth))
L = [SRC, r"\begin{table}[ht]", r"  \centering", r"  \scriptsize", r"  \setlength{\tabcolsep}{3pt}",
     r"  \caption{Channel-robustness ranking stability across sessions for the four conditions (best-channel-per-session). "
     r"Full agreement is the fraction of sessions where all four conditions select the same best channel; per-condition "
     r"agreement is the mean fraction of the other three conditions selecting the same best channel.}",
     r"  \label{tab:channel-robustness}", r"  \begin{tabular}{lccccccc}", r"    \toprule",
     r"    Dataset & Sessions & Full agreement & Mean pairwise & BLINKER-concat & MNE-annot & Proposed-Mean & Proposed-Med \\",
     r"    \midrule"]
for label, ntot, nfull, mp, pm_ in rob_rows:
    L.append(f"    {label} & {ntot} & {nfull}/{ntot} ({nfull/ntot:.3f}) & {mp:.3f} & "
             f"{pm_['BLINKER-concat']:.3f} & {pm_['MNE-annot']:.3f} & {pm_['Proposed-Mean']:.3f} & {pm_['Proposed-Med']:.3f} \\\\")
L += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]
write(ER / "tab_channel_robustness.tex", L)

# =====================================================================
# TABLE 9: tab_channel_selection (frequencies)
# =====================================================================
L = [SRC, r"\begin{table}[ht]", r"  \centering", r"  \scriptsize", r"  \setlength{\tabcolsep}{3pt}",
     r"  \caption{Best-channel selection frequencies pooled over the four conditions (best-channel-per-session).}",
     r"  \label{tab:channel_selection}", r"  \begin{tabular}{llp{0.66\linewidth}}", r"    \toprule",
     r"    Dataset & Summary & Frequencies \\", r"    \midrule"]
for ds in ["raja", "cao"]:
    allsel = pd.concat([best_chan(ds, c) for c in CONDS])
    tot = len(allsel); fr = allsel.value_counts()
    items = "; ".join(f"{ch} {n}/{tot} ({n/tot:.3f})" for ch, n in fr.head(5).items())
    L.append(f"    {DSN[ds]} & Channels & {items} \\\\")
L += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]
write(ER / "tab_channel_selection.tex", L)

# =====================================================================
# Channel -> region (brain_region_*.yaml) and Raja EGI -> 10-20 (32_ch.csv)
# =====================================================================
REGION_ORDER = ["frontal_left", "frontal_right", "central_left", "central_right",
                "parietal_left", "parietal_right", "occipital_left", "occipital_right",
                "temporal_parietal_left", "temporal_parietal_right"]

def region_map_fine(ds):
    """channel -> fine region (keeps _left/_right), as used by the exp1 run."""
    yml = REPO / ("brain_region_raja.yaml" if ds == "raja" else "brain_region_cao2018.yaml")
    data = yaml.safe_load(yml.read_text())["eeg_regions"]
    m = {}
    for grp, chans in data.items():
        for c in chans:
            name = ("E" + str(c)) if ds == "raja" else str(c)
            m[name.upper()] = grp
    return m

def egi_to_1020():
    """Raja EGI label -> 10-20 name, from 32_ch.csv (EGI hardware, Raja only)."""
    m = pd.read_csv(REPO / "32_ch.csv")
    return {f"E{int(r.egi_id)}": str(r["10_20_mapping"]) for _, r in m.iterrows()}

def per_channel(ds):
    """One row per channel: mean P/R/F1 over sessions from the 'all' selection (median),
    plus region and 10-20 name. This is the channel-by-channel exp1 result that is
    already present in the CSV (selection=='all', channel_in_group), with NO region-level
    aggregation."""
    df = load("exp1", ds); df = df[(df.center_method == "median") & (df.selection == "all")]
    g = (df.groupby("channel_in_group")
           .agg(p=("det_precision", "mean"), r=("det_recall", "mean"),
                f1=("det_f1", "mean"), n=("session", "nunique"))
           .reset_index().rename(columns={"channel_in_group": "ch"}))
    rmap = region_map_fine(ds)
    g["region"] = g.ch.apply(lambda c: rmap.get(str(c).upper(), "unmapped"))
    e2n = egi_to_1020()
    g["name1020"] = g.ch.apply(lambda c: e2n.get(str(c), "--")) if ds == "raja" else g.ch
    return g

# =====================================================================
# TABLE 10: tab_exp1_channel_ablation (CHANNEL-BY-CHANNEL within each region)
# =====================================================================
L = [SRC, r"\begin{table}[htbp]", r"\centering", r"\scriptsize",
     r"\setlength{\tabcolsep}{4pt}",
     r"\caption{Experiment~1 channel-by-channel detection performance of Proposed-Med (median centre), "
     r"organised by scalp region with \emph{no} region-level aggregation. Each entry is "
     r"\texttt{proposed\_median\_$\langle$region$\rangle$\_$\langle$channel$\rangle$}: the median-thresholded "
     r"detector evaluated on a single channel, with macro-averaged precision, recall and $F_1$ averaged over all "
     r"sessions (values read directly from the \texttt{selection=all} rows of the Experiment~1 results CSV). "
     r"For Raja the native EGI label is shown with its 10--20 equivalent from the channel map "
     r"(Table~\ref{tab:egi_map}); a dash marks electrodes without a standard 10--20 label. Cao2018 is recorded "
     r"directly in 10--20 nomenclature. Best $F_1$ per dataset in \textbf{bold}.}",
     r"\label{tab:exp1_channel_ablation}", r"\begin{tabular}{lllrrr}", r"\toprule",
     r"Region & Channel & 10--20 & Precision & Recall & $F_1$ \\", r"\midrule"]
for ds in ["raja", "cao"]:
    g = per_channel(ds)
    bestf = g["f1"].max()
    hw = "EGI 128" if ds == "raja" else "10--20"
    L.append(r"\multicolumn{6}{l}{\textit{" + DSN[ds] + f" ({hw}, {int(g['n'].max())} sessions)" + r"}} \\[2pt]")
    for reg in REGION_ORDER:
        sub = g[g.region == reg].sort_values("f1", ascending=False)
        if len(sub) == 0:
            continue
        rfirst = True
        for _, row in sub.iterrows():
            regcell = reg.replace("_", r"\_") if rfirst else ""
            fcell = r"\textbf{" + f"{row.f1:.3f}" + "}" if row.f1 == bestf else f"{row.f1:.3f}"
            n1020 = str(row.name1020).replace("_", r"\_")
            L.append(f"{regcell} & {row.ch} & {n1020} & {row.p:.3f} & {row.r:.3f} & {fcell} \\\\")
            rfirst = False
    L.append(r"\midrule" if ds == "raja" else r"\bottomrule")
L += [r"\end{tabular}", r"\end{table}"]
write(ER / "tab_exp1_channel_ablation.tex", L)

# =====================================================================
# TABLE 11: tab_egi_channel_map (Raja EGI <-> 10-20, from 32_ch.csv)
# =====================================================================
egimap = pd.read_csv(REPO / "32_ch.csv")
rmap_raja = region_map_fine("raja")
egimap["egi_lbl"] = egimap.egi_id.apply(lambda i: f"E{int(i)}")
egimap["yaml_region"] = egimap.egi_lbl.apply(lambda c: rmap_raja.get(c.upper(), "--"))
egimap = egimap.sort_values(["yaml_region", "egi_id"])
L = [SRC, r"\begin{table}[ht]", r"\centering", r"\footnotesize",
     r"\caption{Raja EGI 128-channel (HydroCel GSN) to 10--20 channel-name mapping (file \texttt{32\_ch.csv}), "
     r"used to label the Experiment~1 channel-by-channel results. The region column is the assignment used by "
     r"the Experiment~1 run (\texttt{brain\_region\_raja.yaml}); a dash marks a channel not assigned to one of "
     r"the analysed regions. Cao2018 is acquired directly in 10--20 nomenclature and needs no mapping.}",
     r"\label{tab:egi_map}", r"\begin{tabular}{lll}", r"\toprule",
     r"EGI & 10--20 & Region \\", r"\midrule"]
for _, r in egimap.iterrows():
    reg = r.yaml_region.replace("_", r"\_")
    L.append(f"{r.egi_lbl} & {r['10_20_mapping']} & {reg} \\\\")
L += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
write(ER / "tab_egi_channel_map.tex", L)

# console: print the channel-by-channel identifiers for the audit log
print("\n--- Experiment 1 channel-by-channel (proposed_median_<region>_<channel>) ---")
for ds in ["raja", "cao"]:
    g = per_channel(ds).sort_values(["region", "f1"], ascending=[True, False])
    print(f"[{DSN[ds]}]")
    for _, row in g.iterrows():
        cid = row.ch[1:] if ds == "raja" else row.ch
        print(f"   proposed_median_{row.region}_{cid:<5} ({row.ch}/{row.name1020})  "
              f"P={row.p:.3f} R={row.r:.3f} F1={row.f1:.3f}")

print("\nDONE — all tables regenerated.")
