

````text
You are given access to a repository containing:

1. A final LaTeX manuscript.
2. A compiled manuscript PDF with the name 'writing/ACCESS_latex_template_20260513/0_original_access.pdf'.
- The pdf can be compiled from the LaTeX source using Tectonic or a similar TeX engine using "writing/ACCESS_latex_template_20260513/access.tex".
3. Python scripts that generate result tables and figures which is store in 'C:\Users\balan\IdeaProjects\blink_detection_llm\experiment_script'.
4. CSV/result data files used to generate the manuscript results which is store in 'C:\Users\balan\IdeaProjects\blink_detection_llm\publication_results'.

Your role is to act as a project manager and spawn multiple sub-agents to perform validation and cleanup. The manuscript contains three main experiments. The current objective is NOT to rewrite the manuscript, but to validate, organize, and clean up the result-generation pipeline.

Main goals:

1. Rename Python result-generation scripts so their filenames clearly match the manuscript result table or figure they generate.
2. Independently verify manuscript-reported numerical/statistical results from CSV files.
3. Identify scripts for tables/figures no longer used in the final manuscript and move them into an `obsolete/` folder.
4. Produce clear audit reports so a human can quickly inspect any mismatch.

Important constraints:

- Do not change scientific interpretation unless a clear error is found.
- Do not silently overwrite manuscript values.
- Do not delete files. Move unused scripts to `obsolete/`.
- Preserve reproducibility.
- Use git-aware operations where possible.
- Keep a mapping of every old filename to its new filename.
- If unsure whether a script is used, mark it as “uncertain” instead of moving it.

Agent 1: Manuscript Result Inventory

Tasks:

1. Inspect the final LaTeX manuscript and the compiled PDF `C:\Users\balan\IdeaProjects\blink_detection_llm\writing\ACCESS_latex_template_20260513\0_original_access.pdf`.
2. Identify every result table and figure in the manuscript.
3. For each table/figure, record:
   - Experiment number: Experiment 1, Experiment 2, or Experiment 3
   - Table/Figure number
   - LaTeX label
   - Caption
   - File included in LaTeX, if any
   - Output file path, e.g. `.tex`, `.png`, `.pdf`, `.csv`
   - Result section where it appears
   - Short descriptive slug based on the caption

Deliverable:

Create:

