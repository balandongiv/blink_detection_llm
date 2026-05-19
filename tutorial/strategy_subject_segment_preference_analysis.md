# Strategy Preference By Subject And Segment

## Scope

- Analysed `65` subject-segment pairs across `35` strategies from the artefacts already written under `experiment_output`.
- This report uses the stored best-lane metrics from every `*_lane_summary.csv` file under `experiment_output`.
- The aggregate ranking in `tutorial/report_first_iteration.md` is based on pooled micro-F1. Subject and segment preference here is based on per-pair best F1, so it will favor strategies that win many individual pairs even if they are not the pooled micro-F1 leader.
- Duration-only morphology proxy used in this report: short < 120 ms, typical 120-300 ms, slow 300-500 ms, closure-like > 500 ms.
- Because the annotations do not carry an explicit blink-vs-eye-closure morphology label, anything above 500 ms is treated as closure-like by duration proxy, not by direct plateau-shape labeling.

## Executive Summary

- Pooled micro-F1 leader: `expand_bridge_sw_onset`. Most frequent per-segment F1 winner: `strategy_c` (`21` of `65` segments).
- The main pattern is a split between pooled winners and pair-wise winners: `strategy_c` wins many individual segments, but the expand-bridge family wins the pooled leaderboard because it performs better on higher-volume recall-heavy segments.
- Long-duration events are the clearest shared recall problem. Across the competitive strategies, recall drops much more on long-heavy and closure-heavy segments than on short-heavy segments.
- Short or weak blinks still matter, but they look like a secondary failure mode concentrated in a smaller set of outlier segments such as `S26/S39_20190130_052313_2` and `S22/S35_20190123_040805_3`.
- Strong drop candidates for downstream analyses: `S11`, `S20`, `S26`, and `S27`. Caution subjects: `S3`, `S17`, and `S22`.

## Overall Strategy Ranking

| strategy                          | micro_f1 | micro_recall | micro_precision | mean_pair_f1 | mean_pair_recall | segment_wins | subject_mean_f1_leads |
| --------------------------------- | -------- | ------------ | --------------- | ------------ | ---------------- | ------------ | --------------------- |
| expand_bridge_sw_onset            | 0.676    | 0.722        | 0.635           | 0.601        | 0.667            | 3            | 1                     |
| expand_bridge_adaptive_k          | 0.673    | 0.739        | 0.618           | 0.597        | 0.688            | 3            | 0                     |
| expand_bridge_soft_gate           | 0.673    | 0.738        | 0.619           | 0.599        | 0.689            | 7            | 3                     |
| strategy_e_expand_bridge          | 0.659    | 0.746        | 0.591           | 0.581        | 0.694            | 0            | 0                     |
| strategy_e_sliding_window         | 0.659    | 0.720        | 0.607           | 0.590        | 0.679            | 1            | 1                     |
| expand_bridge_dynamic_low         | 0.659    | 0.745        | 0.590           | 0.581        | 0.695            | 0            | 0                     |
| expand_bridge_dynamic_gap         | 0.658    | 0.742        | 0.590           | 0.580        | 0.691            | 0            | 0                     |
| strategy_e13_self_train           | 0.653    | 0.739        | 0.585           | 0.588        | 0.706            | 6            | 3                     |
| strategy_e_adaptive_k             | 0.653    | 0.735        | 0.588           | 0.587        | 0.703            | 2            | 0                     |
| strategy_c                        | 0.653    | 0.649        | 0.657           | 0.623        | 0.643            | 21           | 8                     |
| expand_bridge_confidence_weighted | 0.652    | 0.737        | 0.584           | 0.576        | 0.687            | 0            | 0                     |
| strategy_e12_amp_filter           | 0.651    | 0.706        | 0.604           | 0.591        | 0.689            | 4            | 2                     |
| strategy_e_slope_guard            | 0.648    | 0.738        | 0.578           | 0.577        | 0.699            | 0            | 0                     |
| strategy_a                        | 0.648    | 0.742        | 0.575           | 0.576        | 0.703            | 2            | 0                     |
| strategy_e8_changepoint           | 0.644    | 0.737        | 0.572           | 0.573        | 0.699            | 0            | 0                     |

## Subject-Level Preference

