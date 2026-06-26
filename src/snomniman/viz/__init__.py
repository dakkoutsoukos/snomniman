"""snomniman.viz - visualization model and static export (depends on core).

Backend-neutral "display-ready" data derived from datasets (array, physical
extent honoring the lower-left origin convention, recommended colormap/limits,
units, scale-bar spec), plus matplotlib-based publication-quality static export
(vector output, cyclic colormaps for phase). Interactive PyQtGraph adapters live
at the GUI boundary so this package stays Qt-free (ADR-0007).
"""

from __future__ import annotations

from .measure import (
    RegionStats,
    distance,
    pixel_area,
    polygon_mask,
    rect_mask,
    region_stats,
    sample_line,
)
from .render import (
    AMPLITUDE,
    LEVEL_DEFAULT,
    LEVEL_FULL,
    LEVEL_MODES,
    PHASE,
    REAL,
    RenderData,
    available_representations,
    default_representation,
    level_range,
    pick_scale_bar,
    prepare_channel,
)

__all__ = [
    "AMPLITUDE",
    "LEVEL_DEFAULT",
    "LEVEL_FULL",
    "LEVEL_MODES",
    "PHASE",
    "REAL",
    "RegionStats",
    "RenderData",
    "available_representations",
    "default_representation",
    "distance",
    "level_range",
    "pick_scale_bar",
    "pixel_area",
    "polygon_mask",
    "prepare_channel",
    "rect_mask",
    "region_stats",
    "sample_line",
]
