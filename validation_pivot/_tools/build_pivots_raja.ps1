. "C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm\validation_pivot\_tools\pivot_cookbook.ps1"

$wbPath = "C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm\validation_pivot\exp1_channel_selection_raja_results.xlsx"

$curated24 = @("Fp1","AF3","F3","AF4","Fp2","F4","FC1","C3","FC5","C4","FC2","FC6","CP1","CP5","CP2","CP6","P7","P3","PO3","O1","PO4","P4","P8","E83")
$only24 = $curated24 | ForEach-Object { ($_.ToLower() + "_only") }

$excel = $null
try {
    $excel = New-ExcelApp
    $wb = $excel.Workbooks.Open($wbPath)

    Add-TableFromUsedRange -Workbook $wb -SheetName "raw_data" -TableName "raw_data_tbl" | Out-Null
    $srcRange = $wb.Worksheets.Item("raw_data").UsedRange

    # Figure 3: per-electrode F1 within each region's own subset rerun
    Add-AveragePivot -Workbook $wb -SourceRange $srcRange `
        -NewSheetName "fig3_per_electrode_subset" -PivotName "PT_Fig3" `
        -RowFieldName "channel_1020" -RowItemsToShow $curated24 `
        -SinglePageFilters @{ center_method = "median" } `
        -MultiPageFilters @{ selection = @("frontal","central","parietal","occipital") } `
        -ValueFieldName "f1" -ValueCaption "Average of f1"

    # Figure 4: subset vs full montage comparison
    Add-ComparisonPivot -Workbook $wb -SourceRange $srcRange `
        -NewSheetName "fig4_subset_vs_montage" -PivotName "PT_Fig4" `
        -RowFieldName "channel_1020" -RowItemsToShow $curated24 `
        -ColumnFieldName "selection" -ColumnItemsToShow @("all_channel","frontal","central","parietal","occipital") `
        -SinglePageFilters @{ center_method = "median" } `
        -ValueFieldName "f1" -ValueCaption "Average of f1"

    # Figure 5: single-channel operation
    Add-AveragePivot -Workbook $wb -SourceRange $srcRange `
        -NewSheetName "fig5_single_channel" -PivotName "PT_Fig5" `
        -RowFieldName "channel_1020" -RowItemsToShow $curated24 `
        -SinglePageFilters @{ center_method = "median" } `
        -MultiPageFilters @{ selection = $only24 } `
        -ValueFieldName "f1" -ValueCaption "Average of f1"

    # Figure 6: single-channel vs full montage comparison
    $fig6Cols = @("all_channel") + $only24
    Add-ComparisonPivot -Workbook $wb -SourceRange $srcRange `
        -NewSheetName "fig6_single_channel_stats" -PivotName "PT_Fig6" `
        -RowFieldName "channel_1020" -RowItemsToShow $curated24 `
        -ColumnFieldName "selection" -ColumnItemsToShow $fig6Cols `
        -SinglePageFilters @{ center_method = "median" } `
        -ValueFieldName "f1" -ValueCaption "Average of f1"

    $wb.Save()
    $wb.Close($false)
    Write-Output "DONE"
}
finally {
    if ($excel) {
        $excel.Quit()
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
    }
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
}
