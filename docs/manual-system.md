# The Manual (`snomniman.manual`)

> Status: **implemented** (ADR-0032). Qt-free backend; an Explorer **Manual** panel
> consumes it; other panels deep-link into it ("How to use this"). Counterpart to the
> Knowledge Center (`docs/knowledge-center.md`).

An in-app, structured, queryable answer to "how do I use this?" - not a documentation
browser, not a README bolted onto a tab. SNOMNIMAN already teaches the *science*
in-app (the Knowledge Center); as the software itself has grown (8 Inspect tabs, a
dozen processing operations, recipes, batch, multi-format export, three report types)
researchers need the same kind of in-app answer for the *software*.

## Philosophy: how, not why

Two questions, two systems, never one answering the other's question:

| | Knowledge Center | Manual |
|---|---|---|
| Answers | *Why?* (the science) | *How?* (the software) |
| Example | "Why does Plane Level use a circular mean for phase?" | "Which button do I click, and what does the 'order' parameter do?" |
| Content | Scientific background, mathematics, references | Buttons, panels, parameters, step-by-step workflows |

A Manual page never repeats the science - it links to the matching Knowledge article
instead (`related_knowledge_articles`). A Knowledge article never explains which
button to click - it links to the matching Manual page instead
(`related_manual_pages`). This split is enforced by convention (both are curated
content, held to the project maxim of stating only what is accurate) and made
navigable by the cross-linking mechanism below.

## Architecture

A second Qt-free, dependency-light leaf package, structurally a near-mirror of
`snomniman.knowledge`:

```
gui  ----------------> manual      (the Manual panel + "How to use this" deep-links)
gui  ----------------> knowledge   (unchanged; each panel may import both to render
                                     a readable cross-link title)
manual -> (nothing internal)
knowledge -> (nothing internal)
```

**Neither `manual` nor `knowledge` imports the other.** This is deliberate: the two
packages have no computational reason to depend on each other, and adding an edge
would be an unjustified new dependency (Rule 7). Their cross-references
(`ManualPage.related_knowledge_articles`, `Article.related_manual_pages`) are plain
string ids - exactly the same pattern `knowledge.Article.related_operations` already
uses to reference `processing` step_ids without importing `processing`. Two things
keep the promise honest without the import:
- The **GUI layer** (`gui/manual.py`, `gui/knowledge.py`) is allowed to import both
  leaves - it does, purely to resolve a readable title for a cross-link instead of
  showing a raw id.
- A **dedicated cross-package test**, `tests/test_manual_knowledge_links.py`, is the
  one place allowed to import both packages together; it asserts every
  `related_manual_pages` id resolves in `manual` and every
  `related_knowledge_articles` id resolves in `knowledge` - broken-link protection
  without the dependency edge.

Modules (mirroring `knowledge/article.py` / `library.py` / `query.py`):
- `page.py` - the `ManualPage` value object (frozen, JSON-serializable), the eight
  category constants, id conventions, `ManualError`.
- `library.py` - the curated content (`PAGES`): getting-started, one per Explorer
  panel, the Processing Workspace + one per registered operation, the AI Scientist as
  seen in the UI, every export/report workflow, settings, shortcuts, troubleshooting.
- `query.py` - read-only access: `get_page` / `find_page` / `pages_in` /
  `page_for_operation` / `search_pages`, plus `integrity_problems` (the internal
  "no broken links" check).

## The page model

A `ManualPage` is **structured, queryable data** - not a markdown page. Required:
`page_id` (dot-namespaced by category, e.g. `workspace.image.plane_level`,
`export.gsf`), `category`, `title`, `summary`, `purpose`. Optional: `steps` (a
step-by-step procedure, rendered as a numbered list), `screenshot` (reserved for a
future image field, unpopulated today), and cross-references: `related_pages` (other
manual page ids, integrity-checked within this package), `related_knowledge_articles`
(knowledge article ids, checked by the cross-package test), `related_operations`
(step_ids), `related_diagnostics` (diagnostic keys).

The id convention is the same linkage glue Knowledge uses: a `ProcessingStep` with
`step_id="image.plane_level"` resolves to the manual page
`workspace.image.plane_level` via `page_for_operation`, mirroring
`article_for_operation`.

## Search and ranking

`search_pages(query)` is a substring search over title/summary/purpose/steps, ranked
by where the match occurs - a title hit outranks a summary hit, which outranks a hit
buried in step-by-step text - then alphabetically among ties. This is deliberately
simple and explainable (not a black-box relevance model): it is the mechanism behind
the "type anything, find the right page first" requirement, and it is what the Manual
panel's search box and the `F1` global entry point both use.

