"""Regenerate the epoch-duration F1 figure from exp40_cao summary CSV.

This is a repo-local copy of the epoch panel logic from the archived figure
generator, restricted to fig_f1_by_epoch.pdf so the other result figures are
left untouched.
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "writing" / "e_result" / "figures"
EPOCH_CSV = REPO_ROOT / "runs" / "exp40_cao" / "exp1_epoch_duration_summary.csv"
EPOCHS = [10.0, 20.0, 30.0, 40.0, 60.0]
PURPLE = "#CC79A7"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def require_epoch_row(rows: list[dict[str, str]], dataset: str, epoch: float) -> dict[str, str]:
    matches = [
        row for row in rows
        if row["dataset"] == dataset and float(row["epoch_duration_s"]) == epoch
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one epoch row for dataset={dataset}, epoch={epoch}")
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

    rows = read_csv(EPOCH_CSV)
    plotted_rows: list[list[object]] = []
    f1_values: list[float] = []
    for epoch in EPOCHS:
        row = require_epoch_row(rows, dataset="all", epoch=epoch)
        plotted_rows.append([int(epoch), row["macro_f1"]])
        f1_values.append(float(row["macro_f1"]))

    fig, ax = plt.subplots(figsize=(6.4, 3.9))
    x = list(range(len(EPOCHS)))
    bars = ax.bar(x, f1_values, width=0.58, color=PURPLE)
    add_bar_labels(ax, bars)
    ax.set_xticks(x)
    ax.set_xticklabels([str(int(epoch)) for epoch in EPOCHS])
    ax.set_ylabel("Macro F1")
    ax.set_xlabel("Epoch duration (s)")
    finish_bar_axes(ax)

    out = OUT_DIR / "fig_f1_by_epoch.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, bbox_inches="tight")
    plt.close(fig)

    print("fig_f1_by_epoch.pdf")
    print("epoch_duration_s,macro_f1")
    for row in plotted_rows:
        print(",".join(str(item) for item in row))
    print(f"Wrote {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
