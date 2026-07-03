"""Scientific reporting (Phase 4C): deterministic experiment/publication/
reproducibility reports, assembled entirely from already-computed, already-
validated facts.

``ReportModel`` is a thin, read-only aggregator - the reporting analogue of
:class:`~snomniman.gui.experiment.ExperimentModel` - and lives here for the same
reason: its only present consumer is the Explorer window, so it is a presenter
inside ``gui`` (Qt-free, unit-testable without a display), not a new backend
package (Rule 7: no new subsystem without a concrete, present consumer). It
composes, and never (re)computes: project/measurement facts come from
``describe``/``ExplorerModel``; diagnostics from ``ExperimentModel.diagnostics_table``;
processing history and the machine-readable appendix from the provenance DAG
(``ExplorerModel.provenance_steps`` / ``core.serialize_dag`` - never a second
representation); recipe identity from ``pipeline.matching_recipe_name``; batch
outcomes from an already-run :class:`~snomniman.batch.BatchResult`; region/profile/
histogram numbers from the validated ``viz.measure`` methods each ``ExplorerModel``
already exposes. A report is data (:class:`Report`/:class:`ReportSection`, both
frozen and JSON-adjacent); :func:`render_markdown`/:func:`render_html` are pure
formatters over that one shared structure - two presentations, not two data models.

PDF export is deliberately not implemented: a laid-out multi-page PDF document
(text + tables + images, not just one figure) would need a new, heavy dependency
(e.g. weasyprint/reportlab) with no present justification (Rule 7; CLAUDE.md
"never introduce a major dependency without an ADR"). Markdown/HTML already cover
lab records, collaborator sharing, and supplementary material; an individual
publication figure is already exportable as vector PDF via the existing
``viz.figure`` pipeline (unchanged by this module) - a report simply lists any such
already-exported figures by filename, it does not re-render them.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from snomniman.batch import BatchResult
from snomniman.core import current_software, serialize_dag
from snomniman.core.exceptions import ProcessingError
from snomniman.pipeline import Recipe, matching_recipe_name

from .experiment import (
    ExperimentCell,
    ExperimentColumn,
    ExperimentModel,
    ExperimentTable,
    ExperimentTableRow,
)
from .model import DiagnosticRow, ExplorerModel, MeasurementSession, PaneSpec

#: The two supported export formats (see the module docstring for why not PDF).
REPORT_FORMAT_MARKDOWN = "markdown"
REPORT_FORMAT_HTML = "html"


@dataclass(frozen=True)
class ReportSection:
    """One titled unit of a report: prose lines, label/value facts, a table, or code.

    Exactly the shapes the Explorer already renders elsewhere (``DiagnosticRow``,
    ``ExperimentTable``) plus plain text - a section picks whichever field(s) it
    needs; the renderers handle any combination.
    """

    title: str
    lines: tuple[str, ...] = ()
    facts: tuple[DiagnosticRow, ...] = ()
    table: ExperimentTable | None = None
    code: str | None = None
    code_language: str = "json"


@dataclass(frozen=True)
class Report:
    """A complete, deterministic report: a title, a generation stamp, and sections."""

    title: str
    generated_at: str
    software: Mapping[str, str]
    sections: tuple[ReportSection, ...] = field(default_factory=tuple)


class ReportModel:
    """Composes the three Phase 4C reports from a project's live sessions.

    Takes exactly what the window already holds - the sessions
    (:class:`~snomniman.gui.model.MeasurementSession`, the same list
    :class:`~snomniman.gui.experiment.ExperimentModel` is built from), the recipe
    library, any batch runs performed this session, any figures exported this
    session, and the last cross-measurement overlay comparison - and reads all of
    it; it computes nothing new and mutates nothing.
    """

    def __init__(
        self,
        sessions: Sequence[MeasurementSession],
        project_title: str,
        *,
        recipes: Mapping[str, Recipe] | None = None,
        batch_runs: Sequence[tuple[Recipe, BatchResult]] = (),
        exported_figures: Sequence[tuple[Path, Path]] = (),
        experiment_stats: ExperimentTable | None = None,
    ) -> None:
        self._sessions = list(sessions)
        self._project_title = project_title
        self._recipes = dict(recipes) if recipes else {}
        self._batch_runs = list(batch_runs)
        self._exported_figures = list(exported_figures)
        self._experiment_stats = experiment_stats
        self._experiment = ExperimentModel(self._sessions)

    # -- Part 1: Experiment Report --------------------------------------------

    def experiment_report(self) -> Report:
        """Project info, measurement/diagnostics summaries, processing, batch, ROI/profile."""
        sections: list[ReportSection | None] = [
            self._project_section(),
            self._measurements_section(),
            self._diagnostics_section(),
            self._processing_history_section(),
            self._applied_recipes_section(),
            *self._batch_sections(),
            self._generated_datasets_section(),
            *self._overlay_sections(),
        ]
        return self._report(f"Experiment Report - {self._project_title}", sections)

    # -- Part 2: Publication Package -------------------------------------------

    def publication_package(self) -> Report:
        """A curated subset for assembling a paper/SI: metadata, tables, figures."""
        sections: list[ReportSection | None] = [
            self._project_section(),
            self._measurements_section(),
            self._metadata_section(),
            self._processing_history_section(),
            self._applied_recipes_section(),
            *self._batch_sections(),
            *self._overlay_sections(),
            self._figures_section(),
        ]
        return self._report(f"Publication Package - {self._project_title}", sections)

    # -- Part 3: Reproducibility Report (one measurement) ----------------------

    def reproducibility_report(self, index: int) -> Report:
        """"Exactly how was this result produced?" for one measurement.

        Reuses the provenance DAG throughout (never a second representation): the
        human-readable chain comes from ``ExplorerModel.provenance_steps()``; the
        machine-readable appendix is the *exact* JSON ``core.serialize_dag`` already
        produces for persistence.
        """
        session = self._sessions[index]
        model = session.model
        dataset = model.dataset
        steps = model.provenance_steps()
        raw_step = next((s for s in steps if s.step_id == "io.read"), None)
        derived_steps = [s for s in steps if s.step_id != "io.read"]

        source_facts = [DiagnosticRow("Measurement", session.title)]
        if raw_step is not None:
            source_facts.extend(DiagnosticRow("Source", line) for line in raw_step.sources)

        matched = matching_recipe_name(dataset, self._recipes) if self._recipes else None
        recipe_facts = (
            DiagnosticRow(
                "Matched recipe", matched or "no known recipe matches this processing chain"
            ),
        )

        if derived_steps:
            step_lines = [_step_line(i, s) for i, s in enumerate(derived_steps, start=1)]
            software = derived_steps[-1].software
        else:
            step_lines = ["This is the raw measurement - no processing has been applied."]
            software = current_software()

        sections = (
            ReportSection("Source measurement", facts=tuple(source_facts)),
            ReportSection("Matched recipe", facts=recipe_facts),
            ReportSection("Processing chain", lines=tuple(step_lines)),
            ReportSection(
                "Software versions (recorded at the last step)",
                facts=tuple(DiagnosticRow(k, v) for k, v in software.items()),
            ),
            ReportSection(
                "Generated datasets",
                facts=(
                    DiagnosticRow(
                        session.title,
                        f"{len(session.history) + 1} dataset(s) "
                        f"(raw + {len(session.history)} derivation(s))",
                    ),
                ),
            ),
            ReportSection(
                "Machine-readable provenance (JSON)",
                code=json.dumps(serialize_dag(dataset.provenance), indent=2),
            ),
        )
        return self._report(f"Reproducibility Report - {session.title}", list(sections))

    # -- shared sections --------------------------------------------------------

    def _report(self, title: str, sections: list[ReportSection | None]) -> Report:
        return Report(
            title=title,
            generated_at=_now(),
            software=current_software(),
            sections=tuple(s for s in sections if s is not None),
        )

    def _project_section(self) -> ReportSection:
        conventions = self._sessions[0].model.conventions_summary() if self._sessions else "n/a"
        facts = (
            DiagnosticRow("Project", self._project_title),
            DiagnosticRow("Measurements", str(len(self._sessions))),
            DiagnosticRow("Conventions", conventions),
        )
        return ReportSection("Project", facts=facts)

    def _measurements_section(self) -> ReportSection:
        columns = (
            ExperimentColumn("Time"),
            ExperimentColumn("Processing"),
            ExperimentColumn("Harmonics"),
            ExperimentColumn("Reference"),
        )
        rows = tuple(
            ExperimentTableRow(
                measurement_id=r.measurement_id,
                title=r.title,
                cells=(
                    ExperimentCell(r.datetime or "-"),
                    ExperimentCell(r.processing),
                    ExperimentCell(r.harmonics),
                    ExperimentCell("yes" if r.has_reference else "no"),
                ),
            )
            for r in self._experiment.browser_rows()
        )
        return ReportSection(
            "Measurements", table=ExperimentTable("Measurement summary", columns, rows)
        )

    def _diagnostics_section(self) -> ReportSection:
        return ReportSection("Diagnostics summary", table=self._experiment.diagnostics_table())

    def _metadata_section(self) -> ReportSection:
        facts = tuple(
            DiagnosticRow(session.title, _identity_line(session.model))
            for session in self._sessions
        )
        return ReportSection("Measurement metadata", facts=facts)

    def _processing_history_section(self) -> ReportSection:
        lines: list[str] = []
        for session in self._sessions:
            derived = [s for s in session.model.provenance_steps() if s.step_id != "io.read"]
            lines.append(f"**{session.title}**")
            if not derived:
                lines.append("- raw (no processing applied)")
            else:
                lines.extend(_step_line(i, s) for i, s in enumerate(derived, start=1))
        return ReportSection("Processing history", lines=tuple(lines))

    def _applied_recipes_section(self) -> ReportSection | None:
        if not self._recipes:
            return None
        lines = [f"{len(self._recipes)} recipe(s) known this session:"]
        for name, recipe in sorted(self._recipes.items()):
            step_ids = ", ".join(s.step_id for s in recipe.steps)
            lines.append(f"- **{name}** ({len(recipe.steps)} step(s): {step_ids})")
        lines.append("")
        lines.append("Matched against each measurement's own provenance chain:")
        for session in self._sessions:
            match = matching_recipe_name(session.model.dataset, self._recipes)
            verdict = f"matches recipe '{match}'" if match else "no known recipe matches"
            lines.append(f"- {session.title}: {verdict}")
        return ReportSection("Applied recipes", lines=tuple(lines))

    def _batch_sections(self) -> list[ReportSection]:
        return [
            ReportSection(
                f"Batch run: {recipe.name}",
                table=self._experiment.batch_result_table(result, recipe),
            )
            for recipe, result in self._batch_runs
        ]

    def _generated_datasets_section(self) -> ReportSection:
        facts = tuple(
            DiagnosticRow(
                session.title,
                f"{len(session.history) + 1} dataset(s) "
                f"(raw + {len(session.history)} derivation(s))",
            )
            for session in self._sessions
        )
        return ReportSection("Generated datasets", facts=facts)

    def _figures_section(self) -> ReportSection | None:
        if not self._exported_figures:
            return None
        lines = tuple(
            f"- `{figure_path.name}` (provenance: `{prov_path.name}`)"
            for figure_path, prov_path in self._exported_figures
        )
        return ReportSection("Exported figures this session", lines=lines)

    def _overlay_sections(self) -> list[ReportSection]:
        sections: list[ReportSection] = []
        if self._experiment_stats is not None:
            sections.append(
                ReportSection("Cross-measurement overlay statistics", table=self._experiment_stats)
            )

        overlay_lines: list[str] = []
        for session in self._sessions:
            if session.model.is_spectral:
                continue
            for record in session.measure_records:
                summary = _overlay_summary(session.model, record)
                if summary is not None:
                    overlay_lines.append(f"- {session.title}: {summary}")
        if overlay_lines:
            sections.append(
                ReportSection("Region/profile measurements", lines=tuple(overlay_lines))
            )

        histogram_lines: list[str] = []
        for session in self._sessions:
            model = session.model
            if model.is_hyperspectral:
                # Per-band, not a whole-cube statistic (mixing every wavenumber
                # together would be scientifically misleading) - the band a
                # researcher was last looking at, defaulting to band 0 for a
                # session whose view was never captured.
                index = _int_or(session.view_state.get("wavenumber_index"), 0)
                hist = model.band_map_histogram(index)
                wn = model.wavenumber_axis()
                band_note = f" at {wn[index]:.1f} cm^-1" if index < wn.size else ""
            else:
                hist = (
                    model.spectrum_histogram()
                    if model.is_spectral
                    else model.channel_histogram()
                )
                band_note = ""
            if hist.count == 0 or hist.mean is None:
                continue
            histogram_lines.append(
                f"- {session.title} ({model.current_channel} {model.current_representation}"
                f"{band_note}): mean {hist.mean:.4g}, median {hist.median:.4g}, "
                f"std {hist.std:.4g}, n={hist.count}"
            )
        if histogram_lines:
            sections.append(
                ReportSection("Value distribution (current channel)", lines=tuple(histogram_lines))
            )
        return sections


# --------------------------------------------------------------------------- #
# Rendering (pure formatters over the one shared Report/ReportSection shape)
# --------------------------------------------------------------------------- #


def render_markdown(report: Report) -> str:
    """Render *report* as a Markdown document."""
    lines = [
        f"# {report.title}",
        "",
        f"*Generated {report.generated_at} - SNOMNIMAN {report.software.get('snomniman', '?')}*",
        "",
    ]
    for section in report.sections:
        lines.append(f"## {section.title}")
        lines.append("")
        if section.facts:
            lines.extend(f"- **{f.label}:** {f.value}" for f in section.facts)
            lines.append("")
        if section.table is not None:
            lines.extend(_markdown_table(section.table))
            lines.append("")
        if section.lines:
            lines.extend(section.lines)
            lines.append("")
        if section.code is not None:
            lines.append(f"```{section.code_language}")
            lines.append(section.code)
            lines.append("```")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_html(report: Report) -> str:
    """Render *report* as a single, self-contained HTML document."""
    parts = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='utf-8'>",
        f"<title>{_esc(report.title)}</title>",
        "<style>body{font-family:sans-serif;max-width:900px;margin:2em auto;padding:0 1em;}"
        "table{border-collapse:collapse;width:100%;margin:0.5em 0;}"
        "th,td{border:1px solid #ccc;padding:4px 8px;text-align:left;}"
        "code,pre{background:#f4f4f4;padding:2px 4px;}</style>",
        "</head><body>",
        f"<h1>{_esc(report.title)}</h1>",
        f"<p><em>Generated {_esc(report.generated_at)} - SNOMNIMAN "
        f"{_esc(report.software.get('snomniman', '?'))}</em></p>",
    ]
    for section in report.sections:
        parts.append(f"<h2>{_esc(section.title)}</h2>")
        if section.facts:
            parts.append("<ul>")
            parts.extend(f"<li><b>{_esc(f.label)}:</b> {_esc(f.value)}</li>" for f in section.facts)
            parts.append("</ul>")
        if section.table is not None:
            parts.append(_html_table(section.table))
        if section.lines:
            parts.append("<ul>")
            parts.extend(f"<li>{_esc(line)}</li>" for line in section.lines)
            parts.append("</ul>")
        if section.code is not None:
            parts.append(f"<pre><code>{_esc(section.code)}</code></pre>")
    parts.append("</body></html>")
    return "\n".join(parts) + "\n"


def export_report(report: Report, path: str | Path, fmt: str = REPORT_FORMAT_MARKDOWN) -> Path:
    """Render *report* and write it to *path*; return the path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = render_html(report) if fmt == REPORT_FORMAT_HTML else render_markdown(report)
    target.write_text(text, encoding="utf-8")
    return target


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _step_line(index: int, step: Any) -> str:
    params = ", ".join(f"{k}={v!r}" for k, v in step.params.items()) or "no parameters"
    return f"{index}. `{step.step_id}` - {step.description} ({params})"


