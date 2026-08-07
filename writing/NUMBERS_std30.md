# Frozen numbers (std=3.0 re-run, runs_second_iteration)


## EXP2 — four-condition headline (best-channel-per-session)
[new] Raja:
    Proposed-Med    F1=0.8777  P=0.8921  R=0.8856  n=46
    Proposed-Mean   F1=0.8671  P=0.8962  R=0.8691  n=46
    BLINKER-concat  F1=0.7644  P=0.6774  R=0.9531  n=46
    MNE-annot       F1=0.6526  P=0.7122  R=0.6868  n=46
[new] Cao2018:
    Proposed-Med    F1=0.8087  P=0.7751  R=0.8744  n=58
    Proposed-Mean   F1=0.8041  P=0.7875  R=0.8536  n=58
    BLINKER-concat  F1=0.6924  P=0.5660  R=0.9826  n=58
    MNE-annot       F1=0.5101  P=0.5843  R=0.5550  n=58
[base] Raja:
    Proposed-Med    F1=0.8581  P=0.9092  R=0.8479  n=46
    Proposed-Mean   F1=0.8448  P=0.9105  R=0.8314  n=46
    BLINKER-concat  F1=0.7644  P=0.6774  R=0.9531  n=46
    MNE-annot       F1=0.6526  P=0.7122  R=0.6868  n=46
[base] Cao2018:
    Proposed-Med    F1=0.7879  P=0.8086  R=0.8033  n=58
    Proposed-Mean   F1=0.7749  P=0.8170  R=0.7767  n=58
    BLINKER-concat  F1=0.6924  P=0.5660  R=0.9826  n=58
    MNE-annot       F1=0.5101  P=0.5843  R=0.5550  n=58

## EXP2 — pooled (Raja+Cao, 104 sessions), new run
    Proposed-Med    F1=0.8392  P=0.8268  R=0.8794  n=104
    Proposed-Mean   F1=0.8320  P=0.8356  R=0.8604  n=104
    BLINKER-concat  F1=0.7242  P=0.6153  R=0.9695  n=104
    MNE-annot       F1=0.5731  P=0.6409  R=0.6133  n=104

## EXP2 — cross-dataset gap (Raja - Cao), new run
    Proposed-Med    Raja=0.8777  Cao=0.8087  gap(R-C)=+0.0690
    Proposed-Mean   Raja=0.8671  Cao=0.8041  gap(R-C)=+0.0630
    BLINKER-concat  Raja=0.7644  Cao=0.6924  gap(R-C)=+0.0720
    MNE-annot       Raja=0.6526  Cao=0.5101  gap(R-C)=+0.1424

## CHANNEL SELECTION FREQUENCY (new run, exp2 argmax-F1 channel)
[Raja]
    pooled selections n=184: E9=80(43.5%), E22=68(37.0%), E3=15(8.2%), E23=13(7.1%), E124=5(2.7%), E24=2(1.1%)
    Proposed-Med vs Proposed-Mean same channel: 89.1% (41/46)
    all-four agree: 21.7% (10/46)
[Cao2018]
    pooled selections n=232: FP1=122(52.6%), FP2=61(26.3%), F7=17(7.3%), F8=16(6.9%), F3=12(5.2%), F4=4(1.7%)
    Proposed-Med vs Proposed-Mean same channel: 82.8% (48/58)
    all-four agree: 17.2% (10/58)

## ERROR STRUCTURE (mean per-session FP/FN at best-channel row, new run, pooled)
    Proposed-Med    FP=180.7  FN=151.7  FP:FN=1.192  regime=FP-heavy
    Proposed-Mean   FP=162.6  FN=184.4  FP:FN=0.882  regime=FN-heavy
    BLINKER-concat  FP=641.5  FN=20.4  FP:FN=31.410  regime=FP-heavy
    MNE-annot       FP=207.6  FN=531.8  FP:FN=0.390  regime=FN-heavy

