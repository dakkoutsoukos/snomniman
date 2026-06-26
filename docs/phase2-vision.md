# Phase 2 Vision - The SNOMNIMAN Experience

**Status:** Product design (pre-GUI). **Last updated:** 2026-06-25

This document is the **experience blueprint** for SNOMNIMAN's interactive
application. It describes *what using the software should feel like* - the
workflows, the information a scientist sees, the way analysis and AI assistance
fit into a research day - **before any GUI code is written**.

It is deliberately implementation-agnostic. It does **not** specify widgets,
windows, toolkits, or layouts. A developer should be able to read it and
understand the experience to build, then choose the implementation. Where a UI
surface is mentioned, it is described by what it *does for the user*, never by how
it is built.

It complements, and does not replace:
- [`vision.md`](vision.md) - why the project exists, who it serves, the principles.
- [`architecture.md`](architecture.md) / [`data-model.md`](data-model.md) - the
  backend that *makes this experience possible* (provenance DAG, immutable raw
  data, typed metadata, structured AI). Every promise below is grounded in a
  guarantee the scientific core already provides.

> Per `vision.md`, we make claims about neaPLOT cautiously and only where
> confident. Below, friction is described as *common pain in vendor analysis
> tools* (including click-driven, hard-to-reproduce workflows). The goal is to
> **exceed** the incumbent on experience, not to disparage it.

---

## 0. Experience pillars

Six pillars govern every UX decision. They are the product principles of
`vision.md` made experiential.

| Pillar | What the user feels |
|---|---|
| **Transparent** | "I can always see what this is, what units it's in, and what was done to it." Nothing is hidden; nothing is silent. |
| **Reproducible** | "Anything I see, I can regenerate from raw - and so can a collaborator, years later." |
| **Fast** | "Exploring feels instant." Flipping channels, hovering pixels, navigating a cube never stalls. |
| **Exploratory** | "I can understand a measurement before I change anything." Inspection is safe and frictionless; raw data is never at risk. |
| **AI-native** | "An expert lab-mate is beside me" - grounded in my data's structure, never overriding it, always auditable. |
| **Publication-grade** | "What's on screen is already close to what goes in the paper" - correct units, scale bars, honest colormaps. |

### Two mantras

1. **"Nothing is hidden, nothing is silent."** Every transformation - a unit
   conversion, a phase unwrap, a normalization - is visible, named, and
   inspectable. The software never quietly alters data. This is the provenance
   DAG and the explicit-conventions model (OHD-6) surfaced as experience.
2. **"Explore before you process."** The first job of the tool is *understanding*
   the measurement. Looking, comparing, and reading metadata come before - and
   are independent of - any processing. The interactive application's first
   increment is therefore **read-only exploration** (see Section 8).

---

## 1. User personas

SNOMNIMAN must be powerful for experts and legible to newcomers. Six personas
span that range; each one's core need shapes a concrete design obligation.

### 1.1 The Newcomer (first-year graduate student)
New to s-SNOM. Does not yet know what `O2` vs `O3` means, why phase matters, which
harmonic carries the "real" near-field signal, or what a good scan looks like.
- **Needs:** sane defaults, plain-language explanations on demand, gentle
  guidance toward the channels and views that matter, and absolute safety (it must
  be impossible to corrupt or overwrite the raw measurement).
- **Design obligation:** the software *teaches by being used* - conventions,
  channel meanings, and metadata are surfaced and explainable, not assumed.

### 1.2 The Power User (experienced SNOM researcher)
Acquires and analyzes data daily. Knows exactly which harmonic, reference, and
normalization they want.
- **Needs:** speed and low friction (keyboard-driven, no repetitive clicking),
  trust that the tool is not silently transforming anything, repeatable pipelines,
  and batch application across many measurements.
- **Design obligation:** every common action is fast and scriptable/repeatable;
  the tool never gets in the way; transparency is never sacrificed for convenience.

### 1.3 The PI / Reviewer
Does not operate the instrument; reviews students' and postdocs' data and figures.
Time-poor.
- **Needs:** to quickly grasp "what is this measurement, is it sound, how was this
  figure produced," and to reproduce or audit a result without re-deriving it by
  hand.
- **Design obligation:** one-glance dataset summaries, one-click provenance, and
  effortless reproduction of any figure.

### 1.4 Facility / Beamline staff
Support many users and instruments; see many measurements.
- **Needs:** robust, forgiving import (including unfamiliar or partial datasets),
  fast quality triage of a measurement, and consistent handling across formats and
  modalities.
