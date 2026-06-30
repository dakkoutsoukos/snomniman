"""Re-reference optical phase: subtract a constant phase from a complex channel.

``PhaseOffset`` rotates a complex optical channel by a constant phase,
``O -> O * exp(-i * dphi)``: the **amplitude is preserved exactly** and only the phase
is shifted. It is the explicit, provenance-recorded phase re-referencing that the
project's phase convention requires (OHD-6D: phase is never silently inverted,
re-referenced, unwrapped, or normalized - any change is an explicit, recorded
operation). The new reference is recorded in ``metadata.conventions.phase_reference``.

Scientific rationale & default basis
------------------------------------
In s-SNOM the *absolute* optical phase has no physical meaning: it depends on the
interferometer path length, the demodulation reference, and instrument drift. Only
phase **contrast** - phase relative to a chosen datum - is interpretable, so phase is
routinely re-referenced before analysis. The robust, convention-correct datum is the
**circular mean** of the channel, ``dphi = angle(mean(O))`` (amplitude-weighted): this
removes the global phase offset while correctly handling phase as a cyclic quantity.
(Taking the arithmetic mean of wrapped phase angles is wrong near the +/-pi wrap - e.g.
+179 deg and -179 deg average to 0 deg instead of 180 deg - which is why the complex
mean is used.) Hence ``reference="mean"`` is the default; ``reference="constant"``
subtracts a user-supplied ``value_rad`` (e.g. to align to a value measured elsewhere).

The richest form - referencing to the mean phase of a chosen *substrate region* - needs
a region parameter and is deliberately deferred to a later phase; whole-image and
constant referencing are valid and complete on their own. This note captures design
intent for future maintenance.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final

import numpy as np
import numpy.typing as npt
import xarray as xr

from snomniman.core import Capability, DataKind, Dataset, Metadata
from snomniman.core.exceptions import ProcessingError
from snomniman.processing.registry import register
from snomniman.processing.step import CHANNEL_COMPLEX, ParameterSpec, ProcessingStep

#: How the subtracted phase datum is chosen.
REFERENCE_MEAN: Final = "mean"  # circular mean of the channel: angle(mean(O))
REFERENCE_CONSTANT: Final = "constant"  # a user-supplied value_rad
_REFERENCES: Final = (REFERENCE_MEAN, REFERENCE_CONSTANT)


@register
class PhaseOffset(ProcessingStep):
    """Subtract a constant phase from a complex channel (amplitude preserved).

    ``reference="mean"`` (default) subtracts the channel's circular-mean phase,
    removing the global offset; ``reference="constant"`` subtracts ``value_rad``. The
    target channel's amplitude is unchanged; its ``state`` becomes ``"referenced"`` and
    the new phase reference is recorded in the conventions. Other channels are
    preserved; the input Dataset is never modified.
    """

    step_id = "image.phase_offset"
    version = 1
    description = "Re-reference a complex channel's phase by a constant (amplitude kept)."
    deterministic = True
    required_capabilities = (Capability.COMPLEX_OPTICAL,)

    @classmethod
    def param_specs(cls) -> list[ParameterSpec]:
        return [
            ParameterSpec(
                "channel",
                "Complex channel whose phase is re-referenced (e.g. 'O2').",
                (str,),
                channel_role=CHANNEL_COMPLEX,
            ),
            ParameterSpec(
                "reference",
                "Datum subtracted: the circular-mean phase, or a constant value.",
                (str,),
                required=False,
                default=REFERENCE_MEAN,
                choices=_REFERENCES,
            ),
            ParameterSpec(
                "value_rad",
                "Constant phase to subtract, in radians (used when reference='constant').",
                (int, float),
                required=False,
                default=0.0,
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
        if not primary.is_complex(channel):
            raise ProcessingError(
                f"{self.step_id}: channel {channel!r} is real; phase re-referencing "
                "requires a complex channel (it has no phase to offset)"
            )

        raw = primary.data
        values = np.asarray(raw[channel].values)
        dphi = _phase_datum(values, reference, float(self._params["value_rad"]))
        rotated = values * np.exp(-1j * dphi)

        new_vars: dict[str, xr.DataArray] = {}
        for raw_name, var in raw.data_vars.items():
            name = str(raw_name)
            if name == channel:
                arr: npt.NDArray[Any] = rotated.astype(var.dtype)
            else:
                arr = np.array(var.values, copy=True)
            new_vars[name] = xr.DataArray(
                arr, coords=var.coords, dims=var.dims, attrs=dict(var.attrs)
            )
        new_data = xr.Dataset(new_vars, coords=raw.coords, attrs=dict(raw.attrs))

        new_channels = tuple(
            replace(ci, state="referenced") if ci.canonical == channel else ci
            for ci in primary.metadata.channels
        )
        new_conventions = replace(
            primary.metadata.conventions,
            phase_reference=f"offset by {reference} (image.phase_offset)",
        )
        new_metadata = replace(
            primary.metadata, channels=new_channels, conventions=new_conventions
        )
        return new_data, primary.kind, new_metadata


def _phase_datum(values: npt.NDArray[Any], reference: str, value_rad: float) -> float:
    """The phase to subtract: the circular mean (cyclic-correct), or a constant."""
    if reference == REFERENCE_CONSTANT:
        return value_rad
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return 0.0
    # Circular mean: the angle of the (amplitude-weighted) mean complex vector. This
    # is the correct average of a cyclic quantity; an arithmetic mean of wrapped
    # angles would be wrong near the +/-pi wrap.
    return float(np.angle(np.mean(finite)))


__all__ = [
    "REFERENCE_CONSTANT",
    "REFERENCE_MEAN",
    "PhaseOffset",
]
