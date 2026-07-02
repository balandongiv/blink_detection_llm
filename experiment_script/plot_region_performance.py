"""Regional / single-channel analysis for the results section.

Produces:
  writing/e_result/tab_region_performance.tex
  writing/figures/fig_region_performance.pdf, .png

Per-channel single-channel performance (median centre, single-channel Stage A screening)
from exp1. Frontopolar = E22/E9 (Raja), FP1/FP2 (Cao2018). Run inside double_threshold_algo.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import yaml
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
import os
NEW = REPO / os.environ.get("BLINK_RUNS_DIR", "runs_second_iteration")
ER = REPO / "writing" / "e_result"
FIGDIR = REPO / "writing" / "figures"; FIGDIR.mkdir(parents=True, exist_ok=True)
DSN = {"raja": "Raja", "cao": "Cao2018"}
FRONTOPOLAR = {"raja": {"E22", "E9"}, "cao": {"FP1", "FP2"}}

def load_exp1(ds):
    fold = "raja" if ds == "raja" else "cao"; fil = "raja" if ds == "raja" else "cao2018"
    df = pd.read_csv(NEW / f"exp1_channel_{fold}" / f"exp1_channel_selection_{fil}_results.csv")
    return df[df.center_method == "median"]

def region_map(ds):
    yml = REPO / ("brain_region_raja.yaml" if ds == "raja" else "brain_region_cao2018.yaml")
    data = yaml.safe_load(yml.read_text())["eeg_regions"]
    m = {}
    for group, chans in data.items():
        coarse = group.rsplit("_", 1)[0] if group.endswith(("_left", "_right")) else group
        for c in chans:
            name = ("E" + str(c)) if ds == "raja" else str(c)
            m[name.upper()] = coarse
    return m

# per-channel single-channel F1 from 'all' selection (whole-scalp map for figure)
allmap = {}
for ds in ["raja", "cao"]:
    df = load_exp1(ds)
    g = df[df.selection == "all"].groupby("channel_in_group").agg(
        f1=("det_f1", "mean"), p=("det_precision", "mean"), r=("det_recall", "mean")).sort_values("f1", ascending=False)
    rm = region_map(ds)
    g["region"] = [rm.get(c.upper(), "other") for c in g.index]
    g["region"] = [("frontopolar" if c.upper() in FRONTOPOLAR[ds] else reg) for c, reg in zip(g.index, g["region"])]
    allmap[ds] = g

# single-channel-Stage-A frontal channels from single:* selections
singlemap = {}
for ds in ["raja", "cao"]:
    df = load_exp1(ds)
    rows = []
    for sel in sorted([s for s in df.selection.unique() if s.startswith("single:")]):
        ch = sel.split(":")[1]
        sub = df[df.selection == sel]
        rows.append((ch, sub.det_precision.mean(), sub.det_recall.mean(), sub.det_f1.mean()))
    sm = pd.DataFrame(rows, columns=["ch", "p", "r", "f1"]).sort_values("f1", ascending=False)
    rm = region_map(ds)
    sm["region"] = [("frontopolar" if c.upper() in FRONTOPOLAR[ds] else rm.get(c.upper(), "frontal")) for c in sm.ch]
    singlemap[ds] = sm

# non-frontal collapse (mean over non-frontal channels from 'all')
nonfrontal = {}
for ds in ["raja", "cao"]:
    g = allmap[ds]
    nf = g[~g.region.isin(["frontal", "frontopolar"])]
    nonfrontal[ds] = nf["f1"].mean()
    print(f"{ds}: non-frontal mean F1 = {nf['f1'].mean():.3f} (n={len(nf)} channels); "
          f"frontal+frontopolar mean = {g[g.region.isin(['frontal','frontopolar'])]['f1'].mean():.3f}")

# NOTE: the region/single-channel summary table was removed in the channel-by-channel
# refactor; the comprehensive per-channel table is now tab_exp1_channel_ablation.tex
# (experiment_script/regen_paper_tables.py). This script now produces only the figure.

# ---------------- FIGURE: per-channel F1 bars grouped by region ----------------
REGION_COLORS = {"frontopolar": "#C44E52", "frontal": "#DD8452", "central": "#4C72B0",
                 "parietal": "#8172B3", "occipital": "#55A868", "temporal_parietal": "#937860",
                 "posterior": "#999999", "other": "#cccccc"}
fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
for ax, ds in zip(axes, ["raja", "cao"]):
    g = allmap[ds]
    colors = [REGION_COLORS.get(r, "#cccccc") for r in g["region"]]
    ax.bar(range(len(g)), g["f1"].values, color=colors)
    ax.set_xticks(range(len(g))); ax.set_xticklabels(g.index, rotation=90, fontsize=7)
    ax.set_title(f"{DSN[ds]}"); ax.set_ylim(0, 1.0)
    ax.set_ylabel("macro-$F_1$ (single channel)" if ds == "raja" else "")
# legend
from matplotlib.patches import Patch
handles = [Patch(color=c, label=r) for r, c in REGION_COLORS.items() if r in {"frontopolar","frontal","central","parietal","occipital","temporal_parietal","posterior"}]
fig.legend(handles=handles, loc="upper center", ncol=7, fontsize=8, frameon=False, bbox_to_anchor=(0.5, 1.04))
fig.suptitle("Single-channel detection $F_1$ by electrode and scalp region", y=1.10, fontsize=12)
fig.tight_layout()
fig.savefig(FIGDIR / "fig_region_performance.pdf", bbox_inches="tight")
fig.savefig(FIGDIR / "fig_region_performance.png", dpi=150, bbox_inches="tight")
print("wrote fig_region_performance.pdf/.png")
