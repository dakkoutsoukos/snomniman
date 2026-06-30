"""Normalize optical amplitude: divide a complex channel by a scalar amplitude datum.

``NormalizeAmplitude`` divides a complex optical channel by a single positive scalar,
``O -> O / s``: the **phase is preserved exactly** and the amplitude is rescaled to a
common, dimensionless scale. It makes amplitude contrast comparable across channels,
harmonics, and measurements (whose raw amplitudes are in arbitrary, instrument- and
gain-dependent units).

Scientific rationale & default basis
------------------------------------
s-SNOM amplitude is reported in arbitrary units that depend on detector gain,
demodulation, and alignment, so a single scan's absolute amplitude carries no absolute
meaning - only *relative* amplitude (contrast) is interpretable. Normalizing to a
common datum is therefore a routine quantitative step. The default datum is the
**peak**, ``s = max(|O|)``, which maps the amplitude into ``[0, 1]`` (peak
normalization, as in ImageJ/Fiji display normalization and common figure preparation);
``reference="mean"`` divides by the mean amplitude instead, giving contrast around 1.

The most quantitative form - normalizing to the mean amplitude of a chosen *substrate
region* (self-normalization to a known material) - needs a region parameter and is
deliberately deferred to a later phase; peak and whole-image-mean normalization are
valid and complete on their own. The normalized channel's ``state`` becomes
``"normalized"`` and its amplitude is dimensionless. This note captures design intent
for future maintenance.
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

#: Amplitude datum the channel is divided by.
REFERENCE_MAX: Final = "max"  # peak amplitude -> result in [0, 1]
REFERENCE_MEAN: Final = "mean"  # mean amplitude -> contrast around 1
_REFERENCES: Final = (REFERENCE_MAX, REFERENCE_MEAN)


@register
class NormalizeAmplitude(ProcessingStep):
    """Divide a complex channel by its peak (default) or mean amplitude; phase preserved.

    The target channel's phase is unchanged; its amplitude becomes a dimensionless
    ratio and its ``state`` becomes ``"normalized"``. Other channels are preserved; the
    input Dataset is never modified.
    """

    step_id = "image.normalize_amplitude"
    version = 1
    description = "Divide a complex channel by its peak or mean amplitude (phase kept)."
    deterministic = True
    required_capabilities = (Capability.COMPLEX_OPTICAL,)

    @classmethod
    def param_specs(cls) -> list[ParameterSpec]:
        return [
            ParameterSpec(
                "channel",
                "Complex channel whose amplitude is normalized (e.g. 'O2').",
                (str,),
                channel_role=CHANNEL_COMPLEX,
            ),
            ParameterSpec(
                "reference",
                "Amplitude datum to divide by: the peak (max) or the mean amplitude.",
                (str,),
                required=False,
                default=REFERENCE_MAX,
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
        if not primary.is_complex(channel):
            raise ProcessingError(
                f"{self.step_id}: channel {channel!r} is real; amplitude normalization "
                "requires a complex channel"
            )

        raw = primary.data
        values = np.asarray(raw[channel].values)
        amplitude = np.abs(values)
        finite = amplitude[np.isfinite(amplitude)]
        datum = float(np.max(finite)) if reference == REFERENCE_MAX else float(np.mean(finite))
        if not np.isfinite(datum) or datum <= 0.0:
            raise ProcessingError(
                f"{self.step_id}: channel {channel!r} has no positive amplitude to "
                f"normalize by ({reference} = {datum})"
            )
        normalized = values / datum

        new_vars: dict[str, xr.DataArray] = {}
        for raw_name, var in raw.data_vars.items():
            name = str(raw_name)
            if name == channel:
                arr: npt.NDArray[Any] = normalized.astype(var.dtype)
            else:
                arr = np.array(var.values, copy=True)
            new_vars[name] = xr.DataArray(
                arr, coords=var.coords, dims=var.dims, attrs=dict(var.attrs)
            )
        new_data = xr.Dataset(new_vars, coords=raw.coords, attrs=dict(raw.attrs))

        new_channels = tuple(
            replace(ci, state="normalized", amplitude_unit="") if ci.canonical == channel else ci
            for ci in primary.metadata.channels
        )
        new_metadata = replace(primary.metadata, channels=new_channels)
        return new_data, primary.kind, new_metadata


__all__ = [
    "REFERENCE_MAX",
    "REFERENCE_MEAN",
    "NormalizeAmplitude",
]
