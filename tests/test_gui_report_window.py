"""Integration tests for scientific reporting (Phase 4C) in the Explorer window.

Covers the orchestration layer: building a `ReportModel` from exactly what the
window already holds (sessions, the recipe library, batch-run history, exported-
figure history, the last cross-measurement overlay comparison), choosing a save
path/format via a stock file dialog, and writing the report. Dialog-driven entry
points delegate to directly-testable core methods (`_build_report_model`,
`_prompt_report_path`, `_write_report`), mirroring the Phase 4A/4B convention.

All tests run headless (offscreen Qt) and skip cleanly when PySide6 is absent.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from snomniman.core import Dataset
from snomniman.gui.model import ExplorerModel

pytest.importorskip("PySide6")

from PySide6 import QtWidgets

from snomniman.batch import STATUS_SUCCESS, BatchOutcome, BatchResult
from snomniman.gui.report import REPORT_FORMAT_HTML, REPORT_FORMAT_MARKDOWN
from snomniman.gui.window import MeasurementExplorerWindow
from snomniman.pipeline import Recipe, RecipeStep


@pytest.fixture
def window(qapp: Any, topography_dataset: Dataset) -> Iterator[MeasurementExplorerWindow]:
    win = MeasurementExplorerWindow(ExplorerModel(topography_dataset, title="Scan 1"))
    win.add_measurement_model(ExplorerModel(topography_dataset, title="Scan 2"))
    yield win
    win.close()
    win.deleteLater()
    qapp.processEvents()


# --------------------------------------------------------------------------- #
# _prompt_report_path: format is inferred from the chosen extension
# --------------------------------------------------------------------------- #


def test_prompt_report_path_returns_none_when_cancelled(
    window: MeasurementExplorerWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: ("", ""))
    assert window._prompt_report_path("default") is None


def test_prompt_report_path_infers_html_from_extension(
    window: MeasurementExplorerWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    chosen = str(tmp_path / "report.html")
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: (chosen, "HTML (*.html)")
    )
    result = window._prompt_report_path("default")
    assert result is not None
    path, fmt = result
    assert fmt == REPORT_FORMAT_HTML
    assert path.suffix == ".html"


def test_prompt_report_path_defaults_to_markdown_without_suffix(
    window: MeasurementExplorerWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    chosen = str(tmp_path / "report")
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: (chosen, "Markdown (*.md)")
    )
    result = window._prompt_report_path("default")
    assert result is not None
    path, fmt = result
    assert fmt == REPORT_FORMAT_MARKDOWN
    assert path.suffix == ".md"


# --------------------------------------------------------------------------- #
# _build_report_model: composes exactly what the window already holds
# --------------------------------------------------------------------------- #


def test_build_report_model_includes_recipes_and_batch_history(
    window: MeasurementExplorerWindow,
) -> None:
    recipe = Recipe(name="topo clean", steps=(RecipeStep("image.fix_zero", 1, {"channel": "Z"}),))
    window._recipes["topo clean"] = recipe
    result = BatchResult(
        recipe_name="topo clean",
        requested=1,
        outcomes=(
            BatchOutcome(
                measurement_id="measurement-0001", title="Scan 1", status=STATUS_SUCCESS
            ),
        ),
    )
    window._batch_runs.append((recipe, result))

    report = window._build_report_model().experiment_report()
    titles = [s.title for s in report.sections]
    assert "Applied recipes" in titles
    assert "Batch run: topo clean" in titles


def test_show_batch_result_records_batch_history(window: MeasurementExplorerWindow) -> None:
    recipe = Recipe(name="topo clean", steps=(RecipeStep("image.fix_zero", 1, {"channel": "Z"}),))
    result = BatchResult(recipe_name="topo clean", requested=0)
    assert window._batch_runs == []
    window._show_batch_result(result, recipe)
    assert window._batch_runs == [(recipe, result)]


def test_export_figure_records_figure_history(
    window: MeasurementExplorerWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    out = tmp_path / "figure.png"
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: (str(out), "PNG (*.png)")
    )
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *a, **k: None)
    assert window._exported_figures == []
    window._export_figure()
    assert len(window._exported_figures) == 1
    figure_path, provenance_path = window._exported_figures[0]
    assert figure_path == out
    assert provenance_path.exists()


# --------------------------------------------------------------------------- #
# _write_report: success + failure paths
# --------------------------------------------------------------------------- #


def test_write_report_writes_file_and_confirms(
    window: MeasurementExplorerWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        QtWidgets.QMessageBox, "information", lambda *a, **k: calls.append("shown")
    )
    report = window._build_report_model().experiment_report()
    path = tmp_path / "report.md"
    window._write_report(report, path, REPORT_FORMAT_MARKDOWN)
    assert path.is_file()
    assert calls


def test_write_report_shows_warning_on_failure(
    window: MeasurementExplorerWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import snomniman.gui.window as window_module

    def _boom(*args: object, **kwargs: object) -> Path:
        raise OSError("disk full")

    monkeypatch.setattr(window_module, "export_report", _boom)
    calls: list[str] = []
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", lambda *a, **k: calls.append("shown"))
    report = window._build_report_model().experiment_report()
    window._write_report(report, tmp_path / "report.md", REPORT_FORMAT_MARKDOWN)
    assert calls


# --------------------------------------------------------------------------- #
# Full dialog-driven flow for each of the three report actions
# --------------------------------------------------------------------------- #


def test_generate_experiment_report_end_to_end(
    window: MeasurementExplorerWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    out = tmp_path / "report.md"
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: (str(out), "Markdown (*.md)")
    )
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *a, **k: None)
    window._on_generate_experiment_report()
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# Experiment Report")
    assert "Scan 1" in text and "Scan 2" in text


def test_generate_publication_package_end_to_end(
    window: MeasurementExplorerWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    out = tmp_path / "package.html"
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: (str(out), "HTML (*.html)")
    )
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *a, **k: None)
    window._on_generate_publication_package()
    text = out.read_text(encoding="utf-8")
    assert "Publication Package" in text
    assert "<html>" in text


def test_generate_reproducibility_report_targets_active_measurement(
    window: MeasurementExplorerWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    assert window._active_index == 1  # "Scan 2" is active (added last)
    out = tmp_path / "repro.md"
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: (str(out), "Markdown (*.md)")
    )
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *a, **k: None)
    window._on_generate_reproducibility_report()
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# Reproducibility Report - Scan 2")


def test_generate_report_cancelled_dialog_writes_nothing(
    window: MeasurementExplorerWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: ("", ""))
    window._on_generate_experiment_report()
    assert list(tmp_path.iterdir()) == []
