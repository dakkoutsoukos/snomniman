# Phase 4 - Scientific Workflow Automation (Research & Design)

**Status:** Research -> Design proposal. **No implementation.** **Date:** 2026-06-30
**Stance:** an s-SNOM / AFM / nano-FTIR researcher processing a *session of many
scans*, asked one question: *what repetitive scientific work should SNOMNIMAN
automate next, now that a single scan can be analyzed end-to-end?*

This document is a sanctioned exception to the standing rule "no new design
documents unless implementation exposes a real problem" (`NEXT.md`): it is the
research-and-design milestone the user commissioned. It contains **no code**,
proposes **no new architecture beyond one small, justified extension**, and is held
to the project maxim - *"two things we can defend over four we can't."* It is the
intended blueprint for all remaining Phase 4 work; ratifying it into `decisions.md`
/ `NEXT.md` / `LOG.md` is a separate, explicit act left to the user.

> **Naming note.** "Phase 4" here means *workflow automation*, the user's milestone
> numbering for this research track. It is distinct from `roadmap.md`'s long-arc
> "Phase 4 - Interactive GUI", which is a different (already in-progress) phase. The
> capability designed here was previously sketched as roadmap **Phase 6 (batch)**;
> this document brings that forward, scopes it honestly, and shows it is mostly the
> *activation of latent capability* rather than new construction.

---

## 0. The thesis, in one paragraph

SNOMNIMAN already lets a researcher take **one** measurement from raw to a
provenance-bearing figure: open, browse, compare, measure, diagnose, process
(Preview -> Accept, never mutating raw), and export. The next frontier is not a new
*capability* but a new *cardinality*: a research day is **many** sibling scans
(a power series, a time series, a sample series, a harmonic stack) that each need
**the same** processing. The dominant tedium - and the dominant reproducibility
risk - is repeating an identical sequence of operations by hand, scan after scan,
slightly differently each time. The honest, governance-aligned answer is to let the
researcher **capture a processing sequence once and replay it**: across the rest of
the session (a recipe), across a folder unattended (batch), and into a single
shareable summary (a report). Crucially, **this is reproducibility infrastructure,
not new science** - it makes no scientific judgment the user did not already make
and accept on the first scan. That single fact is what keeps Phase 4 on the right
side of every project rule.

---

## 1. The load-bearing distinction (read before everything else)

The task asks us to keep four things rigorously separate. They are the spine of this
document, so they are defined here once and used throughout.

| Layer | What it decides | Who authors the judgment | Where it lives today | Validation gate? |
|---|---|---|---|---|
| **Scientific processing** | *How* a single transform changes data (level, flatten, normalize) | The operation's author (validated once) | `processing` (`ProcessingStep`s) | Yes, per operation |
| **Scientific analysis** | *What is true* about a measurement (tilt, roughness, SNR, profiles) | The diagnostic's author (validated once) | `diagnostics`, `viz.measure` | Yes, per metric |
| **AI reasoning** | *Which* operation to consider next, and why | A deterministic `ReasoningRule` (AI only *phrases*) | `ai.reasoning` | Yes, per rule |
| **Workflow automation** | *Repeat a sequence the user already authored and accepted* | **The user** (by having run + accepted it once) | **Nothing yet - this is Phase 4** | **No - it makes no new judgment** |

The fourth row is the whole of Phase 4, and the last column is why it is tractable
and safe. A recipe replaying `plane_level -> line_flatten -> fix_zero` asserts
nothing new: the user chose those steps, those parameters, and accepted each
Preview. Replaying them on the next scan is *the same assertion, repeated* -
exactly what a provenance DAG exists to make reproducible. **Automation orchestrates
already-validated capabilities; it never invents a judgment**, so it does **not**
enter the Scientific Validation Phase (`scientific-validation.md`). The one place a
judgment *would* re-enter - *automatically deciding what a scan needs without the
user authoring it* - is precisely the line we must not cross (Section 2.5); that
remains AI-reasoning territory, deferred until validated.

This is the same discipline the project already applies to AI: *deterministic
systems choose; AI explains* (CLAUDE.md AI rule 3). Workflow automation adds a
quieter sibling: **the user chooses; the engine repeats.**

---

## 2. Deliverable 1 - Workflow Survey

### 2.1 Method

