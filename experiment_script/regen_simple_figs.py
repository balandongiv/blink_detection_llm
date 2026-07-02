"""Regenerate the three displayed legacy figures from the std=3.0 re-run so they match the
revised text. Overwrites writing/e_result/figures/{fig_condition_prf,fig_f1_by_dataset,fig_f1_by_epoch}.pdf
Run inside conda env double_threshold_algo.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
import os
NEW = REPO / os.environ.get("BLINK_RUNS_DIR", "runs_second_iteration")
FIG = REPO / "writing" / "e_result" / "figures"
CONDS = ["BLINKER-concat", "MNE-annot", "Proposed-Mean", "Proposed-Med"]
COL = {"BLINKER-concat": "#C44E52", "MNE-annot": "#8172B3", "Proposed-Mean": "#DD8452", "Proposed-Med": "#4C72B0"}

def load(exp, ds):
    fold = "raja" if ds == "raja" else "cao"; fil = "raja" if ds == "raja" else "cao2018"
    names = {"exp2": ("exp2_{0}", "exp2_strategy_comparison_{1}_results.csv"),
             "exp3": ("exp3_{0}", "exp3_epoch_duration_{1}_results.csv")}
    return pd.read_csv(NEW / names[exp][0].format(fold) / names[exp][1].format("", fil))

def bps(df): return df.loc[df.groupby("session")["det_f1"].idxmax()]

# headline per condition (pooled + per dataset)
best = {}
for ds in ["raja", "cao"]:
    d = load("exp2", ds)
    for c in CONDS:
        best[(ds, c)] = bps(d[d.condition == c])
def metric(ds, c, col): return best[(ds, c)][col].mean()
def pooled(c, col):
    return pd.concat([best[("raja", c)], best[("cao", c)]])[col].mean()

# ---- fig_condition_prf: pooled P/R/F1 grouped bars ----
fig, ax = plt.subplots(figsize=(8, 4.5))
mets = ["det_precision", "det_recall", "det_f1"]; labels = ["Precision", "Recall", "$F_1$"]
x = np.arange(len(mets)); w = 0.2
for i, c in enumerate(CONDS):
    vals = [pooled(c, m) for m in mets]
    ax.bar(x + (i - 1.5) * w, vals, w, label=c, color=COL[c])
ax.set_xticks(x); ax.set_xticklabels(labels); ax.set_ylim(0, 1.0)
ax.set_ylabel("Macro-averaged score"); ax.legend(fontsize=8, ncol=2)
ax.set_title("Pooled performance over all 104 sessions")
fig.tight_layout(); fig.savefig(FIG / "fig_condition_prf.pdf", bbox_inches="tight"); plt.close(fig)
print("wrote fig_condition_prf.pdf")

# ---- fig_f1_by_dataset: F1 per condition, Raja vs Cao ----
fig, ax = plt.subplots(figsize=(8, 4.5))
x = np.arange(len(CONDS)); w = 0.38
ax.bar(x - w/2, [metric("raja", c, "det_f1") for c in CONDS], w, label="Raja", color="#4C72B0")
ax.bar(x + w/2, [metric("cao", c, "det_f1") for c in CONDS], w, label="Cao2018", color="#55A868")
ax.set_xticks(x); ax.set_xticklabels(CONDS, rotation=15, fontsize=9); ax.set_ylim(0, 1.0)
ax.set_ylabel("Macro-averaged $F_1$"); ax.legend(); ax.set_title("Per-condition $F_1$ by dataset")
fig.tight_layout(); fig.savefig(FIG / "fig_f1_by_dataset.pdf", bbox_inches="tight"); plt.close(fig)
print("wrote fig_f1_by_dataset.pdf")

# ---- fig_f1_by_epoch: PM pooled F1 vs duration ----
durs = [10, 20, 30, 40, 50, 60, 120]
fig, ax = plt.subplots(figsize=(8, 4.5))
for ds, col, lab in [("raja", "#4C72B0", "Raja"), ("cao", "#55A868", "Cao2018")]:
    d = load("exp3", ds); d = d[d.center_method == "median"]
    ys = [bps(d[d.epoch_duration_s == float(dd)])["det_f1"].mean() for dd in durs]
    ax.plot(durs, ys, "-o", color=col, label=lab)
# pooled
poolys = []
for dd in durs:
    vv = []
    for ds in ["raja", "cao"]:
        d = load("exp3", ds); d = d[d.center_method == "median"]
        vv += bps(d[d.epoch_duration_s == float(dd)])["det_f1"].tolist()
    poolys.append(np.mean(vv))
ax.plot(durs, poolys, "--s", color="#333333", label="Pooled")
ax.set_xlabel("Epoch duration (s)"); ax.set_ylabel("Macro-averaged $F_1$ (Proposed-Med)")
ax.set_ylim(0.75, 0.92); ax.legend(); ax.set_title("Stability across epoch durations")
fig.tight_layout(); fig.savefig(FIG / "fig_f1_by_epoch.pdf", bbox_inches="tight"); plt.close(fig)
print("wrote fig_f1_by_epoch.pdf")
