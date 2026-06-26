# Product Philosophy - The Soul of SNOMNIMAN

**Status:** Foundational identity document. **Last updated:** 2026-06-25

This is the **highest-level design document** in the project: the one that defines
what SNOMNIMAN *is* and how a researcher should *think* while using it. It answers
"how should researchers reason about this software?" - not "what screens should
exist?"

Every other design decision - architectural, data-model, UI, AI, workflow - should
be checkable against this document. When a future choice is unclear, the question
to ask is not "what would be easy to build?" but "what does SNOMNIMAN's identity
demand here?"

It is implementation-agnostic by design: no toolkits, no widgets, no classes, no
screens. Those are downstream of identity.

### Relationship to the other documents

| Document | Altitude | Answers |
|---|---|---|
| **`product-philosophy.md`** (this) | The **soul** | What is SNOMNIMAN? How should a scientist think in it? |
| `vision.md` | The **why/who** | Why does it exist, for whom, what is success and out of scope? |
| `phase2-vision.md` | The **experience** | What should using it feel like (personas, workflows, viewer, AI)? |
| `CLAUDE.md` | The **constitution** | How do we *work* on it (rules, process, never-do)? |
| `architecture.md` / `data-model.md` | The **machine** | How is it built so the above is possible? |

The principles in `vision.md` and the experience pillars in `phase2-vision.md` are
**operational expressions** of the identity defined here. This document does not
restate them; it gives them a single root.

---

## 1. The core mental model

Every enduring tool has one unifying idea that the whole product hangs from:

| Tool | Mental model |
|---|---|
| VS Code | Everything is a file. |
| Photoshop | Everything is layers. |
| Blender | Everything is objects. |
| Git | Everything is commits. |

SNOMNIMAN's is:

> ## Everything is a derivation of an immutable measurement.

**The central object is the Measurement** - the raw output of the instrument, held
as immutable truth. **The central relationship is derivation** - everything a
researcher does (looking at a channel, leveling topography, normalizing by a
reference, extracting a spectrum, asking the AI to summarize, exporting a figure)
produces a **new result derived from the measurement**, and every derivation is
recorded and traceable back to its source.

You never *edit* a measurement. You *interrogate* it, and each answer is a derived
artifact that knows exactly where it came from.

```
            MEASUREMENT   (raw, immutable, content-hashed -- the source of truth)
                 |
     +-----------+-------------+--------------------+
     |           |             |                    |
  leveled Z   O2 / R_O2    point spectrum        AI summary
     |        normalized        |                (annotation)
   figure        |          baseline-corrected
              referenced        |
                 |            figure
              figure

  Every node records its parents, parameters, and software versions.
  Read upward from ANY artifact and you arrive back at the original measurement.
```

This is the Git insight applied to science: an immutable source plus a graph of
recorded derivations. It is what makes "reproduce this figure in three years" a
routine operation rather than a hope.

### Why "Measurement," and not the alternatives

This choice was deliberate. The candidates and why they were not chosen:

- **Dataset** - the right central object for the *architecture* (`data-model.md`),
  but the wrong one for a researcher's *mental model*. "Dataset" is how the
  software thinks; "measurement" is how a scientist thinks. A researcher says "my
  CdO measurement," never "my xarray-backed Dataset." Identity should speak the
  user's language.
- **Experiment** - too broad. An experiment carries hypotheses, controls, and
  often many measurements; modeling that would pull SNOMNIMAN toward being an
  electronic lab notebook, which `vision.md` places out of scope. An experiment is
  the *context* measurements live in, not the object the tool is built around.
- **Knowledge graph** - too abstract, and it is a *structure*, not an object a
  person holds. The derivation graph genuinely is a knowledge graph, but no
  scientist sits down thinking "I will build a knowledge graph today." Knowledge
  is what *emerges* as derivations accumulate; it is the outcome, not the handle.

So: the **Measurement** is the object the researcher holds; **derivation** is how
they relate to it; the **derivation graph** is the structure that results; and
**defensible understanding** is what it produces. "Dataset" is the technical
embodiment of a measurement-or-derivation inside the machine.

### What the model changes

Adopting this model has consequences that should ripple through every feature:

1. **Truth is sacred.** The original measurement is never altered, overwritten, or
   silently transformed. Everything else is downstream of it.
2. **"Where did this come from?" is always answerable.** Provenance is not a log
   bolted on afterward; it is the *connective tissue* of the whole product.
3. **All work is unified.** Channels, processing steps, AI outputs, and figures
   are not different kinds of thing - they are all *derivations*, carried in one
   graph, governed by one set of rules.
