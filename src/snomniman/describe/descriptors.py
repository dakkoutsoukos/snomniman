"""Structured, JSON-serializable descriptors for the Scientific Description API.

These frozen value objects are *data-tier* projections of the scientific core
(``Dataset``, ``Metadata``, the provenance DAG, ``RawSource``) and the processing
registry.  They hold **honest values** - ``None`` where a value is genuinely
unknown, never an ``"unknown"`` placeholder string (formatting unknowns is a
presentation choice that belongs to a consumer, e.g. the Explorer).  Every
descriptor serializes losslessly to a JSON-ready ``dict`` via :meth:`to_dict`
(tuples become lists; nested descriptors become nested dicts).

They are produced by :mod:`snomniman.describe.summarize`.  See
``docs/description-api.md``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ChannelDescription:
    """One channel: what it is, what it holds, and which views it offers."""

    canonical: str
    kind: str | None  # "optical" | "mechanical" | "topography" (from ChannelInfo)
    role: str | None  # "signal" | "reference"
    harmonic: int | None
    is_complex: bool
    dtype: str
    state: str  # raw / referenced / normalized / unwrapped
    value_unit: str | None  # for real channels (e.g. "nm" for Z)
    amplitude_unit: str | None
    phase_unit: str | None
    available_views: tuple[str, ...]  # ("amplitude", "phase") or ("value",)

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class ConventionsDescription:
    """The scientific conventions in force (OHD-6), reported explicitly."""

    spatial_unit: str
    origin: str
    x_dir: str
    y_dir: str
    phase_unit: str
    phase_reference: str | None
    phase_sign: str | None
    phase_handling: str = "as imported"  # OHD-6D: never silently transformed

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class GeometryDescription:
    """Imaging scan geometry, in canonical nm where applicable."""

    pixels: tuple[int, int] | None
    size_nm: tuple[float, float] | None
    pixel_size_nm: tuple[float, float] | None
    offset_nm: tuple[float, float] | None
    center_nm: tuple[float, float] | None
    rotation_deg: float | None

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class SpectralGeometryDescription:
    """Spectral-axis geometry (the ``SpectralInfo`` analogue of ``GeometryDescription``)."""

    wavenumber_min_cm1: float | None
    wavenumber_max_cm1: float | None
    n_points: int | None
    sampling_cm1: float | None

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class MetadataSummary:
    """A curated, glanceable projection of :class:`~snomniman.core.Metadata`.

    Deliberately a *summary*: it omits the bulky verbatim vendor header (use
    ``Metadata.to_dict`` / ``Dataset.metadata`` for that) and keeps the
    scientifically salient fields plus the explicit conventions and geometry.
    """

    data_kind: str
    vendor: str | None
    model: str | None
    software_version: str | None
    source_type: str | None
    detector: str | None
    wavenumber_cm1: float | None
    wavelength_nm: float | None
    detection: str | None
    harmonics: tuple[int, ...]
    datetime: str | None
    integration_time_s: float | None
    tapping_amplitude_nm: float | None
    setpoint: float | None
    averaging: int | None
    geometry: GeometryDescription
    spectral: SpectralGeometryDescription | None
    conventions: ConventionsDescription
    original_units: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class SourceDescription:
    """A raw-data origin: a referenced (never copied) file or directory."""

    name: str  # the named provenance edge (e.g. "measurement")
    path: str
    filename: str
    sha256: str
    reader: str
    is_directory: bool
    bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class LineageStep:
    """One node of the provenance DAG, projected for inspection."""

    node_id: str
    step_id: str
    step_version: int
    deterministic: bool
    params: dict[str, Any]
    software: dict[str, str]
    applied_at: str
    inputs: tuple[str, ...]  # named input edges into this node
    sources: tuple[SourceDescription, ...]
    is_raw: bool

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class ProvenanceSummary:
    """The derivation history of a dataset: raw or derived, and how."""

    is_raw: bool
    n_steps: int
    steps: tuple[LineageStep, ...]  # topological order (inputs before consumers)
    sources: tuple[SourceDescription, ...]  # distinct raw origins in the graph

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class OperationParameter:
    """One parameter a processing operation accepts.

    ``choices`` and ``channel_role`` mirror the operation's
    :class:`~snomniman.processing.ParameterSpec` UI hints: ``choices`` is a fixed
    set of allowed values (an enum) or ``None``; ``channel_role`` marks a ``str``
    parameter as naming a real/complex/any channel (``"real"`` / ``"complex"`` /
    ``"any"``) or ``None``. They let a generic consumer build the right control
    without operation-specific code.
    """

    name: str
    description: str
    types: tuple[str, ...]  # accepted Python type names
    required: bool
    default: Any
    choices: tuple[Any, ...] | None = None
    channel_role: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class OperationInputSlot:
    """One Dataset input an operation consumes (the projection of an ``InputSpec``).

    Mirrors :class:`OperationParameter` for *datasets* rather than scalar params: a
    single-input operation projects one ``"primary"`` slot; a multi-input operation
    projects one slot per input, so a generic consumer can build the right dataset
    picker per slot without operation-specific code.
    """

    name: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class OperationDescription:
    """A registered processing operation: its input slots and parameter schema."""

    step_id: str
    version: int
    description: str
    deterministic: bool
    parameters: tuple[OperationParameter, ...]
    inputs: tuple[OperationInputSlot, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class MeasurementDescription:
    """The top-level aggregate: everything a consumer needs to orient itself.

    What the measurement *is* (kind, raw/derived), what it *contains* (dims,
    capabilities, channels), its *metadata* summary, and its *provenance*.  The
    operation catalogue is queried separately (it is registry-wide, not a
    property of one measurement) via :func:`~snomniman.describe.describe_operations`.
    """

    title: str | None
    data_kind: str
    is_raw: bool
    dims: dict[str, int]
    capabilities: tuple[str, ...]
    channels: tuple[ChannelDescription, ...]
    metadata: MetadataSummary
    provenance: ProvenanceSummary

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


def _jsonify(obj: Any) -> Any:
    """Recursively convert tuples to lists so the result is JSON-round-trippable."""
    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify(v) for v in obj]
    return obj


__all__ = [
    "ChannelDescription",
    "ConventionsDescription",
    "GeometryDescription",
    "LineageStep",
    "MeasurementDescription",
    "MetadataSummary",
    "OperationDescription",
    "OperationInputSlot",
    "OperationParameter",
    "ProvenanceSummary",
    "SourceDescription",
    "SpectralGeometryDescription",
]