def _identity_line(model: ExplorerModel) -> str:
    identity = model.identity()
    pixels = (
        f"{identity.pixels[0]}x{identity.pixels[1]} px" if identity.pixels else "unknown pixels"
    )
    field = (
        f"{identity.field_nm[0]:.0f}x{identity.field_nm[1]:.0f} nm"
        if identity.field_nm
        else "unknown field"
    )
    vendor = " ".join(filter(None, [identity.vendor, identity.model])) or "unknown instrument"
    return f"{identity.kind}, {pixels}, {field}, {vendor}"


def _overlay_summary(model: ExplorerModel, record: Mapping[str, Any]) -> str | None:
    """Recompute one measurement overlay's statistics (line/rectangle/polygon)."""
    kind = record.get("kind")
    name = record.get("name", "measurement")
    geometry = record.get("geometry", {})
    if model.is_hyperspectral:
        return _spectral_overlay_summary(model, kind, name, geometry)
    spec = PaneSpec(model.current_channel, model.current_representation)
    try:
        if kind == "line":
            p0, p1 = geometry["points"]
            profile = model.line_profile([spec], tuple(p0), tuple(p1))
            curve = profile.curves[0]
            finite = curve.samples[np.isfinite(curve.samples)]
            if finite.size == 0:
                return f"{name} (line): no finite samples"
            return (
                f"{name} (line, {profile.distance_nm:.3g} nm): "
                f"mean {float(np.mean(finite)):.4g} {curve.unit}"
            )
        if kind == "rectangle":
            x0, y0 = geometry["pos"]
            w, h = geometry["size"]
            report = model.rect_statistics([spec], x0, y0, x0 + w, y0 + h)
        elif kind == "polygon":
            points = [tuple(p) for p in geometry["points"]]
            report = model.polygon_statistics([spec], points)
        else:
            return None
    except (KeyError, ValueError, IndexError):
        return None
    row = report.rows[0]
    stat = row.stats
    return (
        f"{name} ({report.kind}): mean {stat.mean:.4g} {row.unit}, "
        f"std {stat.std:.4g}, n={stat.count} px"
    )


