"""Draft the Experiment 1 channel-subset prose through the ChatGPT UI, one file each.

Implements the ``academic-latex-writer`` loop for this section: one fresh chat per
paragraph, an evidence packet as the only permitted source of numbers, a mechanical
gate before installation, and a separate structural revision pass.

    python experiment_script/exp1_draft_prose.py draft     # one chat per paragraph
    python experiment_script/exp1_draft_prose.py revise    # structural pass

Both commands are resumable: ``draft`` skips paragraphs that already hold real prose,
so a run cut short by the UI's per-session send limit is simply re-run.

Run inside conda env ``double_threshold_algo``, after the chatgpt-ui-reasoning smoke gate.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / "agent-skillbook" / "skills"

# Import the session class from THIS repo's skillbook copy first: paragraph_writer
# hardcodes a path to another checkout, and whichever lands in sys.modules first wins.
sys.path.insert(0, str(SKILLS / "chatgpt-ui-reasoning" / "resources"))
sys.path.insert(0, str(SKILLS / "academic-latex-writer" / "resources"))
import chatgpt_ui_session  # noqa: E402,F401  - pins the local copy in sys.modules
from paragraph_writer import Paragraph, draft_all, revise_for_structure  # noqa: E402

OUT_DIR = REPO / "writing" / "e_result" / "exp1"
PACKETS = OUT_DIR / "_packets"
BIBS = (REPO / "writing" / "references_from_csv.bib",
        REPO / "writing" / "references_scopus_new.bib")
CITEABLE = (REPO / "writing" / "CITEABLE_KEYS.txt").read_text(encoding="utf-8")

#: Cross-reference labels that exist in the document. The model is told to use only
#: these, because a dropped or invented label compiles to a silent "??" in the PDF.
LABELS = """Available cross-reference labels (use \\ref{} with ~ before it; use ONLY these):
  tab:egi_map                  - EGI 128 to 10--20 channel map
  tab:exp1_channel_ablation    - per-electrode precision/recall/F1, both datasets
  tab:region_performance       - per-electrode results collapsed to coarse scalp regions
  tab:exp1_subset_summary      - channel subsets vs the full montage, with statistics
  tab:exp1_solo_vs_montage     - single electrode vs the same electrode in the full montage
  tab:channel_selection        - best-channel selection frequencies
  tab:channel-robustness       - agreement on the best channel across the four conditions
  fig:region_performance       - per-electrode F1 bar chart coloured by scalp region
  fig:exp1_region_boxplot      - session-level F1 by channel-selection group
  fig:exp1_single_channel      - session-level F1 for the single-electrode subsets
  fig:exp1_coverage_curve      - F1 against the number of electrodes given to the pipeline
  fig:channel_selection        - best-channel selection frequency chart
  sec:exp2_strategy            - Experiment 2
  sec:exp3_epoch               - Experiment 3"""

COMMON = """
This paragraph belongs to the Results section of the article. Report what was observed;
do not interpret, do not speculate about mechanisms beyond what the packet states, and do
not discuss implications for the field - those belong to the Discussion.
Write British spelling. Refer to the two corpora as Raja and Cao2018.
Write the detector as Proposed-Med. Write F1 as $F_1$ and p-values as $p=0.012$.
"""

PLAN = [
    Paragraph(
        "p01_motivation", packets=[],
        position="opens the Experiment 1 subsection and has no preceding paragraph",
        task=COMMON + """
Write the MOTIVATION paragraph for an experiment called the EEG channel-subset analysis.

Content it must carry:
- Blink artefacts project most strongly over frontal scalp sites, so a detector may not
  need a dense montage; how much of the montage is actually required is unknown.
- The pipeline's Stage A screens epochs with a union rule over the channels it is given,
  so the set of channels determines which epochs reach Stage B. Restricting the channel
  set therefore changes the detector itself, not merely the signal it is shown.
- Consequently each channel subset must be re-run end to end rather than evaluated by
  hiding channels from a single trained detector.
- The question the experiment answers is whether a reduced electrode set is SUFFICIENT
  for the task.

This paragraph must contain NO numeric values at all.
Do not use any \\ref{} in this paragraph.
""",
    ),
    Paragraph(
        "p02_design", packets=["pk_design"],
        task=COMMON + LABELS + """

Write the DESIGN paragraph.

Content it must carry:
- What was run: the complete Stage A to Stage C pipeline on each channel subset
  separately, on both corpora, at 30-second epochs with the median centre.
- How many subsets, of which kinds, and how many sessions per corpus.
- The aggregation rule (best-channel-per-session, then averaged over sessions) and the
  statistical treatment (two-tailed Wilcoxon signed-rank against the full montage,
  Bonferroni correction, rank-biserial effect size).
