"""Compare raw-vs-epoch blink regions on the representative seed channel."""

from __future__ import annotations

import argparse
import ast
import os
import pickle
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MNE_HOME = PROJECT_ROOT / ".mne_home"
MNE_HOME.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("_MNE_FAKE_HOME_DIR", str(MNE_HOME))

import matplotlib.pyplot as plt
import mne
import numpy as np
import pandas as pd


SAMPLE_DIR = Path(__file__).resolve().parent
RAW_PATH = SAMPLE_DIR / "1.edf"
EPOCHS_PATH = SAMPLE_DIR / "dev_epo.fif"
PICKLE_PATH = SAMPLE_DIR / "seed_exp01_pyblinker_results_1.pkl"
DEFAULT_IMAGE_PREFIX = "first_blink_raw_vs_epoch"
DEFAULT_REPORT_PREFIX = "raw_vs_epoch_blinks_report"
DEFAULT_PAD_SECONDS = 3.0
DEFAULT_DOWNSAMPLE_HZ = 20.0
DEFAULT_REPORT_MAX_BLINKS_PER_HTML = 200


def _load_seed_results() -> dict:
    with PICKLE_PATH.open("rb") as handle:
        payload = pickle.load(handle)
    if (
        not isinstance(payload, dict)
        or "events" not in payload
        or "selected_channel" not in payload
    ):
        raise ValueError(
            "seed_exp01_pyblinker_results_1.pkl must be a dict with 'events' and 'selected_channel'."
        )
    if not isinstance(payload["events"], pd.DataFrame):
        raise ValueError("seed results field 'events' must be a pandas DataFrame.")
    return payload


def _representative_channel(payload: dict) -> str:
    selected_channel = payload["selected_channel"]
    if (
        not isinstance(selected_channel, pd.DataFrame)
        or selected_channel.empty
        or "ch" not in selected_channel.columns
    ):
        raise ValueError("selected_channel must be a non-empty DataFrame with a 'ch' column.")
    return str(selected_channel.iloc[0]["ch"])


def _as_float_list(value: object) -> list[float]:
    if value is None:
        return []
    if isinstance(value, float) and np.isnan(value):
        return []
    if isinstance(value, str):
        parsed = ast.literal_eval(value)
        if isinstance(parsed, (list, tuple, np.ndarray)):
            return [float(item) for item in parsed]
        return [float(parsed)]
    if isinstance(value, (list, tuple, np.ndarray)):
        return [float(item) for item in value]
    return [float(value)]


def _build_epoch_blink_table(epochs: mne.BaseEpochs) -> pd.DataFrame:
    metadata = epochs.metadata
    if metadata is None or metadata.empty:
        raise ValueError("dev_epo.fif does not contain epoch metadata.")

    rows: list[dict[str, float | int]] = []
    global_index = 1
    for epoch_row_index, row in metadata.iterrows():
        onsets = _as_float_list(row.get("blink_onset"))
        durations = _as_float_list(row.get("blink_duration"))
        raw_onsets = _as_float_list(row.get("raw_blink_onset"))
        raw_ends = _as_float_list(row.get("raw_blink_end"))
        count = min(len(onsets), len(durations))
        if count <= 0:
            continue

        raw_count = min(len(raw_onsets), len(raw_ends))
        for blink_pos in range(count):
            raw_onset = raw_onsets[blink_pos] if blink_pos < raw_count else float("nan")
            raw_end = raw_ends[blink_pos] if blink_pos < raw_count else float("nan")
            epoch_id_value = row.get("epoch_id", epoch_row_index)
            try:
                epoch_id = int(epoch_id_value)
            except (TypeError, ValueError):
                epoch_id = int(epoch_row_index)

            onset_sec = float(onsets[blink_pos])
            duration_sec = float(durations[blink_pos])
            rows.append(
                {
                    "global_blink_index": global_index,
                    "epoch_row_index": int(epoch_row_index),
                    "epoch_id": epoch_id,
                    "epoch_blink_index": blink_pos + 1,
                    "epoch_onset_sec": onset_sec,
                    "epoch_duration_sec": duration_sec,
                    "epoch_end_sec": onset_sec + duration_sec,
                    "raw_onset_sec": float(raw_onset),
                    "raw_end_sec": float(raw_end),
                }
            )
            global_index += 1

    table = pd.DataFrame.from_records(rows)
    if table.empty:
        raise ValueError("No blink rows found in dev_epo.fif metadata.")
    return table


