"""Polynomial plane (surface) leveling for real-valued image channels.

``PlaneLevel`` is the first production processing operation and the reference
implementation for all future :class:`~snomniman.processing.ProcessingStep`
subclasses.  It fits an order-1 (plane) or higher polynomial surface to the
target channel by ordinary least squares, subtracts the surface, and returns
a new Dataset with the leveled channel and all other channels unchanged.

Scientific validation: the algorithm is tested against analytical solutions
(synthetic tilted planes with known slopes); see ``tests/test_processing_image.py``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import numpy.typing as npt
import xarray as xr

from snomniman.core import Capability, DataKind, Dataset, Metadata
from snomniman.core.exceptions import ProcessingError
from snomniman.processing.registry import register
from snomniman.processing.step import CHANNEL_REAL, ParameterSpec, ProcessingStep


def _poly_design_matrix(
    x_flat: npt.NDArray[np.float64],
    y_flat: npt.NDArray[np.float64],
    order: int,
) -> npt.NDArray[np.float64]:
    """Polynomial design matrix for 2-D pixel coordinates (order 1-3).

    order=1 (plane):      columns [x, y, 1]            — 3 coefficients
    order=2 (paraboloid): columns [x², xy, y², x, y, 1] — 6 coefficients
    order=3:              10 coefficients
    """
    cols: list[npt.NDArray[np.float64]] = []
    for deg in range(order, -1, -1):
        for px in range(deg, -1, -1):
            py = deg - px
            cols.append((x_flat**px) * (y_flat**py))
    return np.column_stack(cols)


def fit_surface(
    values: npt.NDArray[np.float64],
    x: npt.NDArray[np.float64],
    y: npt.NDArray[np.float64],
    order: int = 1,
) -> npt.NDArray[np.float64]:
    """Fit a polynomial surface to ``values`` on grid (``x``, ``y``) and return it.

    ``values`` is 2-D (ny, nx); ``x`` and ``y`` are 1-D coordinate arrays.
    Returns a 2-D surface array of the same shape, ready for subtraction.
    Uses ordinary least squares via :func:`numpy.linalg.lstsq`.
    """
    xx, yy = np.meshgrid(x, y)
    A = _poly_design_matrix(xx.ravel(), yy.ravel(), order)
    coeffs, _, _, _ = np.linalg.lstsq(A, values.ravel(), rcond=None)
    return (A @ coeffs).reshape(values.shape)


@register
class PlaneLevel(ProcessingStep):
    """Subtract a fitted polynomial surface from a real-valued channel.

    The surface is fitted to all pixels of ``channel`` (default ``"Z"``) using
    ordinary least squares and subtracted.  All other channels are preserved
    unchanged.  The input Dataset is never modified.

    ``order=1`` (default) removes global tilt.  ``order=2`` removes a
    paraboloid (bowl-shaped background).  Higher orders remove more complex
    backgrounds but may inadvertently subtract real surface features on small
    samples — use with care.
    """

    step_id = "image.plane_level"
    version = 1
    description = "Subtract a fitted polynomial surface from the target channel."
    deterministic = True
    required_capabilities = (Capability.SPATIAL_2D,)

    @classmethod
    def param_specs(cls) -> list[ParameterSpec]:
        return [
            ParameterSpec(
                "channel",
                "Real-valued channel to level (e.g. 'Z').",
                (str,),
                required=False,
                default="Z",
                channel_role=CHANNEL_REAL,
            ),
            ParameterSpec(
                "order",
                "Polynomial order: 1 = plane, 2 = paraboloid, 3 = higher.",
                (int,),
                required=False,
                default=1,
                choices=(1, 2, 3),
            ),
        ]

    def _execute(
        self, inputs: Mapping[str, Dataset]
    ) -> tuple[xr.Dataset, DataKind, Metadata]:
        primary = inputs["primary"]
        channel: str = self._params["channel"]
        order: int = self._params["order"]

        if channel not in primary.channel_names:
            raise ProcessingError(
                f"{self.step_id}: channel {channel!r} not found; "
                f"available: {primary.channel_names}"
            )
        if primary.is_complex(channel):
            raise ProcessingError(
                f"{self.step_id}: channel {channel!r} is complex; "
                "plane leveling requires a real-valued channel"
            )

        raw = primary.data
        values = np.asarray(raw[channel].values, dtype=np.float64)
        x = np.asarray(primary.coordinate("x").values, dtype=np.float64)
        y = np.asarray(primary.coordinate("y").values, dtype=np.float64)

        surface = fit_surface(values, x, y, order)
        leveled = values - surface

        new_vars: dict[str, xr.DataArray] = {}
        for raw_name, var in raw.data_vars.items():
            name = str(raw_name)
            if name == channel:
                arr: npt.NDArray[Any] = leveled.astype(var.dtype)
            else:
                arr = np.array(var.values, copy=True)
            new_vars[name] = xr.DataArray(
                arr, coords=var.coords, dims=var.dims, attrs=dict(var.attrs)
            )
        new_data = xr.Dataset(new_vars, coords=raw.coords, attrs=dict(raw.attrs))
        return new_data, primary.kind, primary.metadata


__all__ = ["PlaneLevel", "fit_surface"]
