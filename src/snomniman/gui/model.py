"""The Explorer presenter: a Dataset, made ready for a viewer (Qt-free).

``ExplorerModel`` is the read-only view-model behind the Measurement Explorer. It
holds one immutable :class:`Dataset` and exposes it the way a researcher needs to
*understand* it - the measurement's identity, its channels grouped by physical
meaning, display-ready render data (via :mod:`snomniman.viz`), the typed metadata
arranged into readable sections, the provenance/lineage, and a per-pixel cursor
readout. It is deliberately free of any GUI toolkit so all of this logic is
unit-testable without a display, and so the widgets that consume it stay thin and
hold no scientific logic (Rule 4).

It never mutates the dataset: every method reads. "Explore before you process"
(product-philosophy.md) is enforced structurally - there is simply no operation
here that changes anything.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import numpy.typing as npt

from snomniman import viz
from snomniman.core import Dataset, Metadata, current_software
from snomniman.describe import summarize_provenance
from snomniman.io import read
from snomniman.viz import AMPLITUDE, PHASE, REAL, FigureSpec, OverlaySpec, RegionStats, RenderData

# --------------------------------------------------------------------------- #
# View value objects (plain data the widgets render verbatim)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ChannelEntry:
    """One selectable channel in the browser."""

    canonical: str
    descriptor: str  # e.g. "harmonic 2", "height", "reference (harmonic 2)"
    is_complex: bool
    state: str  # raw / referenced / normalized / unwrapped


@dataclass(frozen=True)
class ChannelGroup:
    """A physically-meaningful group of channels (mirrors the data, not filenames)."""

    title: str
    entries: tuple[ChannelEntry, ...]


@dataclass(frozen=True)
class MeasurementIdentity:
    """The always-visible scientific frame: what this measurement *is*."""

    title: str
    kind: str
    is_raw: bool
    pixels: tuple[int, int] | None
    field_nm: tuple[float, float] | None
    wavenumber_cm1: float | None
    detection: str | None
    source_type: str | None
    datetime: str | None
    vendor: str | None
    model: str | None


@dataclass(frozen=True)
class MetadataItem:
    label: str
    value: str
    unit: str | None
    source: str  # where the value came from (provenance of the metadata)


@dataclass(frozen=True)
class MetadataSection:
    title: str
    items: tuple[MetadataItem, ...]


@dataclass(frozen=True)
class ProvenanceStep:
    """One node of the derivation graph, rendered for reading."""

    node_id: str
    step_id: str
    description: str
    deterministic: bool
    params: dict[str, object]
    software: dict[str, str]
    sources: tuple[str, ...]  # human lines describing each RawSource


@dataclass(frozen=True)
class CursorValue:
    label: str
    value: str
    unit: str


@dataclass(frozen=True)
class CursorReadout:
    """What exists under the pointer: a physical coordinate and the values there."""

    in_bounds: bool
    x_nm: float
    y_nm: float
    values: tuple[CursorValue, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PaneSpec:
    """One pane of a comparison: a channel shown in a given representation.

    ``label`` overrides the auto-generated title (used for preview panes where
    the same channel appears twice with different context, e.g. "Z (original)"
    vs "Z (leveled)").
    """

    channel: str
    representation: str  # AMPLITUDE | PHASE | REAL
    label: str | None = None

    @property
    def title(self) -> str:
        if self.label is not None:
            return self.label
        if self.representation == REAL:
            return self.channel
        return f"{self.channel} {self.representation}"


@dataclass(frozen=True)
class ProfileCurve:
    """One channel's values sampled along a line (a read-only observation)."""

    label: str
    unit: str
    samples: npt.NDArray[np.float64]


@dataclass(frozen=True)
class ProfileSet:
    """A line measurement: the geometry plus one curve per visible channel."""

    positions_nm: npt.NDArray[np.float64]  # distance along the line per sample
    distance_nm: float
    dx_nm: float
    dy_nm: float
    curves: tuple[ProfileCurve, ...]


@dataclass(frozen=True)
class RegionStatRow:
    """One channel's statistics over a region."""

    label: str
    unit: str
    stats: RegionStats


@dataclass(frozen=True)
class RegionReport:
    """A region measurement: shared geometry plus per-channel statistics."""

    kind: str  # "rectangle" | "polygon"
    count: int
    area_nm2: float
    rows: tuple[RegionStatRow, ...]


