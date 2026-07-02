"""Integration tests for batch processing (Phase 4B) in the Explorer window.

Covers the orchestration layer that reuses `snomniman.batch.run_batch` across the
sessions the window already manages: selecting measurements (reusing the
Measurement Manager's existing multi-select), committing each successful outcome
into its session exactly as a manual Preview -> Accept would, leaving the currently
displayed measurement refreshed only if it was included, and surfacing the summary
in the Experiment tab. Dialog-driven entry points (`_on_batch_requested`) delegate to
directly-testable core methods (`_run_batch`, `_show_batch_result`), mirroring the
Phase 4A recipe test convention.

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

from snomniman.batch import STATUS_SKIPPED, STATUS_SUCCESS
from snomniman.gui.window import MeasurementExplorerWindow
from snomniman.pipeline import Recipe, RecipeStep


@pytest.fixture
def window(qapp: Any, topography_dataset: Dataset) -> Iterator[MeasurementExplorerWindow]:
    win = MeasurementExplorerWindow(ExplorerModel(topography_dataset, title="Scan 1"))
    win.add_measurement_model(ExplorerModel(topography_dataset, title="Scan 2"))
    yield win
    win.close()
    win.deleteLater()
    qapp.processEvents()


@pytest.fixture
def clean_recipe() -> Recipe:
    return Recipe(
        name="topo clean",
        steps=(
            RecipeStep("image.plane_level", 1, {"channel": "Z", "order": 1}),
            RecipeStep("image.fix_zero", 1, {"channel": "Z"}),
        ),
    )


def _register(window: MeasurementExplorerWindow, recipe: Recipe) -> None:
    window._recipes[recipe.name] = recipe
    window._refresh_recipes()


# --------------------------------------------------------------------------- #
# Core orchestration: _run_batch commits outcomes into sessions
# --------------------------------------------------------------------------- #


def test_run_batch_updates_every_selected_session(
    window: MeasurementExplorerWindow, clean_recipe: Recipe
) -> None:
    result = window._run_batch(clean_recipe, [0, 1])
    assert len(result.succeeded) == 2
    for session in window._sessions:
        assert len(session.history) == 1  # the raw model moved to history
        assert session.model.dataset.channel("Z").values is not None
        z_values = session.model.dataset.channel("Z").values
        np.testing.assert_allclose(np.nanmean(z_values), 0, atol=1e-6)


def test_run_batch_refreshes_active_session_display(
    window: MeasurementExplorerWindow, clean_recipe: Recipe
) -> None:
    # add_measurement_model() switches to the newly added measurement, so session 1
    # ("Scan 2") is active here.
    assert window._active_index == 1
    original_dataset = window._model.dataset
    window._run_batch(clean_recipe, [1])
    assert window._model.dataset is not original_dataset
    assert window._model is window._sessions[1].model


def test_run_batch_does_not_disturb_display_when_active_not_included(
    window: MeasurementExplorerWindow, clean_recipe: Recipe
) -> None:
    assert window._active_index == 1
    original_model = window._model
    window._run_batch(clean_recipe, [0])  # active session (1) excluded
    assert window._model is original_model  # still showing the untouched active session
    assert len(window._sessions[0].history) == 1  # but session 0 was updated


def test_run_batch_does_not_mutate_project_measurements(
    window: MeasurementExplorerWindow, clean_recipe: Recipe
) -> None:
    before = window._measurement_of(window._sessions[0])
    window._run_batch(clean_recipe, [0, 1])
    # The pre-batch snapshot is untouched (Measurement/Dataset are immutable).
    assert len(before.datasets) == 1


# --------------------------------------------------------------------------- #
# Progress + should_stop are forwarded to the runner
# --------------------------------------------------------------------------- #


def test_run_batch_forwards_progress_callback(
    window: MeasurementExplorerWindow, clean_recipe: Recipe
) -> None:
    calls: list[tuple[int, int, str]] = []
    window._run_batch(
        clean_recipe,
        [0, 1],
        on_progress=lambda i, total, outcome: calls.append((i, total, outcome.status)),
    )
    assert calls == [(1, 2, STATUS_SUCCESS), (2, 2, STATUS_SUCCESS)]


def test_run_batch_forwards_should_stop(
    window: MeasurementExplorerWindow, clean_recipe: Recipe
) -> None:
    result = window._run_batch(clean_recipe, [0, 1], should_stop=lambda: True)
    assert result.stopped_early is True
    assert result.outcomes == ()
    # Nothing was touched - should_stop fired before the first measurement.
    assert window._sessions[0].history == []
    assert window._sessions[1].history == []


# --------------------------------------------------------------------------- #
# Skipped measurements are honest, not silently dropped
# --------------------------------------------------------------------------- #


def test_run_batch_skips_incompatible_measurement(window: MeasurementExplorerWindow) -> None:
    bad_recipe = Recipe(name="bad", steps=(RecipeStep("image.reference_normalize", 1, {}),))
    result = window._run_batch(bad_recipe, [0, 1])
    assert [o.status for o in result.outcomes] == [STATUS_SKIPPED, STATUS_SKIPPED]
    assert all(o.reason for o in result.outcomes)
    # Skipped measurements are left untouched.
    assert window._sessions[0].history == []
    assert window._sessions[1].history == []


# --------------------------------------------------------------------------- #
# Results surface in the Experiment tab (not a new report artifact)
# --------------------------------------------------------------------------- #


def test_show_batch_result_populates_experiment_panel(
    window: MeasurementExplorerWindow, clean_recipe: Recipe
) -> None:
    result = window._run_batch(clean_recipe, [0, 1])
    window._show_batch_result(result, clean_recipe)
    assert window._inspect_tabs.currentWidget() is window._experiment_panel
    assert window._experiment_panel._batch.rowCount() == 2
    assert "topo clean" in window._experiment_panel._batch_caption.text()


# --------------------------------------------------------------------------- #
# Dialog-driven entry point: guard rails only (dialogs themselves are stock Qt)
# --------------------------------------------------------------------------- #


def test_on_batch_requested_with_no_recipes_shows_info(
    window: MeasurementExplorerWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def fake_information(*args: Any, **kwargs: Any) -> None:
        calls.append(str(args[2]) if len(args) > 2 else "")

    monkeypatch.setattr(QtWidgets.QMessageBox, "information", fake_information)
    window._on_batch_requested()
    assert calls, "should inform the user no recipes exist yet"


def test_manager_has_batch_button(window: MeasurementExplorerWindow) -> None:
    assert window._manager._batch_btn.text() == "Batch..."


def test_batch_button_click_emits_signal(
    window: MeasurementExplorerWindow, qapp: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        QtWidgets.QMessageBox, "information", lambda *a, **k: calls.append("shown")
    )
    window._manager._batch_btn.click()
    qapp.processEvents()
    assert calls  # no recipes yet -> the info dialog handler ran, proving the wiring fired


def test_on_batch_requested_full_flow_with_registered_recipe(
    window: MeasurementExplorerWindow,
    clean_recipe: Recipe,
    monkeypatch: pytest.MonkeyPatch,
    qapp: Any,
) -> None:
    _register(window, clean_recipe)
    # Always pick the first offered item - "All measurements (...)" for the scope
    # prompt, the only recipe name for the recipe prompt - regardless of call order.
    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getItem",
        staticmethod(lambda parent, title, label, items, **kwargs: (items[0], True)),
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QtWidgets.QMessageBox.StandardButton.Yes),
    )
    info_calls: list[str] = []
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "information",
        staticmethod(lambda *a, **k: info_calls.append("shown")),
    )

    window._on_batch_requested()
    qapp.processEvents()

    assert info_calls  # the final "Batch complete" summary was shown
    assert len(window._sessions[0].history) == 1
    assert len(window._sessions[1].history) == 1
    assert window._inspect_tabs.currentWidget() is window._experiment_panel
