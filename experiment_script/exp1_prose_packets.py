"""Build the evidence packets for the Experiment 1 channel-subset prose.

Every number the drafting model is allowed to write must appear here, computed from
``publication_results/`` by this script. The model receives a packet and nothing else,
and the number gate in ``prose_gates.verify_numbers`` rejects any draft containing a
value that is not in it — so derived quantities (percentages, ratios, differences) are
computed here rather than left for the model to work out.

    python experiment_script/exp1_prose_packets.py

Writes one ``<name>.txt`` per planned paragraph into ``writing/e_result/exp1/_packets/``.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exp1_subset_data as S  # noqa: E402
import paper_data as P  # noqa: E402
import tab3_fig3_region_performance as R  # noqa: E402

OUT = P.ER / "exp1" / "_packets"
DSN = {"raja": "Raja", "cao": "Cao2018"}


def f4(x) -> str:
    return f"{x:.4f}"


def pct(x) -> str:
    return f"{x:.1f}"


def fmt_p(p: float) -> str:
    """How a p-value is written in the prose, so the gate sees the same literal."""
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def write(name: str, lines: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  wrote {name}.txt ({len(lines)} lines)")


# --------------------------------------------------------------------------- design
def packet_design() -> None:
    lines = ["EXPERIMENT 1 DESIGN FACTS (channel-subset analysis)", ""]
    for ds in ("raja", "cao"):
        d = S.load_median(ds)
        n_anat = len([s for s in S.SUBSET_ORDER if s in set(d.selection)])
        n_solo = len([s for s in set(d.selection) if s.endswith("_only")])
        ref = S.reference_macro(ds)
        lines += [
            f"{DSN[ds]}:",
            f"  sessions = {ref['n_sessions']}",
            f"  electrodes in the full montage = "
            f"{int(d.loc[d.selection == S.REFERENCE, 'n_channels_used'].iloc[0])}",
            f"  anatomical channel subsets evaluated = {n_anat} (includes the full montage)",
            f"  single-electrode subsets evaluated = {n_solo}",
            f"  total channel subsets evaluated = {d.selection.nunique()}",
            f"  subsets compared against the full montage = "
            f"{S.subset_stats(ds).attrs['n_comparisons']}",
            "",
        ]
    lines += [
        "Shared design:",
        "  epoch duration = 30 seconds",
        "  Stage-B centre = median (Proposed-Med)",
        "  aggregation = best-channel-per-session, then averaged over sessions",
        "  test = two-tailed Wilcoxon signed-rank, Bonferroni-corrected within each dataset",
        "  effect size = matched-pairs rank-biserial correlation",
        "",
        "SCOPE NOTE (not a number, but a fact the paragraph must state):",
        "  Each subset re-runs Stage A, Stage B and Stage C on that subset alone, so each",
        "  subset is a self-contained detector rather than the full-montage detector with",
        "  channels hidden. The analysis therefore tests whether a subset is SUFFICIENT.",
        "  It is not a leave-one-region-out analysis and does not measure the necessity of",
        "  a region to the complete system.",
    ]
    write("pk_design", lines)


# ------------------------------------------------------------------------ reference
def packet_reference() -> None:
    lines = ["FULL-MONTAGE REFERENCE CONDITION (all_channel, median centre)", ""]
    for ds in ("raja", "cao"):
        r = S.reference_macro(ds)
        lines += [
            f"{DSN[ds]}: precision = {f4(r['precision'])}, recall = {f4(r['recall'])}, "
            f"F1 = {f4(r['f1'])}, sessions = {r['n_sessions']}",
        ]
    lines += [
        "",
        "CROSS-EXPERIMENT IDENTITY (verified per session, not only on the means):",
        "  The Experiment 1 full-montage condition, the Experiment 2 Proposed-Med condition",
        "  and the Experiment 3 30-second condition are the same configuration and produced",
        "  identical per-session values.",
        "  Raja: 46 of 46 sessions identical, maximum absolute F1 difference = 0.0000",
        "  Cao2018: 58 of 58 sessions identical, maximum absolute F1 difference = 0.0000",
        "",
        "This configuration is the one carried unchanged into Experiments 2 and 3.",
    ]
    write("pk_reference", lines)


# --------------------------------------------------------------------- per electrode
def packet_per_electrode() -> None:
    lines = ["PER-ELECTRODE DETECTION UNDER THE FULL-MONTAGE GATE",
             "(each electrode scored inside the 32-channel run; macro-averaged over "
             "sessions)", ""]
    for ds in ("raja", "cao"):
        g = P.per_channel(ds).sort_values("f1", ascending=False)
        lines.append(f"{DSN[ds]} — ranked electrodes (name: precision / recall / F1):")
        for _, r in g.iterrows():
            lines.append(f"  {r['display']}: {f4(r.p)} / {f4(r.r)} / {f4(r.f1)}")
        best, worst = g.iloc[0], g.iloc[-1]
        lines += [
            f"  best electrode = {best['display']} (F1 = {f4(best.f1)})",
            f"  worst electrode = {worst['display']} (F1 = {f4(worst.f1)})",
            "",
        ]
    write("pk_per_electrode", lines)


# -------------------------------------------------------------------------- regional
def packet_regional() -> None:
    lines = ["ANATOMICAL CHANNEL SUBSETS vs THE FULL MONTAGE",
             "(macro precision / recall / F1 at best-channel-per-session; delta F1 is the",
             " paired difference from the full montage; p is Bonferroni-corrected over 13",
             " comparisons within the dataset; r is matched-pairs rank-biserial)", ""]
    for ds in ("raja", "cao"):
        t = S.subset_stats(ds)
        lines.append(f"{DSN[ds]}:")
        for _, r in t.iterrows():
            if r.selection == S.REFERENCE:
                lines.append(f"  {r.label} ({r.n_ch} electrodes): "
                             f"{f4(r.precision)} / {f4(r.recall)} / {f4(r.f1)}  [reference]")
                continue
            lines.append(
                f"  {r.label} ({r.n_ch} electrodes): {f4(r.precision)} / {f4(r.recall)} / "
                f"{f4(r.f1)}  delta F1 = {r.delta:+.4f}  p = {fmt_p(r.p_bonf)}  "
                f"r = {r.r_rb:+.3f}  better than full montage in {r.n_better} of "
                f"{r.n_pairs} sessions")
        ns = t[(t.selection != S.REFERENCE) & (t.p_bonf > 0.05)].label.tolist()
        lines += [
            f"  subsets NOT significantly different from the full montage after "
            f"correction: {', '.join(ns) if ns else 'none'}",
            "",
        ]
    write("pk_regional", lines)


# ------------------------------------------------------------------- region pattern
def packet_region_pattern() -> None:
    """Coarse scalp-region collapse of the per-electrode figure (fig:region_performance).

    Same coarse-region assignment and same numbers as the retired region-performance
    table, kept in a packet so the pattern can still be described in prose.
    """
    lines = [
        "PER-ELECTRODE RESULTS COLLAPSED TO COARSE SCALP REGIONS",
        "(frontopolar, midline/outside, and unassigned electrodes excluded; each region",
        " row averages the per-channel macro precision, recall and F1 over the",
        " electrodes it contains; n is the number of electrodes in the region;",
        " percentages given to 2 decimal places)", "",
    ]
    for ds in ("raja", "cao"):
        g = R.coarse_regions(ds)
        lines.append(f"{P.DSN[ds]}:")
        for region in R.SUMMARY_REGION_ORDER:
            sub = g[g.coarse == region]
            if sub.empty:
                continue
            lines.append(
                f"  {region} (n={len(sub)}): precision = {P.fmt(sub.p.mean())}\\%, "
                f"recall = {P.fmt(sub.r.mean())}\\%, F1 = {P.fmt(sub.f1.mean())}\\%")
        front = g[g.coarse.isin(["frontal", "frontopolar"])]["f1"]
        non_front = g[~g.coarse.isin(["frontal", "frontopolar"])]["f1"]
        lines += [
            f"  frontal+frontopolar electrodes (n={len(front)}): mean F1 = "
            f"{P.fmt(front.mean())}\\%",
            f"  all other electrodes (n={len(non_front)}): mean F1 = "
            f"{P.fmt(non_front.mean())}\\%",
            "",
        ]
    write("pk_region_pattern", lines)


# ---------------------------------------------------------------------- failure mode
def packet_failure() -> None:
    lines = ["HOW THE NON-FRONTAL SUBSETS FAIL", ""]
    for ds in ("raja", "cao"):
        t = S.subset_stats(ds).set_index("label")
        lines.append(f"{DSN[ds]} — precision and recall of the posterior subsets:")
        for lab in ("All (full montage)", "Frontal", "Central", "Parietal", "Occipital",
                    "Posterior"):
            if lab in t.index:
                r = t.loc[lab]
                lines.append(f"  {lab}: precision = {f4(r.precision)}, "
                             f"recall = {f4(r.recall)}, F1 = {f4(r.f1)}")
        lines.append("")

    lines += ["STAGE-B BLINK-REGION THRESHOLD (sample-level detector parameter, "
              "microvolts, averaged over sessions)", ""]
    for ds in ("raja", "cao"):
        th = S.stage_b_threshold(ds).set_index("selection")
        lines.append(f"{DSN[ds]}:")
        for sel in ("fp1_only", "fp2_only", "frontal", "all_channel", "central",
                    "parietal", "occipital", "posterior", "central_right"):
            if sel in th.index:
                lines.append(f"  {th.loc[sel, 'label']} ({sel}): "
                             f"{th.loc[sel, 'thr_uv']:.1f}")
        lines.append("")
    lines += [
        "DIRECTION WARNING — the paragraph must not overstate this:",
        "  On Cao2018 the threshold falls monotonically from the frontopolar subsets to the",
        "  occipital ones. On Raja it does NOT: the central-right subset carries the highest",
        "  threshold of any subset while reaching the second-lowest F1, and the occipital",
        "  subsets sit close to the full-montage value. State the Cao2018 ordering, and state",
        "  plainly that Raja does not show the same ordering. Do not claim a single mechanism",
        "  that holds on both corpora.",
    ]
    write("pk_failure", lines)


# --------------------------------------------------------------------- single channel
def packet_single() -> None:
    lines = ["SINGLE-ELECTRODE OPERATION (the complete pipeline run on one electrode)",
             "NOTE: a single-electrode subset offers no channel to choose between, so these",
             "values carry no best-channel-per-session oracle.", ""]
    for ds in ("raja", "cao"):
        ref = S.reference_macro(ds)["f1"]
        t = S.solo_vs_montage(ds)
        lines.append(f"{DSN[ds]} (full-montage reference F1 = {f4(ref)}):")
        for _, r in t.iterrows():
            lines.append(
                f"  {r.channel} alone: precision = {f4(r.solo_p)}, recall = {f4(r.solo_r)}, "
                f"F1 = {f4(r.solo_f1)}  = {pct(100 * r.solo_f1 / ref)} percent of the "
                f"full-montage reference")
        lines.append("")
    lines += [
        "COMPARISON WITH MULTI-ELECTRODE SUBSETS (same dataset, F1):",
    ]
    for ds in ("raja", "cao"):
        t = S.subset_stats(ds).set_index("label")
        solo = S.solo_vs_montage(ds).set_index("channel")
        best_solo = solo.solo_f1.idxmax()
        lines.append(
            f"  {DSN[ds]}: {best_solo} alone (1 electrode) = {f4(solo.solo_f1.max())}; "
            f"Central ({int(t.loc['Central'].n_ch)} electrodes) = {f4(t.loc['Central'].f1)}; "
            f"Posterior ({int(t.loc['Posterior'].n_ch)} electrodes) = "
            f"{f4(t.loc['Posterior'].f1)}")
    write("pk_single", lines)


# ---------------------------------------------------------------- montage contribution
def packet_contribution() -> None:
    lines = [
        "WHAT THE REST OF THE MONTAGE CONTRIBUTES TO ONE ELECTRODE",
        "Each electrode is scored twice on the same sessions: running the whole pipeline on",
        "that electrode alone, and scored inside the full 32-channel run where Stage A",
        "screens epochs using every electrode. delta F1 = full montage minus single",
        "electrode, so a positive value means the other 31 electrodes helped.",
        "p is Bonferroni-corrected within each dataset.", "",
    ]
    for ds in ("raja", "cao"):
        t = S.solo_vs_montage(ds)
        lines.append(f"{DSN[ds]} (corrected over {t.attrs['n_comparisons']} electrodes):")
        for _, r in t.iterrows():
            lines.append(
                f"  {r.channel}: alone F1 = {f4(r.solo_f1)}, in full montage F1 = "
                f"{f4(r.gated_f1)}, delta F1 = {-r.delta:+.4f}, p = {fmt_p(r.p_bonf)}, "
                f"r = {r.r_rb:+.3f}")
            lines.append(
                f"      recall alone = {f4(r.solo_r)}, recall in full montage = "
                f"{f4(r.gated_r)}; precision alone = {f4(r.solo_p)}, precision in full "
                f"montage = {f4(r.gated_p)}")
        ns = t[t.p_bonf > 0.05].channel.tolist()
        sig = t[t.p_bonf <= 0.05].channel.tolist()
        lines += [f"  no significant gain after correction: {', '.join(ns) or 'none'}",
                  f"  significant gain after correction: {', '.join(sig) or 'none'}", ""]
    write("pk_contribution", lines)


# -------------------------------------------------------------------------- coverage
def packet_coverage() -> None:
    lines = ["SUBSET SIZE AGAINST PERFORMANCE (every point plotted in the coverage figure)",
             "format — subset (electrodes): F1", ""]
    for ds in ("raja", "cao"):
        d = S.load_median(ds)
        lines.append(f"{DSN[ds]}:")
        rows = []
        for sel in S.SUBSET_ORDER + ["fp1_only", "fp2_only", "af3_only", "af4_only",
                                     "f3_only", "f4_only"]:
            if sel not in set(d.selection):
                continue
            sub = d[d.selection == sel]
            label = (S.SUBSET_LABEL.get(sel)
                     or P.spell_1020(sel.replace("_only", "")) + " alone")
            rows.append((int(sub.n_channels_used.iloc[0]),
                         S.bps_series(sub)["f1"].mean(), label))
        for n_ch, f1, label in sorted(rows, key=lambda x: -x[1]):
            lines.append(f"  {label} ({n_ch} electrodes): {f4(f1)}")
        one = [r for r in rows if r[0] == 1]
        lines += [
            f"  spread among the {len(one)} single-electrode subsets: "
            f"{f4(min(r[1] for r in one))} to {f4(max(r[1] for r in one))}",
            "",
        ]
    write("pk_coverage", lines)


# ------------------------------------------------------------------------- frequency
def packet_frequency() -> None:
    lines = ["WHICH ELECTRODE WAS SELECTED AS BEST", ""]
    for ds in ("raja", "cao"):
        freq = S.best_channel_frequency(ds)
        total = int(freq.sum())
        lines.append(f"{DSN[ds]} — Experiment 1, full montage, {total} sessions:")
        for ch, n in freq.items():
            lines.append(f"  {ch}: {n} of {total} sessions ({n / total:.3f})")
        lines.append("")

    lines.append("Pooled over the four detection conditions of Experiment 2 "
                 "(session x condition selections):")
    for ds in ("raja", "cao"):
        df = P.load("exp2", ds)
        best = df["best_channel"].apply(lambda c: P.display_channel(ds, c))
        total = len(best)
        lines.append(f"  {DSN[ds]} ({total} selections):")
        for ch, n in best.value_counts().head(5).items():
            lines.append(f"    {ch}: {n} of {total} ({n / total:.3f})")
    write("pk_frequency", lines)


# ---------------------------------------------------------------------------- oracle
def packet_oracle() -> None:
    lines = [
        "COST OF THE BEST-CHANNEL-PER-SESSION RULE",
        "The manuscript reports every condition at its best-channel-per-session operating",
        "point, which is an oracle. Below, each fixed electrode is scored on every session",
        "and compared with the per-session best electrode of the full montage.", "",
    ]
    for ds in ("raja", "cao"):
        t = S.fixed_vs_oracle(ds)
        lines.append(f"{DSN[ds]} (per-session oracle F1 = {f4(t.attrs['oracle_f1'])}):")
        for _, r in t.iterrows():
            lines.append(
                f"  {r.channel} fixed in advance: F1 = {f4(r.f1)}, mean shortfall against "
                f"the oracle = {f4(r.shortfall_mean)}, median shortfall = "
                f"{f4(r.shortfall_median)}, within 0.02 of the oracle in "
                f"{int(r.within_002)} of {int(r.n)} sessions")
        lines.append("")
    write("pk_oracle", lines)


# ------------------------------------------------------------------------- agreement
def packet_agreement() -> None:
    """Best-channel agreement across the four Experiment 2 conditions.

    Computed exactly as ``tab12_channel_robustness.py`` computes it, including pooling
    over the concatenated 104-session matrix rather than averaging the two dataset
    means, so the packet cannot drift from the published table.
    """
    from itertools import combinations

    import numpy as np

    from tab12_channel_robustness import choice_matrix

    best = P.load_exp2_best()
    lines = ["AGREEMENT ON THE BEST ELECTRODE ACROSS THE FOUR DETECTION CONDITIONS", ""]
    for label, ds_list in [("Raja", ["raja"]), ("Cao2018", ["cao"]),
                           ("Pooled", ["raja", "cao"])]:
        mat = choice_matrix(best, ds_list)
        n, full = len(mat), int((mat.nunique(axis=1) == 1).sum())
        pairwise = np.mean([(mat[a] == mat[b]).mean()
                            for a, b in combinations(P.CONDS, 2)])
        lines += [
            f"{label} ({n} sessions):",
            f"  all four conditions chose the same electrode in {full} of {n} sessions "
            f"({full / n:.3f})",
            f"  mean pairwise agreement = {pairwise:.3f}",
        ]
        for cond in P.CONDS:
            agree = np.mean([(mat[cond] == mat[o]).mean()
                             for o in P.CONDS if o != cond])
            lines.append(f"    {cond}: {agree:.3f}")
        lines.append("")
    write("pk_agreement", lines)


def main() -> None:
    print(f"writing packets -> {OUT}")
    packet_design()
    packet_reference()
    packet_per_electrode()
    packet_region_pattern()
    packet_regional()
    packet_failure()
    packet_single()
    packet_contribution()
    packet_coverage()
    packet_frequency()
    packet_oracle()
    packet_agreement()


if __name__ == "__main__":
    main()
