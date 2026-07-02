"""neaSNOM point-spectroscopy reader: a ``Spectra.txt`` table -> ``Dataset``.

A neaSNOM "Point Spectroscopy" acquisition sweeps a tunable laser ("Piano")
across a wavenumber range at one or more spatial positions, recording amplitude
+ phase of every optical harmonic (and the AFM height ``Z``) at each
(position, wavenumber) sample. The vendor writes this as a single tab-delimited
``<measurement> Spectra.txt`` file: the same ``#``-prefixed header grammar as the
imaging ``.txt`` (see :mod:`snomniman.io._neasnom_header`), followed by a data
table with one row per (position, spectral sample):

``Row  Column  Omega  Wavenumber  Z  O0A  O0P  O1A  O1P  ...``

Validated against a real measurement (see ``docs/point-spectrum-discovery.md``):
``Column`` indexes distinct spatial positions along a real line (its count and
physical length come straight from the header - "Pixel Area (X, Y, Z)" and
"Scan Area (X, Y, Z)" - no dependency on the companion per-position GSF channel
maps the vendor also writes alongside this file, which this reader does not
ingest); ``Omega`` sweeps the wavenumber axis, identically at every position.

This reader produces :class:`~snomniman.core.DataKind.SPECTRUM` (dims
``(wavenumber,)``) when there is exactly one position, or
:class:`~snomniman.core.DataKind.LINE_SCAN` (dims ``(s, wavenumber)``) when there
are several - both pre-existing ``DataKind``/``Capability`` members
(``docs/data-model.md`` sec 2); no core changes were needed for this modality.
"""

from __future__ import annotations

import re
from collections import defaultdict
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
    SpectralInfo,
    StepRecord,
    current_software,
    length_scale_to_nm,
)
from snomniman.core.exceptions import ReaderError

from ._neasnom_header import (
    is_wavenumber_unit,
    num,
    parse_date,
    parse_param_file,
    str_value,
    txt_index,
)

#: Reader id (format + version), used in ``RawSource`` and the registry.
READER_ID = "neasnom.spectrum.txt.v1"

#: Optical channel column token, e.g. "O2A", "O2P" (no reference channels
#: have been observed in a point-spectroscopy export; if the vendor ever
#: emits "R_O2A" this pattern deliberately does not match it, so it is
#: reported honestly via ``_UNRECOGNIZED`` rather than silently mis-tagged).
_OM_COL_RE = re.compile(r"^O(?P<order>\d+)(?P<comp>[AP])$")

_REQUIRED_COLUMNS = ("Row", "Column", "Omega", "Wavenumber", "Z")


