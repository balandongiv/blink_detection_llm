. "C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm\validation_pivot\_tools\pivot_cookbook.ps1"
$wbPath = "C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm\validation_pivot\exp1_channel_selection_raja_results.xlsx"

$SRC = "publication_results/exp1_channel_raja/exp1_channel_selection_raja_results.csv (11408 rows, dataset=raja/Internal), channel mapped EGI->10-20 via validation_pivot/_tools/egi_to_1020_map_internal.csv"

$header = @("Figure/Sheet","Manuscript caption / claim","Source CSV","Rows / Columns / Filters / Values","Aggregation","Manuscript value(s)","Pivot value(s)","Diff","Status","Notes")

$rows = @()

$rows += ,@(
  "GENERAL",
  "Scope: Internal dataset (dataset=raja) only, Figures 3-6 of Experiment 1 (EEG channel-subset analysis). Excludes Cao2018 (sibling agent), Figure 7, Table 1/Figure 8 (other sibling agents).",
  $SRC,
  "raw_data sheet = full mapped CSV as native Excel Table (11408 rows x 23 cols incl. channel_1020). All pivots are genuine Excel COM PivotTable objects (PivotCaches().Create + CreatePivotTable), not typed-in values, built via validation_pivot/_tools/pivot_cookbook.ps1.",
  "n/a","n/a","n/a","n/a","PASS",
  "24 curated electrodes VERIFIED against data by pandas groupby (non-null f1 per region selection): frontal={Fp1,AF3,F3,AF4,Fp2,F4} (6), central={FC1,C3,FC5,C4,FC2,FC6} (6), parietal={CP1,CP5,CP2,CP6} (4), occipital={P7,P3,PO3,O1,PO4,P4,P8,E83} (8) = 24 total. Matches manuscript's implied list exactly."
)

$rows += ,@(
  "E83 mapping gap",
  "N/A - documentation discrepancy check",
  "validation_pivot/_tools/egi_to_1020_map_internal.csv; writing/e_result/obs/exp1/tab_egi_channel_map.tex",
  "n/a","n/a","n/a","n/a","n/a","WARNING",
  "CONFIRMED genuine discrepancy: EGI code E83 is one of the 24 curated electrodes used in the actual raw data (occipital region, e83_only selection present, non-null f1) but is NOT among the 32 EGI codes listed in the manuscript's own official channel-map table (tab_egi_channel_map.tex). The manuscript's own Figure 5/6 electrode-label axis displays it unmapped as literal 'E83' (confirmed in extracted PDF text). This is a pre-existing documentation gap in the manuscript's mapping table, not an error introduced by this validation. Reported only, not modified."
)

$rows += ,@(
  "Figure 3 / fig3_per_electrode_subset",
  "Per-electrode detection F1 within each region's own channel-subset rerun, coloured by scalp region.",
  $SRC,
  "Rows=channel_1020 (24 curated); Filters: center_method=median (single page), selection IN {frontal,central,parietal,occipital} (multi page); Values=Average of f1",
  "Excel PivotTable Average (xlAverage) of f1",
  "Fp2=85.28%,Fp1=84.84%,AF4=77.04%,AF3=70.70%,F3=42.68%,F4=41.00% (frontal); C3=58.59%,C4=1.73% (central); best parietal CP1=1.92%; best occipital PO3=3.35%",
  "Fp2=85.2801%,Fp1=84.8388%,AF4=77.0442%,AF3=70.6996%,F3=42.6821%,F4=40.9978%; C3=58.5925%,C4=1.7343%; CP1=1.9225%; PO3=3.3465%",
  "<=0.005pp on every printed value",
  "PASS",
  "All 10 manuscript-printed Internal values reproduced to within +/-0.005pp using genuine PivotTable Average-of-f1, selection as multi-item page filter, channel_1020 as row field. center_method=median confirmed correct."
)

