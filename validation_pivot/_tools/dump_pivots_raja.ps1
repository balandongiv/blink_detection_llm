. "C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm\validation_pivot\_tools\pivot_cookbook.ps1"

$wbPath = "C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm\validation_pivot\exp1_channel_selection_raja_results.xlsx"

$excel = $null
try {
    $excel = New-ExcelApp
    $wb = $excel.Workbooks.Open($wbPath, $null, $true)  # read-only

    foreach ($name in @("fig3_per_electrode_subset","fig4_subset_vs_montage","fig5_single_channel","fig6_single_channel_stats")) {
        Write-Output "===== $name ====="
        Dump-SheetValues -Worksheet $wb.Worksheets.Item($name)
    }

    $wb.Close($false)
}
finally {
    if ($excel) {
        $excel.Quit()
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
    }
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
}