I enumerated the genuinely repetitive work in a near-field / scanning-probe lab -
not software features - and checked each against how the established tools support
it: **ImageJ/Fiji**, **MountainsMap** (Digital Surf), **Gwyddion**, **WSxM**, and
the vendor tool **neaPLOT**. The s-SNOM/nano-FTIR processing chain itself (background
suppression via higher-harmonic demodulation; normalization of signal harmonics to a
reference) is standard and is a documented *reproducibility* concern in the
literature - which is exactly why repeating it identically matters. Sources are
listed at the end of this section.

### 2.2 The repetitive workflows, ranked

> Each is rated by **frequency** (how often a working researcher hits it),
> **scientific value of automating it** (does it improve correctness/reproducibility,
> or only speed?), and **current SNOMNIMAN support**.

**W1 - Apply the same processing chain to every scan in a session.** *(Rank 1)*
- *Goal:* clean and quantify a set of sibling scans identically - e.g. topography
  `plane_level -> line_flatten -> fix_zero`, or each optical order
  `reference_normalize -> phase_offset` - so they are comparable.
- *Pain today:* the identical 4-6 clicks per scan, repeated 4-40 times; human drift
  in parameters between scans silently destroys comparability; no record that the
  *same* recipe was used on all of them.
- *Frequency:* **every session.** This is the single most common multi-scan motion.
- *Scientific value:* **high, and not merely speed** - identical processing is a
  *correctness* property for any cross-scan comparison (a power series, a before/after,
  a map of a parameter). Inconsistent manual processing is a real source of artifact.
- *Existing support:* MountainsMap **templates** (save a sequence, re-apply) - strong;
  ImageJ **macro recorder + replay** - strong but text/scripting; Gwyddion - **pygwy
  scripting only**; neaPLOT - weak, per-scan manual. **SNOMNIMAN: re-click per scan.**

