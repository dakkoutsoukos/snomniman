"""Amplitude ratio between two spectral measurements (the spectral analogue of
``image.arithmetic``).

``SpectrumRatio`` divides one channel's amplitude view of two *different*,
compatible spectral measurements (``primary`` / ``secondary``) - e.g. a point
spectrum acquired on a nanoparticle divided by one acquired on the bare
substrate, the "amplitude ratio (NP / substrate)" quantity a researcher plots
after point spectroscopy (docs/phase6-spectral-lineshape-analysis.md sec 2/3.1).

This is deliberately **not** ``image.reference_normalize`` (which divides a
signal channel by its matching reference channel *within the same*
measurement, captured simultaneously by the instrument) - it is a genuinely
different two-measurement combination, structurally identical to the already-
shipped ``image.arithmetic`` (ADR-0030: two named inputs, a
``check_compatibility`` gate, an extensible ``mode`` enum), just for spectra
and division instead of subtraction. It is the second real consumer of that
2-input pattern, not a new architectural mechanism.

Compatibility is required, never reconciled: the two inputs must share the
same data kind, the same shape on every dimension they both carry, the same
``wavenumber`` coordinate (same acquisition sweep - SNOMNIMAN never silently
resamples one spectrum onto another's axis), and the chosen channel with the
same complex-ness. The result is a single real-valued channel
``{channel}_ratio``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Final

import numpy as np
import numpy.typing as npt
import xarray as xr

from snomniman.core import Capability, ChannelInfo, DataKind, Dataset, Metadata
from snomniman.processing.registry import register
from snomniman.processing.step import (
    CHANNEL_ANY,
    InputSpec,
    ParameterSpec,
    ProcessingStep,
)

#: Supported combination modes (initially the one ratio form; extensible, mirroring
#: image.arithmetic's own "future modes extend the enum" design).
MODE_RATIO: Final = "ratio"
_MODES: Final = (MODE_RATIO,)

#: Coordinate-equality tolerance (cm^-1): two spectra must sample the same points.
_COORD_ATOL_CM1: Final = 1e-6


@register
class SpectrumRatio(ProcessingStep):
    """Divide one channel's amplitude of two compatible spectral measurements (A / B).

    Inputs are ``primary`` (A, the numerator) and ``secondary`` (B, the
    denominator). ``channel`` selects which channel to combine (its real value
    view, or amplitude for a complex channel). The result is a new
    single-channel real-valued Dataset whose provenance references both inputs.
    """

    step_id = "spectrum.ratio"
    version = 1
    description = "Divide one channel's amplitude of two spectra (A / B)."
    deterministic = True
    required_capabilities = (Capability.SPECTRAL,)

    @classmethod
    def param_specs(cls) -> list[ParameterSpec]:
        return [
            ParameterSpec(
                "channel",
                "Channel to combine (taken from both measurements).",
                (str,),
                channel_role=CHANNEL_ANY,
            ),
            ParameterSpec(
                "mode",
                "Combination: currently only the amplitude ratio A / B.",
                (str,),
                required=False,
                default=MODE_RATIO,
                choices=_MODES,
            ),
        ]

    @classmethod
    def input_specs(cls) -> list[InputSpec]:
        return [
            InputSpec("primary", "Measurement A (the numerator, e.g. on-feature)."),
            InputSpec("secondary", "Measurement B (the denominator, e.g. on-substrate)."),
        ]

    def check_compatibility(self, inputs: Mapping[str, Dataset]) -> tuple[str, ...]:
        a, b = inputs["primary"], inputs["secondary"]
        channel = self._params["channel"]
        problems: list[str] = []

        if a.kind is not b.kind:
            problems.append(f"different data kinds ({a.kind.value} vs {b.kind.value})")

        a_sizes, b_sizes = dict(a.data.sizes), dict(b.data.sizes)
        for axis in sorted({str(k) for k in a_sizes} | {str(k) for k in b_sizes}):
            if a_sizes.get(axis) != b_sizes.get(axis):
                problems.append(
                    f"different {axis} size ({a_sizes.get(axis)} vs {b_sizes.get(axis)})"
                )

        if "wavenumber" in a.data.coords and "wavenumber" in b.data.coords:
            av = np.asarray(a.data.coords["wavenumber"].values, dtype=np.float64)
            bv = np.asarray(b.data.coords["wavenumber"].values, dtype=np.float64)
            if av.shape != bv.shape or not np.allclose(
                av, bv, rtol=0.0, atol=_COORD_ATOL_CM1
            ):
                problems.append("different wavenumber coordinates (sampling or range)")

        in_a, in_b = channel in a.channel_names, channel in b.channel_names
        if not in_a:
            problems.append(f"channel {channel!r} is not in measurement A")
        if not in_b:
            problems.append(f"channel {channel!r} is not in measurement B")
        if in_a and in_b and a.is_complex(channel) != b.is_complex(channel):
            problems.append(
                f"channel {channel!r} is complex in one measurement and real in the other"
            )
        return tuple(problems)

    def _execute(
        self, inputs: Mapping[str, Dataset]
    ) -> tuple[xr.Dataset, DataKind, Metadata]:
        a, b = inputs["primary"], inputs["secondary"]
        channel = self._params["channel"]

        a_view = _amplitude_view(a, channel)
        b_view = _amplitude_view(b, channel)
        with np.errstate(divide="ignore", invalid="ignore"):
            result = a_view / b_view
        result_arr: npt.NDArray[np.float64] = result.astype(np.float64)

        out_name = f"{channel}_ratio"
        src_var = a.data[channel]
        out_var = xr.DataArray(
            result_arr,
            coords=src_var.coords,
            dims=src_var.dims,
            attrs={
                "unit": "a.u.",
                "quantity": "ratio",
                "derived_from": channel,
                "operation": "spectrum.ratio",
            },
        )
        new_data = xr.Dataset({out_name: out_var}, coords=a.data.coords, attrs=dict(a.data.attrs))

        src_info = _channel_info(a, channel)
        kind = src_info.kind if src_info is not None else "optical"
        ratio_info = ChannelInfo(
            out_name, kind, "signal", "float64", value_unit="a.u.",
            harmonic=src_info.harmonic if src_info is not None else None,
        )
        new_metadata = replace(a.metadata, channels=(ratio_info,))
        return new_data, a.kind, new_metadata


def _amplitude_view(dataset: Dataset, channel: str) -> npt.NDArray[np.float64]:
    """The real value view of *channel*: amplitude for complex, real values otherwise."""
    values = np.asarray(dataset.data[channel].values)
    view = np.abs(values) if np.iscomplexobj(values) else np.real(values)
    return view.astype(np.float64)


def _channel_info(dataset: Dataset, channel: str) -> ChannelInfo | None:
    for info in dataset.metadata.channels:
        if info.canonical == channel:
            return info
    return None


__all__ = ["MODE_RATIO", "SpectrumRatio"]
