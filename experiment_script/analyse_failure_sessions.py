"""Failure analysis: why do the worst sessions fail?

Ranks all sessions by Proposed-Med best-channel F1, isolates the bottom 5 per dataset,
and reports for each: ground-truth blink count, TP/FP/FN, error regime, best channel,
GT relative to the dataset median, the epoch-health effect, and (best-effort) the robust
frontopolar amplitude scale from the raw recording.

Outputs:
  writing/e_result/tab_failure_analysis.tex
  prints the full ranking + mechanism summary

Run inside conda env double_threshold_algo.
"""
from __future__ import annotations
from pathlib import Path
import glob
import numpy as np, pandas as pd

REPO = Path(__file__).resolve().parents[1]
import os
NEW = REPO / os.environ.get("BLINK_RUNS_DIR", "runs_second_iteration")
ER = REPO / "writing" / "e_result"
DSN = {"raja": "Raja", "cao": "Cao2018"}
RAW_ROOT = {"raja": Path("D:/dataset/drowsy_driving_raja_processed"),
            "cao": Path("D:/dataset/sustained_attention_driving")}
FRONTOPOLAR = {"raja": ["E22", "E9"], "cao": ["FP1", "FP2"]}

def load(exp, ds):
    fold = "raja" if ds == "raja" else "cao"; fil = "raja" if ds == "raja" else "cao2018"
    names = {"exp2": ("exp2_{0}", "exp2_strategy_comparison_{1}_results.csv"),
             "exp7": ("exp7_{0}", "exp7_epoch_health_{1}_results.csv")}
    return pd.read_csv(NEW / names[exp][0].format(fold) / names[exp][1].format("", fil))

def best_per_session(df):
    return df.loc[df.groupby("session")["det_f1"].idxmax()].copy()

# ---- frontopolar robust amplitude (best-effort) ----
def frontopolar_amplitude(ds, session, channel):
    try:
        import mne
        from scipy.stats import median_abs_deviation
    except Exception:
        return None
    subj = session.split("/")[0]
    rec = session.split("/")[1] if "/" in session else session
    root = RAW_ROOT[ds]
    cands = []
    cands += glob.glob(str(root / subj / f"{rec}*" / "**" / "*raw.fif"), recursive=True)
    cands += glob.glob(str(root / subj / "**" / "*raw.fif"), recursive=True)
    cands += glob.glob(str(root / "**" / f"{rec}*" / "**" / "*raw.fif"), recursive=True)
    for f in cands:
        try:
            raw = mne.io.read_raw_fif(f, preload=True, verbose="ERROR")
            picks = [c for c in [channel] + FRONTOPOLAR[ds] if c in raw.ch_names]
            if not picks:
                continue
            raw.pick(picks[:1]).filter(1.0, 20.0, verbose="ERROR")
            x = raw.get_data()[0]
            return float(1.4826 * median_abs_deviation(x, scale=1.0)) * 1e6  # microvolts
        except Exception:
            continue
    return None

rows_all = {}
median_gt = {}
for ds in ["raja", "cao"]:
    df = load("exp2", ds)
    bps = best_per_session(df[df.condition == "Proposed-Med"]).copy()
    bps["gt"] = bps["det_tp"] + bps["det_fn"]
    bps["regime"] = np.where(bps["det_fp"] > bps["det_fn"], "FP-heavy", "FN-heavy")
    median_gt[ds] = bps["gt"].median()
    # epoch-health effect per session (best-channel F1 health-on minus default)
    e7 = load("exp7", ds)
    on = best_per_session(e7[(e7.center_method == "median") & (e7.use_epoch_health == True)]).set_index("session")["det_f1"]
    off = best_per_session(e7[(e7.center_method == "median") & (e7.use_epoch_health == False)]).set_index("session")["det_f1"]
    bps = bps.sort_values("det_f1").reset_index(drop=True)
    bps["health_delta"] = bps["session"].map(lambda s: (on.get(s, np.nan) - off.get(s, np.nan)))
    rows_all[ds] = bps
    # how many sessions affected
    n = len(bps)
    print(f"[{DSN[ds]}] n={n}  median GT={median_gt[ds]:.0f}  "
          f"#sessions F1<0.6: {(bps.det_f1<0.6).sum()}  F1<0.7: {(bps.det_f1<0.7).sum()}  "
          f"min F1={bps.det_f1.min():.3f}")

# build table (bottom 5 each)
SRC = "% Source: runs_second_iteration/ exp2+exp7; script experiment_script/analyse_failure_sessions.py"
L = [SRC, r"\begin{table*}[ht]", r"  \centering", r"  \scriptsize", r"  \setlength{\tabcolsep}{4pt}",
     r"  \caption{The five lowest-$F_1$ Proposed-Med sessions per corpus (best channel per session). "
     r"GT is the ground-truth blink count ($\mathrm{TP}+\mathrm{FN}$); GT/med is GT relative to the dataset "
     r"median; $\Delta$health is the change in $F_1$ when corrupted epochs are excluded.}",
     r"  \label{tab:failure_analysis}", r"  \begin{tabular}{llrrrrcrrr}", r"    \toprule",
     r"    Dataset & Session & GT & TP & FP & FN & Regime & $F_1$ & GT/med & $\Delta$health \\", r"    \midrule"]
def esc(s): return str(s).replace("_", r"\_")
for ds in ["raja", "cao"]:
    bps = rows_all[ds]
    first = True
    for _, r in bps.head(5).iterrows():
        hd = r["health_delta"]
        hd_s = f"${hd:+.3f}$" if pd.notna(hd) else "n/a"
        dscell = DSN[ds] if first else ""
        L.append(f"    {dscell} & {esc(r['session'])} & {int(r['gt'])} & {int(r['det_tp'])} & {int(r['det_fp'])} & "
                 f"{int(r['det_fn'])} & {r['regime']} & {r['det_f1']:.3f} & {r['gt']/median_gt[ds]:.1f}$\\times$ & {hd_s} \\\\")
        first = False
    L.append(r"    \midrule" if ds == "raja" else r"    \bottomrule")
L += [r"  \end{tabular}", r"\end{table*}"]
(ER / "tab_failure_analysis.tex").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\nwrote tab_failure_analysis.tex")

# mechanism summary
print("\n=== MECHANISM SUMMARY ===")
for ds in ["raja", "cao"]:
    bot = rows_all[ds].head(5)
    fn_heavy = (bot["regime"] == "FN-heavy").sum()
    hi_gt = (bot["gt"] > 1.5 * median_gt[ds]).sum()
    print(f"[{DSN[ds]}] bottom-5: {fn_heavy}/5 FN-heavy (under-detection); "
          f"{hi_gt}/5 have GT > 1.5x median (anomalous blink count); "
          f"median GT/med ratio of bottom-5 = {(bot['gt']/median_gt[ds]).median():.1f}x")
    # amplitude check on bottom sessions vs a few typical sessions
print("\n=== AMPLITUDE CHECK (FN-heavy worst vs typical) ===")
for ds in ["raja"]:
    bps = rows_all[ds]
    worst = bps.iloc[0]
    typ = bps.iloc[len(bps)//2]
    aw = frontopolar_amplitude(ds, worst["session"], worst["channel_in_group"])
    at = frontopolar_amplitude(ds, typ["session"], typ["channel_in_group"])
    print(f"[{DSN[ds]}] worst {worst['session']} amp={aw}  vs typical {typ['session']} amp={at}")
