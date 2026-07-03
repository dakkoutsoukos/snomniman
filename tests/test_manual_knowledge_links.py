"""Cross-package link resolution between the Manual and the Knowledge Center.

Neither ``snomniman.manual`` nor ``snomniman.knowledge`` imports the other (both stay
Qt-free leaf packages - see ``docs/manual-system.md``); their cross-links are plain
string ids instead. This test is where that promise is actually checked - it is the
one place allowed to import both.
"""

from __future__ import annotations

from snomniman.knowledge import all_articles
from snomniman.manual import all_pages


def test_knowledge_articles_link_to_real_manual_pages() -> None:
    from snomniman.manual import find_page as manual_find_page

    bad = [
        (article.article_id, page_id)
        for article in all_articles()
        for page_id in article.related_manual_pages
        if manual_find_page(page_id) is None
    ]
    assert bad == [], f"knowledge articles with dangling related_manual_pages: {bad}"


def test_manual_pages_link_to_real_knowledge_articles() -> None:
    from snomniman.knowledge import find_article

    bad = [
        (page.page_id, article_id)
        for page in all_pages()
        for article_id in page.related_knowledge_articles
        if find_article(article_id) is None
    ]
    assert bad == [], f"manual pages with dangling related_knowledge_articles: {bad}"
