"""Re-reference optical phase to the circular mean of a selected rectangular region.

``RegionPhaseReference`` extends ``image.phase_offset`` from a global image datum to a
spatially-selected substrate datum - the publication-standard quantitative step for
s-SNOM and nano-FTIR phase maps. The result is a phase map where the chosen reference
region (a substrate, a known material, or a flat background patch) has circular-mean
phase ≈ 0, so all other phase values represent optical contrast relative to that region.

Scientific rationale
--------------------
The absolute optical phase in s-SNOM is arbitrary: it depends on the interferometer
path length, the demodulation reference, and instrument drift. Only phase *contrast*
- phase relative to a chosen datum - is physically interpretable. The datum of choice
in quantitative work (Huth et al., Nano Lett. 2012; Basov et al., Science 2016;
Huber et al., Nano Lett. 2008) is the mean phase of a clean substrate region:

    φ_result(x, y) = φ(x, y) - φ_ref,

where φ_ref = circular_mean(φ over the reference region).

The circular mean, ``angle(mean(O_region))``, is used rather than the arithmetic mean
of wrapped angles because phase is a cyclic quantity: the arithmetic average of +179°
and -179° gives 0° instead of the correct 180°.

The global-mean datum (``image.phase_offset`` with ``reference="mean"``) is a
reasonable display normalisation, but it mixes substrate and sample contributions.
A substrate-region datum is clean, reproducible, and directly comparable across
measurements taken on the same substrate.

The amplitude is preserved exactly (the operation is a complex rotation, O -> O*exp(-i*phi_ref)).
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

from ._region import circular_mean_phase, region_complex_values


@register
class RegionPhaseReference(ProcessingStep):
    """Re-reference a complex channel's phase to the circular mean of a reference region.

    The reference region is a rectangle in canonical nm (lower-left origin). Every
    pixel in the image is shifted by the negative of the reference region's circular-mean
    phase, so that region's mean phase becomes zero after the operation. The amplitude
    is preserved exactly; other channels are unchanged; the input Dataset is never modified.

    The reference region typically covers a substrate or known-material area. Its
    circular-mean phase is recorded in the dataset's conventions for provenance.
    """

    step_id = "image.region_phase_reference"
    version = 1
    description = "Re-reference optical phase to the circular mean of a selected region."
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
                f"{self.step_id}: channel {channel!r} is real; phase re-referencing "
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
        dphi = circular_mean_phase(sel)
        rotated: npt.NDArray[Any] = values * np.exp(-1j * dphi)

        new_vars: dict[str, xr.DataArray] = {}
        for raw_name, var in raw.data_vars.items():
            name = str(raw_name)
            arr: npt.NDArray[Any]
            if name == channel:
                arr = rotated.astype(var.dtype)
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
        region_str = (
            f"x=[{self._params['x_min']:.0f},{self._params['x_max']:.0f}] "
            f"y=[{self._params['y_min']:.0f},{self._params['y_max']:.0f}] nm"
        )
        new_conventions = replace(
            primary.metadata.conventions,
            phase_reference=f"region circular mean ({region_str}; image.region_phase_reference)",
        )
        new_metadata = replace(
            primary.metadata, channels=new_channels, conventions=new_conventions
        )
        return new_data, primary.kind, new_metadata


__all__ = ["RegionPhaseReference"]
