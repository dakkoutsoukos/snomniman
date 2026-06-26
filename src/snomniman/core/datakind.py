"""``DataKind`` - the human-facing dataset classification (hybrid dispatch, OHD-8).

``DataKind`` answers "what kind of measurement is this?" for humans and to drive
UX/defaults. It does **not** decide which operations apply - that is the job of
:mod:`snomniman.core.capabilities` (which axes/channels a dataset actually has).
Together they form the hybrid dispatch model (ADR-0017): new modalities add
capabilities without forcing edits to this enum.
"""

from __future__ import annotations

from enum import Enum


class DataKind(Enum):
    """Human-facing classification of a near-field dataset (data-model sec 2)."""

    IMAGE = "image"
    LINE_SCAN = "line_scan"
    APPROACH_CURVE = "approach_curve"
    INTERFEROGRAM = "interferogram"
    SPECTRUM = "spectrum"
    HYPERSPECTRAL = "hyperspectral"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


__all__ = ["DataKind"]