$rows += ,@(
  "Figure 4 / fig4_subset_vs_montage",
  "Per-electrode comparison of Proposed-approach F1: own-subset rerun vs full-montage run.",
  $SRC,
  "Rows=channel_1020 (24 curated); Columns=selection IN {all_channel,frontal,central,parietal,occipital}; Filters: center_method=median; Values=Average of f1",
  "Descriptive: PivotTable Average of f1. Stats (supplementary, post-hoc): paired Wilcoxon signed-rank by session, Bonferroni x24 (scipy.stats.wilcoxon)",
  "Descriptive: Fp1 84.84/86.32; Fp2 85.28/86.82; AF4 77.04/80.32; AF3 70.70/73.76; C3 58.59/61.06; C4 1.73/1.85. Stats: 11 of 24 sig; Fp1,Fp2 NOT sig (adj p=1.000); AF4,AF3 sig; C3 sig/C4 not; CP2,CP5,CP6,PO3,PO4 also sig despite low F1",
  "Descriptive matches to <=0.005pp. Stats: 11 of 24 significant - EXACT MATCH. Non-sig: Fp1(p=1.000),Fp2(p=1.000),FC1,FC5,C4,FC2,CP1,P7,P3,O1,P4,P8. Sig: AF3,F3,AF4,F4,C3,FC6,CP5,CP2,CP6,PO3,PO4 - matches manuscript's explicit named list exactly.",
  "descriptive <=0.005pp; stats: exact call match",
  "PASS",
  "Independent supplementary Wilcoxon (two-tailed, paired by session, Bonferroni x24, median rows only) reproduces manuscript count (11/24), Fp1/Fp2 non-significance, and every explicitly-named electrode call exactly. Post-hoc check performed after the independent pivot validation, as allowed. Script: validation_pivot/_tools/stats_raja.py"
)

$rows += ,@(
  "Figure 5 / fig5_single_channel",
  "Detection F1 of every electrode in the four curated anatomical regions operating as its own self-contained detector.",
  $SRC,
  "Rows=channel_1020 (24 curated); Filters: center_method=median (single page), selection IN {<electrode>_only} (multi page); Values=Average of f1",
  "Excel PivotTable Average of f1",
  "Fp1=83.73,Fp2=83.37,AF4=75.16,AF3=67.59,C3=54.05,F4=39.98,F3=39.85,C4=1.51(weakest); FC5=9.5,FC6=6.7,FC2=2.7,FC1=2.4,CP1=1.9,CP2=1.9,CP5=1.6,CP6=1.5,PO3=3.1,PO4=2.6,O1=2.0,E83=1.8,P3=1.7,P8=1.6,P7=1.6,P4=1.6",
  "Fp1=83.728,Fp2=83.368,AF4=75.161,AF3=67.595,C3=54.045,F4=39.977,F3=39.853,C4=1.513; FC5=9.509,FC6=6.730,FC2=2.687,FC1=2.424,CP1=1.864,CP2=1.862,CP5=1.574,CP6=1.526,PO3=3.148,PO4=2.645,O1=1.967,E83=1.778,P3=1.665,P8=1.622,P7=1.609,P4=1.570",
  "high-precision fields <=0.005pp; chart-only fields <=0.06pp (within +/-0.2pp tolerance)",
  "PASS",
  "Ranking verified: Fp1 > Fp2 > AF4 > AF3 top 4 (Fp1 leads Fp2, matching manuscript note that order flips vs full montage). C4=1.51% confirmed weakest of the 24."
)

