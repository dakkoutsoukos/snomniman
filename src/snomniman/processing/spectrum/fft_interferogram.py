"""Interferogram -> spectrum: apodization, zero-fill, phase correction, forward FFT.

``FftInterferogram`` is the actual Fourier-transform computation nano-FTIR is named
for (docs/phase5-spectral-nanoftir.md sec 2.2, workflow W6): a real-valued signal
recorded against optical path difference (OPD) is apodized (windowed), zero-filled,
phase-corrected, and Fourier-transformed into a complex spectrum (amplitude + phase
versus wavenumber) - the standard conventional-FTIR chain (Griffiths & de Haseth
2007 ch. 3), reused unmodified for the near-field variant (nano-FTIR is a near-field
variant of the same underlying computation). This is the first operation whose
output ``DataKind`` differs from its input's (``INTERFEROGRAM`` -> ``SPECTRUM``), a
mechanism the processing engine already supports
(:meth:`~snomniman.processing.ProcessingStep._execute`'s ``(data, kind, metadata)``
contract, ADR-0017) but that no operation had yet exercised.

Scope
-----
Handles one interferogram at a time (dims exactly ``(opd,)``); a hyperspectral
interferometric cube (dims ``(y, x, opd)``) is explicitly out of scope for this
milestone (Phase 5B). The underlying numerics (``processing.spectrum._math``) are
dimension-agnostic so a future cube variant reuses them without modification.

The interferogram signal must be **real-valued**, matching conventional FTIR
literature; a complex (heterodyne-demodulated) near-field interferogram is a
distinct, acquisition-specific case deliberately deferred (Phase 5A is scoped to
avoid vendor/acquisition-specific assumptions - docs/phase5-spectral-nanoftir.md
sec 6.1).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Final

import numpy as np
import xarray as xr

from snomniman.core import Capability, ChannelInfo, DataKind, Dataset, Metadata
from snomniman.core.exceptions import ProcessingError
from snomniman.core.metadata import InterferometerInfo, SpectralInfo
from snomniman.processing.registry import register
from snomniman.processing.step import CHANNEL_REAL, ParameterSpec, ProcessingStep

from ._math import (
    APODIZATION_BLACKMAN_HARRIS_3,
    APODIZATIONS,
    PHASE_CORRECTION_MERTZ,
    PHASE_CORRECTIONS,
    apodization_window,
    forward_transform,
    mertz_phase_correction,
    uniform_step,
    wavenumber_axis,
    zero_pad,
)

#: Half-width (samples) of the symmetric segment Mertz phase correction estimates
#: phase from - short enough to be low-resolution (fast, robust to spectral
#: structure elsewhere in the interferogram), long enough for a stable phase
#: estimate (Mertz 1967).
_MERTZ_HALF_WIDTH: Final = 32


@register
class FftInterferogram(ProcessingStep):
    """Apodize, zero-fill, phase-correct, and Fourier-transform an interferogram.

    Reads a real-valued channel indexed by ``opd`` (dims exactly ``(opd,)``,
    uniformly sampled, in centimetres) and produces a new ``SPECTRUM`` dataset with
    a complex channel of the same name, indexed by ``wavenumber`` (cm^-1). The
    input Dataset is never modified.
    """

    step_id = "spectrum.fft_interferogram"
    version = 1
    description = "Apodize, zero-fill, phase-correct, and FFT an interferogram into a spectrum."
    deterministic = True
    required_capabilities = (Capability.INTERFEROMETRIC,)

    @classmethod
    def param_specs(cls) -> list[ParameterSpec]:
        return [
            ParameterSpec(
                "channel",
                "Real-valued interferogram channel to transform (e.g. 'O2').",
                (str,),
                channel_role=CHANNEL_REAL,
            ),
            ParameterSpec(
                "apodization",
                "Apodization window applied before the FFT.",
                (str,),
                required=False,
                default=APODIZATION_BLACKMAN_HARRIS_3,
                choices=APODIZATIONS,
            ),
            ParameterSpec(
                "zero_fill",
                "Zero-fill factor (>=1): pads the interferogram to this multiple of "
                "its length before the FFT, interpolating spectral points (no new "
                "resolution).",
                (int,),
                required=False,
                default=1,
            ),
            ParameterSpec(
                "phase_correction",
                "Instrumental phase-error correction: none, or the Mertz method.",
                (str,),
                required=False,
                default=PHASE_CORRECTION_MERTZ,
                choices=PHASE_CORRECTIONS,
            ),
        ]

    def _execute(
        self, inputs: Mapping[str, Dataset]
    ) -> tuple[xr.Dataset, DataKind, Metadata]:
        primary = inputs["primary"]
        channel: str = self._params["channel"]
        apodization: str = self._params["apodization"]
        zero_fill: int = self._params["zero_fill"]
        phase_correction: str = self._params["phase_correction"]

        if primary.kind is not DataKind.INTERFEROGRAM:
            raise ProcessingError(
                f"{self.step_id}: expects an INTERFEROGRAM dataset, "
                f"got {primary.kind.value!r}"
            )
        if channel not in primary.channel_names:
            raise ProcessingError(
                f"{self.step_id}: channel {channel!r} not found; "
                f"available: {primary.channel_names}"
            )
        if primary.is_complex(channel):
            raise ProcessingError(
                f"{self.step_id}: channel {channel!r} is complex; this step expects "
                "a real-valued interferogram (complex near-field interferograms are "
                "not yet supported - see docs/phase5-spectral-nanoftir.md)"
            )
        source = primary.channel(channel)
        if source.dims != ("opd",):
            raise ProcessingError(
                f"{self.step_id}: channel {channel!r} must have dims ('opd',); got "
                f"{source.dims} (hyperspectral interferometric cubes are out of "
                "scope for this step - see Phase 5B)"
            )
        if zero_fill < 1:
            raise ProcessingError(f"{self.step_id}: zero_fill must be >= 1, got {zero_fill}")

        opd = np.asarray(primary.coordinate("opd").values, dtype=np.float64)
        opd_step_cm = uniform_step(opd, name="opd")
        signal = np.asarray(source.values, dtype=np.float64)
        n = signal.size
        n_padded = zero_fill * n
        zpd_index = int(np.argmin(np.abs(opd)))

        window = apodization_window(apodization, n, zpd_index=zpd_index)
        apodized = signal * window
        padded = zero_pad(apodized, n_padded)
        spectrum = forward_transform(padded, n_padded)

        if phase_correction == PHASE_CORRECTION_MERTZ:
            spectrum = mertz_phase_correction(
                signal,
                spectrum,
                zpd_index=zpd_index,
                half_width=_MERTZ_HALF_WIDTH,
                opd_step_cm=opd_step_cm,
                n_padded=n_padded,
            )

        wn = wavenumber_axis(n_padded, opd_step_cm)

        src_info = _channel_info(primary, channel)
        out_var = xr.DataArray(
            spectrum.astype(np.complex64),
            coords={
                "wavenumber": ("wavenumber", wn, {"unit": "cm-1", "long_name": "wavenumber"})
            },
            dims=("wavenumber",),
            attrs={
                "unit": src_info.amplitude_unit if src_info else "a.u.",
                "derived_from": channel,
                "quantity": "spectrum",
            },
        )
        new_data = xr.Dataset({channel: out_var})

        new_channel_info = ChannelInfo(
            canonical=channel,
            kind=src_info.kind if src_info else "optical",
            role="signal",
            dtype="complex64",
            state="spectrum",
            harmonic=src_info.harmonic if src_info else None,
            amplitude_unit=src_info.amplitude_unit if src_info else "a.u.",
            phase_unit="rad",
        )
        new_metadata = replace(
            primary.metadata,
            channels=(new_channel_info,),
            spectral=SpectralInfo(
                wavenumber_min_cm1=float(wn[0]),
                wavenumber_max_cm1=float(wn[-1]),
                n_points=int(wn.size),
                sampling_cm1=float(np.mean(np.diff(wn))) if wn.size > 1 else None,
            ),
            interferometer=InterferometerInfo(apodization=apodization, zero_fill=zero_fill),
        )
        return new_data, DataKind.SPECTRUM, new_metadata


def _channel_info(dataset: Dataset, channel: str) -> ChannelInfo | None:
    for info in dataset.metadata.channels:
        if info.canonical == channel:
            return info
    return None


__all__ = ["FftInterferogram"]