- `dominant_segment_winner` = strategy that wins the most segments inside the subject.
- `best_mean_f1_strategy` = strategy with the highest average pair F1 across that subject.
- `best_mean_recall_any_fp_strategy` = strategy with the highest average pair recall across that subject, without any false-positive constraint.
- In practice, treat the recall-only column as a diagnostic signal. It often surfaces high-FP variants such as `strategy_e_abs_polarity`.

| subject | n_segments | dominant_segment_winner  | segment_wins | best_mean_f1_strategy     | best_mean_recall_any_fp_strategy | mean_best_f1 | min_best_f1 | mean_long_share | mean_closure_share | subject_action |
| ------- | ---------- | ------------------------ | ------------ | ------------------------- | -------------------------------- | ------------ | ----------- | --------------- | ------------------ | -------------- |
| S1      | 3          | strategy_c               | 3            | strategy_c                | strategy_e3_hysteresis           | 0.712        | 0.575       | 19.2%           | 9.2%               | keep           |
| S10     | 3          | expand_bridge_sw_onset   | 1            | strategy_c                | strategy_e_abs_polarity          | 0.765        | 0.711       | 15.1%           | 11.4%              | keep           |
| S11     | 3          | expand_bridge_soft_gate  | 1            | strategy_b                | strategy_e_abs_polarity          | 0.286        | 0.008       | 17.5%           | 12.5%              | drop-candidate |
| S12     | 3          | strategy_b               | 1            | strategy_e13_self_train   | strategy_e9_frontal_avg          | 0.923        | 0.881       | 4.1%            | 3.4%               | keep           |
| S13     | 3          | expand_bridge_adaptive_k | 1            | expand_bridge_soft_gate   | expand_bridge_soft_gate          | 0.858        | 0.778       | 24.3%           | 17.1%              | keep           |
| S16     | 3          | strategy_e3_hysteresis   | 2            | strategy_e3_hysteresis    | strategy_e_abs_polarity          | 0.864        | 0.752       | 1.0%            | 0.5%               | keep           |
| S17     | 2          | expand_bridge_soft_gate  | 1            | expand_bridge_soft_gate   | strategy_d                       | 0.513        | 0.124       | 9.6%            | 5.8%               | caution        |
| S18     | 3          | strategy_b               | 1            | strategy_b                | strategy_d                       | 0.778        | 0.681       | 4.7%            | 3.5%               | keep           |
| S19     | 3          | strategy_e13_self_train  | 3            | strategy_e13_self_train   | strategy_e11_lane_route          | 0.952        | 0.943       | 2.3%            | 1.6%               | keep           |
| S2      | 3          | strategy_c               | 2            | strategy_c                | strategy_e9_frontal_avg          | 0.749        | 0.634       | 19.1%           | 17.9%              | keep           |
| S20     | 3          | expand_bridge_sw_onset   | 1            | strategy_c                | strategy_d                       | 0.400        | 0.153       | 7.3%            | 5.5%               | drop-candidate |
| S21     | 3          | strategy_e13_self_train  | 1            | expand_bridge_sw_onset    | strategy_e_abs_polarity          | 0.917        | 0.812       | 0.3%            | 0.2%               | keep           |
| S22     | 3          | strategy_c               | 2            | strategy_c                | strategy_e_abs_polarity          | 0.474        | 0.061       | 24.1%           | 19.0%              | caution        |
| S23     | 3          | strategy_e12_amp_filter  | 2            | strategy_e12_amp_filter   | strategy_e11_lane_route          | 0.898        | 0.816       | 1.5%            | 1.1%               | keep           |
| S24     | 3          | expand_bridge_soft_gate  | 2            | expand_bridge_soft_gate   | strategy_e_abs_polarity          | 0.834        | 0.799       | 20.8%           | 17.1%              | keep           |
| S26     | 3          | expand_bridge_sw_onset   | 1            | strategy_e_sliding_window | strategy_e_abs_polarity          | 0.549        | 0.032       | 5.8%            | 3.8%               | drop-candidate |
| S27     | 3          | strategy_c               | 1            | strategy_e4_multiscale    | strategy_e_abs_polarity          | 0.346        | 0.180       | 30.6%           | 23.0%              | drop-candidate |
| S3      | 3          | strategy_c               | 3            | strategy_c                | strategy_e_adaptive_k            | 0.403        | 0.362       | 9.5%            | 9.5%               | caution        |
| S4      | 3          | expand_bridge_adaptive_k | 1            | strategy_e13_self_train   | strategy_e_abs_polarity          | 0.768        | 0.439       | 7.5%            | 4.1%               | keep           |
| S5      | 3          | expand_bridge_soft_gate  | 2            | strategy_c                | strategy_e_adaptive_k            | 0.813        | 0.736       | 19.0%           | 15.9%              | keep           |
| S6      | 3          | strategy_c               | 2            | strategy_c                | strategy_e_abs_polarity          | 0.658        | 0.440       | 3.6%            | 1.8%               | keep           |
| S7      | 3          | strategy_c               | 2            | strategy_e12_amp_filter   | strategy_e_abs_polarity          | 0.674        | 0.464       | 1.6%            | 0.6%               | keep           |

