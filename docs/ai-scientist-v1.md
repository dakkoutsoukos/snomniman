# The AI Scientist, v1: Measurement Orientation (`snomniman.ai`)

> Status: **implemented** (ADR-0020). Qt-free backend; consumed by the Explorer's
> read-only **Briefing** panel. **No model dependency** is bundled in this version.

## Philosophy

The first AI capability is **orientation**, not action: *"tell me about this
measurement."* It does not recommend processing, execute anything, or modify the
Dataset. It transforms structured scientific facts into an expert explanation.

Two principles govern it (now permanent in `CLAUDE.md`):

1. **Grounding.** The AI may reason only over deterministic facts produced by
   SNOMNIMAN. It must never become the primary interpreter of raw scientific data
   when deterministic algorithms can establish those facts.
2. **Deterministic fallback.** Every AI-powered feature has a useful deterministic
   fallback. AI *enhances* understanding; it never *gates* access to understanding.

So the briefing is built in two layers: deterministic **facts** (always present,
authoritative) and an optional natural-language **interpretation** (a narrative
renderer on top). The LLM is "just another renderer" of facts that already exist -
like the image view or the publication figure - not a new source of truth.

## Position in the architecture

```
gui
batch  pipeline
describe   diagnostics   ai      (ai depends on describe + diagnostics + core)
processing
io   core
```

`snomniman.ai` consumes **only** `snomniman.describe` (structure) and
`snomniman.diagnostics` (computed facts) - plus `core` for the `Dataset` handle it is
asked about. It must never inspect raw NumPy arrays, Qt widgets, Explorer state,
rendering, or image pixels. It is Qt-free (Rule 4), never mutates a dataset, and adds
nothing to the provenance DAG - a briefing is read-only text, not a derivation.

```
Measurement -> Dataset -> Description API + Diagnostics Engine -> AI Scientist
            -> Briefing (facts [+ optional interpretation])
```

## What it produces

`build_briefing(dataset, *, title=None, provider=None) -> Briefing`. The `Briefing`
(frozen, JSON-serializable) carries:

- **`sections`** - three deterministic fact sections, every statement a
  `BriefingStatement(kind="fact", sources=(...))`:
  - *Measurement Summary* - raw/derived, scan area, sampling, detection, excitation,
    channels, harmonics, reference presence (from `describe`).
  - *Scientific Observations* - topography tilt + roughness, whether plane leveling
    is applied, the strongest optical harmonic, invalid-pixel notes (from
    `diagnostics`).
  - *What This Measurement Enables* - capability statements and per-operation
    applicability (capability description, **not advice**).
- **`interpretation`** - the optional AI narrative (`None` when no provider).
- **`provider`** / **`generated_at`** - what produced the narrative, for audit.
- **`context`** - the exact `BriefingContext` (the `describe` + `diagnostics` JSON
  projections) the briefing was built from: the grounding and the audit trail.

## Provider abstraction (the seam, no SDK yet)

`NarrativeProvider` is a `Protocol` with `name: str` and `narrate(context) -> str`.
The rest of SNOMNIMAN depends only on this protocol, never on a model vendor.

This version bundles **no model SDK** (zero new dependency). It ships:

- `build_orientation_prompt(context)` - the grounded prompt a provider should send,
  built here so it is testable without a network and identical across providers. It
  embeds the entire facts payload verbatim and instructs: use only these facts, never
  invent, separate fact from interpretation, do not recommend processing.
- `MockNarrativeProvider` - a deterministic, network-free provider for tests/demos
  that derives its narrative from the context (proving the grounding path).

A concrete provider (e.g. Anthropic, OpenAI, or a local model) will arrive in a
follow-up as an **optional extra** (`uv sync --extra ai`), lazy-imported, never
required for the backend or CI. An AI inference is non-deterministic; when a provider
is used, the briefing records its `name` and `generated_at` for auditability.

## Grounding strategy (and an honest limitation)

Grounding is enforced by construction: a provider receives **only** the deterministic
facts payload (`BriefingContext`), the prompt forbids invention, and the briefing
stores that exact payload so any statement - fact or narrative - can be audited
against it.

What v1 does **not** do: verify, per sentence, that a free-text narrative used only
the supplied facts (that would need an entailment/NLI checker). The deterministic
fact statements *are* individually source-tagged; the AI narrative is grounded by
construction and auditable against `context`, but is not machine-verified
sentence-by-sentence. This is stated plainly rather than overclaimed, and is a
candidate for a later milestone.

## Explorer integration

A read-only **Briefing** tab (`gui/briefing.py`): collapsible fact sections, an
"Interpretation (AI)" area (which shows a clear "no provider configured - the facts
above are complete and authoritative" note in this build), and a "Copy briefing"
action. No input box, no chat history, no agent behaviour - a scientific briefing,
not a chatbot. The model builds the briefing with no provider, so the app is fully
useful offline today.

## Testing

- Deterministic facts are asserted exactly; every fact statement is checked to cite
  only `description`/`diagnostics`.
- The provider seam is exercised with `MockNarrativeProvider` (no network); the
  prompt builder is tested to embed the facts and the "do not invent" instruction.
- The briefing round-trips through JSON; the non-mutation invariant is asserted.
- No external API is contacted in any test (none is bundled).

## Limitations and future evolution

- No real model provider yet (seam only).
- Orientation only - **no recommendations, no execution** (a later milestone, once
  the operation vocabulary is richer, will add *reviewable* recommendations that the
  deterministic processing engine alone executes).
- No per-sentence narrative verification (see Grounding strategy).
- Deferred panel sections from the original sketch (Recommended Reading, Relevant
  Literature) are intentionally out of scope here.
