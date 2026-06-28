# Next Scientific Priorities (classifying three candidate capabilities)

> **Status:** triage milestone of the Scientific Validation Phase
> ([`scientific-validation.md`](scientific-validation.md)). **Date:** 2026-06-28.
> **No code is written by this milestone.** Its deliverable is a *decision* about each
> candidate: implement now, validate next, or wait - and why.
>
> This document is an **application of ADR-0025** (the Scientific Validation methodology),
> not a new decision: it introduces no new governance, architecture, or abstraction and
> therefore **requires no ADR of its own.** It is the bridge between the product roadmap
> ([`beta-readiness-v1.md`](beta-readiness-v1.md)) and the scientific process
> ([`scientific-validation.md`](scientific-validation.md)).

This document answers one question for three proposed capabilities - **Line Flatten**,
**Harmonic Ranking**, and **Reference Normalization Criteria**: *what kind of work does
each actually require next?* That is deliberately not the same as "are all three good
ideas." Some work is **engineering** (the science is settled; build it). Some is
**scientific research** (a judgment must be validated before it can be automated). Some
is **product sequencing** (justified, but it should wait behind a dependency).

It is governed by the project's two permanent planning systems and their load-bearing
order ([`CLAUDE.md`](../CLAUDE.md), "Planning and Governance"):

1. **Beta Readiness** ([`beta-readiness-v1.md`](beta-readiness-v1.md)) decides whether a
   capability is *needed* by a real workday.
2. **Scientific Validation** ([`scientific-validation.md`](scientific-validation.md))
   decides whether a *scientific judgment* can be *defended*.
3. Implement only at the intersection - **needed AND (settled or validated)** - and only
   by extending an existing abstraction (Rule 7).

The project maxim is the tie-breaker throughout: *"I'd rather the engine recommend two
things it can defend than four it can't."* Honest deferral is a successful outcome.

---

## The classification framework

Each candidate is placed in exactly one category.

| Category | Meaning | What happens next |
|---|---|---|
| **A - Ready for Implementation** | The science is established; this is an engineering task. No Scientific Validation study is required. | Build it (with the ordinary analytical/golden DoD that *every* operation gets). |
| **B - Ready for Scientific Validation** | The capability is valuable, but the deterministic criterion or recommendation logic is not yet validated. | Open a `docs/<topic>-analysis.md` study; the recorded Outcome is the deliverable. |
| **C - Not Currently Justified** | Present evidence supports neither implementation nor a study. | Document why; ship nothing. |

**The crucial distinction that separates A from B (from
[`scientific-validation.md`](scientific-validation.md) Section 1):** the Validation Phase
gates **automated scientific judgment** - a fact the engine *asserts*, a step the engine
*recommends*. It does **not** gate a **manual operation** the researcher explicitly
chooses, previews, and applies with full provenance. An operation is a tool; a
recommendation is a judgment. This is why `image.phase_unwrap` ships and is fully usable
while its *auto-recommendation rule* is deferred. The same line decides Candidate 1.

### One-sentence verdicts

| Candidate | Category | Verdict |
|---|:--:|---|
| **1. Line Flatten** | **A** | Settled SPM science and a Critical beta blocker - **implement now** as a `ProcessingStep`; no validation study. |
| **2. Harmonic Ranking** | **B** | A real need whose signal-vs-noise criterion is exactly the judgment Diagnostics has so far declined to assert - **open the validation study next**. |
| **3. Reference Normalization Criteria** | **B** | The operation *and* a (flat-prior) recommendation already ship; validating *when to decline* is justified but should **wait behind Candidate 2**, whose noise-floor fact it can reuse. |

None of the three is Category C. "Wait" (the success-criteria third bucket) is expressed
here as **sequencing within B** (Candidate 3 behind Candidate 2), not by forcing a
justified capability into C - doing the latter would itself violate scientific honesty.

---

## Candidate 1 - Line Flatten

**Classification: A - Ready for Implementation.**

### Evaluation

| Criterion | Assessment |
|---|---|
| Scientific maturity | **Settled.** Per-scan-line offset/bow removal (row alignment, "destriping") is a decades-old, universal SPM/AFM operation. |
| Literature | Extensive and standard (Gwyddion "Align Rows"/"Flatten"; SPM destriping; every vendor tool incl. neaPLOT). Nothing to discover. |
| Deterministic defensibility | **Total.** Subtract a per-row statistic - median (robust default), mean, or a low-order per-row polynomial. Closed-form, reproducible. |
| Analytical validation | **Available and easy** - a synthetic image with known per-row offsets is recovered exactly (the same pattern that validated `image.plane_level`). |
| Synthetic validation | Available (injected offsets + bow + features). |
| Real-data validation | Available (the CdO `Z` channel). |
| Product impact | **Critical** - beta blocker **C4** / gap **G4**, "the most-missed topography operation." |
| Workflow impact | **High and daily** - plane leveling alone cannot remove per-line offsets; without this, cleaning real scans forces an exit to another tool. |