## Segment-Level Preference

- `duration_mix` uses S/T/L/C = short / typical / slow / closure-like share of reference annotations.
- `best_recall_any_fp_strategy` is recall-only and may be impractical when its precision is poor.

| subject | segment                | best_f1_strategy          | best_f1 | runner_up_strategy        | runner_up_f1 | delta_f1 | best_recall_any_fp_strategy       | best_recall_any_fp | duration_mix                       | difficulty     |
| ------- | ---------------------- | ------------------------- | ------- | ------------------------- | ------------ | -------- | --------------------------------- | ------------------ | ---------------------------------- | -------------- |
| S1      | S01_20170519_043933    | strategy_c                | 0.783   | strategy_b                | 0.658        | 0.126    | strategy_e3_hysteresis            | 0.870              | S=1.4%, T=29.0%, L=59.4%, C=10.1%  | keep           |
| S1      | S01_20170519_043933_2  | strategy_c                | 0.779   | strategy_b                | 0.665        | 0.114    | strategy_e_adaptive_k             | 0.834              | S=0.6%, T=78.3%, L=17.7%, C=3.4%   | keep           |
| S1      | S01_20170519_043933_3  | strategy_c                | 0.575   | expand_bridge_sw_onset    | 0.502        | 0.073    | strategy_a                        | 0.717              | S=0.0%, T=49.2%, L=36.6%, C=14.1%  | keep           |
| S10     | S23_20181226_042222    | strategy_c                | 0.767   | strategy_b                | 0.725        | 0.042    | strategy_e_abs_polarity           | 0.895              | S=0.7%, T=64.7%, L=21.6%, C=13.1%  | keep           |
| S10     | S23_20181226_042222_2  | strategy_b                | 0.816   | expand_bridge_sw_onset    | 0.814        | 0.003    | expand_bridge_dynamic_low         | 0.862              | S=0.0%, T=76.7%, L=11.2%, C=12.1%  | keep           |
| S10     | S23_20181226_042222_3  | expand_bridge_sw_onset    | 0.711   | strategy_e_sliding_window | 0.672        | 0.039    | strategy_e_abs_polarity           | 0.901              | S=14.2%, T=70.8%, L=5.9%, C=9.1%   | keep           |
| S11     | S24_20181227_034657    | expand_bridge_soft_gate   | 0.697   | expand_bridge_adaptive_k  | 0.696        | 0.001    | strategy_e_abs_polarity           | 0.773              | S=13.9%, T=42.7%, L=22.3%, C=21.2% | keep           |
| S11     | S24_20181227_034657_2  | strategy_d                | 0.152   | strategy_e_abs_polarity   | 0.148        | 0.004    | strategy_d                        | 0.241              | S=14.5%, T=49.2%, L=19.8%, C=16.4% | drop-candidate |
| S11     | S24_20181227_034657_3  | strategy_b                | 0.008   | strategy_d                | 0.001        | 0.007    | strategy_b                        | 1.000              | S=0.0%, T=100.0%, L=0.0%, C=0.0%   | drop-candidate |
| S12     | S25_20190124_060024    | strategy_c                | 0.944   | strategy_b                | 0.940        | 0.005    | strategy_d                        | 0.955              | S=1.1%, T=92.6%, L=4.7%, C=1.5%    | keep           |
| S12     | S25_20190124_060024_2  | strategy_b                | 0.881   | strategy_e_vote_2of3      | 0.855        | 0.026    | strategy_d                        | 0.892              | S=1.7%, T=83.3%, L=8.2%, C=6.8%    | keep           |
| S12     | S25_20190124_060024_3  | strategy_e13_self_train   | 0.943   | strategy_c                | 0.942        | 0.001    | strategy_e9_frontal_avg           | 0.947              | S=2.9%, T=91.8%, L=3.5%, C=1.8%    | keep           |
| S13     | S26_20190108_035218    | expand_bridge_soft_gate   | 0.941   | strategy_e13_self_train   | 0.934        | 0.007    | strategy_e4_multiscale            | 0.942              | S=0.4%, T=59.5%, L=24.5%, C=15.6%  | keep           |
| S13     | S26_20190108_035218_2  | strategy_e12_amp_filter   | 0.778   | expand_bridge_sw_onset    | 0.774        | 0.004    | strategy_e13_self_train           | 0.918              | S=11.6%, T=68.5%, L=13.9%, C=6.1%  | keep           |
| S13     | S26_20190108_035218_3  | expand_bridge_adaptive_k  | 0.854   | expand_bridge_soft_gate   | 0.854        | 0.000    | expand_bridge_confidence_weighted | 0.932              | S=0.8%, T=50.7%, L=18.9%, C=29.6%  | keep           |
| S16     | S29_20190111_034326    | strategy_e_adaptive_k     | 0.752   | strategy_e13_self_train   | 0.752        | 0.000    | strategy_a                        | 0.969              | S=71.2%, T=28.5%, L=0.2%, C=0.0%   | keep           |
| S16     | S29_20190111_034326_2  | strategy_e3_hysteresis    | 0.911   | strategy_e4_multiscale    | 0.897        | 0.014    | strategy_e_abs_polarity           | 0.904              | S=0.6%, T=92.9%, L=5.4%, C=1.2%    | keep           |
| S16     | S29_20190111_034326_3  | strategy_e3_hysteresis    | 0.929   | strategy_e4_multiscale    | 0.925        | 0.004    | strategy_e_abs_polarity           | 0.940              | S=0.9%, T=96.5%, L=2.2%, C=0.4%    | keep           |
| S17     | S30_20190114_040013_2  | expand_bridge_soft_gate   | 0.901   | strategy_e13_self_train   | 0.897        | 0.004    | strategy_e_abs_polarity           | 0.937              | S=0.3%, T=64.2%, L=24.6%, C=10.9%  | keep           |
| S17     | S30_20190114_040013_3  | strategy_e_abs_polarity   | 0.124   | strategy_c                | 0.112        | 0.013    | strategy_d                        | 0.826              | S=1.8%, T=83.3%, L=14.0%, C=0.8%   | drop-candidate |
| S18     | S31_20190115_035853    | strategy_e_vote_2of3      | 0.713   | expand_bridge_soft_gate   | 0.624        | 0.089    | strategy_e_vote_2of3              | 0.908              | S=0.3%, T=88.9%, L=8.6%, C=2.2%    | keep           |
| S18     | S31_20190115_035853_2  | strategy_b                | 0.681   | strategy_e_vote_2of3      | 0.674        | 0.007    | strategy_e_vote_2of3              | 0.922              | S=2.9%, T=91.3%, L=2.6%, C=3.2%    | keep           |
| S18     | S31_20190115_035853_3  | strategy_e13_self_train   | 0.941   | expand_bridge_soft_gate   | 0.937        | 0.004    | strategy_e_quantile_thr           | 0.950              | S=0.0%, T=89.2%, L=5.6%, C=5.2%    | keep           |
| S19     | S32_20190116_041137    | strategy_e13_self_train   | 0.950   | strategy_c                | 0.944        | 0.007    | strategy_e11_lane_route           | 0.938              | S=2.2%, T=91.0%, L=4.8%, C=2.0%    | keep           |
| S19     | S32_20190116_041137_2  | strategy_e13_self_train   | 0.962   | strategy_c                | 0.953        | 0.009    | strategy_e11_lane_route           | 0.968              | S=2.2%, T=94.9%, L=2.2%, C=0.8%    | keep           |
| S19     | S32_20190116_041137_3  | strategy_e13_self_train   | 0.943   | strategy_d                | 0.934        | 0.009    | strategy_e8_changepoint           | 0.952              | S=3.8%, T=91.9%, L=2.5%, C=1.9%    | keep           |
| S2      | TEST_20170601_042544   | strategy_c                | 0.735   | strategy_e_quantile_thr   | 0.567        | 0.168    | strategy_e_quantile_thr           | 0.811              | S=0.4%, T=74.9%, L=7.3%, C=17.5%   | keep           |
| S2      | TEST_20170601_042544_2 | strategy_b                | 0.634   | expand_bridge_sw_onset    | 0.542        | 0.092    | strategy_e_vote_2of3              | 0.689              | S=0.0%, T=61.1%, L=7.8%, C=31.1%   | keep           |
| S2      | TEST_20170601_042544_3 | strategy_c                | 0.876   | expand_bridge_sw_onset    | 0.673        | 0.203    | strategy_e12_amp_filter           | 0.891              | S=0.8%, T=91.9%, L=2.3%, C=5.0%    | keep           |
| S20     | s33_20190117_042235    | strategy_c                | 0.789   | strategy_b                | 0.741        | 0.048    | strategy_d                        | 0.995              | S=5.3%, T=90.9%, L=3.3%, C=0.5%    | keep           |
| S20     | s33_20190117_042235_2  | strategy_d                | 0.153   | strategy_e_sliding_window | 0.131        | 0.021    | strategy_e_abs_polarity           | 0.319              | S=27.5%, T=37.2%, L=19.2%, C=16.0% | drop-candidate |
| S20     | s33_20190117_042235_3  | expand_bridge_sw_onset    | 0.258   | strategy_e_sliding_window | 0.242        | 0.016    | expand_bridge_sw_onset            | 0.364              | S=0.0%, T=100.0%, L=0.0%, C=0.0%   | caution        |
| S21     | S34_20190122_044130    | strategy_e_vote_2of3      | 0.975   | strategy_b                | 0.947        | 0.028    | strategy_e_vote_2of3              | 0.980              | S=1.6%, T=96.2%, L=1.7%, C=0.6%    | keep           |
| S21     | S34_20190122_044130_2  | strategy_e13_self_train   | 0.812   | strategy_c                | 0.810        | 0.002    | strategy_a                        | 0.972              | S=57.0%, T=43.0%, L=0.0%, C=0.0%   | keep           |
| S21     | S34_20190122_044130_3  | strategy_e_adaptive_k     | 0.965   | strategy_e5_global_floor  | 0.964        | 0.001    | strategy_e_adaptive_k             | 0.956              | S=1.0%, T=97.4%, L=1.6%, C=0.0%    | keep           |
| S22     | S35_20190123_040805    | expand_bridge_adaptive_k  | 0.678   | expand_bridge_soft_gate   | 0.633        | 0.045    | strategy_e_abs_polarity           | 0.758              | S=3.1%, T=44.6%, L=23.0%, C=29.3%  | keep           |
| S22     | S35_20190123_040805_2  | strategy_c                | 0.682   | strategy_e_adaptive_k     | 0.642        | 0.040    | strategy_e_abs_polarity           | 0.783              | S=2.3%, T=56.8%, L=17.0%, C=23.9%  | keep           |
| S22     | S35_20190123_040805_3  | strategy_c                | 0.061   | strategy_e_adaptive_k     | 0.041        | 0.020    | strategy_e_abs_polarity           | 0.365              | S=59.6%, T=32.7%, L=3.8%, C=3.8%   | drop-candidate |
| S23     | S36_20190125_040931    | strategy_c                | 0.969   | strategy_e13_self_train   | 0.968        | 0.001    | strategy_e_or_fusion              | 0.961              | S=9.3%, T=89.6%, L=1.0%, C=0.1%    | keep           |
| S23     | S36_20190125_040931_2  | strategy_e12_amp_filter   | 0.909   | strategy_c                | 0.907        | 0.001    | strategy_e_sliding_window         | 0.920              | S=12.4%, T=82.7%, L=2.8%, C=2.2%   | keep           |
| S23     | S36_20190125_040931_3  | strategy_e12_amp_filter   | 0.816   | strategy_e13_self_train   | 0.811        | 0.004    | strategy_e11_lane_route           | 0.877              | S=11.3%, T=85.4%, L=2.5%, C=0.8%   | keep           |
| S24     | S38_20190129_035118    | expand_bridge_soft_gate   | 0.861   | expand_bridge_adaptive_k  | 0.860        | 0.001    | strategy_e_abs_polarity           | 0.882              | S=0.6%, T=73.7%, L=16.5%, C=9.3%   | keep           |
| S24     | S38_20190129_035118_2  | strategy_e_vote_2of3      | 0.799   | expand_bridge_sw_onset    | 0.759        | 0.040    | strategy_e_vote_2of3              | 0.793              | S=0.5%, T=60.8%, L=15.5%, C=23.2%  | keep           |
| S24     | S38_20190129_035118_3  | expand_bridge_soft_gate   | 0.841   | strategy_e_expand_bridge  | 0.838        | 0.003    | strategy_e4_multiscale            | 0.865              | S=1.4%, T=68.1%, L=11.6%, C=19.0%  | keep           |
| S26     | S39_20190130_052313    | expand_bridge_sw_onset    | 0.733   | strategy_e_sliding_window | 0.732        | 0.001    | strategy_e11_lane_route           | 0.908              | S=23.7%, T=68.1%, L=4.3%, C=3.8%   | keep           |
| S26     | S39_20190130_052313_2  | strategy_a                | 0.032   | strategy_e4_multiscale    | 0.031        | 0.001    | strategy_e_abs_polarity           | 0.416              | S=68.8%, T=20.8%, L=6.5%, C=3.9%   | drop-candidate |
| S26     | S39_20190130_052313_3  | strategy_e_sliding_window | 0.881   | strategy_e12_amp_filter   | 0.871        | 0.010    | strategy_e11_lane_route           | 0.877              | S=20.5%, T=72.7%, L=3.3%, C=3.6%   | keep           |
| S27     | S40_20190201_033636    | strategy_e_vote_2of3      | 0.436   | strategy_d                | 0.353        | 0.084    | strategy_d                        | 0.646              | S=10.6%, T=53.9%, L=16.1%, C=19.4% | caution        |
| S27     | S40_20190201_033636_2  | strategy_c                | 0.180   | expand_bridge_adaptive_k  | 0.124        | 0.056    | strategy_e_abs_polarity           | 0.419              | S=20.0%, T=29.5%, L=21.9%, C=28.6% | drop-candidate |
| S27     | S40_20190201_033636_3  | strategy_e4_multiscale    | 0.421   | strategy_e3_hysteresis    | 0.398        | 0.023    | strategy_e_abs_polarity           | 0.556              | S=18.9%, T=46.3%, L=13.8%, C=21.1% | caution        |
| S3      | S03_20170605_033654    | strategy_c                | 0.381   | strategy_e_sliding_window | 0.177        | 0.204    | strategy_c                        | 0.500              | S=0.0%, T=96.4%, L=1.8%, C=1.8%    | caution        |
| S3      | S03_20170605_033654_2  | strategy_c                | 0.466   | strategy_e_sliding_window | 0.338        | 0.127    | strategy_e_sliding_window         | 0.702              | S=0.0%, T=85.1%, L=5.3%, C=9.6%    | caution        |
| S3      | S03_20170605_033654_3  | strategy_c                | 0.362   | strategy_e_adaptive_k     | 0.278        | 0.084    | strategy_e_adaptive_k             | 0.624              | S=1.1%, T=75.3%, L=6.5%, C=17.2%   | caution        |
| S4      | S04_20170606_045500    | strategy_c                | 0.439   | strategy_e12_amp_filter   | 0.403        | 0.036    | strategy_c                        | 0.433              | S=1.9%, T=86.1%, L=10.6%, C=1.4%   | caution        |
| S4      | S04_20170606_045500_2  | expand_bridge_adaptive_k  | 0.906   | expand_bridge_soft_gate   | 0.899        | 0.007    | strategy_e4_multiscale            | 0.925              | S=0.1%, T=64.7%, L=28.0%, C=7.2%   | keep           |
| S4      | S04_20170606_045500_3  | strategy_a                | 0.957   | strategy_e7_bg_refit      | 0.954        | 0.003    | strategy_e3_hysteresis            | 0.961              | S=0.0%, T=69.7%, L=26.6%, C=3.8%   | keep           |
| S5      | S05_20170607_032937    | strategy_c                | 0.736   | strategy_e_adaptive_k     | 0.607        | 0.129    | strategy_c                        | 0.752              | S=1.3%, T=75.2%, L=8.8%, C=14.7%   | keep           |
| S5      | S05_20170607_032937_2  | expand_bridge_soft_gate   | 0.787   | expand_bridge_adaptive_k  | 0.765        | 0.022    | expand_bridge_confidence_weighted | 0.819              | S=1.4%, T=64.8%, L=13.2%, C=20.6%  | keep           |
| S5      | S05_20170607_032937_3  | expand_bridge_soft_gate   | 0.917   | strategy_e13_self_train   | 0.912        | 0.005    | expand_bridge_dynamic_gap         | 0.939              | S=1.2%, T=76.2%, L=10.3%, C=12.3%  | keep           |
| S6      | S06_20170817_034716    | strategy_c                | 0.440   | strategy_e12_amp_filter   | 0.386        | 0.054    | strategy_e_abs_polarity           | 0.583              | S=0.6%, T=88.7%, L=7.3%, C=3.4%    | caution        |
| S6      | S06_20170817_034716_2  | strategy_b                | 0.805   | strategy_c                | 0.788        | 0.017    | strategy_e9_frontal_avg           | 0.989              | S=12.7%, T=84.6%, L=2.2%, C=0.5%   | keep           |
| S6      | S06_20170817_034716_3  | strategy_c                | 0.730   | strategy_b                | 0.704        | 0.026    | strategy_e11_lane_route           | 0.991              | S=9.7%, T=85.2%, L=3.7%, C=1.4%    | keep           |
| S7      | S07_20170927_055215    | strategy_c                | 0.819   | strategy_e12_amp_filter   | 0.814        | 0.006    | strategy_e                        | 0.984              | S=11.7%, T=86.1%, L=1.6%, C=0.5%   | keep           |
| S7      | S07_20170927_055215_2  | strategy_c                | 0.464   | strategy_e_adaptive_k     | 0.442        | 0.022    | strategy_e_abs_polarity           | 0.470              | S=11.5%, T=81.4%, L=5.9%, C=1.3%   | caution        |
| S7      | S07_20170927_055215_3  | strategy_e12_amp_filter   | 0.740   | strategy_e13_self_train   | 0.740        | 0.000    | strategy_e11_lane_route           | 0.932              | S=26.2%, T=70.5%, L=3.3%, C=0.0%   | keep           |

