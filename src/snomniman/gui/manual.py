"""The Manual panel: how to use SNOMNIMAN, browsable in context.

Pure presentation (Rule 4): it renders the curated pages from
:mod:`snomniman.manual` and holds no operational content of its own. A researcher can
browse by category, search, read a page, and follow cross-links between pages - and
other panels can deep-link here ("How to use this") via :meth:`ManualPanel.show_page`.

This is the counterpart to :mod:`snomniman.gui.knowledge` (which answers "why?"); it
answers "how?" and never repeats the science - a page links to its Knowledge Center
article instead. Clicking such a link does not navigate within this panel (the Manual
does not know about the Knowledge panel) - it emits :attr:`knowledgeArticleRequested`
for the window to handle, exactly the reverse of how the Knowledge panel emits
``manualPageRequested`` for its own science-to-how-to links.
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from snomniman.knowledge import find_article
from snomniman.manual import (
    AI,
    EXPLORER,
    EXPORT,
    GETTING_STARTED,
    SETTINGS,
    SHORTCUTS,
    TROUBLESHOOTING,
    WORKSPACE,
    ManualPage,
    all_pages,
    find_page,
    search_pages,
)

_PAGE_LINK = "snom-page:"
_KNOWLEDGE_LINK = "snom-knowledge:"
_CATEGORY_LABELS = {
    GETTING_STARTED: "Getting Started",
    EXPLORER: "Explorer",
    WORKSPACE: "Processing Workspace",
    AI: "AI",
    EXPORT: "Export",
    SETTINGS: "Settings",
    SHORTCUTS: "Keyboard Shortcuts",
    TROUBLESHOOTING: "Troubleshooting",
}
_CATEGORY_ORDER = (
    GETTING_STARTED,
    EXPLORER,
    WORKSPACE,
    AI,
    EXPORT,
    SETTINGS,
    SHORTCUTS,
    TROUBLESHOOTING,
)


class ManualPanel(QtWidgets.QWidget):
    """Browse, search, and read how-to-use-it pages inside the app."""

    #: A related-knowledge-article link was clicked; the window opens it in Knowledge.
    knowledgeArticleRequested: QtCore.Signal = QtCore.Signal(str)

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        intro = QtWidgets.QLabel(
            "How to use SNOMNIMAN - every panel, button, operation, and workflow. "
            "Search, or browse by category; for the science behind a feature, follow "
            "its 'See also' link into the Knowledge Center."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #9aa0a6;")
        layout.addWidget(intro)

        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("Search the manual...")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._on_search)
        layout.addWidget(self._search)

        split = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)
        self._tree.currentItemChanged.connect(self._on_item_changed)
        split.addWidget(self._tree)

        self._browser = QtWidgets.QTextBrowser()
        self._browser.setOpenLinks(False)
        self._browser.setOpenExternalLinks(False)
        self._browser.anchorClicked.connect(self._on_anchor)
        split.addWidget(self._browser)
        split.setSizes([200, 420])
        layout.addWidget(split, 1)

        self._populate()
        self._browser.setHtml(_placeholder_html())

    # -- public interface -----------------------------------------------------

    def show_page(self, page_id: str) -> None:
        """Display a page by id (used by 'How to use this' deep-links and links)."""
        page = find_page(page_id)
        if page is None:
            self._browser.setHtml(f"<p>No manual page for <code>{_esc(page_id)}</code>.</p>")
            return
        self._browser.setHtml(_page_html(page))
        self._select_in_tree(page_id)

    def focus_search(self) -> None:
        """Move keyboard focus to the search box and select its text (the F1 entry point)."""
        self._search.setFocus(QtCore.Qt.FocusReason.ShortcutFocusReason)
        self._search.selectAll()

    @property
    def current_html(self) -> str:
        return self._browser.toHtml()

    # -- internals ------------------------------------------------------------

    def _populate(self, query: str = "") -> None:
        pages = search_pages(query) if query else all_pages()
        self._tree.blockSignals(True)
        self._tree.clear()
        for category in _CATEGORY_ORDER:
            members = [p for p in pages if p.category == category]
            if not members:
                continue
            group = QtWidgets.QTreeWidgetItem([_CATEGORY_LABELS[category]])
            group.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            font = group.font(0)
            font.setBold(True)
            group.setFont(0, font)
            self._tree.addTopLevelItem(group)
            for page in members:
                item = QtWidgets.QTreeWidgetItem([page.title])
                item.setData(0, QtCore.Qt.ItemDataRole.UserRole, page.page_id)
                group.addChild(item)
            group.setExpanded(True)
        self._tree.blockSignals(False)

    def _on_search(self, text: str) -> None:
        self._populate(text)

    def _on_item_changed(
        self,
        current: QtWidgets.QTreeWidgetItem | None,
        _previous: QtWidgets.QTreeWidgetItem | None,
    ) -> None:
        if current is None:
            return
        page_id = current.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(page_id, str):
            self._browser.setHtml(_page_html_by_id(page_id))

    def _on_anchor(self, url: QtCore.QUrl) -> None:
        target = url.toString()
        if target.startswith(_PAGE_LINK):
            self.show_page(target[len(_PAGE_LINK):])
        elif target.startswith(_KNOWLEDGE_LINK):
            self.knowledgeArticleRequested.emit(target[len(_KNOWLEDGE_LINK):])

    def _select_in_tree(self, page_id: str) -> None:
        for i in range(self._tree.topLevelItemCount()):
            group = self._tree.topLevelItem(i)
            if group is None:
                continue
            for j in range(group.childCount()):
                child = group.child(j)
                if child is None:
                    continue
                if child.data(0, QtCore.Qt.ItemDataRole.UserRole) == page_id:
                    self._tree.blockSignals(True)
                    self._tree.setCurrentItem(child)
                    self._tree.blockSignals(False)
                    return


# --------------------------------------------------------------------------- #
# ManualPage -> HTML (presentation only; the manual package owns the content)
# --------------------------------------------------------------------------- #


def _page_html_by_id(page_id: str) -> str:
    page = find_page(page_id)
    return _page_html(page) if page is not None else _placeholder_html()


def _page_html(page: ManualPage) -> str:
    parts = [f"<h2>{_esc(page.title)}</h2>", f"<p><i>{_esc(page.summary)}</i></p>"]
    parts.append(f"<p>{_esc(page.purpose)}</p>")
    if page.steps:
        parts.append("<h4>Steps</h4>")
        parts.append("<ol>" + "".join(f"<li>{_esc(s)}</li>" for s in page.steps) + "</ol>")

    related = _related_page_links(page)
    if related:
        parts.append("<h4>Related</h4><p>" + " &nbsp;|&nbsp; ".join(related) + "</p>")
    knowledge = _related_knowledge_links(page)
    if knowledge:
        parts.append(
            "<h4>See also (the science)</h4><p>" + " &nbsp;|&nbsp; ".join(knowledge) + "</p>"
        )
    return "".join(parts)


def _related_page_links(page: ManualPage) -> list[str]:
    links: list[str] = []
    for page_id in page.related_pages:
        target = find_page(page_id)
        if target is not None:
            links.append(f'<a href="{_PAGE_LINK}{page_id}">{_esc(target.title)}</a>')
    return links


def _related_knowledge_links(page: ManualPage) -> list[str]:
    # snomniman.manual itself never imports snomniman.knowledge (both stay leaf
    # packages - see docs/manual-system.md); this GUI presentation module may import
    # both, purely to render a readable title instead of a raw id.
    links: list[str] = []
    for article_id in page.related_knowledge_articles:
        article = find_article(article_id)
        title = article.title if article is not None else article_id
        links.append(f'<a href="{_KNOWLEDGE_LINK}{article_id}">{_esc(title)}</a>')
    return links


def _placeholder_html() -> str:
    return (
        "<p style='color:#777;'>Select a page, search, or press F1, or click "
        "<b>How to use this</b> on an operation or recommendation elsewhere in the "
        "Explorer.</p>"
    )


def _esc(text: object) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


__all__ = ["ManualPanel"]
