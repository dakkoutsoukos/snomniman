"""neaSNOM imaging reader: a GSF measurement *directory* -> ``Dataset`` (OHD-9).

A neaSNOM measurement is a directory containing one ``.gsf`` file per channel
(``O0A raw`` ... ``R-Z CH``) plus a ``.txt`` parameter file. This reader:

1. discovers the channel files and the parameter file;
2. parses each GSF header + float32 grid (:mod:`snomniman.io.gsf`);
3. validates that all channels share one scan geometry;
4. converts to canonical conventions - **nm** spatial units, and the
   **lower-left / x-right / y-up** origin (GSF stores rows top-to-bottom, so each
   grid is flipped vertically; the transformation is recorded in provenance);
5. assembles complex optical/mechanical channels ``O{n} = A * exp(i*P)`` and real
   topography channels, preserving phase exactly as imported (OHD-6D);
6. builds typed :class:`Metadata` (conventions explicit, verbatim header kept),
   a :class:`RawSource` anchor, and a single ``io.read`` provenance node.

Vendor parsing is validated against the real file (Rule 6) and unknown header
fields are preserved verbatim rather than discarded.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import xarray as xr

from snomniman.core import (
    Acquisition,
    ChannelInfo,
    Conventions,
    DataKind,
    Dataset,
    Demodulation,
    Excitation,
    Instrument,
    Metadata,
    ProvenanceNode,
    RawSource,
    ScanInfo,
    StepRecord,
    current_software,
    length_scale_to_nm,
)
from snomniman.core.exceptions import ReaderError

from .gsf import GsfFile, read_gsf

#: Reader id (format + version), used in ``RawSource`` and the registry.
READER_ID = "neasnom.image.gsf.v1"

# Channel token grammar (the part of a filename after the measurement-name prefix).
# Optical/mechanical: e.g. "O2A raw", "R-O3P raw". Topography: "Z raw", "R-Z CH".
_OM_TOKEN = re.compile(
    r"^(?P<ref>R-)?(?P<kind>[OM])(?P<order>\d+)(?P<comp>[AP])(?:\s+(?P<state>\S+))?$"
)
_Z_TOKEN = re.compile(r"^(?P<ref>R-)?Z(?:\s+(?P<variant>\S+))?$")

# Header fields that must match across all channels for one coherent scan grid.
_GEOMETRY_KEYS = ("XRes", "YRes", "XReal", "YReal", "XOffset", "YOffset", "XYUnits")


def read_neasnom_measurement(path: str | Path) -> Dataset:
    """Read a neaSNOM GSF measurement directory into a validated ``Dataset``."""
    root = Path(path)
    if not root.is_dir():
        raise ReaderError(f"not a measurement directory: {root}")

    txt_path = _find_param_file(root)
    # The directory name is the reliable channel-file prefix. The .txt stem is
    # not: some acquisitions name it "<dir> Spectra.txt" (a different modality).
    measbase = root.name
    gsf_paths = sorted(root.glob("*.gsf"))
    if not gsf_paths:
        raise ReaderError(f"no .gsf channel files in {root}")

    parsed: list[tuple[str, GsfFile]] = []
    for gp in gsf_paths:
        token = _channel_token(gp.stem, measbase)
        parsed.append((token, read_gsf(gp)))

    grid = _validate_geometry([gf for _, gf in parsed], root)
    x_nm, y_nm = _build_axes(grid)

    groups = _group_channels(parsed)
    data_vars: dict[str, Any] = {}
    channel_infos: list[ChannelInfo] = []
    optical_orders: set[int] = set()

    for canonical, group in groups.items():
        var, info = _assemble_channel(canonical, group, grid)
        data_vars[canonical] = var
        channel_infos.append(info)
        if info.kind == "optical" and info.role == "signal" and info.harmonic is not None:
            optical_orders.add(info.harmonic)

    xattrs = {"unit": "nm", "long_name": "x (fast scan axis)", "axis": "X"}
    yattrs = {"unit": "nm", "long_name": "y (slow scan axis)", "axis": "Y"}
    xr_ds = xr.Dataset(
        data_vars=data_vars,
        coords={"x": ("x", x_nm, xattrs), "y": ("y", y_nm, yattrs)},
    )

    txt = _parse_param_file(txt_path)
    metadata = _build_metadata(
        grid=grid,
        txt=txt,
        sample_header=parsed[0][1].header,
        channels=tuple(sorted(channel_infos, key=lambda c: c.canonical)),
        harmonics=tuple(sorted(optical_orders)),
    )

    source = RawSource.from_directory(
        root,
        reader=READER_ID,
        files=[*gsf_paths, txt_path],
        reader_params={"channel_map": "default"},
    )
    record = StepRecord(
        step_id="io.read",
        step_version=1,
        deterministic=True,
        params={
            "reader": READER_ID,
            "orientation": "vendor_top_to_bottom->canonical_lower_left_y_up (flipud)",
            "length_unit_conversion": f"{grid.xyunits}->nm",
        },
        software=current_software(),
        input_fingerprint=f"sha256:{source.sha256}",
        notes=f"neaSNOM measurement '{measbase}'",
    )
    node = ProvenanceNode(node_id="n0", record=record, sources={"source": source})

    return Dataset(
        xr_ds,
        kind=DataKind.IMAGE,
        metadata=metadata,
        provenance=node,
        source=source,
    )


# --------------------------------------------------------------------------- #
# Geometry
# --------------------------------------------------------------------------- #


class _Grid:
    """The shared scan grid (all channels share this)."""

    __slots__ = ("xoffset", "xreal", "xres", "xyunits", "yoffset", "yreal", "yres")

    def __init__(self, gf: GsfFile) -> None:
        self.xres = gf.xres
        self.yres = gf.yres
        self.xreal = _require(gf.xreal, "XReal", gf)
        self.yreal = _require(gf.yreal, "YReal", gf)
        self.xoffset = gf.xoffset or 0.0
        self.yoffset = gf.yoffset or 0.0
        self.xyunits = gf.xyunits or "m"


def _require(value: float | None, key: str, gf: GsfFile) -> float:
    if value is None:
        raise ReaderError(f"GSF header missing {key} in {gf.path}")
    return value


def _validate_geometry(files: list[GsfFile], root: Path) -> _Grid:
    ref = files[0]
    for gf in files[1:]:
        for key in _GEOMETRY_KEYS:
            if gf.header.get(key) != ref.header.get(key):
                raise ReaderError(
                    f"inconsistent scan geometry in {root}: {key} "
                    f"{gf.header.get(key)!r} != {ref.header.get(key)!r} ({gf.path})"
                )
    return _Grid(ref)


def _build_axes(grid: _Grid) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Pixel-center coordinates in canonical nm; both axes increase (lower-left)."""
    factor = length_scale_to_nm(grid.xyunits)
    dx = grid.xreal * factor / grid.xres
    dy = grid.yreal * factor / grid.yres
    x0 = grid.xoffset * factor
    y0 = grid.yoffset * factor
    x = x0 + (np.arange(grid.xres, dtype=np.float64) + 0.5) * dx
    y = y0 + (np.arange(grid.yres, dtype=np.float64) + 0.5) * dy
    return x, y


