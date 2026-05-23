"""Core blink detection steps for processing channels.

This module implements the heart of the original Matlab legacy approach used
by *Blinker* to detect and characterize blinks.  The six-step workflow mirrors
the historical code path closely so that results remain comparable to the
Matlab version.
"""

import pandas as pd
from tqdm import tqdm

from src.logging import get_logger
from pyblinker.utils.statistics_utils import get_good_blink_mask, get_blink_statistic
from pyblinker.blinker.fit_blink import FitBlinks

from pyblinker.blinker.get_blink_positions import get_blink_position
from pyblinker.blinker.get_representative_channel import channel_selection


logger = get_logger(__name__)


def process_channel_data(detector, channel: str, verbose: bool = True) -> None:
    """Process blink data for a single channel using the legacy six-step pipeline."""
    logger.debug("Processing channel: %s", channel)

    # STEP 1: Get blink positions
    df = get_blink_position(
        detector.params,
        blink_component=detector.raw_data.get_data(picks=channel)[0],
        ch=channel,
    )

    if df.empty and verbose:
        logger.warning("No blinks detected in channel: %s", channel)

    # STEP 2: Fit blinks
    fitblinks = FitBlinks(
        candidate_signal=detector.raw_data.get_data(picks=channel)[0],
        df=df,
        params=detector.params,
    )
    fitblinks.dprocess()
    df = fitblinks.frame_blinks

    # STEP 3: Extract blink statistics extractBlinkProperties.m
    # Calculate an amplitude criterion (frames in blink to those out) and Now calculate the cutoff ratios -- use default for the values
    blink_stats = get_blink_statistic(
        df,
        detector.params["z_thresholds"],
        signal=detector.raw_data.get_data(picks=channel)[0],
    )
    blink_stats["ch"] = channel
    # There is a step for << Reduce the number of candidate signals based on the blink amp ratios >>, but we move it to channel selection step.

    # STEP 4: Get good blink mask extractBlinkProperties.m
    _, df = get_good_blink_mask(
        df,
        blink_stats["best_median"],
        blink_stats["best_robust_std"],
        detector.params["z_thresholds"],
    )
    # What happen if no good blinks are found or all blinks are bad?
    if df.empty and verbose:
        logger.warning("No good blinks found in channel: %s", channel)
        return
    # STEP 5: Compute blink properties
    df_in = df.copy()
    df_out = BlinkProperties(
        detector.raw_data.get_data(picks=channel)[0],
        df_in,
        detector.params["sfreq"],
        detector.params,
    ).df

    # STEP 6: Apply pAVR restriction # Suggest to move up to df_out = df_out[~(condition_1 & condition_2)] into a specific function.
    condition_1 = df_out["pos_amp_vel_ratio_zero"] < detector.params["p_avr_threshold"]
    condition_2 = df_out["max_value"] < (
        blink_stats["best_median"] - blink_stats["best_robust_std"]
    )
    df_out = df_out[~(condition_1 & condition_2)]

    detector.all_data_info.append({"df": df_out, "ch": channel})
    detector.all_data.append(blink_stats)


def process_all_channels(detector) -> None:
    """Process all channels available in the raw data."""
    logger.info("Processing %d channels.", len(detector.channel_list))
    for channel in tqdm(
        detector.channel_list,
        desc="Processing Channels",
        unit="channel",
        colour="BLACK",
    ):
        process_channel_data(detector, channel)
    logger.info("Finished processing all channels.")


def select_representative_channel(detector) -> pd.DataFrame:
    """Select the best representative channel based on blink statistics."""
    ch_blink_stat = pd.DataFrame(detector.all_data)
    ch_selected = channel_selection(ch_blink_stat, detector.params)
    ch_selected.reset_index(drop=True, inplace=True)
    return ch_selected


def get_representative_blink_data(detector, ch_selected: pd.DataFrame):
    """Retrieve blink data from the selected representative channel."""
    ch = ch_selected.loc[0, "ch"]
    data = detector.raw_data.get_data(picks=ch)[0]
    rep_blink_channel = detector.filter_point(ch, detector.all_data_info)
    df = rep_blink_channel["df"]
    df = detector.filter_bad_blink(df)
    return ch, data, df


def get_blink(detector):
    """Run the complete blink detection pipeline."""
    logger.info("Starting blink detection pipeline.")

    detector.prepare_raw_signal()
    process_all_channels(detector)

    ch_selected = select_representative_channel(detector)
    logger.info("Selected representative channel: %s", ch_selected.loc[0, "ch"])

    ch, data, df = get_representative_blink_data(detector, ch_selected)
    annot = detector.create_annotations(df)

    fig_data = detector.generate_viz(data, df) if detector.viz_data else []
    n_good_blinks = ch_selected.loc[0, "number_good_blinks"]

    logger.info(
        "Blink detection completed. %d good blinks detected.",
        n_good_blinks,
    )

    return annot, ch, n_good_blinks, df, fig_data, ch_selected
