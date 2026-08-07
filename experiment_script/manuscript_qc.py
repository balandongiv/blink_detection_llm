"""Pre-submission QC for the manuscript.

Checks that are cheap to run and expensive to miss:

1. **LaTeX hazards in prose** — an unescaped ``_`` or ``%`` outside math mode compiles to
   a "Missing $ inserted" error or silently swallows the rest of the line. Session
   identifiers such as ``S34_20190122_044130_3`` are the usual source.
2. **Undefined references and citations** — read from ``main.log`` after a build.
3. **Artifact coverage** — every table and figure has a live generator and an existing
   output file (delegated to ``reproduce_manuscript.py check``).
4. **Stale provenance** — no manuscript file may cite ``runs/``, ``runs0/`` or
   ``runs_second_iteration/`` as its source; the published numbers come only from
   ``publication_results/``.

Run inside conda env ``double_threshold_algo``:

    python experiment_script/manuscript_qc.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WRITING = REPO / "writing"
SCRIPTS = REPO / "experiment_script"

#: Directories that must never appear as a source in a manuscript file.
STALE_SOURCES = ("runs_second_iteration/", "runs0/", "runs/exp")

#: Prose lives in these paragraph directories; tables are generated and already escaped.
PROSE_GLOBS = ("e_result/*/paragraph.tex", "f_discussion/*/paragraph.tex",
               "b_intro/*/paragraph.tex", "c_literature_review/*/paragraph.tex",
               "a_abstract/abstract.tex", "g_conclusion/*.tex")


def prose_only(text: str) -> str:
    """Reduce a file to the running prose a reader sees.

    Math mode, whole-line comments, and LaTeX command arguments are all removed, because
    an underscore is perfectly legal inside ``\\ref{tab:exp1_main}`` or a ``%`` comment.
    What is left is text mode, where an unescaped ``_`` breaks the build and an unescaped
    ``%`` silently swallows the rest of the line.
    """
    text = re.sub(r"(?m)^\s*%.*$", " ", text)              # whole-line comments
    text = re.sub(r"\\\[.*?\\\]", " ", text, flags=re.S)   # display math
    text = re.sub(r"(?<!\\)\$[^$]*\$", " ", text)          # inline math
    # Commands with braced arguments: \ref{...}, \input{...}, \citep{...}, \label{...}.
    text = re.sub(r"\\[a-zA-Z@]+\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})*", " ", text)
    return text


def check_latex_hazards() -> int:
    problems = 0
    for pattern in PROSE_GLOBS:
        for path in sorted(WRITING.glob(pattern)):
            body = prose_only(path.read_text(encoding="utf-8"))
            for symbol, label in ((r"_", "UNESCAPED _"), (r"%", "UNESCAPED %")):
                for m in re.finditer(rf"(?<!\\){re.escape(symbol)}", body):
                    start = max(0, m.start() - 45)
                    context = " ".join(body[start:m.start() + 25].split())
                    print(f"{label}   {path.relative_to(WRITING)}: ...{context}...")
                    problems += 1
    return problems


def check_log() -> int:
    log = WRITING / "main.log"
    if not log.exists():
        print("NO main.log — build the manuscript first")
        return 1
    text = log.read_text(encoding="utf-8", errors="replace")
    problems = 0
    for kind in ("Reference", "Citation"):
        for m in re.finditer(rf"LaTeX Warning: {kind} `([^']+)' undefined", text):
            print(f"UNDEFINED {kind.upper()}: {m.group(1)}")
            problems += 1
    for m in re.finditer(r"^! (.+)$", text, re.M):
        print(f"LATEX ERROR: {m.group(1)}")
        problems += 1
    return problems


def check_stale_sources() -> int:
    problems = 0
    for path in sorted(WRITING.rglob("*.tex")):
        if "obs" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for stale in STALE_SOURCES:
            if stale in text:
                print(f"STALE SOURCE  {path.relative_to(WRITING)}: mentions {stale!r}")
                problems += 1
    return problems


def check_artifacts() -> int:
    r = subprocess.run([sys.executable, str(SCRIPTS / "reproduce_manuscript.py"), "check"],
                       cwd=REPO, capture_output=True, text=True)
    print(r.stdout.strip())
    return r.returncode


def main() -> None:
    total = 0
    for name, fn in [("LaTeX hazards in prose", check_latex_hazards),
                     ("Build log", check_log),
                     ("Stale data provenance", check_stale_sources),
                     ("Artifact coverage", check_artifacts)]:
        print(f"\n=== {name} ===")
        n = fn()
        total += n
        if not n:
            print("ok")
    print(f"\n{'PASS' if not total else f'{total} problem(s) found'}")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
