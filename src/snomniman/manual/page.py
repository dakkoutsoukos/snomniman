"""The manual page - one structured, queryable unit of operational teaching.

A :class:`ManualPage` is *not* a documentation page in the doc-browser sense: it
is structured data the application can query, cross-link, and surface in context
("How to use this operation" on a Processing Workspace step, a corner-widget
button on an Explorer tab, the F1 Manual shortcut). Pages explain **how** to use
a feature - buttons, panels, parameters, workflows - never the science behind it
(that is :mod:`snomniman.knowledge`'s job; a page links to the relevant article
instead of repeating it).

Pages carry **honest** content: only ``page_id`` / ``category`` / ``title`` /
``summary`` / ``purpose`` are required, so a page states only what is actually
true of the running application (e.g. the Settings page honestly says no
configurable settings exist yet, rather than inventing one). Cross-references
are by identifier and are integrity-checked within this package; links into
:mod:`snomniman.knowledge` are checked by a dedicated cross-package test instead
of an import, so neither package depends on the other.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

#: The eight manual categories.
GETTING_STARTED = "getting_started"
EXPLORER = "explorer"  # Explorer tabs, docks, and browsing/comparison features
WORKSPACE = "workspace"  # the Processing Workspace + one page per ProcessingStep
AI = "ai"  # the AI Scientist as seen in the UI (Briefing, Suggested Next Steps)
EXPORT = "export"  # every export/report workflow
SETTINGS = "settings"  # configurable options (honestly documents there are none yet)
SHORTCUTS = "shortcuts"  # the keyboard shortcut reference
TROUBLESHOOTING = "troubleshooting"  # common problems and their (honest) resolutions

CATEGORIES = (
    GETTING_STARTED,
    EXPLORER,
    WORKSPACE,
    AI,
    EXPORT,
    SETTINGS,
    SHORTCUTS,
    TROUBLESHOOTING,
)

#: id-prefix convention so the application can resolve a ``ProcessingStep`` to its
#: manual page: a step ``image.plane_level`` -> ``workspace.image.plane_level``
#: (mirrors ``knowledge.OPERATION_PREFIX``).
OPERATION_PAGE_PREFIX = "workspace."


class ManualError(KeyError):
    """Raised for an unknown page id or a manual integrity violation."""


@dataclass(frozen=True)
class ManualPage:
    """One structured manual page (frozen, JSON-serializable).

    ``page_id`` is stable and dot-namespaced by category (e.g.
    ``getting_started.first_five_minutes``, ``workspace.image.plane_level``,
    ``export.gsf``). Only ``title`` / ``summary`` / ``purpose`` are required;
    ``steps`` holds step-by-step instructions where there is a concrete
    procedure to walk through. Cross-references: ``related_pages`` are other
    manual page ids (integrity-checked here); ``related_knowledge_articles`` are
    :mod:`snomniman.knowledge` article ids (checked by a cross-package test, not
    an import); ``related_operations`` are step_ids; ``related_diagnostics`` are
    diagnostic keys.
    """

    page_id: str
    category: str
    title: str
    summary: str
    purpose: str
    steps: tuple[str, ...] = ()
    screenshot: str | None = None  # reserved for future use; not yet populated
    related_pages: tuple[str, ...] = ()
    related_knowledge_articles: tuple[str, ...] = ()
    related_operations: tuple[str, ...] = ()
    related_diagnostics: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}

    def search_text(self) -> str:
        """Lower-cased text used for weighted substring search."""
        return " ".join([self.title, self.summary, self.purpose, *self.steps]).lower()


def _jsonify(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify(v) for v in obj]
    return obj


__all__ = [
    "AI",
    "CATEGORIES",
    "EXPLORER",
    "EXPORT",
    "GETTING_STARTED",
    "OPERATION_PAGE_PREFIX",
    "SETTINGS",
    "SHORTCUTS",
    "TROUBLESHOOTING",
    "WORKSPACE",
    "ManualError",
    "ManualPage",
]
