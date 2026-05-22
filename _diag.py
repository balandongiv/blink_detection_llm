import sys
sys.path.insert(0, 'src'); sys.path.insert(0, 'blink_evaluation/src'); sys.path.insert(0, 'autoreject')
from pathlib import Path
import mne
from blink_evaluation import evaluate_channels, load_ground_truth_annotations
from src.common.bad_epochs import get_valid_epoch_indices
from pyblinker.strategies import kleifges_strategy
from src.common.epoch_input import prepare_epoch_detection_input
from src.io.eeg_channels import load_brain_region_channels, load_raw_with_brain_channels

REPO_ROOT = Path('.').resolve()
FIF_PATH = Path(r'D:\dataset\drowsy_driving_raja_processed\S1\S01_20170519_043933\seg_data_raw\eeg_eog_raw.fif')
CSV_PATH = Path(r'D:\dataset\drowsy_driving_raja\human_label_annotation_eeg\S1\S01_20170519_043933\ear_eog.csv')
BRAIN_REGION_YAML = REPO_ROOT / 'brain_region.yaml'
EPOCH_DURATION_S = 30.0

brain_channels = load_brain_region_channels(BRAIN_REGION_YAML)
raw = load_raw_with_brain_channels(FIF_PATH, brain_channels)
epochs = mne.make_fixed_length_epochs(raw, duration=EPOCH_DURATION_S, preload=True, verbose='ERROR')
prepared = prepare_epoch_detection_input(epochs, pick_types_options={'eeg': True}, filter_low=1.0, filter_high=20.0)
valid_epoch_indices = get_valid_epoch_indices(epochs)
channel_results = kleifges_strategy(prepared, valid_epoch_indices)
gt_annotations = load_ground_truth_annotations(CSV_PATH, EPOCH_DURATION_S)
scored = evaluate_channels(channel_results, gt_annotations, epoch_duration=EPOCH_DURATION_S)

cr = scored.best_channel_result
mc = cr['mapped_candidates'].reset_index(drop=True)
sig = cr['signal_by_epoch']

print('mapped_candidates rows      :', len(mc))
print('signal_by_epoch keys        :', len(sig), '  range:', min(sig), '-', max(sig))
print('valid_epoch_indices len     :', len(valid_epoch_indices), '  first5:', valid_epoch_indices[:5])

missing = [ep for ep in mc['epoch_index'].unique() if sig.get(ep) is None]
print('ep_idx in mc but NOT in sig :', missing)

tp_set = {m.pred_index for m in scored.best_eval_result.true_positives}
fp_set = {e.index for e in scored.best_eval_result.false_positives}
print('tp_set size:', len(tp_set), '  fp_set size:', len(fp_set))
print('tp+fp total:', len(tp_set) + len(fp_set), '  mc rows:', len(mc))

# Are tp+fp indices contiguous and covering 0..len(mc)-1?
all_pred = tp_set | fp_set
expected = set(range(len(mc)))
print('pred indices == 0..len(mc)-1:', all_pred == expected)
print('missing from pred sets:', sorted(expected - all_pred)[:20])
print('extra in pred sets   :', sorted(all_pred - expected)[:20])
