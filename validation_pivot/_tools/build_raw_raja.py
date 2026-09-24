import pandas as pd

ROOT = r"C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm"
csv_path = ROOT + r"\publication_results\exp1_channel_raja\exp1_channel_selection_raja_results.csv"
map_path = ROOT + r"\validation_pivot\_tools\egi_to_1020_map_internal.csv"
out_path = ROOT + r"\validation_pivot\exp1_channel_selection_raja_results.xlsx"

df = pd.read_csv(csv_path)
map_df = pd.read_csv(map_path)
egi2ten = dict(zip(map_df['channel_egi'], map_df['channel_1020']))
df['channel_1020'] = df['channel'].map(egi2ten)

print("rows:", len(df))
print("unmapped channel_1020 count:", df['channel_1020'].isna().sum())

with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='raw_data', index=False)

print("wrote", out_path)
