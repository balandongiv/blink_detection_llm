# LaTeX Thesis Structure Requirements

This document defines a reusable thesis-writing layout for `writing/`. It uses a strict decomposition rule: every chapter, section, subsection, and paragraph has an explicit filesystem location.

## Core Rule

Every prose paragraph must live in its own `.tex` file.

Use this audit model:

```text
one paragraph
one tex file
one folder-level location
one evidence/provenance trail
```

The root `main.tex` must only assemble the thesis. It should not contain long thesis prose except front matter, package setup, title metadata, bibliography setup, and top-level `\input{...}` calls.

## Required Root Layout

Each thesis should have one manuscript root folder, normally named `writing/`.

```text
writing/
  main.tex
  references.bib
  references_from_csv.bib
  .latexmkrc

  front_matter/
    abstract.tex
    acknowledgements.tex
    declaration.tex

  ch01_introduction/
    chapter.tex
    s001_background/
      section.tex
      p001/
        paragraph.tex
      p002/
        paragraph.tex
    s002_problem_statement/
      section.tex
      p001/
        paragraph.tex
    s003_research_questions/
      section.tex
      p001/
        paragraph.tex
    s004_objectives/
      section.tex
      p001/
        paragraph.tex
    s005_scope/
      section.tex
      p001/
        paragraph.tex
    s006_thesis_structure/
      section.tex
      p001/
        paragraph.tex

  ch02_literature_review/
    chapter.tex
    s001_domain_background/
      section.tex
      p001/
        paragraph.tex
    s002_prior_methods/
      section.tex
      ss001_classical_methods/
        subsection.tex
        p001/
          paragraph.tex
      ss002_machine_learning_methods/
        subsection.tex
        p001/
          paragraph.tex
    s003_research_gap/
      section.tex
      p001/
        paragraph.tex

  ch03_methodology/
    chapter.tex
    s001_research_design/
      section.tex
      p001/
        paragraph.tex
    s002_dataset/
      section.tex
      p001/
        paragraph.tex
    s003_preprocessing/
      section.tex
      p001/
        paragraph.tex
    s004_proposed_method/
      section.tex
      ss001_pipeline_overview/
        subsection.tex
        p001/
          paragraph.tex
      ss002_algorithm_steps/
        subsection.tex
        p001/
          paragraph.tex
    s005_evaluation_protocol/
      section.tex
      p001/
        paragraph.tex

  ch04_results/
    chapter.tex
    s001_experimental_setup/
      section.tex
      p001/
        paragraph.tex
    s002_main_results/
      section.tex
      p001/
        paragraph.tex
      tables/
        tab_main_result.tex
      figures/
        fig_main_result.pdf
    s003_additional_analysis/
      section.tex
      p001/
        paragraph.tex

  ch05_discussion/
    chapter.tex
    s001_summary_of_findings/
      section.tex
      p001/
        paragraph.tex
    s002_interpretation/
      section.tex
      p001/
        paragraph.tex
    s003_comparison_with_prior_work/
      section.tex
      p001/
        paragraph.tex
    s004_limitations/
      section.tex
      p001/
        paragraph.tex
    s005_implications/
      section.tex
      p001/
        paragraph.tex

  ch06_conclusion/
    chapter.tex
    s001_conclusion/
      section.tex
      p001/
        paragraph.tex
    s002_contributions/
      section.tex
      p001/
        paragraph.tex
    s003_future_work/
      section.tex
      p001/
        paragraph.tex
```

## Thesis Chapter Requirements

The thesis must use these six chapter folders:

- `ch01_introduction/`
- `ch02_literature_review/`
- `ch03_methodology/`
- `ch04_results/`
- `ch05_discussion/`
- `ch06_conclusion/`

Each chapter folder must contain exactly one chapter aggregator file named `chapter.tex`.

## Naming Requirements

- Chapter folders must be ordered with a two-digit chapter prefix: `ch01_`, `ch02_`, `ch03_`.
- Each chapter folder must contain `chapter.tex`.
- Each main section inside a chapter must be ordered with `s001_<short_name>`, `s002_<short_name>`, `s003_<short_name>`.
- Each section folder must contain `section.tex`.
- Each subsection folder must be ordered with `ss001_<short_name>`, `ss002_<short_name>`, `ss003_<short_name>`.
- Each subsection folder must contain `subsection.tex`.
- Each paragraph folder must be ordered as `p001`, `p002`, `p003`.
- Each paragraph folder must contain exactly one prose leaf file named `paragraph.tex`.
- Table files should use `tab_<short_name>.tex`.
- Figure files should use `fig_<short_name>.<ext>`.
- Scratch, obsolete, or currently disabled material must go under an `obs/` folder and must not be included by default.

## Main File Contract

`main.tex` is the only file that declares the document class, packages, bibliography resources, title, author, and document environment.

It should assemble the thesis like this:

```tex
\begin{document}

\frontmatter
\maketitle
\input{front_matter/abstract}
\input{front_matter/acknowledgements}
\tableofcontents
\listoffigures
\listoftables

\mainmatter
\input{ch01_introduction/chapter}
\input{ch02_literature_review/chapter}
\input{ch03_methodology/chapter}
\input{ch04_results/chapter}
\input{ch05_discussion/chapter}
\input{ch06_conclusion/chapter}

\backmatter
\printbibliography

\end{document}
```

If the thesis class does not support `\frontmatter`, `\mainmatter`, or `\backmatter`, keep the same folder structure and omit those commands.

Do not place `\chapter`, `\section`, `\subsection`, result prose, discussion prose, or literature-review prose directly in `main.tex`.

## Chapter File Contract

