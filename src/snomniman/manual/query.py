"""Query the manual library - the application's read-only access to the pages.

Pure, deterministic lookup over the curated :data:`~snomniman.manual.library.PAGES`:
by id, by category, by the ProcessingStep it explains, and a relevance-ranked
substring search. Plus :func:`integrity_problems`, the manual's "no broken
internal links" check (mirrors :func:`snomniman.knowledge.integrity_problems`).
"""

from __future__ import annotations

from .library import PAGES
from .page import CATEGORIES, OPERATION_PAGE_PREFIX, ManualError, ManualPage

_INDEX: dict[str, ManualPage] = {p.page_id: p for p in PAGES}

# Search-ranking weights: a hit in the title matters more than one buried in the
# step-by-step instructions. Simple and explainable, not a black box.
_TITLE_WEIGHT = 3
_SUMMARY_WEIGHT = 2
_BODY_WEIGHT = 1


def all_pages() -> tuple[ManualPage, ...]:
    """Every page, ordered by (category, title)."""
    return tuple(sorted(PAGES, key=lambda p: (p.category, p.title)))


def find_page(page_id: str) -> ManualPage | None:
    """The page with *page_id*, or ``None``."""
    return _INDEX.get(page_id)


def get_page(page_id: str) -> ManualPage:
    """The page with *page_id*; raises :exc:`ManualError` if unknown."""
    try:
        return _INDEX[page_id]
    except KeyError:
        raise ManualError(f"unknown manual page id: {page_id!r}") from None


def pages_in(category: str) -> tuple[ManualPage, ...]:
    """All pages in *category* (see :data:`~snomniman.manual.page.CATEGORIES`)."""
    return tuple(p for p in all_pages() if p.category == category)


def page_for_operation(step_id: str) -> ManualPage | None:
    """The manual page explaining how to use a processing operation, by ``step_id``."""
    return _INDEX.get(OPERATION_PAGE_PREFIX + step_id)


def search_pages(query: str) -> tuple[ManualPage, ...]:
    """Pages matching *query* (case-insensitive substring), best match first.

    Ranked by where the match occurs - title beats summary beats step-by-step
    body text - then alphabetically for a stable order among equal scores.
    """
    q = query.strip().lower()
    if not q:
        return ()
    scored: list[tuple[int, ManualPage]] = []
    for page in all_pages():
        score = 0
        if q in page.title.lower():
            score += _TITLE_WEIGHT
        if q in page.summary.lower():
            score += _SUMMARY_WEIGHT
        if q in page.purpose.lower() or any(q in s.lower() for s in page.steps):
            score += _BODY_WEIGHT
        if score:
            scored.append((score, page))
    scored.sort(key=lambda item: (-item[0], item[1].title))
    return tuple(page for _score, page in scored)


def integrity_problems() -> list[str]:
    """Return a list of manual integrity violations (empty == healthy).

    Checks: valid category, id namespaced by category, no duplicate ids, and
    every ``related_pages`` cross-reference resolves to an existing page.
    (``related_knowledge_articles`` is checked by a cross-package test instead -
    validating it here would require importing :mod:`snomniman.knowledge`.)
    """
    problems: list[str] = []
    if len(_INDEX) != len(PAGES):
        problems.append("duplicate manual page ids present")
    ids = set(_INDEX)
    for p in PAGES:
        if p.category not in CATEGORIES:
            problems.append(f"{p.page_id}: invalid category {p.category!r}")
        if not p.page_id.startswith(p.category + "."):
            problems.append(f"{p.page_id}: id is not namespaced by category {p.category!r}")
        for rid in p.related_pages:
            if rid not in ids:
                problems.append(f"{p.page_id}: dangling related_pages -> {rid!r}")
    return problems


__all__ = [
    "all_pages",
    "find_page",
    "get_page",
    "integrity_problems",
    "page_for_operation",
    "pages_in",
    "search_pages",
]
