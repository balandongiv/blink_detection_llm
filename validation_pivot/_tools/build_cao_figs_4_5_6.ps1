. "$PSScriptRoot\pivot_cookbook.ps1"

$wbPath = "C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm\validation_pivot\exp1_channel_selection_cao2018_results.xlsx"

$curated18 = @("C3","C4","CP3","CP4","F3","F4","FC3","FC4","FP1","FP2","FT7","FT8","O1","O2","P3","P4","T5","T6")
$only18 = $curated18 | ForEach-Object { ($_.ToLower() + "_only") }

$excel = New-ExcelApp
try {
    $wb = $excel.Workbooks.Open($wbPath)
    $srcSheet = $wb.Worksheets.Item("exp1_channel_selection_cao2018_")
    $srcRange = $srcSheet.ListObjects("Table1").Range

    # Remove pre-existing sheets if re-running
    foreach ($name in @("fig4_subset_vs_montage","fig5_single_channel","fig6_single_channel_stats")) {
        foreach ($ws in $wb.Worksheets) {
            if ($ws.Name -eq $name) { $ws.Delete() }
        }
    }

    # Figure 4: subset (own-region) vs all_channel, per electrode
    Add-ComparisonPivot -Workbook $wb -SourceRange $srcRange `
        -NewSheetName "fig4_subset_vs_montage" -PivotName "PT_Fig4" `
        -RowFieldName "channel" -RowItemsToShow $curated18 `
        -ColumnFieldName "selection" -ColumnItemsToShow @("all_channel","frontal","central","parietal","occipital") `
        -SinglePageFilters @{ center_method = "median" } `
        -ValueFieldName "f1" -ValueCaption "Average of f1"

    # Figure 5: single-channel ("_only") detector F1
    Add-AveragePivot -Workbook $wb -SourceRange $srcRange `
        -NewSheetName "fig5_single_channel" -PivotName "PT_Fig5" `
        -RowFieldName "channel" -RowItemsToShow $curated18 `
        -SinglePageFilters @{ center_method = "median" } `
        -MultiPageFilters @{ selection = $only18 } `
        -ValueFieldName "f1" -ValueCaption "Average of f1"

    # Figure 6: single-channel ("_only") vs all_channel, per electrode
    $fig6Cols = @("all_channel") + $only18
    Add-ComparisonPivot -Workbook $wb -SourceRange $srcRange `
        -NewSheetName "fig6_single_channel_stats" -PivotName "PT_Fig6" `
        -RowFieldName "channel" -RowItemsToShow $curated18 `
        -ColumnFieldName "selection" -ColumnItemsToShow $fig6Cols `
        -SinglePageFilters @{ center_method = "median" } `
        -ValueFieldName "f1" -ValueCaption "Average of f1"

    $wb.Save()

    Write-Output "=== fig4_subset_vs_montage ==="
    Dump-SheetValues -Worksheet $wb.Worksheets.Item("fig4_subset_vs_montage")
    Write-Output "=== fig5_single_channel ==="
    Dump-SheetValues -Worksheet $wb.Worksheets.Item("fig5_single_channel")
    Write-Output "=== fig6_single_channel_stats ==="
    Dump-SheetValues -Worksheet $wb.Worksheets.Item("fig6_single_channel_stats")

    $wb.Close($false)
}
finally {
    $excel.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
}
