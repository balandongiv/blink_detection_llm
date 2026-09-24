. "$PSScriptRoot\pivot_cookbook.ps1"
$wbPath = "C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm\validation_pivot\exp1_channel_selection_cao2018_results.xlsx"
$excel = New-ExcelApp
try {
    $wb = $excel.Workbooks.Open($wbPath, $null, $true)  # read-only
    Write-Output "SHEETS:"
    foreach ($ws in $wb.Worksheets) { Write-Output $ws.Name }
    Write-Output "=== fig6_significance (first 6 rows) ==="
    $ws = $wb.Worksheets.Item("fig6_significance")
    for ($r=1; $r -le 6; $r++) {
        $vals = @()
        for ($c=1; $c -le 8; $c++) { $vals += "$($ws.Cells.Item($r,$c).Value2)" }
        Write-Output ($vals -join " | ")
    }
    Write-Output "=== validation_info (first 3 rows, col A-C) ==="
    $ws = $wb.Worksheets.Item("validation_info")
    for ($r=1; $r -le 3; $r++) {
        $vals = @()
        for ($c=1; $c -le 3; $c++) { $vals += "$($ws.Cells.Item($r,$c).Value2)" }
        Write-Output ($vals -join " || ")
    }
    $wb.Close($false)
}
finally {
    $excel.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
}
