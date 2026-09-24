# -*- coding: utf-8 -*-
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

ROOT = r"C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm"
path = ROOT + r"\validation_pivot\exp1_channel_selection_raja_results.xlsx"

wb = openpyxl.load_workbook(path)
if "validation_info" in wb.sheetnames:
    del wb["validation_info"]
ws = wb.create_sheet("validation_info")

header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
header_font = Font(color="FFFFFF", bold=True)
pass_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
warn_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
fail_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

cols = ["Figure/Sheet", "Manuscript caption / claim", "Source CSV", "Rows / Columns / Filters / Values",
        "Aggregation", "Manuscript value(s)", "Pivot value(s)", "Diff", "Status", "Notes"]
ws.append(cols)
for c in range(1, len(cols)+1):
    cell = ws.cell(row=1, column=c)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(wrap_text=True, vertical="top")

def add_row(*vals, status_col=9):
    ws.append(vals)
    r = ws.max_row
    status = vals[status_col-1]
    fill = None
    if status.startswith("PASS"):
        fill = pass_fill
    elif status == "WARNING":
        fill = warn_fill
    elif status in ("FAIL", "NOT REPRODUCIBLE", "SOURCE NOT FOUND"):
        fill = fail_fill
    if fill:
        ws.cell(row=r, column=status_col).fill = fill
    for c in range(1, len(cols)+1):
        ws.cell(row=r, column=c).alignment = Alignment(wrap_text=True, vertical="top")

SRC = "publication_results/exp1_channel_raja/exp1_channel_selection_raja_results.csv (11408 rows, dataset=raja/Internal), channel mapped EGI->10-20 via validation_pivot/_tools/egi_to_1020_map_internal.csv"

# ---- Scope / method note row ----
add_row(
    "GENERAL",
    "Scope: Internal dataset (dataset=raja) only, Figures 3-6 of Experiment 1 (EEG channel-subset analysis). Excludes Cao2018 (sibling agent), Figure 7, Table 1/Figure 8 (other sibling agents).",
    SRC,
    "raw_data sheet = full mapped CSV as native Excel Table (11408 rows x 23 cols incl. channel_1020). All pivots are genuine Excel COM PivotTable objects (PivotCaches().Create + CreatePivotTable), not typed-in values, built via validation_pivot/_tools/pivot_cookbook.ps1.",
    "n/a",
    "n/a", "n/a", "n/a", "PASS",
    "24 curated electrodes VERIFIED against data by pandas groupby (non-null f1 per region selection): frontal={Fp1,AF3,F3,AF4,Fp2,F4} (6), central={FC1,C3,FC5,C4,FC2,FC6} (6), parietal={CP1,CP5,CP2,CP6} (4), occipital={P7,P3,PO3,O1,PO4,P4,P8,E83} (8) = 24 total. Matches manuscript's implied list exactly.",
)

add_row(
    "E83 mapping gap",
    "N/A - documentation discrepancy check",
    "validation_pivot/_tools/egi_to_1020_map_internal.csv; writing/e_result/obs/exp1/tab_egi_channel_map.tex",
    "n/a", "n/a", "n/a", "n/a", "n/a", "WARNING",
    "CONFIRMED genuine discrepancy: EGI code E83 is one of the 24 curated electrodes used in the actual raw data (occipital region, e83_only selection present, non-null f1) but is NOT among the 32 EGI codes listed in the manuscript's own official channel-map table (tab_egi_channel_map.tex). The manuscript's own Figure 5/6 electrode-label axis displays it unmapped as literal 'E83' (confirmed in extracted PDF text, line ~671/473), i.e. the manuscript itself already treats E83 as a labeling exception rather than silently omitting it. This is a pre-existing documentation gap in the manuscript's mapping table, not an error introduced by this validation. Not fixed here per instructions - reported only.",
)