- A plain statement of scope: this design measures whether a subset is sufficient on its
  own; it is not a leave-one-region-out analysis and does not establish that any region
  is necessary to the complete system. State this limitation directly, do not soften it.
- Mention that Raja electrodes are reported by their 10--20 scalp location, with the
  native EGI index given in Table~\\ref{tab:egi_map}.
""",
    ),
    Paragraph(
        "p03_reference", packets=["pk_design", "pk_reference"],
        task=COMMON + LABELS + """

Write the paragraph reporting the FULL-MONTAGE REFERENCE CONDITION.

Content it must carry:
- The full montage is the reference every subset is measured against, because it assumes
  no prior knowledge of where blinks project.
- Its precision, recall and $F_1$ on both corpora.
- That this condition is identical to the Proposed-Med condition of Experiment 2 and to
  the 30-second condition of Experiment 3 - not merely equal on average, but identical
  session by session on all sessions of both corpora. Report the session counts and that
  the maximum absolute difference was zero. Reference Section~\\ref{sec:exp2_strategy}
  and Section~\\ref{sec:exp3_epoch}.
- That this is the configuration carried unchanged into those experiments.
""",
    ),
    Paragraph(
        "p04_per_electrode", packets=["pk_design", "pk_per_electrode"],
        task=COMMON + LABELS + """

Write the paragraph reporting PER-ELECTRODE detection under the full-montage gate.

Content it must carry:
- Detection quality was concentrated at the frontopolar pair rather than spread over the
  frontal region: give Fp1 and Fp2 on both corpora, then the fall-off at the neighbouring
  frontal sites, then the floor value reached by the worst electrode on each corpus.
- Reference Table~\\ref{tab:exp1_channel_ablation}, Table~\\ref{tab:region_performance}
  and Figure~\\ref{fig:region_performance}.
- One observation the reader should notice: on Raja the two central electrodes C3 and C4
  behaved very differently from each other, whereas on Cao2018 C3 and C4 were close
  together. Report the four values and note the asymmetry is specific to Raja. Do not
  explain it; simply report it.

IMPORTANT: these are per-electrode values measured inside the 32-channel run, where
Stage A screened epochs using every electrode. Describe them that way. Do NOT call them
single-electrode or single-channel results - a separate analysis covers those.
""",
    ),
    Paragraph(
        "p05_regional", packets=["pk_design", "pk_regional"],
        task=COMMON + LABELS + """

Write the paragraph reporting the ANATOMICAL CHANNEL SUBSETS against the full montage.

Content it must carry:
- The frontal subset matched the full montage on both corpora: give its $F_1$, the
  paired difference, and the corrected p-value on each corpus.
- After Bonferroni correction the left and right frontal halves were also statistically
  indistinguishable from the full montage on Raja, and on Cao2018 only the right frontal
  half differed. Give those p-values. Be precise: report exactly which subsets were not
  significantly different after correction.
- Performance then fell steeply and significantly for every central, parietal, occipital
  and posterior subset. Give representative values and note that these differences were
  significant with large effect sizes.
- Reference Table~\\ref{tab:exp1_subset_summary} and
  Figure~\\ref{fig:exp1_region_boxplot}.
""",
    ),
    Paragraph(
        "p06_failure_mode", packets=["pk_design", "pk_failure"],
        task=COMMON + LABELS + """

Write the paragraph reporting HOW the non-frontal subsets failed.

Content it must carry:
- The failure was asymmetric between precision and recall: on Cao2018 the posterior
  subsets retained moderate precision while recall collapsed. Give the numbers.
- On Raja both precision and recall fell. Give the numbers. Do not describe the two
  corpora as behaving the same way.
- The Stage-B blink-region threshold, a sample-level detector parameter, differed
  markedly between subsets. On Cao2018 it decreased from the frontopolar subsets to the
  occipital subsets; give those values.
- CRITICAL HONESTY REQUIREMENT: Raja did NOT show that ordering - its central-right
  subset carried the highest threshold of any subset yet reached one of the lowest $F_1$
  values. State this plainly as a divergence between the corpora. Do NOT claim a single
  threshold-based mechanism that holds on both corpora, and do NOT soften the divergence.
- Reference Table~\\ref{tab:exp1_subset_summary}.
""",
    ),
    Paragraph(
        "p07_single_channel", packets=["pk_design", "pk_single"],
        task=COMMON + LABELS + """

Write the paragraph reporting SINGLE-ELECTRODE operation.

Content it must carry:
- The complete pipeline run on one frontopolar electrode retained most of the
  full-montage performance: give the $F_1$ of the best single electrode on each corpus
  and the percentage of the full-montage reference it represents.