$rows += ,@(
  "Figure 6 / fig6_single_channel_stats",
  "Per-electrode F1: single-electrode operation vs. full montage.",
  $SRC,
  "Rows=channel_1020 (24 curated); Columns=selection IN {all_channel}+{<electrode>_only}; Filters: center_method=median; Values=Average of f1",
  "Descriptive: PivotTable Average of f1. Stats (supplementary, post-hoc): paired Wilcoxon signed-rank by session, Bonferroni x24",
  "14 of 24 sig; delta range -7.02 to -0.15pp; Fp1,Fp2 NOT sig (adj p=1.000 both); AF4,AF3 DID reach sig; most occipital sig 'except O1 and P4'",
  "Descriptive all_channel column matches Fig4/Fig5 exactly (internal consistency passed). Stats: 14 of 24 significant - EXACT MATCH. Delta range -7.015 to -0.155pp - MATCHES after rounding. Fp1 p=1.000, Fp2 p=1.000 - MATCH. AF3 sig, AF4 sig - MATCH. Occipital non-sig set = {O1,P4} exactly, rest (P7,P3,PO3,PO4,P8,E83) sig - EXACT MATCH.",
  "descriptive <=0.005pp; stats count exact; delta range <=0.01pp; every named electrode call exact",
  "PASS",
  "Strongest cross-check in this workbook: every qualitative claim (14/24 count, delta range, Fp1/Fp2 non-sig, AF3/AF4 sig, O1/P4 sole non-sig occipital exceptions) reproduced exactly by independent Wilcoxon. Script: validation_pivot/_tools/stats_raja.py"
)

$rows += ,@(
  "raw_data",
  "n/a - underlying data sheet",
  $SRC,
  "Full 11408-row raw CSV loaded via pandas, channel (EGI code) mapped to new channel_1020 column via egi_to_1020_map_internal.csv, written as a native Excel Table (ListObject) via COM Add-TableFromUsedRange. Used as PivotCache source for all 4 figure pivots.",
  "n/a","n/a","n/a","n/a","PASS",
  "0 unmapped channel_1020 values (all EGI codes in the data, including E83, resolved via the mapping CSV). Row count 11408."
)

$excel = $null
try {
    $excel = New-ExcelApp
    $wb = $excel.Workbooks.Open($wbPath)

    # remove existing validation_info sheet if present
    foreach ($ws in @($wb.Worksheets)) {
        if ($ws.Name -eq "validation_info") { $ws.Delete() }
    }

    $newSheet = $wb.Worksheets.Add()
    $newSheet.Name = "validation_info"

    # header
    for ($c=0; $c -lt $header.Count; $c++) {
        $cell = $newSheet.Cells.Item(1, $c+1)
        $cell.Value2 = $header[$c]
        $cell.Font.Bold = $true
        $cell.Interior.Color = 0x783C1F  # BGR-ish dark blue
        $cell.Font.Color = 0xFFFFFF
    }

    $r = 2
    foreach ($row in $rows) {
        for ($c=0; $c -lt $row.Count; $c++) {
            $newSheet.Cells.Item($r, $c+1).Value2 = $row[$c]
        }
        $statusCol = 9
        $status = $row[$statusCol-1]
        $cell = $newSheet.Cells.Item($r, $statusCol)
        if ($status -eq "PASS") { $cell.Interior.Color = 0xC6EFCE }
        elseif ($status -eq "WARNING") { $cell.Interior.Color = 0x9CEBFF }
        elseif ($status -eq "FAIL") { $cell.Interior.Color = 0xC7C7FF }
        $r++
    }

    $newSheet.Columns.Item(1).ColumnWidth = 26
    $newSheet.Columns.Item(2).ColumnWidth = 46
    $newSheet.Columns.Item(3).ColumnWidth = 30
    $newSheet.Columns.Item(4).ColumnWidth = 46
    $newSheet.Columns.Item(5).ColumnWidth = 20
    $newSheet.Columns.Item(6).ColumnWidth = 46
    $newSheet.Columns.Item(7).ColumnWidth = 46
    $newSheet.Columns.Item(8).ColumnWidth = 20
    $newSheet.Columns.Item(9).ColumnWidth = 14
    $newSheet.Columns.Item(10).ColumnWidth = 60
    $newSheet.Rows.Item(1).RowHeight = 30
    $usedRng = $newSheet.UsedRange
    $usedRng.WrapText = $true
    $usedRng.VerticalAlignment = -4160  # xlTop

    $wb.Save()
    $wb.Close($false)
    Write-Output "VALIDATION_INFO_SAVED"
}
finally {
    if ($excel) {
        $excel.Quit()
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
    }
    [System.GC]::Collect(); [System.GC]::WaitForPendingFinalizers()
}
