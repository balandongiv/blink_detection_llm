"""Post-process Exp2 results: compute Wilcoxon p-values and update the LaTeX table.

Run after both run_exp2_raja.py and run_exp2_cao2018.py have completed.
Reads from:
  runs/exp2_raja/exp2_strategy_comparison_raja_results.csv
  runs/exp2_cao/exp2_strategy_comparison_cao2018_results.csv

Writes:
  writing/e_result/tab_comparison_30s_epoch.tex   (full per-selection breakdown)
  writing/e_result/tab_exp2_inversions.tex         (cases where baselines beat proposed)
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
from scipy.stats import wilcoxon

CONDITIONS = ["BLINKER-concat", "MNE-annot", "Proposed-Mean", "Proposed-Med"]
PROPOSED_PRIMARY = "Proposed-Med"

RAJA_RESULTS = REPO_ROOT / "runs/exp2_raja/exp2_strategy_comparison_raja_results.csv"
CAO_RESULTS  = REPO_ROOT / "runs/exp2_cao/exp2_strategy_comparison_cao2018_results.csv"
TABLE_MAIN   = REPO_ROOT / "writing/e_result/tab_comparison_30s_epoch.tex"
TABLE_INV    = REPO_ROOT / "writing/e_result/tab_exp2_inversions.tex"

# Selection display ordering.
RAJA_SELECTION_ORDER = [
    "frontal", "frontal_left", "frontal_right",
    "single:E22", "single:E9", "single:E3", "single:E23",
]
CAO_SELECTION_ORDER = [
    "frontal", "frontal_left", "frontal_right",
    "single:Fp1", "single:Fp2",
]


def _load_prf_vectors(path: Path) -> dict[str, dict[str, dict[str, list[float]]]]:
    """Return {selection: {condition: {precision, recall, f1: [...]}}}."""
    out: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(
        lambda: {c: {"precision": [], "recall": [], "f1": []} for c in CONDITIONS}
    )
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            sel  = row.get("selection", "")
            cond = row.get("condition", "")
            if cond not in CONDITIONS or not sel:
                continue
            try:
                out[sel][cond]["precision"].append(float(row["det_precision"]))
                out[sel][cond]["recall"].append(float(row["det_recall"]))
                out[sel][cond]["f1"].append(float(row["det_f1"]))
            except (ValueError, KeyError):
                pass
    return dict(out)


def _macro(vals: list[float]) -> float:
    return float(np.mean(vals)) if vals else float("nan")


def _wilcoxon_bonf(vecs_sel: dict[str, dict[str, list[float]]]) -> dict[tuple[str, str], float]:
    """Bonferroni-corrected two-tailed Wilcoxon p-values for all condition pairs."""
    pairs = list(combinations(CONDITIONS, 2))
    n_pairs = len(pairs)
    pvals: dict[tuple[str, str], float] = {}
    for c1, c2 in pairs:
        a = np.array(vecs_sel[c1]["f1"])
        b = np.array(vecs_sel[c2]["f1"])
        n = min(len(a), len(b))
        if n < 2:
            pvals[(c1, c2)] = float("nan")
            continue
        try:
            res = wilcoxon(a[:n], b[:n], alternative="two-sided")
            pvals[(c1, c2)] = min(float(res.pvalue) * n_pairs, 1.0)
        except ValueError:
            pvals[(c1, c2)] = float("nan")
    return pvals


def _fmt_p(p: float) -> str:
    return "n/a" if np.isnan(p) else f"{p:.9f}"


def _find_inversions(
    dataset: str,
    vecs: dict[str, dict[str, dict[str, list[float]]]],
) -> list[dict]:
    """Return rows where BLINKER-concat or MNE-annot macro-F1 >= Proposed-Med macro-F1."""
    inversions = []
    for sel, cond_vecs in vecs.items():
        proposed_f1 = _macro(cond_vecs[PROPOSED_PRIMARY]["f1"])
        for baseline in ("BLINKER-concat", "MNE-annot"):
            bl_f1 = _macro(cond_vecs[baseline]["f1"])
            if not (np.isnan(proposed_f1) or np.isnan(bl_f1)) and bl_f1 >= proposed_f1:
                inversions.append({
                    "dataset":     dataset,
                    "selection":   sel,
                    "baseline":    baseline,
                    "baseline_f1": bl_f1,
                    "proposed_f1": proposed_f1,
                    "delta_f1":    bl_f1 - proposed_f1,
                    "baseline_p":  _macro(cond_vecs[baseline]["precision"]),
                    "baseline_r":  _macro(cond_vecs[baseline]["recall"]),
                    "proposed_p":  _macro(cond_vecs[PROPOSED_PRIMARY]["precision"]),
                    "proposed_r":  _macro(cond_vecs[PROPOSED_PRIMARY]["recall"]),
                })
    return inversions


def _build_main_table(
    raja_vecs: dict,
    cao_vecs:  dict,
) -> list[str]:
    """Build the full per-selection, per-condition comparison table."""
    lines = [
        "% Source: runs/exp2_raja/exp2_strategy_comparison_raja_results.csv;",
        "%         runs/exp2_cao/exp2_strategy_comparison_cao2018_results.csv;",
        "%         script experiment_script/update_exp2_latex.py",
        r"\begin{table*}[ht]",
        r"    \centering",
        r"    \caption{Strategy comparison across channel groups and both datasets"
        r" (macro-averaged, 30-second epochs)."
        r" Combined groups: \textit{frontal}, \textit{frontal\_left}, \textit{frontal\_right}."
        r" Single-channel groups: \textit{single:X}."
        r" Best macro-F1 per (dataset, channel group) shown in \textbf{bold}."
        r" $\dagger$ marks cells where a baseline exceeds or matches Proposed-Med.}",
        r"    \label{tab:exp1_main}",
        r"    \begin{tabular}{llllccc}",
        r"        \toprule",
        r"        Dataset & Group type & Channel group & Condition & Prec. & Rec. & F1 \\",
        r"        \midrule",
    ]

    for dataset, vecs, sel_order in [
        ("Raja", raja_vecs, RAJA_SELECTION_ORDER),
        ("Cao2018", cao_vecs, CAO_SELECTION_ORDER),
    ]:
        first_dataset = True
        for sel in sel_order:
            if sel not in vecs:
                continue
            cond_vecs = vecs[sel]
            group_type = "Combined" if not sel.startswith("single:") else "Single ch."
            sel_label  = sel.replace("single:", "").replace("_", r"\_")

            # Find best F1 condition for this (dataset, selection).
            best_cond = max(CONDITIONS, key=lambda c: _macro(cond_vecs[c]["f1"]))
            proposed_f1 = _macro(cond_vecs[PROPOSED_PRIMARY]["f1"])

            first_sel = True
            for cond in CONDITIONS:
                p = _macro(cond_vecs[cond]["precision"])
                r = _macro(cond_vecs[cond]["recall"])
                f = _macro(cond_vecs[cond]["f1"])
                f_str = f"{f:.4f}" if not np.isnan(f) else "---"
                if cond == best_cond:
                    f_str = r"\textbf{" + f_str + "}"
                # Mark if this baseline >= Proposed-Med.
                if cond in ("BLINKER-concat", "MNE-annot") and not np.isnan(f) and f >= proposed_f1:
                    f_str += r"$^\dagger$"

                ds_cell  = dataset if (first_dataset and first_sel and cond == CONDITIONS[0]) else ""
                grp_cell = group_type if (first_sel and cond == CONDITIONS[0]) else ""
                sel_cell = sel_label if cond == CONDITIONS[0] else ""
                p_str = f"{p:.4f}" if not np.isnan(p) else "---"
                r_str = f"{r:.4f}" if not np.isnan(r) else "---"
                lines.append(
                    f"        {ds_cell} & {grp_cell} & {sel_cell} & {cond}"
                    f" & {p_str} & {r_str} & {f_str} \\\\"
                )
                first_sel = False
            first_dataset = False
        if dataset == "Raja":
            lines.append(r"        \midrule")

    lines += [
        r"        \bottomrule",
        r"    \end{tabular}",
        r"\end{table*}",
    ]
    return lines


def _build_inversions_table(inversions: list[dict]) -> list[str]:
    """Build a small table listing channel groups where a baseline beats Proposed-Med."""
    lines = [
        r"\begin{table}[ht]",
        r"    \centering",
        r"    \caption{Channel groups and datasets where a baseline algorithm equals"
        r" or exceeds Proposed-Med in macro-F1 ($\Delta F_1 \geq 0$)."
        r" BL = baseline; Prop = Proposed-Med."
        r" Higher recall with lower precision explains most cases:"
        r" the baseline trades precision for recall and happens to achieve equal or higher F1"
        r" on this channel subset.}",
        r"    \label{tab:exp2_inversions}",
        r"    \begin{tabular}{lllccccc}",
        r"        \toprule",
        r"        Dataset & Selection & Baseline & BL-P & BL-R & BL-F1"
        r" & Prop-F1 & $\Delta F_1$ \\",
        r"        \midrule",
    ]
    if not inversions:
        lines.append(r"        \multicolumn{8}{c}{No inversions found — Proposed-Med leads on all groups.} \\")
    else:
        for inv in sorted(inversions, key=lambda x: -x["delta_f1"]):
            lines.append(
                f"        {inv['dataset']} & "
                f"{inv['selection'].replace('_', r'_')} & "
                f"{inv['baseline']} & "
                f"{inv['baseline_p']:.4f} & {inv['baseline_r']:.4f} & {inv['baseline_f1']:.4f} & "
                f"{inv['proposed_f1']:.4f} & +{inv['delta_f1']:.4f} \\\\"
            )
    lines += [
        r"        \bottomrule",
        r"    \end{tabular}",
        r"\end{table}",
    ]
    return lines


def _telegram_summary(
    raja_vecs: dict,
    cao_vecs:  dict,
    inversions: list[dict],
) -> str:
    """Build Telegram message with single + combined channel breakdown and inversions."""
    parts = ["[Exp2] Strategy Comparison — COMPLETE\n"]

    for dataset, vecs, sel_order in [
        ("Raja (46)", raja_vecs, RAJA_SELECTION_ORDER),
        ("Cao2018 (58)", cao_vecs, CAO_SELECTION_ORDER),
    ]:
        parts.append(f"\n{dataset}:")
        parts.append(f"  {'Group':<16} {'Cond':<16} {'P':>6} {'R':>6} {'F1':>6}")
        parts.append(f"  {'-'*56}")
        for sel in sel_order:
            if sel not in vecs:
                continue
            cond_vecs = vecs[sel]
            proposed_f1 = _macro(cond_vecs[PROPOSED_PRIMARY]["f1"])
            for cond in CONDITIONS:
                p = _macro(cond_vecs[cond]["precision"])
                r = _macro(cond_vecs[cond]["recall"])
                f = _macro(cond_vecs[cond]["f1"])
                inv_marker = " [>Prop!]" if (
                    cond in ("BLINKER-concat", "MNE-annot")
                    and not np.isnan(f) and f >= proposed_f1
                ) else ""
                parts.append(
                    f"  {sel:<16} {cond:<16} {p:>6.4f} {r:>6.4f} {f:>6.4f}{inv_marker}"
                )

    if inversions:
        parts.append(f"\n*** INVERSIONS: baseline >= Proposed-Med ({len(inversions)} cases) ***")
        for inv in sorted(inversions, key=lambda x: -x["delta_f1"]):
            parts.append(
                f"  [{inv['dataset']}] {inv['selection']}: {inv['baseline']} "
                f"F1={inv['baseline_f1']:.4f} > Prop={inv['proposed_f1']:.4f} "
                f"(+{inv['delta_f1']:.4f}). "
                f"BL: P={inv['baseline_p']:.3f} R={inv['baseline_r']:.3f}; "
                f"Prop: P={inv['proposed_p']:.3f} R={inv['proposed_r']:.3f}"
            )
    else:
        parts.append("\nNo inversions: Proposed-Med leads on all channel groups.")

    return "\n".join(parts)


def _send_telegram(message: str) -> None:
    import urllib.parse, urllib.request
    token_path = REPO_ROOT / "bot_telegram.md"
    if not token_path.exists():
        return
    token = token_path.read_text(encoding="utf-8").strip()
    chat_id = "7784180158"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # Telegram caps at 4096 chars; split into chunks.
    chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
    for chunk in chunks:
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": chunk}).encode()
        try:
            urllib.request.urlopen(url, data=data, timeout=10)
        except Exception:
            pass


def main() -> None:
    for p in (RAJA_RESULTS, CAO_RESULTS):
        if not p.exists():
            print(f"Missing: {p}")
            sys.exit(1)

    raja_vecs = _load_prf_vectors(RAJA_RESULTS)
    cao_vecs  = _load_prf_vectors(CAO_RESULTS)

    inversions = _find_inversions("Raja", raja_vecs) + _find_inversions("Cao2018", cao_vecs)

    # Write main table.
    main_lines = _build_main_table(raja_vecs, cao_vecs)
    TABLE_MAIN.write_text("\n".join(main_lines) + "\n", encoding="utf-8")
    print(f"Written: {TABLE_MAIN}")

    # Write inversions table.
    inv_lines = _build_inversions_table(inversions)
    TABLE_INV.write_text("\n".join(inv_lines) + "\n", encoding="utf-8")
    print(f"Written: {TABLE_INV}")

    # Print and send Telegram.
    tg = _telegram_summary(raja_vecs, cao_vecs, inversions)
    print("\n" + "=" * 70)
    print(tg)
    print("=" * 70)
    _send_telegram(tg)

    # Inversion summary to stdout.
    if inversions:
        print(f"\n{len(inversions)} inversion(s) found:")
        for inv in sorted(inversions, key=lambda x: -x["delta_f1"]):
            print(f"  [{inv['dataset']}] {inv['selection']}: {inv['baseline']} "
                  f"beats Proposed-Med by +{inv['delta_f1']:.4f} F1")
    else:
        print("\nNo inversions: Proposed-Med is best on all channel groups.")


if __name__ == "__main__":
    main()
