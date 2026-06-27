# The Measurement Explorer

**Status:** Interaction-design blueprint (pre-GUI). **Last updated:** 2026-06-25

This is the design blueprint for the **Measurement Explorer** - the central
experience of SNOMNIMAN, and the surface through which researchers open, navigate,
and *understand* a measurement. Everything else the platform does - processing,
AI, publication, batch - should feel like a natural extension of this experience.

It is the blueprint for all future GUI implementation. It is written at the
**interaction-design** level: it describes what the researcher experiences and how
they should think, never toolkits, layouts, or controls. Its job is to let several
developers independently build *compatible* interfaces that all preserve the same
product philosophy.

> **A note on scope.** This is intended to be the *last design document before
> building*. It is not more philosophy - it is the concrete bridge from
> `product-philosophy.md` to a running Explorer. After this, the highest-leverage
> work is implementation: finish the Phase-1 Zarr round-trip, then build the
> read-only Explorer described here.

**Primary reference:** [`product-philosophy.md`](product-philosophy.md). This
document must not contradict its principles; it *operationalizes* them:

- Everything is a derivation of an immutable measurement.
- Explore before you process.
- Nothing is hidden; every result explains itself.
- AI augments understanding.
- Provenance is always available.

See also [`phase2-vision.md`](phase2-vision.md) (broader UX vision) and
[`data-model.md`](data-model.md) (the channels, units, and provenance this
experience renders).

---

## 1. Explorer philosophy

**What it is.** The Measurement Explorer is where a folder of instrument files
becomes an *understood measurement*. It is the first thing a researcher opens and
the place they spend most of their time. It is not a file viewer (passive display
of images) and not "the whole application" (every capability) - it is the place
where **a measurement becomes understanding**.

**Why it exists.** Because understanding must precede transformation (*explore
before you process*). The hardest, most valuable early act in near-field analysis
is comprehension: what did I measure, where is the signal, is it any good, what
does the sample look like. Most tools rush past this to processing. SNOMNIMAN makes
exploration first-class, safe, and fast - the foundation everything else builds on.

**How it should feel.**
- **Like looking through the software at the measurement**, not operating
  software. The tool recedes; the science is the foreground.
- **Immediate.** Open a measurement and instantly grasp what it is - no import
  wizard, no configuration, no decoding cryptic filenames.
- **Safe.** Nothing done here alters anything (the raw measurement is immutable).
  The researcher can click, flip, hover, and wander fearlessly; exploration can
  never break or lose data.
- **Alive.** Flipping channels, hovering pixels, comparing harmonics - all
  instantaneous and fluid. Latency breaks understanding; the Explorer must feel
  like the data is under the researcher's fingertips.
- **Honest.** Everything carries its units, conventions, and lineage. The
  researcher never wonders what they are looking at.
- **Guided, not constrained.** Sane defaults surface what matters for a newcomer;
  an expert can reach anything.

In one line: **the Explorer turns a folder of files into an understood
measurement.**

---

## 2. The first five minutes

The single most important stretch of the entire product. Described as experience,
grounded in a real measurement (the CdO nanoparticle scan: 150 x 150 over 10 um,
PsHet at 5973 cm^-1, with optical orders O0-O5, mechanical M0-M5, references, and
topography).

**Second zero - opening.** The researcher points SNOMNIMAN at a measurement folder.
Immediately - with no wizard and no questions - the measurement appears as *one
coherent thing*, not 56 files. A sensible default channel is already on screen
(say, the optical amplitude that carries the contrast, or the topography),
correctly oriented with the lower-left origin, with a physical scale bar. The
ambient context tells them what this is at a glance: the sample name, 10 um field,
150 x 150 pixels, 5973 cm^-1, PsHet, the date. **They know what they are looking at
before they have done anything.**

**What they notice first.** The science - the image itself - with just enough
context to orient. Not a wall of controls. The measurement is the hero.

**What they naturally explore (and what the software lets happen effortlessly):**
- They **step through harmonics** - O2, O3, O4 - and instantly see which orders
  carry real contrast and which (O5) are just noise. The stepping is instant and
  keeps their zoom and position.
- They **toggle amplitude and phase** of the same optical channel and see phase
  rendered with a cyclic colormap, because phase wraps - it simply looks right.
- They **hover a nanoparticle** and read that exact pixel's value across *every*
  channel at once: optical amplitude, optical phase, topography height. The
  relationships between channels are read directly, not reconstructed in the head.
- They **glance at topography** and see the morphology, and that the near-field
  signal localizes on the particles.
- They notice the **references are present**, and the Explorer quietly indicates
  this measurement *can* be normalized - without pushing them to do it.

