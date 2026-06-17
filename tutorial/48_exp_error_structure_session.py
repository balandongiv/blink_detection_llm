"""Recompute disabled error/session summary tables from exp41 Cao/Raja results.

Input:
  runs/exp41_cao_30s/exp41_strategy_comparison_results.csv

Outputs:
  writing/e_result/tab_error_structure.tex
  writing/e_result/tab_best_session.tex
  runs/exp_error_session/error_regime.csv
  runs/exp_error_session/error_regime_by_dataset.csv
  runs/exp_error_session/session_ranking_proposed_med.csv
  runs/exp_error_session/subject_ranking_proposed_med.csv
  runs/reports/R5disabled_error_session.md
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = ROOT / "runs" / "exp41_cao_30s" / "exp41_strategy_comparison_results.csv"
OUT_DIR = ROOT / "runs" / "exp_error_session"
REPORT_PATH = ROOT / "runs" / "reports" / "R5disabled_error_session.md"
ERROR_TABLE = ROOT / "writing" / "e_result" / "tab_error_structure.tex"
SESSION_TABLE = ROOT / "writing" / "e_result" / "tab_best_session.tex"

CONDITIONS = ["BLINKER-concat", "MNE-annot", "Proposed-Mean", "Proposed-Med"]
DATASETS = ["raja", "cao2018"]
SOURCE_COMMENT = (
    "% Source: runs/exp41_cao_30s/exp41_strategy_comparison_results.csv; "
    "script tutorial/48_exp_error_structure_session.py"
)


def latex_escape(value: object) -> str:
    text = str(value)
    return text.replace("\\", "\\textbackslash{}").replace("_", "\\_")


def subject_from_row(row: pd.Series) -> str:
    session = str(row["session"])
    dataset = str(row["dataset"])
    if "/" not in session:
        raise ValueError(f"Session does not contain a subject prefix: {session}")
    subject = session.split("/", 1)[0]
    if dataset == "raja" and not subject.startswith("S"):
        raise ValueError(f"Raja session does not start with S<k>: {session}")
    return subject


def validate_input(df: pd.DataFrame) -> None:
    expected_columns = {
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
    missing = expected_columns - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    datasets = sorted(df["dataset"].unique())
    if datasets != sorted(DATASETS):
        raise ValueError(f"Expected datasets {DATASETS}, found {datasets}")

    conditions = sorted(df["condition"].unique())
    if conditions != sorted(CONDITIONS):
        raise ValueError(f"Expected conditions {CONDITIONS}, found {conditions}")

    counts = (
        df[["dataset", "session"]]
        .drop_duplicates()
        .groupby("dataset")
        .size()
        .to_dict()
    )
    expected_counts = {"raja": 46, "cao2018": 58}
    if counts != expected_counts:
        raise ValueError(f"Expected session counts {expected_counts}, found {counts}")

    per_session_conditions = df.groupby(["dataset", "session"])["condition"].nunique()
    bad = per_session_conditions[per_session_conditions != len(CONDITIONS)]
    if not bad.empty:
        raise ValueError("Some sessions do not have all four conditions")


def compute_error_regime(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for condition in CONDITIONS:
        subset = df[df["condition"] == condition]
        mean_fp = float(subset["fp"].mean())
        mean_fn = float(subset["fn"].mean())
        ratio = mean_fp / mean_fn if mean_fn else float("inf")
        rows.append(
            {
                "condition": condition,
                "mean_fp_per_session": mean_fp,
                "mean_fn_per_session": mean_fn,
                "fp_fn_ratio": ratio,
                "regime": "FP-heavy" if mean_fp > mean_fn else "FN-heavy",
            }
        )
    return pd.DataFrame(rows)


def compute_error_regime_by_dataset(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby(["dataset", "condition"], as_index=False)
        .agg(mean_fp_per_session=("fp", "mean"), mean_fn_per_session=("fn", "mean"))
    )
    grouped["fp_fn_ratio"] = grouped["mean_fp_per_session"] / grouped["mean_fn_per_session"]
    grouped["regime"] = grouped.apply(
        lambda row: "FP-heavy"
        if row["mean_fp_per_session"] > row["mean_fn_per_session"]
        else "FN-heavy",
        axis=1,
    )
    condition_order = {condition: i for i, condition in enumerate(CONDITIONS)}
    grouped["_condition_order"] = grouped["condition"].map(condition_order)
    grouped = grouped.sort_values(["dataset", "_condition_order"]).drop(columns=["_condition_order"])
    return grouped


def compute_rankings(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    proposed = df[df["condition"] == "Proposed-Med"].copy()
    proposed["subject"] = proposed.apply(subject_from_row, axis=1)

    session_ranking = proposed.sort_values(
        ["f1", "dataset", "session"], ascending=[False, True, True]
    ).reset_index(drop=True)
    session_ranking.insert(0, "rank_desc_f1", session_ranking.index + 1)
    session_ranking = session_ranking[
        [
            "rank_desc_f1",
            "dataset",
            "session",
            "subject",
            "best_channel",
            "tp",
            "fp",
            "fn",
            "precision",
            "recall",
            "f1",
            "wall_clock_s",
        ]
    ]

    subject_ranking = (
        proposed.groupby(["dataset", "subject"], as_index=False)
        .agg(n_sessions=("session", "nunique"), mean_f1=("f1", "mean"))
        .sort_values(["mean_f1", "dataset", "subject"], ascending=[False, True, True])
        .reset_index(drop=True)
    )
    subject_ranking.insert(0, "rank_desc_mean_f1", subject_ranking.index + 1)

    return session_ranking, subject_ranking


def render_error_table(error_regime: pd.DataFrame) -> str:
    rows = []
    for row in error_regime.itertuples(index=False):
        rows.append(
            "    "
            f"{latex_escape(row.condition)} & "
            f"{row.mean_fp_per_session:.1f} & "
            f"{row.mean_fn_per_session:.1f} & "
            f"{row.fp_fn_ratio:.3f} & "
            f"{row.regime} \\\\"
        )

    return "\n".join(
        [
            SOURCE_COMMENT,
            "\\begin{table}[ht]",
            "  \\centering",
            "  \\caption{Error-structure decomposition by condition. Mean false positives (FP) and false negatives (FN) are reported per session.}",
            "  \\label{tab:error-structure}",
            "  \\begin{tabular}{lcccl}",
            "    \\toprule",
            "    Condition & Mean FP/session & Mean FN/session & FP:FN & Regime \\\\",
            "    \\midrule",
            *rows[:2],
            "% DBO-related results are intentionally commented out because DBO is reserved for a future paper.",
            "%    DBO & -- & -- & -- & reserved \\\\",
            *rows[2:],
            "    \\bottomrule",
            "  \\end{tabular}",
            "\\end{table}",
            "",
        ]
    )


def render_session_table(session_ranking: pd.DataFrame, subject_ranking: pd.DataFrame) -> str:
    best_session = session_ranking.iloc[0]
    worst_session = session_ranking.iloc[-1]
    best_subject = subject_ranking.iloc[0]
    worst_subject = subject_ranking.iloc[-1]
    n_sessions = len(session_ranking)
    n_subjects = len(subject_ranking)
    median_session_f1 = float(session_ranking["f1"].median())
    median_subject_f1 = float(subject_ranking["mean_f1"].median())

    rows = [
        (
            "Best session",
            best_session["dataset"],
            best_session["session"],
            1,
            "F1",
            float(best_session["f1"]),
        ),
        (
            "Worst session",
            worst_session["dataset"],
            worst_session["session"],
            1,
            "F1",
            float(worst_session["f1"]),
        ),
        ("Median session", "all", f"{n_sessions} sessions", n_sessions, "F1", median_session_f1),
        (
            "Best subject",
            best_subject["dataset"],
            best_subject["subject"],
            int(best_subject["n_sessions"]),
            "Mean F1",
            float(best_subject["mean_f1"]),
        ),
        (
            "Worst subject",
            worst_subject["dataset"],
            worst_subject["subject"],
            int(worst_subject["n_sessions"]),
            "Mean F1",
            float(worst_subject["mean_f1"]),
        ),
        ("Median subject", "all", f"{n_subjects} subjects", n_subjects, "Mean F1", median_subject_f1),
    ]

    body = [
        "    "
        f"{latex_escape(scope)} & {latex_escape(dataset)} & {latex_escape(unit)} & "
        f"{n} & {latex_escape(metric)} & {value:.4f} \\\\"
        for scope, dataset, unit, n, metric, value in rows
    ]

    return "\n".join(
        [
            SOURCE_COMMENT,
            "\\begin{table}[ht]",
            "  \\centering",
            f"  \\caption{{Best and worst Proposed-Med sessions and subject-level summary rows across {n_sessions} Raja+Cao2018 sessions.}}",
            "  \\label{tab:best-session}",
            "  \\begin{tabular}{lllccl}",
            "    \\toprule",
            "    Scope & Dataset & Unit & $n$ & Metric & Value \\\\",
            "    \\midrule",
            *body,
            "    \\bottomrule",
            "  \\end{tabular}",
            "\\end{table}",
            "",
        ]
    )


def render_report(
    error_regime: pd.DataFrame,
    session_ranking: pd.DataFrame,
    subject_ranking: pd.DataFrame,
) -> str:
    best_session = session_ranking.iloc[0]
    worst_session = session_ranking.iloc[-1]
    best_subject = subject_ranking.iloc[0]
    worst_subject = subject_ranking.iloc[-1]
    n_sessions = len(session_ranking)
    n_subjects = len(subject_ranking)

    lines = [
        "# R5 Disabled Error/Session Recompute",
        "",
        "## Error-structure table",
        "",
        "| Condition | Mean FP/session | Mean FN/session | FP:FN | Regime |",
        "|---|---:|---:|---:|---|",
    ]
    for row in error_regime.itertuples(index=False):
        lines.append(
            f"| {row.condition} | {row.mean_fp_per_session:.1f} | "
            f"{row.mean_fn_per_session:.1f} | {row.fp_fn_ratio:.3f} | {row.regime} |"
        )

    lines.extend(
        [
            "",
            "## Proposed-Med session and subject summaries",
            "",
            "| Scope | Dataset | Unit | n | Metric | Value |",
            "|---|---|---|---:|---|---:|",
            f"| Best session | {best_session['dataset']} | {best_session['session']} | 1 | F1 | {float(best_session['f1']):.4f} |",
            f"| Worst session | {worst_session['dataset']} | {worst_session['session']} | 1 | F1 | {float(worst_session['f1']):.4f} |",
            f"| Median session | all | {n_sessions} sessions | {n_sessions} | F1 | {float(session_ranking['f1'].median()):.4f} |",
            f"| Best subject | {best_subject['dataset']} | {best_subject['subject']} | {int(best_subject['n_sessions'])} | Mean F1 | {float(best_subject['mean_f1']):.4f} |",
            f"| Worst subject | {worst_subject['dataset']} | {worst_subject['subject']} | {int(worst_subject['n_sessions'])} | Mean F1 | {float(worst_subject['mean_f1']):.4f} |",
            f"| Median subject | all | {n_subjects} subjects | {n_subjects} | Mean F1 | {float(subject_ranking['mean_f1'].median()):.4f} |",
            "",
            "## Files changed",
            "",
            "- writing/e_result/tab_error_structure.tex",
            "- writing/e_result/tab_best_session.tex",
            "- tutorial/48_exp_error_structure_session.py",
            "- runs/exp_error_session/error_regime.csv",
            "- runs/exp_error_session/error_regime_by_dataset.csv",
            "- runs/exp_error_session/session_ranking_proposed_med.csv",
            "- runs/exp_error_session/subject_ranking_proposed_med.csv",
            "- runs/reports/R5disabled_error_session.md",
            "",
            "## Murat removal check",
            "",
            "Confirmed: recomputed tables and audit CSVs contain only raja and cao2018; Murat is gone.",
            "",
            "DISABLED_ES_DONE error_table=writing/e_result/tab_error_structure.tex session_table=writing/e_result/tab_best_session.tex script=tutorial/48_exp_error_structure_session.py",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    df = pd.read_csv(INPUT_CSV)
    validate_input(df)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    error_regime = compute_error_regime(df)
    error_by_dataset = compute_error_regime_by_dataset(df)
    session_ranking, subject_ranking = compute_rankings(df)

    error_regime.to_csv(OUT_DIR / "error_regime.csv", index=False)
    error_by_dataset.to_csv(OUT_DIR / "error_regime_by_dataset.csv", index=False)
    session_ranking.to_csv(OUT_DIR / "session_ranking_proposed_med.csv", index=False)
    subject_ranking.to_csv(OUT_DIR / "subject_ranking_proposed_med.csv", index=False)

    ERROR_TABLE.write_text(render_error_table(error_regime), encoding="utf-8")
    SESSION_TABLE.write_text(render_session_table(session_ranking, subject_ranking), encoding="utf-8")
    REPORT_PATH.write_text(render_report(error_regime, session_ranking, subject_ranking), encoding="utf-8")


if __name__ == "__main__":
    main()
