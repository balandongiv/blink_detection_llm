"""Redraft the two Experiment 3 paragraphs whose numbers the epoch-duration fix changed.

Restricting ``tab13_fig10_epoch_duration.py`` to the ``all_channel`` gate changed every
value in the epoch-duration table and, with them, the conclusions the prose drew: pooled
performance now differs from the 30-second reference at no duration, while Raja differs
at 50, 60 and 120 seconds. The previous claim that 10--60 seconds was a uniformly safe
range is no longer supported, so these paragraphs are redrafted against the corrected
packet rather than patched.

    python experiment_script/exp3_redraft_prose.py

Run inside conda env ``double_threshold_algo``, after the chatgpt-ui-reasoning smoke gate.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / "agent-skillbook" / "skills"
sys.path.insert(0, str(SKILLS / "chatgpt-ui-reasoning" / "resources"))
sys.path.insert(0, str(SKILLS / "academic-latex-writer" / "resources"))
import chatgpt_ui_session  # noqa: E402,F401
from paragraph_writer import Paragraph, draft_all  # noqa: E402

WRITING = REPO / "writing"
PACKETS = WRITING / "e_result" / "exp3" / "_packets"
BIBS = (WRITING / "references_from_csv.bib", WRITING / "references_scopus_new.bib")

COMMON = """
Write British spelling, plain declarative academic prose, past tense. Refer to the two
corpora as Raja and Cao2018 and to the detector as Proposed-Med. Write F1 as $F_1$ and
p-values as $p=0.002$; for a p-value below 0.001 write $p<0.001$ and never $p=0.000$.
Available cross-references (use only these): Table~\\ref{tab:epoch_duration},
Figure~\\ref{fig:f1_by_epoch}.
"""

RESULT = Paragraph(
    "r3_epoch_duration", packets=["pk_epoch_duration"],
    task=COMMON + """
Write the RESULTS paragraph reporting the epoch-duration sweep.

Content it must carry:
- Pooled performance was stable: give the pooled spread across the seven durations and
  state that no duration differed significantly from the 30-second reference after
  correction, giving the smallest corrected p-value to support it.
- Cao2018 was likewise stable with no significant difference at any duration; give its
  spread.
- Raja was NOT uniformly stable: it differed significantly from the reference at 50, 60
  and 120 seconds. Give those values and corrected p-values. Do not soften this and do
  not describe 10--60 seconds as a uniformly safe range - the 50 and 60 second results
  contradict that.
- On Raja the 30-second reference was the best of the seven durations; on Cao2018 the
  longest duration was nominally best but not significantly so.
- Reference Table~\\ref{tab:epoch_duration} and Figure~\\ref{fig:f1_by_epoch}.
- This is a Results paragraph: report, do not interpret.
""",
)

DISCUSSION = Paragraph(
    "d7_epoch_stability", packets=["pk_epoch_duration"],
    task=COMMON + """
Write the DISCUSSION paragraph interpreting the epoch-duration sweep.

Content it must carry:
- Pooled across both corpora the pipeline tolerated epoch duration: no duration differed
  significantly from the 30-second reference, and the pooled spread was small.
- Why this matters: epoch duration in driving studies is set by the experimental
  paradigm rather than by the blink detector, so the thresholding procedure must
  tolerate different segmentation choices.
- The exception was corpus-specific. On Raja performance declined significantly at 50,
  60 and 120 seconds, with the largest decline at 120 seconds. Give those numbers.
- A plausible account of the decline: a longer epoch is more likely to contain both
  blink and blink-free signal, so its summary amplitude becomes less representative of
  either state and the screening stage is diluted - the same dilution the pipeline was
  designed to avoid by estimating the threshold from screened epochs. Present this as an
  interpretation, not as something the data proves.
- State honestly that because Raja declined at 50 and 60 seconds as well, the safe
  operating range indicated by these data is narrower than the full tested range, and
  the 30-second setting is the one supported on both corpora.
""",
    position="follows the cross-dataset discussion paragraph",
)


def main() -> None:
    draft_all([RESULT], packet_dir=PACKETS, out_dir=WRITING / "e_result", bib_paths=BIBS,
              transcripts=WRITING / "e_result" / "exp3" / "_transcripts", resume=False)
    draft_all([DISCUSSION], packet_dir=PACKETS, out_dir=WRITING / "f_discussion",
              bib_paths=BIBS,
              transcripts=WRITING / "e_result" / "exp3" / "_transcripts", resume=False)


if __name__ == "__main__":
    main()
