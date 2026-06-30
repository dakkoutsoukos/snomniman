"""End-to-end window tests for the multi-input Processing Workspace (ADR-0030).

These verify the GUI side of multi-input processing: the workspace shows a dataset
picker for an operation's extra input slots, gates Preview when no second dataset is
available, runs a two-input operation through the *same* preview/accept flow as every
other operation, appends the two-parent result to the active measurement's history,
and refuses incompatible inputs with a clear message. Skipped without the gui extra.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import numpy as np
import pytest

from snomniman.core import Dataset, ProvenanceNode, StepRecord
from snomniman.gui.model import ExplorerModel

pytest.importorskip("PySide6")

from snomniman.gui.window import MeasurementExplorerWindow


def _raw_node(node_id: str) -> ProvenanceNode:
    return ProvenanceNode(
        node_id=node_id,
        record=StepRecord(step_id="io.read", step_version=1, deterministic=True),
    )


def _distinct(ds: Dataset, node_id: str, **deltas: float) -> Dataset:
    """A distinct dataset object (own provenance) on the same grid, channels shifted."""
    data = ds.data.copy(deep=True)
    for channel, delta in deltas.items():
        data[channel] = data[channel] + delta
    return Dataset(data, kind=ds.kind, metadata=ds.metadata, provenance=_raw_node(node_id))


def _sliced(ds: Dataset, node_id: str) -> Dataset:
    """A distinct, smaller-grid dataset (for the incompatibility case)."""
    data = ds.data.isel(x=slice(0, 2), y=slice(0, 2))
    return Dataset(data, kind=ds.kind, metadata=ds.metadata, provenance=_raw_node(node_id))


@pytest.fixture
def window(qapp: Any, synthetic_dataset: Dataset) -> Iterator[MeasurementExplorerWindow]:
    win = MeasurementExplorerWindow(ExplorerModel(synthetic_dataset, title="CdO A"))
    win.resize(1100, 720)
    win.show()
    qapp.processEvents()
    yield win
    win.close()
    win.deleteLater()
    qapp.processEvents()


def test_single_measurement_blocks_multi_input_preview(window: MeasurementExplorerWindow) -> None:
    # With one measurement there is no second dataset for the "secondary" slot.
    window._present_operation("image.arithmetic")
    assert window._process._inputs_ready is False
    assert window._process._preview_btn.isEnabled() is False


def test_arithmetic_preview_accept_appends_two_parent_dataset(
    window: MeasurementExplorerWindow, qapp: Any, synthetic_dataset: Dataset
) -> None:
    measurement_b = _distinct(synthetic_dataset, "raw_b", Z=5.0)
    window.add_measurement_model(ExplorerModel(measurement_b, title="CdO B"))
    qapp.processEvents()
    window._present_operation("image.arithmetic")  # active = B; candidate = A
    assert "secondary" in window._process._input_combos
    window._process.apply_params({"channel": "Z", "mode": "a_minus_b"})
    window._process._input_combos["secondary"][0].setCurrentIndex(0)  # pick measurement A
    assert window._process._preview_btn.isEnabled() is True

    history_before = len(window._history)
    window._on_preview_requested("image.arithmetic", window._process.current_params())
    assert window._preview is not None
    window._on_preview_accepted()
    qapp.processEvents()

    # The difference is appended to the active (B) measurement's history.
    assert len(window._history) == history_before + 1
    result = window._model.dataset
    assert "Z_diff" in result.channel_names
    # Two-parent provenance: primary (B) and secondary (A).
    assert set(result.provenance.inputs) == {"primary", "secondary"}
    # a_minus_b with primary B (Z+5) and secondary A: B.Z - A.Z = +5.
    np.testing.assert_allclose(result.channel("Z_diff").values, 5.0)


def test_incompatible_input_is_refused_with_message(
    window: MeasurementExplorerWindow,
    qapp: Any,
    synthetic_dataset: Dataset,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from PySide6 import QtWidgets

    small = _sliced(synthetic_dataset, "raw_small")
    window.add_measurement_model(ExplorerModel(small, title="Small"))
    qapp.processEvents()
    window._present_operation("image.arithmetic")  # active = Small (2x2); candidate = A (4x3)
    window._process.apply_params({"channel": "Z", "mode": "a_minus_b"})
    window._process._input_combos["secondary"][0].setCurrentIndex(0)

    warnings: list[str] = []

    def _capture(*args: Any, **kwargs: Any) -> None:
        warnings.append(args[2] if len(args) > 2 else "")

    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", _capture)
    history_before = len(window._history)
    window._on_preview_requested("image.arithmetic", window._process.current_params())

    # Refused, explained, and nothing committed.
    assert window._preview is None
    assert any("incompatible" in w for w in warnings)
    assert len(window._history) == history_before
