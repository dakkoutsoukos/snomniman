"""Reference normalization for complex optical channels.

``ReferenceNormalize`` divides each complex optical *signal* channel by its matching
*reference* channel of the same harmonic (``O2 / R_O2``, ``O3 / R_O3``, ...). Both
live in the same measurement, so this is a single-input operation. Amplitude becomes
a dimensionless ratio and phase becomes a phase *difference* relative to the
reference - a re-referencing of phase that is **explicit and recorded**, never silent
(OHD-6D): the convention's ``phase_reference`` is updated to record it.

Scientific validation: ``(O / R) * R == O`` to machine precision, and the normalized
phase equals ``angle(O) - angle(R)`` (tested in ``tests/test_processing_image_ops.py``).
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
from snomniman.processing.step import ProcessingStep


def _reference_for(
    signal: ChannelInfo, channels: tuple[ChannelInfo, ...]
) -> ChannelInfo | None:
    """The optical reference channel matching *signal* by harmonic, if any."""
    if signal.harmonic is None:
        return None
    for ch in channels:
        if ch.role == "reference" and ch.kind == "optical" and ch.harmonic == signal.harmonic:
            return ch
    return None


@register
class ReferenceNormalize(ProcessingStep):
    """Divide each complex optical signal channel by its matching reference channel.

    Pairs are detected automatically by harmonic (``O{n}`` with ``R_O{n}``). Each
    normalized channel's amplitude becomes a dimensionless ratio and its phase a
    difference relative to the reference; the channel state becomes ``"normalized"``.
    Reference channels are preserved unchanged. The input Dataset is never modified.
    """

    step_id = "image.reference_normalize"
    version = 1
    description = "Divide complex optical channels by their matching reference channel."
    deterministic = True
    required_capabilities = (Capability.COMPLEX_OPTICAL, Capability.REFERENCE)

    def _execute(
        self, inputs: Mapping[str, Dataset]
    ) -> tuple[xr.Dataset, DataKind, Metadata]:
        primary = inputs["primary"]

        pairs: dict[str, str] = {}  # signal canonical -> reference canonical
        for ch in primary.metadata.channels:
            if ch.role == "signal" and ch.kind == "optical" and primary.is_complex(ch.canonical):
                ref = _reference_for(ch, primary.metadata.channels)
                if ref is not None and ref.canonical in primary.channel_names:
                    pairs[ch.canonical] = ref.canonical
        if not pairs:
            raise ProcessingError(
                f"{self.step_id}: no optical signal/reference pairs found "
                f"(need O{{n}} with a matching R_O{{n}})"
            )

        raw = primary.data
        new_vars: dict[str, xr.DataArray] = {}
        for raw_name, var in raw.data_vars.items():
            name = str(raw_name)
            if name in pairs:
                ref_values = np.asarray(raw[pairs[name]].values)
                signal_values = np.asarray(var.values)
                with np.errstate(divide="ignore", invalid="ignore"):
                    normalized = signal_values / ref_values
                arr: npt.NDArray[Any] = normalized.astype(var.dtype)
            else:
                arr = np.array(var.values, copy=True)
            new_vars[name] = xr.DataArray(
                arr, coords=var.coords, dims=var.dims, attrs=dict(var.attrs)
            )
        new_data = xr.Dataset(new_vars, coords=raw.coords, attrs=dict(raw.attrs))

        new_channels = tuple(
            replace(ci, state="normalized", amplitude_unit="a.u.")
            if ci.canonical in pairs
            else ci
            for ci in primary.metadata.channels
        )
        # Phase is now referenced to the reference channel - record it explicitly.
        new_conventions = replace(
            primary.metadata.conventions,
            phase_reference="reference channel (image.reference_normalize)",
        )
        new_metadata = replace(
            primary.metadata, channels=new_channels, conventions=new_conventions
        )
        return new_data, primary.kind, new_metadata


__all__ = ["ReferenceNormalize"]
