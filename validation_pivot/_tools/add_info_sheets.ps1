$wbPath = "C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm\validation_pivot\exp1_channel_selection_cao2018_results.xlsx"

function New-ExcelApp {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    return $excel
}

function Write-CsvToSheet {
    param($Workbook, [string]$CsvPath, [string]$SheetName)
    foreach ($ws in $Workbook.Worksheets) {
        if ($ws.Name -eq $SheetName) { $ws.Delete() }
    }
    $newSheet = $Workbook.Worksheets.Add()
    $newSheet.Name = $SheetName
    $lines = Get-Content -Path $CsvPath
    $nRows = $lines.Count
    $nCols = ($lines[0] -split ",").Count

    # Build a 2D System.Object[,] array and assign the whole block in one COM call --
    # writing cell-by-cell with Value2 mixing strings/doubles in the same column across
    # rows intermittently throws "Unable to cast object of type 'System.Double' to type
    # 'System.String'" (an Excel COM per-cell format-caching quirk). A single bulk
    # Range.Value2 = array assignment avoids it entirely.
    $arr = New-Object 'object[,]' $nRows, $nCols
    for ($ri = 0; $ri -lt $nRows; $ri++) {
        $cells = $lines[$ri] -split ","
        for ($ci = 0; $ci -lt $nCols; $ci++) {
            $v = $cells[$ci]
            if ($v -eq "True") {
                $arr[$ri, $ci] = "TRUE"
            } elseif ($v -eq "False") {
                $arr[$ri, $ci] = "FALSE"
            } else {
                $parsed = 0.0
                $ok = [double]::TryParse([string]$v, [System.Globalization.NumberStyles]::Any, [System.Globalization.CultureInfo]::InvariantCulture, [ref]$parsed)
                if ($ok) {
                    $arr[$ri, $ci] = [double]$parsed
                } else {
                    $arr[$ri, $ci] = [string]$v
                }
            }
        }
    }
    $topLeft = $newSheet.Cells.Item(1, 1)
    $bottomRight = $newSheet.Cells.Item($nRows, $nCols)
    $newSheet.Range($topLeft, $bottomRight).Value2 = $arr

    $newSheet.Rows.Item(1).Font.Bold = $true
    $newSheet.Columns.AutoFit() | Out-Null
    return $newSheet
}

