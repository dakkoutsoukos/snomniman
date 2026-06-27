"""Tests for the Explorer's Diagnostics panel (presentation of computed facts).

The panel is pure presentation: it must render the model's diagnostic sections and
never mutate the dataset. The scientific correctness of the numbers themselves is
covered by ``tests/test_diagnostics.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

from snomniman.core import Dataset
from snomniman.gui.model import DiagnosticSection, ExplorerModel

pytest.importorskip("PySide6")


def test_model_report_has_expected_sections(synthetic_dataset: Dataset) -> None:
    sections = ExplorerModel(synthetic_dataset).diagnostics_report()
    titles = [s.title for s in sections]
    assert "Topography" in titles
    assert "Optical harmonics" in titles
    assert "Channels" in titles
    assert "Processing applicability" in titles


def test_report_mentions_applicable_operation(synthetic_dataset: Dataset) -> None:
    sections = {s.title: s for s in ExplorerModel(synthetic_dataset).diagnostics_report()}
    ops = sections["Processing applicability"]
    plane = next(r for r in ops.rows if r.label == "image.plane_level")
    assert "available" in plane.value


def test_panel_renders_report(qapp: Any, synthetic_dataset: Dataset) -> None:
    from snomniman.gui.diagnostics import DiagnosticsPanel

    panel = DiagnosticsPanel()
    sections = ExplorerModel(synthetic_dataset).diagnostics_report()
    panel.set_report(sections)
    # One top-level tree item per section.
    assert panel._tree.topLevelItemCount() == len(sections)
    # Re-rendering replaces rather than appends.
    panel.set_report(sections)
    assert panel._tree.topLevelItemCount() == len(sections)


def test_window_has_diagnostics_tab(qapp: Any, synthetic_dataset: Dataset) -> None:
    from snomniman.gui.window import MeasurementExplorerWindow

    window = MeasurementExplorerWindow(ExplorerModel(synthetic_dataset))
    tab_titles = [
        window._inspect_tabs.tabText(i) for i in range(window._inspect_tabs.count())
    ]
    assert "Diagnostics" in tab_titles


def test_diagnostics_does_not_mutate_dataset(qapp: Any, synthetic_dataset: Dataset) -> None:
    import numpy as np

    model = ExplorerModel(synthetic_dataset)
    before = {
        n: synthetic_dataset.channel(n).values.copy() for n in synthetic_dataset.channel_names
    }
    model.diagnostics_report()
    for name, values in before.items():
        np.testing.assert_array_equal(synthetic_dataset.channel(name).values, values)


def test_sections_are_view_objects(synthetic_dataset: Dataset) -> None:
    sections = ExplorerModel(synthetic_dataset).diagnostics_report()
    assert all(isinstance(s, DiagnosticSection) for s in sections)
