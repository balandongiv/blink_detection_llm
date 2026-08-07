"""Shared data layer for every manuscript table/figure generator.

Single source of truth for the published numbers: the directories configured in
``experiment_script/setup/exp_path.yaml`` (``out_dir: publication_results``). No
generator may read ``runs/``, ``runs0/`` or ``runs_second_iteration/`` — those are
working directories whose contents do not match the published manuscript.

Only three experiments have published results:

``exp1``
    Channel-selection ablation — 18-20 channel groups x {median, mean} x 32 channels.
``exp2``
    Strategy comparison — four conditions on the ``all_channel`` gate.
``exp3``
    Epoch-duration sweep — 10/20/30/40/50/60/120 s.

Every four-condition comparison uses **best-channel-per-session** aggregation: for each
session take the row with the highest event-level F1, then average across sessions. The
same rule is applied to all four conditions so no condition is given a private advantage.
See ``writing/VALUE_AUDIT.md``.
"""
from __future__ import annotations

import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.project_paths import EXP_SETUP_DIR, load_exp_config  # noqa: E402

_PATH_CFG = load_exp_config(EXP_SETUP_DIR / "exp_path.yaml")

ER = REPO / "writing" / "e_result"
FIGDIR = REPO / "writing" / "figures"
ER.mkdir(parents=True, exist_ok=True)
FIGDIR.mkdir(parents=True, exist_ok=True)

CONDS = ["BLINKER-concat", "MNE-annot", "Proposed-Mean", "Proposed-Med"]
DSN = {"raja": "Raja", "cao": "Cao2018"}
#: Channel-selection group holding the per-channel rows (one row per electrode).
ALL_CHANNEL = "all_channel"
#: Epoch durations present in the exp3 sweep.
DURATIONS = [10, 20, 30, 40, 50, 60, 120]
#: Fine-grained region order used to lay out the channel-ablation table. The trailing
#: catch-all block keeps midline and off-region electrodes (Fz, F7, T3, A1, ...) visible
#: instead of silently dropping them from the table.
REGION_ORDER = [
    "frontal_left", "frontal_right", "central_left", "central_right",
    "parietal_left", "parietal_right", "occipital_left", "occipital_right",
    "temporal_parietal_left", "temporal_parietal_right",
    "midline_or_outside", "unassigned",
]

#: Groups in ``brain_region_*.yaml`` that are selection gates, not anatomical regions:
#: coarse unions of the ``_left``/``_right`` pairs, single-channel probes, and the
#: full-montage umbrella. Including them would make the channel->region map ambiguous.
_NON_REGION_GROUPS = frozenset({
    "all_channel", "frontal", "central", "parietal", "occipital", "posterior",
})

_FILES = {
    "exp1": ("exp1", "exp1_channel_selection_{ds}_results.csv"),
    "exp2": ("exp2", "exp2_strategy_comparison_{ds}_results.csv"),
    "exp3": ("exp3", "exp3_epoch_duration_{ds}_results.csv"),
}
_SUMMARY = {
    "exp1": "exp1_channel_selection_{ds}_summary.csv",
    "exp3": "exp3_epoch_duration_{ds}_summary.csv",
}

SRC_COMMENT = "% Source: publication_results/; script experiment_script/{script}"


def _dataset_key(ds: str) -> str:
    """Normalise a dataset alias to the key used in ``exp_path.yaml``."""
    return "raja" if ds == "raja" else "cao2018"


def result_path(exp: str, ds: str) -> Path:
    """Absolute path to an experiment's per-session results CSV."""
    exp_key, pattern = _FILES[exp]
    out_dir = _PATH_CFG["out_dirs"][exp_key][_dataset_key(ds)]
    return REPO / out_dir / pattern.format(ds=_dataset_key(ds))


def summary_path(exp: str, ds: str) -> Path:
    """Absolute path to an experiment's summary CSV (exp1 and exp3 only)."""
    exp_key = _FILES[exp][0]
    out_dir = _PATH_CFG["out_dirs"][exp_key][_dataset_key(ds)]
    return REPO / out_dir / _SUMMARY[exp].format(ds=_dataset_key(ds))


