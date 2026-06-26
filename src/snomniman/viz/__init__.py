"""snomniman.viz - visualization model and static export (depends on core).

Backend-neutral "display-ready" data derived from datasets (array, physical
extent honoring the lower-left origin convention, recommended colormap/limits,
units, scale-bar spec), plus matplotlib-based publication-quality static export
(vector output, cyclic colormaps for phase). Interactive PyQtGraph adapters live
at the GUI boundary so this package stays Qt-free (ADR-0007).
"""

from __future__ import annotations

from .render import (
    AMPLITUDE,
    PHASE,
    REAL,
    RenderData,
    available_representations,
    default_representation,
    pick_scale_bar,
    prepare_channel,
)

__all__ = [
    "AMPLITUDE",
    "PHASE",
    "REAL",
    "RenderData",
    "available_representations",
    "default_representation",
    "pick_scale_bar",
    "prepare_channel",
]
