"""
Agentic variant: every word of narrative is written by claude-opus-4-6
after reading the computed tables.  No hardcoded strings, no lines.append().

Output: tutorial/strategy_subject_segment_preference_analysis_agentic.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import anthropic
import pandas as pd

# Re-use all data-building and rendering functions from the existing script.
# Module-level constants in that script (REPO_ROOT, EXPERIMENT_ROOT, OUTPUT_PATH)
# are set relative to its own __file__, so they resolve correctly regardless of
# where this script is called from.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_strategy_subject_segment_analysis import (  # noqa: E402
    annotate_wins,
    build_hardest_segments_table,
    build_pair_strategy_dataframe,
    build_segment_table,
    build_subject_table,
    build_duration_impact_table,
    compute_micro_summary,
    render_markdown_table,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = (
    REPO_ROOT
    / "tutorial"
    / "strategy_subject_segment_preference_analysis_agentic.md"
)

SYSTEM_PROMPT = (
    "You are a precise data analyst writing reproducible EEG research reports. "
    "Every factual claim you write must be directly traceable to a number or cell "
    "in the tables supplied by the user. "
    "Never invent statistics, subject IDs, segment identifiers, or strategy names "
    "that are not present in the data."
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _summary_stats_text(
    df: pd.DataFrame,
    summary_df: pd.DataFrame,
    segment_winners: pd.DataFrame,
    duration_deltas: dict[str, float],
) -> str:
    """Return a bullet-list of key scalar statistics derived from the data."""
    from collections import Counter

    n_pairs = int(df[["subject", "segment"]].drop_duplicates().shape[0])
    n_strategies = int(df["strategy"].nunique())
    winner_counts = Counter(segment_winners["strategy"])
    top_winner, top_count = winner_counts.most_common(1)[0]
    micro_leader = str(summary_df.iloc[0]["strategy"])
    micro_leader_f1 = float(summary_df.iloc[0]["micro_f1"])

    return "\n".join(
        [
            f"- subject-segment pairs analysed: {n_pairs}",
            f"- strategies evaluated: {n_strategies}",
            f"- pooled micro-F1 leader: `{micro_leader}` "
            f"(micro_f1 = {micro_leader_f1:.3f})",
            f"- most frequent per-segment F1 winner: `{top_winner}` "
            f"({top_count} of {n_pairs} segments)",
            f"- mean recall delta on long-heavy segments "
            f"(high vs low long_share): {duration_deltas['long']:+.3f}",
            f"- mean recall delta on closure-heavy segments "
            f"(high vs other closure_share): {duration_deltas['closure']:+.3f}",
            f"- mean recall delta on short-heavy segments "
            f"(high vs other short_share): {duration_deltas['short']:+.3f}",
        ]
    )


def _build_overall_table(summary_df: pd.DataFrame) -> pd.DataFrame:
    table = summary_df.head(15).copy()
    for col in (
        "micro_f1",
        "micro_recall",
        "micro_precision",
        "mean_pair_f1",
        "mean_pair_recall",
    ):
        table[col] = table[col].map(lambda x: f"{x:.3f}")
    return table[
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


def _build_user_prompt(
    overall_table: pd.DataFrame,
    subject_table: pd.DataFrame,
    segment_table: pd.DataFrame,
    duration_impact_table: pd.DataFrame,
    hardest_segments_table: pd.DataFrame,
    summary_stats: str,
) -> str:
    return f"""\
Write a complete markdown research report titled
"# Strategy Preference By Subject And Segment".

All data come from experiment artefacts (`*_lane_summary.csv` files under
`experiment_output/`).  Use only the tables and statistics below — do not
add claims beyond what the data support.

---

## Scalar Statistics (computed from the CSVs)

{summary_stats}

---

## Table 1 — Overall Strategy Ranking (top 15 by pooled micro-F1)

Column definitions:
- `micro_f1`, `micro_recall`, `micro_precision`: pooled TP/FP/FN across all pairs
- `mean_pair_f1`, `mean_pair_recall`: average of per-pair best-lane scores
- `segment_wins`: segments where this strategy had the highest per-pair F1
- `subject_mean_f1_leads`: subjects where this strategy had the highest mean F1

{render_markdown_table(overall_table)}

---

## Table 2 — Subject-Level Preference

Column definitions:
- `dominant_segment_winner`: strategy winning the most segments inside the subject
- `best_mean_f1_strategy`: strategy with the highest average pair F1 for that subject
- `best_mean_recall_any_fp_strategy`: highest average pair recall, no FP constraint
- `mean_best_f1` / `min_best_f1`: mean and minimum of best-strategy F1 across segments
- `mean_long_share`: mean share of reference annotations with duration > 400 ms
- `mean_closure_share`: mean share with duration > 500 ms
- `subject_action`: classification threshold —
  drop-candidate if `mean_best_f1 ≤ 0.40` or `min_best_f1 < 0.05`;
  caution if `mean_best_f1 < 0.60` or `min_best_f1 < 0.20`;
  keep otherwise

