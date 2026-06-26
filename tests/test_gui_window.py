"""Widget-level smoke tests for the Measurement Explorer.

The whole module skips cleanly when PySide6 is not installed (the ``gui`` extra),
so CI without Qt is unaffected. With Qt present it runs headless (offscreen, set
in ``conftest.py``) and verifies the read-only experience end-to-end: the window
builds, channel switching and the amplitude/phase toggle drive the view, the
cursor readout updates, and - crucially - exploring never modifies the Dataset.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from snomniman.core import Dataset
from snomniman.gui.model import ExplorerModel
from snomniman.viz import PHASE

pytest.importorskip("PySide6")

from snomniman.gui.window import MeasurementExplorerWindow


@pytest.fixture
def window(qapp: Any, synthetic_dataset: Dataset) -> MeasurementExplorerWindow:
    return MeasurementExplorerWindow(ExplorerModel(synthetic_dataset))


def test_window_builds_and_shows_default_channel(window: MeasurementExplorerWindow) -> None:
    assert "Measurement Explorer" in window.windowTitle()
    assert window._model.current_channel == "O2"
    assert window._image._image.image is not None  # an image is on screen


def test_channel_switch_updates_view(window: MeasurementExplorerWindow) -> None:
    window._browser.channelSelected.emit("Z")
    assert window._model.current_channel == "Z"
    assert window._model.current_representation == "real"
    assert window._image._image.image is not None


def test_representation_toggle(window: MeasurementExplorerWindow) -> None:
    window._browser.representationSelected.emit(PHASE)
    assert window._model.current_representation == PHASE
    assert window._model.render().cyclic is True


def test_cursor_readout_updates_status(window: MeasurementExplorerWindow) -> None:
    x0, x1, y0, y1 = window._model.render().extent_nm
    window._on_cursor_moved((x0 + x1) / 2, (y0 + y1) / 2, True)
    assert window._readout.text() != ""
    window._on_cursor_moved(x1 + 1e6, (y0 + y1) / 2, False)
    assert window._readout.text() == ""


def test_app_entry_point_importable(qapp: Any) -> None:
    from snomniman.gui import app

    assert callable(app.run)


def test_window_does_not_modify_dataset(window: MeasurementExplorerWindow) -> None:
    ds = window._model.dataset
    before = {name: ds.channel(name).values.copy() for name in ds.channel_names}
    window._browser.channelSelected.emit("Z")
    window._browser.channelSelected.emit("O3")
    window._browser.representationSelected.emit(PHASE)
    for name, arr in before.items():
        np.testing.assert_array_equal(ds.channel(name).values, arr, err_msg=name)
        assert ds.channel(name).data.flags.writeable is False
