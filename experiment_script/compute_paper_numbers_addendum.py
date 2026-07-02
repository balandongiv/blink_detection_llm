"""Addendum computations for the paragraph audit (extends compute_paper_numbers.py)."""
from __future__ import annotations
from pathlib import Path
from itertools import combinations
import numpy as np, pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
NEW = REPO / "runs_second_iteration"
CONDS = ["Proposed-Med", "Proposed-Mean", "BLINKER-concat", "MNE-annot"]

def load(exp, ds):
    m = {"exp2": ("exp2_{0}", "exp2_strategy_comparison_{1}_results.csv"),
         "exp3": ("exp3_{0}", "exp3_epoch_duration_{1}_results.csv")}
    fold = "raja" if ds == "raja" else "cao"; fil = "raja" if ds == "raja" else "cao2018"
    return pd.read_csv(NEW / m[exp][0].format(fold) / m[exp][1].format("", fil))

def best_per_session(df):
    return df.loc[df.groupby("session")["det_f1"].idxmax()].copy()

print("=== (1) EXP3 per-duration Wilcoxon vs 30s (pooled best-channel F1) ===")
# build per-session best F1 by duration, pooled
dur_series = {}
for dur in [10,20,30,40,50,60,120]:
    vals = {}
    for ds in ["raja","cao"]:
        df = load("exp3", ds); df = df[df.center_method=="median"]
        sub = df[df.epoch_duration_s==float(dur)]
        bps = best_per_session(sub)
        for _,r in bps.iterrows():
            vals[f"{ds}/{r['session']}"] = r["det_f1"]
    dur_series[dur] = vals
ref = dur_series[30]
ncomp = 6  # 6 non-reference durations
for dur in [10,20,40,50,60,120]:
    keys = sorted(set(ref) & set(dur_series[dur]))
    a = np.array([dur_series[dur][k] for k in keys]); b = np.array([ref[k] for k in keys])
    try:
        w,p = stats.wilcoxon(a,b,alternative="two-sided")
    except ValueError:
        w,p=np.nan,np.nan
    print(f"   {dur:3d}s vs 30s: mean={a.mean():.4f} d={a.mean()-b.mean():+.4f} p={p:.3f} p_bonf={min(1,p*ncomp):.3f} n={len(a)}")

print("\n=== (2) Full Wilcoxon matrix among 4 conditions (pooled, best-channel F1) ===")
# build per-condition per-session best F1 pooled
cond_vals = {c: {} for c in CONDS}
for ds in ["raja","cao"]:
    df = load("exp2", ds)
    for c in CONDS:
        bps = best_per_session(df[df.condition==c])
        for _,r in bps.iterrows():
            cond_vals[c][f"{ds}/{r['session']}"] = r["det_f1"]
pairs = list(combinations(CONDS,2)); npair=len(pairs)
for a_c,b_c in pairs:
    keys = sorted(set(cond_vals[a_c]) & set(cond_vals[b_c]))
    a=np.array([cond_vals[a_c][k] for k in keys]); b=np.array([cond_vals[b_c][k] for k in keys])
    w,p = stats.wilcoxon(a,b,alternative="two-sided")
    higher = a_c if a.mean()>b.mean() else b_c
    print(f"   {a_c:14s} vs {b_c:14s}: d={a.mean()-b.mean():+.4f} ({higher} higher) p={p:.2e} p_bonf={min(1,p*npair):.2e}")

print("\n=== (3) Channel-selection cross-method agreement (argmax-F1 channel) ===")
for ds in ["raja","cao"]:
    df = load("exp2", ds)
    best = {c: best_per_session(df[df.condition==c]).set_index("session")["channel_in_group"] for c in CONDS}
    cat = pd.DataFrame(best)
    # pairwise agreement
    ag = []
    for a_c,b_c in combinations(CONDS,2):
        ag.append((cat[a_c]==cat[b_c]).mean())
    allfour = (cat.nunique(axis=1)==1).mean()
    print(f"   {ds}: mean pairwise agreement={np.mean(ag):.3f}  all-four={100*allfour:.1f}% ({int((cat.nunique(axis=1)==1).sum())}/{len(cat)})")
# pooled
catall=[]
for ds in ["raja","cao"]:
    df = load("exp2", ds)
    best = {c: best_per_session(df[df.condition==c]).set_index("session")["channel_in_group"] for c in CONDS}
    cat = pd.DataFrame(best); cat.index = [f"{ds}/{i}" for i in cat.index]; catall.append(cat)
catall=pd.concat(catall)
ag=[ (catall[a_c]==catall[b_c]).mean() for a_c,b_c in combinations(CONDS,2)]
allfour=(catall.nunique(axis=1)==1).mean()
print(f"   POOLED: mean pairwise agreement={np.mean(ag):.3f}  all-four={100*allfour:.1f}% ({int((catall.nunique(axis=1)==1).sum())}/{len(catall)})")

print("\n=== (4) Within-subject channel consistency (median fraction picking subject's modal channel) ===")
for ds in ["raja","cao"]:
    df = load("exp2", ds)
    fracs=[]
    for c in CONDS:
        bps = best_per_session(df[df.condition==c]).copy()
        bps["subject"]=bps["session"].str.split("/").str[0]
        for subj,grp in bps.groupby("subject"):
            modal = grp["channel_in_group"].mode().iloc[0]
            fracs.append((grp["channel_in_group"]==modal).mean())
    print(f"   {ds}: median within-subject modal-channel fraction={np.median(fracs):.3f} (n={len(fracs)} subject-method groups)")