- **Design obligation:** import never silently mangles or guesses; unknown fields
  are preserved; quality and structure are assessable at a glance.

### 1.5 The Collaborator
Receives a shared dataset or project, often without the original instrument
software or the operator's knowledge.
- **Needs:** to open, understand, and reproduce someone else's work on their own
  machine, cross-platform.
- **Design obligation:** projects are self-explanatory and portable (open Zarr +
  JSON); understanding does not require the person who made the measurement.

### 1.6 The Future Self
The same researcher, three years later, reproducing their own published figure.
- **Needs:** to reopen a project and regenerate a figure exactly, with a readable
  record of every step.
- **Design obligation:** "reproduce in 3 years" is a routine, one-click operation -
  the headline promise of the whole platform.

---

## 2. Primary workflows

Workflows, not screens. Each is described by the user's **goal**, the **expected
sequence**, and the **pain points to eliminate**. They are ordered roughly as a
research day unfolds: understand, then compare, then assess, then process, then
publish, then share.

### 2.1 Open and orient - "What did I measure?"
- **Goal:** go from a folder on disk to understanding what the measurement is, in
  seconds.
- **Sequence:** point at a measurement folder -> every channel is discovered and
  presented automatically -> the key metadata (sample, scan size, pixels,
  excitation wavenumber, modulation mode, date) is immediately visible -> a
  default channel is shown with correct units and a scale bar.
- **Eliminate:** manual per-file opening; hunting for acquisition parameters in a
  separate text file; guessing units or orientation; any risk to the raw data.

### 2.2 Channel exploration and comparison - "Where is the signal?"
- **Goal:** find which harmonics and which quantity (amplitude vs phase) carry the
  meaningful contrast, and compare signal against reference.
- **Sequence:** flip through harmonics `O0..O5` / `M0..M5` instantly -> toggle
  amplitude vs phase of the same complex channel -> view several channels at once
  to spot which order has structure -> place a cursor and read the same pixel's
  value across *every* channel simultaneously.
- **Eliminate:** slow channel switching; losing cursor/zoom position when changing
  channels; having to mentally register one channel against another; phase shown
  with a colormap that misrepresents its cyclic nature.

### 2.3 Topography <-> near-field correlation - "Does the signal follow the structure?"
- **Goal:** understand how optical contrast relates to sample morphology.
- **Sequence:** view a near-field channel with the topography linked or overlaid ->
  navigate them together (shared zoom/pan and cursor) -> identify where optical
  features coincide with or diverge from height features.
- **Eliminate:** flipping between disconnected views; manual alignment; uncertainty
  about whether two images share the same coordinates.

### 2.4 Quality assessment and triage - "Is this scan good?"
- **Goal:** decide quickly whether a measurement is usable, and which of several
  runs is best.
- **Sequence:** scan for the tell-tale problems (noise-dominated harmonics,
  saturated or dead pixels, scan-line artifacts, drift, dead channels such as an
  all-zero phase) -> compare repeated runs of the same region side by side -> keep
  the good one.
- **Eliminate:** subjective, undocumented "looks fine" judgments; re-discovering
  the same artifact on every dataset; no way to compare runs directly.

### 2.5 Reproducible processing - "Transform it, transparently" *(later increment)*
- **Goal:** apply scientific processing (leveling, line correction, sample/
  reference normalization, explicit phase unwrap, spectral FFT) such that the
  result is fully auditable.
- **Sequence:** choose an operation -> preview its effect -> apply it as a **named,
  recorded step** that produces a *new* dataset (the raw is untouched) -> see the
  growing processing history as a visible chain -> reorder, remove, or tweak a
  step and watch downstream results update.
- **Eliminate:** destructive in-place edits; processing whose parameters are lost
  the moment it is applied; silent phase inversion/re-referencing/normalization;
  inability to answer "how exactly did I get here?"

### 2.6 nano-FTIR spectral workflow - "From interferogram to spectrum"
- **Goal:** turn raw interferograms into corrected complex spectra, and explore
  hyperspectral cubes.
- **Sequence:** view an interferogram -> follow it through apodization, zero-fill,
  phase correction, FFT, and reference ratio as recorded steps -> for a cube, pick
  a pixel to see its spectrum, or pick a wavenumber band to see the spatial map,
  and scrub across wavenumber.
- **Eliminate:** opaque "magic" FFT buttons; uncertainty about which corrections
  were applied; clumsy navigation between spatial and spectral views of a cube.