#: Comparison preset identifiers (see :meth:`ExplorerModel.comparison_layout`).
PRESET_AMP_PHASE = "amplitude_phase"
PRESET_OPTICAL_TOPO = "optical_topography"
PRESET_SAMPLE_REF = "sample_reference"
PRESET_HARMONIC_SERIES = "harmonic_series"

#: Human labels for the presets (for the view controls).
PRESET_LABELS = {
    PRESET_AMP_PHASE: "Amplitude / Phase",
    PRESET_OPTICAL_TOPO: "Optical / Topography",
    PRESET_SAMPLE_REF: "Sample / Reference",
    PRESET_HARMONIC_SERIES: "Harmonic series",
}


# --------------------------------------------------------------------------- #
# The presenter
# --------------------------------------------------------------------------- #

_TXT = ".txt parameters"
_GSF = "GSF header"
_CONV = "SNOMNIMAN convention"


class ExplorerModel:
    """Read-only presenter wrapping one :class:`Dataset` for the Explorer."""

    def __init__(self, dataset: Dataset, *, title: str | None = None) -> None:
        self._ds = dataset
        self._title = title or _default_title(dataset)
        self._channel = _default_channel(dataset)
        self._representation = viz.default_representation(dataset, self._channel)

    @classmethod
    def open_measurement(cls, path: str | Path) -> ExplorerModel:
        """Open a measurement directory (sniffed + dispatched by the reader registry)."""
        dataset = read(path)
        return cls(dataset, title=Path(path).name)

    # -- identity / state -----------------------------------------------------

    @property
    def dataset(self) -> Dataset:
        return self._ds

    @property
    def title(self) -> str:
        return self._title

    @property
    def current_channel(self) -> str:
        return self._channel

    @property
    def current_representation(self) -> str:
        return self._representation

    def representations(self) -> tuple[str, ...]:
        return viz.available_representations(self._ds, self._channel)

    def set_channel(self, canonical: str) -> None:
        if canonical not in self._ds.channel_names:
            raise KeyError(f"no such channel: {canonical!r}")
        self._channel = canonical
        # Reset to the channel's natural default representation (amplitude / real).
        self._representation = viz.default_representation(self._ds, canonical)

    def set_representation(self, representation: str) -> None:
        allowed = self.representations()
        if representation not in allowed:
            raise ValueError(f"{representation!r} not available; choose from {allowed}")
        self._representation = representation

    def render(self) -> RenderData:
        """Display-ready data for the current channel + representation."""
        return viz.prepare_channel(self._ds, self._channel, self._representation)

    def conventions_summary(self) -> str:
        c = self._ds.metadata.conventions
        return f"{c.spatial_unit} - {c.origin} origin - phase as imported"

    # -- channels -------------------------------------------------------------

    def channel_groups(self) -> list[ChannelGroup]:
        """All channels, grouped by physical meaning (optical / mechanical / topo / refs)."""
        present = set(self._ds.channel_names)
        infos = [ch for ch in self._ds.metadata.channels if ch.canonical in present]
        by = {
            "optical": [c for c in infos if c.kind == "optical" and c.role == "signal"],
            "mechanical": [c for c in infos if c.kind == "mechanical" and c.role == "signal"],
            "topography": [c for c in infos if c.kind == "topography" and c.role == "signal"],
            "reference": [c for c in infos if c.role == "reference"],
        }
        groups: list[ChannelGroup] = []
        specs = [
            ("Optical (near-field)", "optical"),
            ("Mechanical (cantilever)", "mechanical"),
            ("Topography", "topography"),
            ("References", "reference"),
        ]
        for title, key in specs:
            members = sorted(
                by[key], key=lambda c: (c.harmonic is None, c.harmonic or 0, c.canonical)
            )
            entries = tuple(
                ChannelEntry(
                    canonical=c.canonical,
                    descriptor=_descriptor(c),
                    is_complex=self._ds.is_complex(c.canonical),
                    state=c.state,
                )
                for c in members
            )
            if entries:
                groups.append(ChannelGroup(title=title, entries=entries))
        return groups

    # -- identity -------------------------------------------------------------

    def identity(self) -> MeasurementIdentity:
        m = self._ds.metadata
        return MeasurementIdentity(
            title=self._title,
            kind=self._ds.kind.value,
            is_raw=self._ds.is_raw,
            pixels=m.scan.pixels,
            field_nm=m.scan.size_nm,
            wavenumber_cm1=m.excitation.wavenumber_cm1,
            detection=m.demodulation.detection,
            source_type=m.excitation.source_type,
            datetime=m.acquisition.datetime,
            vendor=m.instrument.vendor,
            model=m.instrument.model,
        )

    # -- metadata sections ----------------------------------------------------

    def metadata_sections(self) -> list[MetadataSection]:
        m = self._ds.metadata
        sections = [
            MetadataSection("Instrument", (
                MetadataItem("Vendor", _s(m.instrument.vendor), None, _TXT),
                MetadataItem("Model", _s(m.instrument.model), None, _TXT),
                MetadataItem("Software", _s(m.instrument.software_version), None, _TXT),
            )),
            MetadataSection("Excitation", (
                MetadataItem("Source", _s(m.excitation.source_type), None, _TXT),
                MetadataItem("Detector", _s(m.excitation.detector), None, _TXT),
                MetadataItem("Wavenumber", _n(m.excitation.wavenumber_cm1), "cm^-1", _TXT),
            )),
            MetadataSection("Demodulation", (
                MetadataItem("Detection", _s(m.demodulation.detection), None, _TXT),
                MetadataItem("Harmonics", _seq(m.demodulation.harmonics), None, _TXT),
            )),
            MetadataSection("Scan geometry", (
                MetadataItem("Pixels", _pair(m.scan.pixels, "{:d} x {:d}"), None, _GSF),
                MetadataItem("Field size", _pair(m.scan.size_nm, "{:.0f} x {:.0f}"), "nm", _GSF),
                MetadataItem(
                    "Pixel size", _pair(m.scan.pixel_size_nm, "{:.3f} x {:.3f}"), "nm", _GSF
                ),
                MetadataItem("Rotation", _n(m.scan.rotation_deg), "deg", _TXT),
            )),
            MetadataSection("Acquisition", (
                MetadataItem("Date", _s(m.acquisition.datetime), None, _TXT),
                MetadataItem(
                    "Integration time", _n(m.acquisition.integration_time_s), "s", _TXT
                ),
                MetadataItem(
                    "Tapping amplitude", _n(m.acquisition.tapping_amplitude_nm), "nm", _TXT
                ),
                MetadataItem("Setpoint", _n(m.acquisition.setpoint), None, _TXT),
                MetadataItem("Averaging", _s(m.acquisition.averaging), None, _TXT),
            )),
            MetadataSection("Conventions", _convention_items(m)),
        ]
        return sections

    # -- provenance -----------------------------------------------------------

    def provenance_summary(self) -> str:
        summary = summarize_provenance(self._ds.provenance)
        if summary.is_raw:
            return "This is the raw measurement - nothing has been done to it."
        return f"Derived result - {summary.n_steps} step(s) from the raw measurement."

    def provenance_steps(self) -> list[ProvenanceStep]:
        # The structured lineage comes from the backend Scientific Description API;
        # this method only formats it for the inspector (backend owns the facts,
        # the GUI owns the words).
        out: list[ProvenanceStep] = []
        for step in summarize_provenance(self._ds.provenance).steps:
            sources = tuple(
                f"{s.name}: {s.filename} "
                f"(sha256 {s.sha256[:12]}..., reader {s.reader})"
                for s in step.sources
            )
            out.append(ProvenanceStep(
                node_id=step.node_id,
                step_id=step.step_id,
                description=_step_description(step.step_id),
                deterministic=step.deterministic,
                params=dict(step.params),
                software=dict(step.software),
                sources=sources,
            ))
        return out

    # -- comparison -----------------------------------------------------------

    def render_spec(self, spec: PaneSpec) -> RenderData:
        """Display-ready data for one comparison pane."""
        return viz.prepare_channel(self._ds, spec.channel, spec.representation)

    def harmonic_panes(self) -> list[PaneSpec]:
        """Optical near-field harmonics present (amplitude) for the contact sheet."""
        return [PaneSpec(ch, AMPLITUDE) for ch in self._optical_signal_channels()]

    def single_view_specs(self) -> list[PaneSpec]:
        """The channels a single-view measurement reports: current (+ phase) + topography."""
        specs = [PaneSpec(self._channel, self._representation)]
        if self._ds.is_complex(self._channel) and self._representation == AMPLITUDE:
            specs.append(PaneSpec(self._channel, PHASE))
        if "Z" in self._ds.channel_names and self._channel != "Z":
            specs.append(PaneSpec("Z", REAL))
        return specs

    def comparison_layout(self, preset: str) -> list[PaneSpec]:
        """Panes for a comparison ``preset``, anchored on the current channel.

        Only channels that actually exist are included, so a measurement without
        a reference or topography degrades gracefully rather than showing blanks.
        """
        if preset == PRESET_AMP_PHASE:
            if self._ds.is_complex(self._channel):
                return [PaneSpec(self._channel, AMPLITUDE), PaneSpec(self._channel, PHASE)]
            return [PaneSpec(self._channel, REAL)]
        if preset == PRESET_OPTICAL_TOPO:
            optical = self._anchor_optical()
            panes = [self._amplitude_or_real(optical)] if optical else []
            if "Z" in self._ds.channel_names:
                panes.append(PaneSpec("Z", REAL))
            return panes
        if preset == PRESET_SAMPLE_REF:
            base = self._channel[2:] if self._channel.startswith("R_") else self._channel
            panes = []
            for name in (base, f"R_{base}"):
                if name in self._ds.channel_names:
                    panes.append(self._amplitude_or_real(name))
            return panes
        if preset == PRESET_HARMONIC_SERIES:
            return self.harmonic_panes()
        raise ValueError(f"unknown comparison preset: {preset!r}")

    # -- measurements (read-only observations) --------------------------------

    def pixel_area_nm2(self) -> float:
        return viz.pixel_area(self._x_coords(), self._y_coords())

    def line_profile(
        self, specs: Sequence[PaneSpec], p0: tuple[float, float], p1: tuple[float, float]
    ) -> ProfileSet:
        """Sample every visible channel along the line ``p0`` -> ``p1`` (read-only)."""
        x, y = self._x_coords(), self._y_coords()
        dist, dx, dy = viz.distance(p0, p1)
        positions, _ = viz.sample_line(self.render_spec(specs[0]).values, x, y, p0, p1)
        n = int(positions.size)
        curves = []
        for spec in specs:
            rd = self.render_spec(spec)
            _, samples = viz.sample_line(np.asarray(rd.values, dtype=np.float64), x, y, p0, p1, n)
            curves.append(ProfileCurve(label=spec.title, unit=rd.unit, samples=samples))
        return ProfileSet(positions, dist, dx, dy, tuple(curves))

    def rect_statistics(
        self, specs: Sequence[PaneSpec], x0: float, y0: float, x1: float, y1: float
    ) -> RegionReport:
        mask = viz.rect_mask(self._x_coords(), self._y_coords(), x0, y0, x1, y1)
        return self._region_report(specs, mask, "rectangle")

    def polygon_statistics(
        self, specs: Sequence[PaneSpec], vertices: list[tuple[float, float]]
    ) -> RegionReport:
        mask = viz.polygon_mask(self._x_coords(), self._y_coords(), vertices)
        return self._region_report(specs, mask, "polygon")

    def _region_report(
        self, specs: Sequence[PaneSpec], mask: npt.NDArray[np.bool_], kind: str
    ) -> RegionReport:
        pixel_area = self.pixel_area_nm2()
        rows: list[RegionStatRow] = []
        count, area = 0, 0.0
        for spec in specs:
            rd = self.render_spec(spec)
            stats = viz.region_stats(
                np.asarray(rd.values, dtype=np.float64), mask, pixel_area_nm2=pixel_area
            )
            rows.append(RegionStatRow(label=spec.title, unit=rd.unit, stats=stats))
            count, area = stats.count, stats.area_nm2
        return RegionReport(kind, count, area, tuple(rows))

    # -- publication figure (read-only) ---------------------------------------

    def figure_spec(
        self,
        panels: Sequence[tuple[PaneSpec, tuple[float, float]]],
        overlays: Sequence[OverlaySpec],
        *,
        kind: str,
        title: str,
    ) -> FigureSpec:
        """Build a serializable, provenance-bearing :class:`FigureSpec` (read-only).

        ``panels`` pairs each visible pane with its current display levels; the
        colormap, unit, extent and conventions are filled from the dataset so the
        figure carries everything needed to explain and regenerate itself.
        """
        panel_specs: list[viz.PanelSpec] = []
        extent: tuple[float, float, float, float] = (0.0, 1.0, 0.0, 1.0)
        for spec, (vmin, vmax) in panels:
            rd = self.render_spec(spec)
            extent = rd.extent_nm
            panel_specs.append(
                viz.PanelSpec(
                    channel=spec.channel,
                    representation=spec.representation,
                    title=spec.title,
                    unit=rd.unit,
                    colormap=rd.colormap,
                    cyclic=rd.cyclic,
                    vmin=float(vmin),
                    vmax=float(vmax),
                )
            )
        length, label = viz.pick_scale_bar(extent[1] - extent[0])
        conventions = self._ds.metadata.conventions
        software = current_software()
        source = self._ds.source
        return FigureSpec(
            title=title,
            kind=kind,
            measurement=self._title,
            source_path=source.path if source is not None else None,
            source_sha256=source.sha256 if source is not None else None,
            panels=tuple(panel_specs),
            extent_nm=extent,
            scale_bar_nm=length,
            scale_bar_label=label,
            overlays=tuple(overlays),
            conventions={
                "spatial_unit": conventions.spatial_unit,
                "origin": conventions.origin,
                "x_dir": conventions.x_dir,
                "y_dir": conventions.y_dir,
                "phase_unit": conventions.phase_unit,
                "phase": "as imported",
            },
            created_at=datetime.now(UTC).isoformat(),
            snomniman_version=software.get("snomniman", ""),
            software=software,
        )

    def _x_coords(self) -> npt.NDArray[np.float64]:
        return np.asarray(self._ds.coordinate("x").values, dtype=np.float64)

    def _y_coords(self) -> npt.NDArray[np.float64]:
        return np.asarray(self._ds.coordinate("y").values, dtype=np.float64)

    def values_at(self, specs: Sequence[PaneSpec], x_nm: float, y_nm: float) -> CursorReadout:
        """The value of every ``spec`` at one physical point (the comparison cursor)."""
        iy, ix, in_bounds = self._nearest(x_nm, y_nm)
        if not in_bounds:
            return CursorReadout(in_bounds=False, x_nm=x_nm, y_nm=y_nm)
        x = np.asarray(self._ds.coordinate("x").values, dtype=np.float64)
        y = np.asarray(self._ds.coordinate("y").values, dtype=np.float64)
        values = tuple(self._value_for(s.channel, s.representation, iy, ix) for s in specs)
        return CursorReadout(True, float(x[ix]), float(y[iy]), values)

    # -- cursor readout (single view) -----------------------------------------

    def cursor_readout(self, x_nm: float, y_nm: float) -> CursorReadout:
        """Physical coordinate + the values under the pointer (current channel + Z)."""
        iy, ix, in_bounds = self._nearest(x_nm, y_nm)
        if not in_bounds:
            return CursorReadout(in_bounds=False, x_nm=x_nm, y_nm=y_nm)
        x = np.asarray(self._ds.coordinate("x").values, dtype=np.float64)
        y = np.asarray(self._ds.coordinate("y").values, dtype=np.float64)
        values: list[CursorValue] = [self._value_for(self._channel, self._representation, iy, ix)]
        if self._ds.is_complex(self._channel):
            values.append(self._value_for(self._channel, PHASE, iy, ix))
        if "Z" in self._ds.channel_names and self._channel != "Z":
            values.append(self._value_for("Z", REAL, iy, ix, label="Z height"))
        return CursorReadout(True, float(x[ix]), float(y[iy]), tuple(values))

    # -- value helpers --------------------------------------------------------

    def _nearest(self, x_nm: float, y_nm: float) -> tuple[int, int, bool]:
        x = np.asarray(self._ds.coordinate("x").values, dtype=np.float64)
        y = np.asarray(self._ds.coordinate("y").values, dtype=np.float64)
        rd = viz.prepare_channel(self._ds, self._channel, self._representation)
        x0, x1, y0, y1 = rd.extent_nm
        if not (x0 <= x_nm <= x1 and y0 <= y_nm <= y1):
            return 0, 0, False
        return int(np.argmin(np.abs(y - y_nm))), int(np.argmin(np.abs(x - x_nm))), True

    def _value_for(
        self, channel: str, representation: str, iy: int, ix: int, *, label: str | None = None
    ) -> CursorValue:
        val = self._ds.channel(channel).values[iy, ix]
        if representation == AMPLITUDE:
            return CursorValue(label or f"{channel} amplitude", f"{float(np.abs(val)):.4g}", "a.u.")
        if representation == PHASE:
            return CursorValue(label or f"{channel} phase", f"{float(np.angle(val)):.4g}", "rad")
        unit = viz.prepare_channel(self._ds, channel).unit
        return CursorValue(label or channel, f"{float(np.real(val)):.4g}", unit)

    # -- comparison helpers ---------------------------------------------------

    def _optical_signal_channels(self) -> list[str]:
        present = set(self._ds.channel_names)
        infos = [
            ch for ch in self._ds.metadata.channels
            if ch.kind == "optical" and ch.role == "signal" and ch.canonical in present
        ]
        infos.sort(key=lambda c: (c.harmonic is None, c.harmonic or 0, c.canonical))
        return [c.canonical for c in infos]

    def _anchor_optical(self) -> str | None:
        """The current channel if it is an optical signal, else a default optical one."""
        opticals = self._optical_signal_channels()
        if self._channel in opticals:
            return self._channel
        return opticals[0] if opticals else None

    def _amplitude_or_real(self, channel: str) -> PaneSpec:
        return PaneSpec(channel, AMPLITUDE if self._ds.is_complex(channel) else REAL)


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #


