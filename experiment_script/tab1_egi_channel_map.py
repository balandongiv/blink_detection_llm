"""Table 1 — Raja EGI-128 (HydroCel GSN) to 10--20 channel-name mapping.

Writes ``writing/e_result/exp1/tab_egi_channel_map.tex``.

Source: ``32_ch.csv`` (the montage file used by the Raja acquisition) plus the region
assignment actually used by the Experiment 1 run (``brain_region_raja.yaml``). Cao2018 is
recorded directly in 10--20 nomenclature and needs no mapping.

Run inside conda env ``double_threshold_algo``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as P  # noqa: E402

SCRIPT = "tab1_egi_channel_map.py"


def main() -> None:
    rmap = P.region_map("raja")
    names = P.egi_to_1020()
    rows = pd.DataFrame(
        [{"egi_lbl": egi, "egi_id": int(egi[1:]), "name1020": name,
          "region": rmap.get(egi.upper(), "--")}
         for egi, name in names.items()]
    ).sort_values(["region", "egi_id"])

    lines = [
        r"\begin{table}[ht]", r"\centering", r"\footnotesize",
        r"\caption{Internal-dataset EGI 128-channel (HydroCel GSN) to 10--20 scalp-location mapping, "
        r"taken from the \texttt{egi\_pair} block of \texttt{brain\_region\_raja.yaml}. "
        r"Results are reported throughout by 10--20 location; this table gives the native "
        r"EGI index for each one. The region column is the assignment used by the "
        r"Experiment~1 run; \texttt{midline\_or\_outside} marks electrodes outside the "
        r"curated left/right regions. Cao2018 is acquired directly in 10--20 nomenclature "
        r"and needs no mapping.}",
        r"\label{tab:egi_map}", r"\begin{tabular}{lll}", r"\toprule",
        r"10--20 & EGI & Region \\", r"\midrule",
    ]
    for _, row in rows.iterrows():
        lines.append(
            f"{row.name1020} & {row.egi_lbl} & {P.tex_escape(row.region)} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]

    P.write_tex(P.ER / "exp1" / "tab_egi_channel_map.tex", lines, SCRIPT)


if __name__ == "__main__":
    main()
