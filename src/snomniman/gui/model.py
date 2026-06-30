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

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

import snomniman.processing.image  # noqa: F401  (registers image ops for applicability)
from snomniman import viz
from snomniman.ai import Briefing, WorkflowSuggestions, build_briefing, recommend_workflow
from snomniman.core import Dataset, Metadata, current_software
from snomniman.core.exceptions import ProcessingError
from snomniman.describe import (
    LineageStep,
    OperationDescription,
    OperationParameter,
    describe_operation,
    describe_operations,
    summarize_provenance,
)
from snomniman.diagnostics import OperationApplicability, diagnose, operation_applicability
from snomniman.io import read
from snomniman.processing import CHANNEL_COMPLEX, CHANNEL_REAL, get_step
from snomniman.viz import AMPLITUDE, PHASE, REAL, FigureSpec, OverlaySpec, RegionStats, RenderData

from .export import ExportContext

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


@dataclass(frozen=True)
class DiagnosticRow:
    """One labelled diagnostic fact, already formatted for display."""

    label: str
    value: str


@dataclass(frozen=True)
class DiagnosticSection:
    """A titled group of diagnostic facts (topography, channels, ...)."""

    title: str
    rows: tuple[DiagnosticRow, ...]


# --------------------------------------------------------------------------- #
# Processing-workspace view objects (generic, registry-driven)
# --------------------------------------------------------------------------- #

#: Form-control kinds a generic parameter editor can render. Derived from each
#: parameter's declared Python types + ParameterSpec UI hints, so the GUI never
#: hardcodes a per-operation layout.
FIELD_INT = "int"
FIELD_FLOAT = "float"
FIELD_BOOL = "bool"
FIELD_CHANNEL = "channel"  # a str parameter naming a channel (choices = channel names)
FIELD_ENUM = "enum"  # a fixed set of allowed values (choices = the values)
FIELD_TEXT = "text"  # a free-form string (fallback)


@dataclass(frozen=True)
class OperationField:
    """One editable operation parameter, projected for a generic form control.

    ``kind`` selects the control (see the ``FIELD_*`` constants); ``choices`` holds
    the allowed values for ``FIELD_ENUM`` and the eligible channel names (filtered
    for *this* dataset) for ``FIELD_CHANNEL``, and is empty otherwise.
    """

    name: str
    description: str
    kind: str
    required: bool
    default: object | None
    choices: tuple[object, ...]


@dataclass(frozen=True)
class OperationInput:
    """One non-primary dataset input a multi-input operation needs the user to choose.

    Projected from the operation's declared input slots (the ``primary`` slot is the
    active measurement and needs no picker). The candidate datasets are supplied by
    the window (which owns the project), not the per-measurement model.
    """

    name: str
    description: str


@dataclass(frozen=True)
class InputCandidate:
    """A dataset the user can pick for an operation input: a stable key + a label."""

    key: str
    label: str


@dataclass(frozen=True)
class OperationOption:
    """A registered operation projected for the Processing Workspace.

    Everything the workspace needs to list the operation, explain whether it can
    run (and why not), and build its parameter form - all derived from the
    processing registry, ``ParameterSpec``, and the dataset's capabilities. No
    field here is operation-specific code; adding a new ``ProcessingStep`` fills
    this in automatically.
    """

    step_id: str
    title: str  # human title derived from step_id ("image.plane_level" -> "Plane Level")
    group: str  # logical group derived from the step_id namespace ("Image")
    description: str  # the operation's scientific purpose (its ProcessingStep.description)
    version: int
    deterministic: bool
    applicable: bool  # capability test (from the Diagnostics Engine)
    already_applied: bool  # this step already appears in the provenance DAG
    requirements: tuple[str, ...]  # human-readable required capabilities
    missing: tuple[str, ...]  # human-readable missing capabilities (why unavailable)
    fields: tuple[OperationField, ...]
    blocked_reason: str | None  # set if capability-applicable but a required field can't be filled
    inputs: tuple[OperationInput, ...] = ()  # non-primary dataset inputs (multi-input ops)

    @property
    def available(self) -> bool:
        """True iff the operation can be previewed now (capabilities + fields)."""
        return self.applicable and self.blocked_reason is None


@dataclass(frozen=True)
class PreviewPane:
    """One before/after pane: a labelled spec and its already-rendered data."""

    spec: PaneSpec
    render: RenderData


