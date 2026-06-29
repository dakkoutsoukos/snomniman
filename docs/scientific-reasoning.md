# The Scientific Reasoning Rule Engine (`snomniman.ai.reasoning`)

> Status: **implemented** (ADR-0023). Qt-free; deterministic; consumed by the AI
> Scientist's "Suggested Next Steps" (ADR-0022). **No model dependency.**

This is the layer that encodes *how an experienced SNOM researcher decides what to do
next* - as deterministic, inspectable rules, not as an LLM's opinion.

## Philosophy

The motto (now in `CLAUDE.md`):

> **Scientific judgment is deterministic whenever possible. AI exists to communicate,
> contextualize, and teach - not to replace scientific reasoning.**

There are three deterministic tiers in SNOMNIMAN, and reasoning is the third:

| Layer | Question it answers | Module |
|---|---|---|
| Diagnostics | *What is true about this measurement?* (computed facts) | `snomniman.diagnostics` |
| Reasoning | *What should happen next, and why?* (scientific judgment) | `snomniman.ai.reasoning` |
| Processing | *Do it* (the actual, recorded operation) | `snomniman.processing` |

The reasoning engine is the **scientific authority** for "what next" (CLAUDE.md AI
rule 3: deterministic systems *choose*; AI *explains*). Two years from now, "why did
SNOMNIMAN recommend leveling?" must be answerable without consulting a model - "because
the topography has a global tilt that accounts for ~51% of its height variation, the
operation applies, and it has not been applied yet" - and it is.

## What a rule is

A `ReasoningRule` is one unit of scientific judgment about one registered operation.
It is **data + a deterministic evaluation**, registered the same way an operation is:

```python
@register_rule
class PlaneLevelRule(ReasoningRule):
    rule_id = "reasoning.level_dominant_tilt"     # stable identity (traceability)
    step_id = "image.plane_level"                 # the operation it recommends
    summary = "Recommend plane leveling when a measured global tilt dominates ..."
    prerequisite_steps = ()                        # operations that must precede it
    excluded_steps = ()                            # operations it must not co-occur with

    def evaluate(self, ctx: ReasoningContext) -> RuleOutcome | None:
        ...   # reads only ctx (describe + diagnostics); returns a grounded outcome or None
```

A rule reasons **only** over a `ReasoningContext` - the Description API + Diagnostics
Engine projections, plus convenience accessors (`applicability`, `applied_steps`,
`channels`, `field_um`). It never touches raw arrays, never calls a model, never
executes anything (AI rule 1). When the deterministic facts support the step it returns
a `RuleOutcome` (confidence, rationale, source-tagged evidence, considerations, the
operation's pre-filled params, and the expected outcome); otherwise it returns `None`.

**A rule contains only the *scientific* trigger.** It does **not** re-check whether the
operation is structurally applicable or already applied - the engine enforces those
uniformly (see below), so each rule stays small and there is no duplicated logic.

## Rule lifecycle (the engine)

`recommend_workflow(dataset)` (in `recommend.py`) is the engine. For each registered
rule, in this order:

1. **Applicability guard** - skip unless the rule's `step_id` is *applicable* to the
   dataset (the Diagnostics Engine's capability check) and *not already applied* (its
   provenance check). This is why a rule never recommends an unavailable or
   already-done operation - it is structurally impossible, not merely discouraged.
2. **Prerequisite guard** - skip unless every `prerequisite_steps` entry is already in
   the provenance. A rule with an unmet prerequisite simply does not fire *yet*; once
   the prerequisite is applied, it surfaces. This produces a **naturally sequenced
   workflow across the process loop** (do A, then B appears) with no up-front ordering
   solver.
3. **Evaluate** - call `rule.evaluate(ctx)`; keep the `RuleOutcome` if non-`None`.
4. **Mutual exclusion** - of any two surviving proposals where one's `excluded_steps`
   names the other, drop the lower-confidence side.
5. **Order** - sort by `confidence` (descending) and return `WorkflowSuggestions`
   (the ranked recommendations, a `note` if empty, and the grounding `context`).

## Recommendation ordering and confidence

`confidence` is a deterministic **heuristic priority** in [0, 1] derived from the
strength of the evidence - **not** a probability (honesty about kind). It is surfaced
to the researcher as a strength tier (strong / moderate / tentative), never as false
precision. Ordering is by confidence; prerequisites add cross-iteration sequencing.

## The shipped rules

| rule_id | recommends | fires when | confidence |
|---|---|---|---|
| `reasoning.level_dominant_tilt` | `image.plane_level` | the signal topography has a measurable global tilt accounting for a meaningful share of its height variation | fraction of the height's RMS variation attributable to the tilt |
| `reasoning.normalize_with_reference` | `image.reference_normalize` | reference channels are present and complex optical signals are still raw | a fixed "standard practice" prior (0.85) - **unvalidated; under review** (see below) |

Both carry **considerations** - deterministic caveats the researcher should weigh
(e.g. normalization amplifies noise where the reference is weak; high leveling orders
can remove real curvature) - and **interaction-aware evidence** where deterministic
(reference normalization notes when leveling is already done).

> **Validation note (2026-06-29):** the `normalize_with_reference` confidence was
> investigated as a Scientific Validation milestone
> ([`reference-normalization-analysis.md`](reference-normalization-analysis.md), Outcome 2
> = DEFERRED). The study found that an evidence-based *positive* recommendation criterion
> cannot be validated on present data, and that the **flat 0.85 prior is not supported by
> the available evidence**: on every real measurement (all "Self-Reference Off") the `R-`
> channels are near-copies of the signal (`O/R ~ 1`), so normalizing would erase contrast.
> The rule is **left unchanged in that milestone** (a DEFER outcome ships no code), but its
> confidence should be revisited - the defensible near-term fix is a conservative *gate*
> (decline on a redundant / weak / noisy / empty reference - all deterministically
> detectable and validated) rather than a flat prior. See the analysis for the evidence.

### Deliberately *not* shipped yet (the discipline)

- **Phase unwrap** - a sound rule needs a *validated* deterministic "is this phase
  worth unwrapping" signal (a phase-wrapping diagnostic that distinguishes coherent
  wrapping from noise). Until that exists and is validated against a known answer
  (Rule 6), recommending phase unwrap would be guessing - so the rule is deferred, not
  faked. Adding it later is: ship the diagnostic, then `@register_rule` one class.
