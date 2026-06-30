"""Private region-masking utilities for region-aware processing operations.

Shared by the region-referencing steps so the rectangle-mask logic is not
duplicated. Not part of the public API: import only within ``processing.image``.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import numpy.typing as npt

from snomniman.core.exceptions import ProcessingError


def _rect_mask(
    x_coords: npt.NDArray[np.float64],
    y_coords: npt.NDArray[np.float64],
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
) -> npt.NDArray[np.bool_]:
    """Boolean mask of pixels whose centers fall in [x_min, x_max] x [y_min, y_max]."""
    mx = (x_coords >= x_min) & (x_coords <= x_max)
    my = (y_coords >= y_min) & (y_coords <= y_max)
    return np.asarray(my[:, None] & mx[None, :], dtype=bool)


def region_complex_values(
    values: npt.NDArray[Any],
    x_coords: npt.NDArray[np.float64],
    y_coords: npt.NDArray[np.float64],
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    step_id: str,
) -> npt.NDArray[Any]:
    """Finite complex values inside the reference rectangle. Raises if empty.

    Parameters
    ----------
    values:
        2-D complex channel array (shape ``(ny, nx)``).
    x_coords / y_coords:
        1-D coordinate arrays (canonical nm, monotonically increasing).
    x_min, x_max, y_min, y_max:
        Rectangle bounds in canonical nm (already validated x_min < x_max etc.).
    step_id:
        The calling step's ``step_id``, used in error messages.
    """
    mask = _rect_mask(x_coords, y_coords, x_min, x_max, y_min, y_max)
    if not mask.any():
        raise ProcessingError(
            f"{step_id}: reference region "
            f"x=[{x_min:.0f}, {x_max:.0f}] nm, y=[{y_min:.0f}, {y_max:.0f}] nm "
            f"selects no pixels; dataset spans "
            f"x=[{float(x_coords.min()):.0f}, {float(x_coords.max()):.0f}] nm, "
            f"y=[{float(y_coords.min()):.0f}, {float(y_coords.max()):.0f}] nm"
        )
    finite = np.isfinite(values)
    sel = values[mask & finite]
    if sel.size == 0:
        raise ProcessingError(
            f"{step_id}: reference region contains no finite complex values"
        )
    return sel


def circular_mean_phase(sel: npt.NDArray[Any]) -> float:
    """Amplitude-weighted circular mean phase of a complex array.

    This is ``angle(mean(sel))``: the angle of the mean complex vector. It is the
    correct way to average phase as a cyclic quantity - an arithmetic mean of
    wrapped angles would be wrong near the +/-pi branch cut (e.g. averaging +179 deg
    and -179 deg arithmetically gives 0 deg instead of 180 deg).
    """
    return float(np.angle(np.mean(sel)))


def mean_amplitude(sel: npt.NDArray[Any], step_id: str) -> float:
    """Mean amplitude of a complex array. Raises if the mean is not positive.

    A zero or non-positive mean amplitude (all-zero reference region) cannot serve
    as a normalization datum - division would produce inf or NaN.
    """
    val = float(np.mean(np.abs(sel)))
    if not (val > 0.0):
        raise ProcessingError(
            f"{step_id}: reference region mean amplitude is zero or non-finite; "
            "cannot normalize - choose a region with non-zero signal"
        )
    return val