def _selected_raw_blink(events: pd.DataFrame, sfreq: float, blink_index: int) -> dict[str, float]:
    if events.empty:
        raise ValueError("Seed results contain no blink events.")
    if blink_index < 1 or blink_index > len(events):
        raise ValueError(f"raw blink_index must be between 1 and {len(events)}.")
    row = events.iloc[blink_index - 1]
    start_sample = int(row["start_blink"])
    end_sample = int(row["end_blink"])
    onset_sec = (start_sample - 1) / sfreq
    end_sec = (end_sample - 1) / sfreq
    return {
        "raw_blink_index": blink_index,
        "start_sample": start_sample,
        "end_sample": end_sample,
        "onset_sec": onset_sec,
        "end_sec": end_sec,
    }


def _select_epoch_blink_by_global(epoch_blink_table: pd.DataFrame, blink_index: int) -> pd.Series:
    if blink_index < 1 or blink_index > len(epoch_blink_table):
        raise ValueError(
            f"epoch global blink_index must be between 1 and {len(epoch_blink_table)}."
        )
    return epoch_blink_table.iloc[blink_index - 1]


def _select_epoch_blink(epoch_blink_table: pd.DataFrame, args: argparse.Namespace) -> pd.Series:
    by_epoch = args.epoch_id is not None or args.epoch_blink_index is not None
    if by_epoch:
        if args.epoch_id is None or args.epoch_blink_index is None:
            raise ValueError("Use both --epoch-id and --epoch-blink-index together.")
        mask = (epoch_blink_table["epoch_id"] == args.epoch_id) & (
            epoch_blink_table["epoch_blink_index"] == args.epoch_blink_index
        )
        matches = epoch_blink_table.loc[mask]
        if matches.empty:
            epoch_subset = epoch_blink_table.loc[
                epoch_blink_table["epoch_id"] == args.epoch_id
            ]
            if epoch_subset.empty:
                raise ValueError(f"epoch_id {args.epoch_id} not found in dev_epo metadata.")
            max_epoch_blink = int(epoch_subset["epoch_blink_index"].max())
            raise ValueError(
                f"epoch_id {args.epoch_id} has blink indices 1..{max_epoch_blink}; "
                f"got {args.epoch_blink_index}."
            )
        return matches.iloc[0]

    return _select_epoch_blink_by_global(epoch_blink_table, args.blink_index)


def _select_raw_blink_for_epoch(
    epoch_blink: pd.Series,
    events: pd.DataFrame,
    raw_sfreq: float,
) -> dict[str, float]:
    target_onset = float(epoch_blink.get("raw_onset_sec", float("nan")))
    if np.isfinite(target_onset):
        raw_onsets = (events["start_blink"].to_numpy(dtype=float) - 1.0) / raw_sfreq
        raw_index = int(np.argmin(np.abs(raw_onsets - target_onset))) + 1
        return _selected_raw_blink(events, raw_sfreq, raw_index)

    global_index = int(epoch_blink["global_blink_index"])
    fallback_index = min(max(1, global_index), len(events))
    return _selected_raw_blink(events, raw_sfreq, fallback_index)


def _window_indices(
    onset_sec: float,
    end_sec: float,
    sfreq: float,
    n_times: int,
    *,
    pad_seconds: float,
) -> tuple[int, int]:
    center_sec = (onset_sec + end_sec) / 2.0
    start = max(0, int(np.floor((center_sec - pad_seconds) * sfreq)))
    stop = min(n_times - 1, int(np.ceil((center_sec + pad_seconds) * sfreq)))
    if stop <= start:
        stop = min(n_times - 1, start + 1)
    return start, stop