### 2.7 Comparative and batch analysis - "Do this to all of them"
- **Goal:** apply one analysis consistently across many measurements and compare
  outcomes.
- **Sequence:** define an analysis once (interactively) -> apply it unchanged to a
  whole folder -> review the batch results together, each carrying its own
  provenance -> compare datasets side by side.
- **Eliminate:** repeating the same clicks per file; inconsistent handling between
  datasets; results with no record of how they were produced.

### 2.8 Publication figure export - "Make it paper-ready"
- **Goal:** produce a publication-quality figure from any view without leaving the
  application. (Detailed in Section 6.)
- **Sequence:** arrange the view -> export to a vector figure with correct physical
  scale bar, honest colormap, and units -> the figure carries its provenance.
- **Eliminate:** screenshotting; re-plotting in a separate tool; figures with no
  link back to the data or the steps that made them.

### 2.9 Share and reproduce - "Hand it over"
- **Goal:** give a collaborator (or future self) everything needed to understand
  and regenerate the work.
- **Sequence:** save a project (sources + provenance DAG + view state) -> the
  recipient opens it on any platform -> they inspect, reproduce, and build on it.
- **Eliminate:** dependence on the original operator or vendor software; "it only
  works on my machine"; lost analysis recipes.

---

## 3. Information architecture

The governing rule: **the scientifically load-bearing context is always visible;
raw density is available on demand.** Clarity is prioritized over density through
progressive disclosure - the default view is calm, and depth appears when asked
for. A scientist should never have to wonder about units, coordinates, or what
they are looking at.

### 3.1 Always visible (ambient context)
- **Dataset identity:** name, kind (image / spectrum / hyperspectral / ...), and
  whether it is **raw or derived**.
- **Active channel and its nature:** canonical name, whether it is complex
  (amplitude/phase) or real, its unit, harmonic order, and processing **state**
  (raw / referenced / normalized / unwrapped).
- **Conventions badge:** the canonical conventions in force - spatial unit **nm**,
  origin **lower-left**, **phase preserved as imported**. This makes OHD-6 a
  visible fact, not buried trivia.
- **Cursor readout:** under the pointer, the physical coordinate (x, y in nm; or
  wavenumber for spectra) and the value in the active channel (and, on request,
  every channel) with units.
- **Scale bar** on every image, in physical units.
- **Channel list:** all channels, sensibly grouped (optical `O0..O5`, mechanical
  `M0..M5`, references `R_*`, topography `Z` and its variants).
- **Provenance access:** the current processing state and a one-click path to the
  full history.
- **Display range / colormap** currently applied (so nothing about the rendering
  is a mystery).

### 3.2 On demand (progressive disclosure)
- **Full metadata inspector:** instrument, excitation, demodulation, scan
  geometry, acquisition parameters - each value with its unit and its **source**
  (the `.txt` parameter file vs. a per-channel header), and whether it has been
  edited (which would itself be a recorded step).
- **Verbatim vendor header:** the original, untouched header text, treated strictly
  as data.
- **Full provenance DAG:** the complete graph, navigable node by node.
- **Per-channel and per-ROI statistics.**
- **Comparison panels** for multiple channels or datasets.

The principle: **a newcomer sees a clean, labeled view; an expert is one click from
everything.** No essential scientific fact is more than a glance away, and no
screen is cluttered to achieve that.

---

## 4. Viewer vision

The ideal dataset viewer - described purely as experience. The backing data is
never mutated by viewing; exploration is always safe.

- **Instant channel switching.** Moving from `O2` to `O3` is immediate, with no
  reload and no flicker. Harmonics can be stepped through from the keyboard.
- **Synchronized cursor across channels.** Hovering one pixel reveals that same
  physical pixel's value in *every* channel at once - amplitude, phase, mechanical,
  topography - so relationships are read directly rather than reconstructed in the
  head. Zoom and pan are linked across channels viewed together.
- **Complex channels shown honestly.** Amplitude and phase are presented as the two
  views of one complex quantity - toggled or shown side by side - with a **cyclic
  colormap for phase by default**, because phase wraps. Unwrapped phase, when it
  exists, is clearly a *separate* channel produced by an explicit step.
- **Topography correlation.** Height can be overlaid as contours on, or linked
  beside, any near-field channel, navigated together.
- **Reference channels in context.** Signal and its reference (`O2` and `R_O2`)
  can sit side by side, making the basis for any future normalization obvious.
