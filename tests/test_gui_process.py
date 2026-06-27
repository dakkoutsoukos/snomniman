"""Integration tests for the generic Processing Workspace in the Explorer window.

Covers the registry-driven workspace wiring: the operation catalogue populates the
tree, selecting an operation builds its parameter form, and the
Preview -> Accept/Cancel lifecycle, history navigation, and dataset immutability all
work through one interface for *every* operation (not just plane level). The
backend of the workspace is covered Qt-free in ``test_gui_workspace_model.py``.

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
    """True if the widget was explicitly shown (independent of ancestor visibility)."""
    return not widget.testAttribute(Qt.WidgetAttribute.WA_WState_Hidden)


def _image_group_children(window: MeasurementExplorerWindow) -> list[str]:
    """Step ids listed under the 'Image' group in the workspace tree."""
    tree = window._process._tree
    for i in range(tree.topLevelItemCount()):
        group = tree.topLevelItem(i)
        if group is not None and group.text(0) == "Image":
            children = [group.child(j) for j in range(group.childCount())]
            return [c.data(0, Qt.ItemDataRole.UserRole) for c in children if c is not None]
    return []


@pytest.fixture
def window(qapp: Any, synthetic_dataset: Dataset) -> Iterator[MeasurementExplorerWindow]:
    win = MeasurementExplorerWindow(ExplorerModel(synthetic_dataset))
    yield win
    win.close()
    win.deleteLater()
    qapp.processEvents()


# --------------------------------------------------------------------------- #
# Catalogue discovery + the Process tab
# --------------------------------------------------------------------------- #


def test_workspace_in_inspect_tabs(window: MeasurementExplorerWindow) -> None:
    tabs = window._inspect_tabs
    labels = [tabs.tabText(i) for i in range(tabs.count())]
    assert "Process" in labels


def test_catalog_populates_tree_with_all_operations(window: MeasurementExplorerWindow) -> None:
    children = _image_group_children(window)
    assert {
        "image.crop",
        "image.phase_unwrap",
        "image.plane_level",
        "image.reference_normalize",
    } <= set(children)


def test_selecting_operation_builds_parameter_form(window: MeasurementExplorerWindow) -> None:
    window._on_operation_selected("image.plane_level")
    assert set(window._process._fields) == {"channel", "order"}
    assert window._process.current_params() == {"channel": "Z", "order": 1}


def test_selecting_no_param_operation_builds_empty_form(
    window: MeasurementExplorerWindow,
) -> None:
    window._on_operation_selected("image.reference_normalize")
    assert window._process._fields == {}
    assert window._process.current_params() == {}


def test_unavailable_operation_disables_preview(
    qapp: Any, topography_dataset: Dataset
) -> None:
    win = MeasurementExplorerWindow(ExplorerModel(topography_dataset))
    try:
        win._on_operation_selected("image.reference_normalize")
        # reference_normalize needs complex optical + reference channels Z lacks.
        assert not win._process._preview_btn.isEnabled()
    finally:
        win.close()
        win.deleteLater()
        qapp.processEvents()


# --------------------------------------------------------------------------- #
# Preview: a before/after comparison, identical lifecycle for every operation
# --------------------------------------------------------------------------- #


def test_preview_switches_to_comparison(window: MeasurementExplorerWindow, qapp: Any) -> None:
    window._on_preview_requested("image.plane_level", {"channel": "Z", "order": 1})
    qapp.processEvents()
    assert window._stack.currentWidget() is window._comparison
    assert len(window._comparison.specs) == 2


def test_preview_enters_preview_mode(window: MeasurementExplorerWindow, qapp: Any) -> None:
    window._on_operation_selected("image.plane_level")
    window._on_preview_requested("image.plane_level", {"channel": "Z", "order": 1})
    qapp.processEvents()
    assert _is_shown(window._process._apply_btn)
    assert _is_shown(window._process._cancel_btn)
    assert not window._process._preview_btn.isEnabled()
    assert not window._process._tree.isEnabled()  # catalogue locked during preview
    assert _is_shown(window._process._preview_box)


def test_preview_does_not_change_model(window: MeasurementExplorerWindow, qapp: Any) -> None:
    original_model = window._model
    window._on_preview_requested("image.plane_level", {"channel": "Z", "order": 1})
    qapp.processEvents()
    assert window._model is original_model


def test_preview_failure_shows_warning_and_keeps_state(
    window: MeasurementExplorerWindow, qapp: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        QtWidgets.QMessageBox, "warning", lambda *a, **k: calls.append(a[2] if len(a) > 2 else "")
    )
    original_model = window._model
    # plane_level on a complex channel is invalid -> ProcessingError -> warning.
    window._on_preview_requested("image.plane_level", {"channel": "O2", "order": 1})
    qapp.processEvents()
    assert calls, "a warning should have been shown"
    assert window._model is original_model
    assert window._preview is None


# --------------------------------------------------------------------------- #
# Cancel
# --------------------------------------------------------------------------- #


def test_cancel_restores_single_view(window: MeasurementExplorerWindow, qapp: Any) -> None:
    window._on_preview_requested("image.plane_level", {"channel": "Z", "order": 1})
    window._on_preview_cancelled()
    qapp.processEvents()
    assert window._stack.currentWidget() is window._image
    assert window._preview is None


def test_cancel_does_not_change_model(window: MeasurementExplorerWindow, qapp: Any) -> None:
    original_model = window._model
    window._on_preview_requested("image.plane_level", {"channel": "Z", "order": 1})
    window._on_preview_cancelled()
    qapp.processEvents()
    assert window._model is original_model
    assert not _is_shown(window._process._apply_btn)


# --------------------------------------------------------------------------- #
# Accept: commit the derivation (the original measurement is preserved)
# --------------------------------------------------------------------------- #


def test_accept_commits_new_dataset(window: MeasurementExplorerWindow, qapp: Any) -> None:
    original_ds = window._model.dataset
    window._on_preview_requested("image.plane_level", {"channel": "Z", "order": 2})
    window._on_preview_accepted()
    qapp.processEvents()
    assert window._model.dataset is not original_ds
    assert not window._model.dataset.is_raw
    assert window._model.dataset.provenance.record.step_id == "image.plane_level"
    assert window._model.dataset.provenance.record.params == {"channel": "Z", "order": 2}


def test_accept_returns_to_single_view_and_shows_back(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    window._on_preview_requested("image.plane_level", {"channel": "Z", "order": 1})
    window._on_preview_accepted()
    qapp.processEvents()
    assert window._stack.currentWidget() is window._image
    assert _is_shown(window._back_btn)
    assert not _is_shown(window._process._apply_btn)


def test_navigate_back_restores_original(window: MeasurementExplorerWindow, qapp: Any) -> None:
    original_ds = window._model.dataset
    window._on_preview_requested("image.plane_level", {"channel": "Z", "order": 1})
    window._on_preview_accepted()
    qapp.processEvents()
    window._navigate_back()
    qapp.processEvents()
    assert window._model.dataset is original_ds
    assert len(window._history) == 0
    assert not _is_shown(window._back_btn)


# --------------------------------------------------------------------------- #
# Genericity: the SAME workflow drives non-plane-level operations, no extra wiring
# --------------------------------------------------------------------------- #


def test_phase_unwrap_through_generic_workflow(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    window._on_operation_selected("image.phase_unwrap")
    window._on_preview_requested("image.phase_unwrap", {"channel": "O2"})
    qapp.processEvents()
    assert window._stack.currentWidget() is window._comparison
    window._on_preview_accepted()
    qapp.processEvents()
    assert "O2_phase_unwrapped" in window._model.dataset.channel_names
    assert window._model.dataset.provenance.record.step_id == "image.phase_unwrap"


def test_reference_normalize_through_generic_workflow(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    window._on_operation_selected("image.reference_normalize")
    window._on_preview_requested("image.reference_normalize", {})
    window._on_preview_accepted()
    qapp.processEvents()
    assert window._model.dataset.provenance.record.step_id == "image.reference_normalize"


def test_crop_through_generic_workflow(window: MeasurementExplorerWindow, qapp: Any) -> None:
    window._on_operation_selected("image.crop")
    window._on_preview_requested(
        "image.crop", {"x_min": 0.0, "x_max": 120.0, "y_min": 0.0, "y_max": 120.0}
    )
    window._on_preview_accepted()
    qapp.processEvents()
    assert dict(window._model.dataset.data.sizes) == {"x": 2, "y": 2}
    assert window._model.dataset.provenance.record.step_id == "image.crop"


# --------------------------------------------------------------------------- #
# Cardinal invariant: the original dataset is immutable through the whole workflow
# --------------------------------------------------------------------------- #


def test_original_dataset_immutable_through_accept(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    ds = window._model.dataset
    before = {name: ds.channel(name).values.copy() for name in ds.channel_names}
    window._on_preview_requested("image.plane_level", {"channel": "Z", "order": 1})
    window._on_preview_accepted()
    qapp.processEvents()
    for name, arr in before.items():
        np.testing.assert_array_equal(ds.channel(name).values, arr, err_msg=name)
        assert ds.channel(name).data.flags.writeable is False
