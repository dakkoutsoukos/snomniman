# The Knowledge Center (`snomniman.knowledge`)

> Status: **implemented** (ADR-0024). Qt-free backend; an Explorer **Knowledge** panel
> consumes it; other panels deep-link into it ("Learn more"). No model dependency.

A *living scientific knowledge base* integrated into the product - not a manual, not a
doc browser. SNOMNIMAN already contains substantial scientific knowledge (measurements,
harmonics, metadata, diagnostics, operations, provenance, AI briefings); the Knowledge
Center lets a researcher understand any of it **without leaving the application**.

## Philosophy

Most scientific software assumes the user already knows the science. SNOMNIMAN instead
*teaches the science while the user performs it* - lowering the barrier for newcomers and
making the AI more trustworthy, because its explanations are grounded in a curated base
rather than improvised. Documentation is part of the product; learning is part of the
workflow. This serves the project identity: *help researchers understand measurements and
become better scientists.*

Articles are held to the project maxim - scientifically accurate and defensible, concise,
never padded. The library is **initial**, designed to grow, and guarded against drift
(see Integrity).

## Architecture

A Qt-free, dependency-light package (it imports nothing else in the project), so it is a
clean leaf the GUI and a future AI narrator consume:

```
gui  ----------------> knowledge   (the Knowledge panel + "Learn more" deep-links)
ai   (future narrator) -> knowledge (grounds explanations in articles; never invents)
knowledge -> (nothing internal)    (curated content + a query API)
```

Modules:
- `article.py` - the `Article` value object (frozen, JSON-serializable) + category
  constants + id conventions + `KnowledgeError`.
- `library.py` - the curated content (`ARTICLES`): concepts, one per operation, the
  diagnostics, and the AI's philosophy.
- `query.py` - read-only access: `get_article` / `find_article` / `articles_in` /
  `article_for_operation` / `article_for_diagnostic` / `search_articles`, plus
  `integrity_problems` (the "no broken links" check).

## The article model

An `Article` is **structured, queryable data** - not a markdown page. Required:
`article_id` (dot-namespaced by category, e.g. `operation.image.plane_level`),
`category` (`concept` / `operation` / `diagnostic` / `ai`), `title`, `summary`,
`explanation`. Optional (filled only where there is something accurate to say):
`scientific_background`, `mathematical_background`, `practical_guidance` (when to use),
`common_mistakes`, `related_concepts` (article ids), `related_operations` (step_ids),
`related_diagnostics` (keys), `references`. Cross-references are by id and are
integrity-checked - no dangling links.

The id conventions are the linkage glue: an operation `image.plane_level` resolves to
`operation.image.plane_level`; a diagnostic key `rms_roughness` to
`diagnostic.rms_roughness`. That is how any object in the Explorer finds "its" article.

## Explorer integration

A **Knowledge** tab (`gui/knowledge.py`): a category tree, a search box, and an article
view (a `QTextBrowser`) whose `related` links are clickable and navigate within the base
(concept -> operation -> diagnostic -> ...). The panel holds no scientific content - it
renders the articles the backend owns.

**"Learn more" deep-links.** Other panels expose a Learn-more affordance that opens the
relevant article in the Knowledge tab:
- the **Processing Workspace** - "Learn more about this operation" -> the operation article;
- an **AI Scientist recommendation** card - "Learn more" -> the recommended operation's
  article.

Each emits the object's identifier (a `step_id`); the window resolves it via
`article_for_operation` and shows the article. Wiring a new source (a diagnostic row, a
harmonic, the provenance view) is the same one-line pattern with `article_for_diagnostic`
/ the appropriate id - the mechanism is generic.

## AI integration

The AI Scientist **never invents explanations**. Today (no narrative provider), the
integration is the deep-link: a recommendation points at the operation's article, so the
researcher reads curated, accurate teaching rather than model prose. When a narrative
provider is added, it will *ground* its explanations in these articles (quote/augment),
with the Knowledge Center remaining the canonical source of scientific teaching - exactly
the deterministic-authority / AI-interpreter split the project is built on.

## Integrity (no drift)

Two guarantees keep the base honest as the code evolves:
- `integrity_problems()` returns any dangling cross-reference (a `related_*` that resolves
  to no article), invalid category, or duplicate id - asserted empty in tests.
- A test asserts **every registered `ProcessingStep` has an operation article**, so the
  knowledge base cannot silently fall out of sync with the operations it teaches.

## Future expansion

- One article per new operation/diagnostic (the no-drift test will demand it).
- More "Learn more" sources (diagnostics rows, harmonics, provenance, metadata fields).
- Richer concept coverage (specific modalities: nano-FTIR spectroscopy, polariton
  imaging) as the readers and real datasets warrant - added only when accurate.
- A narrative provider that grounds its prose in these articles (it phrases; the base
  teaches).

The library is intentionally an *initial, curated* set: breadth grows as it can be made
accurate, never to pad a count (the maxim).