# --------------------------------------------------------------------------- #
# Channel discovery and assembly
# --------------------------------------------------------------------------- #


def _channel_token(stem: str, measbase: str) -> str:
    prefix = measbase + " "
    if stem.startswith(prefix):
        return stem[len(prefix) :]
    return stem  # fall back to the whole stem if the prefix does not match


class _ChannelGroup:
    """Accumulates the file(s) that build one canonical channel."""

    __slots__ = (
        "amp", "canonical", "files", "harmonic", "kind",
        "phase", "role", "state", "value", "variant",
    )

    def __init__(self, canonical: str, kind: str, role: str) -> None:
        self.canonical = canonical
        self.kind = kind
        self.role = role
        self.harmonic: int | None = None
        self.variant: str | None = None
        self.state = "raw"
        self.amp: GsfFile | None = None
        self.phase: GsfFile | None = None
        self.value: GsfFile | None = None
        self.files: list[str] = []


def _group_channels(parsed: list[tuple[str, GsfFile]]) -> dict[str, _ChannelGroup]:
    groups: dict[str, _ChannelGroup] = {}
    for token, gf in parsed:
        fname = Path(gf.path).name if gf.path else token
        m = _OM_TOKEN.match(token)
        if m is not None:
            role = "reference" if m.group("ref") else "signal"
            kind = "optical" if m.group("kind") == "O" else "mechanical"
            order = int(m.group("order"))
            canonical = f"{'R_' if role == 'reference' else ''}{m.group('kind')}{order}"
            g = groups.setdefault(canonical, _ChannelGroup(canonical, kind, role))
            g.harmonic = order
            g.state = m.group("state") or "raw"
            if m.group("comp") == "A":
                g.amp = gf
            else:
                g.phase = gf
            g.files.append(fname)
            continue

        z = _Z_TOKEN.match(token)
        if z is not None:
            role = "reference" if z.group("ref") else "signal"
            variant = z.group("variant")
            suffix = "" if variant in (None, "raw") else f"_{variant}"
            canonical = f"{'R_' if role == 'reference' else ''}Z{suffix}"
            g = groups.setdefault(canonical, _ChannelGroup(canonical, "topography", role))
            g.variant = variant
            g.value = gf
            g.files.append(fname)
            continue

        raise ReaderError(
            f"unrecognized channel token {token!r} ({fname}); this directory may be "
            f"a non-imaging neaSNOM modality not supported by {READER_ID}"
        )
    return groups


