import mne
import pandas as pd
import yaml

FIF_PATH = r'D:\dataset\drowsy_driving_raja_processed\S1\S01_20170519_043933\seg_data_raw\eeg_eog_raw.fif'
CSV_PATH = r'D:\dataset\drowsy_driving_raja\human_label_annotation\S1\S01_20170519_043933\ear_eog.csv'

# Load brain region channel list
with open(r'C:\Users\balan\IdeaProjects\find_blink_epoch_worktree\brain_region.yaml') as f:
    brain_regions = yaml.safe_load(f)

region_channels = [
    ch
    for region_channels in brain_regions['eeg_regions'].values()
    for ch in region_channels
]

# Load raw file
raw = mne.io.read_raw_fif(FIF_PATH, preload=True, verbose='ERROR')

available = [ch for ch in region_channels if ch in raw.ch_names]
missing   = [ch for ch in region_channels if ch not in raw.ch_names]
if missing:
    print(f"WARNING: channels in yaml but not in file: {missing}")

# Load annotations from CSV and apply to raw
df = pd.read_csv(CSV_PATH)
annotations = mne.Annotations(
    onset=df['onset'].values,
    duration=df['duration'].values,
    description=df['description'].values,
)
raw.set_annotations(annotations)

# Plot a reduced copy so the saved FIF keeps full data
plot_raw = raw.copy()
plot_raw.pick(available)
plot_raw.resample(sfreq=20)
plot_raw.plot(block=True, start=1300)

# Write any annotation edits back to the CSV
ann = plot_raw.annotations
updated_df = pd.DataFrame({
    'onset':       ann.onset,
    'duration':    ann.duration,
    'description': ann.description,
})
updated_df.to_csv(CSV_PATH, index=False)
print(f"Annotations saved to: {CSV_PATH} ({len(updated_df)} rows)")
