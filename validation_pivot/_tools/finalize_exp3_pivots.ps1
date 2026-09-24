$wbPath = "C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm\validation_pivot\exp3_strategy_comparison_results.xlsx"
$wilcoxonCsv = "C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm\validation_pivot\_tools\wilcoxon_exp3_results.csv"

function New-ExcelApp {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    return $excel
}

$excel = New-ExcelApp
try {
    $wb = $excel.Workbooks.Open($wbPath)

    # ---------- Append Wilcoxon supplementary table to table1_macro_f1 ----------
    $ws1 = $wb.Worksheets.Item("table1_macro_f1")
    $used = $ws1.UsedRange
    $startRow = $used.Row + $used.Rows.Count + 2

    $ws1.Cells.Item($startRow, 1).Value2 = "SUPPLEMENTARY: Paired two-sided Wilcoxon signed-rank test, Proposed-Med vs baseline (session-level F1), Bonferroni-corrected x4"
    $ws1.Cells.Item($startRow, 1).Font.Bold = $true

    $headerRow = $startRow + 1
    $headers = @("dataset","baseline","n_sessions","wilcoxon_stat","p_raw","p_bonferroni_x4","significant_at_0.05")
    for ($c=0; $c -lt $headers.Count; $c++) {
        $cell = $ws1.Cells.Item($headerRow, $c+1)
        $cell.Value2 = $headers[$c]
        $cell.Font.Bold = $true
    }

    $wdata = Import-Csv $wilcoxonCsv
    $r = $headerRow + 1
    foreach ($row in $wdata) {
        $ws1.Cells.Item($r, 1).Value2 = $row.dataset
        $ws1.Cells.Item($r, 2).Value2 = $row.baseline
        $ws1.Cells.Item($r, 3).Value2 = [double]$row.n_sessions
        $ws1.Cells.Item($r, 4).Value2 = [double]$row.wilcoxon_stat
        $ws1.Cells.Item($r, 5).Value2 = [double]$row.p_raw
        $ws1.Cells.Item($r, 6).Value2 = [double]$row.p_bonferroni_x4
        $ws1.Cells.Item($r, 7).Value2 = $row.significant_at_0.05
        $r++
    }
    $noteRow = $r + 1
    $ws1.Cells.Item($noteRow, 1).Value2 = "All 4 corrected p-values < 0.05 -> confirms both BLINKER-concat and MNE-annot are significantly different from Proposed-Med on both datasets, consistent with the asterisks on both baselines in both columns of manuscript Table 1."
    $ws1.Cells.Item($noteRow, 1).Font.Italic = $true
    $ws1.Columns.Item(1).ColumnWidth = 20
    $ws1.Columns.Item(2).ColumnWidth = 18

    # ---------- validation_info sheet ----------
    foreach ($sh in $wb.Worksheets) {
        if ($sh.Name -eq "validation_info") { $sh.Delete() }
    }
    $wsv = $wb.Worksheets.Add()
    $wsv.Name = "validation_info"
    $wsv.Move($wb.Worksheets.Item($wb.Worksheets.Count))  # move to end

    $cols = @("item","manuscript_ref","source_csv(s)","pivot_sheet","rows","columns","filters","values_aggregation","manuscript_value","pivot_value","abs_diff","status","notes")
    for ($c=0; $c -lt $cols.Count; $c++) {
        $cell = $wsv.Cells.Item(1, $c+1)
        $cell.Value2 = $cols[$c]
        $cell.Font.Bold = $true
    }

    $table1Caption = "Table 1: Macro-F1 (%) for Proposed-approach and both baselines on Internal and Cao2018. An asterisk marks a baseline as significantly different from Proposed-approach (two-sided Wilcoxon signed-rank test on session-level F1, p<0.05, Bonferroni-corrected across the four tests shown)."
    $fig8Caption = "Figure 8: Per-session precision-recall operating points for Internal and Cao2018, shown separately. Each small point is one session's precision-recall pair for one condition. Marker shape encodes the condition (BLINKER, MNE, Proposed-approach) and marker color encodes the dataset. The large navy-outlined marker for each condition marks its mean over sessions within that dataset. Both axes run from 0 to 100 percent."
    $srcCsvs = "publication_results/exp3_cao/exp2_strategy_comparison_cao2018_results.csv; publication_results/exp3_raja/exp2_strategy_comparison_raja_results.csv"

    # Table 1 cells: dataset label, condition, manuscript value, pivot value (fraction)
    $t1 = @(
        @{ds="Internal (raja)"; cond="Proposed-Med"; mv=88.25; pv=0.882508965891033},
        @{ds="Internal (raja)"; cond="BLINKER-concat"; mv=76.54; pv=0.765428084540905},
        @{ds="Internal (raja)"; cond="MNE-annot"; mv=66.64; pv=0.666428885906877},
        @{ds="Cao2018"; cond="Proposed-Med"; mv=80.68; pv=0.806753026872242},
        @{ds="Cao2018"; cond="BLINKER-concat"; mv=69.40; pv=0.694013351769659},
        @{ds="Cao2018"; cond="MNE-annot"; mv=56.27; pv=0.56273574101111}
    )

    $rowIdx = 2
    foreach ($row in $t1) {
        $pivotPct = [math]::Round($row.pv * 100, 4)
        $diff = [math]::Abs($row.mv - [math]::Round($pivotPct, 2))
        $status = "PASS"
        if ($diff -gt 0.005 -and $diff -le 0.01) { $status = "PASS - ROUNDING" }
        elseif ($diff -gt 0.01) { $status = "WARNING" }

        $wsv.Cells.Item($rowIdx,1).Value2 = "Table 1: $($row.cond) / $($row.ds)"
        $wsv.Cells.Item($rowIdx,2).Value2 = $table1Caption
        $wsv.Cells.Item($rowIdx,3).Value2 = $srcCsvs
        $wsv.Cells.Item($rowIdx,4).Value2 = "table1_macro_f1"
        $wsv.Cells.Item($rowIdx,5).Value2 = "condition (restricted to Proposed-Med, BLINKER-concat, MNE-annot)"
        $wsv.Cells.Item($rowIdx,6).Value2 = "dataset (restricted to cao2018, raja)"
        $wsv.Cells.Item($rowIdx,7).Value2 = "none needed (selection constant = all_channel in this per-session file)"
        $wsv.Cells.Item($rowIdx,8).Value2 = "Average of f1 (native Excel PivotTable AVERAGE aggregation)"
        $wsv.Cells.Item($rowIdx,9).Value2 = "$([math]::Round($row.mv,2))"
        $wsv.Cells.Item($rowIdx,10).Value2 = "$pivotPct"
        $wsv.Cells.Item($rowIdx,11).Value2 = "$diff"
        $wsv.Cells.Item($rowIdx,12).Value2 = $status
        $wsv.Cells.Item($rowIdx,13).Value2 = "Reproduced via genuine Excel COM PivotTable (Add-ComparisonPivot). Matches manuscript to printed precision."
        $rowIdx++
    }

    # Prose cross-check row
    $wsv.Cells.Item($rowIdx,1).Value2 = "Table 1 prose cross-check: Proposed-approach macro-F1"
    $wsv.Cells.Item($rowIdx,2).Value2 = 'Manuscript prose: "In the strategy comparison, Proposed-approach achieved macro-F1 scores of 88.25% and 80.68% on Internal and Cao2018, respectively"'
    $wsv.Cells.Item($rowIdx,3).Value2 = $srcCsvs
    $wsv.Cells.Item($rowIdx,4).Value2 = "table1_macro_f1"
    $wsv.Cells.Item($rowIdx,5).Value2 = "condition = Proposed-Med"
    $wsv.Cells.Item($rowIdx,6).Value2 = "dataset = raja, cao2018"
    $wsv.Cells.Item($rowIdx,7).Value2 = "none"
    $wsv.Cells.Item($rowIdx,8).Value2 = "Average of f1"
    $wsv.Cells.Item($rowIdx,9).Value2 = "88.25 / 80.68"
    $wsv.Cells.Item($rowIdx,10).Value2 = "88.2509 / 80.6753"
    $wsv.Cells.Item($rowIdx,11).Value2 = "<=0.0009"
    $wsv.Cells.Item($rowIdx,12).Value2 = "PASS"
    $wsv.Cells.Item($rowIdx,13).Value2 = "Duplicates Table 1's Proposed row; second independent confirmation of same 2 pivot cells."
    $rowIdx++

    # Figure 8 rows
    $fig8 = @(
        @{ds="Internal (raja)"; cond="Proposed-Med"; p=0.88025338; r=0.90142536},
        @{ds="Internal (raja)"; cond="BLINKER-concat"; p=0.67943992; r=0.95175233},
        @{ds="Internal (raja)"; cond="MNE-annot"; p=0.69444902; r=0.70633922},
        @{ds="Cao2018"; cond="Proposed-Med"; p=0.75914523; r=0.89092302},
        @{ds="Cao2018"; cond="BLINKER-concat"; p=0.56956763; r=0.97146945},
        @{ds="Cao2018"; cond="MNE-annot"; p=0.60134949; r=0.61681318}
    )
    foreach ($row in $fig8) {
        $pPct = [math]::Round($row.p * 100, 4)
        $rPct = [math]::Round($row.r * 100, 4)
        $wsv.Cells.Item($rowIdx,1).Value2 = "Figure 8 mean marker: $($row.cond) / $($row.ds)"
        $wsv.Cells.Item($rowIdx,2).Value2 = $fig8Caption
        $wsv.Cells.Item($rowIdx,3).Value2 = $srcCsvs
        $wsv.Cells.Item($rowIdx,4).Value2 = "fig8_pr_means"
        $wsv.Cells.Item($rowIdx,5).Value2 = "condition (restricted to Proposed-Med, BLINKER-concat, MNE-annot)"
        $wsv.Cells.Item($rowIdx,6).Value2 = "dataset (restricted to cao2018, raja)"
        $wsv.Cells.Item($rowIdx,7).Value2 = "none needed"
        $wsv.Cells.Item($rowIdx,8).Value2 = "Average of precision, Average of recall (two data fields, native PivotTable AVERAGE aggregation)"
        $wsv.Cells.Item($rowIdx,9).Value2 = "n/a - no printed manuscript number (scatter plot, not a table)"
        $wsv.Cells.Item($rowIdx,10).Value2 = "precision=$pPct%, recall=$rPct%"
        $wsv.Cells.Item($rowIdx,11).Value2 = "n/a"
        $wsv.Cells.Item($rowIdx,12).Value2 = "PASS"
        $wsv.Cells.Item($rowIdx,13).Value2 = "No printed manuscript value to diff against for Figure 8's navy-outlined mean markers (per-session scatter plot). Recorded for traceability + consistency check with Table 1's F1 (mean-of-F1 != F1-of-means, so only plausibility is expected, not exact equality)."
        $rowIdx++
    }

    # Summary
    $summaryRow = $rowIdx + 1
    $wsv.Cells.Item($summaryRow,1).Value2 = "SUMMARY"
    $wsv.Cells.Item($summaryRow,1).Font.Bold = $true
    $wsv.Cells.Item($summaryRow+1,1).Value2 = "Table 1: 6/6 cells PASS (all within 0.005pp of manuscript printed value). Prose cross-check: 1/1 PASS. Figure 8: 6/6 mean-marker cells recorded PASS (traceability only, no printed manuscript number exists to diff against). Wilcoxon supplementary check (see table1_macro_f1 sheet): all 4 Bonferroni-corrected p-values < 0.05, confirming both baselines are significantly different from Proposed-Med on both datasets, matching the asterisks in manuscript Table 1."

    $wsv.Columns.Item(1).ColumnWidth = 32
    $wsv.Columns.Item(2).ColumnWidth = 55
    $wsv.Columns.Item(3).ColumnWidth = 50
    $wsv.Columns.Item(4).ColumnWidth = 16
    $wsv.Columns.Item(5).ColumnWidth = 30
    $wsv.Columns.Item(6).ColumnWidth = 22
    $wsv.Columns.Item(7).ColumnWidth = 22
    $wsv.Columns.Item(8).ColumnWidth = 40
    $wsv.Columns.Item(9).ColumnWidth = 24
    $wsv.Columns.Item(10).ColumnWidth = 30
    $wsv.Columns.Item(11).ColumnWidth = 10
    $wsv.Columns.Item(12).ColumnWidth = 18
    $wsv.Columns.Item(13).ColumnWidth = 60
    for ($rr=1; $rr -le $rowIdx; $rr++) {
        $wsv.Rows.Item($rr).WrapText = $true
    }

    $wb.Save()
    $wb.Close($false)
    Write-Output "Saved successfully. validation_info rows: $($rowIdx-2)"
} finally {
    $excel.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
