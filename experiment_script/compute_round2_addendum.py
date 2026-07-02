"""Round-2 addendum numbers: hemisphere symmetry (R3), within-subject
consistency (R4), and epoch-health benefit structure (R5).

All numbers use best-channel-per-session aggregation on runs_second_iteration/,
identical to compute_paper_numbers.py. Writes writing/NUMBERS_round2.md for audit.

Run inside conda env double_threshold_algo.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
import os
NEW = REPO / os.environ.get("BLINK_RUNS_DIR", "runs_second_iteration")
OUT = REPO / "writing" / "NUMBERS_round2.md"

report = []
def P(*a):
    line = " ".join(str(x) for x in a); print(line); report.append(line)
def H(t): P("\n## " + t)


def load(exp, ds):
    m = {"exp2": ("exp2_{0}", "exp2_strategy_comparison_{1}_results.csv"),
         "exp7": ("exp7_{0}", "exp7_epoch_health_{1}_results.csv")}
    fold = "raja" if ds == "raja" else "cao"; fil = "raja" if ds == "raja" else "cao2018"
    return pd.read_csv(NEW / m[exp][0].format(fold) / m[exp][1].format("", fil))


def best_per_session(df):
    return df.loc[df.groupby("session")["det_f1"].idxmax()].copy()


DSN = {"raja": "Raja", "cao": "Cao2018"}

# ============ R3: hemisphere symmetry ============
H("R3 hemisphere symmetry (Proposed-Med, best-channel-per-session within group)")
for ds in ["raja", "cao"]:
    pm = load("exp2", ds)
    pm = pm[pm.condition == "Proposed-Med"]
    vals = {}
    for grp in ["frontal_left", "frontal_right"]:
        sub = pm[pm.selection == grp]
        vals[grp] = best_per_session(sub)["det_f1"].mean()
    delta = vals["frontal_left"] - vals["frontal_right"]
    P(f"    {DSN[ds]}: frontal_left={vals['frontal_left']:.4f}  frontal_right={vals['frontal_right']:.4f}  "
      f"|delta|={abs(delta):.4f}")

# ============ R4: within-subject consistency ============
H("R4 within-subject consistency (Proposed-Med best-channel F1)")
parts = []
for ds in ["raja", "cao"]:
    b = best_per_session(load("exp2", ds)[load("exp2", ds).condition == "Proposed-Med"]).copy()
    b["subject"] = b.session.str.split("/").str[0]; b["dataset"] = ds
    parts.append(b)
allb = pd.concat(parts, ignore_index=True)
multi = allb.groupby(["dataset", "subject"]).filter(lambda g: g.session.nunique() >= 2)
P(f"    subjects with >=2 sessions: {multi.groupby(['dataset','subject']).ngroups} "
  f"covering {multi.session.nunique()} sessions")
wsd = multi.groupby(["dataset", "subject"])["det_f1"].std(ddof=1)
P(f"    mean within-subject SD of F1 = {wsd.mean():.4f}  (median {wsd.median():.4f})")
btw = allb.groupby(["dataset", "subject"])["det_f1"].mean().std(ddof=1)
P(f"    between-subject SD of subject-mean F1 = {btw:.4f}")

def icc1(df):
    groups = [g["det_f1"].values for _, g in df.groupby("subject")]
    k = np.mean([len(g) for g in groups]); grand = np.mean(np.concatenate(groups)); n = len(groups)
    msb = sum(len(g) * (g.mean() - grand) ** 2 for g in groups) / (n - 1)
    msw = sum(((g - g.mean()) ** 2).sum() for g in groups) / (sum(len(g) for g in groups) - n)
    return (msb - msw) / (msb + (k - 1) * msw)
for ds in ["raja", "cao"]:
    sub = multi[multi.dataset == ds]
    P(f"    {DSN[ds]}: ICC(1)={icc1(sub):.3f}")

# ============ R5: epoch-health benefit structure ============
H("R5 epoch-health benefit vs baseline F1 / GT count (Proposed-Med)")
for ds in ["raja", "cao"]:
    e7 = load("exp7", ds)
    on = best_per_session(e7[e7.use_epoch_health == True]).set_index("session")["det_f1"]
    off = best_per_session(e7[e7.use_epoch_health == False]).set_index("session")
    common = on.index.intersection(off.index)
    delta = (on.loc[common] - off.loc[common, "det_f1"])
    base = off.loc[common, "det_f1"]
    gt = off.loc[common, "det_tp"] + off.loc[common, "det_fn"]
    rb, pb = stats.pearsonr(base.values, delta.values)
    rg, pg = stats.pearsonr(gt.values, delta.values)
    low = base < 0.7
    P(f"    {DSN[ds]}: n={len(common)} mean_delta={delta.mean():+.4f}")
    P(f"        corr(baseline_F1, delta)={rb:+.3f} (p={pb:.4f}); corr(GT_count, delta)={rg:+.3f} (p={pg:.4f})")
    P(f"        baseline<0.7: n={int(low.sum())} mean_gain={delta[low].mean():+.4f} | "
      f"baseline>=0.7 mean_gain={delta[~low].mean():+.4f}")

# ============ R2 cross-check: count agreement ============
H("R2 count agreement cross-check (best-channel, pooled 104)")
CONDS = ["Proposed-Med", "Proposed-Mean", "BLINKER-concat", "MNE-annot"]
for c in CONDS:
    preds, truths = [], []
    for ds in ["raja", "cao"]:
        b = best_per_session(load("exp2", ds)[load("exp2", ds).condition == c])
        preds += (b.det_tp + b.det_fp).tolist(); truths += (b.det_tp + b.det_fn).tolist()
    preds = np.array(preds); truths = np.array(truths)
    r = np.corrcoef(preds, truths)[0, 1]; ratio = np.mean(preds / truths)
    P(f"    {c:15s} r={r:.4f} mean(pred/truth)={ratio:.3f}")

OUT.write_text("# Round-2 frozen numbers (runs_second_iteration, std=3.0)\n\n" + "\n".join(report) + "\n",
               encoding="utf-8")
print("\nWROTE", OUT)