Each `chapter.tex` owns exactly one `\chapter{...}` command and the ordered list of section inputs for that chapter.

Example:

```tex
\chapter{Methodology}
\label{ch:methodology}

\input{ch03_methodology/s001_research_design/section}
\input{ch03_methodology/s002_dataset/section}
\input{ch03_methodology/s003_preprocessing/section}
\input{ch03_methodology/s004_proposed_method/section}
\input{ch03_methodology/s005_evaluation_protocol/section}
```

## Section File Contract

Each `section.tex` owns exactly one `\section{...}` command and the ordered list of subsection, paragraph, table, or figure inputs.

For a section with direct paragraphs:

```tex
\section{Limitations}
\label{sec:limitations}

\input{ch05_discussion/s004_limitations/p001/paragraph}
\input{ch05_discussion/s004_limitations/p002/paragraph}
```

For a section with subsections:

```tex
\section{Proposed Method}
\label{sec:proposed_method}

\input{ch03_methodology/s004_proposed_method/ss001_pipeline_overview/subsection}
\input{ch03_methodology/s004_proposed_method/ss002_algorithm_steps/subsection}
```

## Subsection File Contract

Each `subsection.tex` owns exactly one `\subsection{...}` command and the ordered list of paragraph/table/figure inputs for that subsection.

```tex
\subsection{Pipeline Overview}
\label{sec:pipeline_overview}

\input{ch03_methodology/s004_proposed_method/ss001_pipeline_overview/p001/paragraph}
\input{ch03_methodology/s004_proposed_method/ss001_pipeline_overview/p002/paragraph}
```

If a subsection needs subsubsections, create subsubsection folders only when the structure is genuinely necessary:

```text
ss002_algorithm_steps/
  subsection.tex
  sss001_stage_a/
    subsubsection.tex
    p001/paragraph.tex
  sss002_stage_b/
    subsubsection.tex
    p001/paragraph.tex
```

## Paragraph File Contract

Each `paragraph.tex` must contain one logical prose paragraph only.

Allowed content:

- One paragraph of thesis prose.
- Local citation commands required by that paragraph.
- Short inline math required by that paragraph.
- A short provenance comment at the top when needed.

Avoid:

- Multiple prose paragraphs in one file.
- Chapter, section, or subsection headings.
- Long tables.
- Long figures.
- Package declarations.
- Bibliography declarations.
- Global macros.

Example:

```tex
% Evidence: runs/reports/verified_numbers.md, Table 2.
The proposed median-based threshold estimator improved macro-averaged $F_1$
relative to the mean-based variant, indicating that robust scale estimation is
preferable when suspicious epochs contain high-amplitude outliers.
```

## Tables and Figures

Tables and figures should be separate from prose paragraphs.

For results-heavy chapters, prefer this layout:

```text
ch04_results/
  s002_main_results/
    section.tex
    p001/
      paragraph.tex
    tables/
      tab_comparison_30s_epoch.tex
    figures/
      fig_f1_by_dataset.pdf
```

The section or subsection aggregator controls placement:

```tex
\input{ch04_results/s002_main_results/p001/paragraph}
\input{ch04_results/s002_main_results/tables/tab_comparison_30s_epoch}

\begin{figure}[ht]
  \centering
  \includegraphics[width=0.8\linewidth]{ch04_results/s002_main_results/figures/fig_f1_by_dataset.pdf}
  \caption{Macro-averaged $F_1$ by dataset.}
  \label{fig:f1_by_dataset}
\end{figure}
```

## Migration Steps for Another Thesis

1. Create a fresh `writing/` folder.
2. Add `main.tex`, `.latexmkrc`, and the active `.bib` file.
3. Create `front_matter/` if the thesis needs abstract, declaration, acknowledgements, or similar pages.
4. Create the six required chapter folders from `ch01_introduction/` through `ch06_conclusion/`.
5. Put exactly one `chapter.tex` file in each chapter folder.
6. For each chapter, create section folders such as `s001_background/`, `s002_problem_statement/`, and `s003_research_questions/`.
7. Put exactly one `section.tex` file in each section folder.
8. For sections with subsections, create `ss001_<name>/`, `ss002_<name>/`, and so on.
9. Put exactly one `subsection.tex` file in each subsection folder.
10. Put each prose paragraph in `p###/paragraph.tex`.
11. Put tables and figures in section-local or subsection-local `tables/` and `figures/` folders unless they are shared across the whole thesis.
12. Wire the thesis only through `\input{...}` from `main.tex` to chapter files, from chapter files to section files, from section files to subsection or paragraph files, and from subsection files to paragraph/table/figure files.
13. Compile from the manuscript root.

## Validation Checklist

Before considering a thesis structurally valid:

- `main.tex` contains no long thesis prose.
- All six required chapter folders exist.
- Every chapter folder has a `chapter.tex`.
- Every `chapter.tex` contains exactly one `\chapter{...}` command.
- Every main section has its own folder.
- Every section folder has a `section.tex`.
- Every `section.tex` contains exactly one `\section{...}` command.
- Every subsection with more than one paragraph has its own folder.
- Every subsection folder has a `subsection.tex`.
- Every prose paragraph is in a `p###/paragraph.tex` file.
- No `paragraph.tex` contains multiple unrelated paragraphs.
- All active files are reachable through `\input{...}` from `main.tex`.
- Disabled or obsolete material is under `obs/` or is clearly commented out.
- The thesis compiles without missing input files.

## Build Command

Run from the manuscript root:

```powershell
cd writing
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

If `latexmk` is unavailable, use the project's manual build sequence for `pdflatex` and `biber`.