def _default_title(dataset: Dataset) -> str:
    if dataset.source is not None:
        return Path(dataset.source.path).name
    return dataset.kind.value


def _default_channel(dataset: Dataset) -> str:
    """Pick the channel that best introduces the measurement (O2 contrast, else Z)."""
    names = set(dataset.channel_names)
    optical = sorted(
        ch.harmonic
        for ch in dataset.metadata.channels
        if ch.kind == "optical" and ch.role == "signal" and ch.harmonic is not None
    )
    if 2 in optical and "O2" in names:
        return "O2"
    for order in optical:
        if order >= 2 and f"O{order}" in names:
            return f"O{order}"
    if optical and f"O{optical[0]}" in names:
        return f"O{optical[0]}"
    if "Z" in names:
        return "Z"
    return dataset.channel_names[0]


def _descriptor(ch_info: object) -> str:
    c = ch_info  # typed loosely to avoid importing ChannelInfo name in signatures
    harmonic = getattr(c, "harmonic", None)
    kind = getattr(c, "kind", "")
    role = getattr(c, "role", "signal")
    if kind == "topography":
        base = "height"
    elif harmonic is not None:
        base = f"harmonic {harmonic}"
    else:
        base = kind
    return f"reference ({base})" if role == "reference" else base


def _convention_items(m: Metadata) -> tuple[MetadataItem, ...]:
    c = m.conventions
    return (
        MetadataItem("Spatial unit", c.spatial_unit, None, _CONV),
        MetadataItem("Origin", f"{c.origin}, x {c.x_dir}, y {c.y_dir}", None, _CONV),
        MetadataItem("Phase unit", c.phase_unit, None, _CONV),
        MetadataItem("Phase reference", _s(c.phase_reference), None, _CONV),
        MetadataItem("Phase sign", _s(c.phase_sign), None, _CONV),
    )