def _maybe_downsample(
    signal: np.ndarray,
    sfreq: float,
    *,
    downsample: bool,
    target_sfreq: float,
) -> tuple[np.ndarray, float]:
    if not downsample:
        return signal, sfreq
    if target_sfreq <= 0:
        raise ValueError("target_sfreq must be positive.")
    if target_sfreq >= sfreq:
        return signal, sfreq
    decim = max(1, int(round(sfreq / target_sfreq)))
    downsampled = signal[::decim]
    effective_sfreq = sfreq / decim
    return downsampled, effective_sfreq


def _plot_panel(
    ax: plt.Axes,
    *,
    times: np.ndarray,
    signal: np.ndarray,
    blink_start_s: float,
    blink_end_s: float,
    title: str,
) -> None:
    ax.plot(times, signal, color="black", lw=1.0)
    ax.axvspan(blink_start_s, blink_end_s, color="crimson", alpha=0.18)
    ax.axvline(blink_start_s, color="crimson", linestyle="--", lw=1.0)
    ax.axvline(blink_end_s, color="crimson", linestyle="--", lw=1.0)
    ax.set_title(title)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    ax.grid(alpha=0.2)


def _build_comparison_figure(
    *,
    channel_name: str,
    raw_signal: np.ndarray,
    raw_sfreq: float,
    epoch_signal: np.ndarray,
    epoch_sfreq: float,
    raw_blink: dict[str, float],
    epoch_blink: pd.Series,
    pad_seconds: float,
) -> plt.Figure:
    raw_start, raw_stop = _window_indices(
        raw_blink["onset_sec"],
        raw_blink["end_sec"],
        raw_sfreq,
        raw_signal.shape[0],
        pad_seconds=pad_seconds,
    )
    epoch_start, epoch_stop = _window_indices(
        float(epoch_blink["epoch_onset_sec"]),
        float(epoch_blink["epoch_end_sec"]),
        epoch_sfreq,
        epoch_signal.shape[0],
        pad_seconds=pad_seconds,
    )

    raw_times = np.arange(raw_start, raw_stop + 1, dtype=float) / raw_sfreq
    raw_window = raw_signal[raw_start : raw_stop + 1]
    epoch_times = np.arange(epoch_start, epoch_stop + 1, dtype=float) / epoch_sfreq
    epoch_window = epoch_signal[epoch_start : epoch_stop + 1]

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), constrained_layout=True)

    _plot_panel(
        axes[0],
        times=raw_times,
        signal=raw_window,
        blink_start_s=float(raw_blink["onset_sec"]),
        blink_end_s=float(raw_blink["end_sec"]),
        title=(
            f"Top: 1.edf | {channel_name}\n"
            f"raw blink {int(raw_blink['raw_blink_index'])} "
            f"(samples {int(raw_blink['start_sample'])}-{int(raw_blink['end_sample'])})"
        ),
    )
    _plot_panel(
        axes[1],
        times=epoch_times,
        signal=epoch_window,
        blink_start_s=float(epoch_blink["epoch_onset_sec"]),
        blink_end_s=float(epoch_blink["epoch_end_sec"]),
        title=(
            f"Bottom: dev_epo.fif | epoch_id {int(epoch_blink['epoch_id'])} | {channel_name}\n"
            f"epoch blink {int(epoch_blink['epoch_blink_index'])} "
            f"(global {int(epoch_blink['global_blink_index'])})"
        ),
    )
    fig.suptitle(f"Blink-region comparison on {channel_name}", fontsize=14)
    return fig


