import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import res_exp2_fig_f1_by_epoch_duration_fp1_fp2 as M
import paper_data as P

per_ds = {ds: M.f1_by_duration(ds, "median") for ds in ["raja", "cao"]}
block_means, block_p = M.compute_stats(per_ds)

for label in [P.DSN["raja"], "Cao2018"]:
    for channel in M.CHANNEL_LABELS:
        key = (label, channel)
        means = block_means[key]
        pvals = block_p[key]
        print(label, channel)
        for d in P.DURATIONS:
            p = pvals.get(d, None)
            print(f"  {d}s: F1={means[d]*100:.2f}%  p={p}")