def _step_description(step_id: str) -> str:
    if step_id == "io.read":
        return "Imported the raw measurement from the vendor files."
    if step_id == "image.plane_level":
        return "Subtracted a fitted polynomial surface from the target channel."
    return step_id


def _s(value: object) -> str:
    return "unknown" if value is None else str(value)


def _n(value: float | None, digits: int = 4) -> str:
    return "unknown" if value is None else f"{value:.{digits}g}"


def _seq(values: tuple[int, ...]) -> str:
    return ", ".join(str(v) for v in values) if values else "unknown"


def _pair(value: tuple[float, float] | tuple[int, int] | None, fmt: str) -> str:
    return "unknown" if value is None else fmt.format(value[0], value[1])


__all__ = [
    "PRESET_AMP_PHASE",
    "PRESET_HARMONIC_SERIES",
    "PRESET_LABELS",
    "PRESET_OPTICAL_TOPO",
    "PRESET_SAMPLE_REF",
    "ChannelEntry",
    "ChannelGroup",
    "CursorReadout",
    "CursorValue",
    "ExplorerModel",
    "MeasurementIdentity",
    "MetadataItem",
    "MetadataSection",
    "PaneSpec",
    "ProfileCurve",
    "ProfileSet",
    "ProvenanceStep",
    "RegionReport",
    "RegionStatRow",
]
