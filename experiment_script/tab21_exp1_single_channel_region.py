"""Table 21 — single-electrode results aggregated to the five established scalp regions.

Writes ``writing/e_result/exp1/tab_exp1_single_channel_region.tex``.

Companion to Table 17 (``tab17_exp1_subset_summary.py``): Table 17 compares each
region's own self-contained multi-electrode SUBSET rerun against the same electrodes
scored inside the full-montage run. This table adds a third, finer condition — each
region's electrodes run entirely INDEPENDENTLY (one ``*_only`` detector per electrode,
averaged) — so the same region can be read across three levels of channel context:
individual electrode -> regional subset -> full montage.

The primary paired comparison (Single vs Full montage) uses the same session-paired
Wilcoxon signed-rank + matched-pairs rank-biserial framework as
``subset_stats_region_mean``, Bonferroni-corrected over the 5 regions tested within
each dataset (a family separate from the 32-electrode family in
``fig16_exp1_single_channel_stats.py``). The Friedman column is the omnibus test across all
three conditions (Single / Subset / Full), Bonferroni-corrected over the 5 regions
tested within each dataset — a separate family again; see
``exp1_subset_data.three_level_region_stats`` for the pairwise post-hoc contrasts run
when a region's omnibus test is significant.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exp1_subset_data as S  # noqa: E402
import paper_data as P  # noqa: E402

SCRIPT = "tab21_exp1_single_channel_region.py"
OUT = P.ER / "exp1" / "tab_exp1_single_channel_region.tex"


def fmt_p(p: float) -> str:
    if p != p:
        return "--"
    return r"$<0.001$" if p < 0.001 else f"${p:.3f}$"


def dataset_block(ds: str, title: str) -> list[str]:
    reg = S.solo_stats_region_mean(ds)
    three = S.three_level_region_stats(ds)
    lines = [rf"\multicolumn{{8}}{{l}}{{\textit{{{title}}}}} \\[2pt]"]
    for _, r in reg.iterrows():
        region = r["region"]
        subset_f1 = three[region]["means"]["subset"]
        friedman_p = three[region]["friedman_p_bonf"]
        lines.append(
            f"{r['label']} & {r['n_ch']} & {P.fmt(r['f1'])} & {P.fmt(subset_f1)} & "
            f"{P.fmt(r['f1_montage'])} & ${P.fmt_pp(r['delta'])}$ & "
            f"{fmt_p(r['p_bonf'])} & ${r['r_rb']:+.2f}$ & {fmt_p(friedman_p)} \\\\"
        )
    return lines


def main() -> None:
    lines = [
        r"\begin{table}[htbp]", r"\centering", r"\footnotesize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\caption{Single-electrode results of Proposed-approach (median centre) aggregated "
        r"to the five scalp regions used throughout this section (Table~\ref{tab:exp1_subset_summary}; "
        r"``Posterior'' is parietal $\cup$ occipital). $F_1$ (Single) averages each region's "
        r"electrodes' own independent single-electrode detector; $F_1$ (Subset) is the "
        r"same region's self-contained multi-electrode subset rerun "
        r"(Table~\ref{tab:exp1_subset_summary}); $F_1$ (Full) is the same electrodes scored "
        r"inside the full-montage run. $\Delta F_1$, adjusted $p$ and $r_{\mathrm{rb}}$ test "
        r"Single against Full montage only (two-tailed Wilcoxon signed-rank, paired by "
        r"session, Bonferroni-corrected over the 5 regions tested within each dataset); "
        r"$\Delta F_1$ is Single minus Full, so a negative value means the region performed "
        r"worse as independent single-electrode detectors than inside the full montage. "
        r"The last column is the Friedman omnibus test across all three conditions "
        r"(Single / Subset / Full), Bonferroni-corrected over the same 5-region family; "
        r"pairwise post-hoc contrasts for regions reaching significance are reported in "
        r"the text.}",
        r"\label{tab:exp1_single_channel_region}",
        r"\begin{tabular}{lrrrrrrrr}", r"\toprule",
        r"Region & $n$ & $F_1$ Single (\%) & $F_1$ Subset (\%) & $F_1$ Full (\%) & "
        r"$\Delta F_1$ (pp) & adjusted $p$ & $r_{\mathrm{rb}}$ & Friedman adj. $p$ \\",
        r"\midrule",
        *dataset_block("raja", f"{P.DSN['raja']} (EGI 128, {len(P.bps(P.load('exp1', 'raja')))} sessions)"),
        r"\midrule",
        *dataset_block("cao", f"Cao2018 (10--20, {len(P.bps(P.load('exp1', 'cao')))} sessions)"),
        r"\bottomrule", r"\end{tabular}", r"\end{table}",
    ]
    P.write_tex(OUT, lines, SCRIPT)

    for ds, title in (("raja", "Internal"), ("cao", "Cao2018")):
        reg = S.solo_stats_region_mean(ds)
        three = S.three_level_region_stats(ds)
        print(f"=== {title} ===")
        for _, r in reg.iterrows():
            region = r["region"]
            m = three[region]["means"]
            fp = three[region]["friedman_p_bonf"]
            fp_str = f"{fp:.4g}" if fp == fp else "n/a"
            print(f"  {r['label']:10s} single={m['single']*100:6.2f} "
                  f"subset={m['subset']*100:6.2f} full={m['full']*100:6.2f}  "
                  f"delta(single-full)={r['delta']*100:+6.2f} p_bonf={r['p_bonf']:.4g} "
                  f"r_rb={r['r_rb']:+.3f}  friedman_p_bonf={fp_str}")
            for name, pw in three[region]["pairwise"].items():
                print(f"      {name}: delta={pw['delta']*100:+.2f} p_bonf={pw['p_bonf']:.4g} "
                      f"r_rb={pw['r_rb']:+.3f}")


if __name__ == "__main__":
    main()
