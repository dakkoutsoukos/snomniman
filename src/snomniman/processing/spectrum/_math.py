"""Private spectral/interferometric numerics shared by ``processing.spectrum`` steps.

Dimension-agnostic (every function operates along the *last* axis of its input) and
Qt-free, so later Phase 5 milestones (a hyperspectral per-pixel FFT, a line-of-
interferograms variant) can reuse these functions without modifying them - only a new
:class:`~snomniman.processing.ProcessingStep` is added. Not part of the public API:
import only within ``processing.spectrum``.

This implements the standard conventional-FTIR processing chain - apodization,
zero-filling, phase correction, forward FFT - the same numerics nano-FTIR reuses
(docs/phase5-spectral-nanoftir.md sec 2.2, workflow W6).

References
----------
- Griffiths, P. R. & de Haseth, J. A., *Fourier Transform Infrared Spectrometry*,
  2nd ed., Wiley (2007) - ch. 3: apodization, zero-filling, and phase correction as
  the standard FTIR processing chain this module implements.
- Harris, F. J., "On the use of windows for harmonic analysis with the discrete
  Fourier transform", Proc. IEEE 66(1), 51-83 (1978) - apodization window
  definitions (incl. the 3-term Blackman-Harris window, Table II) and the
  coherent-gain normalization used here.
- Mertz, L., "Auxiliary computation for Fourier spectrometry", Infrared Phys. 7,
  17-23 (1967) - the phase-correction method implemented in
  :func:`mertz_phase_correction`.
"""

from __future__ import annotations

from typing import Final

import numpy as np
import numpy.typing as npt
from scipy.signal import windows as sp_windows

from snomniman.core.exceptions import ProcessingError

#: Supported apodization functions (a research-supported subset, not every
#: possible window): the textbook no-op baseline, the two classic general-purpose
#: cosine windows, and the strong-sidelobe-suppression window nano-FTIR literature
#: favors when a weak near-field resonance sits near a much stronger far-field
#: background.
APODIZATION_BOXCAR: Final = "boxcar"
APODIZATION_HANN: Final = "hann"
APODIZATION_HAMMING: Final = "hamming"
APODIZATION_BLACKMAN_HARRIS_3: Final = "blackman_harris_3"
APODIZATIONS: Final = (
    APODIZATION_BOXCAR,
    APODIZATION_HANN,
    APODIZATION_HAMMING,
    APODIZATION_BLACKMAN_HARRIS_3,
)

#: 3-term Blackman-Harris coefficients (Harris 1978, Table II; ~-67 dB sidelobes).
_BH3_COEFFS: Final = (0.42323, 0.49755, 0.07922)

PHASE_CORRECTION_NONE: Final = "none"
PHASE_CORRECTION_MERTZ: Final = "mertz"
PHASE_CORRECTIONS: Final = (PHASE_CORRECTION_NONE, PHASE_CORRECTION_MERTZ)


def apodization_window(name: str, n: int, *, zpd_index: int = 0) -> npt.NDArray[np.float64]:
    """The named apodization window, length *n*, coherent-gain normalized.

    *zpd_index* centers the window on the zero-path-difference sample rather than
    the array's geometric center: a real interferogram is commonly acquired
    single-sided or asymmetrically about ZPD (a short segment before it, a long
    one after), and a symmetric window's peak must align with the ZPD burst, not
    with index ``n // 2`` - naively centering on the array would apodize a
    single-sided interferogram (``zpd_index == 0``) down to zero at its very first,
    highest-amplitude sample. This mirrors how conventional FTIR software windows
    asymmetric interferograms (Griffiths & de Haseth 2007 ch. 3): a symmetric
    window twice the length of the longer side is evaluated, and the slice
    matching the actual (possibly asymmetric) sample span is used, so the window
    value is exactly 1 at ZPD and decays smoothly toward whichever array edge it
    reaches first.

    Normalization (:func:`normalize_window`) rescales the window to unit mean so a
    monochromatic signal's recovered peak amplitude is comparable across window
    choices - only the window *shape* (sidelobe suppression vs. resolution) then
    differs (Harris 1978 sec II).
    """
    if n < 1:
        raise ProcessingError(f"apodization_window: n must be >= 1, got {n}")
    if not (0 <= zpd_index < n):
        raise ProcessingError(
            f"apodization_window: zpd_index ({zpd_index}) out of bounds for n={n}"
        )
    if name == APODIZATION_BOXCAR:
        # A boxcar is uniform regardless of where ZPD falls - no centering needed.
        return normalize_window(np.ones(n, dtype=np.float64))

    half_span = max(zpd_index, n - 1 - zpd_index)
    full_len = 2 * half_span + 1
    if name == APODIZATION_HANN:
        full_window = np.asarray(sp_windows.hann(full_len, sym=True), dtype=np.float64)
    elif name == APODIZATION_HAMMING:
        full_window = np.asarray(sp_windows.hamming(full_len, sym=True), dtype=np.float64)
    elif name == APODIZATION_BLACKMAN_HARRIS_3:
        full_window = _blackman_harris_3(full_len)
    else:
        raise ProcessingError(
            f"apodization_window: unknown apodization {name!r}; "
            f"available: {list(APODIZATIONS)}"
        )
    start = half_span - zpd_index
    window = full_window[start : start + n]
    return normalize_window(window)


