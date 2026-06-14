
Use a local task database:

```text
runs/tasks.sqlite
```

Each task status must be one of:

```text
pending
running
completed
failed
blocked_offline
needs_review
```

Every task must include:

```text
input_hash
output_hash
runner
model_hint
requires_internet
created files
log path
local instruction files consulted
```

If internet turns off:

```text
1. Continue deterministic local tasks:
   - CSV to SQLite
   - SQL queries
   - local validation
   - LaTeX checks
   - existing cached model output review
   - analysis scripts
   - figure/table generation

2. Queue model-dependent tasks:
   - writing
   - deep reasoning validation
   - discussion synthesis
   - conclusion rewrite

3. Resume automatically when internet returns:
   - only rerun incomplete or stale tasks
   - skip tasks with matching input_hash/output_hash
```

Do not depend on memory of previous agent conversations.

Save every prompt, response, and output:

```text
data/cache/model_calls/
  task_intro_gap_p001/
    prompt.md
    response.md
    parsed_output.json
    model.txt
    timestamp.txt
```