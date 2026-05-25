from __future__ import annotations

import argparse
import csv
import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon


def _read_csv(path: Path) -> list[dict]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _as_float(x: str) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def _fmt_float(x: float, nd: int = 4) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "--"
    return f"{x:.{nd}f}"


def _fmt_mean_pm_sd(vals: list[float], nd: int = 4) -> str:
    vals = [v for v in vals if not (math.isnan(v) or math.isinf(v))]
    if not vals:
        return "--"
    m = float(np.mean(vals))
    sd = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
    return f"{m:.{nd}f} $\\pm$ {sd:.{nd}f}"


def _fmt_p(p: float) -> str:
    if p is None or math.isnan(p):
        return "--"
    if p < 1e-4:
        return "<0.0001"
    return f"{p:.4f}"


@dataclass(frozen=True)
class ExpPaths:
    root: Path

    @property
    def exp1_dir(self) -> Path:
        return self.root / "exp1_epoch_duration"

    @property
    def exp41_dir(self) -> Path:
        return self.root / "exp41_strategy_comparison"

    @property
    def exp42_dir(self) -> Path:
        return self.root / "exp42_boundary_tolerance"

    @property
    def exp45_dir(self) -> Path:
        return self.root / "exp45_morphological_detailed"


def _load_best_epoch(paths: ExpPaths) -> float:
    summary_json = paths.exp1_dir / "summary.json"
    if not summary_json.exists():
        raise FileNotFoundError(f"Missing {summary_json}")
    import json

    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    return float(payload["best_epoch_duration_s"])


