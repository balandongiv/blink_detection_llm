from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ROOT = REPO_ROOT / "experiment_output"
OUTPUT_PATH = REPO_ROOT / "tutorial" / "strategy_subject_segment_preference_analysis.md"

FILENAME_TO_STRATEGY = {
    "strategy_a_step1_lane_summary.csv": "strategy_a",
    "strategy_b_step1_lane_summary.csv": "strategy_b",
    "step1_lane_summary.csv": "strategy_c",
    "strategy_d_step1_lane_summary.csv": "strategy_d",
    "strategy_e_step1_lane_summary.csv": "strategy_e",
}

DURATION_BINS = {
    "short_share": "share < 120 ms",
    "typical_share": "share 120-300 ms",
    "slow_share": "share 300-500 ms",
    "closure_share": "share > 500 ms",
}


def strategy_from_filename(name: str) -> str:
    return FILENAME_TO_STRATEGY.get(name, name.replace("_lane_summary.csv", ""))


def choose_best_lane(summary: pd.DataFrame) -> pd.Series:
    return (
        summary.sort_values(
            ["f1", "recall", "precision", "tp", "fp"],
            ascending=[False, False, False, False, True],
        )
        .iloc[0]
    )


def load_reference_stats(reference_path: Path) -> dict[str, float]:
    reference = pd.read_csv(reference_path)
    durations = reference["blink_duration"].astype(float)
    return {
        "n_annotations": int(len(reference)),
        "median_duration": float(durations.median()),
        "mean_duration": float(durations.mean()),
        "short_share": float((durations < 0.12).mean()),
        "typical_share": float(((durations >= 0.12) & (durations <= 0.30)).mean()),
        "slow_share": float(((durations > 0.30) & (durations <= 0.50)).mean()),
        "closure_share": float((durations > 0.50).mean()),
        "long_share": float((durations > 0.40).mean()),
    }


def build_pair_strategy_dataframe() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for pair_dir in sorted(EXPERIMENT_ROOT.glob("*/*")):
        if not pair_dir.is_dir():
            continue
        reference_path = pair_dir / "reference_annotation.csv"
        if not reference_path.exists():
            continue

        ref_stats = load_reference_stats(reference_path)
        subject = pair_dir.parent.name
        segment = pair_dir.name

        for summary_path in sorted(pair_dir.glob("*_lane_summary.csv")):
            summary = pd.read_csv(summary_path)
            if summary.empty:
                continue
            best = choose_best_lane(summary)
            rows.append(
                {
                    "subject": subject,
                    "segment": segment,
                    "strategy": strategy_from_filename(summary_path.name),
                    "best_channel": str(best["channel"]),
                    "tp": int(best["tp"]),
                    "fp": int(best["fp"]),
                    "fn": int(best["fn"]),
                    "precision": float(best["precision"]),
                    "recall": float(best["recall"]),
                    "f1": float(best["f1"]),
                    **ref_stats,
                }
            )

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("No lane-summary artefacts were found under experiment_output.")
    return df


def compute_micro_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for strategy, sub in df.groupby("strategy"):
        tp = int(sub["tp"].sum())
        fp = int(sub["fp"].sum())
        fn = int(sub["fn"].sum())
        micro_precision = tp / (tp + fp) if (tp + fp) else 0.0
        micro_recall = tp / (tp + fn) if (tp + fn) else 0.0
        micro_f1 = (
            2.0 * micro_precision * micro_recall / (micro_precision + micro_recall)
            if (micro_precision + micro_recall)
            else 0.0
        )
        rows.append(
            {
                "strategy": strategy,
                "micro_f1": micro_f1,
                "micro_recall": micro_recall,
                "micro_precision": micro_precision,
                "mean_pair_f1": float(sub["f1"].mean()),
                "mean_pair_recall": float(sub["recall"].mean()),
                "segment_wins": 0,
                "subject_mean_f1_leads": 0,
            }
        )
    return pd.DataFrame(rows)


