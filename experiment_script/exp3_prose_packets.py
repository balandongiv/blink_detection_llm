"""Rebuild the Experiment 3 evidence packets after the epoch-duration fix.

``tab13_fig10_epoch_duration.py`` previously aggregated over channel subsets as well as
channels, so its 30-second row disagreed with the identical condition reported in
Experiments 1 and 2. Restricting it to the ``all_channel`` gate changed every value in
the table and, with them, the conclusions the Experiment 3 prose drew. These packets
carry the corrected values so those paragraphs can be redrafted rather than patched.

    python experiment_script/exp3_prose_packets.py

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402
from tab13_fig10_epoch_duration import REFERENCE_S, f1_by_duration  # noqa: E402

OUT = P.ER / "exp3" / "_packets"
N_CORR = len(P.DURATIONS) - 1


def blocks() -> dict:
    per_ds = {ds: f1_by_duration(ds, "median") for ds in ("raja", "cao")}
    out = {}
    for label, ds_list in [("Raja", ["raja"]), ("Cao2018", ["cao"]),
                           ("Pooled", ["raja", "cao"])]:
        series = {d: {k: v for ds in ds_list for k, v in per_ds[ds][d].items()}
                  for d in P.DURATIONS}
        means = {d: float(np.mean(list(series[d].values()))) for d in P.DURATIONS}
        pvals = {}
        for d in P.DURATIONS:
            if d == REFERENCE_S:
                continue
            keys = sorted(set(series[REFERENCE_S]) & set(series[d]))
            a = np.array([series[d][k] for k in keys])
            b = np.array([series[REFERENCE_S][k] for k in keys])
            pvals[d] = min(1.0, stats.wilcoxon(a, b).pvalue * N_CORR)
        out[label] = {"means": means, "pvals": pvals, "n": len(series[REFERENCE_S])}
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    b = blocks()
    lines = [
        "EPOCH-DURATION SWEEP (Proposed-Med, median centre, full-montage all_channel gate)",
        "Best-channel-per-session macro F1 at each epoch duration, with two-tailed Wilcoxon",
        f"p-values against the {REFERENCE_S}-second reference, Bonferroni-corrected over",
        f"{N_CORR} non-reference durations.", "",
    ]
    for label, data in b.items():
        means, pvals = data["means"], data["pvals"]
        lines.append(f"{label} ({data['n']} sessions):")
        for d in P.DURATIONS:
            if d == REFERENCE_S:
                tag = "  [reference]"
            else:
                # Never emit "p = 0.000": it reads as exactly zero and the model
                # reproduces packet values literally.
                tag = ("  p < 0.001" if pvals[d] < 0.001
                       else f"  p = {pvals[d]:.3f}")
            lines.append(f"  {d} s: F1 = {means[d]:.4f}{tag}")
        lo, hi = min(means.values()), max(means.values())
        best = max(P.DURATIONS, key=lambda d: means[d])
        sig = [d for d in pvals if pvals[d] <= 0.05]
        lines += [
            f"  spread across the seven durations = {hi - lo:.4f} "
            f"(lowest {lo:.4f}, highest {hi:.4f})",
            f"  best duration = {best} s",
            f"  durations differing significantly from {REFERENCE_S} s after correction: "
            + (", ".join(f"{d} s" for d in sorted(sig)) if sig else "none"),
            "",
        ]
    lines += [
        "NOTE FOR THE WRITER:",
        f"  The {REFERENCE_S}-second row equals the Experiment 1 full-montage condition and",
        "  the Experiment 2 Proposed-Med condition exactly (0.8825 Raja, 0.8068 Cao2018).",
        "  Pooled performance does not differ significantly from the reference at any",
        "  duration. Raja does: state which durations, and do not describe 10-60 s as a",
        "  uniformly safe range if the numbers above do not support it.",
    ]
    (OUT / "pk_epoch_duration.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT / 'pk_epoch_duration.txt'}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