def normalize_window(window: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Rescale *window* to unit coherent gain (unit mean value, Harris 1978)."""
    gain = float(np.mean(window))
    if not np.isfinite(gain) or gain <= 0.0:
        raise ProcessingError("normalize_window: window has non-positive coherent gain")
    return window / gain


def _blackman_harris_3(n: int) -> npt.NDArray[np.float64]:
    a0, a1, a2 = _BH3_COEFFS
    if n == 1:
        return np.array([a0 - a1 + a2], dtype=np.float64)
    k = np.arange(n, dtype=np.float64)
    return np.asarray(
        a0 - a1 * np.cos(2.0 * np.pi * k / (n - 1)) + a2 * np.cos(4.0 * np.pi * k / (n - 1)),
        dtype=np.float64,
    )


def zero_pad(signal: npt.NDArray[np.float64], n_padded: int) -> npt.NDArray[np.float64]:
    """Append zeros to *signal* (along its last axis) to reach length *n_padded*.

    Standard single-sided zero-filling (Griffiths & de Haseth ch. 3): padding
    interpolates spectral points but adds no new resolution - the underlying
    instrument line shape is unchanged.
    """
    n = signal.shape[-1]
    if n_padded < n:
        raise ProcessingError(
            f"zero_pad: n_padded ({n_padded}) must be >= signal length ({n})"
        )
    if n_padded == n:
        return signal
    pad_width = [(0, 0)] * (signal.ndim - 1) + [(0, n_padded - n)]
    return np.asarray(np.pad(signal, pad_width, mode="constant", constant_values=0.0))


def uniform_step(coord: npt.NDArray[np.float64], *, name: str, rtol: float = 1e-6) -> float:
    """The (validated) uniform sampling step of a monotonically increasing *coord*.

    Raises :exc:`~snomniman.core.ProcessingError` if *coord* has fewer than 2
    samples, is not strictly increasing, or is not uniformly spaced within *rtol* -
    the FFT relies on a constant sampling interval, so non-uniform sampling must be
    refused rather than silently averaged over.
    """
    if coord.size < 2:
        raise ProcessingError(f"uniform_step: {name} needs at least 2 samples")
    diffs = np.diff(coord)
    if np.any(diffs <= 0):
        raise ProcessingError(f"uniform_step: {name} must be strictly increasing")
    step = float(np.mean(diffs))
    if not np.allclose(diffs, step, rtol=rtol):
        raise ProcessingError(
            f"uniform_step: {name} is not uniformly sampled (required for the FFT)"
        )
    return step


def wavenumber_axis(n_padded: int, opd_step_cm: float) -> npt.NDArray[np.float64]:
    """The wavenumber axis (cm^-1) for a length-*n_padded* real-signal FFT.

    ``wavenumber [cm^-1] = 1 / opd [cm]``, so with OPD sampled in centimetres the
    standard DFT frequency bins (``numpy.fft.rfftfreq``) are directly wavenumbers -
    no unit conversion needed, unlike the canonical-nm spatial axes elsewhere.
    """
    return np.asarray(np.fft.rfftfreq(n_padded, d=opd_step_cm), dtype=np.float64)


def forward_transform(
    signal: npt.NDArray[np.float64], n_padded: int
) -> npt.NDArray[np.complex128]:
    """The real-input forward FFT (``numpy.fft.rfft``) of *signal*, zero-padded to
    *n_padded*. Deterministic: bit-identical for identical input on one platform."""
    return np.asarray(np.fft.rfft(signal, n=n_padded), dtype=np.complex128)


def mertz_phase_correction(
    signal: npt.NDArray[np.float64],
    full_spectrum: npt.NDArray[np.complex128],
    *,
    zpd_index: int,
    half_width: int,
    opd_step_cm: float,
    n_padded: int,
) -> npt.NDArray[np.complex128]:
    """Mertz phase correction (Mertz 1967): estimate and remove instrumental phase.

    A short, low-resolution segment of *signal* symmetric about *zpd_index*
    (``2 * half_width + 1`` samples, clipped to the array bounds - fewer samples on
    one side degrades but does not invalidate the estimate) is FFT'd to a coarse
    complex spectrum; its phase is interpolated (via the real/imaginary parts of the
    unit phasor, avoiding a wrap discontinuity at +/-pi) onto *full_spectrum*'s
    frequency grid, and *full_spectrum* is multiplied by ``exp(-i * phase)``. This
    removes phase error common to instrumental sources (residual ZPD
    mis-registration, dispersive optics) while leaving the sample's own spectral
    phase (where physically meaningful) intact.
    """
    n = signal.shape[-1]
    lo = max(0, zpd_index - half_width)
    hi = min(n, zpd_index + half_width + 1)
    segment = signal[lo:hi]
    if segment.size < 2:
        raise ProcessingError(
            "mertz_phase_correction: too few samples around the ZPD to estimate phase"
        )
    coarse = np.asarray(np.fft.rfft(segment), dtype=np.complex128)
    coarse_wn = wavenumber_axis(segment.size, opd_step_cm)
    full_wn = wavenumber_axis(n_padded, opd_step_cm)

    coarse_phase = np.angle(coarse)
    cos_interp = np.interp(full_wn, coarse_wn, np.cos(coarse_phase))
    sin_interp = np.interp(full_wn, coarse_wn, np.sin(coarse_phase))
    phase = np.arctan2(sin_interp, cos_interp)
    return np.asarray(full_spectrum * np.exp(-1j * phase), dtype=np.complex128)


__all__ = [
    "APODIZATIONS",
    "APODIZATION_BLACKMAN_HARRIS_3",
    "APODIZATION_BOXCAR",
    "APODIZATION_HAMMING",
    "APODIZATION_HANN",
    "PHASE_CORRECTIONS",
    "PHASE_CORRECTION_MERTZ",
    "PHASE_CORRECTION_NONE",
    "apodization_window",
    "forward_transform",
    "mertz_phase_correction",
    "normalize_window",
    "uniform_step",
    "wavenumber_axis",
    "zero_pad",
]