# ---- Figure 3 ----
add_row(
    "Figure 3 / fig3_per_electrode_subset",
    "\"Per-electrode detection F1 within each region's own channel-subset rerun, coloured by scalp region.\"",
    SRC,
    "Rows=channel_1020 (24 curated, RowItemsToShow); Filters: center_method=median (single page), selection IN {frontal,central,parietal,occipital} (multi page); Values=Average of f1",
    "Excel PivotTable Average (xlAverage) of f1",
    "Fp2=85.28%, Fp1=84.84%, AF4=77.04%, AF3=70.70%, F3=42.68%, F4=41.00% (frontal); C3=58.59%, C4=1.73% (central); best parietal CP1=1.92%; best occipital PO3=3.35%",
    "Fp2=85.28%, Fp1=84.84%, AF4=77.04%, AF3=70.70%, F3=42.68%, F4=41.00% (pivot 40.998); C3=58.59%, C4=1.73%; CP1=1.92%; PO3=3.35% (pivot 3.346)",
    "<=0.005pp on every printed value",
    "PASS",
    "All 10 manuscript-printed values for Internal reproduced to within +/-0.005pp using genuine PivotTable Average-of-f1 with selection as a multi-item page filter and channel_1020 as row field. center_method=median filter confirmed correct (matches manuscript, cross-checked by sibling Cao2018 agent).",
)

# ---- Figure 4 ----
add_row(
    "Figure 4 / fig4_subset_vs_montage",
    "\"Per-electrode comparison of Proposed-approach F1 when each electrode was evaluated inside its own self-contained anatomical subset rerun ... against the same electrode evaluated inside the full-montage run.\"",
    SRC,
    "Rows=channel_1020 (24 curated); Columns=selection IN {all_channel,frontal,central,parietal,occipital}; Filters: center_method=median; Values=Average of f1",
    "Excel PivotTable Average of f1, paired descriptive means only (asterisks are supplementary stats, see below)",
    "Descriptive: Fp1 subset=84.84%/montage=86.32%; Fp2 subset=85.28%/montage=86.82%; AF4 subset=77.04%/montage=80.32%; AF3 subset=70.70%/montage=73.76%; C3 subset=58.59%/montage=61.06%; C4 subset=1.73%/montage=1.85%. Stats: \"11 of the 24 electrodes tested remained significantly different\"; Fp1,Fp2 NOT sig (adj p=1.000); AF4,AF3 sig; C3 sig, C4 not; CP2,CP5,CP6,PO3,PO4 also sig despite low F1",
    "Pivot descriptive all match to <=0.005pp (see raw dump). Supplementary Wilcoxon (paired by session, Bonferroni x24, scipy.stats.wilcoxon, median rows only): 11 of 24 significant - EXACT MATCH. Non-sig: Fp1(adj p=1.000),Fp2(adj p=1.000),FC1,FC5,C4,FC2,CP1,P7,P3,O1,P4,P8. Sig: AF3,F3,AF4,F4,C3,FC6,CP5,CP2,CP6,PO3,PO4 - matches manuscript's explicit list (AF4,AF3 sig; C3 sig/C4 not; CP2,CP5,CP6,PO3,PO4 sig) exactly.",
    "descriptive <=0.005pp; stats: exact call match",
    "PASS",
    "Descriptive means match manuscript to full printed precision. Independent supplementary Wilcoxon signed-rank (two-tailed, paired by session, Bonferroni-corrected x24) reproduces the manuscript's count (11/24), the Fp1/Fp2 non-significance, and every explicitly-named significant/non-significant electrode (AF3,F3,AF4,F4,C3,C4,CP2,CP5,CP6,PO3,PO4) exactly. This is a post-hoc statistical check performed after the independent pivot validation, as explicitly allowed.",
)

