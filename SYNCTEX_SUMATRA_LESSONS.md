# SyncTeX, SumatraPDF, and IntelliJ IDEA Lessons Learned

## Context

This note documents the debugging path for the SumatraPDF message:

> No synchronization info at this position

The manuscript is built from `writing/main.tex` and opened as `writing/main.pdf` in SumatraPDF. IntelliJ IDEA is used as the editor.

## What Happened

The visible symptom was a SumatraPDF synchronization failure even after the LaTeX document compiled successfully. The important finding was that a successful PDF build does not automatically mean source synchronization is usable.

For synchronization to work, all of these must be true:

1. The LaTeX engine must generate SyncTeX data.
2. The SyncTeX file must sit next to the exact PDF opened in SumatraPDF.
3. SumatraPDF must open the current PDF, not an older copy from another folder.
4. The editor inverse-search command must point to the correct IntelliJ executable.
5. The clicked PDF location must be mappable text, not blank space, margin, some figure areas, or some bibliography/layout artifacts.

## Fix Applied

The project now has a local `writing/.latexmkrc` that forces SyncTeX:

```perl
$synctex = -1;
$pdflatex = 'pdflatex -synctex=-1 -interaction=nonstopmode -halt-on-error %O %S';
$pdf_mode = 1;
$interaction = 'nonstopmode';
$halt_on_error = 1;
```

The `-synctex=-1` setting writes an uncompressed `main.synctex` file. This is easier to inspect and avoids compatibility issues with tools that handle compressed `main.synctex.gz` poorly.

`writing/main.tex` also carries editor-facing magic comments:

```tex
%! TeX program = pdflatex
%! TeX options = -synctex=-1 -interaction=nonstopmode -halt-on-error
```

## Correct Build Command

Run builds from the `writing/` directory:

```powershell
cd C:\Users\balan\IdeaProjects\blink_detection_llm\writing
latexmk -g -pdf main.tex
```

The repo also provides a stable PowerShell entry point that rebuilds, validates SyncTeX, and optionally opens SumatraPDF through forward search:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_manuscript_synctex.ps1 -OpenPdf
```

Expected build evidence:

```text
Output written on main.pdf
SyncTeX written on main.synctex
```

After the build, these two files should have matching timestamps:

```text
writing/main.pdf
writing/main.synctex
```

## Diagnostic Checklist

Use this sequence before changing LaTeX source files.

1. Check that there is only one active PDF:

```powershell
Get-ChildItem -Path C:\Users\balan\IdeaProjects\blink_detection_llm -Filter main.pdf -Recurse -Force |
  Select-Object FullName,LastWriteTime,Length
```

2. Check that the SyncTeX file exists next to the PDF:

```powershell
Get-Item C:\Users\balan\IdeaProjects\blink_detection_llm\writing\main.pdf,
         C:\Users\balan\IdeaProjects\blink_detection_llm\writing\main.synctex |
  Select-Object FullName,LastWriteTime,Length
```

3. Verify reverse search from PDF to source:

```powershell
synctex edit -o 3:150:150:C:/Users/balan/IdeaProjects/blink_detection_llm/writing/main.pdf
```

This should print an `Input:` path and `Line:` number.

4. Verify forward search from source to PDF:

```powershell
synctex view -i 1:1:C:/Users/balan/IdeaProjects/blink_detection_llm/writing/b_intro/p001/paragraph.tex `
  -o C:/Users/balan/IdeaProjects/blink_detection_llm/writing/main.pdf
```

This should print one or more `Page:`, `x:`, and `y:` results.

5. Confirm SumatraPDF is opening the intended PDF:

```powershell
Get-CimInstance Win32_Process -Filter "Name='SumatraPDF.exe'" |
  Select-Object ProcessId,CommandLine
```

The command line should contain:

```text
C:\Users\balan\IdeaProjects\blink_detection_llm\writing\main.pdf
```

6. Confirm SumatraPDF inverse search is configured:

```powershell
rg -n "EnableTeXEnhancements|InverseSearchCmdLine" "$env:LOCALAPPDATA\SumatraPDF\SumatraPDF-settings.txt"
```

Expected shape:

```text
EnableTeXEnhancements = true
InverseSearchCmdLine = "C:\Program Files\JetBrains\IntelliJ IDEA 2026.1\bin\idea64.exe" --line %l "%f"
```

## SumatraPDF Restart Command

If SumatraPDF still shows stale behavior, restart it and reopen the current PDF through forward search:

```powershell
$sumatra = "$env:LOCALAPPDATA\SumatraPDF\SumatraPDF.exe"
Get-Process SumatraPDF -ErrorAction SilentlyContinue | Stop-Process
Start-Sleep -Milliseconds 500
Start-Process -FilePath $sumatra -ArgumentList @(
  '-reuse-instance',
  '-forward-search',
  'C:\Users\balan\IdeaProjects\blink_detection_llm\writing\b_intro\p001\paragraph.tex',
  '1',
  'C:\Users\balan\IdeaProjects\blink_detection_llm\writing\main.pdf'
)
```

## Prevention Rules

For humans:

- Always compile from `writing/`, not the repository root, unless the output directory is deliberately configured.
- Prefer `scripts\build_manuscript_synctex.ps1 -OpenPdf` when working through IntelliJ/SumatraPDF.
- If IntelliJ runs `pdflatex` directly, make sure its LaTeX run configuration compiler options include `-synctex=-1 -interaction=nonstopmode -halt-on-error`; otherwise it can bypass `writing\.latexmkrc`.
- For the green play button in IntelliJ IDEA with TeXiFy, check `Run > Edit Configurations > LaTeX > main > Compiler arguments`. It must contain:

```text
-synctex=-1 -interaction=nonstopmode -halt-on-error
```

- In the same run configuration, disable focus stealing if available. In `.idea/workspace.xml`, the LaTeX `main` and `paragraph` configurations should have:

```xml
<require-focus>false</require-focus>
```

- If every edit triggers a compile and moves the cursor or PDF view, disable TeXiFy automatic compile/preview-on-save in IntelliJ settings and compile manually with the green button or the script.
- Keep `main.pdf` and `main.synctex` in the same directory.
- In SumatraPDF, test inverse search by double-clicking normal paragraph text. Do not test on margins, blank space, figures, or bibliography whitespace.
- If IntelliJ or SumatraPDF was open before a build change, restart SumatraPDF once after regenerating SyncTeX.

For agents:

- Do not assume SyncTeX is working just because `main.pdf` exists.
- Check `main.log` to see whether the build was run by `latexmk` or direct `pdflatex`; direct IntelliJ builds may ignore `.latexmkrc`.
- Verify with the `synctex` CLI before editing unrelated LaTeX content.
- Prefer absolute paths in `synctex view` and SumatraPDF forward-search commands.
- Check for duplicate PDFs before diagnosing package or source problems.
- Treat viewer-state problems separately from LaTeX build problems.
- Do not delete or regenerate user files outside the build target unless explicitly requested.

## Key Lesson

The correct mental model is:

```text
LaTeX source -> PDF + SyncTeX map -> viewer opens exact PDF -> viewer/editor command maps positions
```

If any link in that chain points to a different file, stale file, unmappable PDF location, or missing command, SumatraPDF can report missing synchronization even when the LaTeX document itself is valid.
