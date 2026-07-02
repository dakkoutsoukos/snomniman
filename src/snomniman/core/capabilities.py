"""``Capability`` - what a dataset *can* support (hybrid dispatch, OHD-8/ADR-0017).

Capabilities describe which named axes and channel kinds a dataset actually has.
Operations declare the capabilities they require; a dataset supports an operation
iff it has the required capabilities. This is the half of the hybrid dispatch
model that determines *applicability* (``DataKind`` drives UX/defaults).

The set is intentionally small for Phase 1 (imaging). New axes/channel kinds add
members here without touching the closed ``DataKind`` enum.
"""

from __future__ import annotations

from enum import Enum


class Capability(Enum):
    """A property of a dataset that gates which operations may run on it."""

    #: Has both ``x`` and ``y`` spatial coordinates (a 2-D scan grid).
    SPATIAL_2D = "spatial_2d"
    #: Has a single spatial coordinate (a line profile).
    SPATIAL_1D = "spatial_1d"
    #: Has a ``wavenumber`` coordinate (spectral content).
    SPECTRAL = "spectral"
    #: Has an ``opd`` coordinate (raw interferometric acquisition, pre-FFT).
    INTERFEROMETRIC = "interferometric"
    #: Has at least one complex optical near-field channel (``O{n}``).
    COMPLEX_OPTICAL = "complex_optical"
    #: Has at least one complex mechanical channel (``M{n}``).
    COMPLEX_MECHANICAL = "complex_mechanical"
    #: Has a topography/height channel (``Z``).
    TOPOGRAPHY = "topography"
    #: Has reference channels (``R_*``) usable for normalization.
    REFERENCE = "reference"
    #: Has more than one harmonic order of an optical/mechanical channel.
    MULTI_HARMONIC = "multi_harmonic"


__all__ = ["Capability"]
