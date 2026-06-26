"""Typed scientific metadata (data-model.md sec 6).

``Metadata`` stores the scientific *conventions explicitly* (OHD-6: nm, lower-left
origin, phase preserved as imported), a stable typed core (instrument, excitation,
demodulation, scan, acquisition, per-channel info), the original vendor units, and
the **verbatim** vendor header. Missing values are ``None`` - never guessed.

Everything here is plain data and JSON-serializable (``to_dict``/``from_dict``) so
it can travel into Zarr ``attrs`` and the provenance/project JSON. The raw header
is treated strictly as data (injection-safe) and is never executed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .datakind import DataKind

#: Bump when the serialized metadata layout changes (supports migrations).
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Conventions:
    """Scientific conventions, stored explicitly and carried with the data (OHD-6)."""

    spatial_unit: str = "nm"
    origin: str = "lower-left"
    x_dir: str = "right"
    y_dir: str = "up"
    phase_unit: str = "rad"
    phase_reference: str | None = None
    phase_sign: str | None = None


@dataclass(frozen=True)
class Instrument:
    """Instrument identification."""

    vendor: str | None = None
    model: str | None = None
    software_version: str | None = None


@dataclass(frozen=True)
class Excitation:
    """Illumination/source description."""

    source_type: str | None = None
    detector: str | None = None
    wavenumber_cm1: float | None = None
    wavelength_nm: float | None = None
    power: float | None = None


@dataclass(frozen=True)
class Demodulation:
    """Lock-in / demodulation description."""

    detection: str | None = None
    harmonics: tuple[int, ...] = ()


@dataclass(frozen=True)
class ScanInfo:
    """Imaging scan geometry, in canonical nm where applicable."""

    pixels: tuple[int, int] | None = None  # (nx, ny)
    size_nm: tuple[float, float] | None = None  # (x, y) physical extent
    center_nm: tuple[float, float] | None = None
    offset_nm: tuple[float, float] | None = None  # lower-left corner
    pixel_size_nm: tuple[float, float] | None = None
    rotation_deg: float | None = None


@dataclass(frozen=True)
class Acquisition:
    """Per-acquisition parameters."""

    datetime: str | None = None
    integration_time_s: float | None = None
    tapping_amplitude_nm: float | None = None
    setpoint: float | None = None
    averaging: int | None = None


@dataclass(frozen=True)
class ChannelInfo:
    """Per-channel descriptor recorded for every assembled channel.

    ``canonical`` is the internal name (e.g. ``O2``, ``R_O2``, ``Z``, ``Z_C``);
    ``vendor_token`` and ``source_files`` preserve exactly what was on disk so the
    mapping is auditable. ``state`` tracks the channel's processing state
    (raw / referenced / normalized / unwrapped) - always ``"raw"`` on import.
    """

    canonical: str
    kind: str  # "optical" | "mechanical" | "topography"
    role: str  # "signal" | "reference"
    dtype: str  # numpy dtype name, e.g. "complex64" | "float32"
    state: str = "raw"
    harmonic: int | None = None
    amplitude_unit: str | None = None
    phase_unit: str | None = None
    value_unit: str | None = None  # for real channels (e.g. "nm" for Z)
    vendor_token: str | None = None
    source_files: tuple[str, ...] = ()


@dataclass(frozen=True)
class Metadata:
    """Typed metadata container for a :class:`~snomniman.core.dataset.Dataset`."""

    data_kind: DataKind
    conventions: Conventions = field(default_factory=Conventions)
    instrument: Instrument = field(default_factory=Instrument)
    excitation: Excitation = field(default_factory=Excitation)
    demodulation: Demodulation = field(default_factory=Demodulation)
    scan: ScanInfo = field(default_factory=ScanInfo)
    acquisition: Acquisition = field(default_factory=Acquisition)
    channels: tuple[ChannelInfo, ...] = ()
    original_units: dict[str, str] = field(default_factory=dict)
    raw_header: dict[str, Any] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    def channel(self, canonical: str) -> ChannelInfo:
        """Return the :class:`ChannelInfo` for a canonical channel name."""
        for ch in self.channels:
            if ch.canonical == canonical:
                return ch
        raise KeyError(canonical)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict (tuples become lists)."""
        out = asdict(self)
        out["data_kind"] = self.data_kind.value
        return {key: _jsonify(value) for key, value in out.items()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Metadata:
        """Reconstruct from :meth:`to_dict` output (inverse of ``to_dict``)."""
        return cls(
            data_kind=DataKind(data["data_kind"]),
            conventions=Conventions(**data.get("conventions", {})),
            instrument=Instrument(**data.get("instrument", {})),
            excitation=Excitation(**data.get("excitation", {})),
            demodulation=Demodulation(
                detection=data.get("demodulation", {}).get("detection"),
                harmonics=tuple(data.get("demodulation", {}).get("harmonics", ())),
            ),
            scan=_scan_from_dict(data.get("scan", {})),
            acquisition=Acquisition(**data.get("acquisition", {})),
            channels=tuple(
                ChannelInfo(
                    canonical=c["canonical"],
                    kind=c["kind"],
                    role=c["role"],
                    dtype=c["dtype"],
                    state=c.get("state", "raw"),
                    harmonic=c.get("harmonic"),
                    amplitude_unit=c.get("amplitude_unit"),
                    phase_unit=c.get("phase_unit"),
                    value_unit=c.get("value_unit"),
                    vendor_token=c.get("vendor_token"),
                    source_files=tuple(c.get("source_files", ())),
                )
                for c in data.get("channels", ())
            ),
            original_units=dict(data.get("original_units", {})),
            raw_header=dict(data.get("raw_header", {})),
            schema_version=data.get("schema_version", SCHEMA_VERSION),
        )


def _opt_pair(value: Any) -> tuple[Any, Any] | None:
    return None if value is None else (value[0], value[1])


def _scan_from_dict(d: dict[str, Any]) -> ScanInfo:
    return ScanInfo(
        pixels=_opt_pair(d.get("pixels")),
        size_nm=_opt_pair(d.get("size_nm")),
        center_nm=_opt_pair(d.get("center_nm")),
        offset_nm=_opt_pair(d.get("offset_nm")),
        pixel_size_nm=_opt_pair(d.get("pixel_size_nm")),
        rotation_deg=d.get("rotation_deg"),
    )


def _jsonify(obj: Any) -> Any:
    """Recursively convert tuples to lists so the result is JSON-round-trippable."""
    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify(v) for v in obj]
    return obj


__all__ = [
    "SCHEMA_VERSION",
    "Acquisition",
    "ChannelInfo",
    "Conventions",
    "Demodulation",
    "Excitation",
    "Instrument",
    "Metadata",
    "ScanInfo",
]