- **Multi-harmonic at a glance.** A compact "contact sheet" of all harmonics lets
  the user see immediately which orders carry signal and which are noise.
- **Fluid image navigation.** Smooth zoom and pan, fit-to-view and true 1:1 pixel
  modes, always in physical units; selecting a region for read-only statistics is
  effortless.
- **Metadata inspection in place.** Selecting any metadata field shows its value,
  unit, and origin, and whether it has been changed.
- **Provenance inspection in place.** The history is browsable as a graph; clicking
  any node answers "what step, what parameters, what software versions produced
  this?" The viewer can always answer "how was this exact view produced?"
- **Spectral and hyperspectral fluency.** For cubes: click a pixel to see its
  spectrum; choose a band to see its map; scrub across wavenumber to watch contrast
  evolve - spatial and spectral views always coupled.
- **Nothing auto-applied silently.** Any display scaling or range is shown and
  adjustable; what the user sees is labeled. The viewer renders honestly and never
  stands in for a processing step.

The feel to aim for: *napari-fluid* multi-dimensional exploration with the
*transparency of a lab notebook* - fast and visual, yet always honest about units,
conventions, and history.

---

## 5. AI experience

AI is a **first-class analysis subsystem**, not a chat bubble bolted on. It
augments the scientist's workflow and **never interrupts or overrides** it. The
design follows the AI Architecture Principles in `CLAUDE.md`: the scientific core
remains authoritative; AI consumes structured objects and produces structured,
auditable, provenance-aware outputs.

### 5.1 How AI fits in (posture)
- **Present but never in the way.** AI is available alongside the work (a companion
  surface, a command), not a modal that blocks the task.
- **Grounded in structure, not raw bytes.** Because the data model exists, AI
  receives a `Dataset`, its `Metadata`, its `Provenance`, channel list, and
  computed statistics - *structured objects*. This makes its help precise and
  specific to the measurement, not vague.

### 5.2 What AI does for each user
- **Summarize a measurement** (great for the PI and Newcomer): "150 x 150 over
  10 um, PsHet at 5973 cm^-1, CdO nanoparticles; `O2`/`O3` show strong contrast,
  `O5` looks noise-dominated, a reference is present." Plain language, grounded in
  metadata.
- **Detect anomalies and quality issues** (Facility staff, Power User): flag noisy
  harmonics, saturated or dead pixels, scan-line artifacts, drift, or a dead
  channel (e.g. an all-zero phase) - as **structured flags and annotations**, not
  just prose.
- **Recommend processing** (Newcomer, Power User): "phase appears wrapped - consider
  an explicit unwrap step"; "normalize `O2` by `R_O2`." Each recommendation is a
  *previewable suggestion* the user can accept, which then becomes an explicit,
  recorded operation - never auto-applied.
- **Compare datasets** (PI, Power User): "same region as yesterday's run, different
  wavenumber; contrast is higher here."
- **Explain metadata and concepts** (Newcomer): "what is tapping amplitude, and why
  does it matter here?" - turning the tool into a teacher.
- **Draft analysis notes and methods text** (everyone, especially at writing time):
  because the provenance DAG records every step, parameter, and version, AI can
  draft an accurate methods paragraph straight from it - inherently reproducible
  prose.

### 5.3 The rules made experiential (trust by construction)
- AI output is always **clearly marked as AI-derived** and visually distinct from
  measured values; it is never blended into the scientific data.
- An AI result that contradicts a measured value is shown as a **recommendation**,
  never a correction.
- When a user acts on an AI suggestion, it becomes an **explicit, user-initiated,
  provenance-recorded operation** - and the AI inference itself is recordable as a
  provenance node (what model, what inputs, what outputs).
- **Structured-first:** masks, flags, tables, and recommendations - things that can
  be versioned, stored, and displayed beside the data - are preferred over opaque
  free text.

The feel to aim for: a **knowledgeable lab-mate**, not an oracle. AI accelerates
understanding, triage, comparison, and writing; the scientist always decides, and
can always audit what the AI did.

---

## 6. Publication workflow

The path from measurement to paper-ready figure must stay **inside** SNOMNIMAN, so
the figure, the data behind it, and the recipe to regenerate it remain one thing.

- **Any view can become a figure.** Whatever is on screen - with its scale bar,
  colormap, units, and physical extent honoring the lower-left origin - exports to
  publication-quality vector output (PDF/SVG) or high-resolution raster.
