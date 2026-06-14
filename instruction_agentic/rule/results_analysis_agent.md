
The Results Analysis Agent must explicitly use:

```text
Raja dataset
Murat2018 dataset
```

Minimum required analyses:

```text
1. Descriptive comparison of Raja vs Murat2018
2. Cross-dataset consistency check
3. Missingness / data-quality analysis
4. Robustness or sensitivity analysis
5. Subgroup or stratified analysis if variables permit
6. Contradiction analysis: where Raja and Murat2018 disagree
```

Outputs:

```text
analysis/scripts/
  01_load_data.py
  02_descriptive_analysis.py
  03_cross_dataset_comparison.py
  04_robustness_analysis.py
  05_extra_analysis.py

analysis/outputs/
  tables/
  figures/
  analysis_summary.md
  result_claims.json
```

The Results Analysis Agent must not directly write the Results section until scripts have produced reproducible outputs.
