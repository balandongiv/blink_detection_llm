import pandas as pd
import numpy as np
from scipy.stats import wilcoxon

ROOT = r"C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm"
csv_path = ROOT + r"\publication_results\exp1_channel_raja\exp1_channel_selection_raja_results.csv"
map_path = ROOT + r"\validation_pivot\_tools\egi_to_1020_map_internal.csv"

df = pd.read_csv(csv_path)
map_df = pd.read_csv(map_path)
egi2ten = dict(zip(map_df['channel_egi'], map_df['channel_1020']))
df['channel_1020'] = df['channel'].map(egi2ten)
df = df[df['center_method'] == 'median'].copy()

curated24 = ["Fp1","AF3","F3","AF4","Fp2","F4","FC1","C3","FC5","C4","FC2","FC6",
             "CP1","CP5","CP2","CP6","P7","P3","PO3","O1","PO4","P4","P8","E83"]
region_of = {
 "Fp1":"frontal","AF3":"frontal","F3":"frontal","AF4":"frontal","Fp2":"frontal","F4":"frontal",
 "FC1":"central","C3":"central","FC5":"central","C4":"central","FC2":"central","FC6":"central",
 "CP1":"parietal","CP5":"parietal","CP2":"parietal","CP6":"parietal",
 "P7":"occipital","P3":"occipital","PO3":"occipital","O1":"occipital","PO4":"occipital",
 "P4":"occipital","P8":"occipital","E83":"occipital",
}

allc = df[df['selection'] == 'all_channel'][['session','channel_1020','f1']].rename(columns={'f1':'f1_montage'})

def run_family(name, get_own_f1_frame):
    print(f"\n===== {name} =====")
    pvals = {}
    deltas = {}
    ns = {}
    for ch in curated24:
        own = get_own_f1_frame(ch)
        mont = allc[allc['channel_1020'] == ch]
        merged = pd.merge(own, mont, on='session', how='inner', suffixes=('_own',''))
        merged = merged.dropna(subset=['f1_own' if 'f1_own' in merged.columns else 'f1', 'f1_montage'])
        # normalize column name for own f1
        own_col = 'f1_own' if 'f1_own' in merged.columns else 'f1'
        merged = merged.dropna(subset=[own_col, 'f1_montage'])
        n = len(merged)
        ns[ch] = n
        if n < 1:
            pvals[ch] = np.nan
            deltas[ch] = np.nan
            continue
        diffs = merged[own_col] - merged['f1_montage']
        deltas[ch] = diffs.mean() * 100
        if n < 1 or np.allclose(diffs, 0):
            pvals[ch] = 1.0
            continue
        try:
            stat, p = wilcoxon(merged[own_col], merged['f1_montage'])
        except ValueError:
            p = 1.0
        pvals[ch] = p

    # Bonferroni correct over 24
    adj = {ch: min(1.0, p * 24) if not np.isnan(p) else np.nan for ch, p in pvals.items()}
    sig = {ch: (adj[ch] < 0.05) for ch in curated24}
    n_sig = sum(1 for ch in curated24 if sig[ch])
    print(f"n sessions per electrode: {ns}")
    print(f"{n_sig} of 24 electrodes significant after Bonferroni correction")
    for ch in curated24:
        print(f"  {ch:5s} region={region_of[ch]:9s} n={ns[ch]:3d} delta(own-montage)={deltas[ch]:+7.3f}pp  raw_p={pvals[ch]:.5g}  adj_p={adj[ch]:.5g}  sig={sig[ch]}")
    if not all(np.isnan(v) for v in deltas.values()):
        vals = [v for v in deltas.values() if not np.isnan(v)]
        print(f"delta range: {min(vals):.3f} to {max(vals):.3f} pp")
    return pvals, adj, sig, deltas

# Figure 4: own-region subset vs all_channel
def own_region(ch):
    reg = region_of[ch]
    sub = df[(df['selection'] == reg) & (df['channel_1020'] == ch)][['session','f1']]
    return sub

run_family("Figure 4: region-subset vs all_channel", own_region)

# Figure 6: single-electrode vs all_channel
def own_single(ch):
    sel = ch.lower() + "_only"
    sub = df[(df['selection'] == sel) & (df['channel_1020'] == ch)][['session','f1']]
    return sub

run_family("Figure 6: single-electrode vs all_channel", own_single)
