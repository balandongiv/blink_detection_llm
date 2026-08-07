"""Table 2 — Experiment 1 channel-by-channel detection performance.

Writes ``writing/e_result/tab_exp1_channel_ablation.tex``.

Every entry is one electrode evaluated on its own: the ``selection == "all_channel"``
rows of the Experiment 1 results already carry per-channel precision/recall/F1, so the
table applies **no** region-level aggregation — it only groups the rows for display.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402

SCRIPT = "tab2_exp1_channel_ablation.py"


def main() -> None:
    lines = [
        r"\begin{table}[htbp]", r"\centering", r"\scriptsize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\caption{Experiment~1 channel-by-channel detection performance of Proposed-Med "
        r"(median centre), organised by scalp region with \emph{no} region-level "
        r"aggregation. Each entry is the median-thresholded detector evaluated on a single "
        r"channel, with macro-averaged precision, recall and $F_1$ averaged over all "
        r"sessions (values read directly from the \texttt{selection=all\_channel} rows of "
        r"the Experiment~1 results). Electrodes are identified by their 10--20 scalp "
        r"location on both corpora; for Raja the corresponding native EGI HydroCel index is "
        r"given alongside it (full mapping in Table~\ref{tab:egi_map}). Best $F_1$ per "
        r"dataset in \textbf{bold}.}",
        r"\label{tab:exp1_channel_ablation}", r"\begin{tabular}{lllrrr}", r"\toprule",
        r"Region & Channel & EGI & Precision & Recall & $F_1$ \\", r"\midrule",
    ]

    for ds in ["raja", "cao"]:
        g = P.per_channel(ds)
        best_f1 = g["f1"].max()
        hardware = "EGI 128" if ds == "raja" else "10--20"
        n_sessions = int(g["n"].max())
        lines.append(
            r"\multicolumn{6}{l}{\textit{"
            + f"{P.DSN[ds]} ({hardware}, {n_sessions} sessions)"
            + r"}} \\[2pt]"
        )
        for region in P.REGION_ORDER:
            sub = g[g.region == region].sort_values("f1", ascending=False)
            if sub.empty:
                continue
            first = True
            for _, row in sub.iterrows():
                region_cell = P.tex_escape(region) if first else ""
                f1_cell = (r"\textbf{" + f"{row.f1:.3f}" + "}"
                           if row.f1 == best_f1 else f"{row.f1:.3f}")
                egi_cell = row.ch if ds == "raja" else "--"
                lines.append(
                    f"{region_cell} & {P.tex_escape(row.display)} & {egi_cell} & "
                    f"{row.p:.3f} & {row.r:.3f} & {f1_cell} \\\\"
                )
                first = False
        lines.append(r"\midrule" if ds == "raja" else r"\bottomrule")

    lines += [r"\end{tabular}", r"\end{table}"]
    P.write_tex(P.ER / "tab_exp1_channel_ablation.tex", lines, SCRIPT)

    # Audit log: the per-channel identifiers behind every number in the table.
    print("\n--- Experiment 1 channel-by-channel (proposed_median_<region>_<channel>) ---")
    for ds in ["raja", "cao"]:
        g = P.per_channel(ds).sort_values(["region", "f1"], ascending=[True, False])
        print(f"[{P.DSN[ds]}]")
        for _, row in g.iterrows():
            print(f"   proposed_median_{row.region}_{row.display:<5} ({row.ch})  "
                  f"P={row.p:.3f} R={row.r:.3f} F1={row.f1:.3f}")


if __name__ == "__main__":
    main()
