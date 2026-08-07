"""Table 7 and Figure 8 - predicted-versus-ground-truth blink-count agreement.

For each session and condition the predicted blink count is TP+FP and the true
count is TP+FN (both from exp2 event-level counts at the best-channel-per-session
row). This count-level check directly validates the blink-rate/PERCLOS usability
argument: a detector whose predicted count tracks the true count near 1:1 can
support blink-rate estimation, whereas an over- or under-counting detector cannot.

Produces:
  writing/figures/fig_count_agreement.pdf, .png
  writing/e_result/tab_count_agreement.tex

Aggregation: best-channel-per-session (writing/VALUE_AUDIT.md). Source CSVs:
publication_results/exp2_*/. Run inside conda env double_threshold_algo.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as PD  # noqa: E402

SCRIPT = "tab7_fig8_count_agreement.py"

CONDS = ["Proposed-Med", "Proposed-Mean", "BLINKER-concat", "MNE-annot"]
COLORS = {"Proposed-Med": "#4C72B0", "Proposed-Mean": "#55A868",
          "BLINKER-concat": "#C44E52", "MNE-annot": "#8172B3"}
MARKERS = {"Proposed-Med": "o", "Proposed-Mean": "s",
           "BLINKER-concat": "^", "MNE-annot": "D"}


def lin_ccc(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    mx, my = x.mean(), y.mean()
    vx, vy = x.var(), y.var()
    cov = ((x - mx) * (y - my)).mean()
    return 2 * cov / (vx + vy + (mx - my) ** 2)


# pooled best-channel rows
best = PD.load_exp2_best()
data = {}
for c in CONDS:
    parts = []
    for ds in ["raja", "cao"]:
        b = best[(ds, c)].copy()
        b["pred"] = b.tp + b.fp
        b["truth"] = b.tp + b.fn
        parts.append(b[["session", "pred", "truth"]])
    data[c] = pd.concat(parts, ignore_index=True)
n_sessions = len(data["Proposed-Med"])

# ---------- stats ----------
stat_rows = []
for c in CONDS:
    d = data[c]
    r, p = stats.pearsonr(d.pred, d.truth)
    ccc = lin_ccc(d.truth, d.pred)
    ratio = np.mean(d.pred / d.truth)
    stat_rows.append((c, r, ccc, ratio, len(d)))
    print(f"  {c:15s} r={r:.4f} CCC={ccc:.4f} mean(pred/truth)={ratio:.3f} n={len(d)}")

# ---------- figure: (A) predicted vs true scatter, (B) Bland-Altman for PM ----------
fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.6))

axA = axes[0]
hi = max(data[c][["pred", "truth"]].values.max() for c in CONDS)
axA.plot([0, hi], [0, hi], color="0.4", ls="--", lw=1.2, zorder=1, label="identity (1:1)")
for c in CONDS:
    d = data[c]
    axA.scatter(d.truth, d.pred, s=20, alpha=0.45, color=COLORS[c],
                marker=MARKERS[c], edgecolors="none", zorder=2, label=c)
axA.set_xlim(0, hi * 1.02); axA.set_ylim(0, hi * 1.02)
axA.set_xlabel("True blink count (TP + FN)")
axA.set_ylabel("Predicted blink count (TP + FP)")
axA.set_title("(a) Predicted vs. true event count")
axA.legend(loc="upper left", fontsize=8.5, framealpha=0.92)
axA.grid(True, color="0.92", lw=0.6)

# Bland-Altman for Proposed-Med
axB = axes[1]
d = data["Proposed-Med"]
mean_ct = (d.pred + d.truth) / 2
diff = d.pred - d.truth
bias = diff.mean(); sd = diff.std(ddof=1)
axB.scatter(mean_ct, diff, s=22, alpha=0.55, color=COLORS["Proposed-Med"],
            edgecolors="none")
axB.axhline(bias, color="#4C72B0", lw=1.6, label=f"bias = {bias:+.0f}")
axB.axhline(bias + 1.96 * sd, color="0.4", ls="--", lw=1.2,
            label=f"$\\pm$1.96 SD ({bias+1.96*sd:+.0f}, {bias-1.96*sd:+.0f})")
axB.axhline(bias - 1.96 * sd, color="0.4", ls="--", lw=1.2)
axB.axhline(0, color="0.7", ls=":", lw=1.0)
axB.set_xlabel("Mean of predicted and true count")
axB.set_ylabel("Predicted $-$ true count")
axB.set_title("(b) Bland-Altman, Proposed-Med")
axB.legend(loc="upper right", fontsize=8.5, framealpha=0.92)
axB.grid(True, color="0.92", lw=0.6)

fig.tight_layout()
PD.save_fig(fig, "fig_count_agreement")

# ---------- table ----------
L = [r"\begin{table}[ht]", r"  \centering",
     r"  \caption{Agreement between the predicted blink count (TP\,+\,FP) and the true count "
     r"(TP\,+\,FN) per session, pooled over Raja and Cao2018 ($n=" + str(n_sessions)
     + r"$) at the best-channel-per-session "
     r"row. The mean count ratio measures systematic over- or under-counting (1.00 is ideal); "
     r"Pearson $r$ and Lin's concordance correlation coefficient (CCC) measure how closely the predicted "
     r"count tracks the true count across sessions.}",
     r"  \label{tab:count_agreement}", r"  \begin{tabular}{lccc}", r"    \toprule",
     r"    Condition & Mean count ratio & Pearson $r$ & Lin's CCC \\", r"    \midrule"]
for c, r, ccc, ratio, n in stat_rows:
    L.append(f"    {c} & {ratio:.2f} & {r:.3f} & {ccc:.3f} \\\\")
L += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]
PD.write_tex(PD.ER / "tab_count_agreement.tex", L, SCRIPT)
