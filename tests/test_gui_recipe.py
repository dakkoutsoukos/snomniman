"""Integration tests for Processing Recipes (Phase 4A) in the Explorer window.

Covers the recipe half of the Processing Workspace: capturing the active
measurement's history as a named recipe, saving/loading it as a ``.snomrecipe``
file, browsing it in the same operation tree ("Recipes" group), inspecting its
steps, and replaying it through the identical Preview -> Accept/Cancel lifecycle
every operation already uses (no second processing interface). File dialogs are
bypassed by calling the private, directly-testable handlers the dialog-driven
methods delegate to (mirroring the project save/open tests' convention).

All tests run headless (offscreen Qt) and skip cleanly when PySide6 is absent.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
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


@pytest.fixture
def window(qapp: Any, topography_dataset: Dataset) -> Iterator[MeasurementExplorerWindow]:
    win = MeasurementExplorerWindow(ExplorerModel(topography_dataset))
    yield win
    win.close()
    win.deleteLater()
    qapp.processEvents()


def _recipes_group_children(window: MeasurementExplorerWindow) -> list[str]:
    tree = window._process._tree
    for i in range(tree.topLevelItemCount()):
        group = tree.topLevelItem(i)
        if group is not None and group.text(0) == "Recipes":
            children = [group.child(j) for j in range(group.childCount())]
            return [c.text(0) for c in children if c is not None]
    return []


def _build_history(window: MeasurementExplorerWindow, qapp: Any) -> None:
    """Manually apply plane_level -> fix_zero, one Preview/Accept at a time."""
    window._on_preview_requested("image.plane_level", {"channel": "Z", "order": 1})
    qapp.processEvents()
    window._on_preview_accepted()
    window._on_preview_requested("image.fix_zero", {"channel": "Z"})
    qapp.processEvents()
    window._on_preview_accepted()


# --------------------------------------------------------------------------- #
# Create + save
# --------------------------------------------------------------------------- #


def test_save_recipe_captures_history_and_registers_it(
    window: MeasurementExplorerWindow, qapp: Any, tmp_path: Path
) -> None:
    _build_history(window, qapp)
    window._write_recipe("topo clean", tmp_path / "topo.snomrecipe")
    assert "topo clean" in window._recipes
    assert (tmp_path / "topo.snomrecipe").is_file()
    assert [s.step_id for s in window._recipes["topo clean"].steps] == [
        "image.plane_level",
        "image.fix_zero",
    ]


def test_save_recipe_failure_on_raw_dataset_shows_warning(
    window: MeasurementExplorerWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        QtWidgets.QMessageBox, "warning", lambda *a, **k: calls.append(a[2] if len(a) > 2 else "")
    )
    window._write_recipe("nothing", tmp_path / "nothing.snomrecipe")
    assert calls, "capturing a raw measurement should warn, not crash"
    assert "nothing" not in window._recipes
    assert not (tmp_path / "nothing.snomrecipe").exists()


# --------------------------------------------------------------------------- #
# Browse + inspect
# --------------------------------------------------------------------------- #


def test_saved_recipe_appears_under_recipes_group(
    window: MeasurementExplorerWindow, qapp: Any, tmp_path: Path
) -> None:
    _build_history(window, qapp)
    window._write_recipe("topo clean", tmp_path / "topo.snomrecipe")
    assert _recipes_group_children(window) == ["topo clean"]


def test_selecting_recipe_shows_its_steps(
    window: MeasurementExplorerWindow, qapp: Any, tmp_path: Path
) -> None:
    _build_history(window, qapp)
    window._write_recipe("topo clean", tmp_path / "topo.snomrecipe")
    window._on_operation_selected("recipe:topo clean")
    detail = window._process._detail.text()
    assert "Plane Level" in detail
    assert "Fix Zero" in detail
    assert _is_shown(window._process._delete_recipe_btn)
    assert not window._process._form_box.isVisible()


# --------------------------------------------------------------------------- #
# Preview -> Accept (replay reuses the exact same lifecycle as a single operation)
# --------------------------------------------------------------------------- #


def test_preview_recipe_switches_to_comparison(
    window: MeasurementExplorerWindow, qapp: Any, tmp_path: Path
) -> None:
    manual_result = window._model.dataset
    _build_history(window, qapp)
    recipe_dataset_values = window._model.dataset.channel("Z").values.copy()
    window._write_recipe("topo clean", tmp_path / "topo.snomrecipe")

    # Fresh window on the same raw dataset, now replay the recipe instead of manually
    # clicking through plane_level -> fix_zero again.
    fresh = MeasurementExplorerWindow(ExplorerModel(manual_result))
    try:
        fresh._recipes["topo clean"] = window._recipes["topo clean"]
        fresh._refresh_recipes()
        fresh._on_preview_requested("recipe:topo clean", {})
        qapp.processEvents()
        assert fresh._stack.currentWidget() is fresh._comparison
        assert fresh._preview is not None
        np.testing.assert_allclose(
            fresh._preview.dataset.channel("Z").values, recipe_dataset_values
        )
        fresh._on_preview_accepted()
        qapp.processEvents()
        np.testing.assert_allclose(fresh._model.dataset.channel("Z").values, recipe_dataset_values)
    finally:
        fresh.close()
        fresh.deleteLater()
        qapp.processEvents()


def test_preview_recipe_failure_shows_warning(
    window: MeasurementExplorerWindow, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from snomniman.pipeline import Recipe, RecipeStep

    calls: list[str] = []
    monkeypatch.setattr(
        QtWidgets.QMessageBox, "warning", lambda *a, **k: calls.append(a[2] if len(a) > 2 else "")
    )
    # reference_normalize needs a complex optical + reference channel; the topography
    # fixture (Z only) has neither, so replay must fail honestly, not crash.
    window._recipes["bad"] = Recipe(
        name="bad", steps=(RecipeStep("image.reference_normalize", 1, {}),)
    )
    window._refresh_recipes()
    window._on_preview_requested("recipe:bad", {})
    qapp.processEvents()
    assert calls, "a warning should have been shown"
    assert window._preview is None


# --------------------------------------------------------------------------- #
# Load + delete
# --------------------------------------------------------------------------- #


def test_read_recipe_loads_and_registers_from_file(
    window: MeasurementExplorerWindow, qapp: Any, tmp_path: Path
) -> None:
    _build_history(window, qapp)
    path = tmp_path / "topo.snomrecipe"
    window._write_recipe("topo clean", path)
    window._recipes.clear()
    window._recipe_paths.clear()
    window._refresh_recipes()
    assert _recipes_group_children(window) == []

    window._read_recipe(path)
    assert "topo clean" in window._recipes
    assert _recipes_group_children(window) == ["topo clean"]


def test_read_recipe_failure_on_corrupt_file_shows_warning(
    window: MeasurementExplorerWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        QtWidgets.QMessageBox, "warning", lambda *a, **k: calls.append(a[2] if len(a) > 2 else "")
    )
    bad = tmp_path / "bad.snomrecipe"
    bad.write_text("not json", encoding="utf-8")
    window._read_recipe(bad)
    assert calls
    assert not window._recipes


def test_remove_recipe_deletes_file_and_tree_entry(
    window: MeasurementExplorerWindow, qapp: Any, tmp_path: Path
) -> None:
    _build_history(window, qapp)
    path = tmp_path / "topo.snomrecipe"
    window._write_recipe("topo clean", path)
    window._remove_recipe("topo clean")
    assert "topo clean" not in window._recipes
    assert not path.exists()
    assert _recipes_group_children(window) == []
