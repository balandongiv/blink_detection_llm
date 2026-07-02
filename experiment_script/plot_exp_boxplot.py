"""Cross-experiment summary: box plot + summary table + Wilcoxon stats table.

Produces:
  writing/figures/fig_exp_boxplot.pdf, .png
  writing/e_result/tab_exp_summary.tex
  writing/e_result/tab_exp_stats.tex

Aggregation: best-channel-per-session (argmax det_f1 over selections per session)
for Proposed-Med at each experiment's primary configuration. See writing/VALUE_AUDIT.md.

Run inside conda env double_threshold_algo.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

REPO = Path(__file__).resolve().parents[1]
import os
NEW = REPO / os.environ.get("BLINK_RUNS_DIR", "runs_second_iteration")
FIGDIR = REPO / "writing" / "figures"; FIGDIR.mkdir(parents=True, exist_ok=True)
ER = REPO / "writing" / "e_result"

def load(exp, ds):
    m = {"exp1": ("exp1_channel_{0}", "exp1_channel_selection_{1}_results.csv"),
         "exp2": ("exp2_{0}", "exp2_strategy_comparison_{1}_results.csv"),
         "exp3": ("exp3_{0}", "exp3_epoch_duration_{1}_results.csv"),
         "exp4": ("exp4_{0}", "exp4_boundary_tolerance_{1}_results.csv"),
         "exp5": ("exp5_{0}", "exp5_nmin_sensitivity_{1}_results.csv"),
         "exp7": ("exp7_{0}", "exp7_epoch_health_{1}_results.csv"),
         "exp8": ("exp8_{0}", "exp8_long_blink_{1}_results.csv")}
    fold = "raja" if ds == "raja" else "cao"; fil = "raja" if ds == "raja" else "cao2018"
    return pd.read_csv(NEW / m[exp][0].format(fold) / m[exp][1].format("", fil))

def bps_series(df):
    """per-session best det_f1 (Series indexed by session)."""
    return df.loc[df.groupby("session")["det_f1"].idxmax()].set_index("session")["det_f1"]

# Proposed-Med per-session best-channel F1 at each experiment's primary config
EXP_DESC = {
    "exp1": "Channel selection (full cap)",
    "exp2": "Strategy comparison",
    "exp3": "Epoch duration (30\\,s)",
    "exp4": "Boundary tolerance (IoU 0.1)",
    "exp5": "Minimum flagged epochs",
    "exp7": "Epoch-health filtering",
    "exp8": "Long-blink analysis",
}
def pm_series(exp, ds):
    if exp == "exp1":
        df = load("exp1", ds); df = df[(df.center_method == "median") & (df.selection == "all")]
        return bps_series(df)
    if exp == "exp2":
        df = load("exp2", ds); return bps_series(df[df.condition == "Proposed-Med"])
    if exp == "exp3":
        df = load("exp3", ds); df = df[(df.center_method == "median") & (df.epoch_duration_s == 30.0)]
        return bps_series(df)
    if exp == "exp4":
        df = load("exp4", ds); df = df[(df.center_method == "median") & (df.iou_threshold == 0.1)]
        return bps_series(df)
    if exp == "exp5":
        df = load("exp5", ds); df = df[(df.center_method == "median") & (df.min_flagged_epochs == 1)]
        return bps_series(df)
    if exp == "exp7":
        df = load("exp7", ds); df = df[(df.center_method == "median") & (df.use_epoch_health == True)]
        return bps_series(df)
    if exp == "exp8":
        df = load("exp8", ds); return bps_series(df[df.blink_category == "all"])

EXPS = ["exp1", "exp2", "exp3", "exp4", "exp5", "exp7", "exp8"]
DSN = {"raja": "Raja", "cao": "Cao2018"}

# exp2 baselines per-session best-channel F1 for reference lines + stats
blinker = {ds: bps_series(load("exp2", ds)[load("exp2", ds).condition == "BLINKER-concat"]) for ds in ["raja", "cao"]}
mne = {ds: bps_series(load("exp2", ds)[load("exp2", ds).condition == "MNE-annot"]) for ds in ["raja", "cao"]}

# ---------------- BOX PLOT ----------------
records = []
for exp in EXPS:
    for ds in ["raja", "cao"]:
        for v in pm_series(exp, ds).values:
            records.append({"Experiment": exp, "Dataset": DSN[ds], "F1": v})
plotdf = pd.DataFrame(records)
sns.set_style("whitegrid")
fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), sharey=True)
for ax, ds in zip(axes, ["raja", "cao"]):
    sub = plotdf[plotdf.Dataset == DSN[ds]]
    sns.boxplot(data=sub, x="Experiment", y="F1", ax=ax,
                color=("#4C72B0" if ds == "raja" else "#55A868"), width=0.6, fliersize=2)
    bl = blinker[ds].mean(); mn = mne[ds].mean()
    ax.axhline(bl, ls="--", color="#C44E52", lw=1.5, label=f"BLINKER-concat ({bl:.2f})")
    ax.axhline(mn, ls=":", color="#8172B3", lw=1.5, label=f"MNE-annot ({mn:.2f})")
    ax.set_title(f"{DSN[ds]} ({sub.Experiment.eq('exp2').sum()} sessions)")
    ax.set_xlabel("Experiment"); ax.set_ylabel("Session-level $F_1$" if ds == "raja" else "")
    ax.set_ylim(0, 1.0); ax.legend(loc="lower left", fontsize=8, framealpha=0.9)
    ax.tick_params(axis="x", rotation=30)
fig.suptitle("Proposed-Med session-level $F_1$ across ablation experiments (best channel per session)", fontsize=12)
fig.tight_layout()
fig.savefig(FIGDIR / "fig_exp_boxplot.pdf", bbox_inches="tight")
fig.savefig(FIGDIR / "fig_exp_boxplot.png", dpi=150, bbox_inches="tight")
print("wrote fig_exp_boxplot.pdf/.png")

# ---------------- SUMMARY TABLE ----------------
SRC = "% Source: runs_second_iteration/; script experiment_script/plot_exp_boxplot.py"
bl_pool = pd.concat([blinker["raja"], blinker["cao"]]).mean()
L = [SRC, r"\begin{table*}[ht]", r"  \centering",
     r"  \caption{Proposed-Med detection performance across all ablation experiments on the Raja and Cao2018 "
     r"driving-EEG corpora. Macro-averaged $F_1$ over all sessions (best-channel-per-session). The best competing "
     r"method is BLINKER-concat from the strategy comparison; $\Delta$ is the pooled Proposed-Med advantage over "
     f"BLINKER-concat (pooled macro-$F_1$ {bl_pool:.4f}).}}",
     r"  \label{tab:exp_summary}", r"  \begin{tabular}{llccll}", r"    \toprule",
     r"    Exp. & Description & PM $F_1$ (Raja) & PM $F_1$ (Cao2018) & Best competitor & $\Delta$ vs competitor \\",
     r"    \midrule"]
for exp in EXPS:
    rj = pm_series(exp, "raja").mean(); cao = pm_series(exp, "cao").mean()
    pool = pd.concat([pm_series(exp, "raja"), pm_series(exp, "cao")]).mean()
    delta = pool - bl_pool
    L.append(f"    {exp} & {EXP_DESC[exp]} & {rj:.4f} & {cao:.4f} & BLINKER-concat & $+{delta:.4f}$ \\\\")
L += [r"    \bottomrule", r"  \end{tabular}", r"\end{table*}"]
(ER / "tab_exp_summary.tex").write_text("\n".join(L) + "\n", encoding="utf-8")
print("wrote tab_exp_summary.tex")

# ---------------- STATS TABLE (PM vs BLINKER-concat, 14 pairs) ----------------
rng = np.random.default_rng(42)
pairs = [(exp, ds) for exp in EXPS for ds in ["raja", "cao"]]
ncomp = len(pairs)
rows = []
for exp, ds in pairs:
    a = pm_series(exp, ds)
    b = blinker[ds]
    common = a.index.intersection(b.index)
    av = a.loc[common].values; bv = b.loc[common].values
    diff = av - bv
    try:
        w, p = stats.wilcoxon(av, bv, alternative="greater", zero_method="wilcox")
    except ValueError:
        w, p = np.nan, np.nan
    p_bonf = min(1.0, p * ncomp) if not np.isnan(p) else np.nan
    n = len(av)
    r_eff = 1 - (2 * w) / (n * (n + 1)) if not np.isnan(w) else np.nan
    boot = np.array([rng.choice(diff, size=len(diff), replace=True).mean() for _ in range(10000)])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    rows.append((exp, DSN[ds], diff.mean(), w, p_bonf, r_eff, lo, hi, n))

def pfmt(p):
    if np.isnan(p): return "n/a"
    if p < 1e-3: return f"$<10^{{{int(np.floor(np.log10(p)))}}}$" if p > 0 else "$<10^{-12}$"
    return f"{p:.3f}"

L = [SRC, r"\begin{table*}[ht]", r"  \centering",
     r"  \caption{Paired Wilcoxon signed-rank tests of Proposed-Med versus the best competing method "
     r"(BLINKER-concat from the strategy comparison) on session-level $F_1$, for each experiment and dataset. "
     r"$\Delta F_1$ is the mean Proposed-Med advantage; $p$ is Bonferroni-corrected over the 14 comparisons "
     r"(one-sided, Proposed-Med greater); $r$ is the rank-biserial effect size; the 95\% CI is a 10{,}000-sample "
     r"bootstrap on $\Delta F_1$.}",
     r"  \label{tab:exp_stats}", r"  \begin{tabular}{llcccccc}", r"    \toprule",
     r"    Exp. & Dataset & $\Delta F_1$ & $W$ & $p_{\mathrm{Bonf}}$ & $r$ & 95\% CI & $n$ \\", r"    \midrule"]
for exp, ds, dm, w, pb, r_, lo, hi, n in rows:
    L.append(f"    {exp} & {ds} & $+{dm:.4f}$ & {w:.0f} & {pfmt(pb)} & {r_:.3f} & $[{lo:+.4f},\\,{hi:+.4f}]$ & {n} \\\\")
L += [r"    \bottomrule", r"  \end{tabular}", r"\end{table*}"]
(ER / "tab_exp_stats.tex").write_text("\n".join(L) + "\n", encoding="utf-8")
print("wrote tab_exp_stats.tex")
print("\nstats preview:")
for r in rows: print("  ", r[0], r[1], f"d={r[2]:+.4f}", f"pBonf={r[4]:.2e}", f"r={r[5]:.3f}", f"CI=[{r[6]:+.4f},{r[7]:+.4f}]")
