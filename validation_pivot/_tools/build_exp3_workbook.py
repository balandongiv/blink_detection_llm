import pandas as pd
from pathlib import Path

root = Path(r"C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm")
cao_path = root / "publication_results" / "exp3_cao" / "exp2_strategy_comparison_cao2018_results.csv"
raja_path = root / "publication_results" / "exp3_raja" / "exp2_strategy_comparison_raja_results.csv"
out_path = root / "validation_pivot" / "exp3_strategy_comparison_results.xlsx"

df_cao = pd.read_csv(cao_path)
df_raja = pd.read_csv(raja_path)

print("cao shape:", df_cao.shape, "unique conditions:", df_cao['condition'].unique())
print("raja shape:", df_raja.shape, "unique conditions:", df_raja['condition'].unique())
print("cao dataset values:", df_cao['dataset'].unique())
print("raja dataset values:", df_raja['dataset'].unique())
print("cao sessions:", df_cao['session'].nunique(), "raja sessions:", df_raja['session'].nunique())

combined = pd.concat([df_cao, df_raja], ignore_index=True)
print("combined shape:", combined.shape)

# Sanity check groupby-average (plain pandas, pre-confirmed numbers to reproduce via pivot)
chk = combined.groupby(['dataset', 'condition'])[['precision', 'recall', 'f1']].mean() * 100
print(chk)

with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
    combined.to_excel(writer, sheet_name="raw_data", index=False)

print("Wrote", out_path)