def read_neasnom_spectrum_measurement(path: str | Path) -> Dataset:
    """Read a neaSNOM point-spectroscopy ``Spectra.txt`` measurement into a ``Dataset``."""
    root = Path(path)
    if not root.is_dir():
        raise ReaderError(f"not a measurement directory: {root}")

    spectra_path = _find_spectra_file(root)
    txt = parse_param_file(spectra_path)
    idx = txt_index(txt)

    header_cells, data_rows = _read_table(spectra_path)
    col_idx = _column_index(header_cells, spectra_path)
    table = _group_by_position(data_rows, col_idx, spectra_path)

    positions = sorted(table)
    wavenumbers = np.array(
        [float(_cell(cells, col_idx, "Wavenumber")) for _, cells in table[positions[0]]],
        dtype=np.float64,
    )
    n_spec = wavenumbers.size
    _validate_positions(table, positions, wavenumbers, col_idx, spectra_path)
    _cross_validate_pixel_area(idx, len(positions), n_spec, spectra_path)

    optical_orders = sorted(
        {int(m.group("order")) for name in col_idx if (m := _OM_COL_RE.match(name))}
    )
    data_vars, channel_infos = _assemble_channels(
        table, positions, col_idx, optical_orders, len(positions), n_spec
    )

    coords: dict[str, Any] = {
        "wavenumber": (
            "wavenumber",
            wavenumbers,
            {"unit": "cm-1", "long_name": "wavenumber", "axis": "wavenumber"},
        )
    }
    dims: tuple[str, ...]
    length_nm: float | None = None
    if len(positions) > 1:
        dims = ("s", "wavenumber")
        length_nm = _line_length_nm(idx)
        pixel_size_nm = length_nm / len(positions) if length_nm is not None else 1.0
        s_values = (np.arange(len(positions), dtype=np.float64) + 0.5) * pixel_size_nm
        coords["s"] = ("s", s_values, {"unit": "nm", "long_name": "scan distance", "axis": "s"})
    else:
        dims = ("wavenumber",)
        for name, (_var_dims, arr, attrs) in data_vars.items():
            data_vars[name] = (dims, np.asarray(arr).reshape(-1), attrs)

    xr_ds = xr.Dataset(data_vars=data_vars, coords=coords)

    metadata = _build_metadata(
        idx=idx,
        txt=txt,
        n_positions=len(positions),
        length_nm=length_nm,
        wavenumbers=wavenumbers,
        channels=tuple(sorted(channel_infos, key=lambda c: c.canonical)),
        harmonics=tuple(optical_orders),
    )

    source = RawSource.from_directory(
        root,
        reader=READER_ID,
        files=[spectra_path],
        reader_params={"channel_map": "default"},
    )
    record = StepRecord(
        step_id="io.read",
        step_version=1,
        deterministic=True,
        params={
            "reader": READER_ID,
            "wavenumber_unit": "cm-1",
            "length_unit_conversion": "um->nm" if length_nm is not None else "n/a",
        },
        software=current_software(),
        input_fingerprint=f"sha256:{source.sha256}",
        notes=f"neaSNOM point-spectroscopy measurement '{root.name}'",
    )
    node = ProvenanceNode(node_id="n0", record=record, sources={"source": source})

    kind = DataKind.LINE_SCAN if len(positions) > 1 else DataKind.SPECTRUM
    return Dataset(xr_ds, kind=kind, metadata=metadata, provenance=node, source=source)


# --------------------------------------------------------------------------- #
# File discovery + table parsing
# --------------------------------------------------------------------------- #


def _find_spectra_file(root: Path) -> Path:
    candidates = sorted(root.glob("*Spectra.txt"))
    if not candidates:
        raise ReaderError(f"no *Spectra.txt point-spectroscopy file in {root}")
    return candidates[0]


def _read_table(path: Path) -> tuple[list[str], list[list[str]]]:
    """Split the file into the tab-delimited column header + data rows.

    Header (``#``) lines are parsed separately by :func:`parse_param_file`; this
    reads the same file again for the (much larger) tabular body, so the two
    parses stay independent and each stays simple.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    body = [ln for ln in lines if not ln.lstrip().startswith("#") and ln.strip()]
    if not body:
        raise ReaderError(f"no data table found in {path}")
    header_cells = [c.strip() for c in body[0].split("\t")]
    data_rows = [ln.split("\t") for ln in body[1:]]
    return header_cells, data_rows


def _column_index(header_cells: list[str], path: Path) -> dict[str, int]:
    col_idx = {name: i for i, name in enumerate(header_cells) if name}
    missing = [c for c in _REQUIRED_COLUMNS if c not in col_idx]
    if missing:
        raise ReaderError(f"Spectra.txt missing required column(s) {missing} in {path}")
    return col_idx


def _cell(cells: list[str], col_idx: dict[str, int], name: str) -> str:
    i = col_idx[name]
    return cells[i].strip() if i < len(cells) else ""


def _group_by_position(
    data_rows: list[list[str]], col_idx: dict[str, int], path: Path
) -> dict[int, list[tuple[int, list[str]]]]:
    table: dict[int, list[tuple[int, list[str]]]] = defaultdict(list)
    for cells in data_rows:
        try:
            col = int(_cell(cells, col_idx, "Column"))
            omega = int(_cell(cells, col_idx, "Omega"))
        except ValueError as exc:
            raise ReaderError(f"non-integer Column/Omega in data row of {path}") from exc
        table[col].append((omega, cells))
    for col in table:
        table[col].sort(key=lambda t: t[0])
    return table


def _validate_positions(
    table: dict[int, list[tuple[int, list[str]]]],
    positions: list[int],
    wavenumbers_ref: npt.NDArray[np.float64],
    col_idx: dict[str, int],
    path: Path,
) -> None:
    """Every position must sweep the identical wavenumber vector (Rule 6)."""
    for col in positions[1:]:
        rows = table[col]
        if len(rows) != wavenumbers_ref.size:
            raise ReaderError(
                f"position {col} has {len(rows)} spectral samples, "
                f"expected {wavenumbers_ref.size} (position {positions[0]}), in {path}"
            )
        wn = np.array(
            [float(_cell(cells, col_idx, "Wavenumber")) for _, cells in rows], dtype=np.float64
        )
        if not np.allclose(wn, wavenumbers_ref):
            raise ReaderError(f"inconsistent wavenumber sweep across positions in {path}")


def _cross_validate_pixel_area(
    idx: dict[str, dict[str, Any]], n_positions: int, n_spec: int, path: Path
) -> None:
    """Cross-check the parsed table shape against the header's own "Pixel Area"."""
    rec = idx.get("Pixel Area (X, Y, Z)")
    if rec is None:
        return
    hdr_x, hdr_z = num(rec, 0), num(rec, 2)
    if hdr_x is not None and int(hdr_x) != n_positions:
        raise ReaderError(
            f"header Pixel Area X={hdr_x!r} does not match "
            f"{n_positions} parsed positions in {path}"
        )
    if hdr_z is not None and int(hdr_z) != n_spec:
        raise ReaderError(
            f"header Pixel Area Z={hdr_z!r} does not match {n_spec} parsed spectral samples "
            f"in {path}"
        )


