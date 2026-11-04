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
from snomniman.viz import LineshapeFit, fit_lineshape

pytest.importorskip("PySide6")

from PySide6 import QtWidgets

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


# --------------------------------------------------------------------------- #
# Dual wavenumber/wavelength axis (Phase 6 stage 3,
# docs/phase6-spectral-lineshape-analysis.md sec 3.5)
# --------------------------------------------------------------------------- #


def test_top_axis_is_the_wavelength_conversion(qapp: Any) -> None:
    view = SpectrumPlotView()
    top = view._plot.getAxis("top")
    assert top.labelText == "wavelength"
    # Same tick *positions* as wavenumber (shared ViewBox); only the label text
    # is the nonlinear 1e4/wavenumber conversion.
    assert top.tickStrings([2000.0, 5000.0], 1.0, 1.0) == ["5.00", "2.00"]
    assert top.tickStrings([0.0], 1.0, 1.0) == [""]


# --------------------------------------------------------------------------- #
# Lineshape fitting interaction (Phase 6 stage 3,
# docs/phase6-spectral-lineshape-analysis.md sec 3.3-3.4)
# --------------------------------------------------------------------------- #


def _lorentzian_curve() -> SpectrumCurve:
    wn = np.arange(5800.0, 6401.0, 1.0)
    lorentzian = 2.0 / (1.0 + ((wn - 6095.0) / (42.4 / 2.0)) ** 2)
    return SpectrumCurve(
        channel="O2_ratio", representation="amplitude", wavenumber_cm1=wn,
        values=lorentzian + 1.0, unit="a.u.", cyclic=False,
    )


def _fit_result(curve: SpectrumCurve, window: tuple[float, float]) -> LineshapeFit:
    return fit_lineshape(curve.wavenumber_cm1, curve.values, window=window, unit=curve.unit)


def test_fit_checkbox_shows_a_default_window_region(qapp: Any) -> None:
    view = SpectrumPlotView()
    view.show_curve(_lorentzian_curve())
    assert view.fit_window_bounds() is None
    assert view._fit_btn.isHidden() is True
    view._fit_checkbox.setChecked(True)
    bounds = view.fit_window_bounds()
    assert bounds is not None
    lo, hi = bounds
    assert 5800.0 <= lo < hi <= 6401.0
    assert view._fit_btn.isHidden() is False


def test_unchecking_fit_removes_the_region_and_result(qapp: Any) -> None:
    view = SpectrumPlotView()
    curve = _lorentzian_curve()
    view.show_curve(curve)
    view._fit_checkbox.setChecked(True)
    view.show_fit(_fit_result(curve, (5900.0, 6300.0)))
    assert view._residual_plot.isHidden() is False
    view._fit_checkbox.setChecked(False)
    assert view.fit_window_bounds() is None
    assert view._residual_plot.isHidden() is True
    assert view._fit_readout.text() == ""


def test_fit_button_emits_fit_requested_with_the_window_bounds(qapp: Any) -> None:
    view = SpectrumPlotView()
    view.show_curve(_lorentzian_curve())
    view._fit_checkbox.setChecked(True)
    view._fit_region.setRegion((5900.0, 6300.0))
    received: list[tuple[float, float]] = []
    view.fitRequested.connect(lambda lo, hi: received.append((lo, hi)))
    view._fit_btn.click()
    assert len(received) == 1
    assert received[0] == pytest.approx((5900.0, 6300.0))


def test_show_fit_populates_curve_residual_and_readout(qapp: Any) -> None:
    view = SpectrumPlotView()
    curve = _lorentzian_curve()
    view.show_curve(curve)
    view._fit_checkbox.setChecked(True)
    result = _fit_result(curve, (5900.0, 6300.0))
    view.show_fit(result)
    assert view._fit_curve_item is not None
    fit_x, fit_y = view._fit_curve_item.getData()
    np.testing.assert_allclose(fit_x, result.wavenumber_cm1)
    np.testing.assert_allclose(fit_y, result.fit_curve)
    _residual_x, residual_y = view._residual_curve.getData()
    np.testing.assert_allclose(residual_y, result.residuals)
    assert view._residual_plot.isHidden() is False
    assert "Lorentzian fit" in view._fit_readout.text()
    assert f"{result.center:.1f}" in view._fit_readout.text()


def test_new_curve_clears_the_fit_result_but_keeps_the_window(qapp: Any) -> None:
    view = SpectrumPlotView()
    curve = _lorentzian_curve()
    view.show_curve(curve)
    view._fit_checkbox.setChecked(True)
    view.show_fit(_fit_result(curve, (5900.0, 6300.0)))
    bounds_before = view.fit_window_bounds()

    view.show_curve(_lorentzian_curve())  # e.g. a channel/position switch

    assert view._fit_curve_item is None
    assert view._residual_plot.isHidden() is True
    assert view._fit_readout.text() == ""
    assert view.fit_window_bounds() == pytest.approx(bounds_before)


def test_window_wires_fit_requested_to_the_model(window: MeasurementExplorerWindow) -> None:
    curve = window._model.spectrum_curve(position_index=0)
    lo, hi = float(curve.wavenumber_cm1[5]), float(curve.wavenumber_cm1[-5])
    window._on_spectrum_fit_requested(lo, hi)
    assert window._spectrum._fit_readout.text() != ""
    assert window._spectrum._fit_curve_item is not None


def test_window_shows_a_message_instead_of_crashing_for_a_too_narrow_window(
    window: MeasurementExplorerWindow, monkeypatch: Any
) -> None:
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *a, **k: None)
    curve = window._model.spectrum_curve(position_index=0)
    lo, hi = float(curve.wavenumber_cm1[0]), float(curve.wavenumber_cm1[1])
    window._on_spectrum_fit_requested(lo, hi)  # must not raise
    assert window._spectrum._fit_readout.text() == ""


# --------------------------------------------------------------------------- #
# The Explorer's one active lineshape fit, for reporting (Phase 6 stage 4,
# docs/phase6-spectral-lineshape-analysis.md sec 4 - no history, by design)
# --------------------------------------------------------------------------- #


def test_window_tracks_the_active_lineshape_fit(window: MeasurementExplorerWindow) -> None:
    assert window._active_lineshape_fit is None
    curve = window._model.spectrum_curve(position_index=0)
    lo, hi = float(curve.wavenumber_cm1[5]), float(curve.wavenumber_cm1[-5])
    window._on_spectrum_fit_requested(lo, hi)
    assert window._active_lineshape_fit is not None
    title, label, result = window._active_lineshape_fit
    assert title == window._model.title
    assert label == curve.label
    assert result.window == (lo, hi)


def test_changing_position_clears_the_active_lineshape_fit(
    window: MeasurementExplorerWindow,
) -> None:
    curve = window._model.spectrum_curve(position_index=0)
    lo, hi = float(curve.wavenumber_cm1[5]), float(curve.wavenumber_cm1[-5])
    window._on_spectrum_fit_requested(lo, hi)
    assert window._active_lineshape_fit is not None

    window._spectrum._position_spin.setValue(3)  # a new curve is now displayed

    assert window._active_lineshape_fit is None


def test_build_report_model_includes_the_active_fit(window: MeasurementExplorerWindow) -> None:
    curve = window._model.spectrum_curve(position_index=0)
    lo, hi = float(curve.wavenumber_cm1[5]), float(curve.wavenumber_cm1[-5])
    window._on_spectrum_fit_requested(lo, hi)

    report = window._build_report_model().experiment_report()

    assert "Spectral peak fit (active)" in [s.title for s in report.sections]
