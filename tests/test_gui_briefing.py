"""Tests for the Explorer's Scientific Briefing panel (presentation only).

The panel renders the model's briefing; correctness of the facts is covered by
``tests/test_ai_briefing.py``. Here we check rendering, the no-provider note, the
copy-to-text rendering, the tab wiring, and the read-only invariant.
"""

from __future__ import annotations

from typing import Any

import pytest

from snomniman.ai import Briefing
from snomniman.core import Dataset
from snomniman.gui.model import ExplorerModel

pytest.importorskip("PySide6")


def test_model_returns_a_briefing(synthetic_dataset: Dataset) -> None:
    briefing = ExplorerModel(synthetic_dataset).scientific_briefing()
    assert isinstance(briefing, Briefing)
    assert len(briefing.sections) == 3
    # No provider configured in the app -> facts only.
    assert briefing.interpretation is None


def test_panel_renders_sections(qapp: Any, synthetic_dataset: Dataset) -> None:
    from snomniman.gui.briefing import BriefingPanel

    panel = BriefingPanel()
    briefing = ExplorerModel(synthetic_dataset).scientific_briefing()
    panel.set_briefing(briefing)
    assert panel._tree.topLevelItemCount() == len(briefing.sections)
    # Re-rendering replaces rather than appends.
    panel.set_briefing(briefing)
    assert panel._tree.topLevelItemCount() == len(briefing.sections)


def test_panel_copy_text_includes_facts(qapp: Any, synthetic_dataset: Dataset) -> None:
    from snomniman.gui.briefing import BriefingPanel

    panel = BriefingPanel()
    panel.set_briefing(ExplorerModel(synthetic_dataset).scientific_briefing())
    text = panel.as_text()
    assert "Measurement Summary" in text
    assert "What This Measurement Enables" in text
    # The no-provider note is communicated, not an empty interpretation.
    assert "complete and authoritative" in panel._interpretation.text()


def test_window_has_briefing_tab(qapp: Any, synthetic_dataset: Dataset) -> None:
    from snomniman.gui.window import MeasurementExplorerWindow

    window = MeasurementExplorerWindow(ExplorerModel(synthetic_dataset))
    titles = [window._inspect_tabs.tabText(i) for i in range(window._inspect_tabs.count())]
    assert "Briefing" in titles


def test_briefing_does_not_mutate_dataset(qapp: Any, synthetic_dataset: Dataset) -> None:
    import numpy as np

    model = ExplorerModel(synthetic_dataset)
    before = {
        n: synthetic_dataset.channel(n).values.copy() for n in synthetic_dataset.channel_names
    }
    model.scientific_briefing()
    for name, values in before.items():
        np.testing.assert_array_equal(synthetic_dataset.channel(name).values, values)
