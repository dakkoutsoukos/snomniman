"""Widget-level smoke tests for the Measurement Explorer.

The whole module skips cleanly when PySide6 is not installed (the ``gui`` extra),
so CI without Qt is unaffected. With Qt present it runs headless (offscreen, set
in ``conftest.py``) and verifies the read-only experience end-to-end: the window
builds, channel switching and the amplitude/phase toggle drive the view, the
quantitative visualization (colorbar/levels/contrast) reflects the active channel,
the cursor readout updates, and - crucially - neither exploring nor adjusting
contrast ever modifies the Dataset.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from snomniman.core import Dataset
from snomniman.gui.model import PRESET_AMP_PHASE, ExplorerModel
from snomniman.viz import PHASE

pytest.importorskip("PySide6")

from snomniman.gui.window import MeasurementExplorerWindow


@pytest.fixture
def window(qapp: Any, synthetic_dataset: Dataset) -> Iterator[MeasurementExplorerWindow]:
    win = MeasurementExplorerWindow(ExplorerModel(synthetic_dataset))
    yield win
    win.close()
    win.deleteLater()
    qapp.processEvents()  # delete widgets now, not chaotically at interpreter exit


# -- structure + navigation -------------------------------------------------- #


def test_window_builds_and_shows_default_channel(window: MeasurementExplorerWindow) -> None:
    assert "Measurement Explorer" in window.windowTitle()
    assert window._model.current_channel == "O2"
    assert window._image._image_item.image is not None  # an image is on screen


def test_channel_switch_updates_view(window: MeasurementExplorerWindow) -> None:
    window._browser.channelSelected.emit("Z")
    assert window._model.current_channel == "Z"
    assert window._model.current_representation == "real"
    assert window._image._image_item.image is not None


def test_representation_toggle(window: MeasurementExplorerWindow) -> None:
    window._browser.representationSelected.emit(PHASE)
    assert window._model.current_representation == PHASE
    assert window._model.render().cyclic is True


# -- quantitative visualization (colorbar / levels / contrast) --------------- #


def test_levels_match_channel_default_on_load(window: MeasurementExplorerWindow) -> None:
    rd = window._model.render()
    assert window._image.levels == pytest.approx((rd.vmin, rd.vmax))
    # A colormap LUT is applied, so the colorbar shows the right value->color map.
    assert window._image._image_item.lut is not None


def test_switching_channel_updates_levels(window: MeasurementExplorerWindow) -> None:
    amplitude_levels = window._image.levels
    window._browser.channelSelected.emit("Z")  # topography: a different value scale
    z_rd = window._model.render()
    assert window._image.levels == pytest.approx((z_rd.vmin, z_rd.vmax))
    assert window._image.levels != amplitude_levels


def test_full_range_widens_then_default_restores(window: MeasurementExplorerWindow) -> None:
    default = window._image.levels
    window._image._reset_full()
    full = window._image.levels
    assert full[0] <= default[0] + 1e-9
    assert full[1] >= default[1] - 1e-9
    window._image._reset_default()
    assert window._image.levels == pytest.approx(default)


def test_manual_levels_apply(window: MeasurementExplorerWindow) -> None:
    window._image._apply_levels(0.25, 0.75)
    assert window._image.levels == pytest.approx((0.25, 0.75))


def test_contrast_change_does_not_modify_dataset(window: MeasurementExplorerWindow) -> None:
    ds = window._model.dataset
    before = {name: ds.channel(name).values.copy() for name in ds.channel_names}
    window._image._reset_full()
    window._image._apply_levels(0.1, 0.2)  # arbitrary display-only levels
    for name, arr in before.items():
        np.testing.assert_array_equal(ds.channel(name).values, arr, err_msg=name)
        assert ds.channel(name).data.flags.writeable is False


# -- cursor readout ---------------------------------------------------------- #


def test_cursor_readout_appears_under_image(window: MeasurementExplorerWindow) -> None:
    x0, x1, y0, y1 = window._model.render().extent_nm
    window._on_cursor_moved((x0 + x1) / 2, (y0 + y1) / 2, True)
    assert window._image._last_readout != ""
    assert "x =" in window._image._last_readout
    window._on_cursor_moved(x1 + 1e6, (y0 + y1) / 2, False)
    assert window._image._last_readout == ""


# -- entry point + the cardinal invariant ------------------------------------ #


def test_app_entry_point_importable(qapp: Any) -> None:
    from snomniman.gui import app

    assert callable(app.run)


# -- publication export ------------------------------------------------------ #


def test_figure_inputs_track_the_view_mode(window: MeasurementExplorerWindow) -> None:
    kind, panels, _ = window._figure_inputs()
    assert kind == "single" and len(panels) == 1
    window._show_comparison(PRESET_AMP_PHASE)
    kind, panels, _ = window._figure_inputs()
    assert kind == "comparison" and len(panels) == 2  # O2 amplitude + O2 phase


def test_export_writes_figure_and_provenance(
    window: MeasurementExplorerWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6 import QtWidgets

    out = tmp_path / "figure.png"
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: (str(out), "PNG (*.png)")
    )
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *a, **k: None)
    window._export_figure()
    assert out.exists() and out.stat().st_size > 0
    assert (tmp_path / "figure.png.provenance.json").exists()


def test_window_does_not_modify_dataset(window: MeasurementExplorerWindow) -> None:
    ds = window._model.dataset
    before = {name: ds.channel(name).values.copy() for name in ds.channel_names}
    window._browser.channelSelected.emit("Z")
    window._browser.channelSelected.emit("O3")
    window._browser.representationSelected.emit(PHASE)
    for name, arr in before.items():
        np.testing.assert_array_equal(ds.channel(name).values, arr, err_msg=name)
        assert ds.channel(name).data.flags.writeable is False
