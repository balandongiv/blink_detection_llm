

Recommended model policy:

```text id="mwweym"
low →
  simple formatting
  file renaming
  folder creation
  manifest generation
  boilerplate LaTeX include files
  simple JSON/YAML edits
  simple validation reports
  extracting already-structured metadata
  converting paragraph plans into folder skeletons
  checking whether required files exist

medium →
  ordinary code edits
  small bug fixes
  simple Python scripts
  simple SQL queries
  simple LaTeX fixes
  rewriting weak but non-critical paragraphs
  summarising a small evidence bundle
  creating experiment run.sh files
  comparing expected vs observed output files

high →
  analysis code
  SQL logic
  evidence extraction
  LaTeX restructuring
  PDF-to-evidence mapping
  rerun pipeline debugging
  Raja/Hakim2029 comparison scripts
  new analysis feasibility checks
  result-diff interpretation
  citation and BibTeX repair

super_high / GPT-5.5-level →
  difficult reasoning
  paper-level synthesis
  deep validation
  discussion writing
  conclusion rewriting
  identifying overclaiming
  checking soundness and flow
  judging whether new analysis is meaningful
  interpreting contradictions between Raja and Hakim2029
```

I would make **low the default**, then escalate only when needed.

---

# Updated model-selection logic

The Agent Manager should choose the lowest tier that can safely complete the task.

```text id="yfr1ll"
Start with low unless:
  - the task changes analysis logic,
  - the task writes academic claims,
  - the task interprets results,
  - the task extracts evidence from complex PDF text,
  - the task affects the final argument of the paper,
  - the task previously failed twice.
```

Escalation rule:

```text id="rcoumv"
low failure twice → medium
medium failure twice → high
high failure once on reasoning-heavy task → super_high
```

---

# Suggested `models.yaml`

```yaml id="f56zbl"
model_tiers:
  low:
    description: "Cheap, fast model for deterministic or low-risk tasks."
    use_for:
      - folder creation
      - manifest generation
      - simple JSON edits
      - simple YAML edits
      - boilerplate LaTeX
      - checking required files
      - extracting structured metadata
      - creating paragraph skeletons
    avoid_for:
      - academic argumentation
      - result interpretation
      - evidence judgment
      - conclusion rewriting
      - discussion synthesis

  medium:
    description: "General implementation model for ordinary coding and non-critical writing."
    use_for:
      - ordinary code edits
      - small Python scripts
      - simple SQL queries
      - simple LaTeX fixes
      - run script creation
      - simple evidence summaries
      - preliminary paragraph rewriting
    avoid_for:
      - deep paper synthesis
      - complex statistical analysis
      - contradiction analysis
      - final conclusion writing

  high:
    description: "Reliable model for technical analysis, SQL logic, evidence extraction, and structural edits."
    use_for:
      - analysis code
      - SQL logic
      - evidence extraction
      - LaTeX restructuring
      - PDF evidence mapping
      - rerun debugging
      - Raja/Hakim2029 comparison
      - citation repair
      - BibTeX repair
    avoid_for:
      - final paper-level synthesis unless reviewed

  super_high:
    description: "Strongest reasoning model for academic synthesis and deep validation."
    use_for:
      - difficult reasoning
      - discussion writing
      - conclusion rewriting
      - paper-level synthesis
      - deep validation
      - overclaiming detection
      - argument soundness
      - deciding whether new analysis is meaningful
      - interpreting contradictions
```

---

# Runner policy

For your two allowed execution paths:

```text id="jzsd6l"
ChatGPT UI/API runner:
  low:
    - quick summaries
    - draft notes
    - simple writing cleanup
  medium:
    - paragraph drafting from clean evidence
    - simple review
  high:
    - evidence extraction
    - citation-grounded writing
  super_high:
    - discussion
    - conclusion
    - deep soundness validation

Terminal Codex runner:
  low:
    - folder scaffolding
    - manifests
    - simple validators
  medium:
    - simple scripts
    - run.sh files
    - small refactors
  high:
    - analysis code
    - SQL pipeline
    - LaTeX restructuring
    - experiment rerun debugging
  super_high:
    - only for complex pipeline failures or architecture-level refactor
```

---

# Practical recommendation

Use this default assignment:

```text id="5yhq8r"
Agent Manager thinking:
  super_high when planning the whole paper or resolving contradictions
  high for task routing and pipeline repair
  medium for routine scheduling
  low only for status checks

Data Ingestion Agent:
  medium by default
  high if schema normalization is complex

PDF/Text Extraction Agent:
  high by default
  super_high if extraction requires judgment

Study Retrieval Agent:
  high by default

Paragraph Structure Agent:
  high by default
  super_high for whole-paper outline

Academic Writing Agent:
  medium for first draft
  high for citation-grounded rewrite
  super_high for final version

Results Analysis Agent:
  high by default
  super_high if interpreting unexpected results

Discussion Agent:
  super_high

Conclusion Agent:
  super_high

Validation Agent:
  low for file checks
  medium for LaTeX compile checks
  high for citation/evidence checks
  super_high for soundness and flow
```

This gives you cost control while still protecting the important academic reasoning stages.
