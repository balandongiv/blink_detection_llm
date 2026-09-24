# TESTED, WORKING recipes for building genuine Excel PivotTables via COM automation.
# Verified against exp1_channel_selection_cao2018_results.xlsx on 2026-09-15: the
# "Average of f1 by channel, filtered by selection(multiple)+center_method" pattern
# below reproduced the manuscript's Figure 5 (Cao2018) single-channel values to
# within 0.05 percentage points (O1: pivot 2.275% vs manuscript-stated 2.28%).
#
# Requires Excel installed (COM: Excel.Application). Run via:
#   powershell -NoProfile -ExecutionPolicy Bypass -File <script>.ps1
#
# IMPORTANT COM GOTCHAS (hit and solved during prototyping):
#  - Do NOT call .Item($i) on RowFields/ColumnFields/PageFields/DataFields/PivotItems
#    collections in PowerShell -- it throws "does not contain a method named Item".
#    Use the indexer instead: $collection[$i]  (or $collection.Item($i) works fine on
#    PivotFields() the top-level field list, oddly -- but NOT on the sub-collections).
#  - PivotFields("name") on the *table* (not a sub-collection) DOES work with string
#    names, e.g. $pt.PivotFields("channel").
#  - To restrict a Page(Filter) field to multiple specific items: set
#    $field.EnableMultiplePageItems = $true, then loop PivotItems and set
#    .Visible = $true/$false explicitly for every item (default is all visible).
#  - To restrict to exactly ONE item, EnableMultiplePageItems can stay false and you
#    can just set $field.CurrentPage = "itemname".
#  - Wrap field additions in $pt.ManualUpdate = $true ... $false; $pt.RefreshTable()
#    to avoid slow recalculation while toggling many PivotItems.
#  - Orientation constants: xlRowField=1, xlColumnField=2, xlPageField=3, xlDataField=4.
#  - Function constants: xlAverage=-4106, xlSum=-4157, xlCount=-4112.
#  - Always $excel.DisplayAlerts = $false and always Quit() + ReleaseComObject in a
#    finally block -- an orphaned EXCEL.EXE process will lock the file.

$xlRowField    = 1
$xlColumnField = 2
$xlPageField   = 3
$xlDataField   = 4
$xlAverage     = -4106
$xlDatabase    = 1

function New-ExcelApp {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    return $excel
}

# Writes a CSV (or list of CSVs to be concatenated) into a sheet named $SheetName as
# a native Excel Table (ListObject) so it can be used as a PivotCache source.
# Fastest approach: use Python/pandas to pre-concatenate + pre-write the raw_data
# sheet (openpyxl), THEN open that .xlsx with this COM script only to add pivots.
# That avoids slow cell-by-cell COM writes for thousands of rows.

function Add-TableFromUsedRange {
    param($Workbook, [string]$SheetName, [string]$TableName)
    $ws = $Workbook.Worksheets.Item($SheetName)
    $rng = $ws.UsedRange
    $lo = $ws.ListObjects.Add(1, $rng, $null, 1)  # xlSrcRange=1, xlYes=1 (has headers)
    $lo.Name = $TableName
    return $lo
}

# Pattern A: single "Average of X" measure, Rows = one field, Filters = one or more
# fields each restricted to a specific set of items (or a single CurrentPage value).
# This is the Figure-3 / Figure-5 style pivot (bar chart of one value per electrode).
function Add-AveragePivot {
    param(
        $Workbook, $SourceRange, [string]$NewSheetName, [string]$PivotName,
        [string]$RowFieldName,
        [string[]]$RowItemsToShow,          # $null = show all
        [hashtable]$SinglePageFilters,      # @{ center_method = "median" }
        [hashtable]$MultiPageFilters,       # @{ selection = @("frontal","central",...) }
        [string]$ValueFieldName,            # e.g. "f1"
        [string]$ValueCaption               # e.g. "Average of f1"
    )
    $newSheet = $Workbook.Worksheets.Add()
    $newSheet.Name = $NewSheetName
    $pc = $Workbook.PivotCaches().Create($xlDatabase, $SourceRange)
    $pt = $pc.CreatePivotTable($newSheet.Range("A3"), $PivotName)

    $fRow = $pt.PivotFields($RowFieldName)
    $fRow.Orientation = $xlRowField

    foreach ($k in $SinglePageFilters.Keys) {
        $f = $pt.PivotFields($k)
        $f.Orientation = $xlPageField
    }
    foreach ($k in $MultiPageFilters.Keys) {
        $f = $pt.PivotFields($k)
        $f.Orientation = $xlPageField
    }

    $fVal = $pt.PivotFields($ValueFieldName)
    $pt.AddDataField($fVal, $ValueCaption, $xlAverage) | Out-Null

    $pt.ManualUpdate = $true

    if ($RowItemsToShow) {
        $fRow.EnableMultiplePageItems = $true
        for ($i=1; $i -le $fRow.PivotItems().Count; $i++) {
            $item = $fRow.PivotItems()[$i]
            $item.Visible = ($RowItemsToShow -contains $item.Name)
        }
    }
    foreach ($k in $SinglePageFilters.Keys) {
        $pt.PivotFields($k).CurrentPage = $SinglePageFilters[$k]
    }
    foreach ($k in $MultiPageFilters.Keys) {
        $f = $pt.PivotFields($k)
        $f.EnableMultiplePageItems = $true
        $wanted = $MultiPageFilters[$k]
        for ($i=1; $i -le $f.PivotItems().Count; $i++) {
            $item = $f.PivotItems()[$i]
            $item.Visible = ($wanted -contains $item.Name)
        }
    }

    $pt.ManualUpdate = $false
    $pt.RefreshTable() | Out-Null
    return $pt
}