def _line_length_nm(idx: dict[str, dict[str, Any]]) -> float | None:
    """Physical length of the scan line, in nm, from the header "Scan Area"."""
    rec = idx.get("Scan Area (X, Y, Z)")
    if rec is None:
        return None
    x, y = num(rec, 0), num(rec, 1)
    if x is None or y is None:
        return None
    factor = length_scale_to_nm(rec.get("unit") or "um")
    return max(abs(x), abs(y)) * factor


# --------------------------------------------------------------------------- #
# Channel assembly
# --------------------------------------------------------------------------- #


def _assemble_channels(
    table: dict[int, list[tuple[int, list[str]]]],
    positions: list[int],
    col_idx: dict[str, int],
    optical_orders: list[int],
    n_positions: int,
    n_spec: int,
) -> tuple[dict[str, tuple[tuple[str, ...], npt.NDArray[Any], dict[str, Any]]], list[ChannelInfo]]:
    data_vars: dict[str, tuple[tuple[str, ...], npt.NDArray[Any], dict[str, Any]]] = {}
    channel_infos: list[ChannelInfo] = []
    dims = ("s", "wavenumber")

    for order in optical_orders:
        amp_col, phase_col = f"O{order}A", f"O{order}P"
        if amp_col not in col_idx or phase_col not in col_idx:
            continue  # amplitude-only/phase-only columns are not expected; skip honestly
        amp = _extract_grid(table, positions, col_idx, amp_col, n_positions, n_spec)
        phase = _extract_grid(table, positions, col_idx, phase_col, n_positions, n_spec)
        canonical = f"O{order}"
        arr = (amp * np.exp(1j * phase)).astype(np.complex64)
        attrs = {
            "canonical": canonical,
            "kind": "optical",
            "role": "signal",
            "harmonic": order,
            "state": "raw",
            "amplitude_unit": "a.u.",
            "phase_unit": "rad",
            "vendor_token": f"{amp_col}/{phase_col}",
        }
        data_vars[canonical] = (dims, arr, attrs)
        channel_infos.append(
            ChannelInfo(
                canonical=canonical,
                kind="optical",
                role="signal",
                dtype="complex64",
                state="raw",
                harmonic=order,
                amplitude_unit="a.u.",
                phase_unit="rad",
                vendor_token=f"{amp_col}/{phase_col}",
                source_files=(),
            )
        )

    if "Z" in col_idx:
        z_raw = _extract_grid(table, positions, col_idx, "Z", n_positions, n_spec)
        z_nm = (z_raw * length_scale_to_nm("m")).astype(np.float64)
        attrs = {
            "canonical": "Z",
            "kind": "topography",
            "role": "signal",
            "state": "raw",
            "value_unit": "nm",
            "vendor_token": "Z",
        }
        data_vars["Z"] = (dims, z_nm, attrs)
        channel_infos.append(
            ChannelInfo(
                canonical="Z",
                kind="topography",
                role="signal",
                dtype="float64",
                state="raw",
                value_unit="nm",
                vendor_token="Z",
                source_files=(),
            )
        )

    return data_vars, channel_infos


