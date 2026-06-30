"""Serialize measurement results to CSV (Qt-free presenter logic).

A line profile or a region's statistics is a *quantitative result* the researcher
needs to take into Excel, Origin, MATLAB, or Python. This module turns the
already-computed result value objects (:class:`~snomniman.gui.model.ProfileSet`,
:class:`~snomniman.gui.model.RegionReport` - whose numbers come from the validated
``snomniman.viz.measure`` backend) into well-formed CSV text: a commented
provenance header so the export is never an orphan, then a clean table with
explicit column headers and physical units.

It is deliberately free of any GUI toolkit (like ``model.py``) so the formatting is
unit-tested headlessly; the widget layer only chooses a delimiter (``,`` for a file,
a tab for clipboard paste) and moves the text to a file or the clipboard.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid an import cycle: model imports ExportContext from here
    from .experiment import ExperimentTable
    from .model import ProfileSet, RegionReport


@dataclass(frozen=True)
class ExportContext:
    """Provenance/identity facts shared by every measurement export (header lines)."""

    measurement: str
    source_path: str | None
    source_sha256: str | None
    conventions: str
    provenance: tuple[str, ...]  # step ids, oldest first
    snomniman_version: str
    created_at: str


@dataclass(frozen=True)
class ExperimentExportContext:
    """Project-level identity facts for an experiment-comparison export (header lines)."""

    project: str
    measurement_count: int
    conventions: str
    snomniman_version: str
    created_at: str


def profile_to_csv(profile: ProfileSet, context: ExportContext, *, delimiter: str = ",") -> str:
    """Render a line profile as CSV: a provenance header then distance + per-channel columns."""
    buffer = StringIO()
    geometry = (
        f"length {profile.distance_nm:.4g} nm; dx {profile.dx_nm:.4g} nm; "
        f"dy {profile.dy_nm:.4g} nm"
    )
    _write_header(buffer, "line profile", context, extra=[("Geometry", geometry)])

    writer = csv.writer(buffer, delimiter=delimiter, lineterminator="\n")
    writer.writerow(["distance_nm", *(f"{c.label} [{c.unit}]" for c in profile.curves)])
    for i, distance in enumerate(profile.positions_nm):
        writer.writerow([_fmt(distance), *(_fmt(c.samples[i]) for c in profile.curves)])
    return buffer.getvalue()


def region_to_csv(report: RegionReport, context: ExportContext, *, delimiter: str = ",") -> str:
    """Render region statistics as CSV: a provenance header then one row per channel."""
    buffer = StringIO()
    region = f"{report.count} pixels; area {report.area_nm2:.6g} nm^2"
    _write_header(buffer, f"{report.kind} region statistics", context, extra=[("Region", region)])

    writer = csv.writer(buffer, delimiter=delimiter, lineterminator="\n")
    writer.writerow(["channel", "unit", "mean", "median", "min", "max", "std", "count", "area_nm2"])
    for row in report.rows:
        s = row.stats
        writer.writerow([
            row.label, row.unit,
            _fmt(s.mean), _fmt(s.median), _fmt(s.minimum), _fmt(s.maximum), _fmt(s.std),
            str(s.count), _fmt(s.area_nm2),
        ])
    return buffer.getvalue()


def experiment_table_to_csv(
    table: ExperimentTable, context: ExperimentExportContext, *, delimiter: str = ","
) -> str:
    """Render an experiment comparison table as CSV: header, then one row per measurement.

    Rows are measurements and columns are the compared quantities (diagnostics or
    cross-measurement statistics). Numeric cells are written at full precision (from
    the cell's sort value), not the rounded display text, so the export is faithful.
    """
    buffer = StringIO()
    lines: list[tuple[str, str]] = [
        ("", f"SNOMNIMAN experiment export - {table.title}"),
        ("Project", context.project),
        ("Measurements", str(context.measurement_count)),
        ("Conventions", context.conventions),
        ("", f"SNOMNIMAN {context.snomniman_version}; exported {context.created_at}"),
    ]
    for label, value in lines:
        buffer.write(f"# {label}: {value}\n" if label else f"# {value}\n")

    writer = csv.writer(buffer, delimiter=delimiter, lineterminator="\n")
    header = ["measurement"]
    header.extend(f"{c.label} [{c.unit}]" if c.unit else c.label for c in table.columns)
    writer.writerow(header)
    for row in table.rows:
        # The cell text is the value as shown in the table (csv quotes any commas,
        # e.g. a "O2, O3" harmonics cell); the numeric sort key is GUI-only.
        writer.writerow([row.title, *(cell.text for cell in row.cells)])
    return buffer.getvalue()


def _write_header(
    buffer: StringIO, what: str, context: ExportContext, *, extra: list[tuple[str, str]]
) -> None:
    """Write the commented provenance header lines shared by every export."""
    lines: list[tuple[str, str]] = [("", f"SNOMNIMAN {what} export"),
                                    ("Measurement", context.measurement)]
    if context.source_path is not None:
        sha = f" (sha256 {context.source_sha256[:12]}...)" if context.source_sha256 else ""
        lines.append(("Source", f"{context.source_path}{sha}"))
    lines.extend(extra)
    lines.append(("Conventions", context.conventions))
    if context.provenance:
        lines.append(("Provenance", " -> ".join(context.provenance)))
    lines.append(("", f"SNOMNIMAN {context.snomniman_version}; exported {context.created_at}"))
    for label, value in lines:
        buffer.write(f"# {label}: {value}\n" if label else f"# {value}\n")


def _fmt(value: float) -> str:
    """Format a number for CSV: ``.10g`` precision, empty for non-finite (NaN/inf)."""
    v = float(value)
    if v != v or v in (float("inf"), float("-inf")):  # NaN or +/-inf -> blank cell
        return ""
    return format(v, ".10g")


__all__ = [
    "ExperimentExportContext",
    "ExportContext",
    "experiment_table_to_csv",
    "profile_to_csv",
    "region_to_csv",
]