- These single-electrode values involve no channel selection at all, so unlike every
  other condition in the article they carry no best-channel-per-session oracle. State
  this explicitly - it makes them the values a deployed single-electrode system would
  produce.
- Performance dropped sharply for single electrodes outside the frontopolar pair; give
  the values.
- Reference Figure~\\ref{fig:exp1_single_channel}.
""",
    ),
    Paragraph(
        "p08_montage_contribution", packets=["pk_design", "pk_contribution"],
        task=COMMON + LABELS + """

Write the paragraph reporting WHAT THE REST OF THE MONTAGE CONTRIBUTED.

Content it must carry:
- This is the one comparison in the experiment that removes channels from the complete
  system rather than testing a subset on its own: each electrode was scored alone and
  again inside the full 32-channel run, on the same sessions.
- At Fp1 and Fp2 the other electrodes produced no significant gain on either corpus.
  Give the differences and the corrected p-values.
- At every weaker electrode the gain was significant. Give the differences and corrected
  p-values, and note that the gain appeared in recall rather than precision.
- Reference Table~\\ref{tab:exp1_solo_vs_montage}.
""",
    ),
    Paragraph(
        "p09_position_vs_count", packets=["pk_design", "pk_coverage"],
        task=COMMON + LABELS + """

Write the paragraph reporting SUBSET SIZE against performance.

Content it must carry:
- The number of electrodes given to the pipeline predicted performance poorly; where
  they sat on the scalp predicted it well.
- Support this with the comparison of one frontopolar electrode against the much larger
  central and posterior subsets on both corpora.
- Give the spread of $F_1$ among the single-electrode subsets on each corpus, to show
  how much variation occurs at a fixed subset size.
- Reference Figure~\\ref{fig:exp1_coverage_curve}.
""",
    ),
    Paragraph(
        "p10_selection_frequency", packets=["pk_design", "pk_frequency"],
        task=COMMON + LABELS + """

Write the paragraph reporting WHICH ELECTRODE WAS SELECTED as best.

Content it must carry:
- Selection concentrated on the frontopolar pair, but which of the two won varied.
- Give the Experiment 1 per-session frequencies for the full montage on both corpora.
- Give the frequencies pooled over the four detection conditions of Experiment 2, for
  the most frequently selected electrodes on each corpus.
- Note that the two corpora favoured different members of the pair.
- Reference Table~\\ref{tab:channel_selection} and Figure~\\ref{fig:channel_selection}.
""",
    ),
    Paragraph(
        "p11_oracle_cost", packets=["pk_design", "pk_oracle"],
        task=COMMON + LABELS + """

Write the paragraph reporting THE COST OF THE BEST-CHANNEL-PER-SESSION RULE.

Content it must carry:
- Every condition in the article is reported at its best-channel-per-session operating
  point, which is an oracle; this paragraph quantifies what that rule is worth so the
  headline values can be read against a deployable fixed-electrode alternative.
- For each corpus, give the $F_1$ of the better fixed frontopolar electrode, its mean
  and median shortfall against the per-session oracle, and how many sessions it landed
  within 0.02 of the oracle.
- Give the same for taking the better of the two frontopolar electrodes.
- State plainly that committing to one frontopolar electrode in advance cost only a small
  amount of $F_1$.
""",
    ),
    Paragraph(
        "p12_agreement", packets=["pk_design", "pk_agreement"],
        task=COMMON + LABELS + """

Write the paragraph reporting AGREEMENT ON THE BEST ELECTRODE across detectors.

Content it must carry:
- Whether the four detection conditions of Experiment 2 chose the same best electrode:
  give full agreement and mean pairwise agreement for each corpus and pooled.
- Full agreement on the exact electrode was low. Report that plainly; it is a negative
  result and must not be softened.
- Agreement was highest for Proposed-Med and lowest for MNE-annot; give those values.
- Reference Table~\\ref{tab:channel-robustness}.
""",
    ),
]


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "draft"
    if mode in ("draft", "draft-fresh"):
        draft_all(PLAN, packet_dir=PACKETS, out_dir=OUT_DIR, bib_paths=BIBS,
                  citeable=CITEABLE, transcripts=OUT_DIR / "_transcripts",
                  resume=(mode == "draft"))
    elif mode == "revise":
        revise_for_structure(PLAN, out_dir=OUT_DIR,
                             transcripts=OUT_DIR / "_transcripts_revise")
    else:
        raise SystemExit("usage: exp1_draft_prose.py [draft|draft-fresh|revise]")


if __name__ == "__main__":
    main()
