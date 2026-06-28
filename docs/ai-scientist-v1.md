# The AI Scientist: Measurement Orientation + Suggested Next Steps (`snomniman.ai`)

> Status: **implemented**. v1 = the **Scientific Briefing** (orientation; ADR-0020).
> v2 = **Suggested Next Steps** (deterministic, grounded workflow recommendations;
> ADR-0022). Qt-free backend; consumed by the Explorer's read-only **AI Scientist**
> (Briefing) panel, which hands a chosen step off to the Processing Workspace. **No
> model dependency** is bundled; the recommendations are deterministic (no provider
> needed). The "Suggested Next Steps" section below documents v2.

## Philosophy

The first AI capability is **orientation**, not action: *"tell me about this
measurement."* It does not execute anything or modify the Dataset; it transforms
structured scientific facts into an expert explanation. The second capability,
**Suggested Next Steps** (below), proposes *what to do next* - still without executing
anything: it ranks registered operations the deterministic facts support, and hands
the chosen one to the Processing Workspace to preview. The AI proposes; the
researcher disposes; the deterministic engine performs the science.

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
    applicability (capability description, **not advice**). This section grows
    automatically as the deterministic vocabulary grows: when a new
    `ProcessingStep` is registered (e.g. `image.reference_normalize`,
    `image.phase_unwrap`, `image.crop`), it appears here with **no AI-specific
    change** - the briefing reads applicability from the Diagnostics Engine, which
    reads each step's declared capabilities (verified by tests). The AI's vocabulary
    is exactly the deterministic engine's vocabulary.
- **`interpretation`** - the optional AI narrative (`None` when no provider).
- **`provider`** / **`generated_at`** - what produced the narrative, for audit.
- **`context`** - the exact `BriefingContext` (the `describe` + `diagnostics` JSON
  projections) the briefing was built from: the grounding and the audit trail.

## Suggested Next Steps (v2 - deterministic workflow recommendations)

`recommend_workflow(dataset, *, title=None) -> WorkflowSuggestions`. After orienting
the researcher, the AI Scientist proposes a **ranked list of next processing steps**.
The recommendations are produced **deterministically** from `describe` + `diagnostics`
(operation applicability, topography tilt, channel states, provenance) - never by an
LLM. This is a deliberate, load-bearing choice, not a stopgap:

- **It is what the two permanent rules require.** Whether a step is *worth* doing -
  "is there a tilt to remove?", "are references present and unnormalized?" - is a
  fact a deterministic algorithm establishes (the Diagnostics Engine already computes
  the tilt). Rule 1 says compute such facts; do not ask an LLM to infer them.
- **It is the deterministic fallback (Rule 2), so there is nothing to fall back
  *from*.** The suggestions are always available, with or without any provider.
- **It makes the safety rules structural, not hopeful.** Because each recommendation
  is *generated from* applicability + provenance, the engine **cannot** suggest an
  unavailable operation, an already-applied one, or anything that contradicts the
  diagnostics. An LLM constrained by a prompt could; a generator cannot.

Each `Recommendation` (frozen, JSON-serializable) carries: the `step_id` + human
`title`, pre-filled `params` (ready for the Workspace), a heuristic `confidence` in
[0, 1] (a deterministic *priority* from the strength of the evidence - **not** a
probability; surfaced as a `strength` tier: strong/moderate/tentative), a one-line
`rationale`, the `evidence` (deterministic facts, each source-tagged
`diagnostics`/`description`), and the `expected_outcome`. `WorkflowSuggestions` holds
the ranked tuple (by confidence), a `note` explaining an empty result (e.g.
everything applicable is already applied), and the same `BriefingContext` grounding.

The recommendations are produced by the **Scientific Reasoning Rule Engine** -
registered, individually-testable `ReasoningRule`s, not ad-hoc code. The engine
(`recommend.py`) evaluates every rule, enforcing the applicability + not-already-applied
guards uniformly (so each rule holds only its *scientific* trigger), honouring rule
prerequisites and exclusions, and ranking by confidence. Each recommendation also carries
`rule_id` (traceability) and `considerations` (deterministic caveats). The shipped rules:

- **Plane Level** (`reasoning.level_dominant_tilt`) - when a measured global tilt
  dominates the *signal* topography (confidence = the fraction of the height's RMS
  variation attributable to the tilt); pre-fills `{channel: <Z>, order: 1}`.
- **Reference Normalize** (`reasoning.normalize_with_reference`) - when reference
  channels exist and optical signals are still raw.

New rules are added by registering one `ReasoningRule` (no engine/GUI change); like the
Briefing's Enables section, the catalogue grows with the deterministic vocabulary, not
with AI code. A future narrative provider may *phrase* the suggestions, but never choose
or rank them. **Full detail, the lifecycle, and what is deliberately deferred
(phase-unwrap until a validated wrapping diagnostic; crop as user-intent-driven):
`docs/scientific-reasoning.md` (ADR-0023).**

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

A read-only **Briefing** tab (`gui/briefing.py`): collapsible fact sections, a
**Suggested next steps** area (one card per recommendation - title, strength badge,
rationale, the deterministic *Why* evidence, the expected outcome, and a **Preview**
button), an "Interpretation (AI)" area (which shows a clear "no provider configured -
the facts above are complete and authoritative" note in this build), and a "Copy
briefing" action. No input box, no chat history, no agent behaviour.

The **Preview** button is the payoff of building the Processing Workspace first: a
recommendation needs *no* AI-specific execution path. It opens the Process tab,
selects the recommended operation, fills its parameters from the recommendation, and
runs the **same** generic preview every operation uses (`window._on_recommendation_
preview` -> `highlight_operation` + `show_operation` + `apply_params` ->
`preview_operation`). The researcher then Accepts or Cancels like any other
derivation. The model builds both briefing and suggestions with no provider, so the
app is fully useful offline today.

## Testing

- Deterministic facts are asserted exactly; every fact statement is checked to cite
  only `description`/`diagnostics`.
- The provider seam is exercised with `MockNarrativeProvider` (no network); the
  prompt builder is tested to embed the facts and the "do not invent" instruction.
- The briefing round-trips through JSON; the non-mutation invariant is asserted.
- No external API is contacted in any test (none is bundled).

## Testing (Suggested Next Steps)

- Grounding + safety are pinned: only applicable operations are recommended, never
  already-applied ones, and no recommendation contradicts the provenance (asserted on
  raw, partially-processed, and fully-processed datasets). Evidence sources are
  checked to be `diagnostics`/`description` only.
- Ranking, the empty-result `note`, JSON round-trip (with grounding context), the
  signal-topography target, and the non-mutation invariant are all tested.
- GUI: the panel renders one Preview button per recommendation and its click emits
  `(step_id, params)`; the window handler opens the Workspace, pre-fills the form, and
  starts the preview. No network is contacted in any test.

## Limitations and future evolution

- No real model provider yet (seam only) - the suggestions are deterministic, so this
  is a *feature* (offline, can't hallucinate an unsafe step), not a gap. A provider
  would later *phrase* the briefing/suggestions, never choose or rank them.
- **Recommendations, but never execution** - the AI proposes registered operations;
  the deterministic engine alone performs them, through an explicit, provenance-
  recorded Accept in the Workspace. There is no auto-apply and no chat.
- v2 ships two recommendation rules (plane level, reference normalize); more (phase
  unwrap on a wrapping signal, comparison/exploration suggestions) extend the same
  pattern.
- No per-sentence narrative verification (see Grounding strategy).
- Deferred panel sections from the original sketch (Recommended Reading, Relevant
  Literature) are intentionally out of scope here.
