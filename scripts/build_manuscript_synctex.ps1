param(
    [string]$ManuscriptDir = (Join-Path $PSScriptRoot "..\writing"),
    [switch]$OpenPdf
)

$ErrorActionPreference = "Stop"

$resolvedManuscriptDir = (Resolve-Path -LiteralPath $ManuscriptDir).Path
$mainTex = Join-Path $resolvedManuscriptDir "main.tex"
$mainPdf = Join-Path $resolvedManuscriptDir "main.pdf"
$sumatra = Join-Path $env:LOCALAPPDATA "SumatraPDF\SumatraPDF.exe"
$forwardSearchFile = Join-Path $resolvedManuscriptDir "b_intro\p001\paragraph.tex"

if (-not (Test-Path -LiteralPath $mainTex)) {
    throw "Cannot find manuscript source: $mainTex"
}

Push-Location $resolvedManuscriptDir
try {
    latexmk -g -pdf main.tex

    $syncTex = Join-Path $resolvedManuscriptDir "main.synctex"
    if (-not (Test-Path -LiteralPath $syncTex)) {
        throw "Build completed, but main.synctex was not generated. Check writing\.latexmkrc."
    }

    synctex edit -o "3:150:150:$($mainPdf.Replace('\', '/'))" | Out-Host

    if ($OpenPdf) {
        if (-not (Test-Path -LiteralPath $sumatra)) {
            throw "Cannot find SumatraPDF executable: $sumatra"
        }

        Start-Process -FilePath $sumatra -ArgumentList @(
            "-reuse-instance",
            "-forward-search",
            $forwardSearchFile,
            "1",
            $mainPdf
        )
    }
}
finally {
    Pop-Location
}