def _extract_grid(
    table: dict[int, list[tuple[int, list[str]]]],
    positions: list[int],
    col_idx: dict[str, int],
    column: str,
    n_positions: int,
    n_spec: int,
) -> npt.NDArray[np.float64]:
    out = np.empty((n_positions, n_spec), dtype=np.float64)
    for i, col in enumerate(positions):
        rows = table[col]
        out[i, :] = [float(_cell(cells, col_idx, column)) for _, cells in rows]
    return out


# --------------------------------------------------------------------------- #
# Metadata assembly
# --------------------------------------------------------------------------- #


def _build_metadata(
    *,
    idx: dict[str, dict[str, Any]],
    txt: dict[str, Any],
    n_positions: int,
    length_nm: float | None,
    wavenumbers: npt.NDArray[np.float64],
    channels: tuple[ChannelInfo, ...],
    harmonics: tuple[int, ...],
) -> Metadata:
    target = idx.get("Target Wavelength")
    wavenumber = num(target) if target and is_wavenumber_unit(target.get("unit")) else None

    is_neaspec = any(r["label"] == "www.neaspec.com" for r in txt["records"])
    instrument = Instrument(
        vendor="neaspec" if is_neaspec else None,
        model=None,
        software_version=str_value(idx.get("Version")),
    )
    excitation = Excitation(
        source_type=str_value(idx.get("Laser Source")),
        detector=str_value(idx.get("Detector")),
        wavenumber_cm1=wavenumber,
    )
    demodulation = Demodulation(
        detection=str_value(idx.get("Demodulation Mode")),
        harmonics=harmonics,
    )
    scan = ScanInfo()
    if n_positions > 1 and length_nm is not None:
        scan = ScanInfo(
            pixels=(n_positions, 1),
            size_nm=(length_nm, 0.0),
            pixel_size_nm=(length_nm / n_positions, 0.0),
        )
    diffs = np.diff(wavenumbers)
    spectral = SpectralInfo(
        wavenumber_min_cm1=float(np.min(wavenumbers)),
        wavenumber_max_cm1=float(np.max(wavenumbers)),
        n_points=int(wavenumbers.size),
        sampling_cm1=float(np.mean(diffs)) if diffs.size else None,
    )
    integ_ms = num(idx.get("Integration time"))
    acquisition = Acquisition(
        datetime=parse_date(str_value(idx.get("Date"))),
        integration_time_s=None if integ_ms is None else integ_ms / 1000.0,
        tapping_amplitude_nm=num(idx.get("Tapping Amplitude")),
        setpoint=num(idx.get("Setpoint")),
        averaging=_int(num(idx.get("Averaging"))),
    )

    original_units = {"wavenumber": "cm-1", "Z": "m"}
    scan_area = idx.get("Scan Area (X, Y, Z)")
    if n_positions > 1 and scan_area is not None and scan_area.get("unit"):
        original_units["s"] = str(scan_area["unit"])

    raw_header = {"parameter_file": txt}

    return Metadata(
        data_kind=DataKind.LINE_SCAN if n_positions > 1 else DataKind.SPECTRUM,
        conventions=Conventions(),
        instrument=instrument,
        excitation=excitation,
        demodulation=demodulation,
        scan=scan,
        spectral=spectral,
        acquisition=acquisition,
        channels=channels,
        original_units=original_units,
        raw_header=raw_header,
    )


def _int(value: float | None) -> int | None:
    return None if value is None else int(value)


__all__ = ["READER_ID", "read_neasnom_spectrum_measurement"]