- **Crop** - cropping is driven by *user intent* (a chosen region), not by a
  deterministic property of the measurement. There is no honest trigger, so there is no
  rule. (Crop remains fully available in the Processing Workspace.)
- **Evidence-based reference-normalization confidence** - replacing the flat 0.85 prior
  with a graded, evidence-based confidence was investigated and **deferred** (Outcome 2,
  [`reference-normalization-analysis.md`](reference-normalization-analysis.md)). The
  *decline* conditions (redundant / weak / noisy / empty reference) are deterministically
  defensible and validated; the *positive* "this reference is meaningful, so normalizing
  helps" branch cannot be validated on present data (no genuinely-referenced measurement -
  appropriateness is an experimental-design fact the array does not encode). Adding it later
  is: obtain a referenced golden measurement, ship the reference-quality + redundancy facts,
  then a confidence-graded rule validated on both branches.

### Scope note on rule interaction (Rule 7)

The prerequisite/exclusion **mechanism** exists and is tested (with synthetic rules),
because it is cheap, matches the rule schema, and has a foreseeable consumer. But the
current four-operation vocabulary contains **no hard prerequisites or exclusions**, so
the shipped rules declare none. Relationships are modelled when they are *real*, not
speculatively - and a full dependency/ordering *solver* is intentionally **not** built;
the suppress-until-applied prerequisite rule already yields sequenced workflows.

## Relationship to the other layers

- **Diagnostics** (depends-on): reasoning consumes computed facts; it never recomputes
  them or reads pixels. If a rule needs a new fact, that fact is added to `diagnostics`
  (deterministic, validated), not inferred inside the rule.
- **Processing** (recommends-into): a rule's `step_id` + `params` point at a registered
  `ProcessingStep`. The engine never applies it; the researcher previews it in the
  Processing Workspace and Accepts (an explicit, provenance-recorded derivation). Adding
  an operation does not require a rule, and adding a rule does not change the operation.
- **The future AI Scientist / provider**: a narrative provider may *phrase* these
  recommendations into warmer prose - it must never *choose, rank, or invent* them. The
  reasoning engine is the authority; the LLM is its interpreter. The deterministic
  suggestions are always present (no provider required).

## Extension model

To teach SNOMNIMAN a new piece of best practice:

1. Ensure the trigger is a **deterministic fact** (extend `diagnostics` if needed,
   with a known-answer test).
2. Subclass `ReasoningRule`: set `rule_id` / `step_id` / `summary`, declare any real
   `prerequisite_steps` / `excluded_steps`, and implement `evaluate` to return a
   grounded `RuleOutcome` (or `None`). `@register_rule`.
3. Add a per-rule test (fires when it should, declines when it should) - rules are
   individually testable by construction.

No engine change, no GUI change (the recommendation flows through the existing AI
Scientist panel into the Processing Workspace), no AI retraining.
