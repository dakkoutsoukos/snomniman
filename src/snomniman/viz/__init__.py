"""snomniman.viz - visualization model and static export (depends on core).

Backend-neutral "display-ready" data derived from datasets (array, physical
extent honoring the lower-left origin convention, recommended colormap/limits,
units, scale-bar spec), plus matplotlib-based publication-quality static export
(vector output, cyclic colormaps for phase). Interactive PyQtGraph adapters live
at the GUI boundary so this package stays Qt-free (ADR-0007).
"""

from __future__ import annotations

from .figure import (
    FIGURE_SCHEMA_VERSION,
    FigureSpec,
    OverlaySpec,
    PanelSpec,
    export,
    provenance_caption,
    provenance_record,
    render_figure,
    render_from_record,
)
from .measure import (
    Peak,
    ProfileFeatures,
    RegionComparison,
    RegionStats,
    analyze_profile,
    compare_regions,
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
    "FIGURE_SCHEMA_VERSION",
    "LEVEL_DEFAULT",
    "LEVEL_FULL",
    "LEVEL_MODES",
    "PHASE",
    "REAL",
    "FigureSpec",
    "OverlaySpec",
    "PanelSpec",
    "Peak",
    "ProfileFeatures",
    "RegionComparison",
    "RegionStats",
    "RenderData",
    "analyze_profile",
    "available_representations",
    "compare_regions",
    "default_representation",
    "distance",
    "export",
    "level_range",
    "pick_scale_bar",
    "pixel_area",
    "polygon_mask",
    "prepare_channel",
    "provenance_caption",
    "provenance_record",
    "rect_mask",
    "region_stats",
    "render_figure",
    "render_from_record",
    "sample_line",
]
