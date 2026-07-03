"""Tests for the Manual panel and its cross-links, mirroring test_gui_knowledge.py.

Page *content* is covered by ``tests/test_manual.py``; here we check the panel
renders, searches, and navigates; that the window has a Manual tab reachable via F1;
that "How to use this" on an operation (Workspace) and on a recommendation (AI
Scientist) opens the correct page; and that Knowledge <-> Manual cross-links
navigate both ways. Headless (offscreen Qt); skips cleanly without PySide6.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from snomniman.core import Dataset
from snomniman.gui.model import ExplorerModel

pytest.importorskip("PySide6")

from PySide6 import QtWidgets

from snomniman.gui.manual import ManualPanel
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
    panel = ManualPanel()
    # Getting Started / Explorer / Workspace / AI / Export / Settings / Shortcuts /
    # Troubleshooting.
    assert panel._tree.topLevelItemCount() == 8


def test_panel_show_page_renders_content(qapp: Any) -> None:
    panel = ManualPanel()
    panel.show_page("workspace.image.plane_level")
    assert "Plane Level" in panel.current_html


def test_panel_show_unknown_page_is_graceful(qapp: Any) -> None:
    panel = ManualPanel()
    panel.show_page("nope.nope")
    assert "No manual page" in panel.current_html


def test_panel_search_filters_tree(qapp: Any) -> None:
    panel = ManualPanel()
    panel._search.setText("plane level")
    qapp.processEvents()
    assert panel._tree.topLevelItemCount() < 8
    assert panel._tree.topLevelItemCount() >= 1


def test_panel_internal_link_navigates(qapp: Any) -> None:
    from PySide6.QtCore import QUrl

    panel = ManualPanel()
    panel.show_page("workspace.image.plane_level")
    # Plane Level links to the Workspace overview page; following it navigates.
    panel._on_anchor(QUrl("snom-page:workspace.overview"))
    assert "Processing Workspace" in panel.current_html


def test_panel_knowledge_link_emits_signal(qapp: Any) -> None:
    from PySide6.QtCore import QUrl

    panel = ManualPanel()
    captured: list[str] = []
    panel.knowledgeArticleRequested.connect(captured.append)
    panel.show_page("workspace.image.plane_level")
    panel._on_anchor(QUrl("snom-knowledge:operation.image.plane_level"))
    assert captured == ["operation.image.plane_level"]


def test_focus_search_gives_search_box_focus(qapp: Any) -> None:
    panel = ManualPanel()
    panel.show()
    panel.focus_search()
    qapp.processEvents()
    assert panel._search.hasFocus()
    panel.close()


# --------------------------------------------------------------------------- #
# Window integration: the Manual tab, F1, and the deep-links
# --------------------------------------------------------------------------- #


def test_window_has_manual_tab(window: MeasurementExplorerWindow) -> None:
    titles = [window._inspect_tabs.tabText(i) for i in range(window._inspect_tabs.count())]
    assert "Manual" in titles


def test_help_manual_action_opens_manual_tab(window: MeasurementExplorerWindow) -> None:
    window._open_manual()
    assert window._inspect_tabs.currentWidget() is window._manual


def test_operation_manual_opens_page(window: MeasurementExplorerWindow) -> None:
    window._on_operation_manual("image.reference_normalize")
    assert window._inspect_tabs.currentWidget() is window._manual
    assert "Reference Normalize" in window._manual.current_html


def test_workspace_manual_button_emits_step_id(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    captured: list[str] = []
    window._process.manualRequested.connect(captured.append)
    window._on_operation_selected("image.plane_level")
    window._process._manual_btn.click()
    assert captured == ["image.plane_level"]


def test_recommendation_manual_button_opens_operation_page(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    buttons = [
        b
        for b in window._briefing._suggest_box.findChildren(QtWidgets.QPushButton)
        if b.text() == "How to use this"
    ]
    assert buttons, "a recommendation should offer How to use this"
    buttons[0].click()
    qapp.processEvents()
    assert window._inspect_tabs.currentWidget() is window._manual
    assert window._manual.current_html  # an operation page is shown


def test_knowledge_article_manual_link_opens_manual_tab(
    window: MeasurementExplorerWindow,
) -> None:
    window._on_open_manual_page("workspace.image.plane_level")
    assert window._inspect_tabs.currentWidget() is window._manual
    assert "Plane Level" in window._manual.current_html


def test_manual_page_knowledge_link_opens_knowledge_tab(
    window: MeasurementExplorerWindow,
) -> None:
    window._on_open_knowledge_article("operation.image.plane_level")
    assert window._inspect_tabs.currentWidget() is window._knowledge
    assert "Plane Level" in window._knowledge.current_html
