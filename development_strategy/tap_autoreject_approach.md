Based on my search through the autoreject repository, here are the specific code locations that implement peak-to-peak rejection threshold learning:

Core Threshold Learning Functions

1. Main Entry Point: _compute_thresholds() (lines 444-484)
- This is the core function that computes channel-level thresholds
- It handles channel type separation and calls _compute_thresh for each channel in parallel
- Returns a dictionary of thresholds keyed by channel name

# autoreject/autoreject.py:444
def _compute_thresholds(epochs, method='bayesian_optimization',
random_state=None, picks=None, augment=True,
dots=None, verbose=True, n_jobs=1):

2. Per-Channel Threshold Learning: _compute_thresh() (lines 329-392)
- Computes the optimal threshold for a single channel
- Uses either Bayesian Optimization (default) or Random Search
- Key line 357: all_threshes = np.sort(np.ptp(this_data, axis=1)) - calculates peak-to-peak values
- Uses cross-validation to find the best threshold

# autoreject/autoreject.py:329
def _compute_thresh(this_data, method='bayesian_optimization',
cv=10, y=None, random_state=None):
...
all_threshes = np.sort(np.ptp(this_data, axis=1))  # Peak-to-peak calculation

3. Peak-to-Peak Calculation: _ChannelAutoReject.fit() (lines 306-326)
- The actual peak-to-peak computation: line 317 deltas = np.ptp(X, axis=1)
- Filters epochs based on the threshold

# autoreject/autoreject.py:306
def fit(self, X, y=None):
deltas = np.ptp(X, axis=1)  # Peak-to-peak across time dimension
self.deltas_ = deltas
keep = deltas <= self.thresh

Subject-Wise Learning Implementation

High-Level API: AutoReject.fit() (lines 988-1067)
- This is where you'd implement subject-wise learning
- For each subject, create an AutoReject instance and call fit() on that subject's epochs
- Stores per-channel thresholds in self.threshes_ (line 1045)

Cross-Validation Loop: _run_local_reject_cv() (lines 786-860)
- Implements the CV splits for finding optimal parameters
- Line 835: cv_splits = CVSplits(cv.split(X), n_folds)
- Optimizes both n_interpolate and consensus parameters while learning thresholds

How to Use for Subject-Wise Learning

The typical pattern would be:

for subject_id in subject_ids:
# Get subject-specific epochs
subject_epochs = get_epochs_for_subject(subject_id)

      # Fit autoreject independently for this subject
      ar = autoreject.AutoReject(n_interpolate=[1, 4, 32],
                                 random_state=11)
      ar.fit(subject_epochs)

      # Store subject-specific thresholds
      subject_thresholds[subject_id] = ar.threshes_

The thresholds learned in ar.threshes_ are the peak-to-peak rejection thresholds for each channel, learned specifically for that subject's data.