## Low-Recall Morphology Investigation

- Broad result: low recall is driven more by long and closure-like events than by short events when looking across all competitive strategies.
- Averaged across the top-12 competitive strategies shown below, the mean recall penalty is `-0.189` on long-heavy segments and `-0.169` on closure-heavy segments, versus `-0.069` on short-heavy segments.
- That means the dominant global issue is not simply tiny blinks. The stronger universal failure mode is slower or sustained ocular events.
- Still, the hardest individual outliers are mixed: some are closure-heavy (`S27` family), some are short-heavy (`S26/S39_20190130_052313_2`, `S22/S35_20190123_040805_3`), and some are typical-duration but likely low-SNR/noisy (`S17/S30_20190114_040013_3`).

| strategy                  | mean_pair_f1 | recall_delta_high_long_vs_low_long | recall_delta_high_closure_vs_other | recall_delta_high_short_vs_other |
| ------------------------- | ------------ | ---------------------------------- | ---------------------------------- | -------------------------------- |
| strategy_c                | 0.623        | -0.175                             | -0.161                             | -0.154                           |
| expand_bridge_sw_onset    | 0.601        | -0.213                             | -0.186                             | -0.063                           |
| expand_bridge_soft_gate   | 0.599        | -0.170                             | -0.155                             | -0.057                           |
| expand_bridge_adaptive_k  | 0.597        | -0.186                             | -0.170                             | -0.067                           |
| strategy_e12_amp_filter   | 0.591        | -0.163                             | -0.158                             | -0.063                           |
| strategy_e_sliding_window | 0.590        | -0.234                             | -0.198                             | -0.055                           |
| strategy_e13_self_train   | 0.588        | -0.188                             | -0.169                             | -0.052                           |
| strategy_e_adaptive_k     | 0.587        | -0.204                             | -0.178                             | -0.061                           |
| strategy_e_expand_bridge  | 0.581        | -0.176                             | -0.158                             | -0.061                           |
| expand_bridge_dynamic_low | 0.581        | -0.177                             | -0.160                             | -0.060                           |
| expand_bridge_dynamic_gap | 0.580        | -0.176                             | -0.156                             | -0.059                           |
| strategy_e_slope_guard    | 0.577        | -0.205                             | -0.180                             | -0.071                           |

