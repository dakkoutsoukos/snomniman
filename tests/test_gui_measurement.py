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