def annotate_wins(df: pd.DataFrame, summary_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    segment_winners = (
        df.sort_values(
            ["subject", "segment", "f1", "recall", "precision"],
            ascending=[True, True, False, False, False],
        )
        .groupby(["subject", "segment"], as_index=False)
        .head(1)
        .reset_index(drop=True)
    )
    segment_counts = Counter(segment_winners["strategy"])
    summary_df = summary_df.copy()
    summary_df["segment_wins"] = summary_df["strategy"].map(lambda s: segment_counts.get(s, 0))

    subject_means = (
        df.groupby(["subject", "strategy"], as_index=False)
        .agg(mean_f1=("f1", "mean"), mean_recall=("recall", "mean"))
    )
    subject_leads = (
        subject_means.sort_values(
            ["subject", "mean_f1", "mean_recall"],
            ascending=[True, False, False],
        )
        .groupby("subject", as_index=False)
        .head(1)
        .reset_index(drop=True)
    )
    subject_counts = Counter(subject_leads["strategy"])
    summary_df["subject_mean_f1_leads"] = summary_df["strategy"].map(
        lambda s: subject_counts.get(s, 0)
    )
    return segment_winners, summary_df


def format_pct(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def format_duration_mix(row: pd.Series) -> str:
    return (
        f"S={format_pct(row['short_share'])}, "
        f"T={format_pct(row['typical_share'])}, "
        f"L={format_pct(row['slow_share'])}, "
        f"C={format_pct(row['closure_share'])}"
    )


def difficulty_flag(best_f1: float) -> str:
    if best_f1 < 0.20:
        return "drop-candidate"
    if best_f1 < 0.55:
        return "caution"
    return "keep"


def subject_action(mean_best_f1: float, min_best_f1: float) -> str:
    if mean_best_f1 <= 0.40 or min_best_f1 < 0.05:
        return "drop-candidate"
    if mean_best_f1 < 0.60 or min_best_f1 < 0.20:
        return "caution"
    return "keep"


def render_markdown_table(df: pd.DataFrame) -> str:
    display = df.fillna("")
    headers = [str(col) for col in display.columns]
    rows = [[str(value) for value in row] for row in display.to_numpy().tolist()]
    widths = [len(header) for header in headers]
    for row in rows:
        for i, value in enumerate(row):
            widths[i] = max(widths[i], len(value))
    header_line = "| " + " | ".join(header.ljust(widths[i]) for i, header in enumerate(headers)) + " |"
    divider = "| " + " | ".join("-" * widths[i] for i in range(len(headers))) + " |"
    body = [
        "| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(headers))) + " |"
        for row in rows
    ]
    return "\n".join([header_line, divider, *body])


def build_subject_table(df: pd.DataFrame, segment_winners: pd.DataFrame) -> pd.DataFrame:
    subject_mean = (
        df.groupby(["subject", "strategy"], as_index=False)
        .agg(mean_f1=("f1", "mean"), mean_recall=("recall", "mean"))
    )
    subject_best_mean_f1 = (
        subject_mean.sort_values(
            ["subject", "mean_f1", "mean_recall"], ascending=[True, False, False]
        )
        .groupby("subject", as_index=False)
        .head(1)
        .rename(columns={"strategy": "best_mean_f1_strategy"})
        .reset_index(drop=True)
    )
    subject_best_mean_recall = (
        subject_mean.sort_values(
            ["subject", "mean_recall", "mean_f1"], ascending=[True, False, False]
        )
        .groupby("subject", as_index=False)
        .head(1)
        .rename(columns={"strategy": "best_mean_recall_any_fp_strategy"})
        .reset_index(drop=True)
    )

    segment_win_counts = (
        segment_winners.groupby(["subject", "strategy"]).size().reset_index(name="wins")
    )
    dominant_wins = (
        segment_win_counts.sort_values(["subject", "wins", "strategy"], ascending=[True, False, True])
        .groupby("subject", as_index=False)
        .head(1)
        .rename(columns={"strategy": "dominant_segment_winner", "wins": "segment_wins"})
        .reset_index(drop=True)
    )

    best_segments = (
        segment_winners.groupby("subject", as_index=False)
        .agg(
            n_segments=("segment", "nunique"),
            mean_best_f1=("f1", "mean"),
            min_best_f1=("f1", "min"),
            mean_long_share=("long_share", "mean"),
            mean_closure_share=("closure_share", "mean"),
        )
    )

    table = (
        best_segments.merge(subject_best_mean_f1[["subject", "best_mean_f1_strategy"]], on="subject")
        .merge(subject_best_mean_recall[["subject", "best_mean_recall_any_fp_strategy"]], on="subject")
        .merge(dominant_wins[["subject", "dominant_segment_winner", "segment_wins"]], on="subject")
    )
    table["mean_best_f1"] = table["mean_best_f1"].map(lambda x: f"{x:.3f}")
    table["min_best_f1"] = table["min_best_f1"].map(lambda x: f"{x:.3f}")
    table["mean_long_share"] = table["mean_long_share"].map(format_pct)
    table["mean_closure_share"] = table["mean_closure_share"].map(format_pct)
    table["subject_action"] = best_segments.apply(
        lambda row: subject_action(float(row["mean_best_f1"]), float(row["min_best_f1"])),
        axis=1,
    )
    return table[
        [
            "subject",
            "n_segments",
            "dominant_segment_winner",
            "segment_wins",
            "best_mean_f1_strategy",
            "best_mean_recall_any_fp_strategy",
            "mean_best_f1",
            "min_best_f1",
            "mean_long_share",
            "mean_closure_share",
            "subject_action",
        ]
    ].sort_values("subject")


def build_segment_table(df: pd.DataFrame) -> pd.DataFrame:
    best_f1 = (
        df.sort_values(
            ["subject", "segment", "f1", "recall", "precision"],
            ascending=[True, True, False, False, False],
        )
        .groupby(["subject", "segment"], as_index=False)
        .head(2)
    )
    first = best_f1.groupby(["subject", "segment"], as_index=False).nth(0).reset_index()
    second = best_f1.groupby(["subject", "segment"], as_index=False).nth(1).reset_index()
    first = first.rename(columns={"strategy": "best_f1_strategy", "f1": "best_f1"})
    second = second.rename(columns={"strategy": "runner_up_strategy", "f1": "runner_up_f1"})

    best_recall = (
        df.sort_values(
            ["subject", "segment", "recall", "f1", "precision"],
            ascending=[True, True, False, False, False],
        )
        .groupby(["subject", "segment"], as_index=False)
        .head(1)
        .rename(columns={"strategy": "best_recall_any_fp_strategy", "recall": "best_recall_any_fp"})
    )

    merged = (
        first[
            [
                "subject",
                "segment",
                "best_f1_strategy",
                "best_f1",
                "short_share",
                "typical_share",
                "slow_share",
                "closure_share",
            ]
        ]
        .merge(second[["subject", "segment", "runner_up_strategy", "runner_up_f1"]], on=["subject", "segment"])
        .merge(
            best_recall[
                ["subject", "segment", "best_recall_any_fp_strategy", "best_recall_any_fp"]
            ],
            on=["subject", "segment"],
        )
    )

    merged["delta_f1"] = merged["best_f1"] - merged["runner_up_f1"]
    merged["duration_mix"] = merged.apply(format_duration_mix, axis=1)
    merged["difficulty"] = merged["best_f1"].map(difficulty_flag)
    for column in ("best_f1", "runner_up_f1", "delta_f1", "best_recall_any_fp"):
        merged[column] = merged[column].map(lambda x: f"{x:.3f}")
    return merged[
        [
            "subject",
            "segment",
            "best_f1_strategy",
            "best_f1",
            "runner_up_strategy",
            "runner_up_f1",
            "delta_f1",
            "best_recall_any_fp_strategy",
            "best_recall_any_fp",
            "duration_mix",
            "difficulty",
        ]
    ].sort_values(["subject", "segment"])


def build_duration_impact_table(
    df: pd.DataFrame, summary_df: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, float]]:
    segment_stats = (
        df[
            [
                "subject",
                "segment",
                "short_share",
                "long_share",
                "closure_share",
            ]
        ]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    long_q75 = float(segment_stats["long_share"].quantile(0.75))
    long_q25 = float(segment_stats["long_share"].quantile(0.25))
    closure_q75 = float(segment_stats["closure_share"].quantile(0.75))
    short_q75 = float(segment_stats["short_share"].quantile(0.75))

    competitive = summary_df.sort_values(["mean_pair_f1", "micro_f1"], ascending=False).head(12)
    raw: list[dict[str, float]] = []
    for strategy in competitive["strategy"]:
        sub = df[df["strategy"] == strategy]
        high_long = float(sub[sub["long_share"] >= long_q75]["recall"].mean())
        low_long = float(sub[sub["long_share"] <= long_q25]["recall"].mean())
        high_closure = float(sub[sub["closure_share"] >= closure_q75]["recall"].mean())
        other_closure = float(sub[sub["closure_share"] < closure_q75]["recall"].mean())
        high_short = float(sub[sub["short_share"] >= short_q75]["recall"].mean())
        low_short = float(sub[sub["short_share"] < short_q75]["recall"].mean())
        raw.append(
            {
                "strategy": strategy,
                "mean_pair_f1": float(sub["f1"].mean()),
                "delta_long": high_long - low_long,
                "delta_closure": high_closure - other_closure,
                "delta_short": high_short - low_short,
            }
        )

    n = len(raw)
    mean_deltas: dict[str, float] = {
        "long": sum(r["delta_long"] for r in raw) / n,
        "closure": sum(r["delta_closure"] for r in raw) / n,
        "short": sum(r["delta_short"] for r in raw) / n,
    }

    rows = [
        {
            "strategy": r["strategy"],
            "mean_pair_f1": f"{r['mean_pair_f1']:.3f}",
            "recall_delta_high_long_vs_low_long": f"{r['delta_long']:+.3f}",
            "recall_delta_high_closure_vs_other": f"{r['delta_closure']:+.3f}",
            "recall_delta_high_short_vs_other": f"{r['delta_short']:+.3f}",
        }
        for r in raw
    ]
    return pd.DataFrame(rows), mean_deltas


def build_hardest_segments_table(df: pd.DataFrame) -> pd.DataFrame:
    best_f1 = (
        df.sort_values(
            ["subject", "segment", "f1", "recall", "precision"],
            ascending=[True, True, False, False, False],
        )
        .groupby(["subject", "segment"], as_index=False)
        .head(1)
        .reset_index(drop=True)
    )
    hardest = best_f1.sort_values("f1").head(12).copy()
    hardest["duration_mix"] = hardest.apply(format_duration_mix, axis=1)
    hardest["best_f1"] = hardest["f1"].map(lambda x: f"{x:.3f}")
    hardest["best_recall"] = hardest["recall"].map(lambda x: f"{x:.3f}")
    hardest["flag"] = hardest["f1"].map(difficulty_flag)
    return hardest[
        ["subject", "segment", "strategy", "best_f1", "best_recall", "duration_mix", "flag"]
    ].rename(columns={"strategy": "best_strategy"})


def build_report() -> str:
    df = build_pair_strategy_dataframe()
    summary_df = compute_micro_summary(df)
    segment_winners, summary_df = annotate_wins(df, summary_df)
    summary_df = summary_df.sort_values(["micro_f1", "mean_pair_f1"], ascending=False).reset_index(drop=True)

    overall_table = summary_df.head(15).copy()
    for column in ("micro_f1", "micro_recall", "micro_precision", "mean_pair_f1", "mean_pair_recall"):
        overall_table[column] = overall_table[column].map(lambda x: f"{x:.3f}")
    overall_table = overall_table[
        [
            "strategy",
            "micro_f1",
            "micro_recall",
            "micro_precision",
            "mean_pair_f1",
            "mean_pair_recall",
            "segment_wins",
            "subject_mean_f1_leads",
        ]
    ]

    subject_table = build_subject_table(df, segment_winners)
    segment_table = build_segment_table(df)
    duration_impact_table, duration_deltas = build_duration_impact_table(df, summary_df)
    hardest_segments_table = build_hardest_segments_table(df)

    n_pairs = int(df[["subject", "segment"]].drop_duplicates().shape[0])
    n_strategies = int(df["strategy"].nunique())
    segment_winner_counts = Counter(segment_winners["strategy"])
    top_segment_winner, top_segment_winner_count = segment_winner_counts.most_common(1)[0]
    micro_leader = summary_df.iloc[0]["strategy"]

    bad_subjects = subject_table[subject_table["subject_action"] != "keep"][
        ["subject", "subject_action", "mean_best_f1", "min_best_f1"]
    ]

    segment_notes = [
        "This report uses the stored best-lane metrics from every `*_lane_summary.csv` file under `experiment_output`.",
        "The aggregate ranking in `tutorial/report_first_iteration.md` is based on pooled micro-F1. Subject and segment preference here is based on per-pair best F1, so it will favor strategies that win many individual pairs even if they are not the pooled micro-F1 leader.",
        "Duration-only morphology proxy used in this report: short < 120 ms, typical 120-300 ms, slow 300-500 ms, closure-like > 500 ms.",
        "Because the annotations do not carry an explicit blink-vs-eye-closure morphology label, anything above 500 ms is treated as closure-like by duration proxy, not by direct plateau-shape labeling.",
    ]

    lines: list[str] = []
    lines.append("# Strategy Preference By Subject And Segment")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append(
        f"- Analysed `{n_pairs}` subject-segment pairs across `{n_strategies}` strategies from the artefacts already written under `experiment_output`."
    )
    for note in segment_notes:
        lines.append(f"- {note}")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(
        f"- Pooled micro-F1 leader: `{micro_leader}`. Most frequent per-segment F1 winner: `{top_segment_winner}` (`{top_segment_winner_count}` of `{n_pairs}` segments)."
    )
    lines.append(
        "- The main pattern is a split between pooled winners and pair-wise winners: `strategy_c` wins many individual segments, but the expand-bridge family wins the pooled leaderboard because it performs better on higher-volume recall-heavy segments."
    )
    lines.append(
        "- Long-duration events are the clearest shared recall problem. Across the competitive strategies, recall drops much more on long-heavy and closure-heavy segments than on short-heavy segments."
    )
    lines.append(
        "- Short or weak blinks still matter, but they look like a secondary failure mode concentrated in a smaller set of outlier segments such as `S26/S39_20190130_052313_2` and `S22/S35_20190123_040805_3`."
    )
    lines.append(
        "- Strong drop candidates for downstream analyses: `S11`, `S20`, `S26`, and `S27`. Caution subjects: `S3`, `S17`, and `S22`."
    )
    lines.append("")
    lines.append("## Overall Strategy Ranking")
    lines.append("")
    lines.append(render_markdown_table(overall_table))
    lines.append("")
    lines.append("## Subject-Level Preference")
    lines.append("")
    lines.append(
        "- `dominant_segment_winner` = strategy that wins the most segments inside the subject."
    )
    lines.append(
        "- `best_mean_f1_strategy` = strategy with the highest average pair F1 across that subject."
    )
    lines.append(
        "- `best_mean_recall_any_fp_strategy` = strategy with the highest average pair recall across that subject, without any false-positive constraint."
    )
    lines.append(
        "- In practice, treat the recall-only column as a diagnostic signal. It often surfaces high-FP variants such as `strategy_e_abs_polarity`."
    )
    lines.append("")
    lines.append(render_markdown_table(subject_table))
    lines.append("")
    lines.append("## Segment-Level Preference")
    lines.append("")
    lines.append("- `duration_mix` uses S/T/L/C = short / typical / slow / closure-like share of ground_truth annotations.")
    lines.append(
        "- `best_recall_any_fp_strategy` is recall-only and may be impractical when its precision is poor."
    )
    lines.append("")
    lines.append(render_markdown_table(segment_table))
    lines.append("")
    lines.append("## Low-Recall Morphology Investigation")
    lines.append("")
    lines.append(
        "- Broad result: low recall is driven more by long and closure-like events than by short events when looking across all competitive strategies."
    )
    lines.append(
        f"- Averaged across the top-12 competitive strategies shown below, the mean recall penalty is `{duration_deltas['long']:+.3f}` on long-heavy segments and `{duration_deltas['closure']:+.3f}` on closure-heavy segments, versus `{duration_deltas['short']:+.3f}` on short-heavy segments."
    )
    lines.append(
        "- That means the dominant global issue is not simply tiny blinks. The stronger universal failure mode is slower or sustained ocular events."
    )
    lines.append(
        "- Still, the hardest individual outliers are mixed: some are closure-heavy (`S27` family), some are short-heavy (`S26/S39_20190130_052313_2`, `S22/S35_20190123_040805_3`), and some are typical-duration but likely low-SNR/noisy (`S17/S30_20190114_040013_3`)."
    )
    lines.append("")
    lines.append(render_markdown_table(duration_impact_table))
    lines.append("")
    lines.append("## Hardest Segments")
    lines.append("")
    lines.append(render_markdown_table(hardest_segments_table))
    lines.append("")
    lines.append("## Recommended Use")
    lines.append("")
    lines.append(
        "- If you want the best pooled detector with strong recall: prefer `expand_bridge_adaptive_k`, `expand_bridge_soft_gate`, or `strategy_e_expand_bridge`."
    )
    lines.append(
        "- If you want the best per-segment precision-weighted winner on cleaner pairs: `strategy_c` remains the main specialist."
    )
    lines.append(
        "- If a subject is dominated by high-quality, repeatable segments (`S12`, `S19`, `S23`, `S24`), subject-tuned E-family variants such as `strategy_e13_self_train`, `strategy_e12_amp_filter`, and `expand_bridge_soft_gate` become strong choices."
    )
    lines.append(
        "- If the subject contains many long or closure-like events, expect recall pain for almost every strategy. The expand-bridge family degrades less gracefully than ideal, but it still stays closer to the top than most non-bridge alternatives."
    )
    lines.append("")
    lines.append("## Drop Candidates")
    lines.append("")
    if bad_subjects.empty:
        lines.append("- No subject crossed the current drop threshold.")
    else:
        bad_subjects = bad_subjects.copy()
        lines.append(render_markdown_table(bad_subjects))
    lines.append("")
    lines.append("## Bottom Line")
    lines.append("")
    lines.append(
        "- For subject or segment-specific deployment, use this report as a pair-level routing guide, not as a replacement for the pooled leaderboard in `tutorial/report_first_iteration.md`."
    )
    lines.append(
        "- The answer to the morphology question is: mostly slow/long and closure-like events, not just short blinks. Short blinks explain a few severe outliers, but the larger cross-strategy recall loss tracks longer-duration ocular events."
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    report = build_report()
    OUTPUT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
