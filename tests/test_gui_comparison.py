"""Widget-level tests for comparative exploration (skipped without the gui extra).

Headless (offscreen) checks that side-by-side comparison renders the right panes,
shares zoom/pan/cursor across them, the contact sheet builds and navigates, and -
crucially - none of it modifies the Dataset.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from snomniman.core import Dataset
from snomniman.gui.model import (
    PRESET_AMP_PHASE,
    PRESET_HARMONIC_SERIES,
    PRESET_OPTICAL_TOPO,
    ExplorerModel,
)

pytest.importorskip("PySide6")

from snomniman.gui.window import MeasurementExplorerWindow


@pytest.fixture
def window(qapp: Any, synthetic_dataset: Dataset) -> MeasurementExplorerWindow:
    return MeasurementExplorerWindow(ExplorerModel(synthetic_dataset))


# -- side-by-side panes ------------------------------------------------------ #


def test_comparison_builds_correct_panes(window: MeasurementExplorerWindow) -> None:
    window._show_comparison(PRESET_AMP_PHASE)
    assert window._stack.currentWidget() is window._comparison
    titles = [s.title for s in window._comparison.specs]
    assert titles == ["O2 amplitude", "O2 phase"]
    assert len(window._comparison.panes) == 2


def test_optical_topography_pairing(window: MeasurementExplorerWindow) -> None:
    window._show_comparison(PRESET_OPTICAL_TOPO)
    assert [s.channel for s in window._comparison.specs] == ["O2", "Z"]


def test_synchronized_zoom_and_pan(window: MeasurementExplorerWindow) -> None:
    window._show_comparison(PRESET_AMP_PHASE)
    panes = window._comparison.panes
    # Zoom/pan one pane; the linked pane must follow (shared ViewBox range).
    box0 = panes[0]._plot.getViewBox()
    box1 = panes[1]._plot.getViewBox()
    box0.setXRange(20.0, 80.0, padding=0)
    np.testing.assert_allclose(box1.viewRange()[0], box0.viewRange()[0], rtol=1e-6)


def test_synchronized_cursor_marks_all_panes(window: MeasurementExplorerWindow) -> None:
    window._show_comparison(PRESET_AMP_PHASE)
    rd = window._model.render_spec(window._comparison.specs[0])
    x0, x1, y0, y1 = rd.extent_nm
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    window._on_comparison_cursor(cx, cy, True)
    # Every pane shows the crosshair at the shared point, and the readout lists
    # a value per visible channel.
    for pane in window._comparison.panes:
        assert pane._vline.isVisible() and pane._hline.isVisible()
        assert pane._vline.value() == pytest.approx(cx)
    assert "O2 amplitude" in window._comparison._last_readout
    assert "O2 phase" in window._comparison._last_readout
    # Leaving the field hides the crosshair and clears the readout.
    window._on_comparison_cursor(x1 + 1e6, cy, False)
    assert window._comparison._last_readout == ""
    assert not window._comparison.panes[0]._vline.isVisible()


# -- contact sheet ----------------------------------------------------------- #


def test_contact_sheet_builds_and_navigates(window: MeasurementExplorerWindow) -> None:
    window._show_contact()
    assert window._stack.currentWidget() is window._contact
    thumbs = window._contact.thumbnails
    assert len(thumbs) == 2  # synthetic dataset has optical O2, O3
    # Clicking a thumbnail selects that channel and returns to the single view.
    thumbs[1].clicked.emit("O3")
    assert window._model.current_channel == "O3"
    assert window._stack.currentWidget() is window._image


def test_harmonic_series_grid(window: MeasurementExplorerWindow) -> None:
    window._show_comparison(PRESET_HARMONIC_SERIES)
    assert [s.channel for s in window._comparison.specs] == ["O2", "O3"]


# -- read-only guarantee ----------------------------------------------------- #


def test_comparison_does_not_modify_dataset(window: MeasurementExplorerWindow) -> None:
    ds = window._model.dataset
    before = {name: ds.channel(name).values.copy() for name in ds.channel_names}
    for preset in (PRESET_AMP_PHASE, PRESET_OPTICAL_TOPO, PRESET_HARMONIC_SERIES):
        window._show_comparison(preset)
        window._on_comparison_cursor(25.0, 25.0, True)
    window._show_contact()
    for name, arr in before.items():
        np.testing.assert_array_equal(ds.channel(name).values, arr, err_msg=name)
        assert ds.channel(name).data.flags.writeable is False


def test_returns_to_single_view(window: MeasurementExplorerWindow) -> None:
    window._show_comparison(PRESET_AMP_PHASE)
    window._show_single()
    assert window._stack.currentWidget() is window._image