## Explorer integration

A **Manual** tab (`gui/manual.py`, right after **Knowledge** in the same Inspect tab
widget): a category tree, a search box, and a page view (a `QTextBrowser`) whose
`related_pages` links are clickable and navigate within the Manual, and whose
`related_knowledge_articles` links jump into the Knowledge tab.

The tab itself is the primary entry point - like Knowledge, Manual needs no special
affordance to reach: click the tab. Two additional entry points route through the
window (child panels never know about each other - the same decoupled-signal pattern
the Knowledge Center established) for the moments a researcher is already looking at
something specific:
- **"How to use this operation" / "How to use this"** - a second button placed next to
  every existing "Learn more" button (the Processing Workspace's operation detail, an
  AI Scientist recommendation card). Each panel defines its own
  `manualRequested = Signal(str)` emitting a `step_id`; the window resolves it via
  `page_for_operation` and switches to the Manual tab.
- **`Help > Manual` (`F1`)** - the global, always-available entry point: opens the
  Manual tab and focuses its search box (`ManualPanel.focus_search()`). This is the
  literal implementation of "nothing is more than one search away."

A per-tab "open the Manual page for whatever I'm looking at" corner button was tried
and removed (user feedback, 2026-07-03): a permanent button sitting next to a tab whose
sole purpose was to switch to that same tab was redundant with just clicking it, and
cluttered the tab bar. The Manual tab's own tree/search remains the way to reach a
specific panel's page directly.

**Cross-linking (both directions).** A Knowledge article's "How to use this" line
(rendered from `related_manual_pages`) emits `KnowledgePanel.manualPageRequested`; a
Manual page's "See also (the science)" line (rendered from
`related_knowledge_articles`) emits `ManualPanel.knowledgeArticleRequested`. The
window connects both to a handler that switches tabs and shows the target - the
Knowledge <-> Manual relationship feels like one integrated system, not two panels
that happen to sit next to each other.

## Integrity (no drift)

Three guarantees keep the Manual honest as the code evolves:
- `manual.integrity_problems()` - dangling *internal* `related_pages`, invalid
  category, duplicate id (mirrors `knowledge.integrity_problems`).
- `tests/test_manual.py::test_every_registered_operation_has_a_manual_page` - the
  load-bearing no-drift invariant: every step in `processing.list_steps()` has a
  manual page, exactly like Knowledge's equivalent test for operation articles.
- `tests/test_manual_knowledge_links.py` - both cross-link directions resolve (see
  Architecture above); this is the check that stands in for an import-time guarantee,
  since neither package imports the other.

## Honest, not padded

Content is held to the same maxim as Knowledge: state only what is actually true of
the running application. The clearest example is the Settings page
(`settings.overview`) - rather than a placeholder implying a Preferences dialog
exists, it states plainly that SNOMNIMAN has none today (confirmed by inspecting the
codebase: no `QSettings`, no Preferences dialog), and that window layout/recent files
are not persisted between sessions (only an explicit `File > Save Project` persists
state). If a future increment adds configurable options, this page documents them
then - not before.

## Explicit scope boundary (deliberate, not a gap)

Individual toolbar buttons (Single / Compare presets / Contact sheet / Export
figure...) and dialogs (Save/Open/Batch) do **not** get their own inline "How to use
this" button in this increment - wiring roughly ten more signal/handler pairs for
marginal individual value was not worth it against the entry points above, which
already reach every major surface. They are fully documented as Manual pages
(`explorer.comparison_mode`, `export.figure`, `workspace.batch`, ...) and reachable
via search or the tree - just not via an inline button on the control itself. This
mirrors how `knowledge-center.md` lists
its own deferred "Learn more" sources (diagnostics rows, harmonics, provenance) as
future expansion rather than treating the initial set as exhaustive.

## Future expansion

- Toolbar-button-level and dialog-level inline entry points, if real usage shows the
  three existing entry points are not enough (Rule 9: earn the added surface).
- `screenshot` population - the field exists (`ManualPage.screenshot`) but is
  unpopulated; adding real screenshots is a content task, not an architecture change.
- One page per new panel/operation/export workflow as the product grows - the
  no-drift test enforces operation coverage; other categories grow as accurately as
  they can be written, never to pad a count (the maxim).
- A narrative provider (if one is ever added per `docs/ai-scientist-v1.md`) could in
  principle ground a "how do I..." answer in these pages the same way it would ground
  a "why..." answer in Knowledge articles - not built today, no seam required yet.
