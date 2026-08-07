# Round-2 frozen numbers (runs_second_iteration, std=3.0)


## R3 hemisphere symmetry (Proposed-Med, best-channel-per-session within group)
    Raja: frontal_left=0.8536  frontal_right=0.8459  |delta|=0.0077
    Cao2018: frontal_left=0.7841  frontal_right=0.7785  |delta|=0.0056

## R4 within-subject consistency (Proposed-Med best-channel F1)
    subjects with >=2 sessions: 33 covering 93 sessions
    mean within-subject SD of F1 = 0.0812  (median 0.0638)
    between-subject SD of subject-mean F1 = 0.1153
    Raja: ICC(1)=0.499
    Cao2018: ICC(1)=0.283

## R5 epoch-health benefit vs baseline F1 / GT count (Proposed-Med)
    Raja: n=46 mean_delta=-0.0060
        corr(baseline_F1, delta)=-0.182 (p=0.2260); corr(GT_count, delta)=-0.185 (p=0.2191)
        baseline<0.7: n=5 mean_gain=+0.0349 | baseline>=0.7 mean_gain=-0.0110
    Cao2018: n=58 mean_delta=+0.0990
        corr(baseline_F1, delta)=-0.795 (p=0.0000); corr(GT_count, delta)=-0.201 (p=0.1294)
        baseline<0.7: n=12 mean_gain=+0.2338 | baseline>=0.7 mean_gain=+0.0639

## R2 count agreement cross-check (best-channel, pooled 104)
    Proposed-Med    r=0.9362 mean(pred/truth)=1.110
    Proposed-Mean   r=0.9172 mean(pred/truth)=1.075
    BLINKER-concat  r=0.8626 mean(pred/truth)=1.991
    MNE-annot       r=0.4653 mean(pred/truth)=0.942
