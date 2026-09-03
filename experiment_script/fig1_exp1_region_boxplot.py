"""Region-grouped box plot of session-level macro F1 (best channel per session, median center).

Each named Stage-A selection group from exp1 (channel_ablation_utils.build_selection_groups)
gets its own box: the bilateral/whole-region group (e.g. "frontal") AND its two hemisphere
halves ("frontal_left", "frontal_right") are shown SEPARATELY, side by side, so the
contribution of the whole region can be compared against each hemisphere in isolation
rather than being pooled into one merged box. Posterior and All have no hemisphere split.
Within each selection, the best-performing channel is taken per session (argmax f1).
Raja and Cao2018 are drawn side by side (hue) in a single figure.

Source: runs0/exp1_channel_cao/exp1_channel_selection_cao2018_results.csv
        runs0/exp1_channel_raja/exp1_channel_selection_raja_results.csv

Produces: writing/figures/fig_exp1_region_boxplot.pdf, .png

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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.project_paths import EXP_SETUP_DIR, load_exp_config  # noqa: E402
import paper_style as S  # noqa: E402

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


# (display label, selection name in the results CSV, region-family index for shading/spacing)
LABELS = [
    ("All", "all_channel", 0),
    ("Frontal", "frontal", 1), ("Frontal-L", "frontal_left", 1), ("Frontal-R", "frontal_right", 1),
    ("Central", "central", 2), ("Central-L", "central_left", 2), ("Central-R", "central_right", 2),
    ("Parietal", "parietal", 3), ("Parietal-L", "parietal_left", 3), ("Parietal-R", "parietal_right", 3),
    ("Occipital", "occipital", 4), ("Occipital-L", "occipital_left", 4), ("Occipital-R", "occipital_right", 4),
    ("Posterior", "posterior", 5),
]
label_order = [lbl for lbl, _, _ in LABELS]
selection_by_label = {lbl: sel for lbl, sel, _ in LABELS}
family_by_label = {lbl: fam for lbl, _, fam in LABELS}


def best_channel_per_session(df: pd.DataFrame, selection: str) -> pd.DataFrame:
    """Per-session best-channel row (argmax f1 over channels) for one selection."""
    sub = df[df.selection == selection]
    if sub.empty:
        return sub
    return sub.loc[sub.groupby("session")["f1"].idxmax()]


records = []
channel_records = []
for ds, path in SRC.items():
    df = pd.read_csv(path)
    df = df[df.center_method == "median"]
    for label, selection, _fam in LABELS:
        best = best_channel_per_session(df, selection)
        if best.empty:
            continue
        for v in best["f1"].values:
            records.append({"Region": label, "Dataset": DSN[ds], "F1": v})
        for ch, n in best["channel"].value_counts().items():
            channel_records.append({
                "Region": label, "Dataset": DSN[ds],
                "channel": display_channel(ds, ch), "n": n,
            })

plotdf = pd.DataFrame(records)
chandf = pd.DataFrame(channel_records).groupby(
    ["Region", "Dataset", "channel"], as_index=False)["n"].sum()


# single most-frequently-"best" channel per region x dataset box, for annotation
def channel_label(region: str, ds_name: str) -> str | None:
    sub = chandf[(chandf.Region == region) & (chandf.Dataset == ds_name)]
    if sub.empty:
        return None
    return sub.sort_values("n", ascending=False).iloc[0]["channel"]


fig, ax = plt.subplots(figsize=(20, 7))
S.style_fig(fig)
sns.boxplot(
    data=plotdf, x="Region", y="F1", hue="Dataset", order=label_order,
    palette=S.DATASET_COLORS, width=0.6, fliersize=2, ax=ax,
)
ax.set_ylim(0, 1.12)
ax.set_xlabel("Selection group")
ax.set_ylabel("Session-level macro $F_1$")
ax.set_title("Best-channel-per-session macro $F_1$ by selection group (median center), Internal vs. Cao2018\n"
             "(whole region shown alongside its own left/right hemisphere halves)")
S.style_axis(ax, grid_axis="both")
legend = ax.legend(title=None, loc="lower right", framealpha=0.9)
for text in legend.get_texts():
    text.set_color(S.NAVY)

# shade alternating region families for readability
fam_seq = [family_by_label[lbl] for lbl in label_order]
prev_fam = None
band_start = None
for i, fam in enumerate(fam_seq + [None]):
    if fam != prev_fam:
        if prev_fam is not None and prev_fam % 2 == 1:
            ax.axvspan(band_start - 0.5, i - 0.5, color=S.PAGE_BG, zorder=0)
        band_start = i
        prev_fam = fam

# recover each box's x-center + hue from its PathPatch, then label with dominant channel(s)
hue_order = ["Internal", "Cao2018"]
color = S.DATASET_COLORS
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

if len(box_info) == len(label_order) * len(hue_order):
    for (cx, ds_name), region in zip(box_info, [r for r in label_order for _ in hue_order]):
        label = channel_label(region, ds_name)
        if label is None:
            continue
        ax.text(cx, 1.06, label, ha="center", va="bottom", fontsize=7.5,
                rotation=90, color=color[ds_name])
else:
    print(f"WARNING: could not recover {len(label_order) * len(hue_order)} box centers "
          f"(got {len(box_info)}); skipping channel annotation")

fig.tight_layout()
fig.savefig(FIGDIR / "fig_exp1_region_boxplot.pdf", bbox_inches="tight")
fig.savefig(FIGDIR / "fig_exp1_region_boxplot.png", dpi=150, bbox_inches="tight")
print("wrote fig_exp1_region_boxplot.pdf/.png")

# console summary
print("\nmedians:")
print(plotdf.groupby(["Region", "Dataset"])["F1"].median().reindex(label_order, level="Region").round(4))
print("\ndominant channel(s) per box:")
for region in label_order:
    for ds_name in hue_order:
        label = channel_label(region, ds_name)
        if label is not None:
            print(f"  {region:12s} {ds_name:8s} {label}")
