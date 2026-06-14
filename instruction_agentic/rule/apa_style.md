
Create:

```text
paper/references.bib
```

Generate it from:

```text
references_meta.bibtex_entry
```

The BibTeX/APA Agent must:

```text
1. Extract title, author, year, journal, DOI from CSV/DB.
2. Normalize missing fields.
3. Create stable citation keys.
4. Remove duplicate references.
5. Save all entries to paper/references.bib.
6. Check every \cite{} key exists.
7. Check every .bib key is used or marked as unused.
```

Recommended LaTeX setup:

```latex
\usepackage[style=apa,backend=biber]{biblatex}
\addbibresource{references.bib}
```

Then at the end:

```latex
\printbibliography
```
