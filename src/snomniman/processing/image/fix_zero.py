"""Fix a height datum: shift a real channel so its minimum / mean / median is zero.

``FixZero`` removes a single constant offset from a real-valued channel (typically
topography ``Z``), setting a defined zero datum. Unlike plane leveling it does **not**
remove tilt or curvature - it shifts the whole channel by one constant, so it is
information-preserving (every height *difference* is unchanged) and is the right tool
once tilt has already been handled, or when the data is already flat and only the
reference level needs fixing.

Scientific rationale & default basis
------------------------------------
AFM/SPM height data has no intrinsic absolute zero: the recorded Z is relative to an
arbitrary scanner/feedback origin, so a datum is chosen before reading feature heights
and depths. The conventional default across scanning-probe software is to put the
**minimum** at zero, so every height is measured upward from the lowest point of the
scan (Gwyddion "Fix Zero" / "Shift Minimum to Zero"; WSxM offset levelling) - hence
``reference="minimum"`` is the default here. ``"mean"`` (zero-mean, convenient for
roughness and cross-scan comparison) and ``"median"`` (robust to a few extreme pixels)
are also offered. The applied shift is a single subtracted constant recorded in
provenance; the height unit (e.g. nm) is unchanged. This note captures design intent
for future maintenance.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

import numpy as np
import numpy.typing as npt
import xarray as xr

from snomniman.core import Capability, DataKind, Dataset, Metadata
from snomniman.core.exceptions import ProcessingError
from snomniman.processing.registry import register
from snomniman.processing.step import CHANNEL_REAL, ParameterSpec, ProcessingStep

#: Datum choices: which statistic of the channel is shifted to zero.
REFERENCE_MINIMUM: Final = "minimum"
REFERENCE_MEAN: Final = "mean"
REFERENCE_MEDIAN: Final = "median"
_REFERENCES: Final = (REFERENCE_MINIMUM, REFERENCE_MEAN, REFERENCE_MEDIAN)


@register
class FixZero(ProcessingStep):
    """Shift a real channel so its minimum (default), mean, or median becomes zero.

    Subtracts a single constant from ``channel`` (default ``"Z"``); all other channels
    are preserved unchanged and the input Dataset is never modified. The shift removes
    only a constant offset - tilt and curvature are untouched (use ``image.plane_level``
    for those).
    """

    step_id = "image.fix_zero"
    version = 1
    description = "Shift a real channel so its minimum, mean, or median is zero."
    deterministic = True
    required_capabilities = (Capability.SPATIAL_2D,)

    @classmethod
    def param_specs(cls) -> list[ParameterSpec]:
        return [
            ParameterSpec(
                "channel",
                "Real-valued channel to zero (e.g. 'Z').",
                (str,),
                required=False,
                default="Z",
                channel_role=CHANNEL_REAL,
            ),
            ParameterSpec(
                "reference",
                "Datum shifted to zero: the channel's minimum, mean, or median.",
                (str,),
                required=False,
                default=REFERENCE_MINIMUM,
                choices=_REFERENCES,
            ),
        ]

    def _execute(
        self, inputs: Mapping[str, Dataset]
    ) -> tuple[xr.Dataset, DataKind, Metadata]:
        primary = inputs["primary"]
        channel: str = self._params["channel"]
        reference: str = self._params["reference"]

        if channel not in primary.channel_names:
            raise ProcessingError(
                f"{self.step_id}: channel {channel!r} not found; "
                f"available: {primary.channel_names}"
            )
        if primary.is_complex(channel):
            raise ProcessingError(
                f"{self.step_id}: channel {channel!r} is complex; "
                "fixing a height datum requires a real-valued channel"
            )

        raw = primary.data
        values = np.asarray(raw[channel].values, dtype=np.float64)
        if not np.any(np.isfinite(values)):
            raise ProcessingError(
                f"{self.step_id}: channel {channel!r} has no finite values to reference"
            )
        offset = _datum(values, reference)
        shifted = values - offset

        new_vars: dict[str, xr.DataArray] = {}
        for raw_name, var in raw.data_vars.items():
            name = str(raw_name)
            if name == channel:
                arr: npt.NDArray[Any] = shifted.astype(var.dtype)
            else:
                arr = np.array(var.values, copy=True)
            new_vars[name] = xr.DataArray(
                arr, coords=var.coords, dims=var.dims, attrs=dict(var.attrs)
            )
        new_data = xr.Dataset(new_vars, coords=raw.coords, attrs=dict(raw.attrs))
        return new_data, primary.kind, primary.metadata


def _datum(values: npt.NDArray[np.float64], reference: str) -> float:
    """The constant to subtract for the chosen datum (over finite pixels only)."""
    if reference == REFERENCE_MINIMUM:
        return float(np.nanmin(values))
    if reference == REFERENCE_MEAN:
        return float(np.nanmean(values))
    return float(np.nanmedian(values))


__all__ = [
    "REFERENCE_MEAN",
    "REFERENCE_MEDIAN",
    "REFERENCE_MINIMUM",
    "FixZero",
]
