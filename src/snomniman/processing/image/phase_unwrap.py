"""Explicit phase unwrapping - unwrapped phase as a first-class derived channel.

``PhaseUnwrap`` reads the wrapped phase of a complex channel and produces a **new**
real channel ``{channel}_phase_unwrapped`` (radians) holding the spatially unwrapped
phase. The raw complex channel is left untouched: per OHD-6D phase is never silently
transformed, and per OHD-4 unwrapped phase is its own channel, produced only by this
explicit, recorded operation.

Algorithm: 2-D unwrapping by sequential 1-D unwrapping (``numpy.unwrap`` along x then
y) - deterministic and dependency-free. It is exact for smoothly-varying fields; it
can mis-handle residue-bearing fields with true 2-D phase singularities (a known
limitation, documented in ``docs/processing-engine.md``). Validated against synthetic
wrapped ramps with analytical ground truth.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

import numpy as np
import numpy.typing as npt
import xarray as xr

from snomniman.core import Capability, ChannelInfo, DataKind, Dataset, Metadata
from snomniman.core.exceptions import ProcessingError
from snomniman.processing.registry import register
from snomniman.processing.step import ParameterSpec, ProcessingStep


def unwrap_2d(phase: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Unwrap a 2-D phase array (radians) along x then y. Deterministic."""
    along_x = np.unwrap(phase, axis=-1)
    return np.asarray(np.unwrap(along_x, axis=-2), dtype=np.float64)


@register
class PhaseUnwrap(ProcessingStep):
    """Add a spatially-unwrapped phase channel for a complex channel.

    The raw channel is preserved; a new real channel ``{channel}_phase_unwrapped``
    (radians, state ``"unwrapped"``) is appended. The input Dataset is never modified.
    """

    step_id = "image.phase_unwrap"
    version = 1
    description = "Produce an unwrapped phase channel from a complex channel."
    deterministic = True
    required_capabilities = (Capability.SPATIAL_2D,)

    @classmethod
    def param_specs(cls) -> list[ParameterSpec]:
        return [
            ParameterSpec(
                "channel",
                "Complex channel whose phase to unwrap (e.g. 'O2').",
                (str,),
                required=True,
            ),
        ]

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
                f"{self.step_id}: channel {channel!r} is not complex; "
                "phase unwrapping requires a complex channel"
            )

        new_name = f"{channel}_phase_unwrapped"
        if new_name in primary.channel_names:
            raise ProcessingError(
                f"{self.step_id}: channel {new_name!r} already exists"
            )

        raw = primary.data
        source = raw[channel]
        values = np.asarray(source.values)
        wrapped = np.arctan2(values.imag, values.real)
        unwrapped: npt.NDArray[Any] = unwrap_2d(np.asarray(wrapped, dtype=np.float64))

        new_vars: dict[str, xr.DataArray] = {
            str(name): xr.DataArray(
                np.array(var.values, copy=True),
                coords=var.coords,
                dims=var.dims,
                attrs=dict(var.attrs),
            )
            for name, var in raw.data_vars.items()
        }
        new_vars[new_name] = xr.DataArray(
            unwrapped,
            coords=source.coords,
            dims=source.dims,
            attrs={"unit": "rad", "derived_from": channel, "quantity": "unwrapped_phase"},
        )
        new_data = xr.Dataset(new_vars, coords=raw.coords, attrs=dict(raw.attrs))

        src_info = {c.canonical: c for c in primary.metadata.channels}.get(channel)
        new_info = ChannelInfo(
            canonical=new_name,
            kind=src_info.kind if src_info else "optical",
            role="signal",
            dtype="float64",
            state="unwrapped",
            harmonic=src_info.harmonic if src_info else None,
            value_unit="rad",
        )
        new_metadata = replace(
            primary.metadata, channels=(*primary.metadata.channels, new_info)
        )
        return new_data, primary.kind, new_metadata


__all__ = ["PhaseUnwrap", "unwrap_2d"]