def load(exp: str, ds: str, **read_csv_kwargs) -> pd.DataFrame:
    """Load a published results CSV. ``ds`` is ``"raja"`` or ``"cao"``."""
    path = result_path(exp, ds)
    if not path.exists():
        raise SystemExit(
            f"missing published results: {path}\n"
            "Every manuscript artifact is generated from publication_results/ only."
        )
    return pd.read_csv(path, **read_csv_kwargs)


def bps(df: pd.DataFrame) -> pd.DataFrame:
    """Best row per session (argmax F1) — the best-channel-per-session operating point."""
    return df.loc[df.groupby("session")["f1"].idxmax()].copy()


def load_exp2_best() -> dict[tuple[str, str], pd.DataFrame]:
    """``(dataset, condition) -> best-channel-per-session frame`` for all four conditions."""
    best = {}
    for ds in ["raja", "cao"]:
        df = load("exp2", ds)
        for cond in CONDS:
            best[(ds, cond)] = bps(df[df["condition"] == cond])
    return best


def macro(best: dict, ds: str, cond: str) -> tuple[float, float, float]:
    """Macro-averaged (precision, recall, F1) for one dataset and condition."""
    b = best[(ds, cond)]
    return b["precision"].mean(), b["recall"].mean(), b["f1"].mean()


def macro_pooled(best: dict, cond: str) -> tuple[float, float, float]:
    """Macro-averaged (precision, recall, F1) pooled over both datasets."""
    f = pd.concat([best[("raja", cond)], best[("cao", cond)]])
    return f["precision"].mean(), f["recall"].mean(), f["f1"].mean()


def paired_f1(best: dict, cond_a: str, cond_b: str,
              ds_list=("raja", "cao")) -> tuple[np.ndarray, np.ndarray]:
    """Session-matched F1 vectors for two conditions, keyed by ``dataset/session``."""
    def keyed(cond):
        frames = [
            best[(ds, cond)].assign(_k=ds + "/" + best[(ds, cond)]["session"])
            for ds in ds_list
        ]
        return pd.concat(frames).set_index("_k")["f1"]

    a, b = keyed(cond_a), keyed(cond_b)
    common = a.index.intersection(b.index)
    return a.loc[common].to_numpy(), b.loc[common].to_numpy()


def bonferroni_wilcoxon(best: dict, alternative: str = "two-sided") -> dict:
    """Pairwise Wilcoxon p-values over all six condition pairs, Bonferroni-corrected."""
    n_pairs = len(list(combinations(CONDS, 2)))
    out = {}
    for a_c, b_c in combinations(CONDS, 2):
        a, b = paired_f1(best, a_c, b_c)
        _, p = stats.wilcoxon(a, b, alternative=alternative)
        out[(a_c, b_c)] = min(1.0, p * n_pairs)
    return out


def region_map(ds: str) -> dict[str, str]:
    """``channel -> fine anatomical region`` exactly as the exp1 run assigned it.

    Only the fine ``_left``/``_right`` groups are anatomical; the coarse unions,
    the ``*_only`` single-channel probes and ``all_channel`` are selection gates and
    are skipped, otherwise every electrode would end up labelled with whichever gate
    happened to be last in the file. Electrodes outside the curated regions fall back
    to the ``Note.midline_or_outside`` list, then to ``"unassigned"``.
    """
    yml = REPO / ("brain_region_raja.yaml" if ds == "raja" else "brain_region_cao2018.yaml")
    doc = yaml.safe_load(yml.read_text())

    def label(ch) -> str:
        return (f"E{ch}" if ds == "raja" else str(ch)).upper()

    out = {}
    for group, channels in doc["eeg_regions"].items():
        if group in _NON_REGION_GROUPS or group.endswith("_only"):
            continue
        for ch in channels:
            out[label(ch)] = group

    for ch in doc.get("Note", {}).get("midline_or_outside", []) or []:
        out.setdefault(label(ch), "midline_or_outside")
    return out


