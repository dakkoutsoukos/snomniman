"""snomniman.manual - the SNOMNIMAN Manual (how to use the software).

A Qt-free, dependency-light package of structured, queryable **pages** that
teach *how* to use the application - every panel, button, workflow, and
setting - as the counterpart to :mod:`snomniman.knowledge`, which teaches
*why* (the science). The two systems deliberately never duplicate one another:
a Manual page explains what a button does and how to use it, then links to the
matching Knowledge article for the science instead of repeating it.

Pages are curated content held to the project maxim: state only what is
actually true of the running application (e.g. the Settings page honestly
says no configurable settings exist yet), never padded to hit a count. The set
is *initial* and designed to grow - one page per new panel/operation/export
workflow; ``integrity_problems`` guards against broken internal links and a
test guards against drift from the registered processing operations. See
``docs/manual-system.md``.
"""

from __future__ import annotations

from .page import (
    AI,
    CATEGORIES,
    EXPLORER,
    EXPORT,
    GETTING_STARTED,
    SETTINGS,
    SHORTCUTS,
    TROUBLESHOOTING,
    WORKSPACE,
    ManualError,
    ManualPage,
)
from .query import (
    all_pages,
    find_page,
    get_page,
    integrity_problems,
    page_for_operation,
    pages_in,
    search_pages,
)

__all__ = [
    "AI",
    "CATEGORIES",
    "EXPLORER",
    "EXPORT",
    "GETTING_STARTED",
    "SETTINGS",
    "SHORTCUTS",
    "TROUBLESHOOTING",
    "WORKSPACE",
    "ManualError",
    "ManualPage",
    "all_pages",
    "find_page",
    "get_page",
    "integrity_problems",
    "page_for_operation",
    "pages_in",
    "search_pages",
]
