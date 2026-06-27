"""Integration tests for the processing workflow in the Measurement Explorer.

Covers the process panel, before/after preview, accept/cancel, model switching,
history navigation, and the cardinal invariant: the original dataset is never
modified by any derivation.

All tests run headless (offscreen Qt) and skip cleanly when PySide6 is absent.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import numpy as np
import pytest

from snomniman.core import Dataset
from snomniman.gui.model import ExplorerModel

pytest.importorskip("PySide6")

from PySide6 import QtWidgets
from PySide6.QtCore import Qt

from snomniman.gui.window import MeasurementExplorerWindow


def _is_shown(widget: QtWidgets.QWidget) -> bool:
    """Return True if the widget was explicitly shown (setVisible(True) was called).

    Qt's isVisible() requires the full ancestor chain to be visible, so it
    returns False for widgets inside a non-show()n window.  WA_WState_Hidden
    tracks the widget's own explicit hide state independently of its ancestors.
    """
    return not widget.testAttribute(Qt.WidgetAttribute.WA_WState_Hidden)


@pytest.fixture
def window(qapp: Any, synthetic_dataset: Dataset) -> Iterator[MeasurementExplorerWindow]:
    win = MeasurementExplorerWindow(ExplorerModel(synthetic_dataset))
    yield win
    win.close()
    win.deleteLater()
    qapp.processEvents()


# --------------------------------------------------------------------------- #
# Panel existence and population
# --------------------------------------------------------------------------- #


def test_process_panel_exists(window: MeasurementExplorerWindow) -> None:
    assert window._process is not None


def test_process_panel_in_inspect_tabs(window: MeasurementExplorerWindow) -> None:
    tabs = window._inspect_tabs
    labels = [tabs.tabText(i) for i in range(tabs.count())]
    assert "Process" in labels


def test_process_panel_shows_real_channels_only(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    qapp.processEvents()
    combo = window._process._channel_combo
    items = [combo.itemText(i) for i in range(combo.count())]
    assert "Z" in items, "real channel Z must be in the selector"
    # Complex channels must not appear
    for complex_ch in ("O2", "O3", "R_O2", "M1"):
        assert complex_ch not in items, f"complex channel {complex_ch!r} must not appear"


# --------------------------------------------------------------------------- #
# Preview: shows comparison with two labeled panes
# --------------------------------------------------------------------------- #


def test_preview_switches_to_comparison_view(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    window._on_preview_requested("Z", 1)
    qapp.processEvents()
    assert window._stack.currentWidget() is window._comparison


def test_preview_shows_two_panes(window: MeasurementExplorerWindow, qapp: Any) -> None:
    window._on_preview_requested("Z", 1)
    qapp.processEvents()
    assert len(window._comparison.specs) == 2


def test_preview_panes_have_labels(window: MeasurementExplorerWindow, qapp: Any) -> None:
    window._on_preview_requested("Z", 1)
    qapp.processEvents()
    specs = window._comparison.specs
    assert any("original" in (s.label or "") for s in specs)
    assert any("leveled" in (s.label or "") for s in specs)


def test_preview_does_not_change_model(window: MeasurementExplorerWindow, qapp: Any) -> None:
    original_model = window._model
    window._on_preview_requested("Z", 1)
    qapp.processEvents()
    assert window._model is original_model


def test_preview_mode_disables_preview_btn(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    # isEnabled() is reliable regardless of parent visibility; isVisible() is not
    # (it requires the full ancestor chain to be visible — i.e. window.show()).
    window._on_preview_requested("Z", 1)
    qapp.processEvents()
    assert not window._process._preview_btn.isEnabled()


# --------------------------------------------------------------------------- #
# Cancel: discard preview and return to single view
# --------------------------------------------------------------------------- #


def test_cancel_restores_single_view(window: MeasurementExplorerWindow, qapp: Any) -> None:
    window._on_preview_requested("Z", 1)
    qapp.processEvents()
    window._on_preview_cancelled()
    qapp.processEvents()
    assert window._stack.currentWidget() is window._image


def test_cancel_does_not_change_model(window: MeasurementExplorerWindow, qapp: Any) -> None:
    original_model = window._model
    window._on_preview_requested("Z", 1)
    window._on_preview_cancelled()
    qapp.processEvents()
    assert window._model is original_model


def test_cancel_leaves_no_preview_ds(window: MeasurementExplorerWindow, qapp: Any) -> None:
    window._on_preview_requested("Z", 1)
    window._on_preview_cancelled()
    qapp.processEvents()
    assert window._preview_ds is None


def test_cancel_restores_preview_btn(window: MeasurementExplorerWindow, qapp: Any) -> None:
    window._on_preview_requested("Z", 1)
    window._on_preview_cancelled()
    qapp.processEvents()
    assert window._process._preview_btn.isEnabled()
    assert not window._process._apply_btn.isVisible()


# --------------------------------------------------------------------------- #
# Accept: commit the derivation
# --------------------------------------------------------------------------- #


def test_accept_updates_model(window: MeasurementExplorerWindow, qapp: Any) -> None:
    original_ds = window._model.dataset
    window._on_preview_requested("Z", 1)
    window._on_preview_accepted()
    qapp.processEvents()
    assert window._model.dataset is not original_ds


def test_accepted_model_is_not_raw(window: MeasurementExplorerWindow, qapp: Any) -> None:
    window._on_preview_requested("Z", 1)
    window._on_preview_accepted()
    qapp.processEvents()
    assert not window._model.dataset.is_raw


def test_accepted_model_provenance_records_step(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    window._on_preview_requested("Z", 1)
    window._on_preview_accepted()
    qapp.processEvents()
    assert window._model.dataset.provenance.record.step_id == "image.plane_level"


def test_accepted_model_provenance_params(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    window._on_preview_requested("Z", 2)
    window._on_preview_accepted()
    qapp.processEvents()
    params = window._model.dataset.provenance.record.params
    assert params["channel"] == "Z"
    assert params["order"] == 2


def test_accept_returns_to_single_view(window: MeasurementExplorerWindow, qapp: Any) -> None:
    window._on_preview_requested("Z", 1)
    window._on_preview_accepted()
    qapp.processEvents()
    assert window._stack.currentWidget() is window._image


def test_accept_restores_preview_btn(window: MeasurementExplorerWindow, qapp: Any) -> None:
    window._on_preview_requested("Z", 1)
    window._on_preview_accepted()
    qapp.processEvents()
    assert window._process._preview_btn.isEnabled()
    assert not window._process._apply_btn.isVisible()


# --------------------------------------------------------------------------- #
# Navigation: back button and history
# --------------------------------------------------------------------------- #


def test_back_button_hidden_initially(window: MeasurementExplorerWindow) -> None:
    assert not _is_shown(window._back_btn)


def test_back_button_appears_after_accept(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    window._on_preview_requested("Z", 1)
    window._on_preview_accepted()
    qapp.processEvents()
    assert _is_shown(window._back_btn)


def test_back_button_label_names_previous(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    original_title = window._model.title
    window._on_preview_requested("Z", 1)
    window._on_preview_accepted()
    qapp.processEvents()
    assert original_title in window._back_btn.text()


def test_navigate_back_restores_original_model(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    original_ds = window._model.dataset
    window._on_preview_requested("Z", 1)
    window._on_preview_accepted()
    qapp.processEvents()
    window._navigate_back()
    qapp.processEvents()
    assert window._model.dataset is original_ds


def test_navigate_back_hides_back_button(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    window._on_preview_requested("Z", 1)
    window._on_preview_accepted()
    qapp.processEvents()
    window._navigate_back()
    qapp.processEvents()
    assert not _is_shown(window._back_btn)


def test_history_empty_after_back(window: MeasurementExplorerWindow, qapp: Any) -> None:
    window._on_preview_requested("Z", 1)
    window._on_preview_accepted()
    qapp.processEvents()
    window._navigate_back()
    qapp.processEvents()
    assert len(window._history) == 0


# --------------------------------------------------------------------------- #
# Cardinal invariant: original dataset is immutable through the whole workflow
# --------------------------------------------------------------------------- #


def test_original_dataset_immutable_through_accept(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    ds = window._model.dataset
    before = {name: ds.channel(name).values.copy() for name in ds.channel_names}
    window._on_preview_requested("Z", 1)
    window._on_preview_accepted()
    qapp.processEvents()
    for name, arr in before.items():
        np.testing.assert_array_equal(ds.channel(name).values, arr, err_msg=name)
        assert ds.channel(name).data.flags.writeable is False


def test_original_dataset_immutable_after_back(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    ds = window._model.dataset
    before = {name: ds.channel(name).values.copy() for name in ds.channel_names}
    window._on_preview_requested("Z", 1)
    window._on_preview_accepted()
    window._navigate_back()
    qapp.processEvents()
    for name, arr in before.items():
        np.testing.assert_array_equal(ds.channel(name).values, arr, err_msg=name)
        assert ds.channel(name).data.flags.writeable is False