```text
reports/result_inventory.csv
reports/result_inventory.md
````

Suggested columns:

```text
experiment, item_type, item_number, label, caption, short_slug, latex_source_file, output_file, result_section, notes
```

Agent 2: Script Renaming and Traceability

Tasks:

1. Locate all Python scripts that generate result tables and figures.
2. Match each script to the corresponding table or figure in `reports/result_inventory.csv`.
3. Rename scripts using this convention:

For figures:

```text
res_exp<experiment_number>_fig_<brief_caption_slug>.py
```

For tables:

```text
res_exp<experiment_number>_table_<brief_caption_slug>.py
```

Examples:

```text
res_exp1_fig_regional_f1_comparison.py
res_exp1_table_per_electrode_statistics.py
res_exp2_fig_threshold_ablation.py
res_exp3_table_cross_dataset_performance.py
```

Rules for slug:

* Use lowercase.
* Use underscores.
* Keep it brief but meaningful.
* Derive it from the figure/table caption.
* Avoid very long filenames.
* Avoid vague names such as `plot1.py`, `final.py`, `table_results.py`.

4. Update any references, Makefiles, notebooks, shell scripts, or documentation that call the old filenames.
5. Create a rename log.

Deliverable:

```text
reports/script_rename_map.csv
```

Suggested columns:

```text
old_path, new_path, experiment, item_type, table_or_figure_number, label, caption_slug, confidence, notes
```

Agent 3: Independent Result Validation

Important: This agent must validate results independently.

Assume this agent has access only to CSV/result data files and the manuscript/PDF. Do not reuse the existing Python result-generation scripts.

Tasks:

1. Read all result values claimed in the manuscript, tables, and figure captions.
2. Create new independent validation scripts under:

```text
validation/
```

3. Recompute the reported statistics directly from CSV files.
4. Compare manuscript values against independently recomputed values.
5. For each checked value, report:

    * Location in manuscript
    * Claimed old value
    * Independently computed new value
    * Difference
    * Match status
    * Note
    * Possible root cause if mismatch occurs

Deliverables:

```text
validation/validate_exp1_results.py
validation/validate_exp2_results.py
validation/validate_exp3_results.py
reports/result_validation_table.csv
reports/result_validation_report.md
```

Use this table format:

```text
experiment, manuscript_location, metric_or_statistic, old_value, new_value, difference, match_status, note, possible_root_cause
```

Match status should be one of:

```text
MATCH
ROUNDING_DIFFERENCE
MISMATCH
UNCLEAR_SOURCE
NOT_REPRODUCIBLE_FROM_AVAILABLE_CSV
```

If values do not match, investigate the likely cause, for example:

* Different rounding rule
* Macro vs micro aggregation
* Different session inclusion/exclusion
* Different channel/electrode subset
* Different statistical test
* Different correction method
* Different CSV source
* Old manuscript value not updated
* Figure/table dropped or obsolete

Do not automatically “fix” manuscript values. Flag them for human review.

Agent 4: Obsolete Script Cleanup

Tasks:

1. Identify Python scripts under the folder 'C:\Users\balan\IdeaProjects\blink_detection_llm\experiment_script' that generate tables or figures not used in the final manuscript.
2. Move these scripts into:

```text
C:\Users\balan\IdeaProjects\blink_detection_llm\experiment_script\obs
```

3. Preserve subfolder structure where helpful.
4. Add a README inside `obsolete/` explaining why files were moved.
5. Do not move scripts that are still needed by active scripts unless they are clearly standalone obsolete generators.

Deliverables:

```text
obsolete/README.md
reports/obsolete_scripts.csv
```

Suggested columns:

```text
old_path, new_path, reason, evidence, confidence, notes
```

Manager Agent: Final Integration and QA

Tasks:

1. Review outputs from all agents.
2. Confirm the repository still runs after renaming.
3. Recompile the manuscript PDF.
4. Confirm that all active result tables and figures still render correctly.
5. Run available tests if present.
6. Produce a final summary.

Final deliverables:

```text
reports/final_cleanup_summary.md
reports/result_inventory.csv
reports/script_rename_map.csv
reports/result_validation_table.csv
reports/result_validation_report.md
reports/obsolete_scripts.csv
obsolete/README.md
```

Final summary must include:

1. Number of active result figures and tables found.
2. Number of scripts renamed.
3. Number of obsolete scripts moved.
4. Number of validated values.
5. Number of exact matches.
6. Number of rounding-only differences.
7. Number of mismatches requiring human review.
8. Any manuscript values that should be checked by the human author.
9. Any scripts or figures that could not be confidently mapped.
10. Commands used to reproduce the checks.

Before finishing, run:

```bash
git status
```

Then summarize all changed files.

```

Other useful tasks you can add:

1. **Traceability matrix**  
   Map every manuscript claim to its source CSV, script, generated output, and LaTeX location.

2. **Pre/post PDF comparison**  
   Recompile before and after cleanup and confirm the visual manuscript output did not change unexpectedly.

3. **Rounding policy audit**  
   Check whether all reported values use consistent decimal places, percentages, p-values, and significance symbols.

4. **Statistical-method audit**  
   Confirm that each test matches the manuscript wording, especially paired vs unpaired tests, Wilcoxon use, Bonferroni correction, macro-F1 aggregation, and session-level pairing.

5. **Reproducibility README**  
   Create a short `README_results.md` explaining how to regenerate every table and figure.

6. **Data manifest with checksums**  
   Add a manifest listing every CSV used for final results, with file paths and checksums.

7. **Unused LaTeX asset cleanup**  
   Identify unused `.tex`, `.png`, `.pdf`, and `.csv` outputs that are no longer included in the manuscript.

8. **Label/caption consistency check**  
   Check that all `\label{}` references, figure numbers, table numbers, and captions match the compiled PDF.

9. **Validation plots/tables folder**  
   Keep independent QC outputs separate from publication outputs, so validation does not contaminate final manuscript assets.

10. **Human-review checklist**  
   Generate one short checklist containing only the mismatches, uncertain mappings, and values needing author decision.
```