def _spectral_overlay_summary(
    model: ExplorerModel, kind: object, name: object, geometry: Mapping[str, Any]
) -> str | None:
    """The hyperspectral analogue of the rectangle/polygon branch above: a mean
    spectrum, not a per-channel statistic (a hyperspectral ROI's natural summary
    is a spectrum). No line case - line-ROI-across-a-band-map is out of scope
    (docs/phase5-spectral-nanoftir.md's Phase 5B decisions)."""
    try:
        if kind == "rectangle":
            x0, y0 = geometry["pos"]
            w, h = geometry["size"]
            spectral_report = model.rect_spectral_region(x0, y0, x0 + w, y0 + h, label=str(name))
        elif kind == "polygon":
            points = [tuple(p) for p in geometry["points"]]
            spectral_report = model.polygon_spectral_region(points, label=str(name))
        else:
            return None
    except (KeyError, ValueError, IndexError, ProcessingError):
        return None
    curve = spectral_report.curve
    finite = curve.values[np.isfinite(curve.values)]
    if finite.size == 0:
        return f"{name} ({spectral_report.kind}): no finite spectrum"
    peak = int(np.argmax(finite))
    return (
        f"{name} ({spectral_report.kind}): mean spectrum over {spectral_report.count} px, "
        f"peak {finite[peak]:.4g} {curve.unit} at {curve.wavenumber_cm1[peak]:.1f} cm^-1"
    )


