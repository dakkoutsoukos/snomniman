"""Tests for the Explorer's AI Scientist panel (presentation only).

The panel renders the model's briefing and workflow suggestions; correctness of the
facts/recommendations is covered by ``tests/test_ai_briefing.py`` and
``tests/test_ai_recommend.py``. Here we check rendering, the no-provider note, the
suggestion cards + their Preview hand-off to the Processing Workspace, the
copy-to-text rendering, the tab wiring, and the read-only invariant.
"""

from __future__ import annotations

from typing import Any

import pytest

from snomniman.ai import Briefing, WorkflowSuggestions
from snomniman.core import Dataset
from snomniman.gui.model import ExplorerModel
from snomniman.processing.image.plane_level import PlaneLevel
from snomniman.processing.image.reference_normalize import ReferenceNormalize

pytest.importorskip("PySide6")

from PySide6 import QtWidgets


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


# --------------------------------------------------------------------------- #
# Suggested next steps (recommendation cards + Workspace hand-off)
# --------------------------------------------------------------------------- #


def test_model_returns_suggestions(synthetic_dataset: Dataset) -> None:
    ws = ExplorerModel(synthetic_dataset).workflow_suggestions()
    assert isinstance(ws, WorkflowSuggestions)
    assert ws.recommendations  # raw synthetic has applicable, un-applied operations


def test_panel_renders_one_preview_button_per_recommendation(
    qapp: Any, synthetic_dataset: Dataset
) -> None:
    from snomniman.gui.briefing import BriefingPanel

    panel = BriefingPanel()
    ws = ExplorerModel(synthetic_dataset).workflow_suggestions()
    panel.set_suggestions(ws)
    previews = [
        b for b in panel._suggest_box.findChildren(QtWidgets.QPushButton) if b.text() == "Preview"
    ]
    assert len(previews) == len(ws.recommendations) >= 2


def test_panel_card_shows_considerations(qapp: Any, synthetic_dataset: Dataset) -> None:
    from snomniman.gui.briefing import BriefingPanel

    panel = BriefingPanel()
    panel.set_suggestions(ExplorerModel(synthetic_dataset).workflow_suggestions())
    texts = [w.text() for w in panel._suggest_box.findChildren(QtWidgets.QLabel)]
    # Reference Normalize carries deterministic caveats, rendered under "Consider:".
    assert any(t.startswith("Consider:") for t in texts)


def test_panel_preview_button_emits_step_and_params(
    qapp: Any, synthetic_dataset: Dataset
) -> None:
    from snomniman.gui.briefing import BriefingPanel

    panel = BriefingPanel()
    ws = ExplorerModel(synthetic_dataset).workflow_suggestions()
    panel.set_suggestions(ws)
    captured: list[tuple[str, object]] = []
    panel.recommendationPreviewRequested.connect(lambda sid, p: captured.append((sid, p)))
    preview = next(
        b for b in panel._suggest_box.findChildren(QtWidgets.QPushButton) if b.text() == "Preview"
    )
    preview.click()
    assert captured
    step_id, params = captured[0]
    assert step_id in {r.step_id for r in ws.recommendations}
    assert isinstance(params, dict)


def test_panel_empty_suggestions_show_note(qapp: Any, synthetic_dataset: Dataset) -> None:
    from snomniman.gui.briefing import BriefingPanel

    # Apply both applicable operations so nothing remains to suggest.
    leveled = PlaneLevel(channel="Z", order=1).apply({"primary": synthetic_dataset})
    both = ReferenceNormalize().apply({"primary": leveled})
    panel = BriefingPanel()
    panel.set_suggestions(ExplorerModel(both).workflow_suggestions())
    assert panel._suggest_box.findChildren(QtWidgets.QPushButton) == []


def test_window_recommendation_opens_workspace_preview(
    qapp: Any, synthetic_dataset: Dataset
) -> None:
    from snomniman.gui.window import MeasurementExplorerWindow

    window = MeasurementExplorerWindow(ExplorerModel(synthetic_dataset))
    try:
        window._on_recommendation_preview("image.plane_level", {"channel": "Z", "order": 1})
        qapp.processEvents()
        # The Process tab is shown, the operation is loaded + pre-filled, and a preview runs.
        assert window._inspect_tabs.currentWidget() is window._process
        assert window._process.current_params() == {"channel": "Z", "order": 1}
        assert window._stack.currentWidget() is window._comparison
        assert window._preview is not None
        assert window._preview.step_id == "image.plane_level"
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()
