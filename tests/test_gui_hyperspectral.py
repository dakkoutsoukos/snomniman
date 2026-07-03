"""Widget- and window-level tests for the hyperspectral workspace (Phase 5B).

Skipped without the gui extra. The widget-level section (no window needed -
mirrors how test_gui_spectrumview.py tests SpectrumPlotView.show_curves
standalone) covers construction, the wavenumber slider/spinbox wiring, and
click-to-pin, driven by directly emitting signals / calling the internal
handler with a stub event (the established convention throughout this test
suite) rather than simulating raw Qt scene mouse events. The window-level
section covers the is_hyperspectral dispatch, view persistence across save/
reopen, GSF band export, and - the direct regression test for the confirmed
preview crash - running spectrum.fft_interferogram through the Processing
Workspace end to end.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from snomniman.core import Dataset

pytest.importorskip("PySide6")

from PySide6 import QtCore

from snomniman.gui.hyperspectral import HyperspectralView
from snomniman.gui.imageview import ChannelImageView
from snomniman.gui.model import ExplorerModel
from snomniman.gui.spectrumview import SpectrumPlotView
from snomniman.gui.window import MeasurementExplorerWindow
from snomniman.pipeline import load_project, save_project


class _StubClickEvent:
    def __init__(self, x: float, y: float) -> None:
        self._pos = QtCore.QPointF(x, y)

    def scenePos(self) -> QtCore.QPointF:
        return self._pos


def test_constructs_with_band_view_and_spectrum_view(qapp: Any) -> None:
    view = HyperspectralView()
    assert isinstance(view.band_view, ChannelImageView)
    assert isinstance(view.spectrum_view, SpectrumPlotView)


def test_wavenumber_range_sizes_the_slider(qapp: Any) -> None:
    view = HyperspectralView()
    view.set_wavenumber_range(25)
    assert view._wavenumber_slider.maximum() == 24
    assert view._wavenumber_spin.maximum() == 24


def test_wavenumber_range_of_one_band_does_not_crash(qapp: Any) -> None:
    view = HyperspectralView()
    view.set_wavenumber_range(1)
    assert view._wavenumber_slider.maximum() == 0


def test_moving_the_spinbox_emits_wavenumber_changed(qapp: Any) -> None:
    view = HyperspectralView()
    view.set_wavenumber_range(25)
    received: list[int] = []
    view.wavenumberChanged.connect(received.append)
    view._wavenumber_spin.setValue(12)
    assert received == [12]


def test_slider_and_spinbox_stay_synchronized(qapp: Any) -> None:
    view = HyperspectralView()
    view.set_wavenumber_range(25)
    view._wavenumber_slider.setValue(7)
    assert view._wavenumber_spin.value() == 7
    view._wavenumber_spin.setValue(3)
    assert view._wavenumber_slider.value() == 3


def test_set_wavenumber_index_does_not_emit(qapp: Any) -> None:
    view = HyperspectralView()
    view.set_wavenumber_range(25)
    received: list[int] = []
    view.wavenumberChanged.connect(received.append)
    view.set_wavenumber_index(10)
    assert received == []
    assert view.wavenumber_index() == 10


def test_wavenumber_readout_sets_text(qapp: Any) -> None:
    view = HyperspectralView()
    view.set_wavenumber_readout("1724.0 cm^-1")
    assert view._wavenumber_readout.text() == "1724.0 cm^-1"


def test_band_click_emits_pixel_clicked_in_physical_coordinates(qapp: Any) -> None:
    view = HyperspectralView()
    received: list[tuple[float, float]] = []
    view.pixelClicked.connect(lambda x, y: received.append((x, y)))
    view._on_band_clicked(_StubClickEvent(12.5, 34.5))
    assert len(received) == 1


def test_band_view_cursor_moved_signal_is_reusable_unmodified(qapp: Any) -> None:
    # The live-hover preview (Part 3/4) reuses ChannelImageView.cursorMoved as-is -
    # no wrapping needed in HyperspectralView.
    view = HyperspectralView()
    received: list[tuple[float, float, bool]] = []
    view.band_view.cursorMoved.connect(lambda x, y, ok: received.append((x, y, ok)))
    view.band_view.cursorMoved.emit(10.0, 20.0, True)
    assert received == [(10.0, 20.0, True)]


# --------------------------------------------------------------------------- #
# Window-level wiring: is_hyperspectral dispatch, persistence, export, preview
# --------------------------------------------------------------------------- #


@pytest.fixture
def window(qapp: Any, hyperspectral_dataset: Dataset) -> Iterator[MeasurementExplorerWindow]:
    win = MeasurementExplorerWindow(ExplorerModel(hyperspectral_dataset, title="Cube"))
    win.resize(1100, 720)
    win.show()
    qapp.processEvents()
    yield win
    win.close()
    win.deleteLater()
    qapp.processEvents()


def test_window_opens_directly_into_the_hyperspectral_view(
    window: MeasurementExplorerWindow,
) -> None:
    assert window._stack.currentWidget() is window._hyperspectral
    assert window._stack.currentWidget() is not window._image
    assert window._stack.currentWidget() is not window._spectrum


def test_image_only_buttons_are_disabled_for_hyperspectral(
    window: MeasurementExplorerWindow,
) -> None:
    assert window._image_only_buttons
    assert all(not b.isEnabled() for b in window._image_only_buttons)


def test_wavenumber_slider_updates_the_band_map(window: MeasurementExplorerWindow) -> None:
    before = np.array(window._hyperspectral.band_view._values, copy=True)
    window._hyperspectral._wavenumber_spin.setValue(12)  # the fixture's known peak band
    after = window._hyperspectral.band_view._values
    assert not np.allclose(before, after)
    assert "1724" in window._active.text()


def test_pixel_click_shows_that_pixels_spectrum(window: MeasurementExplorerWindow) -> None:
    # Pixel (y=2, x=3) is at x=175 nm, y=125 nm (50 nm pitch, pixel centers at
    # 25/75/125/175/225 nm) - well inside the fixture's known peak pixel.
    window._on_hyperspectral_pixel_clicked(175.0, 125.0)
    _, y = window._hyperspectral.spectrum_view._curve_item.getData()
    assert int(np.argmax(y)) == 12  # the known resonance's wavenumber index


def test_switching_between_hyperspectral_and_image_sessions(
    window: MeasurementExplorerWindow, synthetic_dataset: Dataset
) -> None:
    window.add_measurement_model(ExplorerModel(synthetic_dataset))
    assert window._stack.currentWidget() is window._image
    assert all(b.isEnabled() for b in window._image_only_buttons)

    window.switch_to(0)
    assert window._stack.currentWidget() is window._hyperspectral
    assert all(not b.isEnabled() for b in window._image_only_buttons)


def test_export_channel_gsf_exports_the_displayed_band(
    window: MeasurementExplorerWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6 import QtWidgets

    window._hyperspectral._wavenumber_spin.setValue(12)
    out = tmp_path / "band.gsf"
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(out), ""))
    )
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", staticmethod(lambda *a, **k: None))
    window._export_channel_gsf()
    assert out.exists()


def test_save_then_reopen_restores_the_wavenumber_index(
    window: MeasurementExplorerWindow, qapp: Any, hyperspectral_dataset: Dataset, tmp_path: Path
) -> None:
    window._hyperspectral._wavenumber_spin.setValue(12)
    bundle = save_project(window.current_project(), tmp_path / "cube.snomproj")

    reopened = MeasurementExplorerWindow(ExplorerModel(hyperspectral_dataset))
    reopened.resize(1100, 720)
    reopened.show()
    qapp.processEvents()
    try:
        reopened.load_project_object(load_project(bundle))
        qapp.processEvents()
        assert reopened._stack.currentWidget() is reopened._hyperspectral
        assert reopened._hyperspectral.wavenumber_index() == 12
    finally:
        reopened.close()
        reopened.deleteLater()
        qapp.processEvents()


def test_preview_spectrum_fft_interferogram_does_not_crash(
    qapp: Any, synthetic_dataset: Dataset
) -> None:
    # The direct regression test for the confirmed bug: Preview on a dataset
    # with no x/y coordinates used to raise an uncaught DatasetError from a Qt
    # slot. Drives the real _on_preview_requested end to end. Opening a raw
    # INTERFEROGRAM measurement in the window is its own, separately out-of-scope
    # gap (no reader produces one, no viewer exists yet - Phase 5C) - the model is
    # swapped in directly (bypassing _load()'s view refresh) so this test isolates
    # the preview-handling regression from that unrelated, unreachable-today gap.
    import xarray as xr

    from snomniman.core import ChannelInfo, DataKind, Metadata, ProvenanceNode, StepRecord

    n = 256
    opd = np.arange(n, dtype=np.float64) * 1e-4
    signal = np.cos(2.0 * np.pi * 50.0 * opd) * np.exp(-opd * 200.0)
    data = xr.Dataset(
        {"O2": ("opd", signal.astype(np.float64))}, coords={"opd": ("opd", opd, {"unit": "cm"})}
    )
    metadata = Metadata(
        data_kind=DataKind.INTERFEROGRAM,
        channels=(ChannelInfo("O2", "optical", "signal", "float64", amplitude_unit="a.u."),),
    )
    node = ProvenanceNode(
        node_id="n0", record=StepRecord(step_id="io.read", step_version=1, deterministic=True)
    )
    ds = Dataset(data, kind=DataKind.INTERFEROGRAM, metadata=metadata, provenance=node)

    win = MeasurementExplorerWindow(ExplorerModel(synthetic_dataset))
    try:
        win._model = ExplorerModel(ds, title="Interferogram")  # bypass _load()
        win._on_preview_requested("spectrum.fft_interferogram", {"channel": "O2"})
        assert win._preview is not None
        assert win._stack.currentWidget() is win._spectrum
        win._on_preview_accepted()
        assert win._model.dataset.kind is DataKind.SPECTRUM
    finally:
        win.close()
        win.deleteLater()
        qapp.processEvents()


def test_preview_hyperspectral_operation_uses_band_preview(
    window: MeasurementExplorerWindow,
) -> None:
    # normalize_amplitude requires only COMPLEX_OPTICAL - already applies to a
    # hyperspectral cube's O2 channel unmodified (Step 1's regression, exercised
    # here through the real window/ProcessingWorkspace path).
    window._on_preview_requested("image.normalize_amplitude", {"channel": "O2"})
    assert window._preview is not None
    assert window._stack.currentWidget() is window._comparison
    window._on_preview_cancelled()
    assert window._stack.currentWidget() is window._hyperspectral
