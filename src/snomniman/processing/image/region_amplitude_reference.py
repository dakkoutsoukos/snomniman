"""Normalize optical amplitude to the mean amplitude of a selected rectangular region.

``RegionAmplitudeReference`` extends ``image.normalize_amplitude`` from a global
image datum (peak or mean amplitude of the whole image) to a spatially-selected
substrate datum - the quantitative self-normalization step that converts s-SNOM
amplitude from arbitrary instrument units to a dimensionless contrast ratio
referenced to a known material.

Scientific rationale
--------------------
s-SNOM amplitude is reported in arbitrary units that depend on detector gain,
lock-in demodulation amplitude, and optical alignment - so raw amplitude values are
not comparable across harmonics, sessions, or instruments. Only *relative* amplitude
(contrast) is interpretable.

The standard quantitative approach (Dai et al., Science 2014; Woessner et al.,
Nature Materials 2015) is to divide by the mean amplitude of a substrate or
reference-material region:

    A_result(x, y) = |O(x, y)| / A_ref,

where A_ref = mean(|O| over the reference region).

This converts amplitude to a dimensionless ratio relative to a known material,
making comparisons across measurements, harmonics, and samples principled.

The result's amplitude in the reference region has mean ≈ 1.0 by construction;
everything else is amplitude relative to that reference. The phase is preserved
exactly throughout (only a real positive scalar is divided out).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

import numpy as np
import numpy.typing as npt
import xarray as xr

from snomniman.core import Capability, DataKind, Dataset, Metadata
from snomniman.core.exceptions import ProcessingError
from snomniman.processing.registry import register
from snomniman.processing.step import CHANNEL_COMPLEX, ROI_RECTANGLE, ParameterSpec, ProcessingStep

from ._region import mean_amplitude, region_complex_values


@register
class RegionAmplitudeReference(ProcessingStep):
    """Divide a complex channel by the mean amplitude of a reference region.

    The reference region is a rectangle in canonical nm (lower-left origin). Every
    pixel in the image is divided by the reference region's mean amplitude, so that
    region's mean amplitude becomes 1.0 after the operation. The phase is preserved
    exactly; other channels are unchanged; the input Dataset is never modified.

    The reference region typically covers a substrate or known material. The resulting
    amplitude is dimensionless (a ratio relative to the reference material).
    """

    step_id = "image.region_amplitude_reference"
    version = 1
    description = "Normalize optical amplitude to the mean amplitude of a selected region."
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
                "x_min",
                "Left bound of reference region (canonical nm).",
                (int, float),
                region_role=ROI_RECTANGLE,
            ),
            ParameterSpec(
                "x_max",
                "Right bound of reference region (canonical nm).",
                (int, float),
                region_role=ROI_RECTANGLE,
            ),
            ParameterSpec(
                "y_min",
                "Bottom bound of reference region (canonical nm).",
                (int, float),
                region_role=ROI_RECTANGLE,
            ),
            ParameterSpec(
                "y_max",
                "Top bound of reference region (canonical nm).",
                (int, float),
                region_role=ROI_RECTANGLE,
            ),
        ]

    @classmethod
    def validate(cls, params: Mapping[str, Any]) -> dict[str, Any]:
        out = super().validate(params)
        if out["x_min"] >= out["x_max"]:
            raise ProcessingError(
                f"{cls.step_id}: x_min ({out['x_min']}) must be less than x_max ({out['x_max']})"
            )
        if out["y_min"] >= out["y_max"]:
            raise ProcessingError(
                f"{cls.step_id}: y_min ({out['y_min']}) must be less than y_max ({out['y_max']})"
            )
        return out

    def _execute(
        self, inputs: Mapping[str, Dataset]
    ) -> tuple[xr.Dataset, DataKind, Metadata]:
        primary = inputs["primary"]
        channel: str = self._params["channel"]

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
        values: npt.NDArray[Any] = np.asarray(raw[channel].values)
        x = np.asarray(primary.coordinate("x").values, dtype=np.float64)
        y = np.asarray(primary.coordinate("y").values, dtype=np.float64)

        sel = region_complex_values(
            values, x, y,
            float(self._params["x_min"]), float(self._params["x_max"]),
            float(self._params["y_min"]), float(self._params["y_max"]),
            self.step_id,
        )
        datum = mean_amplitude(sel, self.step_id)
        normalized: npt.NDArray[Any] = values / datum

        new_vars: dict[str, xr.DataArray] = {}
        for raw_name, var in raw.data_vars.items():
            name = str(raw_name)
            arr: npt.NDArray[Any]
            if name == channel:
                arr = normalized.astype(var.dtype)
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


__all__ = ["RegionAmplitudeReference"]