$excel = New-ExcelApp
try {
    $wb = $excel.Workbooks.Open($wbPath)

    Write-CsvToSheet -Workbook $wb -CsvPath "C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm\validation_pivot\_tools\fig4_significance.csv" -SheetName "fig4_significance"
    Write-CsvToSheet -Workbook $wb -CsvPath "C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm\validation_pivot\_tools\fig6_significance.csv" -SheetName "fig6_significance"

    # --- validation_info sheet ---
    foreach ($ws in $wb.Worksheets) {
        if ($ws.Name -eq "validation_info") { $ws.Delete() }
    }
    $info = $wb.Worksheets.Add()
    $info.Name = "validation_info"
    $info.Move($wb.Worksheets.Item(1))  # move to front

    $headers = @("Figure","Manuscript Caption (abridged)","Source","Rows / Columns / Filters / Values","Aggregation","Manuscript Value(s)","Pivot Value(s)","Status","Notes")
    for ($c=0; $c -lt $headers.Count; $c++) { $info.Cells.Item(1, $c+1).Value2 = $headers[$c] }
    $info.Rows.Item(1).Font.Bold = $true

    $rows = @(
      @("Fig 3","Per-electrode F1 for every electrode inside its own curated anatomical region (own-region rerun). Sheet: per_electrode_subset (pre-existing, not rebuilt this pass).",
        "publication_results/exp1_channel_cao/sessions/*.csv (58 sessions) concatenated -> raw_data sheet",
        "Rows=channel (18 curated); Filters=selection (multi: frontal,central,parietal,occipital) + center_method=median; Values=Average of f1",
        "Average (mean of per-session F1)",
        "FP1 ~= 0.788 (cross-check vs pre-aggregated publication_results/exp1_channel_cao/exp1_channel_selection_cao2018_results.csv)",
        "FP1 = 0.788028",
        "PASS",
        "Exact match to the pre-aggregated CSV export (0.788027662 vs 0.788027662). Sheet was already present; spot-checked only, not rebuilt."),
      @("Fig 4","Per-electrode Proposed-approach F1: own-region subset (narrow bar) vs full-montage all_channel (wide bar).",
        "raw_data sheet (Table1, 12528 rows)",
        "Rows=channel (18 curated); Columns=selection (all_channel, frontal, central, parietal, occipital); Filters=center_method=median; Values=Average of f1",
        "Average (mean of per-session F1)",
        "Subset bar should equal Fig 3 value for same electrode (internal consistency check)",
        "All 18 subset-column values matched Fig 3 values to full precision (e.g. FP1 subset=0.788028 vs Fig3=0.788028; C3 subset=0.276665 vs Fig3=0.276665)",
        "PASS",
        "IMPORTANT DATA-QUALITY NOTE: the region membership given in the task brief (parietal={CP3,CP4,P3,P4}, occipital={T5,T6,O1,O2}) does NOT match the actual 'selection' column in the data. Verified directly: parietal selection only contains CP3,CP4 (2 electrodes); occipital selection contains O1,O2,P3,P4,T5,T6 (6 electrodes). frontal={FP1,FP2,F3,F4} and central={C3,C4,FC3,FC4,FT7,FT8} DID match as stated. This did not affect pivot correctness since the pivot reads the real 'selection' field directly rather than a hardcoded map, and Fig3<->Fig4 subset values match exactly regardless."),
      @("Fig 5","Detection F1 of every curated electrode operating as its own single-channel ('_only') detector.",
        "raw_data sheet (Table1, 12528 rows)",
        "Rows=channel (18 curated); Filters=selection (multi: 18 '{electrode}_only' values) + center_method=median; Values=Average of f1",
        "Average (mean of per-session F1)",
        "FC4=36.72%, FT8=34.99%, FT7=34.22%, C3=25.43%, C4=25.10%, O1=2.28% (printed); Fp1~=77.7%, Fp2~=75.6%, F3~=49.3%, F4~=49.0% (bar-chart visual estimates)",
        "FC4=36.72%, FT8=34.99%, FT7=34.22%, C3=25.43%, C4=25.10%, O1=2.28%; FP1=77.65%, FP2=75.59%, F3=49.30%, F4=49.03%",
        "PASS",
        "Printed-digit values matched to the displayed 2 decimals exactly. Bar-chart visual-estimate values all within 0.1pp of the manuscript's approximate readings (well inside the +/-0.2pp tolerance)."),
      @("Fig 6","Per-electrode F1: own single-channel '_only' detector (narrow bar) vs full-montage all_channel (wide bar), plus Wilcoxon significance asterisks.",
        "raw_data sheet (Table1, 12528 rows)",
        "Rows=channel (18 curated); Columns=selection (all_channel + 18 '_only' values); Filters=center_method=median; Values=Average of f1",
        "Average (mean of per-session F1); significance via supplementary Python Wilcoxon (see below)",
        "16 of 18 electrodes significant after Bonferroni (x18) correction; only Fp1,Fp2 not significant (adj. p=1.000 both); F3 delta=-10.21pp, F4 delta=-8.96pp (largest reductions)",
        "16 of 18 significant; Fp1 adj.p=1.000, Fp2 adj.p=1.000 (both not significant); F3 delta=-10.2122pp, F4 delta=-8.9623pp",
        "PASS",
        "Descriptive pivot values match Fig3/Fig5 exactly (as expected: all_channel col = Fig4's all_channel col; _only col = Fig5 values). SUPPLEMENTARY STATS (computed via Python/scipy after the independent PivotTable descriptive validation, only to check the significance markers, per the task's explicit allowance for discrepancy/stats investigation): two-tailed Wilcoxon signed-rank on session-paired F1 (own '_only' selection vs all_channel selection, n=58 sessions per electrode), Bonferroni-corrected x18 within dataset. Full per-electrode table on sheet 'fig6_significance'. Result: exact match to manuscript's significant/non-significant calls and to both stated delta magnitudes (-10.21, -8.96 pp).")
    )

    $r = 2
    foreach ($row in $rows) {
        for ($c = 0; $c -lt $row.Count; $c++) {
            $info.Cells.Item($r, $c+1).Value2 = $row[$c]
        }
        $info.Rows.Item($r).WrapText = $true
        $r++
    }

    $info.Cells.Item($r+1, 1).Value2 = "Tolerance policy: manuscript values printed to 2 decimals -> +/-0.005 (0.5pp) absolute tolerance. Bar-chart-only (no printed digit) values -> +/-0.2pp tolerance, WARNING if ambiguous to read."
    $info.Cells.Item($r+2, 1).Value2 = "Fig4/Fig6 significance sheets: fig4_significance, fig6_significance (own-region/own-channel vs all_channel, paired Wilcoxon, Bonferroni x18)."
    $info.Cells.Item($r+3, 1).Value2 = "See sheet fig6_significance for the electrode-by-electrode stats table referenced in the Fig 6 row above."

    $info.Columns.Item(1).ColumnWidth = 8
    $info.Columns.Item(2).ColumnWidth = 40
    $info.Columns.Item(3).ColumnWidth = 30
    $info.Columns.Item(4).ColumnWidth = 45
    $info.Columns.Item(5).ColumnWidth = 20
    $info.Columns.Item(6).ColumnWidth = 40
    $info.Columns.Item(7).ColumnWidth = 40
    $info.Columns.Item(8).ColumnWidth = 12
    $info.Columns.Item(9).ColumnWidth = 60

    $wb.Save()
    $wb.Close($false)
}
finally {
    $excel.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
}
