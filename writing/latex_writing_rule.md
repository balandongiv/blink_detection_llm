The latex structure should be organized as follows:

```text
writing/
  a_abstract/
    main.tex
    p001/
      paragraph.tex
      original_quotes.tex
      evidence.json
      claims.json
      review.md

  b_intro/
    main.tex
    p001/
      paragraph.tex
      original_quotes.tex
      evidence.json
      claims.json
      review.md
    p002/
      paragraph.tex
      original_quotes.tex
      evidence.json
      claims.json
      review.md

  c_literature_review/
    main.tex
    p001/
      paragraph.tex
      original_quotes.tex
      evidence.json
      claims.json
      review.md

  d_methodology/
    main.tex
    p001/
      paragraph.tex
      original_quotes.tex
      evidence.json
      claims.json
      review.md
    p002_experiment_rerun_note/
      paragraph.tex
      experiment_manifest.json
      review.md

  e_results/
    main.tex
    p001_raja_result/
      paragraph.tex
      original_quotes.tex
      evidence.json
      claims.json
      review.md
    p002_raja_rerun_note/
      paragraph.tex
      experiment_manifest.json
      review.md
    p003_hakim2029_result/
      paragraph.tex
      original_quotes.tex
      evidence.json
      claims.json
      review.md
    p004_hakim2029_rerun_note/
      paragraph.tex
      experiment_manifest.json
      review.md

  f_discussion/
    main.tex
    p001/
      paragraph.tex
      original_quotes.tex
      evidence.json
      claims.json
      review.md

  g_conclusion/
    main.tex
    p001/
      paragraph.tex
      original_quotes.tex
      evidence.json
      claims.json
      review.md
```

The main change I recommend is: **even the abstract should follow the paragraph-folder rule**. So instead of only:

```text
a_abstract/
  abstract.tex
```

use:

```text
a_abstract/
  main.tex
  p001/
    paragraph.tex
```

Then `a_abstract/main.tex` contains:

```latex
\input{writing/a_abstract/p001/paragraph}
```

This keeps the whole paper consistent and easier to audit.

---

# Section `main.tex` rule

Each section folder should have a `main.tex`.

Example:

```latex
% writing/b_intro/main.tex

\section{Introduction}

\input{writing/b_intro/p001/paragraph}
\input{writing/b_intro/p002/paragraph}
```

For literature review:

```latex
% writing/c_literature_review/main.tex

\section{Literature Review}

\input{writing/c_literature_review/p001/paragraph}
```

For results:

```latex
% writing/e_results/main.tex

\section{Results}

\input{writing/e_results/p001_raja_result/paragraph}
\input{writing/e_results/p002_raja_rerun_note/paragraph}

\input{writing/e_results/p003_hakim2029_result/paragraph}
\input{writing/e_results/p004_hakim2029_rerun_note/paragraph}
```

---

# Top-level paper file

Your main paper file can then be simple:

```latex
\documentclass{article}

\input{preamble}

\begin{document}

\input{writing/a_abstract/main}
\input{writing/b_intro/main}
\input{writing/c_literature_review/main}
\input{writing/d_methodology/main}
\input{writing/e_results/main}
\input{writing/f_discussion/main}
\input{writing/g_conclusion/main}

\printbibliography

\end{document}
```

---

# Draft/final mode for rerun notes

Add this to `preamble.tex`:

```latex
\newif\ifdraftnotes

% Draft mode:
\draftnotestrue

% Final mode:
% \draftnotesfalse

\newcommand{\experimentnote}[1]{%
  \ifdraftnotes
  \par\noindent
  \begingroup
  \small
  \textbf{Draft reproducibility note.} #1
  \par
  \endgroup
  \fi
}
```

Then each rerun-note paragraph uses:

```latex
\experimentnote{
This experiment can be rerun using
\texttt{analysis/experiments/exp\_001\_raja\_baseline/run.sh}.
The script reloads the Raja dataset from the SQLite database, regenerates the
outputs, and compares them against the preliminary results.
}
```

In draft mode, this note appears.

In final mode, it disappears.

The file still exists for auditing.

---

# Agent validation rule for your structure

The validator should enforce:

```text
Every section folder must contain main.tex.

Every normal paragraph folder must contain:
  paragraph.tex
  original_quotes.tex
  evidence.json
  claims.json
  review.md

Every experiment-note paragraph folder must contain:
  paragraph.tex
  experiment_manifest.json
  review.md

No section main.tex should contain full prose.
It should only contain section headings and \input{} commands.

Each paragraph.tex should contain exactly one paragraph or one draft note block.

Raja and Hakim2029 rerun notes must appear under the same results subsection as their result paragraph.
```

---

# Suggested naming convention

Your current `p001`, `p002` is good. For easier debugging, I recommend descriptive suffixes:

```text
p001_problem_context/
p002_research_gap/
p003_raja_result/
p004_raja_rerun_note/
p005_hakim2029_result/
p006_hakim2029_rerun_note/
```

This keeps ordering while making the purpose obvious.

The final structure is compatible with your existing layout, but stricter, easier to validate, and better for rerunning experiments and hiding draft-only reproducibility notes.
