# Normal Blink
The file `D:\dataset\epoch_blink_development\normal_blink\dev_epo.fif` is an epoch file containing a typical blink event. It serves as a baseline for validating that the epoch-aware pipeline can correctly identify blinks in standard conditions without any bad epochs.
The file `D:\dataset\epoch_blink_development\normal_blink\dev_epo_annotations.csv` contains the corresponding reference annotations for the normal blink event in the epoch file. It is used to compare against the pipeline's output to ensure accurate blink detection under normal conditions.

# Long blink
The file `D:\dataset\epoch_blink_development\long_closure\ear_eog.fif` contains an epoch with a mixture of normal blinks and a
long-duration 
blink event. 
Together in the folder are the corresponding annotations in `D:\dataset\epoch_blink_development\long_closure\ear_eog.csv`, which include the reference blink events for both the normal blinks and the long-duration blink.

There are several label in the annotations.
B-CL mean it is a normal blink closure,
F-CL mean it is a full long blink closure,
HB-CL meaen it is a half blink closure,

However, the fif file and the csv is based on a long continous recording, so the fif file is not epoched. Therefore, 
the pipeline should first epoch the file into either fixed-length epochs, say 30 second, or 60 seconds.