def _parse_index_spec(index_spec: str) -> list[int]:
    values: list[int] = []
    if not index_spec.strip():
        return values
    for token in index_spec.split(","):
        part = token.strip()
        if not part:
            continue
        if "-" in part:
            left, right = part.split("-", 1)
            start = int(left.strip())
            end = int(right.strip())
            step = 1 if end >= start else -1
            values.extend(list(range(start, end + step, step)))
        else:
            values.append(int(part))
    deduped: list[int] = []
    seen: set[int] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _as_tag(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", text.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "channel"


def _resolve_single_output_path(args: argparse.Namespace, epoch_blink: pd.Series) -> Path:
    if args.output is not None:
        return args.output
    epoch_id = int(epoch_blink["epoch_id"])
    epoch_blink_index = int(epoch_blink["epoch_blink_index"])
    global_index = int(epoch_blink["global_blink_index"])
    filename = (
        f"{DEFAULT_IMAGE_PREFIX}_g{global_index}_e{epoch_id}b{epoch_blink_index}.png"
    )
    return SAMPLE_DIR / filename


def _resolve_report_output_path(
    args: argparse.Namespace,
    indices: list[int],
) -> Path:
    if args.report_output is not None:
        return args.report_output
    if args.report_blink_indices.strip():
        spec = _as_tag(args.report_blink_indices)
        suffix = f"indices_{spec}"
    elif args.epoch_id is not None:
        suffix = f"epoch_{args.epoch_id}"
    elif len(indices) == 1:
        suffix = f"g{indices[0]}"
    else:
        suffix = f"g{indices[0]}_to_g{indices[-1]}_n{len(indices)}"
    return SAMPLE_DIR / f"{DEFAULT_REPORT_PREFIX}_{suffix}.html"


def _resolve_report_output_path_for_chunk(
    base_output_path: Path,
    *,
    chunk_number: int,
    total_chunks: int,
) -> Path:
    if total_chunks <= 1:
        return base_output_path
    return base_output_path.with_name(
        f"{base_output_path.stem}_part{chunk_number:02d}_of_{total_chunks:02d}{base_output_path.suffix}"
    )


def _chunk_list(values: list[int], chunk_size: int) -> list[list[int]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")
    return [values[idx : idx + chunk_size] for idx in range(0, len(values), chunk_size)]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot raw-vs-epoch blink windows (single image or MNE report)."
    )
    parser.add_argument(
        "--mode",
        choices=("single", "report"),
        default="single",
        help="Render one comparison image or many comparisons into an HTML MNE report.",
    )
    parser.add_argument(
        "--blink-index",
        type=int,
        default=1,
        help="Global 1-based blink index across all epoch metadata rows.",
    )
    parser.add_argument(
        "--epoch-id",
        type=int,
        default=None,
        help="Optional epoch id selector for single mode (use with --epoch-blink-index).",
    )
    parser.add_argument(
        "--epoch-blink-index",
        type=int,
        default=None,
        help="Optional 1-based blink index within the selected epoch id.",
    )
    parser.add_argument(
        "--report-blink-indices",
        type=str,
        default="",
        help="Comma/range list for report mode, e.g. '1,2,10-15'.",
    )
    parser.add_argument(
        "--report-max-blinks",
        type=int,
        default=None,
        help="Optional cap on total blinks included in report mode. Default: include all.",
    )
    parser.add_argument(
        "--max-blinks-per-html",
        type=int,
        default=DEFAULT_REPORT_MAX_BLINKS_PER_HTML,
        help=(
            "Maximum number of blink figures per HTML report. "
            f"Default: {DEFAULT_REPORT_MAX_BLINKS_PER_HTML}."
        ),
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=None,
        help="HTML output path for report mode. If omitted, auto-name under sample_data.",
    )
    parser.add_argument(
        "--report-title",
        type=str,
        default="Raw vs Epoch Blink Comparison",
        help="Report title for MNE report mode.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Image output path for single mode. If omitted, auto-name under sample_data.",
    )
    parser.add_argument(
        "--pad-seconds",
        type=float,
        default=DEFAULT_PAD_SECONDS,
        help=f"Seconds on each side of the blink midpoint. Default: {DEFAULT_PAD_SECONDS:g}.",
    )
    parser.add_argument(
        "--no-downsample",
        action="store_true",
        help="Keep the original sampling rate instead of downsampling for plotting.",
    )
    parser.add_argument(
        "--downsample-hz",
        type=float,
        default=DEFAULT_DOWNSAMPLE_HZ,
        help=f"Target plotting rate when downsampling is enabled. Default: {DEFAULT_DOWNSAMPLE_HZ:g} Hz.",
    )
    return parser.parse_args()


def _render_single(
    *,
    args: argparse.Namespace,
    channel_name: str,
    events: pd.DataFrame,
    epoch_blink_table: pd.DataFrame,
    raw_signal_full: np.ndarray,
    raw_sfreq: float,
    epoch_data: np.ndarray,
    epoch_sfreq: float,
) -> None:
    epoch_blink = _select_epoch_blink(epoch_blink_table, args)
    raw_blink = _select_raw_blink_for_epoch(epoch_blink, events, raw_sfreq)
    output_path = _resolve_single_output_path(args, epoch_blink)

    raw_signal, raw_plot_sfreq = _maybe_downsample(
        raw_signal_full,
        raw_sfreq,
        downsample=not args.no_downsample,
        target_sfreq=args.downsample_hz,
    )
    epoch_signal, epoch_plot_sfreq = _maybe_downsample(
        epoch_data[int(epoch_blink["epoch_row_index"])],
        epoch_sfreq,
        downsample=not args.no_downsample,
        target_sfreq=args.downsample_hz,
    )

    fig = _build_comparison_figure(
        channel_name=channel_name,
        raw_signal=raw_signal,
        raw_sfreq=raw_plot_sfreq,
        epoch_signal=epoch_signal,
        epoch_sfreq=epoch_plot_sfreq,
        raw_blink=raw_blink,
        epoch_blink=epoch_blink,
        pad_seconds=args.pad_seconds,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

    print(f"Mode: single")
    print(f"Representative channel: {channel_name}")
    print(
        "Plot sampling:",
        {
            "downsample_enabled": not args.no_downsample,
            "requested_target_hz": args.downsample_hz,
            "raw_plot_hz": raw_plot_sfreq,
            "epoch_plot_hz": epoch_plot_sfreq,
            "pad_seconds": args.pad_seconds,
        },
    )
    print(f"Selected epoch blink: {dict(epoch_blink)}")
    print(f"Matched raw blink: {raw_blink}")
    print(f"Saved image: {output_path}")


def _resolve_report_indices(
    *,
    args: argparse.Namespace,
    epoch_blink_table: pd.DataFrame,
) -> list[int]:
    if args.report_blink_indices.strip():
        indices = _parse_index_spec(args.report_blink_indices)
    elif args.epoch_id is not None:
        subset = epoch_blink_table.loc[epoch_blink_table["epoch_id"] == args.epoch_id]
        if subset.empty:
            raise ValueError(f"epoch_id {args.epoch_id} not found in dev_epo metadata.")
        indices = subset["global_blink_index"].astype(int).tolist()
    else:
        indices = epoch_blink_table["global_blink_index"].astype(int).tolist()

    if args.report_max_blinks is not None:
        max_count = max(1, int(args.report_max_blinks))
        indices = indices[:max_count]

    valid: list[int] = []
    for index in indices:
        if index < 1 or index > len(epoch_blink_table):
            raise ValueError(
                f"Report blink index {index} out of range 1..{len(epoch_blink_table)}."
            )
        valid.append(index)
    if not valid:
        raise ValueError("No blink indices resolved for report mode.")
    return valid


def _render_report(
    *,
    args: argparse.Namespace,
    channel_name: str,
    events: pd.DataFrame,
    epoch_blink_table: pd.DataFrame,
    raw_signal_full: np.ndarray,
    raw_sfreq: float,
    epoch_data: np.ndarray,
    epoch_sfreq: float,
) -> None:
    indices = _resolve_report_indices(args=args, epoch_blink_table=epoch_blink_table)
    report_output_path = _resolve_report_output_path(args, indices)
    chunks = _chunk_list(indices, max(1, int(args.max_blinks_per_html)))
    raw_signal, raw_plot_sfreq = _maybe_downsample(
        raw_signal_full,
        raw_sfreq,
        downsample=not args.no_downsample,
        target_sfreq=args.downsample_hz,
    )
    _, epoch_plot_sfreq = _maybe_downsample(
        epoch_data[0],
        epoch_sfreq,
        downsample=not args.no_downsample,
        target_sfreq=args.downsample_hz,
    )
    channel_tag = _as_tag(channel_name)
    saved_paths: list[Path] = []
    total_chunks = len(chunks)
    for chunk_idx, chunk_indices in enumerate(chunks, start=1):
        report = mne.Report(
            title=f"{args.report_title} ({chunk_idx}/{total_chunks})"
            if total_chunks > 1
            else args.report_title
        )
        for index in chunk_indices:
            epoch_blink = _select_epoch_blink_by_global(epoch_blink_table, index)
            raw_blink = _select_raw_blink_for_epoch(epoch_blink, events, raw_sfreq)
            epoch_signal, epoch_plot_sfreq = _maybe_downsample(
                epoch_data[int(epoch_blink["epoch_row_index"])],
                epoch_sfreq,
                downsample=not args.no_downsample,
                target_sfreq=args.downsample_hz,
            )
            fig = _build_comparison_figure(
                channel_name=channel_name,
                raw_signal=raw_signal,
                raw_sfreq=raw_plot_sfreq,
                epoch_signal=epoch_signal,
                epoch_sfreq=epoch_plot_sfreq,
                raw_blink=raw_blink,
                epoch_blink=epoch_blink,
                pad_seconds=args.pad_seconds,
            )
            caption = (
                f"Global blink {int(epoch_blink['global_blink_index'])}. "
                f"epoch_id={int(epoch_blink['epoch_id'])}, "
                f"epoch_blink_index={int(epoch_blink['epoch_blink_index'])}, "
                f"raw_blink_index={int(raw_blink['raw_blink_index'])}."
            )
            report.add_figure(
                fig=fig,
                title=f"Blink {int(epoch_blink['global_blink_index'])}",
                caption=caption,
                section="Raw vs epoch blink windows",
                tags=("blink", "comparison", channel_tag),
            )
            plt.close(fig)

        chunk_output_path = _resolve_report_output_path_for_chunk(
            report_output_path,
            chunk_number=chunk_idx,
            total_chunks=total_chunks,
        )
        chunk_output_path.parent.mkdir(parents=True, exist_ok=True)
        report.save(chunk_output_path, overwrite=True, open_browser=False)
        saved_paths.append(chunk_output_path)

    print(f"Mode: report")
    print(f"Representative channel: {channel_name}")
    print(
        "Plot sampling:",
        {
            "downsample_enabled": not args.no_downsample,
            "requested_target_hz": args.downsample_hz,
            "raw_plot_hz": raw_plot_sfreq,
            "epoch_plot_hz": epoch_plot_sfreq,
            "pad_seconds": args.pad_seconds,
            "n_blinks": len(indices),
            "max_blinks_per_html": args.max_blinks_per_html,
            "n_html_files": total_chunks,
        },
    )
    print(f"Report blink indices: {indices}")
    print(f"Saved reports: {[str(path) for path in saved_paths]}")


def main() -> None:
    args = _parse_args()
    payload = _load_seed_results()
    channel_name = _representative_channel(payload)

    raw = mne.io.read_raw_edf(RAW_PATH, preload=True, verbose="ERROR")
    epochs = mne.read_epochs(EPOCHS_PATH, preload=True, verbose="ERROR")

    if channel_name not in raw.ch_names:
        raise ValueError(f"{channel_name!r} not found in {RAW_PATH.name}.")
    if channel_name not in epochs.ch_names:
        raise ValueError(f"{channel_name!r} not found in {EPOCHS_PATH.name}.")

    events = payload["events"]
    epoch_blink_table = _build_epoch_blink_table(epochs)

    raw_sfreq = float(raw.info["sfreq"])
    epoch_sfreq = float(epochs.info["sfreq"])
    raw_signal_full = raw.get_data(picks=[channel_name])[0]
    epoch_data = epochs.get_data(picks=[channel_name])[:, 0, :]

    if args.mode == "single":
        _render_single(
            args=args,
            channel_name=channel_name,
            events=events,
            epoch_blink_table=epoch_blink_table,
            raw_signal_full=raw_signal_full,
            raw_sfreq=raw_sfreq,
            epoch_data=epoch_data,
            epoch_sfreq=epoch_sfreq,
        )
        return

    _render_report(
        args=args,
        channel_name=channel_name,
        events=events,
        epoch_blink_table=epoch_blink_table,
        raw_signal_full=raw_signal_full,
        raw_sfreq=raw_sfreq,
        epoch_data=epoch_data,
        epoch_sfreq=epoch_sfreq,
    )


if __name__ == "__main__":
    main()
