Example `evidence.json`:
```json
{
  "paragraph_id": "intro_01_background_p001",
  "claims": [
    {
      "claim": "The reviewed studies indicate a persistent limitation in prior evaluation methods.",
      "source_type": "abstract",
      "study_id": "raja_014",
      "exact_original_text": "Exact sentence copied from abstract or PDF here.",
      "source_location": {
        "csv_column": "abstract",
        "pdf_page": null
      },
      "bibtex_key": "Raja2024Evaluation"
    }
  ]
}
```

Example `original_quotes.tex`:

```latex
% Exact original text used to support this paragraph.
% Source: Raja2024Evaluation, abstract

\begin{quote}
Exact original text from the abstract or PDF goes here.
\end{quote}
```

The Validation Agent must fail any paragraph that lacks:

```text
paragraph.tex
original_quotes.tex
evidence.json
claims.json
at least one citation
claim-to-source mapping
```
