"""The Knowledge panel: a living scientific knowledge base, browsable in context.

Pure presentation (Rule 4): it renders the curated articles from
:mod:`snomniman.knowledge` and holds no scientific content of its own. A researcher can
browse by category, search, read an article, and follow cross-links between concepts,
operations, diagnostics, and the AI's philosophy - and other panels can deep-link here
("Learn more") via :meth:`KnowledgePanel.show_article`.

This is not a documentation browser bolted on: it is the same knowledge the AI grounds
its explanations in, surfaced where the researcher needs it.
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from snomniman.knowledge import (
    AI,
    CONCEPT,
    DIAGNOSTIC,
    OPERATION,
    Article,
    all_articles,
    find_article,
    search_articles,
)

_LINK = "snom-article:"
_CATEGORY_LABELS = {
    CONCEPT: "Concepts",
    OPERATION: "Operations",
    DIAGNOSTIC: "Diagnostics",
    AI: "AI Scientist",
}
_CATEGORY_ORDER = (CONCEPT, OPERATION, DIAGNOSTIC, AI)


class KnowledgePanel(QtWidgets.QWidget):
    """Browse, search, and read interconnected scientific articles inside the app."""

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        intro = QtWidgets.QLabel(
            "The science behind this measurement, in context. Browse or search, and "
            "follow the links between concepts, operations, diagnostics, and the AI."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #9aa0a6;")
        layout.addWidget(intro)

        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("Search the knowledge base...")
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

    def show_article(self, article_id: str) -> None:
        """Display an article by id (used by 'Learn more' deep-links and links)."""
        article = find_article(article_id)
        if article is None:
            self._browser.setHtml(
                f"<p>No knowledge article for <code>{_esc(article_id)}</code>.</p>"
            )
            return
        self._browser.setHtml(_article_html(article))
        self._select_in_tree(article_id)

    @property
    def current_html(self) -> str:
        return self._browser.toHtml()

    # -- internals ------------------------------------------------------------

    def _populate(self, query: str = "") -> None:
        articles = search_articles(query) if query else all_articles()
        self._tree.blockSignals(True)
        self._tree.clear()
        for category in _CATEGORY_ORDER:
            members = [a for a in articles if a.category == category]
            if not members:
                continue
            group = QtWidgets.QTreeWidgetItem([_CATEGORY_LABELS[category]])
            group.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            font = group.font(0)
            font.setBold(True)
            group.setFont(0, font)
            self._tree.addTopLevelItem(group)
            for article in members:
                item = QtWidgets.QTreeWidgetItem([article.title])
                item.setData(0, QtCore.Qt.ItemDataRole.UserRole, article.article_id)
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
        article_id = current.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(article_id, str):
            self._browser.setHtml(_article_html_by_id(article_id))

    def _on_anchor(self, url: QtCore.QUrl) -> None:
        target = url.toString()
        if target.startswith(_LINK):
            self.show_article(target[len(_LINK):])

    def _select_in_tree(self, article_id: str) -> None:
        for i in range(self._tree.topLevelItemCount()):
            group = self._tree.topLevelItem(i)
            if group is None:
                continue
            for j in range(group.childCount()):
                child = group.child(j)
                if child is None:
                    continue
                if child.data(0, QtCore.Qt.ItemDataRole.UserRole) == article_id:
                    self._tree.blockSignals(True)
                    self._tree.setCurrentItem(child)
                    self._tree.blockSignals(False)
                    return


# --------------------------------------------------------------------------- #
# Article -> HTML (presentation only; the knowledge package owns the content)
# --------------------------------------------------------------------------- #


def _article_html_by_id(article_id: str) -> str:
    article = find_article(article_id)
    return _article_html(article) if article is not None else _placeholder_html()


def _article_html(article: Article) -> str:
    parts = [f"<h2>{_esc(article.title)}</h2>", f"<p><i>{_esc(article.summary)}</i></p>"]
    parts.append(f"<p>{_esc(article.explanation)}</p>")
    _section(parts, "Scientific background", article.scientific_background)
    _section(parts, "Mathematical background", article.mathematical_background)
    _section(parts, "When to use it", article.practical_guidance)
    _bullets(parts, "Common mistakes", article.common_mistakes)

    related = _related_links(article)
    if related:
        parts.append("<h4>Related</h4><p>" + " &nbsp;|&nbsp; ".join(related) + "</p>")
    if article.references:
        parts.append("<h4>References</h4>")
        parts.append("<ul>" + "".join(f"<li>{_esc(r)}</li>" for r in article.references) + "</ul>")
    return "".join(parts)


def _related_links(article: Article) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    targets = (
        list(article.related_concepts)
        + [f"operation.{s}" for s in article.related_operations]
        + [f"diagnostic.{k}" for k in article.related_diagnostics]
    )
    for article_id in targets:
        if article_id in seen:
            continue
        seen.add(article_id)
        target = find_article(article_id)
        if target is not None:
            links.append(f'<a href="{_LINK}{article_id}">{_esc(target.title)}</a>')
    return links


def _section(parts: list[str], title: str, body: str | None) -> None:
    if body:
        parts.append(f"<h4>{_esc(title)}</h4><p>{_esc(body)}</p>")


def _bullets(parts: list[str], title: str, items: tuple[str, ...]) -> None:
    if items:
        parts.append(f"<h4>{_esc(title)}</h4>")
        parts.append("<ul>" + "".join(f"<li>{_esc(i)}</li>" for i in items) + "</ul>")


def _placeholder_html() -> str:
    return (
        "<p style='color:#777;'>Select an article, or click <b>Learn more</b> on an "
        "operation, diagnostic, or recommendation elsewhere in the Explorer.</p>"
    )


def _esc(text: object) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


__all__ = ["KnowledgePanel"]
