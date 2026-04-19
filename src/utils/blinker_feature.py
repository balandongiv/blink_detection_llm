"""

To delete later
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
import hashlib
import pickle
import time

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal


def _sha256_array(x: np.ndarray) -> str:
    x = np.asarray(x)
    h = hashlib.sha256()
    h.update(str(x.shape).encode("utf-8"))
    h.update(str(x.dtype).encode("utf-8"))
    h.update(x.tobytes(order="C"))
    return h.hexdigest()


@dataclass(frozen=True)
class BlinkPropsPickleFixture:
    # Inputs
    candidate_signal: np.ndarray
    df_in: pd.DataFrame
    srate: float
    params: Dict[str, Any]
    fitted: bool

    # Expected output
    df_out: pd.DataFrame

    # Metadata / guardrails
    created_unix: float
    candidate_signal_sha256: str
    notes: Optional[str] = None


def save_blinkprops_pickle(
    path: str,
    *,
    candidate_signal: np.ndarray,
    df_in: pd.DataFrame,
    srate: float,
    params: Dict[str, Any],
    fitted: bool,
    df_out: pd.DataFrame,
    notes: Optional[str] = None,
    protocol: int = pickle.HIGHEST_PROTOCOL,
) -> None:
    """
    Save BlinkProperties inputs + expected output into a single pickle file.
    """
    fixture = BlinkPropsPickleFixture(
        candidate_signal=np.asarray(candidate_signal),
        df_in=df_in.copy(deep=True),
        srate=float(srate),
        params=dict(params),
        fitted=bool(fitted),
        df_out=df_out.copy(deep=True),
        created_unix=time.time(),
        candidate_signal_sha256=_sha256_array(np.asarray(candidate_signal)),
        notes=notes,
    )

    with open(path, "wb") as f:
        pickle.dump(fixture, f, protocol=protocol)


def load_blinkprops_pickle(
    path: str, *, verify_hash: bool = True
) -> BlinkPropsPickleFixture:
    """
    Load the fixture from pickle. Optionally verify candidate_signal hash for integrity.
    """
    with open(path, "rb") as f:
        fixture: BlinkPropsPickleFixture = pickle.load(f)

    if verify_hash:
        expected = fixture.candidate_signal_sha256
        actual = _sha256_array(np.asarray(fixture.candidate_signal))
        if expected != actual:
            raise ValueError(
                "candidate_signal hash mismatch — fixture may be altered/corrupted."
            )

    return fixture


def replay_and_assert_blinkprops(
    fixture: BlinkPropsPickleFixture,
    BlinkPropertiesCls,
    *,
    rtol: float = 1e-6,
    atol: float = 1e-8,
) -> pd.DataFrame:
    """
    Re-run BlinkProperties on saved inputs and assert the produced df matches df_out.
    Returns the newly computed df.
    """
    new_df = BlinkPropertiesCls(
        fixture.candidate_signal,
        fixture.df_in.copy(deep=True),
        fixture.srate,
        fixture.params,
        fitted=fixture.fitted,
    ).df

    assert_frame_equal(
        new_df,
        fixture.df_out,
        check_dtype=True,
        check_exact=True,
        rtol=rtol,
        atol=atol,
    )
    return new_df
