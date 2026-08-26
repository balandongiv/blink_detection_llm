"""Audit the drafted Experiment 1 paragraphs before they are wired into the build.

Three checks the ChatGPT UI loop cannot make for itself:

1. **LaTeX hazards** — an unescaped ``%`` silently deletes the rest of a line from the
   PDF, and a bare ``_`` in text mode fails the build with "Missing $ inserted". The UI
   reproduces packet identifiers such as ``fp1_only`` verbatim, so this fires often.
2. **Cross-paragraph repetition** — several paragraphs share the design packet, so the
   model tends to restate its scope note in each of them. Neither the number gate nor
   the preservation gate can see across files.
3. **Reference targets** — every ``\\ref`` must resolve against a label that exists in
   the section, because a dropped colon compiles to a silent "??".

    python experiment_script/exp1_check_prose.py

Exit code is non-zero if any check fails, so it can gate a build.
"""
from __future__ import annotations

import difflib
import re
import sys
from itertools import combinations
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "agent-skillbook" / "skills" / "academic-latex-writer"
                      / "resources"))
from prose_gates import check_latex_hazards, refs_in  # noqa: E402

EXP1 = REPO / "writing" / "e_result" / "exp1"
SEC = EXP1 / "sec.tex"
#: Labels defined outside sec.tex that the paragraphs may legitimately point at.
EXTERNAL_LABELS = {
    "sec:exp2_strategy", "sec:exp3_epoch", "sec:datasets", "sec:method", "sec:eval",
    "sec:metrics", "sec:exp_setup", "tab:exp1_main",
}
SIMILARITY = 0.80


def paragraphs() -> dict[str, str]:
    return {p.parent.name: p.read_text(encoding="utf-8")
            for p in sorted(EXP1.glob("p*/paragraph.tex"))}


def sentences(text: str) -> list[str]:
    flat = re.sub(r"\s+", " ", text).strip()
    return [s.strip() for s in re.split(r"(?<=[.])\s+(?=[A-Z])", flat) if len(s) > 60]


def known_labels() -> set[str]:
    """Labels defined in sec.tex plus every label in the \\input-ed table fragments."""
    text = SEC.read_text(encoding="utf-8")
    labels = set(re.findall(r"\\label\{([^}]*)\}", text))
    for m in re.finditer(r"\\input\{e_result/([^}]*)\}", text):
        frag = REPO / "writing" / "e_result" / (m.group(1) + ".tex")
        if frag.exists():
            labels |= set(re.findall(r"\\label\{([^}]*)\}",
                                     frag.read_text(encoding="utf-8")))
    for fig in re.finditer(r"\\label\{(fig:[^}]*)\}", text):
        labels.add(fig.group(1))
    return labels | EXTERNAL_LABELS


def main() -> int:
    paras = paragraphs()
    if not paras:
        print("no paragraphs found — has the draft run completed?")
        return 1
    failures = 0

    print(f"== LaTeX hazards ({len(paras)} paragraphs)")
    for name, text in paras.items():
        gate = check_latex_hazards(text)
        if not gate:
            failures += 1
            print(f"  FAIL {name}: {gate.detail}")
            for item in gate.offending:
                print(f"        {item}")
    if not failures:
        print("  ok")

    print("\n== Cross-paragraph repetition")
    repeats = 0
    for (a_name, a_text), (b_name, b_text) in combinations(paras.items(), 2):
        for s_a in sentences(a_text):
            for s_b in sentences(b_text):
                ratio = difflib.SequenceMatcher(None, s_a, s_b).ratio()
                if ratio >= SIMILARITY:
                    repeats += 1
                    print(f"  {a_name} <-> {b_name}  (similarity {ratio:.2f})")
                    print(f"     {s_a[:150]}")
                    print(f"     {s_b[:150]}")
    if not repeats:
        print("  ok")

    print("\n== Reference targets")
    labels, bad = known_labels(), 0
    for name, text in paras.items():
        for target in sorted(refs_in(text)):
            if target not in labels:
                bad += 1
                failures += 1
                print(f"  FAIL {name}: \\ref{{{target}}} resolves to no label")
    if not bad:
        print("  ok")

    print(f"\nhazard/reference failures = {failures}; repeated sentences = {repeats}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