### Rationale

Line flattening is the clearest possible "engineering, not research" case, and it sits at
the exact intersection the governance demands: **needed** (C4, the top product gap) and
**settled** (no open scientific question). The operation computes a per-row correction by
ordinary statistics; correctness is provable against a known answer. It is a genuinely
*new verb*, distinct from `image.plane_level`'s whole-surface fit - leveling removes one
global plane/polynomial; flattening removes **independent per-line** offsets that a single
surface fit cannot represent. That distinctness is what earns it a place (Rule 2): it is
not a re-parameterization of an existing operation.

**Possible vs. recommend (the split the project always makes):**

- *"Line flattening is possible / correct"* -> **settled; this candidate.** Build the
  operation.
- *"Line flattening should be auto-recommended"* -> a **separate, future Category-B**
  question (detecting line artifacts deterministically - a cousin of phase-wrapping and
  poor-scan detection). It is **not** part of this candidate and must not be smuggled in.
  Ship the manual operation now; defer any reasoning rule until a line-artifact diagnostic
  is validated. This mirrors phase-unwrap exactly.

Because the operation is a manual, previewed, provenance-recorded tool, it does **not**
pass through the Validation Phase - the standard operation DoD (an analytical known-answer
test, Rule 6) is the whole scientific requirement, exactly as for `plane_level` and `crop`
which shipped without a validation study.

### Recommended next milestone

Implement `image.line_flatten` per the existing operation template
([`processing-engine.md`](processing-engine.md)): a registered `ProcessingStep` with
`required_capabilities = (Capability.SPATIAL_2D,)`, a small `param_specs`
(method: median / mean / poly-degree-N; target channel defaulting to `Z`), an analytical
known-answer test, and its Knowledge Center article (the no-drift test will require one).
It appears in the generic Processing Workspace and Diagnostics applicability list with
**zero GUI code**.

### Effort

- **Engineering: low-to-moderate (~1-2 focused days).** One ~150-line step modeled on
  `plane_level.py`, one analytical test, one Knowledge article, doc/LOG/NEXT updates.
- **Scientific: effectively none.** Only the standard analytical validation that every
  operation receives - not a Validation-Phase study.

### Risks

- **Scope creep / premature generality (Rule 2, called out in
  [`NEXT.md`](../NEXT.md)).** Do **not** also add a `polynomial_flatten`, masking DSL, or
  feature-exclusion solver. Keep parameters minimal; a robust **median** default covers
  the dominant real case.
- **Subtracting real structure.** A per-row statistic can erase a genuine horizontal
  feature. Mitigated by the robust default, by it being user-chosen and previewed (what
  changes / what stays), and by the operation never touching the raw.
- **Conceptual overlap with `plane_level`** in the UI/Knowledge. Mitigated by writing the
  article to state the distinct purpose plainly (per-line vs. whole-surface).

### Dependencies

**None.** Reuses the processing engine, registry, generic Workspace, Diagnostics
applicability, Knowledge Center, and no-drift test. Independent of Candidates 2 and 3 and
implementable immediately.

---

## Candidate 2 - Harmonic Ranking

**Classification: B - Ready for Scientific Validation.**

### Evaluation