- **Figures carry their provenance.** An exported figure is linked to the exact
  provenance DAG that produced it, so "regenerate this figure in three years" is a
  routine operation, and an accurate methods description can be drafted from it.
- **Honest, consistent visualization by default.** Cyclic colormaps for phase;
  perceptually-uniform maps for amplitude and topography; explicit, visible color
  ranges; physical-unit scale bars; no silent normalization. Good scientific
  visualization is the default, not an expert option.
- **Multi-panel and comparison figures.** Harmonics, signal-vs-reference, or
  several datasets can be assembled into a single paneled figure.
- **Data and report travel with the figure.** The underlying numbers (CSV / Zarr)
  and a human-readable provenance report can be exported alongside, so a reviewer
  or collaborator can verify the result.
- **Lab-consistent styling.** A group can define a figure style so every figure
  from the lab is visually consistent.

The promise: **a figure is never an orphan.** It always knows what data it came
from and how it was made.

---

## 7. Long-term vision

Five years on, if SNOMNIMAN has become the standard SNOM analysis platform, these
are the experiences that make researchers say *"I never want to go back."*

- **Reproducibility is effortless and total.** Every figure in every paper from the
  lab traces to raw data plus a recorded recipe; regenerating any of them is one
  click; methods sections largely write themselves. Reproducibility stops being a
  chore and becomes a property of simply using the tool.
- **It is the lingua franca of the field.** Collaborators exchange SNOMNIMAN
  projects - open Zarr + JSON - instead of opaque vendor files. Anyone, on any
  platform, can open, inspect, and reproduce a colleague's analysis without the
  original operator or instrument software.
- **It is fast and joyful for daily work.** Exploring a hyperspectral cube,
  flipping harmonics, and comparing runs feel instant. The tool gets out of the
  way; analysis becomes a flow state rather than a fight.
- **It is transparent by default.** Researchers never wonder "what did the software
  do to my data," because it always tells them - and never does anything silent.
  Trust is structural.
- **AI is a genuine research accelerant.** It triages a day's measurements, drafts
  summaries and methods text, suggests analyses, and compares against prior
  datasets - all grounded in structured metadata and provenance, all auditable.
  It amplifies the scientist without ever quietly deciding the science.
- **It evolves with the field.** New modalities (pump-probe delay, polarization,
  new vendors and instruments) slot in without redesign, and the community can
  contribute readers and analyses.
- **It teaches the next generation.** Newcomers learn s-SNOM *by using it*, because
  conventions, channel meanings, and explanations are surfaced rather than buried.

The deeper shift is cultural: from analysis as a private, click-driven,
hard-to-reproduce craft, to analysis as **transparent, shareable, reproducible
science.** That is the thing that makes people not go back.

---

## 8. Sequencing the experience (guidance for building)

This document describes the *destination*. The experience should be built in
increments that each deliver standalone value, honoring "explore before you
process":

1. **Interactive data exploration (read-only).** Open a measurement, browse and
   compare channels, inspect metadata and provenance, navigate images - **no
   processing, no AI authoring yet.** This alone is hugely valuable: it makes
   every later feature easier to build and debug, and it is the fastest path to
   "I can finally just *look* at my data."
2. **Reproducible processing.** Named, recorded steps producing new datasets;
   the visible history; preview-before-apply.
3. **AI assistance.** Summaries, anomaly flags, recommendations, drafted notes -
   structured and provenance-aware from the start.
4. **Publication and batch.** Paper-ready export with provenance; consistent
   styling; one analysis across many datasets.

Each increment is a thin vertical slice of the same coherent experience, not a
separate product.

---

## What this document is not

- Not a widget, window, or layout specification.
- Not a toolkit or implementation choice (no Qt, no class design).
- Not a mockup.
- Not an architecture change - it introduces no new decisions and reopens none.
  The architecture in `architecture.md` and the decisions in `decisions.md` stand
  unchanged; this document describes the *experience* those foundations enable.

When GUI work begins, this blueprint guides *what the experience should be*; the
architecture guides *how to build it*; and the roadmap (`roadmap.md`) sequences the
phases. A developer should be able to read this file and know what kind of tool
SNOMNIMAN is meant to be before writing a single line of interface code.

See also: [`vision.md`](vision.md), [`architecture.md`](architecture.md),
[`data-model.md`](data-model.md), [`roadmap.md`](roadmap.md),
[`decisions.md`](decisions.md), and the AI Architecture Principles in `CLAUDE.md`.
