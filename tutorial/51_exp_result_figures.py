"""Regenerate result-section summary figures from exp41 Cao/Raja CSV output.

This is a repo-local adaptation of the archived result-figure generator, scoped
to the two figures still owned by that generator:

- writing/e_result/figures/fig_condition_prf.pdf
- writing/e_result/figures/fig_f1_by_dataset.pdf

The epoch-duration and channel-selection figures are intentionally left to their
own tutorial scripts.
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "writing" / "e_result" / "figures"
STRATEGY_CSV = REPO_ROOT / "runs" / "exp41_cao_30s" / "exp41_strategy_comparison_summary.csv"

# DBO intentionally excluded because DBO is reserved for a future paper.
CONDITIONS = ["BLINKER-concat", "MNE-annot", "Proposed-Mean", "Proposed-Med"]

BLUE = "#0072B2"
ORANGE = "#E69F00"
GREEN = "#009E73"
VERMILLION = "#D55E00"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def require_row(rows: list[dict[str, str]], **criteria: object) -> dict[str, str]:
    matches = [
        row for row in rows
        if all(row[key] == str(value) for key, value in criteria.items())
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one row for {criteria}, found {len(matches)}")
    return matches[0]


def add_bar_labels(ax, bars) -> None:
    for bar in bars:
        height = bar.get_height()
        ax.annotate(
            f"{height:.3f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            rotation=90,
        )


def finish_bar_axes(ax, ymax: float = 1.08) -> None:
    ax.set_ylim(0, ymax)
    ax.grid(axis="y", color="#d9d9d9", linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def savefig(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, bbox_inches="tight")
    plt.close()


def make_condition_prf(strategy_rows: list[dict[str, str]]) -> Path:
    metrics = [
        ("macro_precision", "Precision", BLUE),
        ("macro_recall", "Recall", ORANGE),
        ("macro_f1", "F1", GREEN),
    ]
    values: dict[str, list[float]] = {metric: [] for metric, _, _ in metrics}

    for condition in CONDITIONS:
        row = require_row(strategy_rows, dataset="all", condition=condition)
        for metric, _, _ in metrics:
            values[metric].append(float(row[metric]))

    x = list(range(len(CONDITIONS)))
    width = 0.24
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for i, (metric, label, color) in enumerate(metrics):
        offsets = [pos + (i - 1) * width for pos in x]
        bars = ax.bar(offsets, values[metric], width, label=label, color=color)
        add_bar_labels(ax, bars)

    ax.set_xticks(x)
    ax.set_xticklabels(CONDITIONS, rotation=20, ha="right")
    ax.set_ylabel("Macro score")
    ax.set_xlabel("Condition")
    ax.legend(frameon=False, ncols=3, loc="upper center", bbox_to_anchor=(0.5, 1.12))
    finish_bar_axes(ax)

    out = OUT_DIR / "fig_condition_prf.pdf"
    savefig(out)
    return out


def make_f1_by_dataset(strategy_rows: list[dict[str, str]]) -> Path:
    datasets = [("raja", "Raja", BLUE), ("cao2018", "Cao2018", VERMILLION)]
    values: dict[str, list[float]] = {dataset: [] for dataset, _, _ in datasets}

    for condition in CONDITIONS:
        for dataset, _, _ in datasets:
            row = require_row(strategy_rows, dataset=dataset, condition=condition)
            values[dataset].append(float(row["macro_f1"]))

    x = list(range(len(CONDITIONS)))
    width = 0.34
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for i, (dataset, label, color) in enumerate(datasets):
        offsets = [pos + (i - 0.5) * width for pos in x]
        bars = ax.bar(offsets, values[dataset], width, label=label, color=color)
        add_bar_labels(ax, bars)

    ax.set_xticks(x)
    ax.set_xticklabels(CONDITIONS, rotation=20, ha="right")
    ax.set_ylabel("Macro F1")
    ax.set_xlabel("Condition")
    ax.legend(frameon=False, ncols=2, loc="upper center", bbox_to_anchor=(0.5, 1.12))
    finish_bar_axes(ax)

    out = OUT_DIR / "fig_f1_by_dataset.pdf"
    savefig(out)
    return out


def main() -> int:
    plt.rcParams.update({
        "font.size": 9,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })

    strategy_rows = read_csv(STRATEGY_CSV)
    outputs = [
        make_condition_prf(strategy_rows),
        make_f1_by_dataset(strategy_rows),
    ]
    for path in outputs:
        print(f"Wrote {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