## Hardest Segments

| subject | segment               | best_strategy           | best_f1 | best_recall | duration_mix                       | flag           |
| ------- | --------------------- | ----------------------- | ------- | ----------- | ---------------------------------- | -------------- |
| S11     | S24_20181227_034657_3 | strategy_b              | 0.008   | 1.000       | S=0.0%, T=100.0%, L=0.0%, C=0.0%   | drop-candidate |
| S26     | S39_20190130_052313_2 | strategy_a              | 0.032   | 0.221       | S=68.8%, T=20.8%, L=6.5%, C=3.9%   | drop-candidate |
| S22     | S35_20190123_040805_3 | strategy_c              | 0.061   | 0.135       | S=59.6%, T=32.7%, L=3.8%, C=3.8%   | drop-candidate |
| S17     | S30_20190114_040013_3 | strategy_e_abs_polarity | 0.124   | 0.243       | S=1.8%, T=83.3%, L=14.0%, C=0.8%   | drop-candidate |
| S11     | S24_20181227_034657_2 | strategy_d              | 0.152   | 0.241       | S=14.5%, T=49.2%, L=19.8%, C=16.4% | drop-candidate |
| S20     | s33_20190117_042235_2 | strategy_d              | 0.153   | 0.249       | S=27.5%, T=37.2%, L=19.2%, C=16.0% | drop-candidate |
| S27     | S40_20190201_033636_2 | strategy_c              | 0.180   | 0.171       | S=20.0%, T=29.5%, L=21.9%, C=28.6% | drop-candidate |
| S20     | s33_20190117_042235_3 | expand_bridge_sw_onset  | 0.258   | 0.364       | S=0.0%, T=100.0%, L=0.0%, C=0.0%   | caution        |
| S3      | S03_20170605_033654_3 | strategy_c              | 0.362   | 0.570       | S=1.1%, T=75.3%, L=6.5%, C=17.2%   | caution        |
| S3      | S03_20170605_033654   | strategy_c              | 0.381   | 0.500       | S=0.0%, T=96.4%, L=1.8%, C=1.8%    | caution        |
| S27     | S40_20190201_033636_3 | strategy_e4_multiscale  | 0.421   | 0.516       | S=18.9%, T=46.3%, L=13.8%, C=21.1% | caution        |
| S27     | S40_20190201_033636   | strategy_e_vote_2of3    | 0.436   | 0.344       | S=10.6%, T=53.9%, L=16.1%, C=19.4% | caution        |

