"""Box plot of session-level macro F1 for the single-channel-only selection groups.

Complements exp1_b_plot_region_boxplot.py: instead of whole-region / hemisphere
groups, this isolates each "<label>_only" selection (fp1_only, fp2_only, f3_only,
f4_only, and for Raja also af3_only, af4_only — see eeg_regions in
brain_region_{cao2018,raja}.yaml) so the standalone contribution of a single
electrode can be read off directly. "_only" is purely the YAML naming
convention used to mark these as singleton selection groups (see
channel_ablation_utils.build_selection_groups); it is dropped for display here.
Raja and Cao2018 are drawn side by side (hue) in a single figure.

Source: runs0/exp1_channel_cao/exp1_channel_selection_cao2018_results.csv
        runs0/exp1_channel_raja/exp1_channel_selection_raja_results.csv

Produces: writing/figures/fig_exp1_single_channel_boxplot.pdf, .png

Run inside conda env double_threshold_algo.
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
import yaml
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.project_paths import EXP_SETUP_DIR, load_exp_config  # noqa: E402

FIGDIR = REPO / "writing" / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)

_PATH_CFG = load_exp_config(EXP_SETUP_DIR / "exp_path.yaml")
SRC = {
    "raja": REPO / Path(_PATH_CFG["out_dirs"]["exp1"]["raja"]) / "exp1_channel_selection_raja_results.csv",
    "cao": REPO / Path(_PATH_CFG["out_dirs"]["exp1"]["cao2018"]) / "exp1_channel_selection_cao2018_results.csv",
}
DSN = {"raja": "Internal", "cao": "Cao2018"}

# Raja uses EGI net numbering (E22, E9, ...); map to 10-20 names via egi_pair.
_raja_yaml = yaml.safe_load((REPO / "brain_region_raja.yaml").read_text(encoding="utf-8"))
RAJA_CHANNEL_NAME = {
    f"E{num}": name.upper()
    for entry in _raja_yaml["egi_pair"]
    for name, num in entry.items()
}


def display_channel(ds: str, channel: str) -> str:
    if ds == "raja":
        return RAJA_CHANNEL_NAME.get(channel, channel)
    return channel


# (display label, selection name in the results CSV) — union across both datasets;
# a dataset that doesn't define a given "_only" group simply contributes no box for it.
LABELS = [
    ("FP1", "fp1_only"),
    ("FP2", "fp2_only"),
    ("F3", "f3_only"),
    ("F4", "f4_only"),
    ("AF3", "af3_only"),
    ("AF4", "af4_only"),
]
label_order = [lbl for lbl, _ in LABELS]
selection_by_label = {lbl: sel for lbl, sel in LABELS}


def best_channel_per_session(df: pd.DataFrame, selection: str) -> pd.DataFrame:
    """Per-session best-channel row (argmax f1 over channels) for one selection.

    Each "_only" selection has exactly one channel, so this just picks that
    channel's row per session (kept for symmetry with the region boxplot).
    """
    sub = df[df.selection == selection]
    if sub.empty:
        return sub
    return sub.loc[sub.groupby("session")["f1"].idxmax()]


records = []
channel_records = []
present_labels = set()
for ds, path in SRC.items():
    if not path.exists():
        continue
    df = pd.read_csv(path)
    df = df[df.center_method == "median"]
    for label, selection in LABELS:
        best = best_channel_per_session(df, selection)
        if best.empty:
            continue
        present_labels.add(label)
        for v in best["f1"].values:
            records.append({"Channel": label, "Dataset": DSN[ds], "F1": v})
        for ch, n in best["channel"].value_counts().items():
            channel_records.append({
                "Channel": label, "Dataset": DSN[ds],
                "channel": display_channel(ds, ch), "n": n,
            })

label_order = [lbl for lbl in label_order if lbl in present_labels]
plotdf = pd.DataFrame(records)
chandf = pd.DataFrame(channel_records).groupby(
    ["Channel", "Dataset", "channel"], as_index=False)["n"].sum()


def channel_label(chan: str, ds_name: str) -> str | None:
    sub = chandf[(chandf.Channel == chan) & (chandf.Dataset == ds_name)]
    if sub.empty:
        return None
    return sub.sort_values("n", ascending=False).iloc[0]["channel"]


sns.set_style("whitegrid")
fig, ax = plt.subplots(figsize=(10, 6))
sns.boxplot(
    data=plotdf, x="Channel", y="F1", hue="Dataset", order=label_order,
    palette={"Internal": "#4C72B0", "Cao2018": "#55A868"}, width=0.6, fliersize=3, ax=ax,
)
ax.set_ylim(0, 1.12)
ax.set_xlabel("Single channel")
ax.set_ylabel("Session-level macro $F_1$")
ax.set_title("Single-channel-only session-level macro $F_1$ (median center), Internal vs. Cao2018")
ax.legend(title=None, loc="lower right", framealpha=0.9)

# recover each box's x-center + hue from its PathPatch, then label with the actual channel
hue_order = ["Internal", "Cao2018"]
color = {"Internal": "#4C72B0", "Cao2018": "#55A868"}
target_rgb = {ds_name: mcolors.to_rgb(color[ds_name]) for ds_name in hue_order}

box_patches = [p for p in ax.patches if type(p).__name__ == "PathPatch"]
box_info = []
for p in box_patches:
    xs = [v[0] for v in p.get_path().vertices]
    cx = (min(xs) + max(xs)) / 2
    fc = p.get_facecolor()[:3]
    ds_name = min(hue_order, key=lambda d: sum((a - b) ** 2 for a, b in zip(fc, target_rgb[d])))
    box_info.append((cx, ds_name))
box_info.sort(key=lambda t: t[0])

# Match each box to its nearest tick position rather than assuming every label
# has both hues present (AF3/AF4 only exist for Raja, so those ticks have one box).
for cx, ds_name in box_info:
    tick = round(cx)
    if not (0 <= tick < len(label_order)):
        continue
    chan = label_order[tick]
    label = channel_label(chan, ds_name)
    if label is None:
        continue
    ax.text(cx, 1.06, label, ha="center", va="bottom", fontsize=8,
             rotation=0, color=color[ds_name])

fig.tight_layout()
fig.savefig(FIGDIR / "fig_exp1_single_channel_boxplot.pdf", bbox_inches="tight")
fig.savefig(FIGDIR / "fig_exp1_single_channel_boxplot.png", dpi=150, bbox_inches="tight")
print("wrote fig_exp1_single_channel_boxplot.pdf/.png")

# console summary
print("\nmedians:")
print(plotdf.groupby(["Channel", "Dataset"])["F1"].median().reindex(label_order, level="Channel").round(4))
print("\nchannel per box:")
for chan in label_order:
    for ds_name in hue_order:
        label = channel_label(chan, ds_name)
        if label is not None:
            print(f"  {chan:6s} {ds_name:8s} {label}")
