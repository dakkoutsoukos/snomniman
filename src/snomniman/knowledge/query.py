"""Query the knowledge library - the application's read-only access to the articles.

Pure, deterministic lookup over the curated :data:`~snomniman.knowledge.library.ARTICLES`:
by id, by category, by the object it explains (operation step_id / diagnostic key), and
a simple substring search. Plus :func:`integrity_problems`, which checks the base for
dangling cross-references - the knowledge equivalent of "no broken links".
"""

from __future__ import annotations

from .article import (
    CATEGORIES,
    DIAGNOSTIC_PREFIX,
    OPERATION_PREFIX,
    Article,
    KnowledgeError,
)
from .library import ARTICLES

_INDEX: dict[str, Article] = {a.article_id: a for a in ARTICLES}


def all_articles() -> tuple[Article, ...]:
    """Every article, ordered by (category, title)."""
    return tuple(sorted(ARTICLES, key=lambda a: (a.category, a.title)))


def find_article(article_id: str) -> Article | None:
    """The article with *article_id*, or ``None``."""
    return _INDEX.get(article_id)


def get_article(article_id: str) -> Article:
    """The article with *article_id*; raises :exc:`KnowledgeError` if unknown."""
    try:
        return _INDEX[article_id]
    except KeyError:
        raise KnowledgeError(f"unknown article id: {article_id!r}") from None


def articles_in(category: str) -> tuple[Article, ...]:
    """All articles in *category* (``concept`` / ``operation`` / ``diagnostic`` / ``ai``)."""
    return tuple(a for a in all_articles() if a.category == category)


def article_for_operation(step_id: str) -> Article | None:
    """The article that explains a processing operation, by its ``step_id``."""
    return _INDEX.get(OPERATION_PREFIX + step_id)


def article_for_diagnostic(key: str) -> Article | None:
    """The article that explains a diagnostic, by its key (e.g. ``rms_roughness``)."""
    return _INDEX.get(DIAGNOSTIC_PREFIX + key)


def search_articles(query: str) -> tuple[Article, ...]:
    """Articles whose title/summary/explanation contain *query* (case-insensitive)."""
    q = query.strip().lower()
    if not q:
        return ()
    return tuple(a for a in all_articles() if q in a.search_text())


def integrity_problems() -> list[str]:
    """Return a list of knowledge-base integrity violations (empty == healthy).

    Checks: valid category, id namespaced by category, no duplicate ids, and every
    cross-reference (``related_concepts`` ids, ``related_operations`` step_ids,
    ``related_diagnostics`` keys) resolves to an existing article.
    """
    problems: list[str] = []
    if len(_INDEX) != len(ARTICLES):
        problems.append("duplicate article ids present")
    ids = set(_INDEX)
    for a in ARTICLES:
        if a.category not in CATEGORIES:
            problems.append(f"{a.article_id}: invalid category {a.category!r}")
        if not a.article_id.startswith(a.category + "."):
            problems.append(f"{a.article_id}: id is not namespaced by category {a.category!r}")
        for rid in a.related_concepts:
            if rid not in ids:
                problems.append(f"{a.article_id}: dangling related_concepts -> {rid!r}")
        for sid in a.related_operations:
            if (OPERATION_PREFIX + sid) not in ids:
                problems.append(
                    f"{a.article_id}: related_operations {sid!r} has no operation article"
                )
        for key in a.related_diagnostics:
            if (DIAGNOSTIC_PREFIX + key) not in ids:
                problems.append(
                    f"{a.article_id}: related_diagnostics {key!r} has no diagnostic article"
                )
    return problems


__all__ = [
    "all_articles",
    "article_for_diagnostic",
    "article_for_operation",
    "articles_in",
    "find_article",
    "get_article",
    "integrity_problems",
    "search_articles",
]
