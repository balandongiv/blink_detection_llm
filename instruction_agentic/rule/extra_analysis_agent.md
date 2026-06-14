
The new analysis must not be created randomly.

The Extra Analysis Idea Miner Agent must:

```text
Read provided PDFs.
Extract analysis ideas.
Map each idea to available variables in Raja and Murat2018.
Reject ideas that cannot be implemented.
Rank ideas by novelty, feasibility, and relevance.
Generate scripts only for feasible analyses.
```

Output example:

```json
{
  "candidate_analysis": [
    {
      "idea": "Cross-dataset robustness check",
      "inspired_by": "study_019",
      "exact_original_text": "Exact PDF text that motivated this idea.",
      "required_variables": ["x", "y", "group"],
      "available_in_raja": true,
      "available_in_murat2018": true,
      "feasibility": "high",
      "recommended": true,
      "script_path": "analysis/scripts/05_cross_dataset_robustness.py"
    }
  ]
}
```

Recommended extra analyses:

```text
1. Cross-dataset replication: test whether the same pattern appears in Raja and Murat2018.
2. Heterogeneity analysis: check whether findings differ by subgroup.
3. Sensitivity analysis: test whether findings change under different filtering rules.
4. Missing-data analysis: report whether missingness could affect interpretation.
5. Contradiction matrix: identify where literature claims and dataset results disagree.
6. Evidence-strength scoring: classify claims as strong, moderate, weak, or speculative.
```

Decision chain:

```text
PDF reading agent extracts idea
↓
exact PDF text is stored
↓
idea is mapped to Raja/Murat2018 variables
↓
feasibility is checked using SQLite schema
↓
manager approves task internally
↓
new analysis code is created
↓
new analysis is run
↓
new result paragraph is written
↓
new rerun-note paragraph is written
```

Each new analysis must have:

```text
analysis/new_analysis/experiment_id/
  idea_source.json
  feasibility_report.md
  run.sh
  analysis.py
  outputs/
  manifest.json
```

Example `idea_source.json`:

```json
{
  "new_analysis_id": "new_001_cross_dataset_robustness",
  "idea": "Compare whether the main pattern is stable across Raja and Murat2018.",
  "inspired_by_pdf": "paper_07.pdf",
  "exact_original_text": "Exact sentence or paragraph from the PDF that inspired the analysis.",
  "required_variables": ["outcome", "group", "method"],
  "available_in_raja": true,
  "available_in_murat2018": true,
  "decision": "implement"
}
```