def _assemble_channel(
    canonical: str, group: _ChannelGroup, grid: _Grid
) -> tuple[tuple[tuple[str, str], npt.NDArray[Any], dict[str, Any]], ChannelInfo]:
    """Build the xarray variable tuple and the :class:`ChannelInfo` for a channel."""
    files = tuple(group.files)
    if group.kind in ("optical", "mechanical"):
        if group.amp is None and group.phase is None:  # pragma: no cover - defensive
            raise ReaderError(f"channel {canonical!r} has no amplitude or phase file")
        if group.amp is not None and group.phase is not None:
            amp = _orient(group.amp.data).astype(np.float64)
            phase = _orient(group.phase.data).astype(np.float64)
            arr: npt.NDArray[Any] = (amp * np.exp(1j * phase)).astype(np.complex64)
            attrs = {
                "canonical": canonical,
                "kind": group.kind,
                "role": group.role,
                "harmonic": group.harmonic,
                "state": group.state,
                "amplitude_unit": "a.u.",
                "phase_unit": "rad",
                "vendor_token": _vendor_token(canonical, group.state),
            }
            info = ChannelInfo(
                canonical=canonical,
                kind=group.kind,
                role=group.role,
                dtype="complex64",
                state=group.state,
                harmonic=group.harmonic,
                amplitude_unit="a.u.",
                phase_unit="rad",
                vendor_token=_vendor_token(canonical, group.state),
                source_files=files,
            )
            return ((("y", "x"), arr, attrs), info)
        # amplitude- or phase-only fallback (preserve as a real channel)
        only = group.amp or group.phase
        assert only is not None
        unit = "a.u." if group.amp is not None else "rad"
        arr = np.ascontiguousarray(_orient(only.data), dtype=np.float32)
        attrs = {
            "canonical": canonical,
            "kind": group.kind,
            "role": group.role,
            "harmonic": group.harmonic,
            "state": group.state,
            "value_unit": unit,
        }
        info = ChannelInfo(
            canonical=canonical,
            kind=group.kind,
            role=group.role,
            dtype="float32",
            state=group.state,
            harmonic=group.harmonic,
            value_unit=unit,
            source_files=files,
        )
        return ((("y", "x"), arr, attrs), info)

    # topography (real); convert length units to nm if the GSF declares a length
    assert group.value is not None
    zunits = group.value.zunits
    oriented = _orient(group.value.data)
    if zunits.strip():
        factor = length_scale_to_nm(zunits)
        arr = np.ascontiguousarray(oriented.astype(np.float64) * factor, dtype=np.float64)
        value_unit = "nm"
    else:
        arr = np.ascontiguousarray(oriented, dtype=np.float32)
        value_unit = "a.u."
    attrs = {
        "canonical": canonical,
        "kind": "topography",
        "role": group.role,
        "state": "raw",
        "value_unit": value_unit,
        "vendor_token": _topo_vendor_token(canonical, group.variant),
    }
    info = ChannelInfo(
        canonical=canonical,
        kind="topography",
        role=group.role,
        dtype=str(arr.dtype),
        state="raw",
        value_unit=value_unit,
        vendor_token=_topo_vendor_token(canonical, group.variant),
        source_files=files,
    )
    return ((("y", "x"), arr, attrs), info)