{render_markdown_table(subject_table)}

---

## Table 3 — Segment-Level Preference

Column definitions:
- `best_f1_strategy` / `best_f1`: per-segment winner and its F1
- `runner_up_strategy` / `runner_up_f1`: second-best strategy and F1
- `delta_f1`: gap between winner and runner-up
- `best_recall_any_fp_strategy` / `best_recall_any_fp`: best-recall strategy, no FP constraint
- `duration_mix`: S / T / L / C shares (short < 120 ms / typical 120-300 ms /
  slow 300-500 ms / closure-like > 500 ms)
- `difficulty`: keep / caution / drop-candidate based on `best_f1` thresholds
  (< 0.20 → drop-candidate, < 0.55 → caution, ≥ 0.55 → keep)

{render_markdown_table(segment_table)}

---

## Table 4 — Duration Impact on Recall (top-12 competitive strategies)

Negative delta = recall drops when that duration class is prevalent.
Computed for the top-12 strategies by mean_pair_f1 shown in Table 1.

{render_markdown_table(duration_impact_table)}

---

## Table 5 — Hardest Segments (12 lowest best-F1 across all strategies)

{render_markdown_table(hardest_segments_table)}

---

## Report Structure Required

Write all eleven sections below, in order:

1. `# Strategy Preference By Subject And Segment`

2. `## Scope`
   State how many pairs and strategies were analysed, and that the data come
   from stored `*_lane_summary.csv` artefacts.

3. `## Executive Summary`
   Bullet points only.  Every bullet must cite a concrete number from the
   scalar statistics or one of the five tables.  Do not include any claim
   that cannot be verified from the data above.

4. `## Overall Strategy Ranking`
   Embed Table 1 verbatim, then write ≤ 3 sentences of analysis naming only
   strategies that appear in the table.

5. `## Subject-Level Preference`
   Define the column meanings briefly, embed Table 2 verbatim, then write
   ≤ 4 sentences identifying notable patterns (e.g. which subjects are
   drop-candidates, which strategy dominates most subjects).

6. `## Segment-Level Preference`
   One-sentence usage note, then embed Table 3 verbatim.

7. `## Low-Recall Morphology Investigation`
   Embed Table 4 verbatim.  Then write ≤ 4 sentences: state which duration
   class produces the largest mean recall drop and quote the exact delta from
   the scalar statistics; when naming outlier segments, cite only segments
   that appear in Table 5 and quote their `duration_mix` from Table 3.

8. `## Hardest Segments`
   One-sentence note, then embed Table 5 verbatim.

9. `## Recommended Use`
   3–5 bullet points derived from the data.  Name only strategies present in
   the tables.

10. `## Drop Candidates`
    Embed a markdown table showing only the rows from Table 2 where
    `subject_action` is not "keep" — columns: subject, subject_action,
    mean_best_f1, min_best_f1.

11. `## Bottom Line`
    One concise paragraph summarising the key takeaway for a practitioner
    deciding which strategy to deploy.

Rules:
- Copy each table verbatim from the data above — do not reformat or abbreviate rows.
- Use backtick formatting for all strategy names and segment identifiers.
- Output only the markdown — no preamble, no explanation outside the sections.
"""


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    # 1. Compute all tables from the stored CSV artefacts
    df = build_pair_strategy_dataframe()
    summary_df = compute_micro_summary(df)
    segment_winners, summary_df = annotate_wins(df, summary_df)
    summary_df = summary_df.sort_values(
        ["micro_f1", "mean_pair_f1"], ascending=False
    ).reset_index(drop=True)

    overall_table = _build_overall_table(summary_df)
    subject_table = build_subject_table(df, segment_winners)
    segment_table = build_segment_table(df)
    duration_impact_table, duration_deltas = build_duration_impact_table(
        df, summary_df
    )
    hardest_segments_table = build_hardest_segments_table(df)

    summary_stats = _summary_stats_text(
        df, summary_df, segment_winners, duration_deltas
    )

    # 2. Build prompt and call claude-opus-4-6 (streaming for long output)
    user_prompt = _build_user_prompt(
        overall_table,
        subject_table,
        segment_table,
        duration_impact_table,
        hardest_segments_table,
        summary_stats,
    )

    client = anthropic.Anthropic()

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=16000,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            }
        ],
    ) as stream:
        final = stream.get_final_message()

    report = next(b.text for b in final.content if b.type == "text")
    OUTPUT_PATH.write_text(report, encoding="utf-8")

    u = final.usage
    print(f"Wrote {OUTPUT_PATH}")
    print(
        f"Tokens — input: {u.input_tokens}  output: {u.output_tokens}  "
        f"cache_read: {u.cache_read_input_tokens}  "
        f"cache_creation: {u.cache_creation_input_tokens}"
    )


if __name__ == "__main__":
    main()
