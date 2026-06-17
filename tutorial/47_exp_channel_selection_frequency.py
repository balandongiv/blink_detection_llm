"""EEG channel-selection frequency analysis for Raja and Cao2018.

Input
-----
runs/exp41_cao_30s/exp41_strategy_comparison_results.csv

Outputs
-------
runs/exp_channel_selection/channel_freq_by_dataset.csv
runs/exp_channel_selection/channel_freq_by_dataset_method.csv
runs/exp_channel_selection/channel_freq_by_subject.csv
runs/exp_channel_selection/method_overlap.csv
writing/e_result/tab_channel_selection.tex
writing/e_result/figures/fig_channel_selection.pdf
runs/reports/R4_channel_selection.md
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = REPO_ROOT / "runs" / "exp41_cao_30s" / "exp41_strategy_comparison_results.csv"
BRAIN_REGION_YAML = REPO_ROOT / "brain_region.yaml"
OUTPUT_DIR = REPO_ROOT / "runs" / "exp_channel_selection"
REPORT_PATH = REPO_ROOT / "runs" / "reports" / "R4_channel_selection.md"
TABLE_PATH = REPO_ROOT / "writing" / "e_result" / "tab_channel_selection.tex"
FIGURE_PATH = REPO_ROOT / "writing" / "e_result" / "figures" / "fig_channel_selection.pdf"

VISIBLE_METHODS = ["BLINKER-concat", "MNE-annot", "Proposed-Mean", "Proposed-Med"]
DATASETS = ["raja", "cao2018"]
REQUIRED_COLUMNS = {
    "dataset",
    "session",
    "condition",
    "best_channel",
    "tp",
    "fp",
    "fn",
    "precision",
    "recall",
    "f1",
    "wall_clock_s",
}
DATASET_LABELS = {"raja": "Raja", "cao2018": "Cao2018"}


def _read_region_map(path: Path) -> dict[str, str]:
    """Read the simple eeg_regions YAML structure as channel -> region."""
    if not path.exists():
        return {}

    try:
        import yaml  # type: ignore

        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        regions = payload.get("eeg_regions", {})
        return {
            str(channel): str(region)
            for region, channels in regions.items()
            for channel in (channels or [])
        }
    except Exception:
        # Fallback for the repository's simple mapping:
        # eeg_regions: / two-space region: / four-space list items.
        channel_to_region: dict[str, str] = {}
        current_region: str | None = None
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.rstrip()
            region_match = re.match(r"^\s{2}([^:#]+):\s*$", line)
            if region_match:
                current_region = region_match.group(1).strip()
                continue
            channel_match = re.match(r"^\s{4}-\s*(\S+)\s*$", line)
            if current_region and channel_match:
                channel_to_region[channel_match.group(1).strip()] = current_region
        return channel_to_region


def _derive_subject(row: pd.Series) -> str:
    session = str(row["session"])
    first = session.split("/", 1)[0]
    if row["dataset"] == "raja":
        match = re.match(r"^(S\d+)$", first)
        if not match:
            raise ValueError(f"Cannot derive Raja subject from session: {session}")
        return match.group(1)
    if row["dataset"] == "cao2018":
        if not first:
            raise ValueError(f"Cannot derive Cao2018 subject from session: {session}")
        return first
    raise ValueError(f"Unexpected dataset while deriving subject: {row['dataset']}")


def _validate_input(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required input columns: {sorted(missing)}")

    datasets = set(df["dataset"].dropna().unique())
    if datasets != set(DATASETS):
        raise ValueError(f"Unexpected datasets: {sorted(datasets)}; expected {DATASETS}")

    methods = set(df["condition"].dropna().unique())
    if methods != set(VISIBLE_METHODS):
        raise ValueError(f"Unexpected conditions: {sorted(methods)}; expected {VISIBLE_METHODS}")

    duplicated = df.duplicated(["dataset", "session", "condition"])
    if duplicated.any():
        dupes = df.loc[duplicated, ["dataset", "session", "condition"]]
        raise ValueError(f"Duplicate dataset/session/condition rows found:\n{dupes}")

    counts = df.groupby(["dataset", "session"])["condition"].nunique()
    incomplete = counts[counts != len(VISIBLE_METHODS)]
    if not incomplete.empty:
        raise ValueError(f"Sessions without all four visible methods:\n{incomplete}")

    if df["best_channel"].isna().any() or (df["best_channel"].astype(str).str.len() == 0).any():
        raise ValueError("Input contains missing or empty best_channel values")


def _frequency_table(
    df: pd.DataFrame,
    group_cols: list[str],
    denominator_cols: list[str],
) -> pd.DataFrame:
    counts = (
        df.groupby(group_cols, as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    denoms = (
        df.groupby(denominator_cols, as_index=False)
        .size()
        .rename(columns={"size": "total_selections"})
    )
    out = counts.merge(denoms, on=denominator_cols, how="left")
    out["fraction"] = out["count"] / out["total_selections"]
    return out.sort_values(denominator_cols + ["count", "best_channel"], ascending=[True] * len(denominator_cols) + [False, True])


def _subject_table(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (dataset, subject), group in df.groupby(["dataset", "subject"], sort=True):
        counts = group["best_channel"].value_counts()
        top_count = int(counts.iloc[0])
        tied_channels = sorted(counts[counts == top_count].index.astype(str).tolist())
        rows.append(
            {
                "dataset": dataset,
                "subject": subject,
                "n_sessions": int(group["session"].nunique()),
                "total_selections": int(len(group)),
                "top_channel": tied_channels[0],
                "top_count": top_count,
                "top_fraction": top_count / len(group),
                "tied_channels": ";".join(tied_channels),
                "is_tie": len(tied_channels) > 1,
            }
        )
    return pd.DataFrame(rows).sort_values(["dataset", "subject"])


def _method_overlap(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for dataset, group in df.groupby("dataset", sort=True):
        pivot = group.pivot(index="session", columns="condition", values="best_channel")
        pivot = pivot[VISIBLE_METHODS]
        total = len(pivot)
        full_agree = pivot.nunique(axis=1).eq(1)
        rows.append(
            {
                "dataset": dataset,
                "comparison": "all_4",
                "method_a": "all",
                "method_b": "all",
                "agreement_sessions": int(full_agree.sum()),
                "total_sessions": int(total),
                "fraction": float(full_agree.mean()),
            }
        )
        for method_a, method_b in combinations(VISIBLE_METHODS, 2):
            agree = pivot[method_a].eq(pivot[method_b])
            rows.append(
                {
                    "dataset": dataset,
                    "comparison": f"{method_a}__{method_b}",
                    "method_a": method_a,
                    "method_b": method_b,
                    "agreement_sessions": int(agree.sum()),
                    "total_sessions": int(total),
                    "fraction": float(agree.mean()),
                }
            )
    return pd.DataFrame(rows)


def _format_fraction(count: int, total: int, digits: int = 3) -> str:
    return f"{count}/{total} ({count / total:.{digits}f})"


def _latex_escape(value: object) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _top_summary(freq: pd.DataFrame, dataset: str, top_n: int = 5) -> str:
    rows = freq[freq["dataset"] == dataset].head(top_n)
    return "; ".join(
        f"{_latex_escape(row['best_channel'])} {_format_fraction(int(row['count']), int(row['total_selections']))}"
        for _, row in rows.iterrows()
    )


def _region_summary(df: pd.DataFrame, dataset: str, top_n: int = 3) -> tuple[str, int, int]:
    subset = df[df["dataset"] == dataset]
    mapped = subset[subset["region"].notna()]
    if mapped.empty:
        return "No mapped selections", 0, int(len(subset))
    counts = (
        mapped.groupby("region", as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values(["count", "region"], ascending=[False, True])
        .head(top_n)
    )
    total = len(subset)
    summary = "; ".join(
        f"{_latex_escape(row['region'])} {_format_fraction(int(row['count']), total)}"
        for _, row in counts.iterrows()
    )
    return summary, int(len(mapped)), int(total)


def _write_latex_table(freq: pd.DataFrame, df: pd.DataFrame, path: Path) -> None:
    lines = [
        "% Source: runs/exp41_cao_30s/exp41_strategy_comparison_results.csv; script tutorial/47_exp_channel_selection_frequency.py",
        r"\begin{table}[ht]",
        r"  \centering",
        r"  \scriptsize",
        r"  \setlength{\tabcolsep}{3pt}",
        r"  \caption{Best-channel selection frequencies pooled over the four visible methods. Region rows use only labels present in \texttt{brain\_region.yaml}; unmapped labels are not forced into a cross-dataset region.}",
        r"  \label{tab:channel_selection}",
        r"  \begin{tabular}{llp{0.68\linewidth}}",
        r"    \toprule",
        r"    Dataset & Summary & Frequencies \\",
        r"    \midrule",
    ]

    for dataset in DATASETS:
        label = DATASET_LABELS[dataset]
        lines.append(
            f"    {_latex_escape(label)} & Channels & {_top_summary(freq, dataset)} \\\\"
        )
        region_text, mapped_n, total_n = _region_summary(df, dataset)
        lines.append(
            f"    {_latex_escape(label)} & Regions & {region_text}; mapped {_format_fraction(mapped_n, total_n)} \\\\"
        )

    lines.extend(
        [
            r"    \bottomrule",
            r"  \end{tabular}",
            r"\end{table}",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_figure(freq_method: pd.DataFrame, path: Path) -> None:
    plot_df = (
        freq_method.sort_values(["dataset", "condition", "count"], ascending=[True, True, False])
        .groupby(["dataset", "condition"], as_index=False)
        .head(5)
    )

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    palette = {
        "BLINKER-concat": "#4C78A8",
        "MNE-annot": "#F58518",
        "Proposed-Mean": "#54A24B",
        "Proposed-Med": "#B279A2",
    }
    for ax, dataset in zip(axes, DATASETS):
        subset = plot_df[plot_df["dataset"] == dataset].copy()
        labels = [f"{row.best_channel}\n{row.condition}" for row in subset.itertuples(index=False)]
        colours = [palette[row.condition] for row in subset.itertuples(index=False)]
        ax.bar(range(len(subset)), subset["fraction"], color=colours, width=0.72)
        ax.set_title(DATASET_LABELS[dataset], fontsize=11)
        ax.set_xticks(range(len(subset)))
        ax.set_xticklabels(labels, rotation=70, ha="right", fontsize=7)
        ax.set_ylim(0, max(0.55, float(plot_df["fraction"].max()) * 1.15))
        ax.grid(axis="y", alpha=0.25, linewidth=0.6)
        ax.tick_params(axis="y", labelsize=8)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
    axes[0].set_ylabel("Selection fraction within method", fontsize=9)

    handles = [plt.Rectangle((0, 0), 1, 1, color=palette[m]) for m in VISIBLE_METHODS]
    fig.legend(handles, VISIBLE_METHODS, loc="upper center", ncol=4, frameon=False, fontsize=8)
    fig.suptitle("Top selected EEG channels by dataset and method", fontsize=12, y=1.02)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def _markdown_top_dataset(freq: pd.DataFrame, dataset: str, top_n: int = 5) -> list[str]:
    rows = freq[freq["dataset"] == dataset].head(top_n)
    return [
        f"- {DATASET_LABELS[dataset]}: "
        + "; ".join(
            f"{row['best_channel']} {_format_fraction(int(row['count']), int(row['total_selections']))}"
            for _, row in rows.iterrows()
        )
    ]


def _markdown_top_method(freq_method: pd.DataFrame, top_n: int = 3) -> list[str]:
    lines: list[str] = []
    for dataset in DATASETS:
        for method in VISIBLE_METHODS:
            rows = freq_method[
                (freq_method["dataset"] == dataset) & (freq_method["condition"] == method)
            ].head(top_n)
            text = "; ".join(
                f"{row['best_channel']} {_format_fraction(int(row['count']), int(row['total_selections']))}"
                for _, row in rows.iterrows()
            )
            lines.append(f"- {DATASET_LABELS[dataset]} / {method}: {text}")
    return lines


def _write_report(
    df: pd.DataFrame,
    freq: pd.DataFrame,
    freq_method: pd.DataFrame,
    subject_freq: pd.DataFrame,
    overlap: pd.DataFrame,
    region_map: dict[str, str],
    path: Path,
) -> None:
    full_overlap = overlap[overlap["comparison"] == "all_4"]
    pairwise_overlap = overlap[overlap["comparison"] != "all_4"]
    subject_summary = (
        subject_freq.groupby("dataset")
        .agg(
            subjects=("subject", "nunique"),
            median_top_fraction=("top_fraction", "median"),
            mean_top_fraction=("top_fraction", "mean"),
            tied_subjects=("is_tie", "sum"),
        )
        .reset_index()
    )

    mapped = df[df["region"].notna()]
    mapped_counts = (
        mapped.groupby(["dataset", "region"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values(["dataset", "count", "region"], ascending=[True, False, True])
    )
    nonstandard_channels = sorted(
        channel for channel in df["best_channel"].astype(str).unique() if " " in channel
    )

    lines = [
        "# R4 Channel Selection Frequency",
        "",
        "## Input",
        f"- Source CSV: `{INPUT_CSV.relative_to(REPO_ROOT).as_posix()}`",
        "- Subject derivation rule: Raja uses the leading `S<k>` directory before `/`; Cao2018 uses the first path component before `/`.",
        f"- Rows analysed: {len(df)} selections from {df['session'].nunique()} sessions across {len(VISIBLE_METHODS)} methods.",
        "",
        "## Top Channels by Dataset",
        *_markdown_top_dataset(freq, "raja"),
        *_markdown_top_dataset(freq, "cao2018"),
        "",
        "## Top Channels by Dataset and Method",
        *_markdown_top_method(freq_method),
        "",
        "## Cross-Method Agreement",
    ]
    for row in full_overlap.itertuples(index=False):
        lines.append(
            f"- {DATASET_LABELS[row.dataset]} full 4-way agreement: "
            f"{_format_fraction(int(row.agreement_sessions), int(row.total_sessions))}"
        )
    for dataset in DATASETS:
        rows = pairwise_overlap[pairwise_overlap["dataset"] == dataset]
        pair_text = "; ".join(
            f"{row.method_a} vs {row.method_b} {_format_fraction(int(row.agreement_sessions), int(row.total_sessions))}"
            for row in rows.itertuples(index=False)
        )
        lines.append(f"- {DATASET_LABELS[dataset]} pairwise: {pair_text}")

    lines.extend(["", "## Within-Subject Consistency"])
    for row in subject_summary.itertuples(index=False):
        lines.append(
            f"- {DATASET_LABELS[row.dataset]}: subjects={int(row.subjects)}, "
            f"median top-channel fraction={row.median_top_fraction:.3f}, "
            f"mean top-channel fraction={row.mean_top_fraction:.3f}, "
            f"subjects with ties={int(row.tied_subjects)}"
        )

    lines.extend(["", "## Region Mapping"])
    if region_map:
        lines.append(
            f"- Region map loaded from `{BRAIN_REGION_YAML.relative_to(REPO_ROOT).as_posix()}` with {len(region_map)} channel labels."
        )
        for dataset in DATASETS:
            total = int((df["dataset"] == dataset).sum())
            mapped_n = int(((df["dataset"] == dataset) & df["region"].notna()).sum())
            rows = mapped_counts[mapped_counts["dataset"] == dataset]
            if rows.empty:
                lines.append(
                    f"- {DATASET_LABELS[dataset]}: no selected channels were present in the region map; channel frequencies are reported without cross-dataset region forcing."
                )
            else:
                region_text = "; ".join(
                    f"{row['region']} {_format_fraction(int(row['count']), total)}"
                    for _, row in rows.iterrows()
                )
                lines.append(
                    f"- {DATASET_LABELS[dataset]}: mapped selections {_format_fraction(mapped_n, total)}; {region_text}."
                )
    else:
        lines.append("- No usable `brain_region.yaml` mapping was available; no cross-dataset region comparison was made.")

    lines.extend(
        [
            "",
            "## Files Created",
            "- `runs/exp_channel_selection/channel_freq_by_dataset.csv`",
            "- `runs/exp_channel_selection/channel_freq_by_dataset_method.csv`",
            "- `runs/exp_channel_selection/channel_freq_by_subject.csv`",
            "- `runs/exp_channel_selection/method_overlap.csv`",
            "- `writing/e_result/tab_channel_selection.tex`",
            "- `writing/e_result/figures/fig_channel_selection.pdf`",
            "- `tutorial/47_exp_channel_selection_frequency.py`",
            "- `runs/reports/R4_channel_selection.md`",
            "",
            "## Data Caveats",
            "- Fractions in dataset-level channel tables use selection rows as the denominator after pooling the four visible methods.",
            "- The two datasets use different montages; channel labels are not compared directly across datasets.",
            "- The available region map covers only the labels listed in `brain_region.yaml`; unmapped selected labels remain unmapped.",
        ]
    )
    if nonstandard_channels:
        lines.append(
            "- Non-standard `best_channel` labels present in the input CSV were preserved as-is: "
            + ", ".join(f"`{channel}`" for channel in nonstandard_channels)
            + "."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Missing input CSV: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)
    _validate_input(df)
    df = df.copy()
    df["subject"] = df.apply(_derive_subject, axis=1)

    region_map = _read_region_map(BRAIN_REGION_YAML)
    df["region"] = df["best_channel"].map(region_map)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    freq = _frequency_table(df, ["dataset", "best_channel"], ["dataset"])
    freq_method = _frequency_table(df, ["dataset", "condition", "best_channel"], ["dataset", "condition"])
    subject_freq = _subject_table(df)
    overlap = _method_overlap(df)

    freq.to_csv(OUTPUT_DIR / "channel_freq_by_dataset.csv", index=False)
    freq_method.to_csv(OUTPUT_DIR / "channel_freq_by_dataset_method.csv", index=False)
    subject_freq.to_csv(OUTPUT_DIR / "channel_freq_by_subject.csv", index=False)
    overlap.to_csv(OUTPUT_DIR / "method_overlap.csv", index=False)

    _write_latex_table(freq, df, TABLE_PATH)
    _write_figure(freq_method, FIGURE_PATH)
    _write_report(df, freq, freq_method, subject_freq, overlap, region_map, REPORT_PATH)

    print(f"Wrote {OUTPUT_DIR / 'channel_freq_by_dataset.csv'}")
    print(f"Wrote {OUTPUT_DIR / 'channel_freq_by_dataset_method.csv'}")
    print(f"Wrote {OUTPUT_DIR / 'channel_freq_by_subject.csv'}")
    print(f"Wrote {OUTPUT_DIR / 'method_overlap.csv'}")
    print(f"Wrote {TABLE_PATH}")
    print(f"Wrote {FIGURE_PATH}")
    print(f"Wrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