def _int_or(value: object, default: int) -> int:
    return value if isinstance(value, int) else default


def _markdown_table(table: ExperimentTable) -> list[str]:
    headers = ["Measurement", *(_column_header(c) for c in table.columns)]
    out = [f"**{table.title}**", "", _md_row(headers), "|" + "|".join(["---"] * len(headers)) + "|"]
    out.extend(_md_row([row.title, *(c.text for c in row.cells)]) for row in table.rows)
    return out


def _md_row(cells: Sequence[str]) -> str:
    return "| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |"


def _html_table(table: ExperimentTable) -> str:
    headers = ["Measurement", *(_column_header(c) for c in table.columns)]
    header_html = "<tr>" + "".join(f"<th>{_esc(h)}</th>" for h in headers) + "</tr>"
    rows_html = [_html_row([row.title, *(c.text for c in row.cells)]) for row in table.rows]
    return f"<p><b>{_esc(table.title)}</b></p><table>{header_html}{''.join(rows_html)}</table>"


def _html_row(cells: Sequence[str]) -> str:
    return "<tr>" + "".join(f"<td>{_esc(cell)}</td>" for cell in cells) + "</tr>"


def _column_header(column: ExperimentColumn) -> str:
    return f"{column.label} [{column.unit}]" if column.unit else column.label


def _esc(text: object) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


__all__ = [
    "REPORT_FORMAT_HTML",
    "REPORT_FORMAT_MARKDOWN",
    "Report",
    "ReportModel",
    "ReportSection",
    "export_report",
    "render_html",
    "render_markdown",
]
