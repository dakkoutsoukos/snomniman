"""Export a single :class:`Dataset` channel to a Gwyddion Simple Field (GSF) file.

This is the interchange counterpart of the canonical Zarr store. The Zarr store
(``write_zarr``) is the loss-less project format - it round-trips the whole dataset
with full provenance. GSF, by contrast, holds **one real-valued grid**, so a SNOM
channel is exported one representation at a time: a complex optical/mechanical
channel as its **amplitude**, **phase**, or real part; a topography channel as its
height. This is what lets a result leave SNOMNIMAN for Gwyddion, neaPLOT, or any
GSF-aware tool.

Two fidelity notes, recorded honestly rather than hidden:

* GSF stores **float32**, so values are narrowed to single precision on export
  (the Zarr store is the loss-less path).
* GSF rows run top-to-bottom; SNOMNIMAN's canonical orientation is lower-left /
  y-up, so the grid is flipped vertically on the way out - the exact inverse of the
  reader's import flip.

Because a single GSF file cannot carry a provenance DAG, every export also writes a
``<file>.provenance.json`` sidecar (mirroring the publication-figure export): it
embeds the full serialized provenance, the source anchor, and the conventions, so
the exported grid is never an orphan.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from snomniman.core import Dataset, current_software, serialize_dag
from snomniman.core.exceptions import DatasetError

from .gsf import write_gsf

#: Channel representations a GSF export accepts (these match the ``viz`` constants).
AMPLITUDE = "amplitude"
PHASE = "phase"
REAL = "real"

#: Marks the provenance sidecar written next to an exported GSF grid.
GSF_EXPORT_FORMAT = "snomniman.gsf_export"
GSF_EXPORT_SCHEMA_VERSION = 1


def export_channel_gsf(
    dataset: Dataset,
    channel: str,
    path: str | Path,
    *,
    representation: str | None = None,
) -> tuple[Path, Path]:
    """Export one ``channel`` of ``dataset`` to a GSF file at ``path``.

    For a complex channel, ``representation`` selects ``"amplitude"`` (default),
    ``"phase"``, or ``"real"``; for a real channel it must be ``None`` or
    ``"real"``. Returns ``(gsf_path, provenance_path)``: the grid and its provenance
    sidecar. Raises :class:`~snomniman.core.DatasetError` for an unknown channel or
    an invalid representation.
    """
    values, representation, unit = _channel_grid(dataset, channel, representation)

    # Canonical lower-left / y-up -> GSF top-to-bottom (inverse of the reader flip).
    grid = np.ascontiguousarray(np.flipud(values), dtype=np.float32)
    header = _gsf_header(dataset, channel, representation, unit)

    gsf_path = Path(path)
    write_gsf(gsf_path, grid, header)

    provenance_path = gsf_path.with_suffix(gsf_path.suffix + ".provenance.json")
    record = _provenance_record(dataset, channel, representation, unit, header)
    provenance_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return gsf_path, provenance_path


def _channel_grid(
    dataset: Dataset, channel: str, representation: str | None
) -> tuple[npt.NDArray[np.float64], str, str]:
    """Resolve ``channel`` + ``representation`` to a real 2-D grid, its name, and unit."""
    array = np.asarray(dataset.channel(channel).values)
    if np.iscomplexobj(array):
        rep = representation or AMPLITUDE
        if rep == AMPLITUDE:
            return np.abs(array).astype(np.float64), rep, "a.u."
        if rep == PHASE:
            return np.angle(array).astype(np.float64), rep, "rad"
        if rep == REAL:
            return array.real.astype(np.float64), rep, "a.u."
        raise DatasetError(
            f"invalid representation {representation!r} for complex channel "
            f"{channel!r}; choose {AMPLITUDE!r}, {PHASE!r}, or {REAL!r}"
        )
    if representation not in (None, REAL):
        raise DatasetError(
            f"channel {channel!r} is real; only the {REAL!r} representation applies "
            f"(got {representation!r})"
        )
    return array.astype(np.float64), REAL, _real_channel_unit(dataset, channel)


def _real_channel_unit(dataset: Dataset, channel: str) -> str:
    """The physical unit of a real channel, from its typed metadata (else a.u.)."""
    try:
        info = dataset.metadata.channel(channel)
    except (KeyError, AttributeError):  # pragma: no cover - defensive
        return "a.u."
    return info.value_unit or "a.u."


def _gsf_header(dataset: Dataset, channel: str, representation: str, unit: str) -> dict[str, str]:
    """Build the GSF text header from the dataset's canonical coordinates (nm)."""
    x = np.asarray(dataset.coordinate("x").values, dtype=np.float64)
    y = np.asarray(dataset.coordinate("y").values, dtype=np.float64)
    nx, ny = int(x.size), int(y.size)
    dx = float(x[1] - x[0]) if nx > 1 else 1.0
    dy = float(y[1] - y[0]) if ny > 1 else 1.0
    return {
        "XRes": str(nx),
        "YRes": str(ny),
        "XReal": f"{dx * nx:.10g}",
        "YReal": f"{dy * ny:.10g}",
        "XOffset": f"{float(x[0]) - dx / 2.0:.10g}",
        "YOffset": f"{float(y[0]) - dy / 2.0:.10g}",
        "XYUnits": "nm",  # SNOMNIMAN's canonical spatial unit (OHD-6B)
        "ZUnits": _gsf_z_unit(unit),
        "Title": f"{channel} {representation}",
    }


def _gsf_z_unit(unit: str) -> str:
    """Map a SNOMNIMAN value unit to a GSF ZUnits string (a.u. -> empty)."""
    return "" if unit in ("a.u.", "") else unit


def _provenance_record(
    dataset: Dataset, channel: str, representation: str, unit: str, header: dict[str, str]
) -> dict[str, Any]:
    """The machine-readable + human-readable provenance sidecar for an export."""
    source = dataset.source
    conventions = dataset.metadata.conventions
    return {
        "format": GSF_EXPORT_FORMAT,
        "schema_version": GSF_EXPORT_SCHEMA_VERSION,
        "channel": channel,
        "representation": representation,
        "unit": unit,
        "source_path": source.path if source is not None else None,
        "source_sha256": source.sha256 if source is not None else None,
        "conventions": {
            "spatial_unit": conventions.spatial_unit,
            "origin": conventions.origin,
            "x_dir": conventions.x_dir,
            "y_dir": conventions.y_dir,
            "phase_unit": conventions.phase_unit,
            "phase": "as imported",
        },
        "gsf_header": dict(header),
        "provenance": serialize_dag(dataset.provenance),
        "software": current_software(),
        "created_at": datetime.now(UTC).isoformat(),
        "caption": (
            f"GSF export of channel {channel} ({representation}, {unit}) from a "
            f"{'raw' if dataset.is_raw else 'derived'} SNOMNIMAN measurement"
            + (
                f"; source sha256 {source.sha256[:12]}..."
                if source is not None
                else ""
            )
        ),
    }


__all__ = [
    "AMPLITUDE",
    "GSF_EXPORT_FORMAT",
    "GSF_EXPORT_SCHEMA_VERSION",
    "PHASE",
    "REAL",
    "export_channel_gsf",
]