**W2 - Process a folder of many scans unattended (batch).** *(Rank 2)*
- *Goal:* apply a fixed recipe to dozens-to-hundreds of measurement directories
  (a sweep, a time-lapse, a day's output) without sitting at the GUI.
- *Pain today:* GUI-bound, one scan at a time; cannot leave it running overnight.
- *Frequency:* per large dataset / per project (less often than W1, higher leverage).
- *Scientific value:* high - throughput **plus** a single reproducible run record
  (which recipe, which inputs, which versions, what failed).
- *Existing support:* ImageJ **Process > Batch > Macro** (folder in -> folder out);
  MountainsMap **batch + simultaneous processing**; Gwyddion **standalone pygwy**;
  neaPLOT - none to speak of. **SNOMNIMAN: `snomniman.batch` is an empty stub.**

**W3 - Generate a quantitative experiment summary / report.** *(Rank 3)*
- *Goal:* one shareable artifact for a collaborator / the PI / a paper's SI: a table
  across all measurements (roughness, tilt, harmonic signal/noise, ROI means) plus
  each scan's identity and provenance.
- *Pain today:* assembled by hand in Excel/Word; numbers retyped; provenance lost in
  the copy-paste.
- *Frequency:* end of experiment, for handoff / publication.
- *Scientific value:* high for **communication and defensibility** (extends the
  figure-regeneration story to a whole experiment); the numbers themselves are
  already computed and validated.
- *Existing support:* MountainsMap **auto-updating report documents** - strong;
  ImageJ Results table - partial; others manual. **SNOMNIMAN: `ExperimentModel`
  already builds the tables + CSV; there is no report *document* artifact.**

**W4 - Reproduce a figure / number set consistently across measurements.** *(Rank 4)*
- *Goal:* the same panel layout (O2 amplitude + phase + Z, same scale bar) and the
  same ROI-statistics table, for each sample in a figure series.
- *Pain today:* rebuild the figure per scan; re-draw the ROI; transcribe the stats.
- *Frequency:* paper/report time.
- *Scientific value:* consistency + provenance on every panel.
- *Existing support:* MountainsMap templates (strong); others manual.
  **SNOMNIMAN: figure export + CSV exist, one measurement at a time.** (Overlaps W1/W3:
  a "figure recipe" is a recipe whose last step is an export.)

**W5 - Bulk export / convert for downstream tools (Origin, Python, Gwyddion).** *(Rank 5)*
- *Goal:* write every processed channel of every scan to GSF/CSV/Zarr in one action.
- *Pain today:* per-file, per-channel manual export.
- *Frequency:* per project handoff.
- *Scientific value:* modest (logistics), but it is the literal **Workflow C
  switch-back point** in `beta-readiness-v1.md` - "process a day of scans and export
  for Origin/Python," named there as *the single most important obstacle to daily
  adoption.* Mostly a sub-case of W2 (batch with an export step).
- *Existing support:* all the comparison tools batch-export. **SNOMNIMAN: per-channel
  GSF + per-dataset Zarr exist; no bulk path.**

**W6 - Compare experiments / track a sample across sessions.** *(Rank 6, mostly covered)*
- *Goal:* apply last week's analysis to this week's sample and compare.
- *Existing support:* MountainsMap's *replace-the-raw-data, recompute* model.
- *SNOMNIMAN:* `ExperimentModel` already compares **within** a project (read-only).
  Cross-session comparison is a recipe (W1) + the existing experiment views; it needs
  little new. Listed for completeness, not as a Phase 4 driver.

### 2.3 Ranked summary

| # | Workflow | Frequency | Value of automating | SNOMNIMAN today | Phase 4 driver |
|---|----------|:---------:|---------------------|-----------------|:--------------:|
| W1 | Same chain on every scan | Every session | **High (correctness + speed)** | Re-click per scan | **Yes (4A)** |
| W2 | Batch a folder unattended | Per dataset | High (throughput + record) | Empty stub | **Yes (4B)** |
| W3 | Experiment summary / report | Per experiment | High (communication) | Tables/CSV only | **Yes (4C)** |
| W4 | Repeat a figure/number set | Per paper | Medium-high (consistency) | One at a time | Folds into 4A/4C |
| W5 | Bulk export/convert | Per handoff | Medium (the switch-back) | No bulk path | Folds into 4B |
| W6 | Cross-session comparison | Occasional | Medium | Mostly covered | Reuse, not new |

### 2.4 What the established tools teach (and where SNOMNIMAN can lead)

- **ImageJ/Fiji - the canonical UX.** *Record* a sequence as a replayable artifact,
  then *Process > Batch > Macro* it over a folder. The lesson: **the captured
  sequence and the batch runner are two halves of one feature.** Phase 4 should ship
  them as 4A (capture/replay) then 4B (batch the captured thing), in that order.
- **MountainsMap - the philosophical twin.** A document-based system where you build
  an analysis once, **save it as a template**, re-apply it to batches, and where
  **raw data stays unchanged and can be replaced to re-run the same pipeline on new
  input**, with **automatic recalculation** of dependents. This is *exactly*
  SNOMNIMAN's identity - "everything is a derivation of an immutable measurement"
  (`product-philosophy.md`) - and SNOMNIMAN's provenance DAG is a **better**
  substrate for it than a proprietary document model, because the derivation graph is
  already explicit, serializable, and audit-grade. A SNOMNIMAN recipe *is* a
  MountainsMap template, expressed as a re-bindable provenance sub-DAG.
- **Gwyddion - the bar to clear.** Batch in Gwyddion means **writing a standalone
  pygwy script** (glob a directory, `gwy_file_load`, `gwy_process_func_run`).
  Powerful, but it excludes every researcher who does not script. SNOMNIMAN can lead
  by making the *same* power **first-class in the GUI with full provenance** - no
  scripting, no lost lineage.
- **neaPLOT - the incumbent to displace.** The vendor tool offers little reproducible
  recipe/batch support; this is precisely the "Workflow C" daily-adoption gap
  `beta-readiness-v1.md` identifies. Automation is where SNOMNIMAN converts its
  reproducibility lead into a *daily* reason to switch.
- **The science itself is repetitive by construction.** The standard s-SNOM/nano-FTIR
  chain - higher-harmonic demodulation to suppress background, then normalization of
  signal harmonics to a reference (e.g. gold) for a reproducible scattering amplitude
  - is applied *per harmonic, per scan*, and the literature ties contrast
  reproducibility directly to applying that normalization *consistently*. Repeating
  it identically is not a convenience; it is method.

*Sources:* [ImageJ batch macro tutorial](https://imagej.net/tutorials/batch-processing-with-ij-macro),
[ImageJ Process>Batch](https://imagej.net/scripting/batch),
[Batch Processing Methods in ImageJ (Klemm & Miura)](https://link.springer.com/chapter/10.1007/978-3-030-76394-7_2),
[MountainsMap profilometry](https://www.digitalsurf.com/software-solutions/profilometry/),
[What's new in Mountains 8](https://www.digitalsurf.com/news/whats-new-in-mountains-8/),
[Gwyddion pygwy tutorial](http://gwyddion.net/documentation/pygwy.php),
[PyGwyBatch](https://github.com/onakanob/PyGwyBatch),
[High-fidelity nano-FTIR by on-pixel normalization of signal harmonics (Nanophotonics 2022)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11501567/).

---

## 3. Deliverable 2 - Automation Opportunities

For each workflow, *what* can be automated, the *deterministic boundary*, and the
*honest constraints*. Nothing below introduces a scientific judgment.

### 3.1 The Processing Recipe (capture + replay) - serves W1, W4

- **What it is.** An ordered, input-agnostic list of steps -
  `[(step_id, version, params), ...]` - i.e. **a provenance chain with its input
  leaf detached.** A recipe is *data*, not a script: it is the same `StepRecord`
  content the DAG already stores, lifted out and made re-bindable.
- **Capture.** Read it straight off a measurement's history. `summarize_provenance`
  already walks the DAG and returns ordered `LineageStep`s carrying exactly
  `step_id`, `step_version`, and `params`. Capturing a recipe is *projecting that
  list and dropping the `io.read` leaf.*
- **Replay.** For each step, rebuild it from the registry and apply it, threading
  each output into the next input: `get_step(step_id)(**params).apply({"primary":
  ds})`. The result is an ordinary derived `Dataset` with a fresh, correct provenance
  DAG - **indistinguishable from hand-clicking the same steps**, because it *is* the
  same calls.
- **Deterministic boundary.** Param validation (`ProcessingStep.validate`), capability
  checks (`required_capabilities` + `operation_applicability`), and the non-mutation
  contract all already hold per step. A recipe adds a *loop*, not a new rule.
- **Honest constraints (state them; they are the design):**
  1. **Multi-input steps.** Exactly **one** registered operation is multi-input:
     `image.arithmetic` (a `secondary` dataset input). Its `secondary` binding is
     *measurement-specific* and therefore not context-free. **Every other operation
     in the entire current vocabulary takes only the `primary` measurement** - so a
     portable, single-input **linear recipe covers the whole topography and optical
     chain today.** v1 recipes are exactly those single-`primary`-input chains;
     a step with a non-primary dataset input is either excluded from a portable recipe
     or carries an explicit per-run binding (deferred to 4B). This is a clean,
     defensible line, not a hack.
  2. **Applicability mismatch.** A recipe applied to a scan lacking a required
     capability (e.g. `line_flatten` on a scan with no topography) must fail *that
     step* honestly - the engine already raises `ProcessingError`; the runner reports
     "step k did not apply to measurement m" rather than guessing. No silent skips
     that change the science.
  3. **Versioning.** A recipe records each step's `version`. Replaying under a newer
     installed version is a provenance-visible fact (the DAG versions every step),
     consistent with the existing determinism policy - never papered over.
- **This is workflow automation, not AI:** the user authored and accepted these steps
  on the first scan; the recipe repeats *their* decision.

### 3.2 Batch (apply a recipe across many measurements) - serves W2, W5

- **What it is.** The body of the `snomniman.batch` stub, whose own docstring already
  declares the job: *"Applies a provenance DAG (or template) across many sources,
  emitting results, a per-result provenance record, and a run manifest."* Input: a
  recipe + a set of measurements (a project's measurements, or a folder of
  measurement directories via the reader registry). Output: one derived dataset per
  input (appended to each `Measurement`'s history), per-result provenance (free - it
  is in the DAG), and a **run manifest** (recipe identity, inputs, per-input
  success/failure, software versions).
- **Deterministic boundary.** Batch is a *loop + manifest + error policy* over the
  recipe runner. It computes nothing scientific.
- **Bulk export (W5)** is a batch whose terminal action is `export_channel_gsf` /
  `write_zarr` into an output directory - no separate subsystem.
- **Honest constraints:** local and serial in v1 (parallelism is a later optimization,
  Rule 1 - do not optimize before there is a measured need); a clear, recorded policy
  for partial failure (continue + report, never abort-silently).

### 3.3 Report / experiment summary - serves W3, W4

- **What it is.** Assemble *existing* read-only projections into one provenance-bearing
  document: the `ExperimentModel` tables (project-wide diagnostics + cross-measurement
  ROI/line statistics, already CSV-exportable), each measurement's identity +
  provenance (from `describe`), and selected figures (`viz.figure`, which already
  emits a regeneratable spec).
- **Deterministic boundary.** This is *projection and serialization*, not computation.
  Every number already comes from a validated source; the report only **arranges and
  attributes** them.
- **Honest constraints (this is the scope-creep risk - guard it):** a deterministic
  structured document (Markdown/HTML) + the existing CSV/figure artifacts; **no new
  metrics, no custom layout engine, no interactive report editor.** If it grows past
  "assemble what we already compute, with provenance," it has overreached.

### 3.4 What must **not** be automated (the deferrals that keep Phase 4 honest)

- **Auto-choosing a recipe for a scan** ("the software decides what processing this
  measurement needs"). That is **AI reasoning *choosing*** - it makes a new
  per-measurement judgment - and it stays in the validation-gated lane. The Reasoning
  Engine may *recommend one step with evidence*, and a future rule could even
  *suggest applying an existing, user-authored recipe*; neither may **fabricate and
  auto-run** a pipeline. The user authors the recipe; automation only repeats it.
- **Per-scan adaptive parameters** (e.g. "pick the flattening order per scan"). New
  per-measurement judgment -> validation-gated, not Phase 4.
- **A scripting / macro language or a plugin system.** A recipe is a *declarative step
  list*, deliberately **not** Turing-complete. Keeping it data (not code) preserves
  auditability and dodges Rule 7. A scripting API remains a separate, ADR-gated Phase
  8 question.

---

## 4. Deliverable 3 - Architectural Analysis

### 4.1 The central finding: Phase 4 is mostly *activation of latent capability*

The architecture was built, from Phase 1, to make this cheap. Three facts:

1. **The provenance DAG is already executable and persistable.** `processing/step.py`
   states it outright: steps are "both *data* ... and *behaviour*," the data half is
   JSON-serializable, behaviour is recovered from the registry - "making the
   provenance DAG both executable and persistable." Replay is the use this was
   designed for.
2. **The step list is already extracted.** `describe.summarize_provenance` returns
   ordered `LineageStep`s with `step_id`, `step_version`, and `params` - a recipe is a
   projection of this, minus the read leaf.
3. **The batch module is a deliberate empty stub** with the correct dependencies
   already declared (`batch -> pipeline, io, core`) and its responsibility documented.
   It was carved out *for this* and left unbuilt on purpose (Rule 7: build it when the
   need is concrete - it now is).

### 4.2 Reuse map - what already exists

| Need | Already provided by | Change required |
|---|---|---|
| Run one step | `processing` registry + `ProcessingStep.apply` | none |
| Validate params / check applicability | `validate`, `required_capabilities`, `operation_applicability` | none |
| Refuse incompatible inputs | `check_compatibility` (enforced in `apply`) | none |
| Extract an ordered step list | `describe.summarize_provenance` (`LineageStep`) | none |
| Per-result provenance | the DAG + `serialize_dag` | none (free) |
| Where results land | `pipeline.Measurement.datasets` history; `Project` | none |
| Persist results / sessions | `io.write_zarr` / `read_zarr`, `save_project` | none |
| Batch input from a folder | `io.read` reader registry | none |
| Report tables + cross-measurement stats | `gui/experiment.ExperimentModel` (+ CSV) | none |
| Report facts (identity, provenance, metadata) | `describe`, `diagnostics` | none |
| Report figures | `viz.figure` (+ provenance sidecar) | none |
| Preview / Accept derivation UX | the generic Processing Workspace | none |

### 4.3 The minimal additions actually required

Five additions, each extending an existing layer; **no new subsystem**, **no Qt in
the backend** (Rule 4), **no change to `core` / persistence**.

1. **A `Recipe` value object + JSON (de)serialization.** A small frozen dataclass:
   an ordered tuple of `RecipeStep(step_id, version, params)` plus light metadata
   (name, created_at, captured software versions, optional required-capability hint).
   It is a *detached, input-agnostic projection of a provenance chain.* **Lands in
   `pipeline`** (reproducibility infrastructure; it already depends on `processing` +
   `core` and owns `Project`/serialization). Optional `.snomrecipe` JSON file; can
   also be embedded in the `.snomproj` manifest. *Reuses the existing `StepRecord`
   shape - it is not a new serialization of an operation, just a re-bindable view.*
2. **A single-measurement recipe runner.** `apply_recipe(recipe, dataset) ->
   Dataset` (and a history-returning variant), threading steps through `apply` and
   surfacing per-step applicability. **Lands in `pipeline`.** Pure orchestration.
3. **The `batch` module body.** `run_batch(recipe, inputs) -> BatchResult`
   (per-input derived dataset + a manifest + a continue-on-error policy). **Fills the
   existing stub**, deps unchanged.
4. **A report assembler (4C, thin).** Composes `ExperimentModel` + `describe` +
   `viz.figure` into a structured document. **Lands as a thin addition reusing those
   layers** (candidate home: extend `describe` for the data document, `viz` for any
   rendered form; decide at 4C, keep it minimal). The most scope-creep-prone item -
   gate it hard.
5. **Thin GUI surfaces (presentation only).** "Save processing as recipe" (from the
   history), "Apply recipe..." (to current / selected measurements / a folder), a
   batch dialog + results summary, "Generate report...". All consume the backend; no
   scientific logic (Rule 4). A new recipe step appears in batch automatically,
   exactly as a new operation appears in the Workspace automatically.

### 4.4 What must **not** be added (Rule 7 discipline)

- No plugin / entry-point discovery (steps and recipes stay explicit data).
- No scripting language / macro DSL (recipe = declarative step list, not code).
- No new provenance schema (the DAG already represents all of this; a recipe is a
  *view* of it, and batch results are *ordinary* DAG nodes).
- No cloud / distributed / parallel batch in v1 (local serial loop; optimize only on
  a measured need, Rule 1).
- No change to `core`, `io` persistence, or the multi-input contract (all already
  present since ADR-0030 / OHD-2).

### 4.5 Architecture verdict

Phase 4 connects components that were designed to connect. Net new surface area: one
small `Recipe` dataclass, a runner loop, the batch body, a thin report assembler, and
thin GUI - and **no new scientific judgment**, so the Scientific Validation gate (the
one check that could block it) is never triggered. This is the cleanest possible fit
to "needed AND reuse-only," and it warrants **exactly one ADR** (Section 5.4).

---

## 5. Deliverable 4 - Phase 4 Roadmap

Three milestones emerge from the survey, in dependency order. Each lists objective,
value, complexity, dependencies, scope, and governance.

### 5.1 Phase 4A - Processing Recipes (capture + replay on one measurement)

- **Objective.** Capture a measurement's processing history as a portable,
  provenance-faithful recipe, and replay it onto another measurement through the same
  Preview -> Accept derivation path.
- **Value.** Removes the dominant per-scan tedium **and** upgrades cross-scan
  comparability from "hopefully consistent" to **guaranteed identical processing** -
  a scientific-integrity gain, not only a convenience. Directly serves W1/W4.
- **Complexity.** **Low-Medium.** New: `Recipe` + JSON I/O, `apply_recipe`,
  capture-from-history, thin GUI. Reuses the entire engine.
- **Dependencies.** `processing` registry, provenance DAG, `pipeline` - all present.
- **Scope.** Single-`primary`-input linear chains (the whole current vocabulary except
  `image.arithmetic`); honest per-step applicability reporting; a recipe round-trip
  golden test; a Knowledge Center article (the no-drift invariant will want one).
- **Governance.** **No Scientific Validation needed** (no new judgment). Reproducibility
  infrastructure. Passes the commit-value test on the workflow arm.

### 5.2 Phase 4B - Batch Processing (replay a recipe across many inputs)

- **Objective.** Fill `snomniman.batch`: run a recipe over a project's measurements or
  a folder of measurement directories, headlessly, emitting per-result provenance and
  a run manifest (which recipe, which inputs, success/failure per input, versions).
- **Value.** Closes the **single most important daily-adoption gap** in
  `beta-readiness-v1.md` (Workflow C: "process a day of scans and export for
  Origin/Python"). Throughput + an auditable run record. Reaches batch parity with
  MountainsMap/ImageJ and **exceeds Gwyddion** (first-class, no scripting). Bulk export
  (W5) is a batch with an export terminal step.
- **Complexity.** **Medium.** New: `run_batch` + `BatchResult`/manifest + error policy;
  GUI batch dialog + results table. Reuses 4A's runner, the reader registry, the
  `Project` model, Zarr.
- **Dependencies.** **4A** (recipe + runner).
- **Scope.** Local, serial; folder input via the reader registry; results appended to
  the project; explicit continue-on-error + manifest. Parallelism deferred (Rule 1).
- **Governance.** No new science.

### 5.3 Phase 4C - Automated Reporting / Experiment Summary

- **Objective.** Assemble a single provenance-bearing experiment report (structured
  document + existing CSV/figures) from `ExperimentModel` + `describe` + `viz.figure`.
- **Value.** End-of-experiment deliverable for collaborators / the PI / a paper's SI;
  extends figure-regeneration defensibility to a whole experiment. Serves W3/W4.
- **Complexity.** **Medium**, dominated by *scope discipline*, not algorithm. New: a
  thin report assembler + a GUI "Generate report".
- **Dependencies.** `ExperimentModel` (present); 4A/4B optional (a report can describe
  a hand-processed project too).
- **Scope.** Deterministic Markdown/HTML + the existing data/figure artifacts; **no new
  metrics, no layout engine, no interactive editor.** Defer anything beyond "assemble
  what we already compute, attributed."
- **Governance.** No new science; every number traces to a validated source.

### 5.4 Sequencing, governance gate, and deferrals

- **Run the user-testing protocol first.** `NEXT.md`'s current top priority is the
  Beta Readiness user-testing protocol (Section 5 of `beta-readiness-v1.md`). It will
  *confirm or re-order* this roadmap from real friction. Workflow C already predicts
  batch is the #1 multi-scan gap, but **watching real users order this backlog beats
  any internal critique** - the project's own stated discipline. This document is the
  blueprint to execute *once that signal confirms the multi-scan workday is the
  frontier* (it almost certainly will).
- **This is "beta-readiness-v2" territory.** v1 closed the *single-scan* workday
  (Critical C1-C4 + H1, done). Phase 4 is the *multi-scan* workday; re-running the
  review through that lens is the natural framing.
- **One ADR (proposed: ADR-0031).** Phase 4 introduces a new persisted artifact (the
  `Recipe`) and activates the `batch` module - a decision worth recording once
  (latest existing is ADR-0030). Recommended scope of the ADR: *recipes are a
  re-bindable projection of a provenance chain (not a new schema, not a script);
  batch is a serial local loop over the recipe runner; auto-selection of recipes is
  explicitly out of scope and remains validation-gated.*
- **Explicit deferrals (honest non-goals for Phase 4):** auto-recipe selection (AI
  *choosing* - validation-gated); per-scan adaptive parameters (new judgment);
  parallel/distributed batch (Rule 1); a scripting/macro API (Phase 8, its own ADR);
  spectroscopy/hyperspectral batch (needs the Phase 5/6 readers first - batch the
  *image* modality now, widen later for free since the runner is modality-agnostic).

### 5.5 Definition of done (per milestone)

Per `NEXT.md`: tests green (unit + invariant; a recipe **round-trip + replay-equals-
manual** golden test is the scientific-grade check here), `ruff` clean,
`mypy --strict` clean, the Qt-free invariant green, a Knowledge article where a new
user-facing capability lands, docs updated, `LOG.md` appended, `NEXT.md` refreshed.

---

## 6. Risks, open questions, and the honesty ledger

- **Scope creep in 4C (highest risk).** A "report builder" invites endless layout
  features. Mitigation: it may only *assemble and attribute already-computed facts*;
  if it computes or lays out, it has overreached. Consider shipping 4A+4B and letting
  user testing decide whether 4C is wanted before building it.
- **Multi-input recipes.** `image.arithmetic`'s `secondary` binding is the one
  non-portable case. v1 answer: single-`primary`-input recipes only; a binding policy
  for multi-input is a documented 4B follow-on, not a v1 promise. (This is a feature
  of the honesty, not a gap to hide.)
- **The "automation invites a recommendation" temptation.** The instant recipes exist,
  it is tempting to have the AI *pick* one. That crosses into validation-gated
  judgment. Hold the line: the user authors recipes; the engine repeats them; any
  *suggestion* to apply one is a future, separately-validated reasoning rule.
- **Determinism expectations.** Replay reproduces the *operations*, recorded with the
  installed step versions; bit-identity holds only for steps declared deterministic on
  a matching environment (the existing policy). Say so; never overstate (CLAUDE.md).
- **Open question for the user:** should a recipe live as a standalone `.snomrecipe`
  file, be embedded in the `.snomproj` manifest, or both? (Recommendation: both - a
  reusable file *and* a copy embedded in any project that used it, so a saved session
  is self-describing.)

---

## 7. Success criterion - the question this document answers

> *If SNOMNIMAN is already a mature scientific analysis environment, what repetitive
> scientific work should it automate next?*

**Repeating a researcher-authored processing sequence:** across a session (4A
recipes), across a folder unattended (4B batch), and into one shareable
provenance-bearing summary (4C report). This is the multi-scan workday - the W1/W2/W3
tedium that today sends a researcher back to MountainsMap or a pygwy script - and it
is the natural successor to the single-scan workday v1 already finished.

It is the right next thing for three reasons that are really one reason:

1. **It is the most repetitive real lab work** that SNOMNIMAN cannot yet do (W1/W2 hit
   *every session*), and it is the documented #1 daily-adoption gap (Workflow C).
2. **It is almost entirely reuse** - the DAG was built executable-and-persistable, the
   step list is already extracted, the batch module was carved out for it. The net new
   code is a small `Recipe` object, a loop, the batch body, and thin GUI.
3. **It introduces no new scientific judgment**, so it ships under the project maxim
   without touching the Scientific Validation gate - while *strengthening*
   reproducibility, the project's core promise, by making "the same processing on
   every scan" a guarantee rather than a hope.

Automation here is the quiet sibling of the AI principle the project already lives by:
*the deterministic layer is the authority; the user chooses, and the engine faithfully
repeats.* Phase 4 turns "I did the analysis, once, by hand" into "I can prove I did
**the same** analysis to **all of it** - and hand it over."

---

## Appendix A - A recipe, made concrete (illustrative, not implementation)

A captured topography-cleaning recipe, as the re-bindable projection of a provenance
chain it would be:

```json
{
  "format": "snomniman.recipe",
  "schema_version": 1,
  "name": "CdO topography clean",
  "created_at": "2026-06-30T...",
  "software": {"snomniman": "..."},
  "steps": [
    {"step_id": "image.plane_level",  "version": 1, "params": {"channel": "Z", "order": 1}},
    {"step_id": "image.line_flatten", "version": 1, "params": {"channel": "Z", "method": "median"}},
    {"step_id": "image.fix_zero",     "version": 1, "params": {"channel": "Z"}}
  ]
}
```

Replay, in spirit (each call already exists and already records provenance):

```text
ds = measurement.raw
for step in recipe.steps:
    op = get_step(step.step_id)(**step.params)      # registry + validate (exists)
    if not applicable(op, ds): report_and_stop(step) # operation_applicability (exists)
    ds = op.apply({"primary": ds})                   # non-mutating, DAG-recording (exists)
# ds is a normal derived dataset, indistinguishable from hand-clicking the chain.
```

The only genuinely new artifacts are the JSON shape above and the loop - everything
the loop calls is shipped, tested, and validated today.

## Appendix B - Cross-references

`CLAUDE.md` (Rules 1-9; the AI rules; the maxim) - `docs/product-philosophy.md`
("everything is a derivation of an immutable measurement") -
`docs/beta-readiness-v1.md` (Workflow C; G6 batch; the user-testing protocol) -
`docs/scientific-validation.md` (the gate this work does *not* trigger) -
`docs/processing-engine.md` (the step lifecycle a recipe replays) -
`docs/architecture.md` (the `batch -> pipeline, io, core` edge already drawn) -
`docs/decisions.md` (ADR-0030 multi-input; proposed ADR-0031 here) -
`src/snomniman/processing/step.py` ("the provenance DAG both executable and
persistable") - `src/snomniman/describe/summarize.py` (`summarize_provenance`) -
`src/snomniman/batch/__init__.py` (the stub this activates).
