"""Provenance-bearing publication figures (Qt-free, matplotlib).

A figure is one of the most important *derivations* of a measurement, so it must
never become an orphan: the exported figure travels with a provenance record that
says exactly where it came from and how it was drawn. The record is the full,
serializable :class:`FigureSpec` plus capture metadata, so the same figure can be
**regenerated** later from the original measurement.

This stays read-only: a figure only *shows* data (fetched from the immutable
Dataset at render time), it never changes it. Rendering uses a standalone
matplotlib ``Figure`` + Agg canvas (no global pyplot state, no GUI toolkit), so it
runs headless and is testable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Polygon
from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar

from snomniman.core import Dataset

from .measure import sample_line
from .render import prepare_channel

#: Bumped when the figure-spec layout changes (reproducibility across versions).
FIGURE_SCHEMA_VERSION = 1

_OVERLAY_COLOR = "#ffcc33"
_PROFILE_COLORS = ("#46c2ff", "#ffb454", "#7ee787", "#ff7b72", "#d2a8ff", "#79c0ff")


@dataclass(frozen=True)
class PanelSpec:
    """One panel of a figure: a channel rendered with explicit display settings."""

    channel: str
    representation: str
    title: str
    unit: str
    colormap: str
    cyclic: bool
    vmin: float
    vmax: float


@dataclass(frozen=True)
class OverlaySpec:
    """A measurement overlay drawn on the panels (physical nm geometry)."""

    kind: str  # "line" | "rectangle" | "polygon"
    name: str
    points: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class FigureSpec:
    """A complete, serializable description of a publication figure."""

    title: str
    kind: str  # "single" | "comparison" | "harmonic_series" | "measurement"
    measurement: str
    source_path: str | None
    source_sha256: str | None
    panels: tuple[PanelSpec, ...]
    extent_nm: tuple[float, float, float, float]
    scale_bar_nm: float
    scale_bar_label: str
    overlays: tuple[OverlaySpec, ...] = ()
    conventions: dict[str, str] = field(default_factory=dict)
    created_at: str = ""
    snomniman_version: str = ""
    software: dict[str, str] = field(default_factory=dict)
    schema_version: int = FIGURE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "kind": self.kind,
            "measurement": self.measurement,
            "source_path": self.source_path,
            "source_sha256": self.source_sha256,
            "panels": [vars(p) for p in self.panels],
            "extent_nm": list(self.extent_nm),
            "scale_bar_nm": self.scale_bar_nm,
            "scale_bar_label": self.scale_bar_label,
            "overlays": [
                {"kind": o.kind, "name": o.name, "points": [list(pt) for pt in o.points]}
                for o in self.overlays
            ],
            "conventions": dict(self.conventions),
            "created_at": self.created_at,
            "snomniman_version": self.snomniman_version,
            "software": dict(self.software),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FigureSpec:
        return cls(
            title=data["title"],
            kind=data["kind"],
            measurement=data["measurement"],
            source_path=data.get("source_path"),
            source_sha256=data.get("source_sha256"),
            panels=tuple(PanelSpec(**p) for p in data["panels"]),
            extent_nm=_as_extent(data["extent_nm"]),
            scale_bar_nm=data["scale_bar_nm"],
            scale_bar_label=data["scale_bar_label"],
            overlays=tuple(
                OverlaySpec(o["kind"], o["name"], tuple(tuple(pt) for pt in o["points"]))
                for o in data.get("overlays", ())
            ),
            conventions=dict(data.get("conventions", {})),
            created_at=data.get("created_at", ""),
            snomniman_version=data.get("snomniman_version", ""),
            software=dict(data.get("software", {})),
            schema_version=data.get("schema_version", FIGURE_SCHEMA_VERSION),
        )


def render_figure(spec: FigureSpec, dataset: Dataset) -> Figure:
    """Render ``spec`` against ``dataset`` into a matplotlib ``Figure`` (read-only)."""
    has_profile = spec.kind == "measurement" and any(o.kind == "line" for o in spec.overlays)
    rows, cols = _grid_shape(len(spec.panels))
    fig = Figure(figsize=(4.2 * cols, 4.0 * rows + (2.2 if has_profile else 0.0)), dpi=200)
    FigureCanvasAgg(fig)
    grid = fig.add_gridspec(rows + (1 if has_profile else 0), cols)

    for index, panel in enumerate(spec.panels):
        ax = fig.add_subplot(grid[index // cols, index % cols])
        _draw_panel(ax, fig, panel, dataset, spec)

    if has_profile:
        profile_ax = fig.add_subplot(grid[rows, :])
        _draw_profile(profile_ax, spec, dataset)

    fig.suptitle(spec.title, fontsize=13, fontweight="bold")
    fig.tight_layout()
    return fig


def export(spec: FigureSpec, dataset: Dataset, path: str | Path) -> tuple[Path, Path]:
    """Render and save the figure plus its provenance sidecar JSON.

    Returns ``(figure_path, provenance_path)``. The provenance JSON embeds the full
    spec, so the figure can be regenerated from the original measurement.
    """
    figure_path = Path(path)
    fig = render_figure(spec, dataset)
    fig.savefig(figure_path, bbox_inches="tight")
    provenance_path = figure_path.with_suffix(figure_path.suffix + ".provenance.json")
    provenance_path.write_text(json.dumps(provenance_record(spec), indent=2), encoding="utf-8")
    return figure_path, provenance_path


def render_from_record(record: dict[str, Any], dataset: Dataset) -> Figure:
    """Regenerate a figure from a saved provenance record (reproducibility)."""
    return render_figure(FigureSpec.from_dict(record["figure_spec"]), dataset)


def provenance_record(spec: FigureSpec) -> dict[str, Any]:
    """The machine-readable provenance: the full spec plus a readable caption."""
    return {"figure_spec": spec.to_dict(), "caption": provenance_caption(spec)}


def provenance_caption(spec: FigureSpec) -> str:
    """A human-readable caption answering 'where did this figure come from?'."""
    panels = "; ".join(
        f"{p.title} ({p.colormap}, {p.vmin:.3g}..{p.vmax:.3g} {p.unit})" for p in spec.panels
    )
    lines = [
        f"Figure: {spec.title}",
        f"Measurement: {spec.measurement}"
        + (f" (sha256 {spec.source_sha256[:12]}...)" if spec.source_sha256 else ""),
        f"Panels: {panels}",
    ]
    if spec.overlays:
        lines.append("Measurements: " + "; ".join(f"{o.name} [{o.kind}]" for o in spec.overlays))
    if spec.conventions:
        lines.append("Conventions: " + ", ".join(f"{k}={v}" for k, v in spec.conventions.items()))
    versions = ", ".join(f"{k} {v}" for k, v in spec.software.items())
    lines.append(f"SNOMNIMAN {spec.snomniman_version}" + (f" ({versions})" if versions else ""))
    lines.append(f"Exported: {spec.created_at}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Drawing
# --------------------------------------------------------------------------- #


def _draw_panel(
    ax: Any, fig: Figure, panel: PanelSpec, dataset: Dataset, spec: FigureSpec
) -> None:
    values = prepare_channel(dataset, panel.channel, panel.representation).values
    image = ax.imshow(
        values,
        extent=spec.extent_nm,
        origin="lower",  # lower-left convention (OHD-6C)
        cmap=panel.colormap,
        vmin=panel.vmin,
        vmax=panel.vmax,
        interpolation="nearest",
        aspect="equal",
    )
    ax.set_title(panel.title, fontsize=11)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.03, label=panel.unit or None)

    if spec.scale_bar_nm > 0:
        bar = AnchoredSizeBar(
            ax.transData,
            spec.scale_bar_nm,
            spec.scale_bar_label,
            loc="lower right",
            color="white",
            frameon=False,
            size_vertical=spec.scale_bar_nm * 0.03,
            pad=0.4,
        )
        ax.add_artist(bar)

    for overlay in spec.overlays:
        _draw_overlay(ax, overlay)


def _draw_overlay(ax: Any, overlay: OverlaySpec) -> None:
    points = overlay.points
    if overlay.kind == "line":
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        ax.plot(xs, ys, color=_OVERLAY_COLOR, linewidth=1.6)
    else:  # rectangle | polygon -> closed outline
        ax.add_patch(
            Polygon(points, closed=True, fill=False, edgecolor=_OVERLAY_COLOR, linewidth=1.6)
        )


def _draw_profile(ax: Any, spec: FigureSpec, dataset: Dataset) -> None:
    line = next(o for o in spec.overlays if o.kind == "line")
    p0, p1 = line.points[0], line.points[1]
    x = dataset.coordinate("x").values
    y = dataset.coordinate("y").values
    for index, panel in enumerate(spec.panels):
        values = prepare_channel(dataset, panel.channel, panel.representation).values
        positions, samples = sample_line(values, x, y, p0, p1)
        lo, hi = float(samples.min()), float(samples.max())
        normalized = (samples - lo) / (hi - lo) if hi > lo else samples * 0.0
        ax.plot(
            positions,
            normalized,
            color=_PROFILE_COLORS[index % len(_PROFILE_COLORS)],
            label=f"{panel.title} [{lo:.3g}..{hi:.3g} {panel.unit}]",
        )
    ax.set_xlabel("distance (nm)")
    ax.set_ylabel("normalized")
    ax.set_title(f"Profile along {line.name}", fontsize=10)
    ax.legend(fontsize=8, loc="best")


def _grid_shape(n: int) -> tuple[int, int]:
    if n <= 1:
        return 1, 1
    cols = 2 if n <= 4 else 3
    return (n + cols - 1) // cols, cols


def _as_extent(values: Any) -> tuple[float, float, float, float]:
    x0, x1, y0, y1 = (float(v) for v in values)
    return x0, x1, y0, y1


__all__ = [
    "FIGURE_SCHEMA_VERSION",
    "FigureSpec",
    "OverlaySpec",
    "PanelSpec",
    "export",
    "provenance_caption",
    "provenance_record",
    "render_figure",
    "render_from_record",
]
