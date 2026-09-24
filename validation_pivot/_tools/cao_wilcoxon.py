import pandas as pd
import numpy as np
from scipy.stats import wilcoxon
import glob

files = sorted(glob.glob(r'C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm\publication_results\exp1_channel_cao\sessions\*.csv'))
dfs = [pd.read_csv(f) for f in files]
df = pd.concat(dfs, ignore_index=True)
df = df[df.center_method == 'median']

curated18 = ["C3","C4","CP3","CP4","F3","F4","FC3","FC4","FP1","FP2","FT7","FT8","O1","O2","P3","P4","T5","T6"]

def paired(channel, sel_a, sel_b):
    a = df[(df.channel == channel) & (df.selection == sel_a)][['session', 'f1']].rename(columns={'f1': 'f1_a'})
    b = df[(df.channel == channel) & (df.selection == sel_b)][['session', 'f1']].rename(columns={'f1': 'f1_b'})
    m = a.merge(b, on='session', how='inner')
    return m

# find each electrode's own region
region_map = {}
regions = ['frontal', 'central', 'parietal', 'occipital']
for ch in curated18:
    sels = df[(df.channel == ch) & (df.selection.isin(regions))]['selection'].unique()
    assert len(sels) == 1, (ch, sels)
    region_map[ch] = sels[0]

print("Region membership actually found in data:")
for r in regions:
    members = [ch for ch, v in region_map.items() if v == r]
    print(f"  {r}: {members}")
print()

results_fig4 = []
results_fig6 = []
for ch in curated18:
    region = region_map[ch]
    m4 = paired(ch, region, 'all_channel')
    n4 = len(m4)
    diffs4 = m4['f1_a'] - m4['f1_b']
    if np.all(diffs4 == 0) or n4 < 1:
        stat4, p4 = np.nan, 1.0
    else:
        try:
            stat4, p4 = wilcoxon(m4['f1_a'], m4['f1_b'])
        except ValueError:
            stat4, p4 = np.nan, 1.0
    mean_delta4 = diffs4.mean()
    results_fig4.append((ch, region, n4, mean_delta4, p4))

    only_sel = ch.lower() + '_only'
    m6 = paired(ch, only_sel, 'all_channel')
    n6 = len(m6)
    diffs6 = m6['f1_a'] - m6['f1_b']
    if np.all(diffs6 == 0) or n6 < 1:
        stat6, p6 = np.nan, 1.0
    else:
        try:
            stat6, p6 = wilcoxon(m6['f1_a'], m6['f1_b'])
        except ValueError:
            stat6, p6 = np.nan, 1.0
    mean_delta6 = diffs6.mean()
    results_fig6.append((ch, only_sel, n6, mean_delta6, p6))

print("=== Figure 4: own-region vs all_channel (Wilcoxon, session-paired) ===")
print(f"{'channel':8} {'region':10} {'n':4} {'mean_delta_pp':>14} {'p_raw':>10} {'p_bonf18':>10} {'sig@.05':>8}")
for ch, region, n, delta, p in results_fig4:
    pb = min(p * 18, 1.0)
    sig = "YES" if pb < 0.05 else "no"
    print(f"{ch:8} {region:10} {n:4} {delta*100:14.4f} {p:10.5f} {pb:10.5f} {sig:>8}")

print()
print("=== Figure 6: own single-channel vs all_channel (Wilcoxon, session-paired) ===")
print(f"{'channel':8} {'only_sel':10} {'n':4} {'mean_delta_pp':>14} {'p_raw':>10} {'p_bonf18':>10} {'sig@.05':>8}")
for ch, sel, n, delta, p in results_fig6:
    pb = min(p * 18, 1.0)
    sig = "YES" if pb < 0.05 else "no"
    print(f"{ch:8} {sel:10} {n:4} {delta*100:14.4f} {p:10.5f} {pb:10.5f} {sig:>8}")

# Save for embedding into workbook
out = pd.DataFrame(results_fig6, columns=['channel', 'only_selection', 'n_sessions', 'mean_delta_f1', 'p_raw'])
out['p_bonferroni18'] = (out['p_raw'] * 18).clip(upper=1.0)
out['significant_0.05'] = out['p_bonferroni18'] < 0.05
out['mean_delta_pp'] = out['mean_delta_f1'] * 100
out.to_csv(r'C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm\validation_pivot\_tools\fig6_significance.csv', index=False)

out4 = pd.DataFrame(results_fig4, columns=['channel', 'region', 'n_sessions', 'mean_delta_f1', 'p_raw'])
out4['p_bonferroni18'] = (out4['p_raw'] * 18).clip(upper=1.0)
out4['significant_0.05'] = out4['p_bonferroni18'] < 0.05
out4['mean_delta_pp'] = out4['mean_delta_f1'] * 100
out4.to_csv(r'C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm\validation_pivot\_tools\fig4_significance.csv', index=False)
