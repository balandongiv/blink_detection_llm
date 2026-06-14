# Hard rules
```text
1. Use MCP/GROBID as the primary PDF extraction method.
2. Do not use ad-hoc PDF parsing unless MCP/GROBID fails.
3. If fallback extraction is used, log the failure and record the fallback in extraction_method.
4. Store raw GROBID/MCP output before transforming it into SQLite.
5. Preserve exact original text.
6. Preserve provenance:
   - PDF filename
   - page number if available
   - section heading if available
   - paragraph/order index if available
   - extraction method
   - extraction timestamp
7. Insert extracted text into SQLite, not directly into writing files.
8. Every writing paragraph must cite extracted evidence from the DB or CSV metadata.
```



# Required extraction tables

```sql
CREATE TABLE IF NOT EXISTS pdf_extractions (
  extraction_id TEXT PRIMARY KEY,
  study_id TEXT,
  pdf_path TEXT NOT NULL,
  extraction_method TEXT NOT NULL,
  mcp_tool_name TEXT,
  grobid_output_path TEXT,
  status TEXT NOT NULL,
  error_message TEXT,
  extracted_at TEXT
);
```

```sql
CREATE TABLE IF NOT EXISTS pdf_text_chunks (
  chunk_id TEXT PRIMARY KEY,
  extraction_id TEXT NOT NULL,
  study_id TEXT,
  pdf_path TEXT NOT NULL,
  page_start INTEGER,
  page_end INTEGER,
  section_heading TEXT,
  chunk_order INTEGER,
  chunk_type TEXT,
  original_text TEXT NOT NULL,
  FOREIGN KEY (extraction_id) REFERENCES pdf_extractions(extraction_id)
);
```

Updated PDF extraction pipeline:

```text
PDF/Text Extraction Agent:
  1. Read README_GROBID_MCP.md.
  2. Read instruction_agentic/prompt/pdf_reader_prompt.md.
  3. Use MCP/GROBID as primary extraction method.
  4. Store raw GROBID/MCP output.
  5. Convert structured extraction to SQLite.
  6. Preserve exact original text for paragraph-level evidence.
  7. Allow fallback only after logged MCP/GROBID failure.
```
