# The Scientific Validation Phase (how scientific capabilities enter SNOMNIMAN)

> **The canonical methodology for adding scientific capability to SNOMNIMAN.** A
> diagnostic, a recommendation rule, or any automated scientific judgment enters the
> engine only after passing this process. **Implementation is the last step, never
> the first.** And **honest deferral - concluding that the evidence does not yet
> justify a capability - is a successful outcome of this process, not a failure.**
>
> **Status:** permanent project methodology (governance, not a one-off plan;
> ADR-0025). The worked exemplar is
> [`phase-wrapping-analysis.md`](phase-wrapping-analysis.md).

This document is the **scientific half** of SNOMNIMAN's permanent decision framework.
Its **product half** is [`beta-readiness-v1.md`](beta-readiness-v1.md): the Beta
Readiness Review identifies the *workflow gaps* that decide what is worth building;
this document decides whether a proposed *scientific* capability can be **defended**
well enough to build at all. They answer different questions and both must say "yes":

| Planning system | Asks | Decides |
|---|---|---|
| **Beta Readiness** ([`beta-readiness-v1.md`](beta-readiness-v1.md)) | *What do researchers still need?* | Product priority - which workflow gaps block a full day of real work. |
| **Scientific Validation** (this document) | *What can we honestly automate?* | Scientific justification - whether deterministic evidence supports a capability. |

**Only a capability that is both *needed* (Beta Readiness) and *validated* (this
process) should be implemented.** A needed-but-unvalidated capability is deferred
until the science is settled; a validated-but-unneeded one waits for a real consumer
(Rule 7). This is the dual-track governance that replaces speculative
feature-by-feature planning.

---

## 1. Why this phase exists - and why "Validation," not "Knowledge"

SNOMNIMAN's foundational development is complete: the architecture, the Measurement
Explorer, the deterministic processing engine, the Description API, the Diagnostics
Engine, the AI Scientist (Briefing + a deterministic Reasoning Rule Engine), and the
Knowledge Center are all in place. The bottleneck is no longer software architecture.
It is **deciding which scientific judgments SNOMNIMAN should make - and proving it can
make them defensibly.**

This phase was first framed as the "Scientific Knowledge Phase." It is renamed to the
**Scientific Validation Phase** because *validation*, not *accumulation*, is the
discipline that actually governs what enters the engine:

- **"Knowledge accumulation" centers collecting** - more facts, more articles, more
  rules. But the project maxim is the opposite of accumulation: *a missing capability
  is preferable to an unjustified one.* Success is not measured by how much the engine
  knows; it is measured by how much it can **defend**.
- **"Validation" centers the gate.** A capability does not enter because it is
  plausible or because it would be convenient to automate a workflow. It enters
  because analytical, synthetic, and real-data evidence justify it (Rule 6). The
  deliverable of each milestone is *an answer* - "yes, and here is the evidence" or
  "no, not yet, and here is why" - not a feature.
- **It removes a genuine naming collision.** The shipped **Knowledge Center**
  (`snomniman.knowledge`) is the in-app teaching subsystem - a different thing
  entirely. The *phase* that governs what science enters the engine is about
  validating judgments, not curating articles. "Validation" keeps the two distinct.

What this phase is **not**: it is **not** a gate on *manual capability*. A researcher
can run `image.phase_unwrap` by hand in the Processing Workspace even though its
automatic-recommendation rule is deferred. The gate is on **automated scientific
judgment** (a diagnostic the engine asserts as fact; a recommendation the AI makes),
never on a tool the researcher chooses to apply explicitly with full provenance.

---

## 2. The development workflow

Every future scientific capability follows this lifecycle. Read it top to bottom:
implementation is the final step, reached only if the evidence justifies it.

```text
        Scientific Question        "When should an expert recognize / recommend X?"
              |
              v
        Literature Review          establish the accepted science; borrow diagnostics,
              |                     do not invent metrics
              v
   Candidate Deterministic         what objective, reproducible quantity could decide
        Diagnostics                this? (a fact computable from the data, not a guess)
              |
              v
      Analytical Validation        does theory guarantee the diagnostic means what we
              |                     claim? (closed-form / known-answer reasoning)
              v
      Synthetic Validation         does it give the right answer on generated data with
              |                     analytically known ground truth? (Rule 6)
              v
   Real Measurement Validation     does it behave correctly on real measurements -
              |                     both where it should fire and where it should decline?
              v
           Decision                defensible + needed -> implement; defensible but not
              |                     yet real-data-validatable -> defer; not defensible -> stop
              v
    Implementation (only if         the diagnostic fact first, then (if warranted and
        justified)                  golden-validated) the recommendation rule + article
```

Two structural rules govern the order:

