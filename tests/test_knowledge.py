"""Tests for the Knowledge Center backend (snomniman.knowledge).

The library is curated content, so the tests guard its *integrity* and its *coupling
to the code*: no dangling cross-references, and - the load-bearing invariant - every
registered ProcessingStep has an operation article (the knowledge base cannot silently
drift away from the operations it teaches). Plus the query API and JSON serialization.
"""

from __future__ import annotations

import json

import pytest

import snomniman.processing.image  # noqa: F401  (registers the image operations)
from snomniman.knowledge import (
    AI,
    CONCEPT,
    DIAGNOSTIC,
    OPERATION,
    Article,
    KnowledgeError,
    all_articles,
    article_for_diagnostic,
    article_for_operation,
    articles_in,
    find_article,
    get_article,
    integrity_problems,
    search_articles,
)
from snomniman.processing import list_steps

_OPERATION_PREFIX = "operation."


# --------------------------------------------------------------------------- #
# Integrity + coupling to the code (no drift)
# --------------------------------------------------------------------------- #


def test_knowledge_base_has_no_integrity_problems() -> None:
    problems = integrity_problems()
    assert problems == [], "knowledge base integrity violations:\n" + "\n".join(problems)


def test_every_registered_operation_has_an_article() -> None:
    # The load-bearing no-drift invariant: teaching content tracks the code.
    missing = [s for s in list_steps() if article_for_operation(s) is None]
    assert missing == [], f"operations without a knowledge article: {missing}"


def test_operation_articles_map_to_real_steps() -> None:
    steps = set(list_steps())
    for article in articles_in(OPERATION):
        step_id = article.article_id[len(_OPERATION_PREFIX):]
        assert step_id in steps, f"operation article for unknown step {step_id!r}"


def test_every_article_id_is_namespaced_by_category() -> None:
    for article in all_articles():
        assert article.article_id.startswith(article.category + ".")


def test_required_fields_present() -> None:
    for article in all_articles():
        assert article.title and article.summary and article.explanation


# --------------------------------------------------------------------------- #
# Query API
# --------------------------------------------------------------------------- #


def test_categories_are_populated() -> None:
    for category in (CONCEPT, OPERATION, DIAGNOSTIC, AI):
        assert articles_in(category), f"no articles in category {category!r}"


def test_article_for_operation_resolves() -> None:
    article = article_for_operation("image.plane_level")
    assert article is not None
    assert article.category == OPERATION
    assert "Plane Level" in article.title


def test_article_for_operation_unknown_is_none() -> None:
    assert article_for_operation("image.does_not_exist") is None


def test_article_for_diagnostic_resolves() -> None:
    article = article_for_diagnostic("rms_roughness")
    assert article is not None and article.category == DIAGNOSTIC


def test_find_and_get_article() -> None:
    assert find_article("concept.phase") is not None
    assert find_article("nope.nope") is None
    assert get_article("concept.phase").title
    with pytest.raises(KnowledgeError):
        get_article("nope.nope")


def test_search_finds_by_keyword() -> None:
    hits = {a.article_id for a in search_articles("harmonic")}
    assert "concept.harmonics" in hits
    assert search_articles("") == ()


# --------------------------------------------------------------------------- #
# Serialization
# --------------------------------------------------------------------------- #


def test_articles_json_serializable() -> None:
    for article in all_articles():
        assert isinstance(article, Article)
        text = json.dumps(article.to_dict())
        back = json.loads(text)
        assert back["article_id"] == article.article_id
        assert isinstance(back["common_mistakes"], list)  # tuples -> lists
