"""Two-input arithmetic between measurements (the first multi-input operation).

``Arithmetic`` combines one channel of two compatible measurements pixel-by-pixel.
It is the first operation to consume **two** named inputs (``primary`` = A,
``secondary`` = B), validating the multi-input processing framework (ADR-0030): the
provenance DAG records both parents, and the result is an ordinary derived Dataset
that lives in the primary measurement's history.

The operation is deliberately *general* - a two-input arithmetic combination - so it
is not permanently "difference": the ``mode`` enum currently exposes the three
difference forms (A - B, B - A, |A - B|), and future modes (sum, ratio, normalized
difference, ...) extend the same operation rather than adding new step types.

It operates on each channel's real **value view** - the real values of a real
channel, or the **amplitude** ``|.|`` of a complex channel (phase difference is
cyclic and re-referencing, a separate explicit concern, not done here). The result
is a single real-valued channel ``{channel}_diff``.

Compatibility is required, never reconciled: the two inputs must share the same data
kind, dimensions, coordinates (pixel spacing + extent), and the chosen channel with
the same complex-ness. Mismatches are refused with a clear reason - SNOMNIMAN never
silently resamples or aligns scientific data (registration/resampling are separate,
future, explicit operations).
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

#: Supported arithmetic modes (initially the three difference forms; extensible).
MODE_A_MINUS_B: Final = "a_minus_b"
MODE_B_MINUS_A: Final = "b_minus_a"
MODE_ABS_DIFFERENCE: Final = "absolute_difference"
_MODES: Final = (MODE_A_MINUS_B, MODE_B_MINUS_A, MODE_ABS_DIFFERENCE)

#: Coordinate-equality tolerance (nm): two grids must sample the same points.
_COORD_ATOL_NM: Final = 1e-6


@register
class Arithmetic(ProcessingStep):
    """Combine one channel of two compatible measurements (A and B) pixel-by-pixel.

    Inputs are ``primary`` (A, the active measurement) and ``secondary`` (B). The
    ``mode`` selects the combination; ``channel`` selects which channel to combine
    (its real value view, or amplitude for a complex channel). The result is a new
    single-channel real-valued Dataset whose provenance references both inputs.
    """

    step_id = "image.arithmetic"
    version = 1
    description = "Combine one channel of two measurements (A - B, B - A, |A - B|)."
    deterministic = True
    required_capabilities = (Capability.SPATIAL_2D,)

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
                "Combination: A - B, B - A, or the absolute difference |A - B|.",
                (str,),
                required=False,
                default=MODE_A_MINUS_B,
                choices=_MODES,
            ),
        ]

    @classmethod
    def input_specs(cls) -> list[InputSpec]:
        return [
            InputSpec("primary", "Measurement A (the active measurement)."),
            InputSpec("secondary", "Measurement B (the measurement to combine with A)."),
        ]

    def check_compatibility(self, inputs: Mapping[str, Dataset]) -> tuple[str, ...]:
        a, b = inputs["primary"], inputs["secondary"]
        channel = self._params["channel"]
        problems: list[str] = []

        if a.kind is not b.kind:
            problems.append(f"different data kinds ({a.kind.value} vs {b.kind.value})")

        a_sizes, b_sizes = dict(a.data.sizes), dict(b.data.sizes)
        for axis in ("y", "x"):
            if a_sizes.get(axis) != b_sizes.get(axis):
                problems.append(
                    f"different {axis} size ({a_sizes.get(axis)} vs {b_sizes.get(axis)})"
                )

        for axis in ("x", "y"):
            if axis in a.data.coords and axis in b.data.coords:
                av = np.asarray(a.data.coords[axis].values, dtype=np.float64)
                bv = np.asarray(b.data.coords[axis].values, dtype=np.float64)
                if av.shape == bv.shape and not np.allclose(av, bv, rtol=0.0, atol=_COORD_ATOL_NM):
                    problems.append(f"different {axis} coordinates (pixel spacing or extent)")

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
        mode = self._params["mode"]

        a_view = _value_view(a, channel)
        b_view = _value_view(b, channel)
        if mode == MODE_A_MINUS_B:
            result = a_view - b_view
        elif mode == MODE_B_MINUS_A:
            result = b_view - a_view
        else:  # MODE_ABS_DIFFERENCE
            result = np.abs(a_view - b_view)
        result_arr: npt.NDArray[np.float64] = result.astype(np.float64)

        unit = _channel_unit(a, channel)
        out_name = f"{channel}_diff"
        src_var = a.data[channel]
        out_var = xr.DataArray(
            result_arr,
            coords=src_var.coords,
            dims=src_var.dims,
            attrs={
                "unit": unit,
                "quantity": "difference",
                "derived_from": channel,
                "operation": mode,
            },
        )
        new_data = xr.Dataset({out_name: out_var}, coords=a.data.coords, attrs=dict(a.data.attrs))

        src_info = _channel_info(a, channel)
        kind = src_info.kind if src_info is not None else "topography"
        diff_info = ChannelInfo(out_name, kind, "signal", "float64", value_unit=unit)
        new_metadata = replace(a.metadata, channels=(diff_info,))
        return new_data, a.kind, new_metadata


def _value_view(dataset: Dataset, channel: str) -> npt.NDArray[np.float64]:
    """The real value view of *channel*: amplitude for complex, real values otherwise."""
    values = np.asarray(dataset.data[channel].values)
    view = np.abs(values) if np.iscomplexobj(values) else np.real(values)
    return view.astype(np.float64)


def _channel_info(dataset: Dataset, channel: str) -> ChannelInfo | None:
    for info in dataset.metadata.channels:
        if info.canonical == channel:
            return info
    return None


def _channel_unit(dataset: Dataset, channel: str) -> str | None:
    """The unit of the channel's value view (amplitude unit if complex, else value unit)."""
    info = _channel_info(dataset, channel)
    if info is None:
        return None
    if dataset.is_complex(channel):
        return info.amplitude_unit
    return info.value_unit


__all__ = [
    "MODE_ABS_DIFFERENCE",
    "MODE_A_MINUS_B",
    "MODE_B_MINUS_A",
    "Arithmetic",
]
