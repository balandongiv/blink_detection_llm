"""Greedy predicted-vs-ground-truth blink event matching."""
from __future__ import annotations

import numpy as np


def _event_peak_time(row, epoch_signal: np.ndarray, sfreq: float) -> float:
    onset_s = float(row["blink_onset"])
    duration_s = float(row["blink_duration"])
    start_samp = int(round(onset_s * sfreq))
    end_samp = int(round((onset_s + duration_s) * sfreq))
    start_samp = max(0, min(start_samp, len(epoch_signal) - 1))
    end_samp = max(start_samp + 1, min(end_samp, len(epoch_signal)))
    event_signal = epoch_signal[start_samp:end_samp]
    peak_local = int(np.argmax(np.abs(event_signal)))
    return (start_samp + peak_local) / float(sfreq)


def _events_overlap(left, right) -> bool:
    left_start = float(left["blink_onset"])
    left_end = left_start + float(left["blink_duration"])
    right_start = float(right["blink_onset"])
    right_end = right_start + float(right["blink_duration"])
    return max(left_start, right_start) < min(left_end, right_end)


def match_events(
    predicted,
    ground_truth,
    signal_by_epoch: dict,
    sfreq: float,
    peak_side_tolerance_s: float | None = None,
) -> tuple[list[int], list[int], list[int]]:
    """Greedily match predicted and ground-truth events within each epoch."""
    predicted = predicted.reset_index(drop=True)
    ground_truth = ground_truth.reset_index(drop=True)

    matched_pred: set[int] = set()
    matched_gt: set[int] = set()

    epoch_indices = sorted(
        set(predicted["epoch_index"].tolist()) | set(ground_truth["epoch_index"].tolist())
    )

    for epoch_index in epoch_indices:
        pred_group = predicted[predicted["epoch_index"] == epoch_index]
        gt_group = ground_truth[ground_truth["epoch_index"] == epoch_index]
        unmatched_gt = set(gt_group.index.tolist())
        epoch_signal = np.asarray(signal_by_epoch.get(int(epoch_index), []), dtype=float)

        for pred_index, pred_row in pred_group.sort_values("blink_onset").iterrows():
            best_gt_index = None
            for gt_index in list(unmatched_gt):
                gt_row = gt_group.loc[gt_index]
                if not _events_overlap(pred_row, gt_row):
                    continue
                if peak_side_tolerance_s is not None and len(epoch_signal) > 0:
                    pred_peak = _event_peak_time(pred_row, epoch_signal, sfreq)
                    gt_peak = _event_peak_time(gt_row, epoch_signal, sfreq)
                    if abs(pred_peak - gt_peak) > peak_side_tolerance_s:
                        continue
                best_gt_index = gt_index
                break
            if best_gt_index is not None:
                matched_pred.add(pred_index)
                matched_gt.add(best_gt_index)
                unmatched_gt.remove(best_gt_index)

    tp_pred = list(matched_pred)
    fp_pred = [i for i in predicted.index if i not in matched_pred]
    fn_gt = [i for i in ground_truth.index if i not in matched_gt]
    return tp_pred, fp_pred, fn_gt