## BEST/WORST SESSION + SUBJECT (Proposed-Med, new run, pooled 104)
    n sessions=104  F1 range 0.4088..0.9946  median=0.8808
    best session: Cao2018 S55/090930n F1=0.9946 (ch FP2)
    worst session: Cao2018 S31/061103n F1=0.4088 (ch FP2, tp=523 fp=64 fn=1449)
    n subjects=44  subject mean-F1 median=0.8420
    best subject: Cao2018 S55 mean_f1=0.9946 (1 sess)
    worst subject: Cao2018 S31 mean_f1=0.5244 (2 sess)

## EXP3 epoch duration (Proposed-Med best-channel-per-session)
    Raja: 10s=0.8709, 20s=0.8749, 30s=0.8777, 40s=0.8717, 50s=0.8778, 60s=0.8754, 120s=0.8531
    Cao2018: 10s=0.8086, 20s=0.8087, 30s=0.8087, 40s=0.8119, 50s=0.8121, 60s=0.8176, 120s=0.8160
    Pooled (104):
      10s=0.8362, 20s=0.8380, 30s=0.8392, 40s=0.8383, 50s=0.8412, 60s=0.8432, 120s=0.8324

## EXP4 boundary tolerance / IoU (Proposed-Med best-channel-per-session)
    Raja: iou0.0=0.9545, iou0.1=0.8754, iou0.2=0.8325, iou0.3=0.7541, iou0.5=0.4507
    Cao2018: iou0.0=0.9506, iou0.1=0.8176, iou0.2=0.7863, iou0.3=0.6708, iou0.5=0.2247

## EXP5 n_min sensitivity (Proposed-Med best-channel-per-session)
    Raja: nmin1=0.8777, nmin2=0.8811, nmin3=0.8839, nmin5=0.8839
    Cao2018: nmin1=0.8087, nmin2=0.8087, nmin3=0.8088, nmin5=0.8095

## EXP7 epoch-health effect (Proposed-Med best-channel-per-session)
    Raja: health-on=0.8717  health-off=0.8777  delta=-0.0060
    Cao2018: health-on=0.9086  health-off=0.8087  delta=+0.1000

## EXP8 long-blink (Proposed-Med best-channel-per-session by category)
    Raja: GT total=31095 normal=28706 long=2389 (7.7% long)
        all     recall=0.8856  F1=0.8777
        normal  recall=0.8967  F1=0.8758
        long    recall=0.7668  F1=0.5434
    Cao2018: GT total=85318 normal=77057 long=8261 (9.7% long)
        all     recall=0.8744  F1=0.8087
        normal  recall=0.8693  F1=0.7912
        long    recall=0.8027  F1=0.4606
    POOLED GT total=116413 normal=105763 long=10650 (9.1% long)
    POOLED normal recall=0.8814
    POOLED long recall=0.7868

## EXP1 per-channel performance (median, selection=all, mean across sessions)
[Raja] top channels:
    E9     region=frontal    P=0.864 R=0.895 F1=0.868
    E22    region=frontal    P=0.866 R=0.886 F1=0.862
    E3     region=frontal    P=0.870 R=0.772 F1=0.801
    E23    region=frontal    P=0.819 R=0.713 F1=0.734
    E24    region=frontal    P=0.640 R=0.391 F1=0.451
    E124   region=frontal    P=0.697 R=0.370 F1=0.446
    E28    region=central    P=0.385 R=0.071 F1=0.112
    bottom channels (mean F1): E58=0.017, E96=0.017, E98=0.017, E52=0.017
    region mean F1: frontal=0.605, central=0.054, occipital=0.027, parietal=0.018
[Cao2018] top channels:
    FP1    region=frontal    P=0.742 R=0.900 F1=0.795
    FP2    region=frontal    P=0.741 R=0.873 F1=0.783
    F7     region=frontal    P=0.709 R=0.563 F1=0.596
    F3     region=frontal    P=0.726 R=0.543 F1=0.589
    F8     region=frontal    P=0.708 R=0.547 F1=0.589
    F4     region=frontal    P=0.718 R=0.524 F1=0.574
    FC3    region=central    P=0.669 R=0.370 F1=0.438
    bottom channels (mean F1): T5=0.092, T6=0.082, O2=0.033, O1=0.031
    region mean F1: frontal=0.654, central=0.377, parietal=0.155, temporal_parietal=0.140, occipital=0.059

