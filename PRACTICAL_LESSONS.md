# Practical Lessons Learned — Blink Detection LLM Experiment Pipeline

Date: 2026-06-26  
Context: Running Exp1–8 ablation study across Raja (EGI-128, 46 sessions) and Cao2018 (10-20, 58 sessions) datasets using a multi-stage autoreject blink detector vs BLINKER and MNE baselines.

---

## 1. Windows Multiprocessing: Handle Exhaustion is Real

**Problem:** Setting `N_JOBS = None` (use all CPU cores) causes `DuplicateHandle` permission errors on Windows when processes are killed prematurely and worker processes become orphaned. With 24 logical threads, orphaned workers from previous killed runs can exhaust Windows handle limits.

**Fix:** Set `N_JOBS = 16` (two-thirds of available threads). This leaves headroom for the OS and prevents handle exhaustion even if workers are orphaned.

**Lesson:** On Windows with `ProcessPoolExecutor` or `joblib`, always set an explicit `N_JOBS` limit. Never use `None` or `-1` in production experiment scripts. A safe heuristic is `max(1, cpu_count() * 2 // 3)`.

---

## 2. Resume Support with OVERWRITE=False is Essential

**Problem:** Experiment 3 (406 tasks) took ~60 minutes. If the script is killed at 75%, all progress is lost without caching.

**Fix:** Every session result is written to `runs/<exp>/sessions/<session_name>.csv` immediately. On restart, the script checks for existence and skips (`OVERWRITE=False`). Only the final summary aggregation runs on all cached files.

**Lesson:** For any experiment that takes >10 minutes, implement per-session caching with a flag to skip completed sessions. Name cache files by session identifier so partial restarts are deterministic.

---

## 3. Session CSV Schema Must Be Stable Before Caching

**Problem:** Exp1 Cao2018 session files were written with the OLD schema (`best_channel` column, no `channel_in_group`) before per-channel evaluation was implemented. The script re-used cached files and produced wrong summary statistics (n=1 per channel instead of n=58).

**Fix:** Delete ALL cached session files whenever the output schema changes. The schema version is not embedded in the CSV, so there is no automatic way to detect stale files.

**Lesson:** When changing the per-session output schema (adding/removing columns), delete all cached sessions for that experiment before re-running. Consider embedding a `schema_version` column so scripts can auto-detect and invalidate stale caches.

---

## 4. DictWriter Requires a Union of Keys for Mixed-Schema Rows

**Problem:** Session CSVs contain both Proposed rows (with `stageA_*` fields) and baseline rows (BLINKER, MNE — no `stageA_*`). `csv.DictWriter` raises `ValueError` if fieldnames don't match all rows.

**Fix:**
```python
all_keys: list[str] = []
seen: set[str] = set()
for row in rows:
    for k in row.keys():
        if k not in seen:
            all_keys.append(k)
            seen.add(k)
writer = csv.DictWriter(fh, fieldnames=all_keys, extrasaction="ignore", restval="")
```

**Lesson:** Always collect the union of all row keys before creating a `DictWriter` when rows may have different schemas. Use `restval=""` to fill missing fields with empty strings.

---

## 5. Per-Channel Evaluation vs Best-Channel: Different Insights

**Problem:** The original `evaluate_channels()` call returned only the BEST channel result. This hid poor channels but also made it impossible to see per-channel variation within a group.

**Fix:** Loop over `channel_results` and call `evaluate_channels([ch_result])` for each channel individually. Each channel gets its own row in the output CSV.

**Lesson:** Report per-channel results whenever you have a multi-channel group. The "best channel" view hides inversions and variability. Per-channel reporting reveals which channels drive performance and which are unsuitable.

---

## 6. Periorbital vs Lateral Frontal: Signal Quality Determines Algorithm Suitability

**Empirical finding:** The Proposed algorithm (autoreject-based threshold) wins on periorbital channels (E9, E22 for Raja; FP1, FP2 for Cao2018) but LOSES on lateral frontal channels (F3, F4, F7, F8 for Cao2018; E3, E23, E33 for Raja).

**Reason:** Stage A autoreject relies on detecting high-amplitude epochs as blink-containing. On lateral frontal channels, blink amplitude is weak → autoreject cannot reliably identify blink epochs → Stage B learns a wrong threshold → Stage C fails.

**Lesson:** The suitability of an autoreject-based method is channel-dependent. Always evaluate on periorbital or frontopolar channels for blink detection. Report per-channel results and note inversions as findings about channel suitability, not algorithm failures.

---

## 7. BLINKER's High Recall Is Misleading

