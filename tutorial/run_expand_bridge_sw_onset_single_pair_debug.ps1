param(
    [string]$Subject = "S1",
    [string]$Segment = "S01_20170519_043933",
    [string]$Strategy = "expand_bridge_sw_onset_soft_gate",
    [double]$TargetF1 = 0.90,
    [int]$TopChannels = 4,
    [string]$LogLevel = "INFO"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $PSScriptRoot "28_expand_bridge_sw_onset_single_pair_debug.py"
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$launcherLogDir = Join-Path $repoRoot "experiment_output\single_pair_sw_onset_debug\$Segment\$stamp"
New-Item -ItemType Directory -Force -Path $launcherLogDir | Out-Null
$transcriptPath = Join-Path $launcherLogDir "powershell_transcript.log"

Set-Location $repoRoot
Start-Transcript -Path $transcriptPath -Force | Out-Null

try {
    Write-Host ("[{0}] Running single-pair top-10 rerun + top-3 analysis" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
    Write-Host "Repo root      : $repoRoot"
    Write-Host "Python script  : $scriptPath"
    Write-Host "Subject/Segment: $Subject / $Segment"
    Write-Host "Preferred follow-up strategy: $Strategy"
    Write-Host "Target F1      : $TargetF1"
    Write-Host "Top channels   : $TopChannels"
    Write-Host "Transcript     : $transcriptPath"
    Write-Host ""

    & python $scriptPath `
        --subject $Subject `
        --segment $Segment `
        --strategy $Strategy `
        --target-f1 $TargetF1 `
        --top-channels $TopChannels `
        --output-stamp $stamp `
        --log-level $LogLevel

    if ($LASTEXITCODE -ne 0) {
        throw "Python script exited with code $LASTEXITCODE"
    }
}
finally {
    Stop-Transcript | Out-Null
}