def _orient(data: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
    """Flip rows so the array is canonical lower-left / y-up (GSF is top-to-bottom)."""
    return np.ascontiguousarray(np.flipud(data))


def _vendor_token(canonical: str, state: str) -> str:
    base = canonical.replace("R_", "R-")
    return f"{base} {state}".strip()


def _topo_vendor_token(canonical: str, variant: str | None) -> str:
    base = canonical.split("_")[0].replace("R", "R-Z") if canonical.startswith("R_") else "Z"
    return f"{base} {variant}".strip() if variant else base


# --------------------------------------------------------------------------- #
# Parameter (.txt) file parsing
# --------------------------------------------------------------------------- #


def _find_param_file(root: Path) -> Path:
    txts = sorted(root.glob("*.txt"))
    if not txts:
        raise ReaderError(f"no .txt parameter file in {root}")
    for t in txts:
        if t.stem == root.name:
            return t
    return txts[0]


def _parse_param_file(path: Path) -> dict[str, Any]:
    """Parse the neaSNOM ``.txt`` into verbatim lines + ordered records."""
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    records: list[dict[str, Any]] = []
    for line in raw_lines:
        if not line.startswith("#"):
            continue
        content = line[1:].strip()
        if not content:
            continue
        parts = [p.strip() for p in content.split("\t")]
        label = parts[0].rstrip(":").strip()
        unit: str | None = None
        values: list[str] = []
        for tok in parts[1:]:
            if not tok:
                continue
            if unit is None and not values and tok.startswith("[") and tok.endswith("]"):
                unit = tok[1:-1]
            else:
                values.append(tok)
        records.append({"label": label, "unit": unit, "values": values})
    return {"lines": raw_lines, "records": records}


def _txt_index(txt: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {r["label"]: r for r in txt["records"]}


def _num(rec: dict[str, Any] | None, i: int = 0) -> float | None:
    if rec is None:
        return None
    values = rec["values"]
    if i >= len(values):
        return None
    try:
        return float(values[i].replace(",", ""))
    except ValueError:
        return None


def _str(rec: dict[str, Any] | None, i: int = 0) -> str | None:
    if rec is None or i >= len(rec["values"]):
        return None
    return str(rec["values"][i])


# --------------------------------------------------------------------------- #
# Metadata assembly
# --------------------------------------------------------------------------- #


def _build_metadata(
    *,
    grid: _Grid,
    txt: dict[str, Any],
    sample_header: dict[str, str],
    channels: tuple[ChannelInfo, ...],
    harmonics: tuple[int, ...],
) -> Metadata:
    idx = _txt_index(txt)
    factor = length_scale_to_nm(grid.xyunits)

    # excitation: the "Target Wavelength" field is actually a wavenumber (cm^-1).
    target = idx.get("Target Wavelength")
    wavenumber = _num(target) if target and _is_wavenumber(target.get("unit")) else None

    center = idx.get("Scanner Center Position (X, Y)")
    center_nm = _pair_to_nm(center, factor_from_unit=center.get("unit") if center else None)
    rotation = _num(idx.get("Rotation"))

    is_neaspec = any(r["label"].startswith("www.neaspec") for r in txt["records"])
    instrument = Instrument(
        vendor="neaspec" if is_neaspec else None,
        model=None,
        software_version=_str(idx.get("Version")),
    )
    excitation = Excitation(
        source_type=_str(idx.get("Laser Source")),
        detector=_str(idx.get("Detector")),
        wavenumber_cm1=wavenumber,
    )
    demodulation = Demodulation(
        detection=_str(idx.get("Demodulation Mode")),
        harmonics=harmonics,
    )
    scan = ScanInfo(
        pixels=(grid.xres, grid.yres),
        size_nm=(grid.xreal * factor, grid.yreal * factor),
        center_nm=center_nm,
        offset_nm=(grid.xoffset * factor, grid.yoffset * factor),
        pixel_size_nm=(grid.xreal * factor / grid.xres, grid.yreal * factor / grid.yres),
        rotation_deg=rotation,
    )
    integ_ms = _num(idx.get("Integration time"))
    acquisition = Acquisition(
        datetime=_parse_date(_str(idx.get("Date"))),
        integration_time_s=None if integ_ms is None else integ_ms / 1000.0,
        tapping_amplitude_nm=_num(idx.get("Tapping Amplitude")),
        setpoint=_num(idx.get("Setpoint")),
        averaging=_int(_num(idx.get("Averaging"))),
    )

    original_units = {
        "x": grid.xyunits,
        "y": grid.xyunits,
        "wavenumber": "cm-1",
    }
    for ch in channels:
        if ch.kind == "topography" and ch.value_unit == "nm":
            original_units[ch.canonical] = sample_header.get("ZUnits", "m") or "m"

    raw_header = {
        "parameter_file": txt,
        "gsf_header_sample": dict(sample_header),
    }

    return Metadata(
        data_kind=DataKind.IMAGE,
        conventions=Conventions(),
        instrument=instrument,
        excitation=excitation,
        demodulation=demodulation,
        scan=scan,
        acquisition=acquisition,
        channels=channels,
        original_units=original_units,
        raw_header=raw_header,
    )


def _is_wavenumber(unit: str | None) -> bool:
    if not unit:
        return False
    u = unit.lower()
    return "cm" in u and ("-1" in u or "⁻¹" in u or "¹" in u)


def _pair_to_nm(
    rec: dict[str, Any] | None, *, factor_from_unit: str | None
) -> tuple[float, float] | None:
    if rec is None:
        return None
    a, b = _num(rec, 0), _num(rec, 1)
    if a is None or b is None:
        return None
    factor = length_scale_to_nm(factor_from_unit) if factor_from_unit else 1.0
    return (a * factor, b * factor)


def _parse_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%m/%d/%Y %H:%M:%S").isoformat()
    except ValueError:
        return None


def _int(value: float | None) -> int | None:
    return None if value is None else int(value)


__all__ = ["READER_ID", "read_neasnom_measurement"]