## Recommended Use

- If you want the best pooled detector with strong recall: prefer `expand_bridge_adaptive_k`, `expand_bridge_soft_gate`, or `strategy_e_expand_bridge`.
- If you want the best per-segment precision-weighted winner on cleaner pairs: `strategy_c` remains the main specialist.
- If a subject is dominated by high-quality, repeatable segments (`S12`, `S19`, `S23`, `S24`), subject-tuned E-family variants such as `strategy_e13_self_train`, `strategy_e12_amp_filter`, and `expand_bridge_soft_gate` become strong choices.
- If the subject contains many long or closure-like events, expect recall pain for almost every strategy. The expand-bridge family degrades less gracefully than ideal, but it still stays closer to the top than most non-bridge alternatives.

## Drop Candidates

| subject | subject_action | mean_best_f1 | min_best_f1 |
| ------- | -------------- | ------------ | ----------- |
| S11     | drop-candidate | 0.286        | 0.008       |
| S17     | caution        | 0.513        | 0.124       |
| S20     | drop-candidate | 0.400        | 0.153       |
| S22     | caution        | 0.474        | 0.061       |
| S26     | drop-candidate | 0.549        | 0.032       |
| S27     | drop-candidate | 0.346        | 0.180       |
| S3      | caution        | 0.403        | 0.362       |

## Bottom Line

- For subject or segment-specific deployment, use this report as a pair-level routing guide, not as a replacement for the pooled leaderboard in `tutorial/report_first_iteration.md`.
- The answer to the morphology question is: mostly slow/long and closure-like events, not just short blinks. Short blinks explain a few severe outliers, but the larger cross-strategy recall loss tracks longer-duration ocular events.
