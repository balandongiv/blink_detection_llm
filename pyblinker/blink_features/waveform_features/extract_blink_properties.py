from typing import Literal, Tuple

import pandas as pd

from pyblinker.blink_features._blink_metrics_shared import normalize_modality
from pyblinker.blink_features.kinematics.core_metrics import (
    compute_amp_vel_ratio_base,
    compute_amp_vel_ratio_tent,
    compute_amp_vel_ratio_zero_to_max,
    compute_blink_velocity,
    compute_inter_blink_max_vel,
)
from pyblinker.blink_features.morphology.core_metrics import (
    compute_blink_durations,
    compute_blink_peak_times,
    compute_time_base_shut,
    compute_time_zero_shut,
)


class BlinkProperties:
    """
    Return a structure with blink shapes and properties for individual blinks
    % Return a structure with blink shapes and properties for individual blinks
    %
    % Parameters:
    %     signalData    signalData structure
    %     params        params structure with parameters
    %     blinkProps    (output) structure with the blink properties
    %     blinkFits     (output) structure with the blink landmarks
    """

    def __init__(self, candidate_signal, df, srate, params, *, fitted: bool = True):
        """Initializes BlinkProperties object to calculate blink features.

        This class calculates various properties of detected blinks based on
        the input candidate_signal, DataFrame of blink fits, sampling rate, and parameters.
        It initializes blink velocity, durations, amplitude-velocity ratios,
        and time-related features.

        The optional ``params['modality']`` flag controls whether zero-based
        landmarks are considered. ``"ear"`` modality retains the schema but
        fills all ``*_zero`` columns with ``NaN`` because Eye Aspect Ratio
        blinks lack zero crossings.

        Parameters
        ----------
        candidate_signal : numpy.ndarray
            The raw signal candidate_signal from which blinks were detected.
        df : pandas.DataFrame
            DataFrame containing blink fit parameters, expected to have columns like
            'left_base', 'right_base', 'left_zero', 'right_zero', 'right_x_intercept', 'left_x_intercept',
            'left_base_half_height', 'right_base_half_height', 'left_zero_half_height', 'right_zero_half_height',
            'max_blink', 'max_value', 'aver_right_velocity', 'aver_left_velocity', 'x_intersect', 'y_intersect',
            'left_x_intercept_int', 'right_x_intercept_int', 'start_shut_tst', 'peaks_pos_vel_base', 'peaks_pos_vel_zero'.
        srate : float
            Sampling rate of the signal candidate_signal in Hz.
        params : dict
            Dictionary of parameters, expected to contain keys:
                - 'shut_amp_fraction': Fraction of maximum amplitude for shut time calculation.
                - 'z_thresholds': Z-score thresholds (structure of thresholds is assumed to be handled internally by methods using it).
        fitted : bool, optional
            If ``True`` additional features requiring blink fitting are computed.
            Defaults to ``True``.
        """
        self.signal_len = None
        self.blink_velocity = None
        self.candidate_signal = candidate_signal
        self.df = df
        self.srate = srate
        self.shut_amp_fraction = params["shut_amp_fraction"]
        self.p_avr_threshold = params["p_avr_threshold"]
        self.z_thresholds = params["z_thresholds"]

        self.modality: Literal["eeg", "ear"] = normalize_modality(
            params.get("modality")
        )

        self.fitted = fitted

        self.df_res = []
        self._run_property_pipeline()

    def _run_property_pipeline(self) -> None:
        """Execute MATLAB-style property extraction stages in order."""

        self.reset_index()
        self.set_blink_velocity()

        self._compute_duration_stage()
        self._compute_amp_velocity_stage()
        self._compute_shut_time_stage()
        self._compute_summary_time_stage()

    def _compute_duration_stage(self) -> None:
        self.set_blink_duration()

    def _compute_amp_velocity_stage(self) -> None:
        self.set_blink_amp_velocity_ratio_zero_to_max()
        self.amplitude_velocity_ratio_base()
        if self.fitted:
            self.amplitude_velocity_ratio_tent()

    def _compute_shut_time_stage(self) -> None:
        self.time_zero_shut()
        self.time_base_shut()

    def _compute_summary_time_stage(self) -> None:
        self.extract_other_times()

    def reset_index(self):
        self.df.reset_index(drop=True, inplace=True)

    def set_blink_velocity(self):
        self.signal_len = self.candidate_signal.shape[0]
        self.blink_velocity = compute_blink_velocity(self.candidate_signal)

    def set_blink_duration(self):
        compute_blink_durations(
            self.df,
            self.srate,
            modality=self.modality,
            fitted=self.fitted,
        )

    def _ensure_velocity(self):
        if self.blink_velocity is None:
            self.set_blink_velocity()

    def set_blink_amp_velocity_ratio_zero_to_max(self):
        """ "Computes and sets both positive and negative amplitude-velocity ratios (zero-to-max)."""
        self._ensure_velocity()
        compute_amp_vel_ratio_zero_to_max(
            self.df,
            self.candidate_signal,
            self.blink_velocity,
            self.srate,
            modality=self.modality,
        )

    def amplitude_velocity_ratio_base(self):
        """
        Blink amplitude-velocity ratio from base to max
        :return:
        """
        self._ensure_velocity()
        compute_amp_vel_ratio_base(
            self.df,
            self.candidate_signal,
            self.blink_velocity,
            self.srate,
        )

    def amplitude_velocity_ratio_tent(self):
        """
         Blink amplitude-velocity ratio estimated from tent slope
        :return:
        """
        compute_amp_vel_ratio_tent(
            self.df,
            self.candidate_signal,
            self.srate,
        )

    def time_zero_shut(self):
        """
        Time zero shut
        :return:
        """
        compute_time_zero_shut(
            self.df,
            self.candidate_signal,
            self.srate,
            modality=self.modality,
            shut_amp_fraction=self.shut_amp_fraction,
        )

    def time_base_shut(self):
        """
        Time base shut
        :return:
        """
        compute_time_base_shut(
            self.df,
            self.candidate_signal,
            self.srate,
            shut_amp_fraction=self.shut_amp_fraction,
            fitted=self.fitted,
        )

    def extract_other_times(self):
        compute_blink_peak_times(
            self.df,
            self.candidate_signal,
            self.srate,
            fitted=self.fitted,
        )
        compute_inter_blink_max_vel(
            self.df,
            self.srate,
            modality=self.modality,
            signal_len=len(self.candidate_signal),
        )

    def blink_bounds(self, row: pd.Series, method: str) -> Tuple[int, int] | None:
        """Return inclusive (left, right) indices for the requested method."""

        method_key = method.lower()
        mapping = {
            "base": ("left_base", "right_base"),
            "zero": ("left_zero", "right_zero"),
            "tent": ("left_x_intercept", "right_x_intercept"),
            "half_base": ("left_base_half_height", "right_base_half_height"),
            "half_zero": ("left_zero_half_height", "right_zero_half_height"),
        }
        if method_key not in mapping:
            raise ValueError(f"Unknown blink boundary method: {method}")
        if self.modality == "ear" and "zero" in method_key:
            return None

        left_col, right_col = mapping[method_key]
        if left_col not in row or right_col not in row:
            return None

        left_val = row[left_col]
        right_val = row[right_col]
        if pd.isna(left_val) or pd.isna(right_val):
            return None

        try:
            left_idx = int(round(float(left_val)))
            right_idx = int(round(float(right_val)))
        except (TypeError, ValueError):
            return None

        if right_idx < left_idx:
            return None
        return left_idx, right_idx
