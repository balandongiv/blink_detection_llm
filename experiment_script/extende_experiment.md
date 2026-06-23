
### 2. Compare channel-selection strategies

Test the same pipeline, but under several channel sets:

| Condition                           | Channels used for Stage A (HydroCel)                                                                                                | EEG channels                                         | Purpose                                            |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- | -------------------------------------------------- |
| Single-channel                      | Each channel individually                                                                                                           | Each channel individually                            | Identifies the most informative electrodes         |
| Frontal left (`FL`)                 | 22, 23, 24, 33                                                                                                                      | Fp1, AF3, F3, F7                                     | Tests left frontal blink-related activity          |
| Frontal right (`FR`)                | 3, 9, 122, 124                                                                                                                      | AF4, Fp2, F8, F4                                     | Tests right frontal blink-related activity         |
| Frontal bilateral (`FL_FR`)         | 3, 9, 22, 23, 24, 33, 122, 124                                                                                                      | Fp1, Fp2, AF3, AF4, F3, F4, F7, F8                   | Tests combined frontal activity                    |
| FTC / central left (`CL`)           | 13, 28, 36, 45                                                                                                                      | FC1, FC5, C3, T7                                     | Left central-temporal control condition            |
| FTC / central right (`CR`)          | 104, 108, 112, 117                                                                                                                  | C4, T8, FC2, FC6                                     | Right central-temporal control condition           |
| FTC / central bilateral (`CL_CR`)   | 13, 28, 36, 45, 104, 108, 112, 117                                                                                                  | FC1, FC5, C3, T7, C4, T8, FC2, FC6                   | Combined central-temporal control condition        |
| Parietal left (`PL`)                | 37, 47, 52, 58                                                                                                                      | CP1, CP5, P3, P7                                     | Tests left parietal activity                       |
| Parietal right (`PR`)               | 87, 92, 96, 98                                                                                                                      | CP2, P4, P8, CP6                                     | Tests right parietal activity                      |
| Parietal bilateral (`PL_PR`)        | 37, 47, 52, 58, 87, 92, 96, 98                                                                                                      | CP1, CP5, P3, P7, CP2, P4, P8, CP6                   | Tests combined parietal activity                   |
| Occipital left (`OL`)               | 67, 70                                                                                                                              | PO3, O1                                              | Tests left posterior/occipital activity            |
| Occipital right (`OR`)              | 77, 83                                                                                                                              | PO4, O2                                              | Tests right posterior/occipital activity           |
| Occipital bilateral (`OR_OL`)       | 67, 70, 77, 83                                                                                                                      | PO3, O1, PO4, O2                                     | Tests combined posterior/occipital activity        |
| Posterior bilateral (`PL_PR_OR_OL`) | 37, 47, 52, 58, 67, 70, 77, 83, 87, 92, 96, 98                                                                                      | CP1, CP5, P3, P7, CP2, P4, P8, CP6, PO3, O1, PO4, O2 | Tests sensitivity to non-blink posterior artefacts |
| Midline / unassigned (`NA`)         | 11, 14, 55, 129                                                                                                                     | Fz, Oz, Pz, Cz                                       | Optional midline comparison condition              |
| All channels                        | 3, 9, 11, 13, 14, 22, 23, 24, 28, 33, 36, 37, 45, 47, 52, 55, 58, 67, 70, 77, 83, 87, 92, 96, 98, 104, 108, 112, 117, 122, 124, 129 | All listed channels                                  | Baseline / current implementation                  |


### 3. Compare channel-combination rules

Your current code uses an **“any-channel” rule**:

[
\text{flag epoch if any channel exceeds its threshold}
]
