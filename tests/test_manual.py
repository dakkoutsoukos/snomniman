"""Tests for the Manual backend (snomniman.manual).

Mirrors ``tests/test_knowledge.py``: the library is curated content, so the tests
guard its *integrity* and its *coupling to the code* - no dangling internal links,
and the load-bearing invariant - every registered ProcessingStep has a manual page
(the manual cannot silently drift away from the operations it documents). Plus the
query API and JSON serialization.
"""

from __future__ import annotations

import json

import pytest

import snomniman.processing.image  # registers the image operations
import snomniman.processing.spectrum  # noqa: F401  (registers the spectrum operations)
from snomniman.manual import (
    AI,
    EXPLORER,
    EXPORT,
    GETTING_STARTED,
    SETTINGS,
    SHORTCUTS,
    TROUBLESHOOTING,
    WORKSPACE,
    ManualError,
    ManualPage,
    all_pages,
    find_page,
    get_page,
    integrity_problems,
    page_for_operation,
    pages_in,
    search_pages,
)
from snomniman.processing import list_steps

_CATEGORIES = (
    GETTING_STARTED,
    EXPLORER,
    WORKSPACE,
    AI,
    EXPORT,
    SETTINGS,
    SHORTCUTS,
    TROUBLESHOOTING,
)


# --------------------------------------------------------------------------- #
# Integrity + coupling to the code (no drift)
# --------------------------------------------------------------------------- #


def test_manual_has_no_integrity_problems() -> None:
    problems = integrity_problems()
    assert problems == [], "manual integrity violations:\n" + "\n".join(problems)


def test_every_registered_operation_has_a_manual_page() -> None:
    # The load-bearing no-drift invariant: the manual tracks the code.
    missing = [s for s in list_steps() if page_for_operation(s) is None]
    assert missing == [], f"operations without a manual page: {missing}"


def test_every_page_id_is_namespaced_by_category() -> None:
    for page in all_pages():
        assert page.page_id.startswith(page.category + ".")


def test_required_fields_present() -> None:
    for page in all_pages():
        assert page.title and page.summary and page.purpose


# --------------------------------------------------------------------------- #
# Query API
# --------------------------------------------------------------------------- #


def test_categories_are_populated() -> None:
    for category in _CATEGORIES:
        assert pages_in(category), f"no pages in category {category!r}"


def test_page_for_operation_resolves() -> None:
    page = page_for_operation("image.plane_level")
    assert page is not None
    assert page.category == WORKSPACE
    assert "Plane Level" in page.title


def test_page_for_operation_unknown_is_none() -> None:
    assert page_for_operation("image.does_not_exist") is None


def test_find_and_get_page() -> None:
    assert find_page("workspace.overview") is not None
    assert find_page("nope.nope") is None
    assert get_page("workspace.overview").title
    with pytest.raises(ManualError):
        get_page("nope.nope")


def test_search_finds_by_keyword() -> None:
    hits = {p.page_id for p in search_pages("plane")}
    assert "workspace.image.plane_level" in hits
    assert search_pages("") == ()


def test_search_ranks_title_matches_first() -> None:
    # "Plane Level" the title should outrank a page that only mentions "plane" in
    # its steps/purpose text.
    results = search_pages("plane")
    assert results[0].page_id == "workspace.image.plane_level"


# --------------------------------------------------------------------------- #
# Serialization
# --------------------------------------------------------------------------- #


def test_pages_json_serializable() -> None:
    for page in all_pages():
        assert isinstance(page, ManualPage)
        text = json.dumps(page.to_dict())
        back = json.loads(text)
        assert back["page_id"] == page.page_id
        assert isinstance(back["steps"], list)  # tuples -> lists
