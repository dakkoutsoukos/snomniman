"""snomniman.knowledge - the Knowledge Center (a living scientific knowledge base).

A Qt-free, dependency-light package of structured, queryable **articles** that teach
the science *inside* the application: near-field concepts, every processing operation,
the diagnostics, and the AI Scientist's philosophy. It is not a manual and not a doc
browser - articles are concise, interconnected data the Explorer surfaces in context
("Learn more" on an operation, a diagnostic, a recommendation), and that a future AI
narrator grounds its explanations in (it teaches; the model phrases).

Articles are curated content held to the project maxim: scientifically accurate and
defensible, never padded. The set is *initial* and designed to grow (one article per new
operation/diagnostic); ``integrity_problems`` guards against broken cross-references and a
test guards against drift from the registered operations. See ``docs/knowledge-center.md``.
"""

from __future__ import annotations

from .article import (
    AI,
    CATEGORIES,
    CONCEPT,
    DIAGNOSTIC,
    OPERATION,
    Article,
    KnowledgeError,
)
from .query import (
    all_articles,
    article_for_diagnostic,
    article_for_operation,
    articles_in,
    find_article,
    get_article,
    integrity_problems,
    search_articles,
)

__all__ = [
    "AI",
    "CATEGORIES",
    "CONCEPT",
    "DIAGNOSTIC",
    "OPERATION",
    "Article",
    "KnowledgeError",
    "all_articles",
    "article_for_diagnostic",
    "article_for_operation",
    "articles_in",
    "find_article",
    "get_article",
    "integrity_problems",
    "search_articles",
]