**How the software guides them.** Good defaults (the right channel, an honest
colormap, sensible scaling). A channel organization that mirrors the physics
(optical orders, mechanical orders, references, topography) so the structure is
obvious without decoding filenames. An optional, one-paragraph **AI orientation**
("strong contrast in O2/O3; O5 is noise-dominated; reference present; CdO
nanoparticles on a 10 um field") offered at the edge of attention, never blocking.
Everything labeled; nothing requiring a manual.

**By minute five** the researcher understands *what was measured, which channels
matter, what the sample looks like, and whether the scan is good* - having
processed nothing, opened no manual, and risked no data. (Compare the incumbent
experience, where five minutes in one is often still opening individual files and
hunting through a separate text file for the acquisition parameters.)

---

## 3. Information hierarchy

The governing rule from the philosophy: **nothing is hidden, but nothing is
overwhelming.** Information lives in three tiers by how often it is needed. The
scientific frame is always present; depth is layered behind calm, discoverable
gestures.

### Always visible (the scientific frame)
The context required to trust what is on screen, present at all times:
- **Measurement identity** - sample/title, kind (image / spectrum / ...), and
  whether this is the **raw measurement or a derived result**.
- **Active channel and its nature** - canonical name (e.g. `O2`), whether it is
  complex or real, whether amplitude or phase is shown, its unit, harmonic order,
  and processing **state** (raw / referenced / normalized / unwrapped).
- **Conventions in force** - nm spatial unit, lower-left origin, phase preserved as
  imported. Compact, ambient, never in doubt.
- **Cursor readout** - under the pointer: the physical coordinate (x, y in nm, or
  wavenumber) and the value(s) at that point, with units.
- **Scale bar** in physical units.
- **The channel set** - all channels, grouped by meaning, with the active one
  marked.
- **Current color mapping and range** - so the rendering is never a mystery.
- **A persistent provenance affordance** - "this is raw" or "derived from ..." -
  always one gesture from the full lineage.

### Quickly accessible (one gesture away)
The things a researcher reaches for many times an hour:
- **Channel comparison** - several channels at once, and a contact sheet of all
  harmonics to spot signal-bearing orders instantly.
- **The metadata inspector** - instrument, excitation, demodulation, scan
  geometry, acquisition - each value with its unit and its **source** (the `.txt`
  parameters vs. a per-channel header).
- **The provenance view** - the derivation graph (Section 4).
- **The AI companion** - summary and in-context questions (Section 5).
- **Statistics** - per-channel and per-region summaries.
- **Signal-with-reference** - any channel beside its reference.

### Rarely needed (available, never in the way)
- The **verbatim vendor header** text (treated strictly as data).
- Per-file detail, the directory manifest, and content hashes.
- Fine display controls (e.g. interpolation, gamma).
- Schema and software versions (which also surface inside provenance nodes).

**The test:** a newcomer sees a clean, fully labeled measurement; an expert is one
gesture from everything; and no essential scientific fact is ever more than a
glance away.

---

## 4. Navigation model

Navigation should feel *obvious* - the researcher should always know where they are
and how to get anywhere. There is one unifying metaphor that makes this true:

> **You are always somewhere in the derivation graph of a measurement.**

At the root is the immutable measurement. Around it are its **channels** (views of
the raw node). Branching from it are its **derivations** (processed results, AI
analyses, figures). "Up" always leads back toward the measurement; nothing is a
dead end; everything is connected and labeled.

Within that metaphor, each axis of movement has an obvious feel:

- **Channels and harmonics.** Stepping through harmonic orders (`O0..O5`,
  `M0..M5`) feels like turning a dial across an ordered sequence - instantaneous,
  preserving zoom and cursor. Amplitude and phase are a **toggle on one complex
  channel**, because they are two views of the same quantity, never two unrelated
  images.
- **Signal and reference.** A reference (`R_O2`) is "the same channel, on the
  reference," and sits one hop from its signal, because pairing them is the natural
  prelude to normalization.
- **Space.** Zoom and pan in physical units, with fit and true-pixel views and a
  persistent sense of location; linked across any channels shown together, so a
  feature stays registered as the researcher moves.
- **Metadata.** Browsed as meaningful groups rather than a flat dump; from any
  value, its source (and later its edit history) is one step away.
- **Provenance and derived datasets.** This is the spine. Derived results are not
  hidden in a separate list of files - they are **branches off the measurement**.
  The researcher moves outward from the raw measurement to any derivation, and back
  from any derivation to its parents. Selecting a node shows that artifact *and* its
  lineage. Building a processing result later simply grows this same graph.
- **Across measurements.** A measurement is the unit of work; moving between
  measurements (e.g. the four CdO runs) is lightweight, and comparing two is a
  natural gesture.

Because all movement happens inside one graph rooted at an immutable measurement,
navigation never fragments into disconnected modes. The researcher is never lost,
because there is always a visible path home to the measurement.

---

## 5. AI integration

AI is a first-class participant in exploration, not a chat box bolted to the side.
The key idea - and it falls directly out of the product philosophy - is:

> ## An AI result is just another derivation of the measurement.

It is not magic and not a separate system. An AI interpretation is a node in the
*same* derivation graph as a leveled image or a normalized spectrum, carrying the
same kind of provenance (which model, what inputs, what it produced):

```
Measurement
   |
   +-- leveled topography     (processing derivation)
   +-- normalized O2          (processing derivation)
   +-- publication figure     (export derivation)
   +-- AI interpretation      (AI derivation -- same graph, same provenance)
```

This single framing makes AI both **trustworthy** (auditable, provenance-bearing,
inspectable) and **architecturally clean** (no special case - it obeys the same
rules as every other result).

**How AI naturally participates while exploring.** Because AI consumes the same
structured measurement the researcher sees (its data, metadata, provenance,
channels, and statistics), its help is specific and grounded, and it is available
*in context* - about this region, this channel, this measurement - rather than in a
separate mode:
- **Orient** - a one-paragraph summary on open: "150 x 150 over 10 um, PsHet at
  5973 cm^-1, CdO nanoparticles; O2/O3 show strong contrast; O5 is noise; a
  reference is present."
- **Explain a region** - select a particle and ask "what is this?"; AI answers in
  context (high near-field amplitude localized on a topographic feature) as a
  structured annotation placed on the data.
- **Suggest channels** - "the meaningful contrast is in O2 and O3; O4-O5 are
  noise-dominated" - steering a newcomer to the right data.
- **Recommend comparisons** - "this resembles yesterday's run on the same ROI at a
  different wavenumber - compare?"
- **Answer provenance questions** - "how was this image made?" / "what has been
  done to this?" - AI reads the derivation graph and explains it in plain language.
- **Flag anomalies** - a dead channel (an all-zero phase), scan-line artifacts,
  drift, saturation - surfaced as structured flags on the data.

**The posture (from the philosophy, made experiential).** AI *proposes and
explains; it never asserts or alters.* Its outputs are clearly marked as
AI-derived, recorded as derivations, and fully inspectable. When AI suggests an
action - "this phase looks wrapped; consider an explicit unwrap" - accepting it
creates an explicit, **researcher-initiated, recorded** processing derivation: the
AI did not change the science; the scientist did, on the AI's advice. It should
feel like an expert collaborator who has already read every channel and every
metadata field, looking over the researcher's shoulder - making them faster and
more confident, never taking the science out of their hands.

---

## 6. Transparency

Transparency is an interaction guarantee, not a feature: **every artifact in the
Explorer can explain itself.** Selecting any result - an image, a number, a figure,
an AI note - answers three questions without the researcher leaving the flow:

1. **Where did I come from?** Its parent measurement and derivations - one gesture
   to the full lineage, always terminating at the immutable measurement.
2. **How was I produced?** The step(s), parameters, and software versions that made
   it - or, for an AI result, the model and the inputs it analyzed.
3. **What assumptions were made?** The units, coordinate conventions, phase
   reference, and normalization state in force - and anything unknown is shown as
   unknown, never invented.

Experientially this means: the conventions are always ambient, so units and origin
are never in question; the provenance is browsable and *readable* (a narrative a
researcher, collaborator, or reviewer can follow, not a cryptic log); and even
display choices (color range, scaling) are visible, so the researcher can always
tell measured from derived from AI-suggested from a mere display setting. **The user
should never feel lost** - from anywhere, they can answer "what am I looking at, and
how did it get here?"

---

## 7. Future growth

The Explorer must absorb every future capability *without conceptual redesign* -
and it can, because each addition is either a new **kind of measurement** or a new
**kind of derivation**, both of which the model already handles. The concepts
(measurement, channel/view, derivation, provenance, AI-as-derivation) are *closed*
under these additions - the test of a sound mental model.

- **Hyperspectral cubes** - a measurement with an added spectral axis. The same
  Explorer: navigate space and spectrum together (pick a pixel to see its spectrum;
  pick a band to see its map; scrub across wavenumber). Cursor, readout, and
  provenance extend naturally; no new metaphor.
- **Point spectra** - a measurement whose primary axis is wavenumber rather than
  x, y. Same identity, same metadata/provenance/AI; the view adapts to the data's
  shape (its capabilities), not a different application.
- **Processing pipelines** - processing produces derivations, which are already the
  spine of navigation. A pipeline is a path through the derivation graph; building
  one simply grows branches. "Explore before you process" means processing is
  entered *from* understanding, as a natural next step.
  *Realized:* the **Processing Workspace** (the Process tab) is one generic,
  registry-driven surface for *every* operation - it lists the registered steps
  (grouped, with availability and a plain reason when an operation does not apply),
  builds each parameter form automatically from the operation's `ParameterSpec`, and
  runs one identical Preview -> (what changes / what stays / the provenance to be
  recorded) -> Accept/Cancel flow that records a new derivation without ever touching
  the raw measurement. A newly added operation appears here with **no GUI work** -
  implement, register, declare its parameters and required capabilities, and it is
  immediately discoverable, configurable, previewable, and recordable. (Details:
  `docs/processing-engine.md`, "Processing Workspace".)
- **AI-generated analyses** - more derivations (Section 5), already first-class.
- **Publication workflows** - a figure is a derivation that carries its provenance;
  exporting creates a figure-derivation from the current understanding.
- **Batch operations** - applying a derivation-path across many measurements. Since
  a measurement is the unit and a derivation-path is reusable, batch is "apply this
  branch pattern to those measurements" - no new mental model.

Every future capability is an *extension of the same graph*, not a bolt-on. That is
what lets the Explorer remain simple while the platform grows.

---

## 8. What makes it better than neaPLOT?

Compared at the level of **experience**, not feature lists. (Per `vision.md`, we
speak about neaPLOT cautiously; the "frustrations" below are common friction in
today's vendor and click-driven analysis workflows, stated only where we are
confident, not specific claims about any one tool's internals.)

| Workflow | Friction today | How SNOMNIMAN removes it | Why it is fundamentally better |
|---|---|---|---|
| **Opening a measurement** | Files opened one by one; acquisition parameters live in a separate text file consulted by hand; "what is this?" is assembled mentally. | The measurement opens as one understood thing, with context and an optional AI orientation. | The unit of work is the **measurement**, not files. Understanding is immediate, not reconstructed. |
| **Finding the signal across channels** | Channel switching can be slow or lose context; correlating one pixel across channels is manual. | Instant channel stepping, a synchronized cross-channel cursor, a harmonic contact sheet. | The data's multi-channel nature is treated as **one object**; the tool does the cross-referencing. |
| **Knowing what was done / reproducing** | Provenance is opaque; reproducing a figure months later is hard; "how did I make this?" is often unanswerable. | Every result carries its lineage; reproduce-from-raw is structural. | Provenance is the **substrate**, not a feature you must remember to use. Trust and reproducibility come by construction. |
| **Processing transparency** | Steps can feel like opaque buttons; parameters and assumptions are easily lost; silent phase/normalization changes are a risk. | Every step is an explicit, named, recorded derivation; nothing silent; the raw is never touched. | You can always **defend the result** in review. |
| **Getting to a figure** | Often exported or screenshotted into a separate plotting tool, severing the figure from its data. | Figures are derivations with provenance, made in place, publication-honest by default. | The figure, its data, and its recipe are **one thing**. |
| **Onboarding** | Steep and manual-driven; conventions implicit. | Legible by design; AI explains; conventions surfaced. | The tool **teaches as it is used**; a newcomer is productive quickly. |
| **Understanding help** | No in-context expert; you rely on your own memory or a colleague's. | A grounded, auditable AI collaborator that has read every channel and field. | The scientist's perception and recall are **augmented**, never their authority replaced. |

The throughline: incumbent tools frame analysis as *operating software on files*.
SNOMNIMAN frames it as *understanding a measurement*, with transparency and
reproducibility as the substrate and AI as a grounded collaborator. The difference
is not a longer feature list - it is **what the activity fundamentally is.**

---

## 9. Product North Star

> After a full day inside SNOMNIMAN, a researcher should remember their
> *measurements*, not the software. They should recall that they understood their
> data faster and more deeply than ever before; that they never once worried about
> corrupting a file or losing track of how a result was made; that every image,
> number, and figure could tell them where it came from; that an expert
> collaborator was always at their side - making them faster and more confident
> without ever taking the science out of their hands; and that everything they
> produced was something they could hand to a colleague or defend to a reviewer
> without hesitation. The lasting impression should be quiet trust - the sense that
> the tool got out of the way and let them do better science. They should close the
> laptop thinking not "that was good software," but **"I never want to go back."**

This paragraph is the test for every future Explorer decision: if a proposed change
does not move a researcher closer to that day, it is the wrong change.

---

## Using this document

When GUI work begins, this blueprint defines *what the Explorer should be*;
`product-philosophy.md` defines *why*; `architecture.md` defines *how to build it*.
Build in the philosophy's order: the **read-only Explorer first** (open, navigate,
understand - no processing or AI authoring), because exploration is the foundation
every later capability extends.

A developer should finish this document able to evaluate any interface choice
against a single question: *does it help a researcher understand a measurement, with
nothing hidden and everything traceable back to immutable truth?*

See also: [`product-philosophy.md`](product-philosophy.md),
[`phase2-vision.md`](phase2-vision.md), [`vision.md`](vision.md),
[`data-model.md`](data-model.md), [`architecture.md`](architecture.md).