# ---- Figure 5 ----
add_row(
    "Figure 5 / fig5_single_channel",
    "\"Detection F1 of every electrode in the four curated anatomical regions operating as its own self-contained detector ... coloured by scalp region.\"",
    SRC,
    "Rows=channel_1020 (24 curated); Filters: center_method=median (single page), selection IN {<24 electrode>_only} (multi page); Values=Average of f1",
    "Excel PivotTable Average of f1",
    "Fp1=83.73%,Fp2=83.37%,AF4=75.16%,AF3=67.59%,C3=54.05%,F4=39.98%,F3=39.85%,C4=1.51%(weakest); chart labels: FC5=9.5,FC6=6.7,FC2=2.7,FC1=2.4,CP1=1.9,CP2=1.9,CP5=1.6,CP6=1.5,PO3=3.1,PO4=2.6,O1=2.0,E83=1.8,P3=1.7,P8=1.6,P7=1.6,P4=1.6 (all 1-decimal chart precision); Fig6 text bound: delta -7.02 to -0.15pp",
    "Fp1=83.73(pivot 83.728),Fp2=83.37(83.368),AF4=75.16(75.161),AF3=67.59(67.595),C3=54.05(54.045),F4=39.98(39.977),F3=39.85(39.853),C4=1.51(1.513); FC5=9.51,FC6=6.73,FC2=2.69,FC1=2.42,CP1=1.86,CP2=1.86,CP5=1.57,CP6=1.53,PO3=3.15,PO4=2.65,O1=1.97,E83=1.78,P3=1.66,P8=1.62,P7=1.61,P4=1.57",
    "high-precision fields <=0.005pp; chart-only fields <=0.06pp (well within +/-0.2pp tolerance)",
    "PASS",
    "Ranking verified: Fp1 > Fp2 > AF4 > AF3 are the top 4 (Fp1 now leads Fp2, matching manuscript's note that the order flips vs full-montage). All values within tolerance. C4=1.51% confirmed as the single weakest among the 24 (matches 'weakest was C4 at F1=1.51%').",
)

# ---- Figure 6 ----
add_row(
    "Figure 6 / fig6_single_channel_stats",
    "\"Per-electrode F1: single-electrode operation vs. full montage.\"",
    SRC,
    "Rows=channel_1020 (24 curated); Columns=selection IN {all_channel} + {<24 electrode>_only}; Filters: center_method=median; Values=Average of f1",
    "Excel PivotTable Average of f1 (descriptive) + supplementary Wilcoxon",
    "\"14 of the 24 electrodes tested remained significantly different after correction\"; F1 delta range -7.02 to -0.15pp among all 24; Fp1,Fp2 NOT sig (adj p=1.000 both); AF4,AF3 DID reach sig; most occipital sig 'except O1 and P4'",
    "Descriptive all_channel column matches Fig4/Fig5 values exactly (internal consistency check passed). Supplementary Wilcoxon (paired by session, Bonferroni x24): 14 of 24 significant - EXACT MATCH. Delta range -7.015 to -0.155pp - MATCHES (-7.02 to -0.15 after rounding). Fp1 adj p=1.000, Fp2 adj p=1.000 - MATCH (non-sig). AF3 sig, AF4 sig - MATCH. Occipital non-sig set = {O1, P4} exactly, all other occipital (P7,P3,PO3,PO4,P8,E83) sig - EXACT MATCH to 'except O1 and P4'.",
    "descriptive <=0.005pp; stats count exact; delta range <=0.01pp; every named electrode call exact",
    "PASS",
    "Strongest cross-check in this workbook: every qualitative claim in the manuscript text (14/24 count, delta range, Fp1/Fp2 non-sig, AF3/AF4 sig, O1/P4 as the sole non-sig occipital exceptions) was reproduced exactly by an independent Wilcoxon signed-rank computation over session-paired f1 (median center_method only), Bonferroni-corrected x24. See validation_pivot/_tools/stats_raja.py for the script.",
)

# ---- Raw data sheet note ----
add_row(
    "raw_data",
    "n/a - underlying data sheet",
    SRC,
    "Full 11408-row raw CSV loaded via pandas, channel (EGI code) mapped to new channel_1020 column via egi_to_1020_map_internal.csv, written as a native Excel Table (ListObject) via COM Add-TableFromUsedRange. Used as PivotCache source for all 4 figure pivots.",
    "n/a", "n/a", "n/a", "n/a", "PASS",
    "0 unmapped channel_1020 values (all EGI codes in the data, including E83, resolved via the mapping CSV). Row count 11408 (background note said 11409; off-by-one vs actual file, immaterial).",
)

for i, width in enumerate([26, 46, 30, 46, 20, 46, 46, 20, 14, 60], start=1):
    ws.column_dimensions[get_column_letter(i)].width = width
ws.freeze_panes = "A2"

wb.save(path)
print("saved", path)
print("sheets:", wb.sheetnames)
