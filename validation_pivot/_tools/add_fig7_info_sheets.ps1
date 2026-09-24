# Adds "fig7_significance" and "validation_info" sheets to the two Figure 7
# workbooks, using data computed in Python (pandas + scipy.stats.wilcoxon) and
# serialized to _fig7_sheets.json. Uses COM (not openpyxl) so the existing
# PivotTable/PivotCache in each workbook is left intact.

. "$PSScriptRoot\pivot_cookbook.ps1"
$root = (Resolve-Path "$PSScriptRoot\..\..").Path

$json = Get-Content "$PSScriptRoot\_fig7_sheets.json" -Raw | ConvertFrom-Json

function Write-Table {
    param($Worksheet, [int]$StartRow, [string[]]$Headers, $Rows)
    for ($c=0; $c -lt $Headers.Count; $c++) {
        $Worksheet.Cells.Item($StartRow, $c+1) = $Headers[$c]
        $Worksheet.Cells.Item($StartRow, $c+1).Font.Bold = $true
    }
    $r = $StartRow + 1
    foreach ($row in $Rows) {
        for ($c=0; $c -lt $row.Count; $c++) {
            $Worksheet.Cells.Item($r, $c+1) = $row[$c]
        }
        $r++
    }
    return $r
}

function Add-Sheets {
    param([string]$WorkbookPath, [string]$DatasetKey, [string]$ChannelFieldName,
          [string]$SourceCsv, [string]$CenterMethodNote)

    $excel = New-ExcelApp
    try {
        $wb = $excel.Workbooks.Open($WorkbookPath)

        # ---- fig7_significance ----
        $wsSig = $wb.Worksheets.Add()
        $wsSig.Name = "fig7_significance"
        $wsSig.Cells.Item(1,1) = "Figure 7 supplementary significance cross-check (Wilcoxon signed-rank, paired by session, vs 30s reference; Bonferroni x6 within electrode)"
        $wsSig.Cells.Item(1,1).Font.Bold = $true
        $headers = @("electrode","epoch_duration_s","our mean f1 (%)","our raw p","our Bonferroni p","our call","manuscript p (Bonf.)","manuscript call","match")
        $rows = @()
        foreach ($row in $json.sig_rows.$DatasetKey) {
            $rows += ,@($row[0], $row[1], $row[2], $row[3], $row[4], $row[5], $row[6], $row[7], $row[8])
        }
        Write-Table -Worksheet $wsSig -StartRow 3 -Headers $headers -Rows $rows | Out-Null
        $wsSig.Columns.Item("A:I").AutoFit() | Out-Null

        # ---- validation_info ----
        $wsInfo = $wb.Worksheets.Add()
        $wsInfo.Name = "validation_info"
        $r = 1
        $lines = @(
            "VALIDATION INFO - Figure 7: Stability Across Epoch Durations ($DatasetKey)",
            "Manuscript caption: Macro-averaged F1 of Proposed-approach across epoch durations, on the full 32-channel montage, for Fp1 and Fp2 (Experiment 1's two consistently best-performing electrodes) reported separately: Internal (top row) and Cao2018 (bottom row). Durations of 10, 20, 30 (reference), 40, 50, 60 and 120 seconds were tested; asterisk marks durations differing significantly from the 30s reference after Bonferroni correction.",
            "Source CSV: $SourceCsv (raw, session-level rows; parsed with pandas.read_csv, not naive text splitting, because flagged_valid_epoch_indices contains embedded commas inside quotes).",
            "Pivot spec: Rows = epoch_duration_s (7 items: 10,20,30,40,50,60,120). Columns = $ChannelFieldName restricted to {Fp1-equivalent, Fp2-equivalent}. Filters (single page item each) = selection=all_channel, center_method=median. Values = Average of f1 (xlAverage), Excel native PivotTable via COM (Add-ComparisonPivot in pivot_cookbook.ps1).",
            "center_method determination: computed the 30s/all_channel average f1 for Fp1 and Fp2 under BOTH center_method=mean and center_method=median in pandas before building any pivot. $CenterMethodNote",
            "Tolerance: manuscript values are printed to 2 decimal places (%). A pivot value is PASS if it rounds to the same 2-decimal-place percentage as the manuscript value (|diff| <= 0.01pp); PASS - ROUNDING if 0.01-0.05pp off; WARNING if 0.05-0.1pp off; FAIL if >0.1pp off. Rows where the manuscript's prose gives no explicit numeric F1 for that duration (only the Fig. 7 plot shows it, and only a subset of durations are quoted with numbers in text) are marked PASS (qualitative) and their non-/significance claim is instead checked against our own Wilcoxon computation on the fig7_significance sheet.",
            "Comparisons below: 14 rows (7 durations x 2 electrodes)."
        )
        foreach ($line in $lines) {
            $wsInfo.Cells.Item($r,1) = $line
            $wsInfo.Range($wsInfo.Cells.Item($r,1), $wsInfo.Cells.Item($r,6)).Merge() | Out-Null
            $wsInfo.Cells.Item($r,1).WrapText = $true
            $r += 1
        }
        $r += 1
        $headers2 = @("electrode","epoch_duration_s","pivot f1 (%)","manuscript f1 (%)","diff (pp)","status")
        $rows2 = @()
        foreach ($row in $json.info_rows.$DatasetKey) {
            $rows2 += ,@($row[0], $row[1], $row[2], $row[3], $row[4], $row[5])
        }
        Write-Table -Worksheet $wsInfo -StartRow $r -Headers $headers2 -Rows $rows2 | Out-Null
        $wsInfo.Columns.Item("A:F").AutoFit() | Out-Null
        $wsInfo.Columns.Item("A:A").ColumnWidth = 100

        $wb.Save()
        $wb.Close($false)
    }
    finally {
        $excel.Quit()
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
        [GC]::Collect()
        [GC]::WaitForPendingFinalizers()
    }
}

$meanMedianNoteCao = "Cao2018: mean gave Fp1=79.3868%/Fp2=78.0148%; median gave Fp1=79.6794%/Fp2=78.4498%. Manuscript states 79.68%/78.45% -> median matches (mean is off by ~0.3-0.4pp). center_method=median confirmed."
$meanMedianNoteInt = "Internal: mean gave Fp1=85.5550%/Fp2=85.9891%; median gave Fp1=86.3199%/Fp2=86.8215%. Manuscript states 86.32%/86.82% -> median matches (mean is off by ~0.8-0.9pp). center_method=median confirmed."

Write-Output "Adding info/significance sheets to Cao2018 workbook..."
Add-Sheets -WorkbookPath (Join-Path $root "validation_pivot\exp2_epoch_duration_cao2018_results.xlsx") `
    -DatasetKey "Cao2018" -ChannelFieldName "channel" `
    -SourceCsv "publication_results\exp2_cao\exp3_epoch_duration_cao2018_results.csv" `
    -CenterMethodNote $meanMedianNoteCao

Write-Output "Adding info/significance sheets to Internal workbook..."
Add-Sheets -WorkbookPath (Join-Path $root "validation_pivot\exp2_epoch_duration_raja_results.xlsx") `
    -DatasetKey "Internal" -ChannelFieldName "channel_1020 (mapped from EGI HydroCel code via egi_to_1020_map_internal.csv; Fp1=E22, Fp2=E9)" `
    -SourceCsv "publication_results\exp2_raja\exp3_epoch_duration_raja_results.csv" `
    -CenterMethodNote $meanMedianNoteInt

Write-Output "Done."
