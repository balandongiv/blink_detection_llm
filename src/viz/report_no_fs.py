# Create an HTML report from BlinkDetector outputs using MNE Report
import mne
import pandas as pd
from html import escape


def make_blink_report(
    *,
    fig_data: list[dict],
    ch: str,
    number_good_blinks: int,
    ch_selected=None,
    blink_details: "pd.DataFrame | None" = None,
    title: str = "Blink Detection Report",
    out_path: str = "blink_report.html",
    overwrite: bool = True,
) -> str:
    """
    Build a self-contained HTML report from BlinkDetector results.

    Parameters
    ----------
    fig_data : list of dict
        Each dict must contain keys: 'fig', 'blink_quality', 'maxFrames', 'idx_window'.
    ch : str
        Channel used for detection/visualization.
    number_good_blinks : int
        Count of good blinks.
    ch_selected : Any
        Your `ch_selected` object; shown as text in the summary.
    blink_details : pd.DataFrame, optional
        Per-blink metrics table (will be rendered in the report if provided).
    title : str
        Report title.
    out_path : str
        Output HTML file path.
    overwrite : bool
        Overwrite the output file if it exists.

    Returns
    -------
    str
        Path to the written HTML file.
    """
    report = mne.Report(title=title)

    # ---------- Summary (HTML) ----------
    ch_sel_str = escape(str(ch_selected))
    summary_html = f"""
    <h3>Summary</h3>
    <ul>
      <li><b>Primary channel:</b> {escape(str(ch))}</li>
      <li><b># Good blinks:</b> {int(number_good_blinks)}</li>
      <li><b>Selected channel(s):</b> <code>{ch_sel_str}</code></li>
    </ul>
    """
    report.add_html(title="Summary", html=summary_html, section="Overview")

    # ---------- Optional table ----------
    if blink_details is not None:
        if not isinstance(blink_details, pd.DataFrame):
            try:
                blink_details = pd.DataFrame(blink_details)
            except Exception:
                blink_details = None
        if blink_details is not None and not blink_details.empty:
            # Lightly limit huge tables while preserving all rows via details/summary
            html_table_full = blink_details.to_html(
                border=0, classes="dataframe compact", escape=False
            )
            html_table = f"""
            <details open>
              <summary><b>Blink details table</b> (rows: {len(blink_details)})</summary>
              {html_table_full}
            </details>
            """
            report.add_html(title="Blink details", html=html_table, section="Overview")

    # ---------- Figures ----------
    for i, entry in enumerate(fig_data):
        fig = entry.get("fig", None)
        if fig is None:
            continue
        bq = entry.get("blink_quality", "Unknown")
        mf = entry.get("maxFrames", "NA")
        idx_window = entry.get("idx_window", [])
        win_txt = (
            f"[{idx_window[0]} … {idx_window[-1]}] ({len(idx_window)} samples)"
            if len(idx_window)
            else "NA"
        )

        caption = f"Quality: {bq} | Max frame: {mf} | Window: {win_txt}"
        # add_figure will embed a PNG snapshot of the Matplotlib figure
        report.add_figure(
            fig=fig,
            title=f"Blink {i:03d}",
            caption=caption,
            section=f"Blinks · channel {ch}",
            image_format="png",
            tags=("blink", str(ch)),
        )

    # ---------- Save ----------
    report.save(out_path, overwrite=overwrite, open_browser=False)
    return out_path
