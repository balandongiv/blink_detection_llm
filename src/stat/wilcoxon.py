"""Pairwise Wilcoxon signed-rank tests on matched session-level scores.

Used by the exp2 strategy-comparison scripts to compare detector conditions:
proposed vs baselines is tested one-tailed (alternative="greater"), all other
pairs two-tailed, with a Bonferroni correction across all pairs.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from scipy.stats import rankdata, wilcoxon

__all__ = ["matched_rank_biserial", "run_wilcoxon_tests"]


def matched_rank_biserial(a: np.ndarray, b: np.ndarray) -> float:
    """Matched-pairs rank-biserial correlation r for the Wilcoxon signed-rank test.

    r ranges from -1 to +1; positive means a tends to exceed b.
    """
    diffs = a - b
    nonzero = diffs[diffs != 0]
    if len(nonzero) == 0:
        return 0.0
    ranks = rankdata(np.abs(nonzero))
    T_plus = float(np.sum(ranks[nonzero > 0]))
    n = len(nonzero)
    return (2.0 * T_plus / (n * (n + 1) / 2.0)) - 1.0


def run_wilcoxon_tests(
    results: list[dict],
    dataset_name: str,
    conditions: list[str],
    *,
    proposed: frozenset[str],
    baselines: frozenset[str],
) -> None:
    """Run all pairwise Wilcoxon tests on session-level F1 for *dataset_name*.

    ``proposed``/``baselines`` mark which conditions are hypothesised to
    outperform which — those pairs are tested one-tailed; every other pair
    is tested two-tailed.
    """
    rows = [r for r in results if r["dataset"] == dataset_name]
    if not rows:
        return

    lookup: dict[str, dict[str, float]] = defaultdict(dict)
    for r in rows:
        lookup[r["session"]][r["condition"]] = r["f1"]

    complete = sorted(
        s for s, cmap in lookup.items()
        if all(c in cmap for c in conditions)
    )
    n_pairs = len(conditions) * (len(conditions) - 1) // 2
    alpha_corrected = 0.05 / n_pairs

    print(f"\nWilcoxon signed-rank tests - {dataset_name.upper()}")
    print(f"  n_sessions={len(complete)}  "
          f"n_comparisons={n_pairs}  "
          f"alpha_Bonferroni={alpha_corrected:.4f}")
    print(f"  {'Comparison':<38}  {'tail':<9}  {'W':>8}  {'p':>8}  {'r':>6}  sig")
    print(f"  {'-' * 80}")

    for i, ca in enumerate(conditions):
        for j, cb in enumerate(conditions):
            if j <= i:
                continue
            va = np.array([lookup[s][ca] for s in complete])
            vb = np.array([lookup[s][cb] for s in complete])

            # Determine direction: proposed > baseline → one-tailed
            if ca in proposed and cb in baselines:
                alt, label = "greater", f"{ca} > {cb}"
            elif cb in proposed and ca in baselines:
                # swap so proposed is always "a"
                va, vb = vb, va
                alt, label = "greater", f"{cb} > {ca}"
            else:
                alt, label = "two-sided", f"{ca} vs {cb}"

            diffs = va - vb
            if np.all(diffs == 0):
                print(f"  {label:<38}  {'-':<9}  all diffs zero")
                continue
            try:
                stat, p = wilcoxon(va, vb, alternative=alt)
                r = matched_rank_biserial(va, vb)
                sig = "***" if p < alpha_corrected else "**" if p < 0.01 else "*" if p < 0.05 else ""
                print(
                    f"  {label:<38}  {alt:<9}  {stat:>8.1f}  {p:>8.4f}  {r:>6.3f}  {sig}"
                )
            except Exception as exc:
                print(f"  {label:<38}  error: {exc}")

    print()
