"""Tables 14/15 and Figure 11 — cross-experiment summary of Proposed-Med.

Writes:
  ``writing/e_result/tab_exp_summary.tex``
  ``writing/e_result/tab_exp_stats.tex``
  ``writing/figures/fig_exp_boxplot.{pdf,png}``

Each of the three experiments is reduced to its primary configuration and Proposed-Med is
compared against the strongest baseline (BLINKER-concat) on session-level F1. The box plot
shows the distributions the summary table averages over, because a mean F1 alone cannot
show whether a method is uniformly good or merely good on average.

Aggregation: best-channel-per-session (argmax F1 over selections per session). See
``writing/VALUE_AUDIT.md``.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402

SCRIPT = "tab14_tab15_fig11_exp_summary.py"
BOOTSTRAP_N = 10_000
REFERENCE_EPOCH_S = 30.0
BASELINE = "BLINKER-concat"

EXPS = ["exp1", "exp2", "exp3"]
EXP_DESC = {
    "exp1": "Channel selection (whole-cap oracle)",
    "exp2": "Strategy comparison",
    "exp3": "Epoch duration (30\\,s)",
}


def bps_series(df: pd.DataFrame) -> pd.Series:
    """Per-session best F1, indexed by session."""
    return df.loc[df.groupby("session")["f1"].idxmax()].set_index("session")["f1"]


def pm_series(exp: str, ds: str) -> pd.Series:
    """Proposed-Med per-session F1 at the experiment's primary configuration."""
    if exp == "exp1":
        df = P.load("exp1", ds)
        return bps_series(df[df.center_method == "median"])
    if exp == "exp2":
        df = P.load("exp2", ds)
        return bps_series(df[df.condition == "Proposed-Med"])
    if exp == "exp3":
        df = P.load("exp3", ds)
        return bps_series(df[(df.center_method == "median")
                            & (df.epoch_duration_s == REFERENCE_EPOCH_S)])
    raise ValueError(f"unknown experiment {exp!r}")


def baseline_series(ds: str, condition: str) -> pd.Series:
    df = P.load("exp2", ds)
    return bps_series(df[df.condition == condition])


def build_figure(pm: dict, blinker: dict, mne: dict) -> None:
    records = [
        {"Experiment": exp, "Dataset": P.DSN[ds], "F1": v}
        for exp in EXPS for ds in ["raja", "cao"] for v in pm[(exp, ds)].to_numpy()
    ]
    plotdf = pd.DataFrame(records)

    sns.set_style("whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.2), sharey=True)
    for ax, ds in zip(axes, ["raja", "cao"]):
        sub = plotdf[plotdf.Dataset == P.DSN[ds]]
        sns.boxplot(data=sub, x="Experiment", y="F1", ax=ax,
                    color=("#4C72B0" if ds == "raja" else "#55A868"),
                    width=0.6, fliersize=2)
        bl, mn = blinker[ds].mean(), mne[ds].mean()
        ax.axhline(bl, ls="--", color="#C44E52", lw=1.5, label=f"BLINKER-concat ({bl:.2f})")
        ax.axhline(mn, ls=":", color="#8172B3", lw=1.5, label=f"MNE-annot ({mn:.2f})")
        ax.set_title(f"{P.DSN[ds]} ({len(pm[('exp2', ds)])} sessions)")
        ax.set_xlabel("Experiment")
        ax.set_ylabel("Session-level $F_1$" if ds == "raja" else "")
        ax.set_ylim(0, 1.0)
        ax.legend(loc="lower left", fontsize=8, framealpha=0.9)
    fig.suptitle("Proposed-Med session-level $F_1$ across experiments "
                 "(best channel per session)", fontsize=12)
    fig.tight_layout()
    P.save_fig(fig, "fig_exp_boxplot")
    plt.close(fig)


def build_summary(pm: dict, blinker: dict) -> list[str]:
    bl_pooled = pd.concat([blinker["raja"], blinker["cao"]]).mean()
    lines = [
        r"\begin{table*}[ht]", r"  \centering",
        r"  \caption{Proposed-Med detection performance across the three experiments on "
        r"the Raja and Cao2018 driving-EEG corpora. Macro-averaged $F_1$ over all sessions "
        r"(best-channel-per-session). The best competing method is BLINKER-concat from the "
        r"strategy comparison; $\Delta$ is the pooled Proposed-Med advantage over "
        f"BLINKER-concat (pooled macro-$F_1$ {bl_pooled:.4f}).}}",
        r"  \label{tab:exp_summary}", r"  \begin{tabular}{llccll}", r"    \toprule",
        r"    Exp. & Description & PM $F_1$ (Raja) & PM $F_1$ (Cao2018) & "
        r"Best competitor & $\Delta$ vs competitor \\",
        r"    \midrule",
    ]
    for exp in EXPS:
        raja, cao = pm[(exp, "raja")].mean(), pm[(exp, "cao")].mean()
        pooled = pd.concat([pm[(exp, "raja")], pm[(exp, "cao")]]).mean()
        lines.append(
            f"    {exp} & {EXP_DESC[exp]} & {raja:.4f} & {cao:.4f} & {BASELINE} & "
            f"${pooled - bl_pooled:+.4f}$ \\\\"
        )
    lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table*}"]
    return lines