# Pattern B: comparison pivot -- Rows = one field (e.g. channel), Columns = another
# field restricted to exactly the 2 categories being compared (e.g. own-region vs
# all_channel, or {electrode}_only vs all_channel), Filters = remaining constants.
# This is the Figure-4 / Figure-6 style pivot (paired bars per electrode).
function Add-ComparisonPivot {
    param(
        $Workbook, $SourceRange, [string]$NewSheetName, [string]$PivotName,
        [string]$RowFieldName, [string[]]$RowItemsToShow,
        [string]$ColumnFieldName, [string[]]$ColumnItemsToShow,
        [hashtable]$SinglePageFilters,
        [string]$ValueFieldName, [string]$ValueCaption
    )
    $newSheet = $Workbook.Worksheets.Add()
    $newSheet.Name = $NewSheetName
    $pc = $Workbook.PivotCaches().Create($xlDatabase, $SourceRange)
    $pt = $pc.CreatePivotTable($newSheet.Range("A3"), $PivotName)

    $fRow = $pt.PivotFields($RowFieldName)
    $fRow.Orientation = $xlRowField
    $fCol = $pt.PivotFields($ColumnFieldName)
    $fCol.Orientation = $xlColumnField
    foreach ($k in $SinglePageFilters.Keys) {
        $pt.PivotFields($k).Orientation = $xlPageField
    }
    $fVal = $pt.PivotFields($ValueFieldName)
    $pt.AddDataField($fVal, $ValueCaption, $xlAverage) | Out-Null

    $pt.ManualUpdate = $true
    if ($RowItemsToShow) {
        $fRow.EnableMultiplePageItems = $true
        for ($i=1; $i -le $fRow.PivotItems().Count; $i++) {
            $item = $fRow.PivotItems()[$i]
            $item.Visible = ($RowItemsToShow -contains $item.Name)
        }
    }
    if ($ColumnItemsToShow) {
        $fCol.EnableMultiplePageItems = $true
        for ($i=1; $i -le $fCol.PivotItems().Count; $i++) {
            $item = $fCol.PivotItems()[$i]
            $item.Visible = ($ColumnItemsToShow -contains $item.Name)
        }
    }
    foreach ($k in $SinglePageFilters.Keys) {
        $pt.PivotFields($k).CurrentPage = $SinglePageFilters[$k]
    }
    $pt.ManualUpdate = $false
    $pt.RefreshTable() | Out-Null
    return $pt
}

function Dump-SheetValues {
    param($Worksheet)
    $u = $Worksheet.UsedRange
    for ($r=1; $r -le $u.Rows.Count; $r++) {
        $vals = @()
        for ($c=1; $c -le $u.Columns.Count; $c++) {
            $vals += "$($Worksheet.Cells.Item($u.Row+$r-1, $u.Column+$c-1).Value2)"
        }
        Write-Output ($vals -join " | ")
    }
}

# ---------------------------------------------------------------------------
# EXAMPLE USAGE (this is exactly what reproduced Figure 5 / Cao2018 correctly):
#
# $excel = New-ExcelApp
# $wb = $excel.Workbooks.Open("C:\...\exp1_channel_selection_cao2018_results.xlsx")
# $srcRange = $wb.Worksheets.Item("exp1_channel_selection_cao2018_").UsedRange
# $curated18 = @("C3","C4","CP3","CP4","F3","F4","FC3","FC4","FP1","FP2","FT7","FT8","O1","O2","P3","P4","T5","T6")
# $only18 = $curated18 | ForEach-Object { ($_.ToLower() + "_only") }
# Add-AveragePivot -Workbook $wb -SourceRange $srcRange `
#   -NewSheetName "fig5_single_channel" -PivotName "PT_Fig5" `
#   -RowFieldName "channel" -RowItemsToShow $curated18 `
#   -SinglePageFilters @{ center_method = "median" } `
#   -MultiPageFilters @{ selection = $only18 } `
#   -ValueFieldName "f1" -ValueCaption "Average of f1"
# $wb.Save(); $wb.Close($false); $excel.Quit()
# [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
# ---------------------------------------------------------------------------