4. **The verb changes.** Users do not "edit data." They "derive understanding."
   That single shift - from destructive editing to recorded derivation - is the
   difference between a calculator and a scientific platform.

---

## 2. Enduring principles

These principles do not change as features are added. They are the laws of the
experience; every operational pillar elsewhere descends from them.

1. **The measurement is sacred.** Raw data is immutable. All work derives from it
   and never alters it. A user must never fear losing their original.

2. **Nothing is hidden, nothing is silent.** Every transformation - a unit
   conversion, a phase unwrap, a normalization - is visible, named, and
   inspectable. The software never changes the scientific meaning of data without
   saying so, explicitly, as a recorded operation.

3. **Explore before you process.** Understanding precedes transformation. Looking,
   comparing, and reading metadata are first-class, safe, and require no
   commitment. You can fully understand a measurement before changing anything.

4. **Provenance is the product, not a byproduct.** The recorded chain of
   derivations is as valuable as any single result. SNOMNIMAN treats history as a
   deliverable a scientist can read, share, and defend - not as exhaust.

5. **Every result can explain itself.** Any image, spectrum, number, or figure can
   answer, on demand: what am I, what are my units and conventions, and exactly how
   was I made? Nothing on screen is anonymous.

6. **AI augments understanding; it never owns the truth.** AI derives, proposes,
   and explains. It never asserts scientific authority, never overrides a measured
   value, and never acts on the science without the researcher. (See Section 3.)

7. **Reproducibility is structural, not aspirational.** "Regenerate from raw" is a
   property of how the system is built, not a discipline the user must maintain.
   Reproducibility happens by construction.

8. **Legible to newcomers, powerful for experts.** The same transparency that
   teaches a first-year student empowers a veteran. Clarity is never sacrificed for
   power, and power is never buried under simplicity.

9. **Honesty about kind.** Measured, derived, modeled, and AI-suggested artifacts
   are always distinguishable, and one is never silently promoted to another. The
   software is candid about what it knows, what it computed, and what it guessed -
   and it never guesses a missing value; unknown is shown as unknown.

---

## 3. Human + AI collaboration

Most scientific software is organized as:

```
Data  ->  Tools  ->  User
```

The user wields tools against data. SNOMNIMAN reorients this:

```
Data  ->  AI  ->  Human understanding
```

AI does the heavy lifting of *cognition* - reading everything, surfacing what
matters, drafting, explaining - so the researcher spends their attention on
*judgment* and *science*. This is a different philosophy, and it must be held with
discipline, because the heavy lifting AI does is **perception and preparation, not
authority**.

### The division of labor

| AI carries | The researcher keeps |
|---|---|
| Breadth - reading every channel, every metadata field, every prior dataset | Judgment - what the result means |
| Recall - "you saw something like this last month" | Hypothesis - what to ask next |
| First drafts - summaries, methods text, processing suggestions | Decision - what to accept, reject, publish |
| Vigilance - flagging anomalies, artifacts, dead channels | Authority - the final scientific claim |

AI is a tireless, knowledgeable lab-mate that has read all of your data and never
gets bored. It is **not** an oracle, and it is **not** the scientist.

### How the collaboration must feel

The researcher should come away feeling:

- **More capable** - they see and understand more than they could unaided, because
  the AI has read what no human has time to read.
- **Faster** - the drudgery of triage, comparison, and first-draft writing is
  lifted.
- **More confident** - the AI catches what they would miss, and because every AI
  output is grounded in structured data and is fully inspectable, they can verify
  rather than trust blindly.

And never **replaced** - because the AI proposes and the scientist disposes. An AI
suggestion only becomes part of the science when the researcher accepts it, at
which point it becomes an explicit, recorded operation initiated by them.

### The rule that makes it safe

AI consumes the structured objects SNOMNIMAN already produces - the measurement,
its metadata, its provenance - and returns structured, inspectable outputs that are
themselves recorded as derivations. Collaboration is built on **auditability**:
the human can always see the basis for what the AI said, and can always trace,
accept, or discard it. Trust is earned by transparency, not requested on faith.

> AI proposes. The scientist disposes. The measurement remains the arbiter.

---

## 4. Scientific trust

Trust is the currency of scientific software. A tool that produces a beautiful
result you cannot defend in review is worthless. SNOMNIMAN's deepest purpose is to
make every result **defensible** - believable, verifiable, reproducible, and
honest about its assumptions. Trust is built from:

- **Immutability** - users know their raw measurement is never touched, so there is
  nothing to fear and nothing to undo.
