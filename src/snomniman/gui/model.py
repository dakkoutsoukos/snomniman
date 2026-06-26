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

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from snomniman import viz
from snomniman.core import Dataset, Metadata
from snomniman.io import read
from snomniman.viz import RenderData

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
        steps = list(self._ds.provenance.iter_nodes())
        if self._ds.is_raw:
            return "This is the raw measurement - nothing has been done to it."
        return f"Derived result - {len(steps)} step(s) from the raw measurement."

    def provenance_steps(self) -> list[ProvenanceStep]:
        out: list[ProvenanceStep] = []
        for node in self._ds.provenance.iter_nodes():
            rec = node.record
            sources = tuple(
                f"{name}: {Path(src.path).name} "
                f"(sha256 {src.sha256[:12]}..., reader {src.reader})"
                for name, src in node.sources.items()
            )
            out.append(ProvenanceStep(
                node_id=node.node_id,
                step_id=rec.step_id,
                description=_step_description(rec.step_id),
                deterministic=rec.deterministic,
                params=dict(rec.params),
                software=dict(rec.software),
                sources=sources,
            ))
        return out

    # -- cursor readout -------------------------------------------------------

    def cursor_readout(self, x_nm: float, y_nm: float) -> CursorReadout:
        """Physical coordinate + the values under the pointer (current channel + Z)."""
        x = np.asarray(self._ds.coordinate("x").values, dtype=np.float64)
        y = np.asarray(self._ds.coordinate("y").values, dtype=np.float64)
        rd = viz.prepare_channel(self._ds, self._channel, self._representation)
        x0, x1, y0, y1 = rd.extent_nm
        if not (x0 <= x_nm <= x1 and y0 <= y_nm <= y1):
            return CursorReadout(in_bounds=False, x_nm=x_nm, y_nm=y_nm)
        ix = int(np.argmin(np.abs(x - x_nm)))
        iy = int(np.argmin(np.abs(y - y_nm)))

        values: list[CursorValue] = [self._value_at(self._channel, iy, ix)]
        if self._ds.is_complex(self._channel):
            values.append(self._phase_at(self._channel, iy, ix))
        for topo in ("Z",):  # topography context, if present
            if topo in self._ds.channel_names and topo != self._channel:
                values.append(self._value_at(topo, iy, ix, label="Z height"))
        return CursorReadout(True, float(x[ix]), float(y[iy]), tuple(values))

    def _value_at(self, channel: str, iy: int, ix: int, *, label: str | None = None) -> CursorValue:
        da = self._ds.channel(channel)
        if self._ds.is_complex(channel):
            amp = float(np.abs(da.values[iy, ix]))
            return CursorValue(label or f"{channel} amplitude", f"{amp:.4g}", "a.u.")
        unit = viz.prepare_channel(self._ds, channel).unit
        return CursorValue(label or channel, f"{float(da.values[iy, ix]):.4g}", unit)

    def _phase_at(self, channel: str, iy: int, ix: int) -> CursorValue:
        val = self._ds.channel(channel).values[iy, ix]
        return CursorValue(f"{channel} phase", f"{float(np.angle(val)):.4g}", "rad")


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
    "ChannelEntry",
    "ChannelGroup",
    "CursorReadout",
    "CursorValue",
    "ExplorerModel",
    "MeasurementIdentity",
    "MetadataItem",
    "MetadataSection",
    "ProvenanceStep",
]
