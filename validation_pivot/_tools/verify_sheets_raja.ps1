. "C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm\validation_pivot\_tools\pivot_cookbook.ps1"
$wbPath = "C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm\validation_pivot\exp1_channel_selection_raja_results.xlsx"
$excel = $null
try {
    $excel = New-ExcelApp
    $wb = $excel.Workbooks.Open($wbPath, $null, $true)
    Write-Output "SHEETS:"
    foreach ($ws in $wb.Worksheets) { Write-Output (" - " + $ws.Name) }
    $wb.Close($false)
}
finally {
    if ($excel) {
        $excel.Quit()
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
    }
    [System.GC]::Collect(); [System.GC]::WaitForPendingFinalizers()
}
