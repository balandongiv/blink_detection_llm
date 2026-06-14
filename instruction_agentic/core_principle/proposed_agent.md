
| Agent                         | Main responsibility                                                      | Writes files? | Can run in parallel? |
| ----------------------------- | ------------------------------------------------------------------------ | ------------: | -------------------: |
| **Agent Manager**             | Thinks, plans, assigns tasks, checks status, chooses runner/model        |            No |         Controls all |
| **Data Ingestion Agent**      | Converts CSV to SQLite DB; ingests Raja and Murat2018 datasets           |           Yes |                  Yes |
| **PDF/Text Extraction Agent** | Extracts exact abstract/PDF text, page numbers, quotes, and provenance   |           Yes |                  Yes |
| **Study Retrieval Agent**     | Finds relevant studies for introduction and section claims using SQL/FTS |           Yes |                  Yes |
| **Paragraph Structure Agent** | Generates paragraph-level writing plans for each section/subsection      |           Yes |               Partly |
| **Academic Writing Agent**    | Writes LaTeX paragraph files using only cited evidence                   |           Yes |                  Yes |
| **Results Analysis Agent**    | Analyzes Raja and Murat2018 datasets; adds new analysis                  |           Yes |                  Yes |
| **Critical Analysis Agent**   | Interprets results, compares datasets, identifies limits/contradictions  |           Yes |                  Yes |
| **Discussion Agent**          | Writes discussion paragraphs tied to evidence and results                |           Yes |                  Yes |
| **Conclusion Agent**          | Inspects existing conclusion and rewrites it to match paper findings     |           Yes |           No/limited |
| **BibTeX/APA Agent**          | Generates dedicated `.bib` file from DB/CSV metadata                     |           Yes |                  Yes |
| **Validation Agent**          | Checks citations, evidence traceability, LaTeX compile, paragraph rules  |           Yes |                  Yes |
| **Soundness/Flow Agent**      | Checks argument flow, coherence, academic tone, and overclaiming         |           Yes |                  Yes |
| **Resume/State Agent**        | Tracks task state, hashes, retries, and internet-offline continuation    |           Yes |               Always |

Additional experiment agents:

| Agent                                 | Purpose                                                                         |
| ------------------------------------- | ------------------------------------------------------------------------------- |
| **Preliminary Result Registry Agent** | Records old/preliminary outputs before rerunning anything                       |
| **Experiment Rerun Agent**            | Reruns existing code for Raja and Murat2018                                     |
| **Result Diff Agent**                 | Compares rerun results against preliminary results                              |
| **New Analysis Idea Agent**           | Reads supplied PDFs and proposes possible extra analyses                        |
| **Analysis Feasibility Agent**        | Checks whether proposed analysis can be done using Raja/Murat2018 variables     |
| **New Analysis Coding Agent**         | Creates new analysis code only for feasible ideas                               |
| **Experiment Documentation Agent**    | Creates dedicated LaTeX paragraph explaining how to rerun each experiment       |
| **Draft Note Visibility Agent**       | Ensures experiment notes appear only in draft mode and are hidden in final mode |