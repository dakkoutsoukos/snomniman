"""End-to-end window tests for the research workflow: save, reopen, export.

These verify the milestone's success criterion - a researcher can load a
measurement, process it, measure it, save the project, and reopen it to continue
exactly where they left off - plus the processed-data / channel / measurement
exports. Skipped without the gui extra; headless (offscreen) otherwise.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from snomniman.core import Dataset
from snomniman.gui.model import ExplorerModel
from snomniman.io import read_zarr
from snomniman.pipeline import load_project, save_project

pytest.importorskip("PySide6")

from snomniman.gui.window import MeasurementExplorerWindow


@pytest.fixture
def window(qapp: Any, synthetic_dataset: Dataset) -> Iterator[MeasurementExplorerWindow]:
    win = MeasurementExplorerWindow(ExplorerModel(synthetic_dataset, title="CdO"))
    win.resize(1100, 720)
    win.show()  # realize the scene so measurement geometry maps to physical coords
    qapp.processEvents()
    yield win
    win.close()
    win.deleteLater()
    qapp.processEvents()


def _apply_plane_level(window: MeasurementExplorerWindow) -> None:
    """Drive the generic preview/accept path to add one derivation to the history."""
    window._on_preview_requested("image.plane_level", {"channel": "Z", "order": 1})
    window._on_preview_accepted()


# -- the File menu ----------------------------------------------------------- #


def test_file_menu_exposes_the_workflow_actions(window: MeasurementExplorerWindow) -> None:
    texts = {a.text() for a in window._file_menu.actions()}
    # The required File actions are present (ampersands are keyboard accelerators).
    assert {
        "&New",
        "&Open Measurement...",
        "Open &Project...",
        "&Save Project",
        "Save Project &As...",
    } <= texts
    # The Export submenu carries the data / channel / measurement / figure exports.
    export_texts = {a.text() for a in window._export_menu.actions()}
    assert {
        "Processed &Data (Zarr)...",
        "&Channel (GSF)...",
        "&Measurement (CSV)...",
        "&Figure...",
    } <= export_texts


# -- save / reopen ----------------------------------------------------------- #


def test_current_project_bundles_history(window: MeasurementExplorerWindow) -> None:
    _apply_plane_level(window)
    project = window.current_project()
    assert len(project.datasets) == 2  # raw + leveled
    assert project.current_index == 1
    assert project.current.is_raw is False
    assert project.raw.is_raw is True


def test_save_then_reopen_restores_the_session(
    window: MeasurementExplorerWindow, qapp: Any, synthetic_dataset: Dataset, tmp_path: Path
) -> None:
    # Process, measure, and move off the default channel.
    _apply_plane_level(window)
    window._browser.channelSelected.emit("O3")
    window._measure.add_rectangle()
    assert len(window._measure.items) == 1

    bundle = save_project(window.current_project(), tmp_path / "session.snomproj")

    # Reopen in a fresh window, exactly as relaunching the app would.
    reopened = MeasurementExplorerWindow(ExplorerModel(synthetic_dataset))
    reopened.resize(1100, 720)
    reopened.show()
    qapp.processEvents()
    try:
        reopened.load_project_object(load_project(bundle))
        qapp.processEvents()
        # History (the raw measurement) and the active derived dataset are restored.
        assert len(reopened._history) == 1
        assert reopened._model.dataset.is_raw is False
        # The active channel the session was on is restored.
        assert reopened._model.current_channel == "O3"
        # The measurement is restored onto the image.
        assert len(reopened._measure.items) == 1
        assert reopened._measure.items[0].kind == "rectangle"
    finally:
        reopened.close()
        reopened.deleteLater()
        qapp.processEvents()


def test_open_project_handler_round_trips(
    window: MeasurementExplorerWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6 import QtWidgets

    _apply_plane_level(window)
    bundle = save_project(window.current_project(), tmp_path / "p.snomproj")

    fresh = MeasurementExplorerWindow(ExplorerModel(window._model.dataset))
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getExistingDirectory", lambda *a, **k: str(bundle)
    )
    try:
        fresh._open_project()
        assert fresh._project_path == bundle
        assert len(fresh._history) == 1  # the raw measurement
    finally:
        fresh.close()
        fresh.deleteLater()


# -- measurement-session round-trip ------------------------------------------ #


def test_measurement_records_round_trip(window: MeasurementExplorerWindow) -> None:
    window._measure.add_line()
    window._measure.add_rectangle()
    records = window._measure.to_records()
    assert [r["kind"] for r in records] == ["line", "rectangle"]

    window._measure.load_records(records)
    again = window._measure.to_records()
    assert [r["kind"] for r in again] == ["line", "rectangle"]
    assert [r["name"] for r in again] == [r["name"] for r in records]


# -- exports ----------------------------------------------------------------- #


def test_export_data_zarr_writes_reloadable_store(
    window: MeasurementExplorerWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6 import QtWidgets

    out = tmp_path / "processed.zarr"
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: (str(out), "Zarr store (*.zarr)")
    )
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *a, **k: None)
    window._export_data_zarr()
    assert out.is_dir()
    assert read_zarr(out).kind is window._model.dataset.kind


def test_export_channel_gsf_writes_file_and_sidecar(
    window: MeasurementExplorerWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6 import QtWidgets

    out = tmp_path / "channel.gsf"
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: (str(out), "GSF (*.gsf)")
    )
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *a, **k: None)
    window._export_channel_gsf()
    assert out.exists() and out.stat().st_size > 0
    assert (tmp_path / "channel.gsf.provenance.json").exists()


def test_export_measurement_csv_writes_file(
    window: MeasurementExplorerWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6 import QtWidgets

    window._measure.add_rectangle()  # an active measurement to export
    out = tmp_path / "stats.csv"
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: (str(out), "CSV (*.csv)")
    )
    window._export_measurement_csv()
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "# SNOMNIMAN" in text and "channel,unit,mean" in text
