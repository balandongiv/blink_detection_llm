. "C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm\validation_pivot\_tools\pivot_cookbook.ps1"

$wbPath = "C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm\validation_pivot\exp3_strategy_comparison_results.xlsx"
$xlColumnField = 2
$xlDataField = 4
$xlAverage = -4106

$excel = New-ExcelApp
try {
    $wb = $excel.Workbooks.Open($wbPath)

    # Convert raw_data to a native Excel Table
    $lo = Add-TableFromUsedRange -Workbook $wb -SheetName "raw_data" -TableName "RawData"
    $srcRange = $lo.Range

    # --- Sheet 1: table1_macro_f1 --- Rows=condition (restricted to 3), Columns=dataset (cao2018, raja), Values=Average of f1
    $pt1 = Add-ComparisonPivot -Workbook $wb -SourceRange $srcRange `
        -NewSheetName "table1_macro_f1" -PivotName "PT_Table1" `
        -RowFieldName "condition" -RowItemsToShow @("Proposed-Med","BLINKER-concat","MNE-annot") `
        -ColumnFieldName "dataset" -ColumnItemsToShow @("cao2018","raja") `
        -SinglePageFilters @{} `
        -ValueFieldName "f1" -ValueCaption "Average of f1"

    Write-Output "=== table1_macro_f1 ==="
    Dump-SheetValues -Worksheet $wb.Worksheets.Item("table1_macro_f1")

    # --- Sheet 2: fig8_pr_means --- Rows=condition (all 4, but we'll show only the 3 real conditions), Columns=dataset, Values = Average of precision AND Average of recall
    $newSheet2 = $wb.Worksheets.Add()
    $newSheet2.Name = "fig8_pr_means"
    $pc2 = $wb.PivotCaches().Create(1, $srcRange)
    $pt2 = $pc2.CreatePivotTable($newSheet2.Range("A3"), "PT_Fig8")

    $fRow2 = $pt2.PivotFields("condition")
    $fRow2.Orientation = 1  # xlRowField
    $fCol2 = $pt2.PivotFields("dataset")
    $fCol2.Orientation = $xlColumnField

    $fPrec = $pt2.PivotFields("precision")
    $pt2.AddDataField($fPrec, "Average of precision", $xlAverage) | Out-Null
    $fRec = $pt2.PivotFields("recall")
    $pt2.AddDataField($fRec, "Average of recall", $xlAverage) | Out-Null

    $pt2.ManualUpdate = $true
    $fRow2.EnableMultiplePageItems = $true
    for ($i=1; $i -le $fRow2.PivotItems().Count; $i++) {
        $item = $fRow2.PivotItems()[$i]
        $item.Visible = (@("Proposed-Med","BLINKER-concat","MNE-annot") -contains $item.Name)
    }
    $fCol2.EnableMultiplePageItems = $true
    for ($i=1; $i -le $fCol2.PivotItems().Count; $i++) {
        $item = $fCol2.PivotItems()[$i]
        $item.Visible = (@("cao2018","raja") -contains $item.Name)
    }
    $pt2.ManualUpdate = $false
    $pt2.RefreshTable() | Out-Null

    Write-Output "=== fig8_pr_means ==="
    Dump-SheetValues -Worksheet $wb.Worksheets.Item("fig8_pr_means")

    $wb.Save()
    $wb.Close($false)
} finally {
    $excel.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