## EXP1/EXP2 best fixed single channel vs best fixed group (median / Proposed-Med)
[Raja] best fixed single: single:E22=0.8373 | best fixed group: frontal_right=0.6659
    all singles: E22=0.837, E9=0.834, E3=0.752, E23=0.676
    all groups:  frontal_right=0.666, frontal=0.584, frontal_left=0.513
[Cao2018] best fixed single: single:FP1=0.7765 | best fixed group: frontal_left=0.6611
    all singles: FP1=0.777, FP2=0.756
    all groups:  frontal_left=0.661, frontal=0.642, frontal_right=0.617

## WILCOXON: Proposed-Med vs BLINKER-concat (session-level best-channel F1, new run)
    raja    PM vs BLINKER-concat  d_mean=+0.1133 W=883.0 p=4.85e-05 p_bonf=4.37e-04 r=0.183 CI=[+0.0537,+0.1733] n=46
    raja    PM vs MNE-annot       d_mean=+0.2251 W=893.0 p=2.83e-05 p_bonf=2.54e-04 r=0.174 CI=[+0.1303,+0.3280] n=46
    raja    PM vs Proposed-Mean   d_mean=+0.0106 W=628.0 p=1.37e-02 p_bonf=1.23e-01 r=0.419 CI=[+0.0029,+0.0201] n=46
    cao     PM vs BLINKER-concat  d_mean=+0.1163 W=1588.0 p=7.09e-09 p_bonf=6.38e-08 r=0.072 CI=[+0.0847,+0.1472] n=58
    cao     PM vs MNE-annot       d_mean=+0.2985 W=1565.0 p=1.97e-08 p_bonf=1.78e-07 r=0.085 CI=[+0.2145,+0.3847] n=58
    cao     PM vs Proposed-Mean   d_mean=+0.0046 W=948.0 p=2.37e-01 p_bonf=1.00e+00 r=0.446 CI=[-0.0000,+0.0100] n=58
    pooled  PM vs BLINKER-concat  d_mean=+0.1150 W=4791.0 p=1.17e-11 p_bonf=1.05e-10 r=0.123 CI=[+0.0832,+0.1468] n=104
    pooled  PM vs MNE-annot       d_mean=+0.2661 W=4781.0 p=1.46e-11 p_bonf=1.31e-10 r=0.124 CI=[+0.2026,+0.3329] n=104
    pooled  PM vs Proposed-Mean   d_mean=+0.0072 W=3130.0 p=1.88e-02 p_bonf=1.69e-01 r=0.427 CI=[+0.0029,+0.0123] n=104

## FAILURE ANALYSIS: bottom-5 sessions (Proposed-Med best-channel, new run)
[Raja] median GT(tp+fn)=526
    S16/S29_20190111_034326_3      F1=0.421 ch=E9    tp=494 fp=32 fn=1328 GT=1822
    S24/S38_20190129_035118_2      F1=0.600 ch=E9    tp=490 fp=26 fn=627 GT=1117
    S1/S01_20170519_043933_3       F1=0.645 ch=E22   tp=127 fp=135 fn=5 GT=132
    S18/S31_20190115_035853_2      F1=0.685 ch=E22   tp=317 fp=154 fn=138 GT=455
    S3/S03_20170605_033654_3       F1=0.690 ch=E22   tp=70 fp=42 fn=21 GT=91
[Cao2018] median GT(tp+fn)=1314
    S31/061103n                    F1=0.409 ch=FP2   tp=523 fp=64 fn=1449 GT=1972
    S53/090925m                    F1=0.416 ch=FP1   tp=290 fp=737 fn=77 GT=367
    S49/080527n                    F1=0.554 ch=F7    tp=147 fp=210 fn=27 GT=174
    S42/070105n                    F1=0.607 ch=FP2   tp=1010 fp=1004 fn=305 GT=1315
    S01/051017m                    F1=0.616 ch=FP1   tp=331 fp=335 fn=77 GT=408
