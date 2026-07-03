"""Widget-level tests for interactive measurements (skipped without the gui extra).

Headless (offscreen) checks that placing line / rectangle / polygon measurements
produces correct results across visible channels, that the history (rename / hide /
delete) works, that measurements survive a channel change, and that nothing here
ever modifies the Dataset.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import numpy as np
import pytest

from snomniman.core import Dataset
from snomniman.gui.model import ExplorerModel, ProfileSet, RegionReport

pytest.importorskip("PySide6")

from snomniman.gui.window import MeasurementExplorerWindow


@pytest.fixture
def window(qapp: Any, synthetic_dataset: Dataset) -> Iterator[MeasurementExplorerWindow]:
    win = MeasurementExplorerWindow(ExplorerModel(synthetic_dataset))
    win.resize(1100, 720)
    win.show()  # realize the scene so ROI handle positions map to physical coords
    qapp.processEvents()
    yield win
    win.close()
    win.deleteLater()
    qapp.processEvents()


# -- placing measurements ---------------------------------------------------- #


def test_add_line_profiles_every_visible_channel(window: MeasurementExplorerWindow) -> None:
    window._measure.add_line()
    item = window._measure.active
    assert item is not None and item.kind == "line"
    assert isinstance(item.result, ProfileSet)
    # Single-view specs: O2 amplitude (current), O2 phase, Z topography.
    labels = [c.label for c in item.result.curves]
    assert labels == ["O2 amplitude", "O2 phase", "Z"]
    assert item.result.distance_nm > 0.0


def test_add_rectangle_reports_statistics(window: MeasurementExplorerWindow) -> None:
    window._measure.add_rectangle()
    item = window._measure.active
    assert item is not None and isinstance(item.result, RegionReport)
    assert item.result.kind == "rectangle"
    assert item.result.count > 0
    assert item.result.area_nm2 > 0.0
    assert [r.label for r in item.result.rows] == ["O2 amplitude", "O2 phase", "Z"]


def test_add_polygon_reports_statistics(window: MeasurementExplorerWindow) -> None:
    window._measure.add_polygon()
    item = window._measure.active
    assert item is not None and isinstance(item.result, RegionReport)
    assert item.result.kind == "polygon"


def test_adding_a_measurement_focuses_single_view(window: MeasurementExplorerWindow) -> None:
    from snomniman.gui.model import PRESET_AMP_PHASE

    window._show_comparison(PRESET_AMP_PHASE)
    assert window._stack.currentWidget() is window._comparison
    window._measure.add_line()
    assert window._stack.currentWidget() is window._image  # focuses the measurement surface


# -- history (rename / hide / delete) ---------------------------------------- #


def test_history_rename_hide_delete(window: MeasurementExplorerWindow) -> None:
    window._measure.add_line()
    window._measure.add_rectangle()
    assert len(window._measure.items) == 2
    line, rect = window._measure.items

    window._measure.rename(line, "Particle width")
    assert window._measure.items[0].name == "Particle width"

    window._measure.set_visible(rect, False)
    assert rect.visible is False and rect.roi.isVisible() is False

    window._measure.delete(line)
    assert len(window._measure.items) == 1
    window._measure.clear()
    assert window._measure.items == []


# -- robustness -------------------------------------------------------------- #


def test_measurements_survive_channel_change(window: MeasurementExplorerWindow) -> None:
    window._measure.add_line()
    assert window._measure.active is not None
    window._browser.channelSelected.emit("O3")  # change the active channel
    item = window._measure.active
    assert item is not None and isinstance(item.result, ProfileSet)
    # Recomputed for the new channel set (O3 amplitude + O3 phase + Z).
    assert item.result.curves[0].label == "O3 amplitude"


def test_measurements_do_not_modify_dataset(window: MeasurementExplorerWindow) -> None:
    ds = window._model.dataset
    before = {name: ds.channel(name).values.copy() for name in ds.channel_names}
    window._measure.add_line()
    window._measure.add_rectangle()
    window._measure.add_polygon()
    window._measure.refresh()
    for name, arr in before.items():
        np.testing.assert_array_equal(ds.channel(name).values, arr, err_msg=name)
        assert ds.channel(name).data.flags.writeable is False


# --------------------------------------------------------------------------- #
# Spectral ROI measurements (Phase 5B): hyperspectral band-map ROIs report a
# mean spectrum (SpectralRegionReport), not per-channel statistics.
# --------------------------------------------------------------------------- #


@pytest.fixture
def hyperspectral_window(
    qapp: Any, hyperspectral_dataset: Dataset
) -> Iterator[MeasurementExplorerWindow]:
    win = MeasurementExplorerWindow(ExplorerModel(hyperspectral_dataset, title="Cube"))
    win.resize(1100, 720)
    win.show()
    qapp.processEvents()
    yield win
    win.close()
    win.deleteLater()
    qapp.processEvents()


def _place_rectangle(
    window: MeasurementExplorerWindow,
    name: str,
    pos: tuple[float, float],
    size: tuple[float, float],
) -> None:
    new_record = {
        "kind": "rectangle", "name": name, "visible": True,
        "geometry": {"pos": list(pos), "size": list(size)},
    }
    window._measure.load_records([*window._measure.to_records(), new_record])


def test_measure_controller_is_bound_to_the_band_view_in_spectral_mode(
    hyperspectral_window: MeasurementExplorerWindow,
) -> None:
    assert hyperspectral_window._measure.spectral is True
    assert hyperspectral_window._measure._image is hyperspectral_window._hyperspectral.band_view


def test_line_tool_is_hidden_in_spectral_mode(
    hyperspectral_window: MeasurementExplorerWindow,
) -> None:
    # QWidget.isVisible() considers ancestor visibility too, so the Measure tab
    # must be the active one for these checks to reflect our own setVisible calls.
    hyperspectral_window._inspect_tabs.setCurrentWidget(hyperspectral_window._measure_panel)
    assert hyperspectral_window._measure_panel._line_btn.isVisible() is False
    assert hyperspectral_window._measure_panel._overlay_btn.isVisible() is True


def test_add_line_is_a_no_op_in_spectral_mode(
    hyperspectral_window: MeasurementExplorerWindow,
) -> None:
    hyperspectral_window._measure.add_line()
    assert hyperspectral_window._measure.items == []


def test_rectangle_roi_recovers_the_known_resonance(
    hyperspectral_window: MeasurementExplorerWindow,
) -> None:
    # Covers the fixture's known peak pixel (y=2, x=3) at (175, 125) nm.
    _place_rectangle(hyperspectral_window, "ROI A", (100.0, 75.0), (150.0, 100.0))
    item = hyperspectral_window._measure.active
    assert item is not None
    from snomniman.gui.model import SpectralRegionReport

    assert isinstance(item.result, SpectralRegionReport)
    assert item.result.kind == "rectangle"
    assert item.result.count > 0
    assert int(np.argmax(item.result.curve.values)) == 12


def test_polygon_roi_reports_spectral_region(
    hyperspectral_window: MeasurementExplorerWindow,
) -> None:
    from snomniman.gui.model import SpectralRegionReport

    window = hyperspectral_window
    window._measure.load_records([{
        "kind": "polygon", "name": "P1", "visible": True,
        "geometry": {"points": [[50.0, 50.0], [300.0, 50.0], [300.0, 200.0], [50.0, 200.0]]},
    }])
    item = window._measure.active
    assert item is not None and isinstance(item.result, SpectralRegionReport)
    assert item.result.kind == "polygon"


def test_wavenumber_change_does_not_recompute_spectral_roi(
    hyperspectral_window: MeasurementExplorerWindow,
) -> None:
    from snomniman.gui.model import SpectralRegionReport

    _place_rectangle(hyperspectral_window, "ROI A", (100.0, 75.0), (150.0, 100.0))
    item = hyperspectral_window._measure.active
    assert item is not None and isinstance(item.result, SpectralRegionReport)
    before = item.result.curve.values.copy()
    hyperspectral_window._hyperspectral._wavenumber_spin.setValue(5)
    item = hyperspectral_window._measure.active
    assert item is not None and isinstance(item.result, SpectralRegionReport)
    np.testing.assert_array_equal(before, item.result.curve.values)


def test_overlay_roi_spectra_needs_at_least_two(
    hyperspectral_window: MeasurementExplorerWindow,
) -> None:
    _place_rectangle(hyperspectral_window, "ROI A", (100.0, 75.0), (150.0, 100.0))
    assert len(hyperspectral_window._measure.spectral_region_curves()) == 1
    hyperspectral_window._measure_panel._overlay_spectra()
    assert "two or more" in hyperspectral_window._measure_panel._analysis.text()


def test_overlay_roi_spectra_with_two_rois(hyperspectral_window: MeasurementExplorerWindow) -> None:
    _place_rectangle(hyperspectral_window, "ROI A", (100.0, 75.0), (150.0, 100.0))
    _place_rectangle(hyperspectral_window, "ROI B", (0.0, 0.0), (50.0, 50.0))
    curves = hyperspectral_window._measure.spectral_region_curves()
    assert set(curves) == {"ROI A", "ROI B"}
    hyperspectral_window._measure_panel._overlay_spectra()
    assert len(hyperspectral_window._measure_panel._curves) == 2


def test_compare_regions_is_unaffected_in_spectral_mode(
    hyperspectral_window: MeasurementExplorerWindow,
) -> None:
    # "Compare regions" stays exactly as-is (confirmed scope decision): it only
    # ever matches RegionReport results, so it degrades to its existing message.
    _place_rectangle(hyperspectral_window, "ROI A", (100.0, 75.0), (150.0, 100.0))
    _place_rectangle(hyperspectral_window, "ROI B", (0.0, 0.0), (50.0, 50.0))
    assert hyperspectral_window._measure.compare_recent_regions() is None
    hyperspectral_window._measure_panel._compare_regions()
    assert "Place two regions" in hyperspectral_window._measure_panel._analysis.text()


def test_spectral_region_csv_export_has_wavenumber_column(
    hyperspectral_window: MeasurementExplorerWindow,
) -> None:
    _place_rectangle(hyperspectral_window, "ROI A", (100.0, 75.0), (150.0, 100.0))
    text = hyperspectral_window._measure_panel._active_csv(delimiter=",")
    assert text is not None
    assert "wavenumber_cm1" in text
    lines = [line for line in text.splitlines() if not line.startswith("#")]
    assert len(lines) == 26  # header + 25 wavenumber rows


def test_switching_to_hyperspectral_updates_measure_panel_tools(
    window: MeasurementExplorerWindow, hyperspectral_dataset: Dataset
) -> None:
    window._inspect_tabs.setCurrentWidget(window._measure_panel)
    assert window._measure_panel._line_btn.isVisible() is True
    window.add_measurement_model(ExplorerModel(hyperspectral_dataset))
    assert window._measure_panel._line_btn.isVisible() is False
    assert window._measure_panel._overlay_btn.isVisible() is True
    window.switch_to(0)
    assert window._measure_panel._line_btn.isVisible() is True
    assert window._measure_panel._overlay_btn.isVisible() is False


def test_hyperspectral_measurements_do_not_modify_dataset(
    hyperspectral_window: MeasurementExplorerWindow,
) -> None:
    ds = hyperspectral_window._model.dataset
    before = {name: ds.channel(name).values.copy() for name in ds.channel_names}
    _place_rectangle(hyperspectral_window, "ROI A", (100.0, 75.0), (150.0, 100.0))
    hyperspectral_window._measure.refresh()
    for name, arr in before.items():
        np.testing.assert_array_equal(ds.channel(name).values, arr, err_msg=name)
        assert ds.channel(name).data.flags.writeable is False