def _p_cell(p: float) -> str:
    if np.isnan(p):
        return "n/a"
    if p <= 0:
        return r"$<10^{-12}$"
    if p < 1e-3:
        return f"$<10^{{{int(np.floor(np.log10(p)))}}}$"
    return f"{p:.3f}"


def build_stats(pm: dict, blinker: dict) -> list[str]:
    rng = np.random.default_rng(42)
    pairs = [(exp, ds) for exp in EXPS for ds in ["raja", "cao"]]
    n_comparisons = len(pairs)

    rows = []
    for exp, ds in pairs:
        a, b = pm[(exp, ds)], blinker[ds]
        common = a.index.intersection(b.index)
        av, bv = a.loc[common].to_numpy(), b.loc[common].to_numpy()
        diff = av - bv
        try:
            w, p = stats.wilcoxon(av, bv, alternative="greater", zero_method="wilcox")
        except ValueError:
            w, p = np.nan, np.nan
        p_bonf = min(1.0, p * n_comparisons) if not np.isnan(p) else np.nan
        n = len(av)
        r_eff = 1 - (2 * w) / (n * (n + 1)) if not np.isnan(w) else np.nan
        boot = np.array([rng.choice(diff, size=n, replace=True).mean()
                         for _ in range(BOOTSTRAP_N)])
        lo, hi = np.percentile(boot, [2.5, 97.5])
        rows.append((exp, P.DSN[ds], diff.mean(), w, p_bonf, r_eff, lo, hi, n))

    lines = [
        r"\begin{table*}[ht]", r"  \centering",
        r"  \caption{Paired Wilcoxon signed-rank tests of Proposed-Med versus the best "
        r"competing method (BLINKER-concat from the strategy comparison) on session-level "
        r"$F_1$, for each experiment and dataset. $\Delta F_1$ is the mean Proposed-Med "
        r"advantage; $p$ is Bonferroni-corrected over the " + str(n_comparisons)
        + r" comparisons (one-sided, Proposed-Med greater); $r$ is the rank-biserial "
        r"effect size; the 95\% CI is a " + f"{BOOTSTRAP_N:,}".replace(",", "{,}")
        + r"-sample bootstrap on $\Delta F_1$.}",
        r"  \label{tab:exp_stats}", r"  \begin{tabular}{llcccccc}", r"    \toprule",
        r"    Exp. & Dataset & $\Delta F_1$ & $W$ & $p_{\mathrm{Bonf}}$ & $r$ & "
        r"95\% CI & $n$ \\",
        r"    \midrule",
    ]
    for exp, ds, mean_diff, w, p_bonf, r_eff, lo, hi, n in rows:
        lines.append(
            f"    {exp} & {ds} & ${mean_diff:+.4f}$ & {w:.0f} & {_p_cell(p_bonf)} & "
            f"{r_eff:.3f} & $[{lo:+.4f},\\,{hi:+.4f}]$ & {n} \\\\"
        )
    lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table*}"]

    print("\nstats preview:")
    for exp, ds, mean_diff, _w, p_bonf, r_eff, lo, hi, _n in rows:
        print(f"   {exp} {ds:8s} d={mean_diff:+.4f} pBonf={p_bonf:.2e} "
              f"r={r_eff:.3f} CI=[{lo:+.4f},{hi:+.4f}]")
    return lines


def main() -> None:
    pm = {(exp, ds): pm_series(exp, ds) for exp in EXPS for ds in ["raja", "cao"]}
    blinker = {ds: baseline_series(ds, BASELINE) for ds in ["raja", "cao"]}
    mne = {ds: baseline_series(ds, "MNE-annot") for ds in ["raja", "cao"]}

    build_figure(pm, blinker, mne)
    P.write_tex(P.ER / "tab_exp_summary.tex", build_summary(pm, blinker), SCRIPT)
    P.write_tex(P.ER / "tab_exp_stats.tex", build_stats(pm, blinker), SCRIPT)


if __name__ == "__main__":
    main()
