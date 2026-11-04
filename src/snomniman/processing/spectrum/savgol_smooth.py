"""Savitzky-Golay smoothing for a real-valued spectral channel.

``SavgolSmooth`` fits a local low-order polynomial across a sliding window
along the ``wavenumber`` axis and replaces each sample with that polynomial's
value at its center - the standard smoothing pass a researcher applies before
lineshape fitting (docs/phase6-spectral-lineshape-analysis.md sec 3.2; the
figure that commissioned this operation calls the result "savgol mean").
Structurally the simplest step in the codebase: one array transform, no
shape/kind change, closest precedent ``image.fix_zero``/``image.line_flatten``
(single channel replaced in place, every other channel and coordinate
untouched, input Dataset never modified).

Scope: requires a **real-valued** channel. In the workflow this operation is
built for, smoothing always follows :class:`~snomniman.processing.spectrum.
ratio.SpectrumRatio` (an amplitude ratio, already real) - smoothing a complex
optical signal's real/imaginary parts independently would not correspond to
smoothing its amplitude or phase, and nothing in the source workflow asks for
that, so it is not invented here (Rule 7). A complex channel is refused with a
clear message rather than silently misinterpreted.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import numpy.typing as npt
import xarray as xr
from scipy.signal import savgol_filter

from snomniman.core import Capability, DataKind, Dataset, Metadata
from snomniman.core.exceptions import ProcessingError
from snomniman.processing.registry import register
from snomniman.processing.step import CHANNEL_REAL, ParameterSpec, ProcessingStep


@register
class SavgolSmooth(ProcessingStep):
    """Smooth a real-valued spectral channel with a Savitzky-Golay filter.

    Applies :func:`scipy.signal.savgol_filter` along the ``wavenumber``
    dimension; every other channel and dimension is preserved unchanged.
    """

    step_id = "spectrum.savgol_smooth"
    version = 1
    description = "Savitzky-Golay smoothing of a real-valued channel along wavenumber."
    deterministic = True
    required_capabilities = (Capability.SPECTRAL,)

    @classmethod
    def param_specs(cls) -> list[ParameterSpec]:
        return [
            ParameterSpec(
                "channel",
                "Real-valued spectral channel to smooth (e.g. an 'O2_ratio' "
                "produced by spectrum.ratio).",
                (str,),
                channel_role=CHANNEL_REAL,
            ),
            ParameterSpec(
                "window_length",
                "Filter window length in samples (odd, >=3, <= the wavenumber "
                "axis length). No general-purpose default - the right value "
                "depends on the spectrum's sampling and expected feature width.",
                (int,),
            ),
            ParameterSpec(
                "polyorder",
                "Polynomial order fit within each window (must be < window_length).",
                (int,),
                required=False,
                default=3,
            ),
        ]

    def _execute(
        self, inputs: Mapping[str, Dataset]
    ) -> tuple[xr.Dataset, DataKind, Metadata]:
        primary = inputs["primary"]
        channel: str = self._params["channel"]
        window_length: int = self._params["window_length"]
        polyorder: int = self._params["polyorder"]

        if channel not in primary.channel_names:
            raise ProcessingError(
                f"{self.step_id}: channel {channel!r} not found; "
                f"available: {primary.channel_names}"
            )
        if primary.is_complex(channel):
            raise ProcessingError(
                f"{self.step_id}: channel {channel!r} is complex; Savitzky-Golay "
                "smoothing requires a real-valued channel (e.g. the output of "
                "spectrum.ratio)"
            )
        var = primary.data[channel]
        if "wavenumber" not in var.dims:
            raise ProcessingError(
                f"{self.step_id}: channel {channel!r} has no 'wavenumber' "
                f"dimension (dims: {var.dims})"
            )
        if window_length < 3 or window_length % 2 == 0:
            raise ProcessingError(
                f"{self.step_id}: window_length must be an odd integer >= 3, "
                f"got {window_length}"
            )
        if polyorder < 0 or polyorder >= window_length:
            raise ProcessingError(
                f"{self.step_id}: polyorder must satisfy 0 <= polyorder < "
                f"window_length ({window_length}), got {polyorder}"
            )
        n_wn = var.sizes["wavenumber"]
        if window_length > n_wn:
            raise ProcessingError(
                f"{self.step_id}: window_length ({window_length}) exceeds the "
                f"wavenumber axis length ({n_wn})"
            )

        raw = primary.data
        axis = var.dims.index("wavenumber")
        values = np.asarray(var.values, dtype=np.float64)
        smoothed = savgol_filter(values, window_length, polyorder, axis=axis)

        new_vars: dict[str, xr.DataArray] = {}
        for raw_name, v in raw.data_vars.items():
            name = str(raw_name)
            if name == channel:
                arr: npt.NDArray[Any] = smoothed.astype(v.dtype)
            else:
                arr = np.array(v.values, copy=True)
            new_vars[name] = xr.DataArray(
                arr, coords=v.coords, dims=v.dims, attrs=dict(v.attrs)
            )
        new_data = xr.Dataset(new_vars, coords=raw.coords, attrs=dict(raw.attrs))
        return new_data, primary.kind, primary.metadata


__all__ = ["SavgolSmooth"]
