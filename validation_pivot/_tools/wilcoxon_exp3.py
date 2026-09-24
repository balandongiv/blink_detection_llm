import pandas as pd
from scipy.stats import wilcoxon
from pathlib import Path

root = Path(r"C:\Users\balan\Desktop\farah_fyp-main\farah_fyp-main\blink_detection_llm")
cao_path = root / "publication_results" / "exp3_cao" / "exp2_strategy_comparison_cao2018_results.csv"
raja_path = root / "publication_results" / "exp3_raja" / "exp2_strategy_comparison_raja_results.csv"

df_cao = pd.read_csv(cao_path)
df_raja = pd.read_csv(raja_path)
combined = pd.concat([df_cao, df_raja], ignore_index=True)

results = []
for dataset in ["cao2018", "raja"]:
    sub = combined[combined["dataset"] == dataset]
    piv = sub.pivot(index="session", columns="condition", values="f1")
    for baseline in ["BLINKER-concat", "MNE-annot"]:
        paired = piv[["Proposed-Med", baseline]].dropna()
        assert len(paired) == (58 if dataset == "cao2018" else 46), f"n mismatch: {len(paired)}"
        stat, p = wilcoxon(paired["Proposed-Med"], paired[baseline], alternative="two-sided")
        results.append({
            "dataset": dataset,
            "baseline": baseline,
            "n_sessions": len(paired),
            "wilcoxon_stat": stat,
            "p_raw": p,
        })

res_df = pd.DataFrame(results)
res_df["p_bonferroni_x4"] = (res_df["p_raw"] * 4).clip(upper=1.0)
res_df["significant_at_0.05"] = res_df["p_bonferroni_x4"] < 0.05
print(res_df.to_string(index=False))

out_csv = root / "validation_pivot" / "_tools" / "wilcoxon_exp3_results.csv"
res_df.to_csv(out_csv, index=False)
print("\nWrote", out_csv)