| Criterion | Assessment |
|---|---|
| Scientific maturity | **Mixed.** The *physics* (higher demodulation harmonics suppress far-field background) is well established; a *single-scan deterministic criterion* for "which harmonics are signal vs. noise" is **not** settled. |
| Literature | Strong on demodulation and background suppression (Keilmann & Hillenbrand 2004; harmonic-order selection practice); thin on a defensible single-measurement noise-floor threshold. |
| Deterministic defensibility | **The open question.** `diagnostics` already reports amplitude + decay ratio but *deliberately declines SNR* because "a true SNR needs a noise model or a signal-free region, neither available deterministically from a single image" (`descriptors.py`, ADR-0019). Ranking *is* that declined judgment. |
| Analytical validation | **Partial** - synthetic harmonics with an injected noise floor give known answers; the *real* noise model is the unknown the study must confront. |
| Synthetic validation | Available (orders that should rank as signal vs. as noise). |
| Real-data validation | **Plausibly both branches on existing data** - the CdO scan shows informative O1-O3 and near-noise O4/O5 (the phase-wrapping study already found O4's residues "100% in low-amplitude noise"). This is a real advantage over phase-wrapping, which lacked a positive-branch measurement. |
| Product impact | **High** - Beta Readiness **M4** ("signal-vs-noise channel triage"), which this **subsumes**; "Nothing marks which orders are signal vs. noise" is named friction (Section 1.3). |
| Workflow impact | **High** - relevant in every channel-browsing session (choosing the working harmonic is a first-five-minutes act). |

### Rationale

This is the textbook Category-B capability: clearly **needed** (M4; the named browsing
friction), but resting on a judgment the deterministic layer has **explicitly refused to
fake**. That refusal is the strongest possible signal that ranking must be *validated*,
not assumed. Beta Readiness itself pre-commits this: item 11 of its roadmap says a
signal-vs-noise triage must "run through the Scientific Validation process ... *before*
shipping any recommendation or marking. If it cannot be defended on present data, say so
and defer." [`NEXT.md`](../NEXT.md) names it the strongest next science candidate.

Crucially, this study may be *more* conclusive than phase-wrapping was, because the
existing CdO measurement plausibly exercises **both** branches - it appears to contain
both signal-bearing and noise-dominated harmonics on one real scan. That is exactly the
two-sided real-data validation the methodology requires and that phase-wrapping could not
achieve.

### The precise scientific question to investigate

> **Can the boundary between signal-bearing and noise-dominated optical harmonics be
> determined deterministically from a single measurement - without an external noise
> model - with enough confidence to rank or mark channels; and can that criterion be
> validated on real data on both branches (correctly identifying the signal harmonics AND
> correctly identifying the noise harmonics)?**

Candidate diagnostics for the study to weigh (literature-grounded, none invented here):
the **amplitude-decay curve flattening** as orders approach the noise floor (decay ratio
-> 1 signals "no further suppression, only noise"); **spatial structure / cross-order
coherence** (signal harmonics share spatial features and correlate across orders and with
topography; noise harmonics are spatially white); and an **amplitude-significance / noise-
floor estimate** from low-signal regions. The Decision states which single quantity or
defensible combination thresholds cleanly - or concludes honestly that none does (a valid
Outcome 2 or 3).

### Recommended next milestone

Open `docs/harmonic-ranking-analysis.md` from the Section 6 template of
[`scientific-validation.md`](scientific-validation.md) and work the lifecycle to a
recorded Outcome. **Diagnostics precede recommendations:** the first shippable artifact
(only on a defensible outcome) is a *fact* in `snomniman.diagnostics` (e.g. a per-harmonic
signal/noise classification or quality rank with known-answer tests); a marking or a
`ReasoningRule` follows only if the fact is validated on both branches.

### Effort

- **Engineering: deferred until the Outcome, then small.** If Outcome 1: a new diagnostic
  descriptor + function with known-answer tests (extends `harmonic_diagnostics`, which
  already computes amplitude/decay), an optional channel-list marking in the GUI, and
  optionally one `ReasoningRule`. **No engineering before validation.**
- **Scientific: substantial - this is the milestone's real cost.** A full study:
  literature review, candidate-diagnostic selection, analytical + synthetic known-answers,
  and two-sided real-data validation on the CdO scan.

### Risks

- **The honest outcome may be defer or stop.** The signal may not separate from the noise
  floor cleanly enough on a single scan (the very reason SNR was declined). Per the maxim
  that is a **success**, but it means no shipped feature - set expectations accordingly.
- **Two-sided validation could still fall short** if the CdO scan does not cleanly furnish
  both a known-signal and a known-noise harmonic; a second measurement may be needed.
- **Over-claiming.** "Rank" must mean a defensible quality ordering, never a precise
  numeric SNR the data cannot support (avoid the false-precision trap; mirror the
  confidence-as-tier discipline of the reasoning engine).

### Dependencies

- Builds on the existing `harmonic_diagnostics` (amplitude + decay already computed).
- Shares its core unknown - a deterministic **noise-floor / amplitude-significance**
  estimate - with Candidate 3; doing this study first can **produce the very fact
  Candidate 3 then reuses** (see "The shared thread" below). This is the main sequencing
  argument.

---

## Candidate 3 - Reference Normalization Criteria

**Classification: B - Ready for Scientific Validation** (lower urgency; sequence after
Candidate 2).

### Evaluation

| Criterion | Assessment |
|---|---|
| Scientific maturity | **Operation settled; the recommendation criterion is not.** `image.reference_normalize` ships and is validated (`(O/R)*R == O` to machine precision; phase becomes an explicit, recorded difference). The open part is *when normalizing is appropriate vs. misleading.* |
| Literature | Normalization practice is well documented; the failure mode (a weak/near-zero reference amplifies noise) is understood qualitatively and is already in the rule's `considerations`. |
| Deterministic defensibility | **Plausible and concrete** - reference-amplitude significance (the fraction of pixels where the reference is near the noise floor) is directly computable, unlike a generic SNR. |
| Analytical validation | **Available** - `O/R` is exact where `R` is significant; the noise-amplification regime as `R -> 0` is analytically characterizable. |
| Synthetic validation | Available (strong reference vs. weak/noisy reference, known answers). |
| Real-data validation | Available (the CdO scan carries `R_O*` references to inspect for weak regions). |
| Product impact | **Low-to-moderate** - the operation **and** a recommendation already ship; this *refines the honesty* of an existing rule rather than filling a gap. |
| Workflow impact | **Moderate** - prevents the engine from confidently recommending normalization when the reference is too weak to trust. |

### Rationale - separating the two claims (as the brief requires)

- *"Reference normalization is possible."* -> **Already true and shipped.** The operation
  exists, is capability-gated (`COMPLEX_OPTICAL`, `REFERENCE`), and is analytically
  validated. This half needs nothing.
- *"Reference normalization should be recommended."* -> **Already happening, but on an
  unvalidated basis.** `ReferenceNormalizeRule` (`reasoning.normalize_with_reference`)
  fires whenever references exist and signals are still raw, at a **flat confidence of
  0.85** - a "standard-practice prior," not a measured criterion. It does **not** check
  whether the reference is actually strong enough for the division to be meaningful; the
  weak-reference failure mode is only a *caveat string*, never a *gate*.

So the open question is narrow and real: **should the recommendation ever decline (or
down-weight) when the reference is too weak - and can that boundary be drawn
deterministically?** Today the engine recommends normalization with the same 0.85
confidence on a pristine reference and on a noise-dominated one. The project maxim favors
investigating whether that uniform confidence is defensible.

> **The scientific question:** *When is dividing an optical order by its reference
> scientifically appropriate (the reference is a meaningful common-mode response) versus
> misleading (the reference is near the noise floor, so the division injects noise) - and
> can that distinction be made deterministically and graded into the recommendation's
> confidence?*

**Why B and not C.** A reasonable Category-C argument exists - "0.85-as-standard-practice
is fine; refining it is gold-plating." It is rejected, narrowly, because the current rule
can *confidently recommend a step that would mislead* on a weak reference, and tightening
that is a genuine honesty improvement, not a cosmetic one - squarely the kind of judgment
this phase exists to validate. It is **B with low urgency**, not C.

### Recommended next milestone

After Candidate 2 reports, open `docs/reference-normalization-analysis.md`. Most likely
shippable artifact (on a defensible outcome): a deterministic **reference-quality fact**
in `diagnostics` (reusing the noise-floor/amplitude-significance work from Candidate 2),
then a ~10-line refinement of the existing `ReferenceNormalizeRule` to **grade or gate**
its confidence on that fact instead of a flat prior. No new operation; no new subsystem.

### Effort

- **Engineering: small (after validation).** A reference-quality diagnostic with
  known-answer tests, plus a confidence refinement to one existing rule. The doc already
  notes a rule change is roughly a ten-line edit.
- **Scientific: moderate.** A focused study - smaller than Candidate 2 because the failure
  mode is concrete (weak reference) and the candidate diagnostic (reference-amplitude
  significance) is well-defined and analytically tractable.

### Risks

- **Possible Outcome: confirm the prior.** The study may conclude the flat 0.85 is
  acceptable and a gate adds little. That is a legitimate, honest result - it retires the
  question rather than shipping complexity.
- **Threshold subjectivity.** "Reference too weak" needs a defensible cut, not an
  arbitrary one - hence the dependence on the Candidate-2 noise-floor work.
- **Low marginal value if rushed** ahead of Candidate 2 - it would re-derive the same
  noise-floor machinery in isolation (a Rule-2/Rule-7 duplication risk).

### Dependencies

- **Sequenced after Candidate 2.** Both rest on the same unsolved primitive - a
  deterministic noise-floor / amplitude-significance estimate. Doing harmonic ranking
  first lets this study **reuse that validated fact** rather than reinvent it, and avoids
  building two parallel noise estimators (Rule 7).
- Reuses the shipped operation and the shipped reasoning rule (refines, does not add).

---

## The shared scientific thread (why the order is what it is)

Candidates 2 and 3 are not independent. Both reduce to the **one primitive the diagnostics
layer has so far declined to compute: a deterministic estimate of the noise floor /
amplitude significance from a single measurement** (ADR-0019's deferred SNR).

- Harmonic ranking asks: *which harmonics sit above the noise floor?*
- Reference-normalization criteria asks: *is this reference channel above the noise
  floor?*

These are the same measurement applied to different channels. Investigating harmonic
ranking first is therefore not just a priority call - it is the **dependency-correct**
order: it is the natural place to confront the noise-floor question head-on, and a
defensible result there becomes a reusable `diagnostics` fact that Candidate 3 consumes.
Doing Candidate 3 first would force it to solve the harder general problem in a narrow
corner and risk a parallel implementation (Rule 7). Settling the primitive once, in the
higher-impact study, then reusing it, is the disciplined path.

---

## Prioritized roadmap (what happens next, and why)

| # | Candidate | Category | Track | Action | Gate before it ships |
|:-:|---|:--:|---|---|---|
| 1 | **Line Flatten** | A | Product (C4) | **Implement now** - `image.line_flatten` + article + analytical test | Standard operation DoD (known-answer test) - no validation study |
| 2 | **Harmonic Ranking** | B | Science (M4) | **Open the validation study next** - `docs/harmonic-ranking-analysis.md` | Two-sided real-data validation; diagnostic fact before any rule/marking |
| 3 | **Reference Normalization Criteria** | B | Science | **Validate after #2**, reusing its noise-floor fact - `docs/reference-normalization-analysis.md` | A defensible reference-quality fact; otherwise confirm the prior and stop |

**Why this order:**

1. **Line Flatten is the only candidate that is both needed and already settled**, so it
   is the only one ready to *build*. It is also the highest-value product item of the
   three (a Critical beta blocker), reuses everything, and needs no GUI work. It should be
   the next thing implemented - in parallel with, and independent of, the science track.
2. **Harmonic Ranking is the strongest science-track milestone**: highest product impact
   among the unvalidated judgments (subsumes M4 and a named friction), the most
   foundational (it confronts the noise-floor primitive the other science item also
   needs), and - unlike phase-wrapping - plausibly validatable on both branches with
   existing real data. It should be the next *validation study* opened.
3. **Reference Normalization Criteria waits behind Harmonic Ranking**: it is justified (it
   would make an already-shipped recommendation more honest), but it is lower-urgency
   (operation and recommendation already work) and dependency-coupled (it should reuse,
   not duplicate, the noise-floor fact). It is the right *third* step, not a Category-C
   dismissal.

This is the dual-track governance working as designed: **the product track advances by
building settled science that researchers need (Line Flatten); the science track advances
by validating one judgment at a time, in dependency order, and accepting honest deferral
(Harmonic Ranking, then Reference Normalization).** Nothing here adds a subsystem; every
landing point is an existing abstraction (`processing` / `diagnostics` / `ai.reasoning` /
`knowledge`).

---

## What the project now knows (success-criteria check)

- **Implement next:** Line Flatten (Category A - settled science, Critical product need).
- **Enter Scientific Validation next:** Harmonic Ranking (Category B - precise question
  defined above; the noise-floor judgment Diagnostics has so far declined to assert).
- **Wait (then validate):** Reference Normalization Criteria (Category B, sequenced behind
  Harmonic Ranking to reuse its noise-floor fact rather than duplicate it).
- **Not justified (Category C):** none of the three - and none was forced into C to fill
  the bucket.

These three decisions are intended to drive the next several iterations. Re-evaluate the
order against fresh **Beta Readiness user-testing** evidence (Section 5 of
[`beta-readiness-v1.md`](beta-readiness-v1.md)): observed forced-exits reorder this
backlog faster than any internal analysis.

---

## See also

- [`scientific-validation.md`](scientific-validation.md) - the methodology and the
  three-outcome Decision step; the Section 6 template each Category-B study uses.
- [`beta-readiness-v1.md`](beta-readiness-v1.md) - the product roadmap (C4/G4 for
  Candidate 1; M4 for Candidate 2).
- [`phase-wrapping-analysis.md`](phase-wrapping-analysis.md) - the worked exemplar
  (Outcome 2); the model for both Category-B studies.
- [`diagnostics-engine.md`](diagnostics-engine.md) - where a validated fact lands; the
  ADR-0019 reasons SNR was deferred (the crux of Candidates 2 and 3).
- [`scientific-reasoning.md`](scientific-reasoning.md) - where a validated recommendation
  lands; the shipped `ReferenceNormalizeRule` this work would refine.
- [`processing-engine.md`](processing-engine.md) - the operation template Candidate 1
  follows.
