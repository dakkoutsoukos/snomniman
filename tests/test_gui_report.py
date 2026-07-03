"""Tests for the Qt-free reporting presenter (Phase 4C: snomniman.gui.report).

``ReportModel`` composes the Experiment Report / Publication Package /
Reproducibility Report entirely from already-computed facts (ExperimentModel,
ExplorerModel, the provenance DAG, BatchResult, Recipe matching) - these tests
confirm the composition is correct and deterministic, not that any underlying
number is right (that is covered where each number is actually computed).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import snomniman.processing.image  # noqa: F401  (registers image ops)
from snomniman.batch import STATUS_SKIPPED, BatchOutcome, BatchResult
from snomniman.core import Dataset, deserialize_dag
from snomniman.gui.model import DiagnosticRow, ExplorerModel, MeasurementSession
from snomniman.gui.report import (
    REPORT_FORMAT_HTML,
    REPORT_FORMAT_MARKDOWN,
    Report,
    ReportModel,
    ReportSection,
    export_report,
    render_html,
    render_markdown,
)
from snomniman.pipeline import Recipe, RecipeStep, capture_recipe
from snomniman.processing.image.fix_zero import FixZero
from snomniman.processing.image.plane_level import PlaneLevel


def _session(
    dataset: Dataset,
    *,
    mid: str,
    title: str,
    history: list[ExplorerModel] | None = None,
    measure_records: list[dict[str, object]] | None = None,
) -> MeasurementSession:
    return MeasurementSession(
        model=ExplorerModel(dataset, title=title),
        measurement_id=mid,
        title=title,
        history=history or [],
        measure_records=measure_records or [],
    )


def _manual_chain(dataset: Dataset) -> Dataset:
    leveled = PlaneLevel(channel="Z", order=1).apply({"primary": dataset})
    return FixZero(channel="Z").apply({"primary": leveled})


@pytest.fixture
def two_sessions(
    synthetic_dataset: Dataset, topography_dataset: Dataset
) -> list[MeasurementSession]:
    return [
        _session(synthetic_dataset, mid="measurement-0001", title="CdO full"),
        _session(topography_dataset, mid="measurement-0002", title="Topo only"),
    ]


# --------------------------------------------------------------------------- #
# Experiment Report (Part 1)
# --------------------------------------------------------------------------- #


def test_experiment_report_includes_expected_sections(
    two_sessions: list[MeasurementSession],
) -> None:
    report = ReportModel(two_sessions, "Test Project").experiment_report()
    assert report.title == "Experiment Report - Test Project"
    titles = [s.title for s in report.sections]
    assert "Project" in titles
    assert "Measurements" in titles
    assert "Diagnostics summary" in titles
    assert "Processing history" in titles
    assert "Generated datasets" in titles
    # No recipes/batch runs were given, so those sections are honestly absent.
    assert "Applied recipes" not in titles
    assert not any(t.startswith("Batch run:") for t in titles)


def test_experiment_report_project_section_facts(two_sessions: list[MeasurementSession]) -> None:
    report = ReportModel(two_sessions, "Test Project").experiment_report()
    project = next(s for s in report.sections if s.title == "Project")
    facts = {f.label: f.value for f in project.facts}
    assert facts["Project"] == "Test Project"
    assert facts["Measurements"] == "2"


def test_experiment_report_measurements_table_lists_every_measurement(
    two_sessions: list[MeasurementSession],
) -> None:
    report = ReportModel(two_sessions, "Test Project").experiment_report()
    table = next(s for s in report.sections if s.title == "Measurements").table
    assert table is not None
    assert [row.title for row in table.rows] == ["CdO full", "Topo only"]


def test_experiment_report_processing_history_reflects_provenance(
    topography_dataset: Dataset,
) -> None:
    derived = _manual_chain(topography_dataset)
    session = _session(derived, mid="measurement-0001", title="Scan 1")
    report = ReportModel([session], "Test Project").experiment_report()
    history = next(s for s in report.sections if s.title == "Processing history")
    text = "\n".join(history.lines)
    assert "image.plane_level" in text
    assert "image.fix_zero" in text


def test_experiment_report_raw_measurement_says_so(topography_dataset: Dataset) -> None:
    session = _session(topography_dataset, mid="measurement-0001", title="Scan 1")
    report = ReportModel([session], "Test Project").experiment_report()
    history = next(s for s in report.sections if s.title == "Processing history")
    assert any("raw" in line for line in history.lines)


def test_experiment_report_generated_datasets_counts_derivations(
    topography_dataset: Dataset,
) -> None:
    derived = PlaneLevel(channel="Z", order=1).apply({"primary": topography_dataset})
    session = _session(
        derived, mid="measurement-0001", title="Scan 1", history=[ExplorerModel(topography_dataset)]
    )
    report = ReportModel([session], "Test Project").experiment_report()
    generated = next(s for s in report.sections if s.title == "Generated datasets")
    assert "2 dataset(s)" in generated.facts[0].value


def test_experiment_report_value_distribution_present_when_finite(
    two_sessions: list[MeasurementSession],
) -> None:
    report = ReportModel(two_sessions, "Test Project").experiment_report()
    titles = [s.title for s in report.sections]
    assert "Value distribution (current channel)" in titles


# --------------------------------------------------------------------------- #
# Applied recipes + batch sections
# --------------------------------------------------------------------------- #


def test_applied_recipes_section_reports_a_provenance_match(topography_dataset: Dataset) -> None:
    derived = _manual_chain(topography_dataset)
    recipe = capture_recipe(derived, name="topo clean")
    session = _session(derived, mid="measurement-0001", title="Scan 1")
    report = ReportModel(
        [session], "Test Project", recipes={"topo clean": recipe}
    ).experiment_report()
    applied = next(s for s in report.sections if s.title == "Applied recipes")
    text = "\n".join(applied.lines)
    assert "topo clean" in text
    assert "matches recipe 'topo clean'" in text


def test_applied_recipes_section_reports_no_match_honestly(topography_dataset: Dataset) -> None:
    other = Recipe(name="unrelated", steps=(RecipeStep("image.fix_zero", 1, {"channel": "Z"}),))
    session = _session(topography_dataset, mid="measurement-0001", title="Scan 1")
    report = ReportModel(
        [session], "Test Project", recipes={"unrelated": other}
    ).experiment_report()
    applied = next(s for s in report.sections if s.title == "Applied recipes")
    assert any("no known recipe matches" in line for line in applied.lines)


def test_batch_section_reuses_experiment_batch_result_table(
    two_sessions: list[MeasurementSession],
) -> None:
    recipe = Recipe(
        name="topo clean", steps=(RecipeStep("image.fix_zero", 1, {"channel": "Z"}),)
    )
    result = BatchResult(
        recipe_name="topo clean",
        requested=1,
        outcomes=(
            BatchOutcome(
                measurement_id="measurement-0002",
                title="Topo only",
                status=STATUS_SKIPPED,
                reason="did not apply",
            ),
        ),
        elapsed_seconds=1.5,
    )
    report = ReportModel(
        two_sessions, "Test Project", batch_runs=[(recipe, result)]
    ).experiment_report()
    batch_section = next(s for s in report.sections if s.title == "Batch run: topo clean")
    assert batch_section.table is not None
    assert batch_section.table.rows[0].cells[0].text == STATUS_SKIPPED


# --------------------------------------------------------------------------- #
# Publication Package (Part 2)
# --------------------------------------------------------------------------- #


def test_publication_package_includes_metadata_and_figures(
    two_sessions: list[MeasurementSession], tmp_path: Path
) -> None:
    fig = tmp_path / "figure.pdf"
    prov = tmp_path / "figure.provenance.json"
    fig.write_text("x")
    prov.write_text("{}")
    report = ReportModel(
        two_sessions, "Test Project", exported_figures=[(fig, prov)]
    ).publication_package()
    titles = [s.title for s in report.sections]
    assert report.title == "Publication Package - Test Project"
    assert "Measurement metadata" in titles
    figures = next(s for s in report.sections if s.title == "Exported figures this session")
    assert any("figure.pdf" in line for line in figures.lines)


def test_publication_package_omits_figures_section_when_none_exported(
    two_sessions: list[MeasurementSession],
) -> None:
    report = ReportModel(two_sessions, "Test Project").publication_package()
    assert "Exported figures this session" not in [s.title for s in report.sections]


# --------------------------------------------------------------------------- #
# Region/profile overlay recomputation
# --------------------------------------------------------------------------- #


def test_overlay_rectangle_is_recomputed_from_stored_geometry(
    topography_dataset: Dataset,
) -> None:
    record = {
        "kind": "rectangle",
        "name": "ROI 1",
        "visible": True,
        "geometry": {"pos": [25.0, 25.0], "size": [100.0, 50.0]},
    }
    session = _session(
        topography_dataset, mid="measurement-0001", title="Scan 1", measure_records=[record]
    )
    report = ReportModel([session], "Test Project").experiment_report()
    overlays = next(s for s in report.sections if s.title == "Region/profile measurements")
    assert any("ROI 1" in line and "rectangle" in line for line in overlays.lines)


def test_overlay_with_bad_geometry_is_skipped_not_raised(topography_dataset: Dataset) -> None:
    record = {"kind": "rectangle", "name": "bad", "visible": True, "geometry": {}}
    session = _session(
        topography_dataset, mid="measurement-0001", title="Scan 1", measure_records=[record]
    )
    # Must not raise; the malformed record simply contributes nothing.
    report = ReportModel([session], "Test Project").experiment_report()
    assert not any(s.title == "Region/profile measurements" for s in report.sections)


# --------------------------------------------------------------------------- #
# Hyperspectral sessions (Phase 5B): a real fact must be reported, not silently
# dropped - is_spectral stays False for a hyperspectral session, so it always
# flowed through these code paths; the fix is what they compute, not whether.
# --------------------------------------------------------------------------- #


def test_hyperspectral_overlay_rectangle_reports_a_spectrum_peak(
    hyperspectral_dataset: Dataset,
) -> None:
    record = {
        "kind": "rectangle",
        "name": "ROI A",
        "visible": True,
        "geometry": {"pos": [100.0, 75.0], "size": [150.0, 100.0]},  # covers the known peak
    }
    session = _session(
        hyperspectral_dataset, mid="measurement-0001", title="Cube", measure_records=[record]
    )
    report = ReportModel([session], "Test Project").experiment_report()
    overlays = next(s for s in report.sections if s.title == "Region/profile measurements")
    assert any(
        "ROI A" in line and "rectangle" in line and "cm^-1" in line for line in overlays.lines
    )


def test_hyperspectral_overlay_with_bad_geometry_is_skipped_not_raised(
    hyperspectral_dataset: Dataset,
) -> None:
    record = {"kind": "rectangle", "name": "bad", "visible": True, "geometry": {}}
    session = _session(
        hyperspectral_dataset, mid="measurement-0001", title="Cube", measure_records=[record]
    )
    report = ReportModel([session], "Test Project").experiment_report()
    assert not any(s.title == "Region/profile measurements" for s in report.sections)


def test_hyperspectral_histogram_line_is_per_band_not_whole_cube(
    hyperspectral_dataset: Dataset,
) -> None:
    session = _session(hyperspectral_dataset, mid="measurement-0001", title="Cube")
    session.view_state = {"wavenumber_index": 12}  # the fixture's known peak band
    report = ReportModel([session], "Test Project").experiment_report()
    dist = next(s for s in report.sections if s.title == "Value distribution (current channel)")
    line = next(line for line in dist.lines if "Cube" in line)
    assert "1724.0 cm^-1" in line


def test_hyperspectral_histogram_defaults_to_band_zero_without_view_state(
    hyperspectral_dataset: Dataset,
) -> None:
    session = _session(hyperspectral_dataset, mid="measurement-0001", title="Cube")
    report = ReportModel([session], "Test Project").experiment_report()
    dist = next(s for s in report.sections if s.title == "Value distribution (current channel)")
    line = next(line for line in dist.lines if "Cube" in line)
    assert "1700.0 cm^-1" in line


# --------------------------------------------------------------------------- #
# Reproducibility Report (Part 3)
# --------------------------------------------------------------------------- #


def test_reproducibility_report_raw_measurement(topography_dataset: Dataset) -> None:
    session = _session(topography_dataset, mid="measurement-0001", title="Scan 1")
    report = ReportModel([session], "Test Project").reproducibility_report(0)
    assert report.title == "Reproducibility Report - Scan 1"
    chain = next(s for s in report.sections if s.title == "Processing chain")
    assert "raw measurement" in chain.lines[0]
    matched = next(s for s in report.sections if s.title == "Matched recipe")
    assert "no known recipe" in matched.facts[0].value


def test_reproducibility_report_matched_recipe_and_provenance(
    topography_dataset: Dataset,
) -> None:
    derived = _manual_chain(topography_dataset)
    recipe = capture_recipe(derived, name="topo clean")
    session = _session(derived, mid="measurement-0001", title="Scan 1")
    report = ReportModel(
        [session], "Test Project", recipes={"topo clean": recipe}
    ).reproducibility_report(0)

    matched = next(s for s in report.sections if s.title == "Matched recipe")
    assert matched.facts[0].value == "topo clean"

    chain = next(s for s in report.sections if s.title == "Processing chain")
    text = "\n".join(chain.lines)
    assert "image.plane_level" in text and "image.fix_zero" in text

    appendix = next(
        s for s in report.sections if s.title == "Machine-readable provenance (JSON)"
    )
    assert appendix.code is not None
    data = json.loads(appendix.code)
    rebuilt = deserialize_dag(data)
    assert rebuilt.node_id == derived.provenance.node_id


def test_reproducibility_report_source_section_has_raw_source(
    topography_dataset: Dataset,
) -> None:
    session = _session(topography_dataset, mid="measurement-0001", title="Scan 1")
    report = ReportModel([session], "Test Project").reproducibility_report(0)
    source = next(s for s in report.sections if s.title == "Source measurement")
    assert source.facts[0].label == "Measurement"
    assert source.facts[0].value == "Scan 1"


# --------------------------------------------------------------------------- #
# Rendering (Markdown / HTML) + export
# --------------------------------------------------------------------------- #


def _sample_report() -> Report:
    return Report(
        title="Sample & <Report>",
        generated_at="2026-07-02T00:00:00+00:00",
        software={"snomniman": "0.1.0"},
        sections=(
            ReportSection("Facts", facts=(_fact("A", "1"), _fact("B", "<2>"))),
            ReportSection("Notes", lines=("- a note", "- another & one")),
            ReportSection("Code", code='{"a": 1}'),
        ),
    )


def _fact(label: str, value: str) -> DiagnosticRow:
    return DiagnosticRow(label, value)


def test_render_markdown_contains_title_and_sections() -> None:
    text = render_markdown(_sample_report())
    assert "# Sample & <Report>" in text
    assert "**A:** 1" in text
    assert "- a note" in text
    assert "```json" in text
    assert '{"a": 1}' in text


def test_render_html_escapes_content() -> None:
    text = render_html(_sample_report())
    assert "<title>Sample &amp; &lt;Report&gt;</title>" in text
    assert "&lt;2&gt;" in text  # the fact value was escaped, not left raw
    assert "<pre><code>" in text


def test_export_report_writes_markdown(tmp_path: Path) -> None:
    path = export_report(_sample_report(), tmp_path / "report.md", REPORT_FORMAT_MARKDOWN)
    assert path.is_file()
    assert "# Sample" in path.read_text(encoding="utf-8")


def test_export_report_writes_html(tmp_path: Path) -> None:
    path = export_report(_sample_report(), tmp_path / "report.html", REPORT_FORMAT_HTML)
    assert path.is_file()
    assert "<html>" in path.read_text(encoding="utf-8")


def test_export_report_creates_parent_directories(tmp_path: Path) -> None:
    path = export_report(_sample_report(), tmp_path / "nested" / "dir" / "report.md")
    assert path.is_file()
