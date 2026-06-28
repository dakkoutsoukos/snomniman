"""Tests for the Knowledge panel and the 'Learn more' deep-links.

The article *content* is covered by ``tests/test_knowledge.py``; here we check the
panel renders, searches, and navigates, that the window has a Knowledge tab, and that
'Learn more' on an operation (Workspace) and on a recommendation (AI Scientist) opens
the correct article. Headless (offscreen Qt); skips cleanly without PySide6.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from snomniman.core import Dataset
from snomniman.gui.model import ExplorerModel

pytest.importorskip("PySide6")

from PySide6 import QtWidgets

from snomniman.gui.knowledge import KnowledgePanel
from snomniman.gui.window import MeasurementExplorerWindow


@pytest.fixture
def window(qapp: Any, synthetic_dataset: Dataset) -> Iterator[MeasurementExplorerWindow]:
    win = MeasurementExplorerWindow(ExplorerModel(synthetic_dataset))
    yield win
    win.close()
    win.deleteLater()
    qapp.processEvents()


# --------------------------------------------------------------------------- #
# The panel
# --------------------------------------------------------------------------- #


def test_panel_populates_all_categories(qapp: Any) -> None:
    panel = KnowledgePanel()
    # Concepts / Operations / Diagnostics / AI Scientist.
    assert panel._tree.topLevelItemCount() == 4


def test_panel_show_article_renders_content(qapp: Any) -> None:
    panel = KnowledgePanel()
    panel.show_article("operation.image.plane_level")
    assert "Plane Level" in panel.current_html


def test_panel_show_unknown_article_is_graceful(qapp: Any) -> None:
    panel = KnowledgePanel()
    panel.show_article("nope.nope")
    assert "No knowledge article" in panel.current_html


def test_panel_search_filters_tree(qapp: Any) -> None:
    panel = KnowledgePanel()
    panel._search.setText("harmonic")
    qapp.processEvents()
    # Fewer top-level groups than the full four when filtered to a single topic.
    assert panel._tree.topLevelItemCount() < 4
    assert panel._tree.topLevelItemCount() >= 1


def test_panel_internal_link_navigates(qapp: Any) -> None:
    from PySide6.QtCore import QUrl

    panel = KnowledgePanel()
    panel.show_article("operation.image.plane_level")
    # The plane-level article links to the topography concept; following it navigates.
    panel._on_anchor(QUrl("snom-article:concept.topography"))
    assert "Topography" in panel.current_html


# --------------------------------------------------------------------------- #
# Window integration: the Knowledge tab + 'Learn more' deep-links
# --------------------------------------------------------------------------- #


def test_window_has_knowledge_tab(window: MeasurementExplorerWindow) -> None:
    titles = [window._inspect_tabs.tabText(i) for i in range(window._inspect_tabs.count())]
    assert "Knowledge" in titles


def test_operation_learn_more_opens_article(window: MeasurementExplorerWindow) -> None:
    window._on_operation_learn_more("image.reference_normalize")
    assert window._inspect_tabs.currentWidget() is window._knowledge
    assert "Reference Normalize" in window._knowledge.current_html


def test_workspace_learn_more_button_emits_step_id(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    captured: list[str] = []
    window._process.learnMoreRequested.connect(captured.append)
    window._on_operation_selected("image.plane_level")
    window._process._learn_btn.click()
    assert captured == ["image.plane_level"]


def test_recommendation_learn_more_opens_operation_article(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    # Click the first recommendation card's "Learn more" button.
    buttons = [
        b
        for b in window._briefing._suggest_box.findChildren(QtWidgets.QPushButton)
        if b.text() == "Learn more"
    ]
    assert buttons, "a recommendation should offer Learn more"
    buttons[0].click()
    qapp.processEvents()
    assert window._inspect_tabs.currentWidget() is window._knowledge
    assert window._knowledge.current_html  # an operation article is shown