- **Provenance** - every result carries its full lineage; "how was this made?" is
  always answerable, down to parameters and software versions.
- **Explicit assumptions** - units, coordinate conventions, phase reference, and
  normalization state are stored and shown, never assumed and never guessed.
- **Transparent processing** - there are no black-box steps; every operation is
  named, inspectable, and reconstructable.
- **Inspectable AI** - AI never asserts from behind a curtain; it shows its basis,
  marks its outputs as AI-derived, and records what it did.
- **Reversibility** - because work is derivation rather than destruction, a user can
  always return to truth, re-derive, or branch a different way.
- **Validated correctness** - the software's own algorithms are verified against
  synthetic data with known answers, golden real files, and trusted references.
  Trust is *earned by verification*, not asserted by the vendor.

The throughline: SNOMNIMAN never asks the user to take its word for anything. Every
claim it helps a scientist make can be traced, checked, and reproduced. That is
what turns output into evidence.

---

## 5. Product identity

> **SNOMNIMAN is the software that turns a near-field measurement into
> understanding you can defend.** It treats raw data as immutable truth and
> everything learned from it as a transparent, traceable derivation - so every
> image, spectrum, number, and figure can explain what it is, what units it
> carries, and exactly how it was made. It places a tireless, knowledgeable
> assistant beside the researcher to do the heavy lifting of seeing, comparing, and
> explaining, while leaving every scientific judgment - and every claim to
> authority - with the human. It is fast enough to explore in, honest enough to
> publish from, and reproducible enough that a colleague, a reviewer, or one's
> future self can open the work years later and retrace every step back to the
> original measurement. SNOMNIMAN is not a viewer and not a calculator; it is the
> place where near-field data becomes trustworthy science.

---

## 6. Anti-goals

These are **identity** boundaries - what SNOMNIMAN must never become in
*character*, regardless of features. (They are distinct from the **scope**
non-goals in `vision.md`, which bound what the platform *does*: not acquisition,
not modeling, not cloud.) Each anti-goal below is the negation of a principle; if a
proposed feature pushes toward one of these, it is wrong no matter how attractive.

- **Never a black box.** It must never produce a result a user cannot inspect,
  explain, or trace. (Violates: nothing is hidden; every result explains itself.)
- **Never a silent processor.** It must never alter data, units, phase, coordinate
  conventions, or apply normalization without an explicit, recorded operation.
  (Violates: the measurement is sacred; nothing is silent.)
- **Never an AI oracle.** It must never let AI assert scientific conclusions as
  authoritative, override measured values, or act on the science unprompted.
  (Violates: AI augments, never owns.)
- **Never a vendor cage.** It must never trap a researcher's work in a proprietary,
  unreadable, or unportable form; projects are open and self-explanatory so anyone
  can open and reproduce them. (Violates: reproducibility; trust.)
- **Never a menu labyrinth.** It must never dissolve into feature-bloated,
  click-driven complexity where the mental model is lost under toolbars. Every
  feature must still be a *derivation of a measurement*; if it cannot be expressed
  that way, it does not belong. (Violates: a coherent mental model; legibility.)
- **Never a destructive editor.** It must never make a user fear losing their
  original data or their history. (Violates: the measurement is sacred;
  reversibility.)
- **Never a figure factory.** It must never optimize for figures that look
  impressive but cannot be reproduced or audited. A figure that cannot trace back
  to its measurement is a failure, however beautiful. (Violates: every result
  explains itself; provenance is the product.)

---

## Using this document

This is the lens for every future decision. Before adding a feature, changing a
workflow, or designing an interaction, run it through these questions:

1. **Does it keep the measurement sacred?** (No silent mutation of raw or of
   scientific meaning.)
2. **Is the result a traceable derivation?** (Can you read upward from it to the
   measurement?)
3. **Can the result explain itself?** (Units, conventions, lineage on demand.)
4. **Does AI stay an augmenter, not an owner?** (Proposes, records, never asserts.)
5. **Does it preserve the coherent mental model?** (Everything is still a
   derivation of a measurement - not a new, disconnected concept.)
6. **Would a reviewer trust it?** (Inspectable, reproducible, honest about kind.)

If a proposal cannot answer "yes" to all six, the design is not finished - or the
feature does not belong. When the answers are clear, the decision is usually clear
too. That is the point of having a soul: it makes the thousand small choices ahead
easier, because the project already knows what it is.

See also: [`vision.md`](vision.md), [`phase2-vision.md`](phase2-vision.md),
[`architecture.md`](architecture.md), [`data-model.md`](data-model.md), and the AI
Architecture Principles in `CLAUDE.md`.