def _exp1_epoch_table(paths: ExpPaths) -> tuple[list[float], float, dict[float, float], dict[float, float]]:
    """Return (durations, reference, macro_f1_by_dur, p_by_dur_vs_ref)."""
    rows = _read_csv(paths.exp1_dir / "exp1_epoch_duration_results.csv")
    if not rows:
        raise ValueError("No EXP1 rows found.")

    # Session-level F1 per duration (across both datasets, matching by session id).
    by_session: dict[str, dict[float, float]] = {}
    durations: set[float] = set()
    for r in rows:
        sess = r["session"]
        dur = _as_float(r["epoch_duration_s"])
        f1 = _as_float(r["f1"])
        durations.add(dur)
        by_session.setdefault(sess, {})[dur] = f1

    durations_sorted = sorted(durations)
    ref = 60.0  # Script reference; keep stable for the write-up table.
    if ref not in durations_sorted:
        ref = durations_sorted[len(durations_sorted) // 2]

    macro_f1_by_dur: dict[float, float] = {}
    for dur in durations_sorted:
        f1s = [m.get(dur, float("nan")) for m in by_session.values()]
        f1s = [x for x in f1s if not math.isnan(x)]
        macro_f1_by_dur[dur] = float(np.mean(f1s)) if f1s else float("nan")

    # Wilcoxon vs reference on matched sessions (sessions that have both dur and ref).
    p_by_dur: dict[float, float] = {}
    for dur in durations_sorted:
        if dur == ref:
            continue
        xs = []
        ys = []
        for sess, m in by_session.items():
            if dur in m and ref in m:
                xs.append(m[dur])
                ys.append(m[ref])
        if not xs:
            p_by_dur[dur] = float("nan")
            continue
        try:
            stat, p = wilcoxon(np.array(xs), np.array(ys), alternative="two-sided")
            p_by_dur[dur] = float(p)
        except Exception:
            p_by_dur[dur] = float("nan")

    return durations_sorted, ref, macro_f1_by_dur, p_by_dur


def _exp41_condition_stats(paths: ExpPaths) -> tuple[list[str], dict[str, dict[str, list[float]]]]:
    rows = _read_csv(paths.exp41_dir / "exp41_strategy_comparison_results.csv")
    if not rows:
        raise ValueError("No EXP41 rows found.")

    conditions: list[str] = []
    by_cond: dict[str, dict[str, list[float]]] = {}
    for r in rows:
        cond = r["condition"]
        if cond not in by_cond:
            by_cond[cond] = {"precision": [], "recall": [], "f1": []}
            conditions.append(cond)
        by_cond[cond]["precision"].append(_as_float(r["precision"]))
        by_cond[cond]["recall"].append(_as_float(r["recall"]))
        by_cond[cond]["f1"].append(_as_float(r["f1"]))

    # Preserve canonical order if present.
    canonical = ["BLINKER-concat", "MNE-annot", "DBO", "Proposed-Mean", "Proposed-Med"]
    ordered = [c for c in canonical if c in by_cond] + [c for c in conditions if c not in canonical]
    return ordered, by_cond


def _wilcoxon_proposed_vs_baselines(paths: ExpPaths) -> dict[str, float]:
    """One-tailed Wilcoxon on session-level F1: Proposed-Med > baseline."""
    rows = _read_csv(paths.exp41_dir / "exp41_strategy_comparison_results.csv")
    by_session: dict[str, dict[str, float]] = {}
    for r in rows:
        by_session.setdefault(r["session"], {})[r["condition"]] = _as_float(r["f1"])

    proposed = "Proposed-Med"
    baselines = ["BLINKER-concat", "MNE-annot", "DBO"]

    pvals: dict[str, float] = {}
    for b in baselines:
        xs = []
        ys = []
        for sess, m in by_session.items():
            if proposed in m and b in m:
                xs.append(m[proposed])
                ys.append(m[b])
        if not xs:
            pvals[b] = float("nan")
            continue
        try:
            stat, p = wilcoxon(np.array(xs), np.array(ys), alternative="greater")
            pvals[b] = float(p)
        except Exception:
            pvals[b] = float("nan")
    return pvals


def _replace_between(text: str, start_pat: str, end_pat: str, replacement: str) -> str:
    m1 = re.search(start_pat, text, flags=re.MULTILINE)
    m2 = re.search(end_pat, text, flags=re.MULTILINE)
    if not m1 or not m2 or m2.start() <= m1.end():
        raise ValueError("Could not find replace bounds.")
    return text[: m1.end()] + replacement + text[m2.start() :]


def _update_tab_effect_epoch_size(path: Path, durations: list[float], ref: float, macro_f1: dict[float, float], p_by_dur: dict[float, float]) -> None:
    txt = path.read_text(encoding="utf-8")

    body_lines: list[str] = []
    for dur in durations:
        dur_tex = f"{int(dur)}\\,s"
        f1 = _fmt_float(macro_f1.get(dur, float('nan')), 4)
        if dur == ref:
            p = "(reference)"
        else:
            p = _fmt_p(p_by_dur.get(dur, float("nan")))
        body_lines.append(f"        {dur_tex:<6} & {f1} & {p} \\\\")

    replacement = "\n" + "\n".join(body_lines) + "\n"
    # Replace between \midrule and \bottomrule.
    new_txt = _replace_between(txt, r"\\midrule\s*", r"\s*\\bottomrule", replacement)
    path.write_text(new_txt, encoding="utf-8")


def _update_tab_comparison(path: Path, epoch_s: float, conditions: list[str], by_cond: dict[str, dict[str, list[float]]], pvals_baseline: dict[str, float]) -> None:
    txt = path.read_text(encoding="utf-8")

    # Determine best (highest mean) for bolding.
    means = {}
    for cond in conditions:
        means[cond] = {
            "precision": float(np.mean(by_cond[cond]["precision"])),
            "recall": float(np.mean(by_cond[cond]["recall"])),
            "f1": float(np.mean(by_cond[cond]["f1"])),
        }
    best_p = max(means, key=lambda c: means[c]["precision"])
    best_r = max(means, key=lambda c: means[c]["recall"])
    best_f = max(means, key=lambda c: means[c]["f1"])

    alpha = 0.05 / 3.0  # Bonferroni for 3 baseline comparisons vs Proposed-Med

    lines: list[str] = []
    for cond in conditions:
        p = _fmt_mean_pm_sd(by_cond[cond]["precision"], 4)
        r = _fmt_mean_pm_sd(by_cond[cond]["recall"], 4)
        f1 = _fmt_mean_pm_sd(by_cond[cond]["f1"], 4)

        if cond == best_p:
            p = f"\\textbf{{{p}}}"
        if cond == best_r:
            r = f"\\textbf{{{r}}}"
        if cond == best_f:
            f1 = f"\\textbf{{{f1}}}"

        suffix = ""
        if cond in pvals_baseline and not math.isnan(pvals_baseline[cond]) and pvals_baseline[cond] < alpha:
            suffix = " $^\\dagger$"

        lines.append(f"        {cond:<14} & {p} & {r} & {f1}{suffix} \\\\")

    replacement = "\n" + "\n".join(lines) + "\n"
    new_txt = _replace_between(txt, r"\\midrule\s*", r"\s*\\bottomrule", replacement)

    # Update caption epoch mention (keep filename stable even if not 60s).
    new_txt = re.sub(
        r"Main comparison on [0-9]+-second epochs\.",
        f"Main comparison on {int(epoch_s)}-second epochs.",
        new_txt,
    )
    path.write_text(new_txt, encoding="utf-8")


def _update_results_epoch_default(path: Path, epoch_s: float) -> None:
    txt = path.read_text(encoding="utf-8")
    txt2 = txt
    txt2 = txt2.replace(
        "Unless otherwise stated, each continuous session is divided into non-overlapping\n60-second epochs, and the evaluation is conducted at the event level using the\n",
        f"Unless otherwise stated, each continuous session is divided into non-overlapping\n{int(epoch_s)}-second epochs (selected by Experiment~1), and the evaluation is conducted at the event level using the\n",
    )
    path.write_text(txt2, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Update LaTeX write-up files from an orchestration log directory.")
    ap.add_argument("--logdir", type=Path, required=True)
    ap.add_argument("--writing-dir", type=Path, default=Path("writing"))
    args = ap.parse_args()

    paths = ExpPaths(args.logdir)
    writing_dir = (args.writing_dir if args.writing_dir.is_absolute() else (Path.cwd() / args.writing_dir)).resolve()

    best_epoch = _load_best_epoch(paths)

    # Update Experiment 1 epoch duration table.
    durations, ref, macro_f1, p_by_dur = _exp1_epoch_table(paths)
    _update_tab_effect_epoch_size(writing_dir / "tab_effect_different_epoch_size.tex", durations, ref, macro_f1, p_by_dur)

    # Update main comparison table (Experiment 41 in codebase naming).
    conds, by_cond = _exp41_condition_stats(paths)
    pvals = _wilcoxon_proposed_vs_baselines(paths)
    _update_tab_comparison(writing_dir / "tab_comparison_60s_epoch.tex", best_epoch, conds, by_cond, pvals)

    # Update default epoch mention in results section.
    _update_results_epoch_default(writing_dir / "result.tex", best_epoch)


if __name__ == "__main__":
    main()

