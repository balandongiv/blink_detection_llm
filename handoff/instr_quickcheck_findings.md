# instr.md Quick Check — Findings

**Date:** 2026-06-12
**Scope:** Review/fix `instr.md`, then a *minimal* runtime check of the three execution paths
(ChatGPT UI runner, Terminal Codex runner, GROBID) before the full sweep.
**Verdict:** 🟡 **Mostly ready.** GROBID and Codex are good. The ChatGPT UI runner is
authenticated and reachable but currently **flaky** (Cloudflare challenge + a generation error
on live calls). Plan defects found were fixed.

---

## 1. Plan fixes applied to `instr.md` and authoritative files

| # | File | Problem | Fix |
|---|------|---------|-----|
| 1 | `instr.md` §5 | Tutorial paths were doubled: `tutorial/tutorial/40_exp1_...py`. Actual files live at `tutorial/40_*.py`. | Removed the duplicated `tutorial/` prefix from all six entries. |
| 2 | `instruction_agentic/model_selection.md` | Still referenced **`Hakim2029`** (3×: "Raja/Hakim2029 comparison scripts", "contradictions between Raja and Hakim2029", "Raja/Hakim2029 comparison"). Directly violates instr.md §3. | Replaced all with **`Murat2018`**. |
| 3 | `writing/latex_writing_rule.md` | Still used **`hakim2029`** folder names (`p003_hakim2029_result`, `p004_hakim2029_rerun_note`, etc.) and `Hakim2029` prose. Violates §3; these are declared "authoritative" by §2, so the contradiction is material. | Replaced all `hakim2029`→`murat2018` and `Hakim2029`→`Murat2018`. |

**Verified:** the only remaining "Hakim" strings in the plan are the two §3 prohibition lines in
`instr.md` (expected).

---

## 2. Referenced instruction files — existence check (instr.md §2)

All five required local instruction files are present:

| File | Status |
|------|--------|
| `academic_paper_maker/README_CHATGPT_MCP.md` | ✅ |
| `academic_paper_maker/README_GROBID_MCP.md` | ✅ |
| `instruction_agentic/model_selection.md` | ✅ |
| `instruction_agentic/prompt/pdf_reader_prompt.md` | ✅ |
| `writing/latex_writing_rule.md` | ✅ |

Per §2 rule 5, no task should be `blocked` on a missing instruction file.

---

## 3. Runtime checks — the three execution paths

### 3a. GROBID — ✅ working (after restart)
- Initial state: `http://localhost:8070/api/isalive` → no response. Container
  `academic_paper_maker_grobid` existed but had **Exited (255)** ~34 min earlier.
- Docker daemon running; image `grobid/grobid:0.8.1` present (19.8 GB).
- Action: `docker start academic_paper_maker_grobid`. API became alive (`true`) after ~15 s.
- **Left running** for the upcoming sweep.

### 3b. Terminal Codex runner — ✅ working
- `codex` on PATH at `C:\Users\balan\AppData\Roaming\npm\codex`, version **codex-cli 0.139.0**.
- `codex login status` → **"Logged in using ChatGPT"** (exit 0).
- Model/effort policy file (`instruction_agentic/model_selection.md`) present and now Hakim-free.

### 3c. ChatGPT UI runner — 🟡 reachable & authenticated, but flaky
Prerequisites all present: `test_chatgpt_session.py`, Selenium profile
`C:\selenium\chatgpt-profile\Default`, `chrome.exe`, Python `selenium 4.44.0` + `webdriver_manager`.

Ran the authoritative smoke test (`python test_chatgpt_session.py`) three times:

| Run | Page title | Result |
|-----|-----------|--------|
| 1 | `ChatGPT` (home — session valid) | Prompt inserted & submitted, but model replied **"Something went wrong while generating the response…"** (server-side generation error). Script still printed SUCCESS because it only checks that *an* assistant message returned. |
| 2 | — | **chromedriver startup crash** (transient). |
| 3 | `Just a moment...` | **Cloudflare bot challenge**; textarea never appeared → `TimeoutException`. |

**Interpretation:** the cookie/session is valid (run 1 loaded the real home screen, not a login
page). The failures are not auth failures — they are (a) a transient ChatGPT generation error and
(b) a Cloudflare interstitial that appears under rapid repeated automated hits. I stopped after
run 3 to avoid escalating the bot challenge.

**Caveat on the smoke test itself:** `test_chatgpt_session.py` reports SUCCESS as long as any
assistant element is found — so it passed run 1 even though the actual content was an error
message. For the sweep, the runner wrapper should treat
`"Something went wrong while generating"` and a `Just a moment...` title as **failures** and back
off/retry, not as valid output.

---

## 4. Recommendations before the full sweep

1. **ChatGPT runner hardening (highest priority).** Add response guards that detect and retry on:
   - title `Just a moment...` (Cloudflare) → back off (10–30 s), single Selenium worker only.
   - body `Something went wrong while generating the response` → retry.
   The existing `send_with_retry` wrapper (README §5.4) covers transient cases but does not yet
   inspect *content*. Do not run multiple Selenium workers against the one shared profile.
2. **Keep GROBID warm.** It exited once already; add an isalive precheck + auto `docker start` at
   sweep startup so PDF extraction doesn't fail mid-run.
3. **Path-namespace inconsistency in instr.md (not yet fixed — decision needed).** The plan mixes
   `paper/sections/...` (§10.1, §12, §19 `paper/references.bib`) with `writing/...` (§5 config,
   `latex_writing_rule.md`, §8). Pick one root (the LaTeX rule and §5 favor `writing/`) and make
   §10.1/§12/§19 consistent so agents emit files to one tree. Flagged rather than auto-fixed
   because it changes the output contract for several agents.
4. **Runner naming.** §1/§18 call path A the "ChatGPT UI/API-connected runner", but
   `README_CHATGPT_MCP.md` is **Selenium-UI only** (no API path). Either add the API path or drop
   "/API" to avoid implying an unavailable capability.

---

## 5. Summary

- Plan defects fixed: tutorial path doubling + all stray `Hakim2029` references (now `Murat2018`).
- GROBID: ✅ started, alive on `:8070`.
- Codex CLI: ✅ installed (0.139.0), logged in.
- ChatGPT UI: 🟡 authenticated and driveable, but hitting Cloudflare/generation errors under
  repeated calls — needs content-aware retry/back-off before a batch sweep.
- Open items for you to decide: `paper/` vs `writing/` root, and the "/API" runner label.
