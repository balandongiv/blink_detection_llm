
The pipeline must **never write from CSV directly** after ingestion.

CSV files remain the raw source, but the working source of truth is:

```text
data/db/paper_sources.sqlite
```

CSV location:

```text
G:\My Drive\iterate_literature_review\complete_file_available_in_zotero.csv
```

Minimum tables:

```sql
studies(
  study_id TEXT PRIMARY KEY,
  title TEXT,
  authors TEXT,
  year INTEGER,
  journal TEXT,
  doi TEXT,
  abstract TEXT,
  source_csv TEXT,
  dataset_name TEXT
);

pdf_text(
  text_id TEXT PRIMARY KEY,
  study_id TEXT,
  page INTEGER,
  section_hint TEXT,
  original_text TEXT,
  extraction_method TEXT,
  source_pdf TEXT
);

references_meta(
  ref_id TEXT PRIMARY KEY,
  study_id TEXT,
  bibtex_key TEXT,
  apa7_text TEXT,
  bibtex_entry TEXT
);

claims(
  claim_id TEXT PRIMARY KEY,
  paragraph_id TEXT,
  claim_text TEXT,
  evidence_text_id TEXT,
  study_id TEXT,
  confidence_score REAL
);

paragraphs(
  paragraph_id TEXT PRIMARY KEY,
  section TEXT,
  subsection TEXT,
  paragraph_order INTEGER,
  tex_path TEXT,
  status TEXT,
  word_count INTEGER
);

tasks(
  task_id TEXT PRIMARY KEY,
  agent_name TEXT,
  input_hash TEXT,
  output_hash TEXT,
  status TEXT,
  requires_internet INTEGER,
  runner TEXT,
  model_hint TEXT,
  created_at TEXT,
  updated_at TEXT
);
```

Add SQLite FTS:

```sql
CREATE VIRTUAL TABLE study_fts USING fts5(
  study_id,
  title,
  abstract,
  content='studies',
  content_rowid='rowid'
);

CREATE VIRTUAL TABLE pdf_text_fts USING fts5(
  text_id,
  study_id,
  original_text,
  content='pdf_text',
  content_rowid='rowid'
);
```

---