@dataclass(frozen=True)
class OperationPreview:
    """The result of previewing an operation, before it is committed.

    Carries the derived (not-yet-committed) Dataset plus everything needed to
    explain the derivation: before/after panes, a plain-language change summary
    (what changes / what stays), and the provenance node that *will* be created.
    The original Dataset is untouched - accepting simply adopts ``dataset``.
    """

    step_id: str
    title: str  # suggested title for the derived dataset
    dataset: Dataset  # the derived dataset (committed verbatim on Accept)
    panes: tuple[PreviewPane, ...]
    changes: tuple[str, ...]  # what this operation will change
    unchanged: tuple[str, ...]  # what it leaves untouched
    provenance: ProvenanceStep  # the provenance node that will be recorded


#: Human-readable phrases for each capability, for the "why unavailable" message.
_CAPABILITY_PHRASES = {
    "spatial_2d": "a 2-D scan (x and y axes)",
    "spatial_1d": "a line profile (one spatial axis)",
    "spectral": "a spectral (wavenumber) axis",
    "complex_optical": "complex optical channels (O{n})",
    "complex_mechanical": "complex mechanical channels (M{n})",
    "topography": "a topography channel (Z)",
    "reference": "reference channels (R_*)",
    "multi_harmonic": "multiple harmonic orders",
}


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
        return [
            _format_lineage_step(step)
            for step in summarize_provenance(self._ds.provenance).steps
        ]

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

    # -- measurement export context (read-only) -------------------------------

    def export_context(self) -> ExportContext:
        """Identity + provenance facts that head every measurement (CSV) export.

        Shared by the profile and region exporters so a saved table always records
        which measurement and derivation it came from (the same honesty the figure
        and GSF exports carry).
        """
        source = self._ds.source
        steps = summarize_provenance(self._ds.provenance).steps
        return ExportContext(
            measurement=self._title,
            source_path=source.path if source is not None else None,
            source_sha256=source.sha256 if source is not None else None,
            conventions=self.conventions_summary(),
            provenance=tuple(step.step_id for step in steps),
            snomniman_version=current_software().get("snomniman", ""),
            created_at=datetime.now(UTC).isoformat(),
        )

    # -- diagnostics (read-only deterministic observations) -------------------

    def diagnostics_report(self) -> tuple[DiagnosticSection, ...]:
        """Formatted diagnostics for the inspector.

        The numbers come from the backend Scientific Diagnostics Engine
        (``snomniman.diagnostics``); this method only formats them for reading
        (backend owns the facts, the GUI owns the words). All values are
        deterministic observations, never recommendations.
        """
        report = diagnose(self._ds)
        sections: list[DiagnosticSection] = []

        topo = report.topography
        if topo is not None:
            unit = topo.unit or ""
            sections.append(DiagnosticSection("Topography", (
                DiagnosticRow("Channel", topo.channel),
                DiagnosticRow("Plane tilt", f"{topo.slope_magnitude_per_um:.3g} {unit}/µm".strip()),
                DiagnosticRow(
                    "Tilt x / y",
                    f"{topo.slope_x_per_um:.3g} / {topo.slope_y_per_um:.3g} {unit}/µm".strip(),
                ),
                DiagnosticRow("Height range", _fmt_value(topo.height_range, unit)),
                DiagnosticRow("RMS roughness (detilted)", _fmt_value(topo.rms_roughness, unit)),
            )))

        harm = report.harmonics
        if harm is not None:
            rows = []
            for amp in harm.amplitudes:
                decay = "" if amp.decay_ratio is None else f"  (x{amp.decay_ratio:.2f} vs lower)"
                cls = amp.classification
                if amp.spatial_coherence is not None:
                    cls = f"{cls} (coherence {amp.spatial_coherence:+.2f})"
                rows.append(DiagnosticRow(
                    f"O{amp.order} mean amplitude",
                    f"{amp.mean_amplitude:.3g} a.u.{decay} - {cls}",
                ))
            sections.append(DiagnosticSection("Optical harmonics", tuple(rows)))

        channel_rows = []
        for stat in report.channel_statistics:
            unit = stat.unit or ""
            if stat.finite_count == 0:
                channel_rows.append(DiagnosticRow(stat.channel, "no finite values"))
                continue
            detail = f"range {stat.minimum:.3g} - {stat.maximum:.3g} {unit}".strip()
            if stat.invalid_count:
                detail += f", {stat.invalid_count} invalid"
            channel_rows.append(DiagnosticRow(f"{stat.channel} ({stat.view})", detail))
        sections.append(DiagnosticSection("Channels", tuple(channel_rows)))

        op_rows = []
        for app in report.applicability:
            if not app.applicable:
                status = f"needs {', '.join(app.missing_capabilities)}"
            elif app.already_applied:
                status = "available (already applied)"
            else:
                status = "available"
            op_rows.append(DiagnosticRow(app.step_id, status))
        sections.append(DiagnosticSection("Processing applicability", tuple(op_rows)))

        return tuple(sections)

    # -- scientific briefing (read-only AI orientation) -----------------------

    def scientific_briefing(self) -> Briefing:
        """The measurement-orientation briefing (deterministic facts; no provider).

        The facts come from the backend AI Scientist (`snomniman.ai.build_briefing`,
        grounded in the Description API + Diagnostics Engine). No narrative provider
        is configured in the app yet, so this returns facts only - which are complete
        and authoritative on their own (AI never gates understanding).
        """
        return build_briefing(self._ds, title=self._title)

    def workflow_suggestions(self) -> WorkflowSuggestions:
        """Ranked, grounded 'suggested next steps' for this measurement (read-only).

        The suggestions are produced **deterministically** by the AI Scientist
        (`snomniman.ai.recommend_workflow`) from the Description API + Diagnostics
        Engine: each points at a registered operation that is applicable and not
        already applied, with pre-filled parameters the Processing Workspace can
        preview. No provider is required; nothing is executed or mutated here.
        """
        return recommend_workflow(self._ds, title=self._title)

    # -- processing workspace (generic, registry-driven) ----------------------

    def operation_catalog(self) -> list[OperationOption]:
        """Every registered operation, projected for the Processing Workspace.

        Pure projection of the processing registry + this dataset's capabilities:
        the list, grouping, availability, "why unavailable", and each operation's
        parameter form all come from ``describe`` + ``diagnostics`` + the dataset.
        A newly registered ``ProcessingStep`` appears here automatically, with no
        GUI change (that is the whole point of the workspace).
        """
        apps = {a.step_id: a for a in operation_applicability(self._ds)}
        return [self._operation_option(d, apps.get(d.step_id)) for d in describe_operations()]

    def operation_option(self, step_id: str) -> OperationOption:
        """Project one registered operation for the workspace (raises if unknown)."""
        apps = {a.step_id: a for a in operation_applicability(self._ds)}
        return self._operation_option(describe_operation(step_id), apps.get(step_id))

    def preview_operation(
        self,
        step_id: str,
        params: Mapping[str, object],
        inputs: Mapping[str, Dataset] | None = None,
    ) -> OperationPreview:
        """Apply ``step_id`` with ``params`` to a *copy* and describe the result.

        Builds the step from the registry and applies it to this measurement as the
        ``"primary"`` input, plus any extra named ``inputs`` for a multi-input
        operation (e.g. ``{"secondary": other_dataset}`` for arithmetic). Returns an
        :class:`OperationPreview` describing the derivation - before/after panes, a
        change summary, and the provenance node that will be recorded (it references
        every input). The active Dataset is **not** modified; the derived Dataset is
        carried on the preview and committed verbatim only if the user accepts. Raises
        :exc:`~snomniman.core.ProcessingError` for invalid params, incompatible
        inputs, or unmet preconditions (the caller surfaces it; nothing is committed).
        """
        step = get_step(step_id)(**params)
        all_inputs: dict[str, Dataset] = {"primary": self._ds}
        if inputs:
            all_inputs.update(inputs)
        derived = step.apply(all_inputs)
        changes, unchanged, focus = self._diff_summary(self._ds, derived)
        panes = self._preview_panes(self._ds, derived, focus)
        lineage = summarize_provenance(derived.provenance).steps
        provenance = _format_lineage_step(lineage[-1])
        return OperationPreview(
            step_id=step_id,
            title=self._derived_title(step_id, dict(params)),
            dataset=derived,
            panes=panes,
            changes=changes,
            unchanged=unchanged,
            provenance=provenance,
        )

    def _operation_option(
        self, desc: OperationDescription, app: OperationApplicability | None
    ) -> OperationOption:
        fields = tuple(self._operation_field(p) for p in desc.parameters)
        applicable = app.applicable if app is not None else True
        requirements = tuple(
            _capability_phrase(c) for c in (app.required_capabilities if app else ())
        )
        missing = tuple(
            _capability_phrase(c) for c in (app.missing_capabilities if app else ())
        )
        blocked = self._blocked_reason(fields) if applicable else None
        # Non-primary input slots become dataset pickers; the window supplies the
        # candidate datasets (it owns the project), so candidates are not built here.
        op_inputs = tuple(
            OperationInput(slot.name, slot.description)
            for slot in desc.inputs
            if slot.name != "primary"
        )
        return OperationOption(
            step_id=desc.step_id,
            title=_operation_title(desc.step_id),
            group=_operation_group(desc.step_id),
            description=desc.description,
            version=desc.version,
            deterministic=desc.deterministic,
            applicable=applicable,
            already_applied=app.already_applied if app is not None else False,
            requirements=requirements,
            missing=missing,
            fields=fields,
            blocked_reason=blocked,
            inputs=op_inputs,
        )

    def _operation_field(self, p: OperationParameter) -> OperationField:
        """Map one parameter (types + UI hints) to a generic form-control descriptor."""
        if p.channel_role is not None:
            return OperationField(
                p.name, p.description, FIELD_CHANNEL, p.required, p.default,
                self._channels_for_role(p.channel_role),
            )
        if p.choices is not None:
            return OperationField(
                p.name, p.description, FIELD_ENUM, p.required, p.default, tuple(p.choices)
            )
        return OperationField(
            p.name, p.description, _scalar_kind(p.types), p.required, p.default, ()
        )

    def _channels_for_role(self, role: str) -> tuple[str, ...]:
        """Channel names of *this* dataset eligible for a channel parameter's role."""
        names = self._ds.channel_names
        if role == CHANNEL_REAL:
            return tuple(n for n in names if not self._ds.is_complex(n))
        if role == CHANNEL_COMPLEX:
            return tuple(n for n in names if self._ds.is_complex(n))
        return tuple(names)

    @staticmethod
    def _blocked_reason(fields: tuple[OperationField, ...]) -> str | None:
        """Why a capability-applicable operation still cannot run on this dataset."""
        for f in fields:
            if f.required and f.kind == FIELD_CHANNEL and not f.choices:
                return f"this measurement has no eligible channel for '{f.name}'"
        return None

    def _derived_title(self, step_id: str, params: dict[str, object]) -> str:
        title = _operation_title(step_id).lower()
        for p in describe_operation(step_id).parameters:
            if p.channel_role is not None and p.name in params:
                return f"{self._title} -> {title} ({params[p.name]})"
        return f"{self._title} -> {title}"

    # -- preview diff (generic: compares the derived dataset to the current one) --

    def _diff_summary(
        self, before: Dataset, after: Dataset
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        before_names = list(before.channel_names)
        after_names = list(after.channel_names)
        before_set, after_set = set(before_names), set(after_names)
        added = [c for c in after_names if c not in before_set]
        removed = [c for c in before_names if c not in after_set]
        common = [c for c in after_names if c in before_set]
        shape_changed = dict(before.data.sizes) != dict(after.data.sizes)
        modified = [
            c for c in common
            if before.channel(c).values.shape == after.channel(c).values.shape
            and not _arrays_equal(before.channel(c).values, after.channel(c).values)
        ]

        changes: list[str] = []
        if shape_changed:
            changes.append(_shape_change_line(before, after))
        changes.extend(_added_channel_line(after, c) for c in added)
        changes.extend(f"Removes channel {c}." for c in removed)
        changes.extend(f"Recomputes channel {c}." for c in modified)
        changes.extend(_state_change_lines(before, after))
        phase_line = _phase_reference_change(before, after)
        if phase_line is not None:
            changes.append(phase_line)

        focus_source = [*modified, *added] or [self._channel]
        ordered = ([self._channel] if self._channel in focus_source else []) + [
            c for c in focus_source if c != self._channel
        ]
        focus = tuple(c for c in ordered[:2] if c in after_set or c in before_set)

        unchanged = _unchanged_lines(before, after, modified, added, removed, shape_changed)
        return tuple(changes), unchanged, focus

    def _preview_panes(
        self, before: Dataset, after: Dataset, focus: tuple[str, ...]
    ) -> tuple[PreviewPane, ...]:
        panes: list[PreviewPane] = []
        for channel in focus:
            panes.extend(self._before_panes(before, after, channel))
            rep = viz.default_representation(after, channel)
            is_new = channel not in before.channel_names
            label = f"{channel} (new)" if is_new else f"{channel} (after)"
            panes.append(
                PreviewPane(
                    PaneSpec(channel, rep, label=label),
                    viz.prepare_channel(after, channel, rep),
                )
            )
        return tuple(panes)

    def _before_panes(
        self, before: Dataset, after: Dataset, channel: str
    ) -> list[PreviewPane]:
        if channel in before.channel_names:
            rep = viz.default_representation(before, channel)
            return [
                PreviewPane(
                    PaneSpec(channel, rep, label=f"{channel} (before)"),
                    viz.prepare_channel(before, channel, rep),
                )
            ]
        # An added channel had no "before"; show the source it was derived from.
        source, rep = _derived_source(before, after, channel)
        if source is None:
            return []
        return [
            PreviewPane(
                PaneSpec(source, rep, label=f"{source} (before)"),
                viz.prepare_channel(before, source, rep),
            )
        ]

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
# Measurement session (one measurement's live working state; Qt-free)
# --------------------------------------------------------------------------- #


@dataclass
class MeasurementSession:
    """One measurement's live working state in the Explorer (Qt-free).

    The Explorer binds a single set of widgets to the *active* session at a time. A
    session owns the active view-model (``model``), its derivation back-stack
    (``history``, oldest first), a stable project-local id, and an editable display
    ``title``. ``measure_records`` and ``view_state`` hold the overlay geometry and
    the view (channel / representation / mode / preset) captured when the user
    switches away, so switching back restores the measurement without re-reading
    from disk. The immutable, persisted counterpart is ``pipeline.Measurement``.
    """

    model: ExplorerModel
    measurement_id: str
    title: str
    history: list[ExplorerModel] = field(default_factory=list)
    measure_records: list[dict[str, Any]] = field(default_factory=list)
    view_state: dict[str, Any] = field(default_factory=dict)


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
    """A reading-friendly description of a provenance step.

    The raw-import node is not a registered operation; every other step's words
    come from the operation's own ``ProcessingStep.description`` (single source of
    truth - no per-operation table to maintain here).
    """
    if step_id == "io.read":
        return "Imported the raw measurement from the vendor files."
    try:
        return get_step(step_id).description
    except ProcessingError:
        return step_id


def _format_lineage_step(step: LineageStep) -> ProvenanceStep:
    """Format one Description-API lineage node for the inspector / preview."""
    sources = tuple(
        f"{s.name}: {s.filename} (sha256 {s.sha256[:12]}..., reader {s.reader})"
        for s in step.sources
    )
    return ProvenanceStep(
        node_id=step.node_id,
        step_id=step.step_id,
        description=_step_description(step.step_id),
        deterministic=step.deterministic,
        params=dict(step.params),
        software=dict(step.software),
        sources=sources,
    )


def _operation_title(step_id: str) -> str:
    """Human title from a step_id: ``image.plane_level`` -> ``Plane Level``."""
    return step_id.split(".")[-1].replace("_", " ").title()


def _operation_group(step_id: str) -> str:
    """Logical group from a step_id namespace: ``image.plane_level`` -> ``Image``."""
    head = step_id.split(".")[0] if "." in step_id else "general"
    return head.replace("_", " ").title()


def _capability_phrase(value: str) -> str:
    return _CAPABILITY_PHRASES.get(value, value)


def _scalar_kind(types: tuple[str, ...]) -> str:
    """Form-control kind for a scalar parameter from its accepted type names."""
    if "bool" in types:  # bool is a subclass of int - test it first
        return FIELD_BOOL
    if "float" in types:  # (int, float) accepts floats -> use the float control
        return FIELD_FLOAT
    if "int" in types:
        return FIELD_INT
    return FIELD_TEXT


def _arrays_equal(a: npt.NDArray[Any], b: npt.NDArray[Any]) -> bool:
    """True iff two arrays are equal (NaN==NaN), comparing complex by components."""
    a = np.asarray(a)
    b = np.asarray(b)
    if a.shape != b.shape:
        return False
    if np.iscomplexobj(a) or np.iscomplexobj(b):
        return _arrays_equal(a.real, b.real) and _arrays_equal(a.imag, b.imag)
    if np.issubdtype(a.dtype, np.floating):
        return bool(np.array_equal(a, b, equal_nan=True))
    return bool(np.array_equal(a, b))


def _shape_change_line(before: Dataset, after: Dataset) -> str:
    bx, by = int(before.data.sizes["x"]), int(before.data.sizes["y"])
    ax, ay = int(after.data.sizes["x"]), int(after.data.sizes["y"])
    return f"Restricts the field of view to {ax}x{ay} pixels (was {bx}x{by})."


def _added_channel_line(after: Dataset, channel: str) -> str:
    attrs = after.data[channel].attrs
    bits: list[str] = []
    quantity = attrs.get("quantity")
    if isinstance(quantity, str) and quantity:
        bits.append(quantity.replace("_", " "))
    unit = attrs.get("unit")
    if isinstance(unit, str) and unit:
        bits.append(unit)
    suffix = f" ({', '.join(bits)})" if bits else ""
    source = attrs.get("derived_from")
    if isinstance(source, str) and source:
        return f"Adds channel {channel}{suffix}, derived from {source}."
    return f"Adds channel {channel}{suffix}."


def _state_change_lines(before: Dataset, after: Dataset) -> list[str]:
    before_states = {c.canonical: c.state for c in before.metadata.channels}
    lines: list[str] = []
    for c in after.metadata.channels:
        old = before_states.get(c.canonical)
        if old is not None and c.state != old:
            lines.append(f"Marks {c.canonical} as {c.state}.")
    return lines


def _phase_reference_change(before: Dataset, after: Dataset) -> str | None:
    old = before.metadata.conventions.phase_reference
    new = after.metadata.conventions.phase_reference
    if new != old and new:
        return f"Re-references phase to: {new}."
    return None


def _unchanged_lines(
    before: Dataset,
    after: Dataset,
    modified: list[str],
    added: list[str],
    removed: list[str],
    shape_changed: bool,
) -> tuple[str, ...]:
    lines = ["The raw measurement is untouched; this records a new derived dataset."]
    touched = set(modified) | set(added) | set(removed)
    untouched = [c for c in before.channel_names if c not in touched]
    if untouched and not shape_changed:
        kept = ", ".join(untouched)
        lines.append(f"{len(untouched)} other channel(s) keep their values: {kept}.")
    if not shape_changed:
        lines.append("Coordinates and field of view are unchanged.")
    conv = before.metadata.conventions
    if _phase_reference_change(before, after) is None:
        lines.append(f"Conventions unchanged ({conv.spatial_unit}, {conv.origin} origin).")
    return tuple(lines)


def _derived_source(
    before: Dataset, after: Dataset, channel: str
) -> tuple[str | None, str]:
    """The source channel + best 'before' representation for an added channel.

    Data-driven (reads the new channel's ``derived_from``/``quantity`` attrs the
    operation chose to set), so it is generic - no step_id is hardcoded.
    """
    attrs = after.data[channel].attrs
    source = attrs.get("derived_from")
    if isinstance(source, str) and source in before.channel_names:
        if attrs.get("quantity") == "unwrapped_phase" and before.is_complex(source):
            return source, PHASE
        return source, viz.default_representation(before, source)
    return None, REAL


def _fmt_value(value: float | None, unit: str) -> str:
    """Format a possibly-missing numeric diagnostic with its unit."""
    if value is None:
        return "unknown"
    return f"{value:.3g} {unit}".strip()


def _s(value: object) -> str:
    return "unknown" if value is None else str(value)


def _n(value: float | None, digits: int = 4) -> str:
    return "unknown" if value is None else f"{value:.{digits}g}"


def _seq(values: tuple[int, ...]) -> str:
    return ", ".join(str(v) for v in values) if values else "unknown"


def _pair(value: tuple[float, float] | tuple[int, int] | None, fmt: str) -> str:
    return "unknown" if value is None else fmt.format(value[0], value[1])


__all__ = [
    "FIELD_BOOL",
    "FIELD_CHANNEL",
    "FIELD_ENUM",
    "FIELD_FLOAT",
    "FIELD_INT",
    "FIELD_TEXT",
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
    "InputCandidate",
    "MeasurementIdentity",
    "MeasurementSession",
    "MetadataItem",
    "MetadataSection",
    "OperationField",
    "OperationInput",
    "OperationOption",
    "OperationPreview",
    "PaneSpec",
    "PreviewPane",
    "ProfileCurve",
    "ProfileSet",
    "ProvenanceStep",
    "RegionReport",
    "RegionStatRow",
]