#: 10--20 labels whose conventional spelling is not simply all-uppercase.
_1020_SPELLING = {"FP1": "Fp1", "FP2": "Fp2", "FZ": "Fz", "CZ": "Cz",
                  "PZ": "Pz", "OZ": "Oz", "FCZ": "FCz", "CPZ": "CPz"}


def spell_1020(name: str) -> str:
    """Conventional 10--20 spelling: ``fp1`` -> ``Fp1``, ``po3`` -> ``PO3``, ``cz`` -> ``Cz``."""
    upper = str(name).upper()
    return _1020_SPELLING.get(upper, upper)


def egi_to_1020() -> dict[str, str]:
    """Raja EGI HydroCel label -> 10--20 name.

    Read from the ``egi_pair`` block of ``brain_region_raja.yaml``, which covers all 32
    recorded electrodes. ``32_ch.csv`` is not used: it leaves several channels unmapped
    (E3 and E23 in particular, which are AF4 and AF3), and reporting those as a bare EGI
    index makes the channel table unreadable for anyone not working in HydroCel indices.
    """
    doc = yaml.safe_load((REPO / "brain_region_raja.yaml").read_text())
    pairs = doc.get("egi_pair") or []
    out = {}
    for entry in pairs:
        for name, egi_id in entry.items():
            out[f"E{int(egi_id)}"] = spell_1020(name)
    return out


def per_channel(ds: str) -> pd.DataFrame:
    """One row per electrode: mean P/R/F1 over sessions, with region and 10--20 name.

    Read straight from the ``selection == "all_channel"`` rows of the exp1 results —
    these are already per-channel, so no region-level aggregation is applied.
    """
    df = load("exp1", ds)
    df = df[(df["center_method"] == "median") & (df["selection"] == ALL_CHANNEL)]
    if df.empty:
        raise SystemExit(
            f"no selection=={ALL_CHANNEL!r} rows in {result_path('exp1', ds)} — "
            "the per-channel table cannot be built."
        )
    g = (df.groupby("channel")
           .agg(p=("precision", "mean"), r=("recall", "mean"),
                f1=("f1", "mean"), n=("session", "nunique"))
           .reset_index().rename(columns={"channel": "ch"}))
    rmap = region_map(ds)
    g["region"] = g.ch.apply(lambda c: rmap.get(str(c).upper(), "unassigned"))
    if ds == "raja":
        names = egi_to_1020()
        g["name1020"] = g.ch.apply(lambda c: names.get(str(c), "--"))
    else:
        g["name1020"] = g.ch.apply(spell_1020)
    # Scalp location is what the reader reasons about, so it is the label used in the
    # prose and in every packet; the raw EGI index stays available in `ch` for the
    # channel-map table.
    g["display"] = g["name1020"]
    return g


def display_channel(ds: str, channel: str) -> str:
    """Scalp-location label for a raw channel label from any results CSV."""
    if ds == "raja":
        return egi_to_1020().get(str(channel), str(channel))
    return spell_1020(channel)


def fmt(x: float) -> str:
    """Four-decimal metric formatting used throughout the result tables."""
    return f"{x:.4f}"


def tex_escape(s) -> str:
    """Escape the one character that actually bites us in session/subject labels."""
    return str(s).replace("_", r"\_")


def write_tex(path: Path, lines: list[str], script: str) -> None:
    """Write a LaTeX fragment with a provenance comment as its first line."""
    body = [SRC_COMMENT.format(script=script), *lines]
    Path(path).write_text("\n".join(body) + "\n", encoding="utf-8")
    print("wrote", path.relative_to(REPO))


def save_fig(fig, stem: str) -> None:
    """Save a figure as both PDF (for LaTeX) and PNG (for quick review)."""
    fig.savefig(FIGDIR / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(FIGDIR / f"{stem}.png", dpi=150, bbox_inches="tight")
    print(f"wrote figures/{stem}.pdf, figures/{stem}.png")