- **Diagnostics precede recommendations.** A deterministic *fact* ("the phase does
  not wrap," "the topography is tilted by 0.8 deg") can and should be validated and
  shipped before any *recommendation* that consumes it. The Diagnostics Engine is the
  scientific authority; a Reasoning Rule is a thin, explainable consumer of a fact
  that already stands on its own (ADR-0019 -> ADR-0023). Never ship a recommendation
  whose underlying fact has not itself passed validation.
- **Real-data validation is two-sided.** A rule must be validated where it should
  *fire* **and** where it should *decline*. Validating only the "decline" side (the
  trap phase-wrapping fell into - no real measurement that genuinely wraps) is
  insufficient to register a recommendation: the positive branch is unproven. This is
  the most common reason a defensible criterion is still deferred.

---

## 3. Engineering principles (permanent)

These restate, for the scientific track, the project's Core Principles and the three
permanent AI rules (`CLAUDE.md`). They do not change; they are listed here so a future
contributor reads the validation discipline in one place.

1. **Scientific honesty takes precedence over feature count.** The number of judgments
   SNOMNIMAN can make *and defend* is the success metric - not the number of features.
2. **A missing feature is preferable to an unjustified feature.** When evidence is
   insufficient, the correct deliverable is to say so and not ship it - never to lower
   the scientific bar to automate a workflow.
3. **Deterministic diagnostics precede deterministic recommendations.** Establish the
   fact, validate the fact, ship the fact; only then build a rule on top of it.
4. **AI never substitutes for missing scientific evidence.** A gap in deterministic
   evidence is filled by *deferral*, not by asking a model to infer the judgment. AI
   reasons over facts SNOMNIMAN has established; it never manufactures them (AI rule 1).
5. **Scientific claims require deterministic support.** Anything the engine asserts as
   fact, or recommends as a next step, must be reconstructable from a deterministic
   computation over the data - auditable years later without "the model thought so"
   (Rule 6; AI rule 3 - deterministic systems *choose*, AI *explains*).
6. **Honest deferral is a successful scientific outcome.** "We investigated X, the
   criterion is sound, but it cannot be validated on real data yet, so we defer" is a
   complete and valuable milestone. It protects the engine's credibility.

> **The project maxim (the lens for every decision in this phase):**
> *"I'd rather the engine recommend two things it can defend than four it can't."*

---

## 4. The Decision step and its three outcomes

The Decision is not binary. An investigation ends in exactly one of three outcomes,
all legitimate:

- **Outcome 1 - Validate and implement.** The criterion is defensible *and* can be
  validated on real data on both branches (fire and decline). Ship the diagnostic
  fact; if a recommendation is warranted and a golden measurement validates it,
  register the `ReasoningRule`; add the Knowledge Center article. This is the only
  outcome that adds an automated judgment.
- **Outcome 2 - Defensible, but defer the rule.** The criterion is analytically and
  synthetically sound, but real-data validation of the positive branch is not yet
  possible (e.g. no real measurement exercises it). Ship the *diagnostic fact* if it
  is independently defensible; **defer the recommendation rule** until the missing
  golden data exists. This is the phase-wrapping outcome
  ([`phase-wrapping-analysis.md`](phase-wrapping-analysis.md)).
- **Outcome 3 - Not defensible; stop.** The science does not support a deterministic
  criterion (the signal is indistinguishable from noise, the judgment is genuinely
  subjective, the metric was invented rather than established). Document why and ship
  nothing. This is a successful milestone: it prevents an unjustified feature.

Record the outcome and its evidence in a validation document (Section 6). Outcomes 2
and 3 are not failures to be retried until they "pass" - they are findings.

---

## 5. Where a validated capability lands (no new architecture)

The validation process produces science, not subsystems. A capability that reaches
Outcome 1 extends abstractions that already exist (Rule 7); it never adds a platform
layer:

| Validated artifact | Lands in | As |
|---|---|---|
| A deterministic **fact** | `snomniman.diagnostics` | a new descriptor / metric (ADR-0019) |
| A deterministic **recommendation** | `snomniman.ai.reasoning` | a registered `ReasoningRule` (ADR-0023) |
| The **teaching** for it | `snomniman.knowledge` | a curated `Article` (ADR-0024) |
| A new deterministic **operation** | `snomniman.processing` | a registered `ProcessingStep` (ADR-0021) |

Because the Diagnostics panel, the AI Scientist panel, the Processing Workspace, and
the Knowledge Center are all generic and registry-driven, a validated capability
surfaces in the Explorer with little or no GUI work. The architecture's job is done;
this phase only feeds it validated science. See
[`architecture.md`](architecture.md) ("Extending the system").

---

## 6. The Scientific Validation Template

Every investigation produces a `docs/<topic>-analysis.md` document with these nine
sections. Copy this skeleton; phase-wrapping is a filled-in example of it.

```markdown
# <Topic> Validation Analysis (a Scientific Validation milestone)

> Question: <the one-sentence expert judgment under investigation>
> Status: analysis only / implemented (Outcome N). No code unless Outcome 1.

## 1. Scientific question
   The expert judgment, decomposed into necessary / sufficient / ambiguous /
   impossible evidence classes. What would an experienced researcher actually look at?

## 2. Literature review
   The accepted science. Candidate diagnostics borrowed from the literature, with
   citations. (Do not invent metrics; ground them.)

## 3. Candidate diagnostics
   The specific objective, reproducible quantities considered, and which are kept vs
   rejected and why. Name the one (or the defensible combination) that could decide.

## 4. Analytical validation
   Does theory guarantee the diagnostic means what we claim? Closed-form arguments,
   known-answer reasoning, the conditions under which the implemented algorithm is exact.

## 5. Synthetic validation
   Results on generated data with analytically known ground truth - including cases
   that should fire and cases that should decline. A table of known-answer outcomes.

## 6. Real-data validation
   Results on real measurements, on both branches (where it should fire and where it
   should decline). State honestly which branch the available data can and cannot exercise.

## 7. Decision
   Outcome 1 / 2 / 3, with the explicit reasoning. If implementing, the criterion
   (triggers, thresholds, amplitude/quality masks, assumptions, confidence model).

## 8. Honest limitations
   What the criterion does not cover; the assumptions it rests on; the failure modes;
   what would make it wrong.

## 9. Future work
   What evidence would change the outcome (e.g. a specific golden measurement), and
   the concrete next steps when it becomes available.

## References
   The literature cited above.
```

---

## 7. The Future Scientific Validation Queue

Candidate investigations, **not yet started and not to be implemented** ahead of their
validation. Each enters through the process above and ends in one of the three
outcomes. Order is indicative; researcher feedback (Beta Readiness user testing) and
data availability reorder it.

| Candidate judgment | The question to answer | Notes / known blockers |
|---|---|---|
| **Harmonic ranking** | Which optical harmonics carry signal vs. noise, deterministically? | Subsumes the Beta Readiness "signal-vs-noise channel triage" (M4). A real workflow need; must pass validation before any marking/recommendation ships. |
| **Phase-wrapping recommendation** | When should phase unwrapping be auto-recommended? | **Outcome 2 already reached** ([`phase-wrapping-analysis.md`](phase-wrapping-analysis.md)): criterion defensible, rule deferred. Blocked on a genuinely-wrapping real golden measurement (nano-FTIR / interferometric). |
| **Reference normalization criteria** | When is normalizing an optical order by its reference appropriate (vs. misleading)? | The operation ships; the *judgment of when* is the open question. |
| **Poor-scan detection** | Can an unusable scan (instability, parasitic interference, tracking loss) be flagged deterministically? | Diagnostics currently defers SNR/clipping/drift as not-yet-defensible (ADR-0019); revisit under this process. |
| **Drift detection** | Can scanner/thermal drift be detected from a single scan or across siblings? | May require multi-scan or line-correlation evidence; literature review first. |
| **Tip-artifact detection** | Can tip-convolution / parasitic-scattering artifacts be recognized deterministically? | Likely hard; a strong Outcome 3 candidate. Investigate honestly rather than guess. |

This queue lives here as the canonical scientific roadmap; [`NEXT.md`](../NEXT.md)
points at whichever investigation is active.

---

## 8. How to use this document

- **Proposing a scientific capability?** Do not open an editor. Open a validation
  document from the Section 6 template and work the Section 2 lifecycle. The answer -
  including "no, not yet" - is the deliverable.
- **Prioritizing?** Cross-check against [`beta-readiness-v1.md`](beta-readiness-v1.md):
  a validated capability that no researcher workflow needs still waits (Rule 7); a
  needed capability that has not been validated still waits (the maxim). Implement only
  at the intersection.
- **Reviewing a shipped judgment in two years?** Trace it back to its validation
  document and its deterministic fact. "Why did it recommend X?" must always be
  answerable from evidence, never from a model.

See also: [`beta-readiness-v1.md`](beta-readiness-v1.md) (the product roadmap),
[`phase-wrapping-analysis.md`](phase-wrapping-analysis.md) (the worked exemplar),
[`diagnostics-engine.md`](diagnostics-engine.md) (where facts land),
[`scientific-reasoning.md`](scientific-reasoning.md) (where rules land),
[`decisions.md`](decisions.md) (ADR-0025), and `CLAUDE.md` (Core Principles, the
maxim, the three AI rules).
</content>
</invoke>
