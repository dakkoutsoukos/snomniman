"""End-to-end window tests for Phase 2B experiment analysis (read-only).

These verify the experiment-level workflow through the window: the Manager browser
summarises every measurement, measurements compare side by side (reusing the
comparison viewer), the Experiment tab tabulates project-wide diagnostics, and the
active overlay is evaluated across measurements and exported. A single-measurement
project stays unobtrusive. Skipped without the gui extra; headless otherwise.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from snomniman.core import Dataset
from snomniman.gui.model import ExplorerModel

pytest.importorskip("PySide6")

from snomniman.gui.window import MeasurementExplorerWindow


def _text(item: Any) -> str:
    """A table cell's text (QTableWidget.item may be None; tests expect it present)."""
    assert item is not None
    return str(item.text())


@pytest.fixture
def window(qapp: Any, synthetic_dataset: Dataset) -> Iterator[MeasurementExplorerWindow]:
    win = MeasurementExplorerWindow(ExplorerModel(synthetic_dataset, title="CdO A"))
    win.resize(1100, 720)
    win.show()  # realize the scene so overlay geometry maps to physical coords
    qapp.processEvents()
    yield win
    win.close()
    win.deleteLater()
    qapp.processEvents()


def _add_second(window: MeasurementExplorerWindow, synthetic_dataset: Dataset) -> None:
    window.add_measurement_model(ExplorerModel(synthetic_dataset, title="CdO B"))


# -- experiment browser (Part 3) --------------------------------------------- #


def test_manager_browser_summarizes_measurements(
    window: MeasurementExplorerWindow, synthetic_dataset: Dataset
) -> None:
    _add_second(window, synthetic_dataset)
    table = window._manager._table
    assert table.rowCount() == 2
    assert {_text(table.item(r, 0)) for r in range(2)} == {"CdO A", "CdO B"}
    # Harmonics + reference columns come from structure (cheap, no diagnose).
    assert _text(table.item(0, 3)) == "2, 3"
    assert _text(table.item(0, 4)) == "yes"


def test_single_measurement_browser_is_one_quiet_row(window: MeasurementExplorerWindow) -> None:
    # One measurement: a single row and Compare disabled (the app feels unchanged).
    assert window._manager._table.rowCount() == 1
    assert window._manager._compare_btn.isEnabled() is False


# -- cross-measurement comparison (Part 1) ----------------------------------- #


def test_compare_measurements_enters_compare_mode(
    window: MeasurementExplorerWindow, synthetic_dataset: Dataset, qapp: Any
) -> None:
    _add_second(window, synthetic_dataset)
    window.compare_measurements([0, 1])
    qapp.processEvents()
    assert window._experiment_compare == (0, 1)
    assert window._stack.currentWidget() is window._comparison
    assert len(window._comparison.specs) == 2  # one pane per measurement


def test_switching_measurement_exits_compare_mode(
    window: MeasurementExplorerWindow, synthetic_dataset: Dataset, qapp: Any
) -> None:
    _add_second(window, synthetic_dataset)
    window.compare_measurements([0, 1])
    qapp.processEvents()
    window.switch_to(1)  # picking a single measurement leaves compare mode
    qapp.processEvents()
    assert window._experiment_compare is None
    assert window._stack.currentWidget() is window._image


# -- experiment diagnostics (Part 4) ----------------------------------------- #


def test_experiment_tab_populates_diagnostics(
    window: MeasurementExplorerWindow, synthetic_dataset: Dataset, qapp: Any
) -> None:
    _add_second(window, synthetic_dataset)
    window._inspect_tabs.setCurrentWidget(window._experiment_panel)  # fires the lazy populate
    qapp.processEvents()
    diag = window._experiment_panel._diagnostics
    assert diag.rowCount() == 2
    # First column is the measurement; at least one diagnostic column follows.
    assert diag.columnCount() >= 2
    assert {_text(diag.item(r, 0)) for r in range(2)} == {"CdO A", "CdO B"}


# -- cross-measurement statistics (Part 5) ----------------------------------- #


def test_compare_overlay_builds_and_exports_statistics(
    window: MeasurementExplorerWindow,
    synthetic_dataset: Dataset,
    qapp: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from PySide6 import QtWidgets

    _add_second(window, synthetic_dataset)
    window._measure.add_rectangle()  # an overlay on the active measurement
    qapp.processEvents()

    window._compare_overlay()
    assert window._experiment_stats is not None
    assert len(window._experiment_stats.rows) == 2  # both measurements measured
    assert window._experiment_panel._statistics.rowCount() == 2

    out = tmp_path / "comparison.csv"
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: (str(out), "CSV (*.csv)")
    )
    window._export_experiment_stats()
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "# SNOMNIMAN experiment export" in text and "measurement," in text


def test_compare_overlay_without_overlay_is_a_noop(
    window: MeasurementExplorerWindow, synthetic_dataset: Dataset, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6 import QtWidgets

    _add_second(window, synthetic_dataset)
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *a, **k: None)
    window._compare_overlay()  # no overlay placed -> hint, nothing computed
    assert window._experiment_stats is None
