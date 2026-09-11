"""Shared colour palette and axis styling for every manuscript figure.

Fixed palette matching the processing-pipeline flowchart. Every figure must use only
these nine colours — no other hex values — and categorical assignments are chosen so
that colours sitting side by side (e.g. frontal vs. central, Proposed-Mean vs.
Proposed-Med) are different enough in hue that no hatch/pattern is needed to tell
them apart.
"""
from __future__ import annotations

import matplotlib.pyplot as plt

NAVY = "#1F427E"        # dark navy — headings / title bars
EEG_BLUE = "#4456A6"     # EEG waveform / primary blue
PANEL_BLUE = "#8497B8"   # medium blue panel background
LIGHT_BLUE = "#ECF3FA"   # light blue panel background
PAGE_BG = "#F9FBFE"      # very light page background
YELLOW = "#FEF2CE"       # candidate-epoch yellow
CORAL = "#F8A899"        # blink-region coral
GREEN = "#6EB093"        # threshold green
LAVENDER = "#C3C6E4"     # light lavender

#: Coarse scalp-region colours. Frontal and central sit next to each other in every
#: figure that uses them, so they are given the two most different hues in the
#: palette (navy vs. coral) rather than the two blues.
REGION_COLORS = {
    "frontal": NAVY,
    "central": CORAL,
    "parietal": GREEN,
    "occipital": LAVENDER,
    # Electrodes outside the four curated regions (midline sites, edge sites, and, on
    # Cao2018, the A1/A2 mastoid references) — only used by all-electrode figures that
    # plot every full-montage channel rather than the four-region subset above.
    "midline_or_outside": YELLOW,
    "unassigned": EEG_BLUE,
}

#: Two-corpus comparisons (Internal vs. Cao2018).
DATASET_COLORS = {"Internal": NAVY, "Cao2018": CORAL}

#: Four-condition strategy comparisons (BLINKER-concat, MNE-annot, Proposed-Mean,
#: Proposed-Med). Proposed-Mean and Proposed-Med are the two most closely related
#: strategies and are drawn side by side, so they get navy vs. lavender rather than
#: the two blues.
CONDITION_COLORS = {
    "BLINKER-concat": CORAL,
    "MNE-annot": GREEN,
    "Proposed-Mean": LAVENDER,
    "Proposed-Med": NAVY,
}

#: Font sizes used consistently across every manuscript figure (see the
#: manuscript-figure-typography skill/standard). "Chrome" is every structural text
#: element that frames the data: figure/panel titles (incl. ``fig.suptitle``), axis
#: labels, tick labels, and legend text -- these are always the same size so every
#: figure reads at the same scale and no legend looks "louder" than its own axis
#: labels. "In-plot" is any text drawn over the data itself -- bar-value labels,
#: per-point annotations, significance markers, in-plot group headers -- one size
#: smaller than chrome so it stays visually subordinate to the data it annotates
#: instead of competing with it. Neither tier may exceed 10pt; import these two
#: constants rather than hardcoding a third value.
FONT_CHROME = 10
FONT_INPLOT = 8


def style_fig(fig: plt.Figure) -> None:
    """Page background matching the flowchart cards."""
    fig.patch.set_facecolor(PAGE_BG)


def style_axis(ax: plt.Axes, *, grid_axis: str = "y") -> None:
    """Apply the shared navy-on-light-blue look to one axes, including the shared
    chrome font size (title/axis-label/tick-label) -- see FONT_CHROME/FONT_INPLOT."""
    ax.set_facecolor(LIGHT_BLUE)

    if grid_axis in ("y", "both"):
        ax.yaxis.grid(True, linestyle="--", linewidth=0.6, alpha=0.6, color=PANEL_BLUE)
    if grid_axis in ("x", "both"):
        ax.xaxis.grid(True, linestyle="--", linewidth=0.6, alpha=0.6, color=PANEL_BLUE)
    ax.set_axisbelow(True)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(PANEL_BLUE)
    ax.spines["bottom"].set_color(PANEL_BLUE)

    ax.tick_params(axis="both", colors=NAVY, labelsize=FONT_CHROME)
    ax.xaxis.label.set_color(NAVY)
    ax.yaxis.label.set_color(NAVY)
    ax.xaxis.label.set_size(FONT_CHROME)
    ax.yaxis.label.set_size(FONT_CHROME)
    if ax.get_title():
        ax.title.set_color(NAVY)
        ax.title.set_size(FONT_CHROME)
