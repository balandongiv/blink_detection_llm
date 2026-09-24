# Builds the Figure 7 (Experiment 2: Stability Across Epoch Durations) comparison
# pivots for both datasets, using the tested Add-ComparisonPivot pattern from
# pivot_cookbook.ps1. Rows = epoch_duration_s (7 items), Columns = channel
# restricted to {Fp1,Fp2} equivalents, Filters = selection=all_channel,
# center_method=median (confirmed via pandas cross-check against manuscript
# 30s reference values: median matched 79.68/78.45 (Cao2018) and 86.32/86.82
# (Internal) exactly; mean did not).

. "$PSScriptRoot\pivot_cookbook.ps1"

$root = (Resolve-Path "$PSScriptRoot\..\..").Path

function Build-Fig7 {
    param(
        [string]$WorkbookPath,
        [string]$RawSheetName,
        [string]$ChannelFieldName,
        [string[]]$ChannelItems
    )
    $excel = New-ExcelApp
    try {
        $wb = $excel.Workbooks.Open($WorkbookPath)
        $ws = $wb.Worksheets.Item($RawSheetName)
        $srcRange = $ws.UsedRange

        Add-ComparisonPivot -Workbook $wb -SourceRange $srcRange `
            -NewSheetName "fig7_epoch_duration" -PivotName "PT_Fig7" `
            -RowFieldName "epoch_duration_s" -RowItemsToShow $null `
            -ColumnFieldName $ChannelFieldName -ColumnItemsToShow $ChannelItems `
            -SinglePageFilters @{ selection = "all_channel"; center_method = "median" } `
            -ValueFieldName "f1" -ValueCaption "Average of f1" | Out-Null

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

Write-Output "Building Cao2018 fig7 pivot..."
Build-Fig7 -WorkbookPath (Join-Path $root "validation_pivot\exp2_epoch_duration_cao2018_results.xlsx") `
    -RawSheetName "raw_data" -ChannelFieldName "channel" -ChannelItems @("FP1","FP2")

Write-Output "Building Internal fig7 pivot..."
Build-Fig7 -WorkbookPath (Join-Path $root "validation_pivot\exp2_epoch_duration_raja_results.xlsx") `
    -RawSheetName "raw_data" -ChannelFieldName "channel_1020" -ChannelItems @("Fp1","Fp2")

Write-Output "Done."
