"""Widget-level smoke tests for the point-spectroscopy Explorer experience.

Skips cleanly without the ``gui`` extra (mirrors ``test_gui_window.py``). With Qt
present it runs headless (offscreen) and verifies: opening a spectral measurement
shows the spectrum plot page (not the image view), channel/representation/position
switching drive the curve, the image-only affordances (comparison/contact sheet)
are disabled rather than reachable-and-crashing, switching between a spectral and
an imaging session in one window works, and nothing ever mutates the Dataset.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import numpy as np
import pytest

from snomniman.core import Dataset
from snomniman.gui.model import ExplorerModel

pytest.importorskip("PySide6")

from snomniman.gui.model import SpectrumCurve
from snomniman.gui.spectrumview import SpectrumPlotView
from snomniman.gui.window import MeasurementExplorerWindow


@pytest.fixture
def window(qapp: Any, spectrum_dataset: Dataset) -> Iterator[MeasurementExplorerWindow]:
    win = MeasurementExplorerWindow(ExplorerModel(spectrum_dataset))
    yield win
    win.close()
    win.deleteLater()
    qapp.processEvents()


def test_window_opens_directly_into_the_spectrum_view(
    window: MeasurementExplorerWindow,
) -> None:
    assert window._stack.currentWidget() is window._spectrum
    assert window._stack.currentWidget() is not window._image
    assert "position 1/6" in window._active.text()


def test_position_selector_is_shown_for_a_multi_position_line_scan(
    window: MeasurementExplorerWindow,
) -> None:
    assert window._spectrum._position_row.isHidden() is False


def test_image_only_buttons_are_disabled(window: MeasurementExplorerWindow) -> None:
    assert window._image_only_buttons  # the fixture actually built some
    assert all(not b.isEnabled() for b in window._image_only_buttons)


def test_channel_selection_updates_the_curve(window: MeasurementExplorerWindow) -> None:
    window._on_channel_selected("Z")
    assert window._model.current_channel == "Z"
    assert "Showing   Z" in window._active.text()


def test_representation_toggle_updates_the_curve(window: MeasurementExplorerWindow) -> None:
    window._on_representation_selected("phase")
    assert window._model.current_representation == "phase"
    assert "O2 phase" in window._active.text()


def test_position_change_updates_the_curve(window: MeasurementExplorerWindow) -> None:
    curve_before = window._model.spectrum_curve(position_index=0)
    window._spectrum._position_spin.setValue(3)
    assert "position 4/6" in window._active.text()
    curve_after = window._model.spectrum_curve(position_index=3)
    assert not np.allclose(curve_before.values, curve_after.values)


_SINGLE_POINT_SPECTRA_TXT = """# www.neaspec.com
# Scan:\t \tPoint Spectroscopy (PsHet)
# Pixel Area (X, Y, Z):\t[px]\t1\t1\t3
Row\tColumn\tOmega\tWavenumber\tZ\tO0A\tO0P\t
0\t0\t0\t5920 \t8.0E-07\t64.5\t0\t
0\t0\t1\t5921 \t8.1E-07\t63.1\t0\t
0\t0\t2\t5922 \t8.2E-07\t78.1\t0\t
"""


def test_single_position_hides_the_position_selector(qapp: Any, tmp_path: Any) -> None:
    from snomniman.io.neasnom_spectrum import read_neasnom_spectrum_measurement

    d = tmp_path / "single"
    d.mkdir()
    (d / "single Spectra.txt").write_text(_SINGLE_POINT_SPECTRA_TXT, encoding="utf-8")
    ds = read_neasnom_spectrum_measurement(d)
    win = MeasurementExplorerWindow(ExplorerModel(ds))
    try:
        assert win._stack.currentWidget() is win._spectrum
        assert win._spectrum._position_row.isHidden() is True
        assert "position" not in win._active.text()
    finally:
        win.close()
        win.deleteLater()
        qapp.processEvents()


def test_switching_between_spectral_and_image_sessions(
    window: MeasurementExplorerWindow, synthetic_dataset: Dataset
) -> None:
    window.add_measurement_model(ExplorerModel(synthetic_dataset))
    assert window._stack.currentWidget() is window._image
    assert all(b.isEnabled() for b in window._image_only_buttons)

    window.switch_to(0)
    assert window._stack.currentWidget() is window._spectrum
    assert all(not b.isEnabled() for b in window._image_only_buttons)


def test_metadata_and_provenance_panels_populate_without_crashing(
    window: MeasurementExplorerWindow,
) -> None:
    sections = {s.title for s in window._model.metadata_sections()}
    assert "Spectral axis" in sections
    assert window._model.provenance_summary() != ""


def test_briefing_populates_without_crashing(window: MeasurementExplorerWindow) -> None:
    briefing = window._model.scientific_briefing()
    assert len(briefing.sections) == 3


def test_window_never_mutates_the_dataset(
    window: MeasurementExplorerWindow, spectrum_dataset: Dataset
) -> None:
    before = {n: spectrum_dataset.channel(n).values.copy() for n in spectrum_dataset.channel_names}
    window._on_channel_selected("Z")
    window._on_representation_selected("real")
    window._spectrum._position_spin.setValue(2)
    window._on_channel_selected("O2")
    window._on_representation_selected("phase")
    for name, values in before.items():
        np.testing.assert_array_equal(spectrum_dataset.channel(name).values, values)


# --------------------------------------------------------------------------- #
# Multi-curve overlay (Phase 5B: SpectrumPlotView.show_curves), tested directly
# against the widget - no window needed for this isolated capability.
# --------------------------------------------------------------------------- #


def _curve(label_amplitude: float, *, cyclic: bool = False) -> SpectrumCurve:
    wn = np.linspace(1700.0, 1750.0, 10)
    values = np.full(10, label_amplitude) if not cyclic else np.linspace(-3.0, 3.0, 10)
    return SpectrumCurve(
        channel="O2", representation="amplitude", wavenumber_cm1=wn, values=values,
        unit="a.u.", cyclic=cyclic,
    )


def test_show_curves_adds_one_item_per_curve(qapp: Any) -> None:
    view = SpectrumPlotView()
    view.show_curves({"ROI A": _curve(1.0), "ROI B": _curve(2.0)})
    assert len(view._overlay_items) == 2
    qapp.processEvents()


def test_show_curves_replaces_not_accumulates(qapp: Any) -> None:
    view = SpectrumPlotView()
    view.show_curves({"ROI A": _curve(1.0), "ROI B": _curve(2.0)})
    view.show_curves({"ROI C": _curve(3.0)})
    assert len(view._overlay_items) == 1


def test_show_curves_uses_distinct_colors(qapp: Any) -> None:
    view = SpectrumPlotView()
    view.show_curves({"ROI A": _curve(1.0), "ROI B": _curve(2.0), "ROI C": _curve(3.0)})
    pens = [item.opts["pen"] for item in view._overlay_items]
    colors = {pen.color().name() for pen in pens}
    assert len(colors) == 3  # every curve gets a distinct color


def test_show_curve_still_works_standalone(qapp: Any) -> None:
    view = SpectrumPlotView()
    view.show_curve(_curve(5.0))
    _, y = view._curve_item.getData()
    np.testing.assert_allclose(y, 5.0)
    assert view._overlay_items == []


def test_show_curve_after_show_curves_clears_overlays(qapp: Any) -> None:
    view = SpectrumPlotView()
    view.show_curves({"ROI A": _curve(1.0), "ROI B": _curve(2.0)})
    view.show_curve(_curve(9.0))
    assert view._overlay_items == []
    _, y = view._curve_item.getData()
    np.testing.assert_allclose(y, 9.0)


def test_show_curves_single_entry_matches_show_curve_y_range(qapp: Any) -> None:
    view_curves = SpectrumPlotView()
    view_curves.show_curves({"ROI A": _curve(1.0, cyclic=True)})
    view_single = SpectrumPlotView()
    view_single.show_curve(_curve(1.0, cyclic=True))
    assert view_curves._plot.getViewBox().viewRange()[1] == pytest.approx(
        view_single._plot.getViewBox().viewRange()[1]
    )


def test_show_curves_empty_mapping_clears_the_plot(qapp: Any) -> None:
    view = SpectrumPlotView()
    view.show_curve(_curve(1.0))
    view.show_curves({})
    x, _ = view._curve_item.getData()
    assert x is None or len(x) == 0
    assert view._overlay_items == []
