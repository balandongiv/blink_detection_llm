"""Authoritative recomputation of all headline numbers for the academic writing task.

Source of truth: runs_second_iteration/ (validated std=3.0 re-run). Baseline: runs/.

Headline aggregation (matches HANDOFF_std30_academic_writing.md sec.2/5.1e):
  best-channel-per-session = for each (session, condition) take the row with the
  maximum det_f1 over all available selections, then average across sessions.
  Precision/recall reported are taken from that same argmax-F1 row.

Outputs:
  - prints a structured report
  - writes writing/NUMBERS_std30.md  (frozen source of truth for all prose/tables)

Run inside conda env double_threshold_algo.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
import yaml

REPO = Path(__file__).resolve().parents[1]
import os
NEW = REPO / os.environ.get("BLINK_RUNS_DIR", "runs_second_iteration")
BASE = REPO / "runs"
OUT_MD = REPO / "writing" / "NUMBERS_std30.md"

CONDS = ["Proposed-Med", "Proposed-Mean", "BLINKER-concat", "MNE-annot"]
DS_NICE = {"raja": "Raja", "cao": "Cao2018"}

# ---------- file locators ----------
def f_exp(run, exp, ds):
    names = {
        "exp1": ("exp1_channel_{0}", "exp1_channel_selection_{1}_results.csv"),
        "exp2": ("exp2_{0}", "exp2_strategy_comparison_{1}_results.csv"),
        "exp3": ("exp3_{0}", "exp3_epoch_duration_{1}_results.csv"),
        "exp4": ("exp4_{0}", "exp4_boundary_tolerance_{1}_results.csv"),
        "exp5": ("exp5_{0}", "exp5_nmin_sensitivity_{1}_results.csv"),
        "exp7": ("exp7_{0}", "exp7_epoch_health_{1}_results.csv"),
        "exp8": ("exp8_{0}", "exp8_long_blink_{1}_results.csv"),
    }
    folder_ds = "raja" if ds == "raja" else "cao"
    file_ds = "raja" if ds == "raja" else "cao2018"
    # exp1 folder uses exp1_channel_raja / exp1_channel_cao
    folder = names[exp][0].format(folder_ds)
    fname = names[exp][1].format("", file_ds)
    return run / folder / fname

def load(run, exp, ds):
    return pd.read_csv(f_exp(run, exp, ds))

# ---------- helpers ----------
def best_per_session(df):
    """Return one row per session: the argmax det_f1 row (keeps P,R,F1,fp,fn,tp,channel,selection)."""
    idx = df.groupby("session")["det_f1"].idxmax()
    return df.loc[idx].copy()

def headline(df, cond_filter):
    """best-channel-per-session: mean over sessions of per-session max det_f1, plus P/R from argmax row."""
    d = cond_filter(df)
    bps = best_per_session(d)
    return dict(
        f1=bps["det_f1"].mean(),
        precision=bps["det_precision"].mean(),
        recall=bps["det_recall"].mean(),
        n=bps["session"].nunique(),
        bps=bps,
    )

def cond_eq(name):
    return lambda df: df[df["condition"] == name]

def median_filter(df):
    return df[df["center_method"] == "median"]

def mean_filter(df):
    return df[df["center_method"] == "mean"]

# region map
def load_region_map(ds):
    yml = REPO / ("brain_region_raja.yaml" if ds == "raja" else "brain_region_cao2018.yaml")
    data = yaml.safe_load(yml.read_text())["eeg_regions"]
    ch2group = {}
    for group, chans in data.items():
        for c in chans:
            name = str(c)
            if ds == "raja":
                name = "E" + name
            ch2group[name.upper()] = group
    return ch2group

COARSE = lambda g: g.rsplit("_", 1)[0] if g.endswith(("_left", "_right")) else g

report = []
def P(*a):
    line = " ".join(str(x) for x in a)
    print(line)
    report.append(line)

def H(t):
    P("\n## " + t)

# =====================================================================
# 1. EXP2 four-condition headline + cross-dataset
# =====================================================================
H("EXP2 — four-condition headline (best-channel-per-session)")
exp2_head = {}  # (run,ds,cond) -> dict
for run_name, run in [("new", NEW), ("base", BASE)]:
    for ds in ["raja", "cao"]:
        df = load(run, "exp2", ds)
        for cond in CONDS:
            h = headline(df, cond_eq(cond))
            exp2_head[(run_name, ds, cond)] = h
        P(f"[{run_name}] {DS_NICE[ds]}:")
        for cond in CONDS:
            h = exp2_head[(run_name, ds, cond)]
            P(f"    {cond:15s} F1={h['f1']:.4f}  P={h['precision']:.4f}  R={h['recall']:.4f}  n={h['n']}")

# pooled (104 sessions) new run
H("EXP2 — pooled (Raja+Cao, 104 sessions), new run")
pooled = {}
for cond in CONDS:
    vals_f1, vals_p, vals_r = [], [], []
    for ds in ["raja", "cao"]:
        bps = exp2_head[("new", ds, cond)]["bps"]
        vals_f1 += bps["det_f1"].tolist()
        vals_p += bps["det_precision"].tolist()
        vals_r += bps["det_recall"].tolist()
    pooled[cond] = dict(f1=np.mean(vals_f1), p=np.mean(vals_p), r=np.mean(vals_r), n=len(vals_f1))
    P(f"    {cond:15s} F1={pooled[cond]['f1']:.4f}  P={pooled[cond]['p']:.4f}  R={pooled[cond]['r']:.4f}  n={pooled[cond]['n']}")

H("EXP2 — cross-dataset gap (Raja - Cao), new run")
for cond in CONDS:
    r = exp2_head[("new", "raja", cond)]["f1"]
    c = exp2_head[("new", "cao", cond)]["f1"]
    P(f"    {cond:15s} Raja={r:.4f}  Cao={c:.4f}  gap(R-C)={r-c:+.4f}")

# =====================================================================
# 2. Channel-selection frequency (argmax-F1 channel per session/condition)
# =====================================================================
H("CHANNEL SELECTION FREQUENCY (new run, exp2 argmax-F1 channel)")
chan_sel = {}
for ds in ["raja", "cao"]:
    df = load(NEW, "exp2", ds)
    P(f"[{DS_NICE[ds]}]")
    per_cond_best = {}
    for cond in CONDS:
        bps = best_per_session(df[df["condition"] == cond])
        per_cond_best[cond] = bps.set_index("session")["channel_in_group"]
    # frequency pooled over 4 methods
    allsel = pd.concat([per_cond_best[c] for c in CONDS])
    freq = allsel.value_counts()
    tot = len(allsel)
    P(f"    pooled selections n={tot}: " + ", ".join(f"{ch}={n}({100*n/tot:.1f}%)" for ch, n in freq.head(6).items()))
    # PM vs PMean agreement
    pm = per_cond_best["Proposed-Med"]; pmean = per_cond_best["Proposed-Mean"]
    common = pm.index.intersection(pmean.index)
    agree = (pm.loc[common] == pmean.loc[common]).mean()
    P(f"    Proposed-Med vs Proposed-Mean same channel: {100*agree:.1f}% ({(pm.loc[common]==pmean.loc[common]).sum()}/{len(common)})")
    # all four agreement
    cat = pd.DataFrame({c: per_cond_best[c] for c in CONDS})
    allfour = (cat.nunique(axis=1) == 1).mean()
    P(f"    all-four agree: {100*allfour:.1f}% ({(cat.nunique(axis=1)==1).sum()}/{len(cat)})")
    chan_sel[ds] = dict(freq=freq, tot=tot, pm_pmean=agree, allfour=allfour)

# =====================================================================
# 3. Error structure (best-channel row fp/fn per session)
# =====================================================================
H("ERROR STRUCTURE (mean per-session FP/FN at best-channel row, new run, pooled)")
err = {}
for cond in CONDS:
    fps, fns = [], []
    for ds in ["raja", "cao"]:
        bps = exp2_head[("new", ds, cond)]["bps"]
        fps += bps["det_fp"].tolist(); fns += bps["det_fn"].tolist()
    mfp, mfn = np.mean(fps), np.mean(fns)
    err[cond] = dict(fp=mfp, fn=mfn, ratio=mfp / mfn if mfn else np.inf)
    P(f"    {cond:15s} FP={mfp:.1f}  FN={mfn:.1f}  FP:FN={err[cond]['ratio']:.3f}  regime={'FP-heavy' if mfp>mfn else 'FN-heavy'}")

# =====================================================================
# 4. Best/worst session + subject (Proposed-Med, new run, pooled)
# =====================================================================
H("BEST/WORST SESSION + SUBJECT (Proposed-Med, new run, pooled 104)")
pm_rows = []
for ds in ["raja", "cao"]:
    bps = exp2_head[("new", ds, "Proposed-Med")]["bps"].copy()
    bps["dataset"] = ds
    pm_rows.append(bps)
pm_all = pd.concat(pm_rows, ignore_index=True)
pm_all["subject"] = pm_all["session"].str.split("/").str[0]
pm_all_sorted = pm_all.sort_values("det_f1", ascending=False).reset_index(drop=True)
P(f"    n sessions={len(pm_all)}  F1 range {pm_all['det_f1'].min():.4f}..{pm_all['det_f1'].max():.4f}  median={pm_all['det_f1'].median():.4f}")
best = pm_all_sorted.iloc[0]; worst = pm_all_sorted.iloc[-1]
P(f"    best session: {DS_NICE[best['dataset']]} {best['session']} F1={best['det_f1']:.4f} (ch {best['channel_in_group']})")
P(f"    worst session: {DS_NICE[worst['dataset']]} {worst['session']} F1={worst['det_f1']:.4f} (ch {worst['channel_in_group']}, tp={int(worst['det_tp'])} fp={int(worst['det_fp'])} fn={int(worst['det_fn'])})")
subj = pm_all.groupby(["dataset", "subject"]).agg(n=("session", "nunique"), mean_f1=("det_f1", "mean")).reset_index().sort_values("mean_f1", ascending=False)
P(f"    n subjects={len(subj)}  subject mean-F1 median={subj['mean_f1'].median():.4f}")
bs = subj.iloc[0]; ws = subj.iloc[-1]
P(f"    best subject: {DS_NICE[bs['dataset']]} {bs['subject']} mean_f1={bs['mean_f1']:.4f} ({int(bs['n'])} sess)")
P(f"    worst subject: {DS_NICE[ws['dataset']]} {ws['subject']} mean_f1={ws['mean_f1']:.4f} ({int(ws['n'])} sess)")

# =====================================================================
# 5. EXP3 epoch duration (PM best-channel-per-session)
# =====================================================================
H("EXP3 epoch duration (Proposed-Med best-channel-per-session)")
exp3 = {}
for ds in ["raja", "cao"]:
    df = load(NEW, "exp3", ds)
    df = median_filter(df)
    row = {}
    for dur in sorted(df["epoch_duration_s"].unique()):
        sub = df[df["epoch_duration_s"] == dur]
        row[dur] = best_per_session(sub)["det_f1"].mean()
    exp3[ds] = row
    P(f"    {DS_NICE[ds]}: " + ", ".join(f"{int(d)}s={v:.4f}" for d, v in row.items()))
# pooled
P("    Pooled (104):")
durs = sorted(set(exp3["raja"]) & set(exp3["cao"]))
exp3_pooled = {}
for dur in durs:
    vals = []
    for ds in ["raja", "cao"]:
        df = median_filter(load(NEW, "exp3", ds))
        sub = df[df["epoch_duration_s"] == dur]
        vals += best_per_session(sub)["det_f1"].tolist()
    exp3_pooled[dur] = np.mean(vals)
P("      " + ", ".join(f"{int(d)}s={v:.4f}" for d, v in exp3_pooled.items()))

# =====================================================================
# 6. EXP4 boundary tolerance (PM best-channel-per-session by IoU)
# =====================================================================
H("EXP4 boundary tolerance / IoU (Proposed-Med best-channel-per-session)")
exp4 = {}
for ds in ["raja", "cao"]:
    df = median_filter(load(NEW, "exp4", ds))
    row = {}
    for iou in sorted(df["iou_threshold"].unique()):
        sub = df[df["iou_threshold"] == iou]
        row[iou] = best_per_session(sub)["det_f1"].mean()
    exp4[ds] = row
    P(f"    {DS_NICE[ds]}: " + ", ".join(f"iou{io}={v:.4f}" for io, v in row.items()))

# =====================================================================
# 7. EXP5 n_min sensitivity (PM best-channel-per-session)
# =====================================================================
H("EXP5 n_min sensitivity (Proposed-Med best-channel-per-session)")
exp5 = {}
for ds in ["raja", "cao"]:
    df = median_filter(load(NEW, "exp5", ds))
    row = {}
    for nm in sorted(df["min_flagged_epochs"].unique()):
        sub = df[df["min_flagged_epochs"] == nm]
        row[nm] = best_per_session(sub)["det_f1"].mean()
    exp5[ds] = row
    P(f"    {DS_NICE[ds]}: " + ", ".join(f"nmin{int(n)}={v:.4f}" for n, v in row.items()))

# =====================================================================
# 8. EXP7 epoch-health effect (PM best-channel-per-session, health on/off)
# =====================================================================
H("EXP7 epoch-health effect (Proposed-Med best-channel-per-session)")
exp7 = {}
for ds in ["raja", "cao"]:
    df = median_filter(load(NEW, "exp7", ds))
    on = best_per_session(df[df["use_epoch_health"] == True])["det_f1"].mean()
    off = best_per_session(df[df["use_epoch_health"] == False])["det_f1"].mean()
    exp7[ds] = dict(on=on, off=off, delta=on - off)
    P(f"    {DS_NICE[ds]}: health-on={on:.4f}  health-off={off:.4f}  delta={on-off:+.4f}")

# =====================================================================
# 9. EXP8 long-blink (PM normal vs long recall + F1, GT counts)
# =====================================================================
H("EXP8 long-blink (Proposed-Med best-channel-per-session by category)")
exp8 = {}
for ds in ["raja", "cao"]:
    df = load(NEW, "exp8", ds)  # already median-only
    cats = {}
    for cat in ["all", "normal", "long"]:
        sub = df[df["blink_category"] == cat]
        bps = best_per_session(sub)
        cats[cat] = dict(recall=bps["det_recall"].mean(), f1=bps["det_f1"].mean(), prec=bps["det_precision"].mean())
    # GT counts: dedupe by session (n_gt_* identical across channels)
    gt = df.drop_duplicates("session")[["n_gt_total", "n_gt_normal", "n_gt_long"]].sum()
    exp8[ds] = dict(cats=cats, gt=gt)
    P(f"    {DS_NICE[ds]}: GT total={int(gt['n_gt_total'])} normal={int(gt['n_gt_normal'])} long={int(gt['n_gt_long'])} ({100*gt['n_gt_long']/gt['n_gt_total']:.1f}% long)")
    for cat in ["all", "normal", "long"]:
        P(f"        {cat:7s} recall={cats[cat]['recall']:.4f}  F1={cats[cat]['f1']:.4f}")
# pooled GT
gt_tot = sum(int(exp8[ds]['gt']['n_gt_total']) for ds in ['raja','cao'])
gt_norm = sum(int(exp8[ds]['gt']['n_gt_normal']) for ds in ['raja','cao'])
gt_long = sum(int(exp8[ds]['gt']['n_gt_long']) for ds in ['raja','cao'])
P(f"    POOLED GT total={gt_tot} normal={gt_norm} long={gt_long} ({100*gt_long/gt_tot:.1f}% long)")
# pooled recall normal/long
for cat in ["normal", "long"]:
    vals = []
    for ds in ["raja", "cao"]:
        df = load(NEW, "exp8", ds)
        vals += best_per_session(df[df["blink_category"] == cat])["det_recall"].tolist()
    P(f"    POOLED {cat} recall={np.mean(vals):.4f}")

# =====================================================================
# 10. EXP1 per-channel / region (median, selection=='all')
# =====================================================================
H("EXP1 per-channel performance (median, selection=all, mean across sessions)")
exp1_chan = {}
for ds in ["raja", "cao"]:
    df = median_filter(load(NEW, "exp1", ds))
    allsel = df[df["selection"] == "all"]
    g = allsel.groupby("channel_in_group").agg(
        f1=("det_f1", "mean"), p=("det_precision", "mean"), r=("det_recall", "mean"), n=("session", "nunique")
    ).sort_values("f1", ascending=False)
    ch2group = load_region_map(ds)
    g["group"] = [ch2group.get(c.upper(), "unknown") for c in g.index]
    g["region"] = [COARSE(x) for x in g["group"]]
    exp1_chan[ds] = g
    P(f"[{DS_NICE[ds]}] top channels:")
    for ch, rr in g.head(7).iterrows():
        P(f"    {ch:6s} region={rr['region']:10s} P={rr['p']:.3f} R={rr['r']:.3f} F1={rr['f1']:.3f}")
    P(f"    bottom channels (mean F1): " + ", ".join(f"{ch}={rr['f1']:.3f}" for ch, rr in g.tail(4).iterrows()))
    # region means
    reg = g.groupby("region")["f1"].mean().sort_values(ascending=False)
    P(f"    region mean F1: " + ", ".join(f"{k}={v:.3f}" for k, v in reg.items()))

# best single channel (fixed, mean across sessions) vs best group (fixed) from exp2
H("EXP1/EXP2 best fixed single channel vs best fixed group (median / Proposed-Med)")
for ds in ["raja", "cao"]:
    d2 = load(NEW, "exp2", ds)
    pm = d2[d2["condition"] == "Proposed-Med"]
    # fixed single channel: mean across sessions per single: selection
    singles = pm[pm["selection"].str.startswith("single:")].groupby("selection")["det_f1"].mean().sort_values(ascending=False)
    groups = pm[~pm["selection"].str.startswith("single:")].groupby("selection")["det_f1"].mean().sort_values(ascending=False)
    P(f"[{DS_NICE[ds]}] best fixed single: {singles.index[0]}={singles.iloc[0]:.4f} | best fixed group: {groups.index[0]}={groups.iloc[0]:.4f}")
    P(f"    all singles: " + ", ".join(f"{s.split(':')[1]}={v:.3f}" for s, v in singles.items()))
    P(f"    all groups:  " + ", ".join(f"{s}={v:.3f}" for s, v in groups.items()))

# =====================================================================
# 11. Wilcoxon stats: PM vs BLINKER-concat, per experiment-context
# =====================================================================
H("WILCOXON: Proposed-Med vs BLINKER-concat (session-level best-channel F1, new run)")
# We compare within exp2 (only experiment with all conditions), per dataset + pooled.
def paired_best(df, condA, condB):
    a = best_per_session(df[df["condition"] == condA]).set_index("session")["det_f1"]
    b = best_per_session(df[df["condition"] == condB]).set_index("session")["det_f1"]
    common = a.index.intersection(b.index)
    return a.loc[common].values, b.loc[common].values

stats_rows = []
comparisons = []
for ds in ["raja", "cao"]:
    df = load(NEW, "exp2", ds)
    for comp in ["BLINKER-concat", "MNE-annot", "Proposed-Mean"]:
        a, b = paired_best(df, "Proposed-Med", comp)
        comparisons.append((ds, comp, a, b))
# pooled PM vs each
for comp in ["BLINKER-concat", "MNE-annot", "Proposed-Mean"]:
    aa, bb = [], []
    for ds in ["raja", "cao"]:
        df = load(NEW, "exp2", ds)
        a, b = paired_best(df, "Proposed-Med", comp)
        aa += a.tolist(); bb += b.tolist()
    comparisons.append(("pooled", comp, np.array(aa), np.array(bb)))

ncomp = len(comparisons)
rng = np.random.default_rng(42)
for ds, comp, a, b in comparisons:
    diff = a - b
    alt = "greater"
    # use two-sided for Proposed-Mean (paper used two-sided), greater for baselines
    try:
        w, p = stats.wilcoxon(a, b, alternative="greater", zero_method="wilcox")
    except ValueError:
        w, p = np.nan, np.nan
    p_bonf = min(1.0, p * ncomp) if not np.isnan(p) else np.nan
    n = len(a)
    r_eff = 1 - (2 * w) / (n * (n + 1)) if not np.isnan(w) else np.nan
    boot = [rng.choice(diff, size=len(diff), replace=True).mean() for _ in range(10000)]
    ci_lo, ci_hi = np.percentile(boot, [2.5, 97.5])
    P(f"    {ds:7s} PM vs {comp:15s} d_mean={diff.mean():+.4f} W={w:.1f} p={p:.2e} p_bonf={p_bonf:.2e} r={r_eff:.3f} CI=[{ci_lo:+.4f},{ci_hi:+.4f}] n={n}")
    stats_rows.append(dict(ds=ds, comp=comp, dmean=diff.mean(), W=w, p=p, p_bonf=p_bonf, r=r_eff, ci_lo=ci_lo, ci_hi=ci_hi, n=n))

# =====================================================================
# 12. Failure analysis: bottom-5 sessions each dataset (PM best-channel)
# =====================================================================
H("FAILURE ANALYSIS: bottom-5 sessions (Proposed-Med best-channel, new run)")
for ds in ["raja", "cao"]:
    bps = exp2_head[("new", ds, "Proposed-Med")]["bps"].copy()
    bps["gt"] = bps["det_tp"] + bps["det_fn"]
    bps = bps.sort_values("det_f1")
    P(f"[{DS_NICE[ds]}] median GT(tp+fn)={bps['gt'].median():.0f}")
    for _, rr in bps.head(5).iterrows():
        P(f"    {rr['session']:30s} F1={rr['det_f1']:.3f} ch={rr['channel_in_group']:5s} tp={int(rr['det_tp'])} fp={int(rr['det_fp'])} fn={int(rr['det_fn'])} GT={int(rr['gt'])}")

# write
OUT_MD.parent.mkdir(parents=True, exist_ok=True)
OUT_MD.write_text("# Frozen numbers (std=3.0 re-run, runs_second_iteration)\n\n" + "\n".join(report) + "\n", encoding="utf-8")
print("\n\nWROTE", OUT_MD)