**Finding:** BLINKER-concat achieves recall ~0.95–0.99 on almost all channels, including poor ones. This inflates its F1 on lateral frontal channels relative to Proposed.

**Root cause:** BLINKER uses a permissive concatenation threshold tuned for periorbital channels globally. On weak-signal channels, it still detects "blinks" with ~50% precision (i.e., every other detection is a false alarm).

**Lesson:** F1 alone can be misleading. Always report precision AND recall. A detector with P=0.52, R=0.99 is not clinically useful. The Proposed algorithm trades some recall for much higher precision (+20–30pp), which is the right trade-off for blink artifact rejection.

---

## 8. Telegram Notifications: Read Token at Runtime, Never Hardcode

**Rule:** The Telegram bot token is stored in `bot_telegram.md` (git-ignored). It is read at runtime by `exp_tg_report.py`. Never print, log, or hardcode the token in any script.

**Lesson:** For any experiment with long runtimes (>15 min), add Telegram heartbeat + completion notifications. This allows monitoring from any device. Keep credentials in a git-ignored file and load them at runtime only.

---

## 9. Background Queue Timeout: Use a Script File, Not Inline PowerShell

**Problem:** PowerShell background tasks launched via the Agent tool have a 10-minute timeout. An inline script that calls `WaitForExit()` on 10 sequential experiments (total ~4 hours) will be killed.

**Fix:** Write the queue logic to a `.ps1` file and launch it as a separate `pwsh` process:
```powershell
Start-Process -FilePath "pwsh" -ArgumentList "-NonInteractive -File queue.ps1" -WindowStyle Hidden
```

**Lesson:** Never put long-running sequential logic into an inline background PowerShell command. Write it to a script file and launch the script file as a detached process. Use a `queue_progress.txt` log file (via `Tee-Object`) to monitor progress.

---

## 10. Import Errors Surface Only at Script End (After All Data Processing)

**Problem:** `run_exp4_raja.py` was missing `import time` and `start_time = time.time()`. The error only surfaced at the very end of the script (Telegram notification block), after all 46 sessions were processed and the summary CSV was already written. The session data was fine but the script exited with code 1.

**Fix:** Add `import time` to the import block and `start_time = time.time()` as the first line of `main()`.

**Lesson:** Place timing and notification code in a `try/finally` block so that failures in post-processing (Telegram, JSON export) do not mask successful data collection. Alternatively, check all scripts for `time.time()` usage before running them.

---

## 11. Epoch Health Filter: Dataset-Specific Impact

**Finding (Exp7):** `use_epoch_health=True` has negligible effect on Raja (-0.5pp) but dramatically improves Cao2018 FP1 (+12.1pp: 0.743 → 0.864).

**Reason:** The Raja dataset already excludes invalid epochs via its session structure. Cao2018 has more artifact-contaminated epochs that the health filter correctly removes, giving Stage A a cleaner signal.

**Lesson:** Ablation parameters can have dataset-specific effects. Always run ablations on both datasets and report them separately. Do not assume that a parameter improvement on one dataset generalises to the other.

---

## 12. Long Blinks Are a Systematic Weakness

**Finding (Exp8):** F1 for long blinks (≥ 400 ms) is ~0.49 for Raja and ~0.45 for Cao2018 — roughly 32pp below normal blink performance.

**Root cause:** The algorithm was designed for typical blinks (~100–300 ms). Long blinks (eye closures, drowsiness) span multiple epochs, causing undersegmentation.

**Lesson:** If the application requires detecting long blinks or eye closures, a separate detector with a longer epoch window and different threshold strategy is needed. Consider training a dedicated "long blink" classifier or applying a merging step to detected short blinks.

---

## 13. Naming Conventions Must Be Established Before Running Experiments

**Problem:** Without a consistent naming convention, results from different scripts cannot be compared or cited in a paper. The `condition` column in early scripts used free-form strings like `"frontal|any|median|E9"`.

**Fix:** Standardise on `proposed_<center>_<selection>_<channel>` (e.g., `proposed_median_frontal_e9`). This is unambiguous, sortable, and directly maps to the paper's table rows.

**Lesson:** Define your naming convention before writing the first experiment script. Put it in a shared constants file (`exp_constants.py`) so all scripts use the same format.

---

## 14. Summary Tables as Ground Truth: Write Them Early

**Lesson:** After each experiment round, immediately write a benchmark ground truth document (like `BENCHMARK_GROUND_TRUTH.md`) with the exact numeric results. This serves as:
- A regression test target for any future refactoring
- A quick reference when writing the paper
- Context for any LLM agent asked to refactor or extend the code

Include the exact parameter settings (epoch duration, std threshold, N_JOBS, etc.) so results are reproducible.
