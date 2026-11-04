# Phases 7-9 Master Roadmap: Automated Feature Analysis, Physics Modeling, and the Scientific Assistant

> **Status: Research & Design only. No code in this milestone.** This document is the
> requested integrated blueprint for the remainder of SNOMNIMAN's scientific evolution.
> It follows the same discipline as every prior design-only milestone
> (`deployment-strategy.md`, `phase4-workflow-automation.md`, `phase5-spectral-nanoftir.md`,
> `phase6-spectral-lineshape-analysis.md`): propose, do not implement; an ADR (where one is
> actually needed) is written when a phase is implemented, not now.

## 0. A note on numbering (read this first)

The commissioning brief asked for "Phase 6 - Automated Scientific Feature Analysis,"
"Phase 7 - Physics Modeling," "Phase 8 - Scientific Assistant." **Phase 6 is already
shipped** - `docs/phase6-spectral-lineshape-analysis.md`, the ratio -> smooth -> fit -> report
lineshape-analysis workflow, complete end-to-end (`LOG.md` "2026-07-14d," `NEXT.md`
"Spectral lineshape analysis track"). Reusing "Phase 6" for a different, unrelated
milestone would collide with a real, already-shipped body of work and break every existing
cross-reference to it (CLAUDE.md, NEXT.md, LOG.md, the Knowledge/Manual pages it produced).

This document therefore renumbers the three requested phases to continue the project's
actual sequence:

| Requested name | Renumbered to | Why |
|---|---|---|
| "Phase 6 - Automated Scientific Feature Analysis" | **Phase 7** | Phase 6 = spectral lineshape analysis (shipped, 2026-07-14). |
| "Phase 7 - Physics Modeling" | **Phase 8** | Follows Phase 7 in sequence. |
| "Phase 8 - Scientific Assistant" | **Phase 9** | Follows Phase 8 in sequence. |

(`docs/roadmap.md`'s own Phase 5-8 labels are already stale and superseded - see its
"Current driver" section and CLAUDE.md's note on `phase5-spectral-nanoftir.md`
"superseding the stale roadmap.md placeholder of the same name." This document does not
attempt to fix `roadmap.md`'s numbering; that is a pre-existing, separately-flagged
cleanup, out of this milestone's scope.) All three deliverables below use **Phase
7 / Phase 8 / Phase 9** throughout. Content and scope match the brief exactly; only the
numbers changed.

---

## 1. Executive summary

SNOMNIMAN's foundation is complete: project management, multi-measurement workflows,
experiment analysis, provenance, the processing framework (incl. multi-input), the
scientific processing and analysis toolboxes, region-aware processing, workflow
automation (recipes/batch/reporting), spectral processing foundations, and the
hyperspectral workspace are all shipped (see CLAUDE.md's status header and `LOG.md`).
Phase 5C (real interferogram/hyperspectral readers) remains hard-blocked on vendor data
that does not yet exist in this repository.

This document plans the next three phases as **one coherent scientific platform**, not
three independent feature sets:

- **Phase 7 (Automated Scientific Feature Analysis)** turns a measurement's pixels into
  *countable, comparable scientific objects* - particles, domains, edges - using
  deterministic, literature-precedented image analysis. **Key design finding:** this
  phase needs **no new architectural layer**. Segmentation is a `ProcessingStep` (a
  labeled channel is a derived `Dataset`, exactly like any other operation output);
  per-feature statistics are new `snomniman.diagnostics` descriptors; experiment-wide
  feature comparison extends the existing `gui.experiment.ExperimentModel`
  (ADR-0029); reporting extends `gui.report.ReportModel` (Phase 4C). No ADR is
  required - this is the same category as Line Flatten and Phase 3B/3C: settled
  engineering over an existing abstraction.
- **Phase 8 (Physics Modeling)** fits deterministic physical models (Drude, Lorentz
  oscillator, the finite dipole model, the lightning rod model) to already-processed
  spectra to extract material parameters (dielectric function, resonance frequency,
  carrier density). **Key design finding:** this phase *does* introduce one new
  backend module, `snomniman.physics`, because it is a genuinely new class of derived
  knowledge (inverting a near-field tip-sample interaction model), the same category
  of decision that justified `describe` (ADR-0018), `diagnostics` (ADR-0019), and `ai`
  (ADR-0020) each getting their own module. It needs its own ADR, written at
  implementation time. Every capability in this phase is split, exactly as the project
  always splits it: *"is this fit possible"* (a tool the researcher explicitly runs,
  previews, and records in provenance - Category A, standard operation DoD) versus
  *"should the engine auto-recommend or auto-assert this model applies"* (a judgment -
  Category B, gated by the full Scientific Validation Phase, `docs/scientific-validation.md`).
  This document proposes tools only; it proposes **no** auto-recommendation rule
  without a validation study.
- **Phase 9 (Scientific Assistant)** extends the existing `snomniman.ai` module (the
  Scientific Briefing + Scientific Reasoning Rule Engine, ADR-0020/0022/0023) to reason
  over Phase 7 and Phase 8 facts in addition to `describe`/`diagnostics` facts, and adds
  experiment-level orientation (an "Experiment Briefing"), deterministic outlier
  flagging, and new `ReasoningRule`s once Phase 7/8 facts exist. **Key design finding:**
  this is disciplined reuse of an architecture that was already built for exactly this
  purpose - no new AI paradigm, no new safety mechanism. The three permanent AI rules
  (CLAUDE.md) and the evidence-sourced `BriefingStatement`/`Evidence` pattern already
  generalize to any new fact producer; Phase 9 just needs new fact producers (Phase
  7/8) to reason over, which is why Phase 9 is sequenced *after* them.

**The load-bearing dependency, stated up front:** Phase 8's most scientifically
interesting capability (carrier-density estimation from an inverted near-field model) is
gated on data this repository does not currently have in two independent ways - see
Deliverable 4 (Section 6) for the full graph:

1. **Phase 5C is still hard-blocked** (`NEXT.md`, re-confirmed 2026-07-02g): no real
   interferogram or hyperspectral files exist, so broadband nano-FTIR dielectric-function
   extraction and hyperspectral-cube feature segmentation cannot be real-data-validated
   yet. The existing real point-spectroscopy CdO dataset (used for Phase 6) is *not*
   blocked - it supports Drude/Lorentz-oscillator/FDM fitting on single spectra today.
2. **A new gap this document found:** `snomniman.core.metadata` has no tip-geometry
   field (radius, cone angle, taper angle) anywhere - required by the finite dipole and
   lightning rod models and not vendor-exported by the neaSNOM reader. This is not a
   hard blocker (the fit tool can take tip geometry as explicit, honestly-labeled
   user-supplied parameters, never a silent assumption - CLAUDE.md "never guess missing
   metadata"), but it does block ever treating a Phase 8 fit result as an unattended
   *fact* the way `diagnostics` facts are.

---

## 2. Where SNOMNIMAN stands today (pointers, not re-derivation)

This section deliberately does not repeat what CLAUDE.md's status header, `NEXT.md`, and
`docs/architecture.md` already state authoritatively. The load-bearing facts this
document builds on, verified against source during this milestone:

- **Data model** (`snomniman.core`): `DataKind` = `IMAGE | LINE_SCAN | APPROACH_CURVE |
  INTERFEROGRAM | SPECTRUM | HYPERSPECTRAL`. `Capability` = `SPATIAL_2D | SPATIAL_1D |
  SPECTRAL | INTERFEROMETRIC | COMPLEX_OPTICAL | COMPLEX_MECHANICAL | TOPOGRAPHY |
  REFERENCE | MULTI_HARMONIC`. `Metadata` currently has: `Conventions`, `Instrument`,
  `Excitation`, `Demodulation`, `ScanInfo`, `SpectralInfo`, `InterferometerInfo`,
  `Acquisition`, `ChannelInfo` - **no tip/probe-geometry field** (verified by search;
  see Section 4.4).
- **Diagnostics** (`snomniman.diagnostics.descriptors`): `ChannelStatistics`,
  `HistogramData`, `TopographyDiagnostics`, `HarmonicAmplitude`/`HarmonicDiagnostics`
  (signal/weak/noise/empty/unknown classification, ADR-0026), `OperationApplicability`,
  aggregated in `MeasurementDiagnostics`. All are frozen, JSON-serializable, honest
  (`None` where uncomputable).
- **Reasoning** (`snomniman.ai.reasoning`): `ReasoningRule`/`ReasoningContext`/
  `RuleOutcome`, a decorator-based registry (`register_rule`), evaluated by
  `ai.recommend`. Shipped rules: `PlaneLevelRule` (fires), `ReferenceNormalizeRule`
  (registered but withdrawn - Outcome 2). The mechanism for `prerequisite_steps` /
  `excluded_steps` exists and is tested but unused (no real prerequisite relationships
  exist yet).
- **Analysis** (`snomniman.viz.measure`): `RegionStats`, `Peak`, `ProfileFeatures`,
  `RegionComparison`, `LineshapeFit` (Lorentzian + linear baseline,
  `scipy.optimize.curve_fit`), functions `analyze_profile`, `compare_regions`,
  `fit_lineshape`. This is the precedent for "an analysis that reports a fact about a
  measurement, deliberately *not* a `ProcessingStep*, because it doesn't produce a new
  object to chain from" (Phase 6 design doc, Section 3.3) - the same precedent Phase 8
  fits will follow.
- **Spectral processing** (`snomniman.processing.spectrum`): `fft_interferogram`
  (`Capability.INTERFEROMETRIC`), `ratio` (`Capability.SPECTRAL`, 2-input, ADR-0030),
  `savgol_smooth` (`Capability.SPECTRAL`).
- **Experiment/report presenters** (`snomniman.gui.experiment` / `snomniman.gui.report`):
  `ExperimentModel` and `ReportModel` are **Qt-free but live in `gui`**, not the backend
  - because their only present consumer is the Explorer window (Rule 7: "no new backend
  package without a concrete, present consumer," the exact reasoning in `report.py`'s own
  module docstring). This matters for Sections 3 and 5 below: experiment-wide
  *presentation* aggregation belongs beside `ExperimentModel`; new *backend* facts belong
  in `diagnostics`/`physics`/`ai`.
- **Dependencies** (`pyproject.toml`): `numpy`, `scipy`, `xarray`, `zarr`, `h5py`,
  `matplotlib`. No `scikit-image`, no `scikit-learn`, no `lmfit`. Any of these would need
  its own ADR per CLAUDE.md ("never introduce a major dependency without an ADR") -
  Sections 3 and 4 below design around **not** needing one for the first milestones, and
  name exactly where a future one might become justified.
- **ADRs**: the highest accepted decision is **ADR-0032** (the Manual). The next free
  number is **ADR-0033**.
- **Real sample data** (per the Phase 5C revisit, `LOG.md` "2026-07-02g"): exactly 3
  imaging measurements (`2D (PsHet)`, including the CdO nanoparticle sample used
  throughout Phases 3-6) and 1 point-spectroscopy measurement (`Point Spectroscopy
  (PsHet)`, a direct wavenumber sweep, not interferometric). No interferogram export, no
  hyperspectral-cube export exists anywhere in the sample set.

---

## 3. Deliverable 1 - Phase 7: Automated Scientific Feature Analysis

### 3.1 Philosophy and scope

The project's decision litmus (`docs/product-philosophy.md`, GUI Rule 9) is: does a
feature improve a researcher's understanding of a measurement? Feature analysis earns
its place the same way every prior toolbox increment did (Phase 3A/3B/3C): it takes
something a researcher currently does by eye ("there are roughly a dozen particles, the
big ones look about 40-60 nm across") and makes it a **countable, reproducible,
provenance-recorded fact**. It must not become a second, speculative "smart" image
pipeline bolted beside the existing one - it is asked to be, and is designed to be,
**more processing steps plus more diagnostics facts**, nothing else.

**What is explicitly out of scope for Phase 7** (named, not silently missing, per the
project's discipline of listing deferred scope): machine-learning-based
segmentation (no training data, no labeled ground truth exists, and it would
violate "never treat AI as the primary interpreter of raw data" - AI rule 1); automatic
*classification* of a detected feature's physical identity ("this is a nanoparticle vs.
a scan artifact") - that is a Phase 9/Scientific-Validation-gated judgment, not a Phase
7 deterministic measurement; and cross-file/instrument feature tracking (e.g. "this is
the same particle across three time-lapse scans") - no time-series/registration
capability exists yet and would be its own validation study.

### 3.2 Scientifically meaningful structures in s-SNOM/nano-FTIR data

Grounded in what an s-SNOM/AFM researcher actually looks for (mirrors how Line Flatten's
design started from "what does a researcher already do by eye," `next-scientific-
priorities.md` Candidate 1):

| Structure | Typical source channel | Established analogue | Real data available now? |
|---|---|---|---|
| Topographic particles / islands / grains | `Z` (topography) | AFM "grain analysis" (Gwyddion, MountainsMap) | **Yes** - the CdO nanoparticle sample is exactly this. |
| Optical domains (amplitude/phase contrast regions) | `O{n}A` / `O{n}P` | Near-field domain mapping (phase-separated materials, e.g. VO2 insulator-metal domains) | Yes (any `O{n}` channel), though no real domain-structured sample is confirmed in the current set. |
| Step edges / domain walls | `Z` or any channel, gradient-based | Standard edge detection in SPM analysis | Yes. |
| Periodic near-field fringes (polariton/plasmon interference) | `O{n}A`/`O{n}P` line cuts or 2-D maps | Fourier-domain fringe-wavelength extraction | Plausible on the CdO sample if a resonance is spatially imaged; the direct consumer is Phase 8 dispersion analysis (Section 4.3, capability 6). |
| Value-distribution features (bimodality, multi-population statistics) | any channel's `HistogramData` (already shipped) | Already partly visible via the existing histogram | Yes - reuses a shipped descriptor. |

### 3.3 Segmentation approaches surveyed

Literature/precedent survey (no invented metrics, mirroring the Scientific Validation
Phase's own discipline even though - see 3.4 - most of Phase 7 does not require a
validation *study*, only the standard operation DoD):

| Approach | What it does | Verdict for Phase 7 |
|---|---|---|
| **Global/adaptive thresholding** (fixed, percentile, Otsu 1979) | Binarize by intensity/height | **Adopt first.** Closed-form, deterministic, the same category of "settled SPM science" as Line Flatten. Otsu's method needs only a histogram (already computed by `HistogramData`). |
| **Connected-component labeling** | Group thresholded pixels into discrete regions | **Adopt.** `scipy.ndimage.label` / `find_objects` - already a dependency, no new one needed. |
| **Gradient/edge-based detection** | Find boundaries by intensity gradient | **Adopt for edges/domain-wall detection** (a second, simpler segmentation mode) via `numpy.gradient` + thresholding - no new dependency. |
| **Watershed** (Beucher & Meyer 1993) | Splits touching/overlapping particles that connected-components would merge | **Defer.** Not available in `scipy.ndimage`; needs `scikit-image.segmentation.watershed`, a new major dependency requiring its own ADR. Only propose this if real multi-particle data demonstrates connected-components under-counts due to touching particles (Rule 7 - do not add speculatively). |
| **Region growing / clustering (k-means on multi-channel features)** | Groups pixels by similarity across several channels at once | **Name, do not build yet.** No `scikit-learn` dependency exists; a genuine multi-channel-feature use case (e.g. combining `Z` + `O2A` + `O2P` to find domains invisible in any single channel) would justify it later, but nothing in the current real data set demonstrates the need. |

**Decision for the first Phase 7 milestone:** threshold + connected-components only.
This is the same "possible vs. speculative generality" discipline Line Flatten used
(`next-scientific-priorities.md`: "do not also add a `polynomial_flatten`... keep
parameters minimal").

### 3.4 Architecture: where this lands (the key design decision)

The brief asks Phase 7 to integrate with "the existing ROI, Measurements, Diagnostics,
Experiment, and Reporting systems." The disciplined way to do that - and the central
finding of this deliverable - is to **not** create a new top-level module. Every piece
of Phase 7 maps onto `docs/architecture.md` Section 10's existing landing-point table:

| Phase 7 piece | Lands in (existing layer) | Mechanism | New ADR? |
|---|---|---|---|
| Segmentation (threshold -> labeled integer channel) | `snomniman.processing.image` | New `ProcessingStep`s (e.g. `image.threshold_segment`), exactly like every other operation - previewed, provenance-recorded, produces a new derived `Dataset` with an added integer-labeled channel. **A labeled channel is not a new data type**: it is an ordinary real-valued channel (dtype int) on the existing `xarray`-backed `Dataset`, so **zero core/persistence change** is needed (same "no redesign" finding Phase 5A/5B and Phase 2C each independently reached). | No |
| Per-feature statistics (area, perimeter, aspect ratio, mean height/amplitude per labeled region) | `snomniman.diagnostics` | New descriptor(s) (e.g. `FeatureDiagnostics`/`ParticleFeature`) computed from a labeled channel + its source channel, following the `HarmonicDiagnostics` precedent (a tuple of per-object frozen records) | No (ADR-0019 already covers "a new descriptor") |
| Experiment-wide feature comparison (size-distribution histograms, per-measurement feature counts across a project) | `gui.experiment.ExperimentModel` | Extends the existing aggregation exactly as it already aggregates per-measurement diagnostics/ROI stats into an `ExperimentTable` (ADR-0029) | No |
| Reporting | `gui.report.ReportModel` | New "Feature Analysis" `ReportSection`, same pattern as the Phase 6 "Spectral peak fit (active)" section | No |
| ROI integration | existing `viz.measure.region_stats` / Measurements framework | A detected feature's bounding region seeds an ROI selection (a GUI convenience: "promote this labeled region to the active ROI"), reusing the *existing* ROI mechanism verbatim, not a new one | No |
| Teaching | `snomniman.knowledge` / `snomniman.manual` | New `Article`s (one per new operation/diagnostic, satisfying the existing no-drift test) + `ManualPage`s | No (ADR-0024/0032 already cover this) |

**Why this is correct and not just convenient:** the project's own "Extending the
system" table (`architecture.md` Section 10) exists precisely to prevent this kind of
milestone from inventing a `snomniman.features` layer out of habit. A labeled-region map
genuinely is "a deterministic operation output" (it is derived from, and only from, an
existing channel by a documented deterministic rule); per-feature statistics genuinely
are "a deterministic fact" (a number computed from data, no different in kind from
`TopographyDiagnostics`, just indexed by feature instead of by whole-channel). Nothing
about Phase 7 needs a new kind of module.

### 3.5 Particle/domain detection & morphology

Given a labeled channel (from `image.threshold_segment`), per-label statistics are
computed with **no new dependency**, using `scipy.ndimage.label`/`find_objects` for
region indexing and hand-computed image moments for shape (the same category of
"the standard analytical answer, not an invented metric" the project always insists on):

- **Count** - number of labeled regions above a minimum-pixel-count filter (removes
  single-pixel noise; the filter is a `ParameterSpec`, not a silent default).
- **Area** - pixel count x `pixel_size_nm` (already in `ScanInfo`) -> physical units,
  never pixels alone (mirrors the project's "canonical spatial unit nm" convention,
  OHD-6).
- **Equivalent diameter** - `2 * sqrt(area / pi)`.
- **Perimeter** - boundary-pixel count (compare the labeled region to its
  `scipy.ndimage.binary_erosion`), a standard discrete-perimeter estimate.
- **Aspect ratio / orientation** - eigenvalues/eigenvectors of the region's
  second-order central-moment (covariance) matrix over its pixel coordinates - the
  same closed-form construction `skimage.measure.regionprops` uses internally, computed
  directly with `numpy` (no dependency needed for this specific case).
- **Per-feature channel statistics** - mean/max/min of the *source* channel's value
  within the label (e.g. mean height of each particle, mean optical amplitude of each
  domain) - reuses the exact `ChannelStatistics` computation, scoped to a mask.

All of the above are **honest by construction**: a degenerate region (zero-area,
single-pixel) reports `None` for shape metrics that require >= 3 pixels, never a
divide-by-zero or a fabricated value - the same discipline every existing diagnostic
follows.

### 3.6 Feature statistics (per-measurement and aggregate)

Two levels, matching the two levels the project already separates everywhere else
(single measurement vs. experiment-wide):

- **Per-measurement** (`diagnostics.FeatureDiagnostics`): the tuple of per-feature
  records above, plus a summary (count, total area fraction covered, and a
  `HistogramData` of the size distribution - reusing the shipped histogram descriptor
  verbatim, exactly as suggested by its own docstring: "experiment-level comparison can
  consume this directly without redesign").
- **Experiment-wide** (`gui.experiment.ExperimentModel` extension): aggregates
  `FeatureDiagnostics` across every measurement in the project into one comparative
  table/histogram (e.g. "particle size distribution, all measurements" or "feature count
  per measurement"), CSV-exportable exactly like the existing cross-measurement ROI/line
  statistics (ADR-0029).

### 3.7 Integration summary (answers the brief's integration question directly)

- **ROI**: a labeled feature becomes a selectable region via the existing
  `rect_mask`/`polygon_mask`/`region_stats` machinery - "select feature #N" simply
  constructs the ROI geometry from that label's bounding polygon, then everything
  downstream (Measurements, CSV export) is unchanged.
- **Measurements**: no new mode. A feature-derived ROI flows through the existing
  `RegionReport` path.
- **Diagnostics**: `FeatureDiagnostics` joins `MeasurementDiagnostics` exactly as
  `HarmonicDiagnostics` did, surfacing in the existing Diagnostics panel with no new
  panel needed (it is generic/registry-driven per Rule 9's payoff).
- **Experiment**: `ExperimentModel` gains one more aggregate table (Section 3.6),
  reusing `ExperimentTable`/CSV export verbatim.
- **Reporting**: `ReportModel` gains one more `ReportSection` (Section 3.4 table),
  reusing `Report`/`render_markdown`/`render_html` verbatim.

### 3.8 Honest limitations & deferred scope

- Watershed splitting of touching particles is **not** included (Section 3.3); expect
  connected-components to *under-count* densely packed or overlapping particles. This
  is a documented limitation, not a silent gap.
- No shape classification beyond aspect ratio/orientation (no "is this circular /
  faceted / elongated" categorical judgment - that would be a Scientific Validation
  candidate if a real research need appears).
- No time-series/registration (tracking the same particle across repeated scans).
- No multi-channel (combined `Z` + optical) segmentation in the first milestone
  (Section 3.3's clustering row) - single-channel threshold segmentation only.
- Real-data validation is currently limited to the CdO topography channel (one real
  particle field); optical-domain segmentation and edge detection have no confirmed
  domain-structured real sample yet - synthetic validation only until one appears
  (same honesty discipline as Phase 5A/6's synthetic-only interferogram validation).

---

## 4. Deliverable 2 - Phase 8: Physics Modeling

### 4.1 Philosophy and scope: the "tool vs. judgment" split

Every capability below is deliberately split into two independent questions, because
the project has applied exactly this split to every prior scientific capability
(`next-scientific-priorities.md`'s "possible vs. recommend" framing for Line Flatten and
phase-unwrap):

1. **"Can a researcher run this fit, previewed, on a spectrum they chose?"** - this is
   an ordinary operation/analysis. It needs the standard operation Definition of Done
   (an analytical/known-answer round-trip test, Rule 6) - the same bar `fit_lineshape`
   already cleared. **No Scientific Validation Phase study is required** for the tool
   itself, because nothing is being *asserted automatically* - the researcher explicitly
   chooses the model, previews the fit, and the result is recorded with full provenance
   (which model, which parameters, which starting values).
2. **"Should the engine auto-recommend which physical model applies, or auto-assert a
   fitted parameter as a fact?"** - this is a scientific judgment (e.g. "this spectrum's
   near-field decay looks Drude-like, therefore recommend a Drude fit," or "carrier
   density = 2e19 cm^-3" stated in a Briefing without the researcher having run
   anything). **This requires the full Scientific Validation Phase lifecycle** -
   literature review, candidate diagnostics, analytical/synthetic/real-data validation
   on both branches, Decision - exactly like harmonic ranking (ADR-0026) and unlike a
   plain operation.

**This document proposes only capability (1) for each item below.** No auto-
recommendation rule is proposed anywhere in Phase 8; each would be its own future
Scientific Validation candidate (added to the queue in Section 8's roadmap, not
implemented here). This directly satisfies the brief's constraint: "do not propose
implementations that cannot be scientifically validated" - the *tools* are validated by
the ordinary analytical-round-trip DoD; the *judgments* are not proposed at all until a
validation study exists to justify them.

### 4.2 Architecture: a new `snomniman.physics` module

Unlike Phase 7, Phase 8 does need one new backend module. The justification, argued
against Rule 7 the same way ADR-0018/0019/0020 each had to argue it at the time:

- A fitted material parameter (a Drude plasma frequency, a Lorentz oscillator strength,
  an FDM-inverted permittivity, an estimated carrier density) is not a statistic about
  the measured array (that is what `diagnostics` already is) and not a projection of
  existing metadata (that is `describe`). It is a **new kind of derived scientific
  knowledge** - the output of inverting a physical *model* through the data, not a
  summary of the data itself. That is a qualitative difference, the same one that
  justified `diagnostics` as a sibling of `describe` rather than a field bolted onto it
  (ADR-0019's own reasoning).
- It has a real, substantial, and growing vocabulary (Drude, Lorentz, FDM, LRM, fringe
  dispersion, carrier density) - large enough to be its own coherent subject, not one
  extra function.
- It has **no** current consumer other than a future Explorer panel and, later, Phase 9 -
  which is exactly the position `ai` was in before ADR-0020 justified it: "AI is a
  first-class analysis subsystem... not a UI add-on."

**Position in the layer stack** (extends, does not restructure, the existing diagram in
`architecture.md` Section 2):

```
gui
batch  pipeline
ai          (Phase 9: describe + diagnostics + physics + core; NEW edge -> physics)
physics     (Phase 8: NEW module; core [+ diagnostics/describe for grounding inputs])
describe    diagnostics
processing
io   core
viz         (independent leaf; gui-only consumer, unchanged)
```

`physics` depends on `core` (for `Dataset`/`Metadata`/units) and, for grounding inputs,
may read `describe`/`diagnostics` projections (e.g. `SpectralInfo`, the harmonic
classification, an already-computed `LineshapeFit`) - but it does **not** import `viz`
(no `physics -> viz` edge): it implements its own `scipy.optimize` fitting the same way
`viz.measure` does, rather than creating a cross-edge between two sibling analysis
modules. This mirrors how `diagnostics`, `describe`, and `ai` are independent siblings
today, each using `scipy`/`numpy` over `core` directly rather than importing one
another's implementation details. (Whether a Phase 8 fit function's *signature* accepts
a `viz.measure.LineshapeFit` as a convenience starting-point - the caller passing an
already-computed peak position as an initial guess - is a reasonable implementation-time
choice; it does not require an import edge, only a plain-data parameter.)

Like `viz.measure.fit_lineshape`, physics fits are **analyses, not `ProcessingStep`s**:
they report a fact (a parameter set) about a spectrum, not a new immutable object to
chain further processing from. This is the same Phase 6 precedent, restated for a new
domain.

**A new ADR is required** (proposed number: **ADR-0033**, the next free slot; the exact
number is confirmed only when actually written, per convention) - "Physics Modeling: a
new `snomniman.physics` module for deterministic material-parameter extraction." Written
at the start of Phase 8's first implementation milestone (Section 8), not now.

### 4.3 Capability-by-capability design

For each capability: scientific motivation, required inputs, Phase 6/7 dependency,
validation strategy, expected outputs. Citations are a literature-review **starting
point** for the eventual implementation milestone, not a completed review - the
Scientific Validation Phase's own template (Section 6 of `scientific-validation.md`)
requires re-verifying and expanding them at that time.

#### 1. Dielectric function extraction (general)

- **Motivation.** The complex near-field signal `s(omega) = s'(omega) + i*s''(omega)` is
  not itself the sample's dielectric function `epsilon(omega)` - it is that function
  filtered through the tip-sample near-field interaction. Extracting `epsilon(omega)`
  is the prerequisite for comparing a measurement to bulk optical constants or to a
  specific material model.
- **Required inputs.** A processed spectrum (after `spectrum.ratio`/`spectrum.
  savgol_smooth`, optionally `spectrum.fft_interferogram` for broadband data);
  `Metadata.excitation` (the illumination wavenumber(s)); a chosen tip-sample model
  (FDM or LRM, below) with its own required inputs.
- **Dependency.** Consumes Phase 6's processed-spectrum pipeline directly; for
  broadband interferometric spectra it additionally needs Phase 5A's
  `fft_interferogram` output, which is only real-data-validatable once Phase 5C
  delivers a real interferogram file.
- **Validation.** Round-trip: given a known synthetic `epsilon(omega)` (e.g. a Drude or
  Lorentz model with chosen parameters), forward-model it through FDM/LRM to a
  synthetic `s(omega)`, add controlled noise, and verify the inversion recovers the
  original `epsilon(omega)` within a documented tolerance (Rule 6 - the same discipline
  the Lorentzian lineshape and FFT-interferogram round-trip tests already use). Real-data
  validation requires an independent reference measurement of the same material's bulk
  dielectric function (e.g. from ellipsometry or a literature value) - not present in
  this repository; `(user)`-gated.
- **Output.** A frozen `DielectricFit` (or similar) value object: `epsilon` as a
  function of wavenumber (or its fitted model parameters), fit quality, and the model
  + assumptions used - never asserted without stating which tip-sample model produced
  it.

#### 2. Drude model fitting

- **Motivation.** Free-carrier (metallic/doped-semiconductor) optical response:
  `epsilon(omega) = epsilon_inf - omega_p^2 / (omega^2 + i*omega*gamma)`. Directly
  relevant to doped-semiconductor and plasmonic samples (including CdO, whose
  free-carrier response the mentor's own figure targets per `phase6-spectral-
  lineshape-analysis.md`'s origin story).
- **Required inputs.** A dielectric-function spectrum (capability 1) or, more directly,
  a near-field amplitude/phase spectrum plus a chosen tip-sample model to fit
  `omega_p`/`gamma`/`epsilon_inf` directly against the *measured* `s(omega)` (avoiding a
  two-stage inversion error stack-up) - the more practical of the two paths and the one
  this document recommends starting with.
- **Dependency.** Phase 6 (processed spectrum), optionally Phase 8 capability 4 (FDM) as
  the forward model connecting `epsilon(omega)` to the measured `s(omega)`.
- **Validation.** Textbook closed-form model (Ashcroft & Mermin, *Solid State Physics*) -
  analytically exact by construction; synthetic recovery of known `(omega_p, gamma,
  epsilon_inf)` through the forward model plus noise; real-data validation against the
  CdO point spectrum is possible **today** (no Phase 5C dependency) but only validates
  internal self-consistency (does the fit converge and reproduce the curve), not
  absolute accuracy, without an independent carrier-density reference (see capability 7).
- **Output.** `omega_p`, `gamma`, `epsilon_inf` with fit uncertainty, `R^2`/residual
  structure exactly like `LineshapeFit` already reports (including the honest
  "low `R^2` means the model doesn't apply, not a bug" framing the Phase 6 Knowledge
  article already establishes for Lorentzian fits - the same caveat generalizes here).

#### 3. Lorentz oscillator fitting (material-parameter version)

- **Motivation.** Phonon/molecular-vibration/plasmon resonances:
  `epsilon(omega) = epsilon_inf + S*omega_TO^2 / (omega_TO^2 - omega^2 - i*omega*gamma)`.
  Distinct from Phase 6's *phenomenological* Lorentzian lineshape fit (which fits the
  *measured* amplitude/phase curve directly with no physical units attached to its
  parameters) - this capability fits the same functional family but to the **physical
  dielectric function**, with `omega_TO`, `gamma`, and oscillator strength `S` as the
  fitted physical quantities.
- **Required inputs/dependency/validation/output.** Same structure as Drude (capability
  2), swapping the dielectric-function model; the two are naturally implemented as one
  shared fitting primitive (`physics.fit_dielectric_model(kind="drude"|"lorentz", ...)`)
  rather than duplicated code (Rule 2, "no re-parameterization of an existing
  operation" - same discipline Line Flatten's design cited for `plane_level` vs.
  `line_flatten`, applied here to keep Drude/Lorentz as one shared mechanism, not two).

#### 4. Finite dipole model (FDM)

- **Motivation.** The standard, widely-used analytical tip-sample interaction model
  connecting a sample's `epsilon(omega)` to the measured near-field signal `s(omega)`,
  via an effective point-dipole polarizability with a tip-geometry-dependent correction
  factor (Cvitkovic, Ocelic & Hillenbrand 2007). It is the forward model capabilities 1-3
  actually need to relate `epsilon(omega)` <-> `s(omega)`; without it, Drude/Lorentz
  fitting can only be done against a *proxy* (the raw amplitude/phase curve), not the
  physical dielectric function.
- **Required inputs.** Tip radius, tip-sample distance/tapping amplitude (partially
  available: `Metadata.acquisition.tapping_amplitude_nm` already exists; tip radius does
  **not** - Section 4.4), the illumination wavenumber, and a reference material with
  known `epsilon(omega)` for the (standard FDM practice) normalization step.
- **Dependency.** None on Phase 7. Depends on Phase 6's processed spectra.
- **Validation.** Analytically exact within the model's own stated approximations
  (closed-form, from the cited literature); synthetic forward/inverse round-trip
  (choose `epsilon`, forward-model `s`, invert, recover `epsilon`); real-data validation
  needs both a known-reference sample (standard FDM practice - e.g. a bare Si or SiO2
  reference region) and instrument-accurate tip geometry (Section 4.4) - the tip-geometry
  half is `(user)`-gated until that metadata gap is closed.
- **Output.** A `TipModelFit`/`epsilon(omega)` estimate plus the explicit list of
  assumptions used (tip radius source: measured vs. user-estimated vs. nominal;
  reference material and its assumed `epsilon`) - **never silently defaulted** (CLAUDE.md:
  "never guess missing metadata").

#### 5. Lightning rod model (LRM)

- **Motivation.** A more rigorous tip-sample model than FDM (a more realistic tip-charge
  distribution, better accuracy for strongly resonant or high-permittivity-contrast
  samples), from Hauer, Engelhardt & Taubner (2012) and Govyadinov, Mastel, Golmar,
  Chuvilin, Carney & Hillenbrand (2014).
- **Required inputs/dependency.** Same physical inputs as FDM, plus the model's own
  additional geometric parameters (a multi-parameter tip shape, not a single effective
  radius) - a strictly larger metadata/parameter burden than FDM.
- **Validation.** Same round-trip discipline as FDM, but the model is numerically
  heavier (an iterative or multipole-expansion calculation rather than a closed-form
  formula), so synthetic validation is more implementation work, not more scientific
  risk.
- **Verdict: defer.** Implement FDM first (capability 4); revisit LRM only if FDM's
  accuracy proves insufficient for a real research question (Rule 7 - do not build the
  more complex model speculatively). Named here, not scoped for near-term
  implementation - see Section 8's roadmap (milestone 8D, conditional).

#### 6. Plasmon/polariton fringe & dispersion analysis

- **Motivation.** Real-space near-field images of polaritonic materials (phonon
  polaritons, plasmons) show periodic interference fringes whose wavelength encodes the
  polariton dispersion relation - a direct, standard nano-optics measurement (distinct
  from a point-spectrum fit).
- **Required inputs.** A 2-D optical amplitude/phase image with visible fringes; the
  illumination wavenumber.
- **Dependency.** Reuses the **deliberately-deferred 2-D FFT / radial power spectral
  density** capability first named in Phase 3B (`NEXT.md`: "frequency analysis (2-D FFT
  / power spectrum / radial PSD) only if users need it"). Phase 8 gives it its first
  concrete, present consumer - which resolves that prior Rule-7 deferral rather than
  reopening it speculatively.
- **Validation.** Synthetic image with an injected known fringe wavelength recovers it
  exactly (closed-form Fourier-transform reasoning, analytically guaranteed); real-data
  validation needs a real polaritonic-fringe sample, which is **not confirmed present**
  in the current sample set (the CdO sample is a localized-resonance nanoparticle
  measurement, not a propagating-polariton fringe measurement) - `(user)`-gated pending
  a suitable real dataset.
- **Output.** Fringe wavelength(s) + a dispersion-relation data point (`(k, omega)`) per
  illumination frequency used; no automatic "this is a polariton" classification (that
  would be a judgment, out of scope per Section 4.1).

#### 7. Carrier-density estimation

- **Motivation.** The single most directly relevant capability to the mentor's original
  CdO research question (Phase 6's origin, `phase6-spectral-lineshape-analysis.md`): a
  localized surface phonon/plasmon resonance frequency, combined with a known
  doping-dependence model (background permittivity, effective mass), gives an estimated
  free-carrier density.
- **Required inputs.** A fitted resonance (from capability 2/3, Drude/Lorentz), an
  explicit, user-supplied set of material constants (effective mass, background
  permittivity, mobility if needed) - **not** silently assumed; these are
  material-specific literature values the researcher must supply and the report must
  echo back verbatim as stated assumptions.
- **Dependency.** Capabilities 2-4 (a resonance fit + a tip-sample model to relate the
  fitted near-field parameter to a physical `epsilon(omega)`).
- **Validation.** The math (LSPh-resonance-to-carrier-density formulas) is standard
  solid-state physics, analytically exact given its stated assumptions; synthetic
  round-trip (choose a carrier density, compute the expected resonance via the model,
  invert, recover the density) is straightforward. **Real-data validation requires an
  independent ground truth for the actual CdO sample's carrier density** (e.g. a Hall
  measurement or a literature value for that specific growth batch) - **not present in
  this repository**. This is the same category of gap as phase-wrapping's missing
  golden measurement (`phase-wrapping-analysis.md`, Outcome 2): the tool can be built and
  self-consistency-tested, but its absolute accuracy cannot be validated against real
  data without that reference. `(user)`-gated.
- **Output.** An estimated carrier density with explicit propagated uncertainty and the
  full assumption list attached (echoing the exact inputs used) - reported as *"an
  estimate under these stated assumptions,"* never as an unqualified fact. This
  phrasing discipline is not optional stylistic advice - it is what keeps this capability
  inside the "tool" category (Section 4.1) rather than silently becoming an unvalidated
  "judgment."

### 4.4 The tip-geometry metadata gap

A real finding from this milestone's research, not previously documented: **no field in
`snomniman.core.metadata` captures tip/probe geometry** (radius, cone half-angle, taper
length). `Metadata.acquisition` has `tapping_amplitude_nm` and `setpoint` but nothing
about the probe itself; the neaSNOM GSF reader does not export it either (it is
typically bench/probe-supplier information, not per-scan instrument telemetry).

This blocks FDM/LRM (capabilities 4-5) from ever being *silently* parameterized - which
is the correct, conservative failure mode (CLAUDE.md: "never guess missing metadata"),
but it means the fit tools must expose tip radius/geometry as an explicit, required
`ParameterSpec` (like every other operation parameter), and any report of a resulting
`epsilon(omega)`/carrier-density estimate must state which tip-geometry values were used
and their source (measured, vendor-nominal, or user-estimated). A future additive
`Metadata.probe: ProbeInfo | None` field (mirroring how `SpectralInfo`/
`InterferometerInfo` were each added additively in Phase 5, no redesign) is a candidate
if a vendor export is ever found to carry it - named here for a future milestone, not
implemented now.

### 4.5 Honest limitations & deferred scope

- No auto-recommendation or auto-classification of which physical model applies (Section
  4.1) - every fit is researcher-initiated.
- Carrier-density estimation and any dielectric-function extraction claim absolute
  accuracy only as far as user-supplied material constants and tip geometry are correct
  - the tool reports self-consistency, not independently-verified truth, until a golden
  reference exists (Section 4.3, capabilities 4/7).
- LRM is named, not scoped for near-term work (Section 4.3, capability 5).
- Broadband (interferometric) dielectric-function extraction stays blocked behind Phase
  5C exactly like every other interferogram-dependent capability.
- Fringe/dispersion analysis (capability 6) has no confirmed real polaritonic sample
  yet - synthetic-only validation until one exists.

---

## 5. Deliverable 3 - Phase 9: The Scientific Assistant

### 5.1 Philosophy: deterministic computation vs. AI interpretation

This is not a new philosophy - it is CLAUDE.md's existing "AI Architecture Principles"
and its three permanent AI rules, restated for the two new fact sources Phases 7 and 8
add:

| | Deterministic computation (the scientific authority) | AI interpretation (communication only) |
|---|---|---|
| Who decides | `diagnostics` (incl. new `FeatureDiagnostics`), `physics`, `ai.reasoning` rules | Never decides; only narrates/prioritizes/explains |
| What it can assert | Any statement traceable to a computed value with a source tag | Nothing it computed itself; only restates/organizes what the deterministic layer already asserted |
| Fallback | Always present, with or without a narrative provider (AI rule 2) | Optional narrative layer on top |
| Failure mode if evidence is missing | Reports `None` / declines (a `ReasoningRule` returns `None`, exactly as `ReferenceNormalizeRule` already does) | Never fills the gap by inventing a plausible-sounding conclusion (AI rule 1 + this brief's explicit constraint) |

**This table is not new infrastructure** - it is the exact mechanism already shipped:
`BriefingStatement(kind="fact", sources=(...))` and `RuleOutcome.evidence` already force
every AI-visible claim to carry a deterministic source. Phase 9 adds no new safety
mechanism; it only requires that Phase 7/8's new descriptors participate in the same
source-tagging discipline that `diagnostics`/`describe` already follow - which Sections
3 and 4 above already specify (frozen, JSON-serializable, honest-`None` value objects).

### 5.2 Architecture: extending `snomniman.ai`, not replacing it

`snomniman.ai` was built exactly for this (`docs/ai-scientist-v1.md`: "AI is a
first-class analysis subsystem... not a UI add-on"). Phase 9 is disciplined reuse:

- **New dependency edge: `ai -> physics`.** Today `ai` depends on `describe` +
  `diagnostics` + `core`. Adding `physics` as a third deterministic-fact source it
  composes is the same pattern already in place, not a new one.
- **New dependency edge: `ai -> pipeline`** (for experiment-level reasoning, below).
  `pipeline` already depends on `processing`+`core` and does not depend on `ai`, so this
  introduces no cycle.
- **A structural note this research surfaced:** `gui.experiment.ExperimentModel` and
  `gui.report.ReportModel` are **presenters that live in `gui`**, not the backend
  (Section 2) - because their only present consumer was the Explorer window (Rule 7).
  Experiment-*level reasoning* (an "Experiment Briefing," cross-measurement outlier
  detection) is a different thing from experiment-level *presentation aggregation*: it
  is a deterministic judgment over facts, the same category of work `ai` already does
  for a single measurement. It therefore belongs in the **backend** `snomniman.ai`
  (operating directly on a `pipeline.Project`'s `Measurement`s via `describe`/
  `diagnostics`/`physics`, independent of the GUI's `ExperimentModel`), not bolted onto
  the `gui` presenter (which must stay Qt-free presentation logic, not scientific
  judgment, per Rule 4's spirit). The Explorer's Experiment tab then becomes a
  **consumer** of this new `ai` capability, the same relationship the existing Briefing
  panel already has with `ai.briefing`.

### 5.3 Capability-by-capability design

#### 1. Experiment summaries ("Experiment Briefing")

- **What.** A new `ai.build_experiment_briefing(project: pipeline.Project) ->
  ExperimentBriefing`, structurally parallel to `build_briefing` but composing
  `describe`/`diagnostics`/`physics` facts across every `Measurement` in the project
  instead of one dataset's facts.
- **Grounding.** Every statement is a `BriefingStatement` sourced to a specific
  measurement's specific fact (e.g. "3 of 5 measurements show a global topographic
  tilt exceeding 15% of height variation" - traceable to each measurement's
  `TopographyDiagnostics`).
- **Deterministic fallback.** Always available; a narrative provider (if configured,
  AI rule 2) only phrases it.

#### 2. Outlier detection

- **What.** A deterministic statistical flag: which measurement(s) in a project sit
  outside the project's own distribution for a given metric (e.g. a z-score/IQR test on
  `rms_roughness`, on a Phase 7 feature count, or on a Phase 8 fitted parameter).
- **Why this is computation, not AI judgment.** The threshold rule (e.g. "beyond 2
  standard deviations of the project's own mean") is a plain, auditable statistic - the
  same category of thing `diagnostics` already computes, just across measurements
  instead of within one. It lives in `ai` (not `diagnostics`) only because it requires
  a `pipeline.Project`-level view, which single-measurement `diagnostics` structurally
  does not have access to.
- **Validation caveat.** A *specific* outlier rule that claims scientific significance
  (e.g. "this measurement is instrumentally bad," not just "numerically distant from its
  siblings") would be a Scientific Validation candidate (comparable to the deferred
  "poor-scan detection" queue item, `scientific-validation.md` Section 7). Phase 9
  proposes only the honest, purely-statistical version: *"measurement X's roughness is
  2.4 standard deviations from this project's mean"* - a fact about the numbers, not a
  claim about instrument quality.

#### 3. Workflow recommendations

- **What.** New `ReasoningRule`s, using the **existing, unchanged** engine
  (`ai.reasoning`/`ai.recommend`), once Phase 7/8 facts exist to trigger on - e.g. a
  rule that recommends `image.threshold_segment` when a channel's `HistogramData`
  shows clear bimodality, or one that recommends a Drude fit when a spectrum's optical
  harmonic decay pattern resembles a free-carrier response.
- **Each new rule is individually Scientific-Validation-gated**, exactly like every
  existing rule. This document does **not** propose the specific bimodality/free-carrier
  triggers above as ready to implement - they are named as *examples of the kind of rule
  Phase 9 makes possible once Phase 7/8 ship*, each requiring its own literature review
  and two-sided real/synthetic validation (mirroring how `PlaneLevelRule` was validated
  before shipping, and how `ReferenceNormalizeRule`'s positive branch was withdrawn for
  lacking exactly this validation).

#### 4. Interpretation of completed analyses

- **What.** Extends the Briefing's existing "Scientific Observations" section (which
  already narrates `diagnostics` facts) to also narrate Phase 7 (`FeatureDiagnostics`)
  and Phase 8 (physics fit results) facts, when present on a measurement. Mechanical
  extension of an existing pattern - no new mechanism.

#### 5. Comparison between experiments (cross-project)

- **What.** Comparing two entire `.snomproj` bundles (e.g. "before vs. after a process
  change" as two separate projects), not two measurements within one project (which
  `ExperimentModel`'s existing Compare feature, ADR-0029, already does).
- **Honest gap.** No current mechanism opens two projects simultaneously for
  comparison; this is genuinely new, not a small extension. It requires either (a) a
  lightweight read-only loader that opens a second `.snomproj` alongside the active one
  purely for comparison (no editing, no save-back - avoiding any multi-project-editing
  complexity), or (b) is deferred entirely.
- **Verdict: defer, gated by Beta Readiness evidence.** Per Rule 7 and the project's
  own governance order (CLAUDE.md "Planning and Governance": Beta Readiness identifies
  the workflow gap *before* Scientific Validation or implementation), this capability
  should not be built until real user-testing (the still-open Beta Readiness user-testing
  protocol, Section 5 of `beta-readiness-v1.md`) shows researchers actually need
  cross-project comparison rather than within-project comparison. Named in the roadmap
  (Section 8) as a conditional milestone, not scheduled.

### 5.4 Safety: how it stays honest

No new safety mechanism is proposed because none is needed - restating why, precisely,
since the brief asks for this explicitly ("must never invent scientific conclusions
unsupported by available data"):

1. Every new fact producer (Phase 7's `FeatureDiagnostics`, Phase 8's `physics` fit
   results) is designed in Sections 3-4 to be a frozen, JSON-serializable, honestly-`None`
   value object - the same contract every existing `diagnostics`/`describe` descriptor
   already has.
2. The Briefing/Recommendation machinery already refuses to emit a claim without a
   `sources`/`evidence` tag pointing at such an object.
3. `ReasoningRule.evaluate` already returns `None` (not a weak guess) when evidence is
   insufficient - the mechanism, not a new policy, is what Phase 9's new rules must use.
4. The Scientific Validation Phase gate (`docs/scientific-validation.md`) already governs
   every new *automated judgment* project-wide; Phase 9 adds no exemption and no
   shortcut - every new `ReasoningRule` in Section 5.3.3, and any auto-classification
   anywhere in Phase 7/8, goes through it exactly like `PlaneLevelRule` and the harmonic
   classification did.

---

## 6. Deliverable 4 - Dependency graph

### 6.1 What each phase enables / depends on

```
                    Phase 5A/5B/6 (spectral processing, hyperspectral, lineshape fit)
                    Phase 3A-3C (core ops, analysis toolbox, region-aware ops)
                    Phase 2A-2C (multi-measurement, experiment, multi-input)
                              |
                              |  (all shipped; the platform Phase 7-9 build on)
                              v
        +---------------------------------------------------+
        |                    PHASE 7                        |
        |   image.threshold_segment (processing.image, NEW)  |
        |   FeatureDiagnostics (diagnostics, NEW)            |
        |   ExperimentModel feature aggregation (gui, ext.)  |
        |   ReportModel "Feature Analysis" section (gui, ext.)|
        +---------------------------------------------------+
                              |
                enables: ROI-seeding from a feature;
                a segmented-domain input for physics fits (optional; not required)
                              |
                              v
        +---------------------------------------------------+
        |                    PHASE 8                        |
        |   snomniman.physics (NEW module, own ADR)          |
        |   Drude/Lorentz fitting <-- Phase 6 processed spectra|
        |   FDM <-- Drude/Lorentz + tip geometry (NEW metadata gap)|
        |   LRM <-- FDM (deferred)                            |
        |   fringe/dispersion <-- deferred 2-D FFT (Phase 3B item, now has a consumer)|
        |   carrier density <-- Drude/Lorentz + FDM + user-supplied constants|
        +---------------------------------------------------+
                              |
                enables: physical-parameter facts as Briefing/report content;
                candidate triggers for future ReasoningRules
                              |
                              v
        +---------------------------------------------------+
        |                    PHASE 9                        |
        |   ai.build_experiment_briefing (NEW, ai -> pipeline edge)|
        |   ai outlier detection (NEW, ai -> pipeline edge)   |
        |   new ReasoningRules over Phase 7/8 facts (existing engine, EACH individually validation-gated)|
        |   Briefing narration of Phase 7/8 facts (extension) |
        |   cross-project comparison (DEFERRED, Beta-Readiness-gated)|
        +---------------------------------------------------+
```

### 6.2 Every prerequisite, explicit

| Capability | Hard prerequisite | Soft/data prerequisite |
|---|---|---|
| Phase 7 threshold segmentation (topography/optical) | `processing.image` registry, `Capability.SPATIAL_2D` | None - real CdO topography data available now |
| Phase 7 experiment-wide feature comparison | Phase 7 single-measurement `FeatureDiagnostics`; `gui.experiment.ExperimentModel` | Real multi-measurement data is thin (3 imaging measurements total) - validated but not richly exercised |
| Phase 7 hyperspectral/optical-domain segmentation on a cube | Phase 7 base + `DataKind.HYPERSPECTRAL` | **Blocked by Phase 5C** (no real hyperspectral cube exists) |
| Phase 8 Drude/Lorentz fit on a point spectrum | Phase 6 `spectrum.ratio`/`savgol_smooth`; new `snomniman.physics` module | None for the tool itself - real point-spectrum CdO data available now (internal-consistency validation only) |
| Phase 8 FDM inversion | Phase 8 Drude/Lorentz fitting primitive | **Blocked (soft):** no tip-geometry metadata field exists (Section 4.4); requires explicit user-supplied values |
| Phase 8 LRM | Phase 8 FDM | Deferred by design (Section 4.3.5), not currently blocked, simply not scheduled |
| Phase 8 broadband dielectric-function extraction | Phase 5A `fft_interferogram` output | **Blocked by Phase 5C** (no real interferogram file exists) |
| Phase 8 fringe/dispersion analysis | 2-D FFT primitive (new, but no new dependency - `numpy.fft`) | **Soft-blocked:** no confirmed real polaritonic-fringe sample in the current set |
| Phase 8 carrier-density estimation | Phase 8 Drude/Lorentz + FDM | **Blocked (soft):** no independent ground-truth carrier density for the real CdO sample exists in-repo |
| Phase 9 Experiment Briefing / outlier detection | `ai -> pipeline` edge (new, non-cyclic); Phase 7/8 optional (works today over existing `describe`/`diagnostics` facts alone) | None - can ship *before* Phase 7/8, reasoning only over what already exists, then gain more to reason over as 7/8 land |
| Phase 9 new `ReasoningRule`s over Phase 7/8 facts | Phase 7/8 shipped; **each rule individually Scientific-Validation-gated** | Real-data validation for each specific rule, case by case |
| Phase 9 cross-project comparison | A new project-loading mechanism (unscoped) | **Deferred**, gated on Beta Readiness user-testing evidence, not a data blocker |

**The single most important sequencing fact this graph makes explicit:** Phase 9's
*Experiment Briefing and outlier detection* have **no dependency on Phase 7 or Phase 8**
- they can be built first, reasoning over the facts SNOMNIMAN already has today. Only
Phase 9's *new recommendation rules* and *richer narration* need Phase 7/8 to exist
first. This reopens a legitimate sequencing question addressed in Section 8.

---

## 7. Deliverable 5 - Validation strategy

Per-capability validation requirements, stated against the same three-tier discipline
(analytical -> synthetic -> real-data) every prior scientific milestone in this project
has used.

| Capability | Analytical validation | Synthetic sufficient? | Real data required? | Regression tests (expected) | References (starting point) |
|---|---|---|---|---|---|
| Threshold segmentation | Closed-form (Otsu histogram-variance argument) | Yes, for shipping the tool | No (nice-to-have, CdO available) | Known-count synthetic image (N injected blobs -> N detected regions, within a documented pixel-count tolerance) | Otsu, N. (1979), *IEEE Trans. SMC* 9(1) |
| Per-feature morphology (area/perimeter/aspect ratio) | Yes (closed-form moment/perimeter formulas) | Yes | No (nice-to-have) | Known-shape synthetic regions (a circle, an ellipse of known eccentricity) recovered within tolerance | Standard image-moment formulas (any image-processing text); Gwyddion grain-analysis documentation as the SPM-domain precedent |
| Experiment-wide feature aggregation | N/A (pure aggregation) | Yes | Thin (3 real measurements) | `ExperimentTable` shape/CSV round-trip tests, mirroring ADR-0029's existing pattern | - |
| Drude/Lorentz oscillator fit (tool) | Yes (closed-form dielectric-function models) | Yes, for the tool DoD | For internal-consistency only (CdO point spectrum available now) | Known-parameter synthetic recovery (`(omega_p, gamma)` or `(omega_TO, S, gamma)` recovered within tolerance), mirroring `fit_lineshape`'s existing known-good/known-bad test pair | Ashcroft & Mermin (1976), *Solid State Physics*; Wooten, F. (1972), *Optical Properties of Solids* |
| FDM inversion | Yes, within the model's stated approximations | Yes, for the tool DoD | **Yes, for absolute accuracy** - a reference sample + tip geometry, `(user)`-gated | Forward/inverse round-trip on synthetic `epsilon(omega)` | Cvitkovic, Ocelic & Hillenbrand (2007), *Opt. Express* 15, 8550 |
| LRM | Yes (more complex derivation) | Yes, deferred implementation | **Yes**, `(user)`-gated, deferred | Same round-trip pattern as FDM, once implemented | Hauer, Engelhardt & Taubner (2012), *Opt. Express* 20, 13173; Govyadinov et al. (2014), *ACS Nano* 8, 6911 |
| Fringe/dispersion analysis | Yes (Fourier-transform theory is exact) | Yes, for the tool DoD | **Yes**, no confirmed sample yet, `(user)`-gated | Known-wavelength synthetic fringe pattern recovered exactly | Standard Fourier-optics treatment; near-field polariton imaging literature (to be reviewed at implementation time) |
| Carrier-density estimation | Yes, within stated assumptions | Yes, for the tool DoD | **Yes, absolute accuracy `(user)`-gated** (no independent reference for the real CdO sample) | Known-density synthetic round-trip | Standard doped-semiconductor optical-response literature (to be reviewed at implementation time) |
| Experiment Briefing | N/A (pure composition of already-validated facts) | N/A | No new requirement - reuses validated per-measurement facts | Same JSON-round-trip/source-tagging tests every `Briefing`/`Recommendation` type already has | - |
| Outlier detection (statistical) | Yes (z-score/IQR are closed-form) | Yes | Thin (3-4 real measurements limits how meaningful a "project distribution" is in-repo today) | Known-outlier synthetic project (one measurement's metric deliberately shifted) flagged correctly | Standard descriptive-statistics texts |
| Any new `ReasoningRule` (Phase 7/8 triggers) | **Case by case - full Scientific Validation Phase lifecycle required**, not covered by this document | Required, both branches | **Required, both branches** (fire and decline) | Per the existing `ReasoningRule` test pattern (`PlaneLevelRule`'s tests as the template) | Case by case, at study time |

**A note on what "sufficient" means here, restated from the brief's own framing:** for
every *tool* (an operation or analysis a researcher explicitly runs), synthetic
validation is sufficient to ship - this is the standing project convention (`fit_
lineshape`, `fft_interferogram`, `image.plane_level` all shipped this way). Real-data
validation is required only when a capability is asserted *automatically* (a
`ReasoningRule`, or any claim of absolute physical accuracy rather than internal
self-consistency) - which is precisely why Section 4 repeatedly separates "the fit
recovers the input it was given" (a tool claim, synthetic-sufficient) from "the fit is
physically correct for this sample" (a real-world claim, requiring an external
reference this repository does not currently have).

---

## 8. Deliverable 6 - Implementation roadmap

Many small, independently releasable milestones, per the brief's explicit preference and
the project's own established cadence (Phase 5A/5B/5C/5D, Phase 6 stages 1-4). Nothing
below is started by this document; it is the ordered menu for future sessions, subject to
re-prioritization once the still-open Beta Readiness user-testing protocol produces real
friction evidence (CLAUDE.md's standing governance order: product need, then scientific
validation, then implementation).

### Phase 7 milestones

| Milestone | Objective | Scientific value | Architectural impact | Complexity | Validation | Deliverables |
|---|---|---|---|---|---|---|
| **7A** | `image.threshold_segment`: a `ProcessingStep` producing a labeled integer channel from a threshold (fixed/percentile/Otsu) on any real-valued channel | Turns "I see particles" into a reproducible count | None (new `ProcessingStep`, existing registry) | Low | Known-count synthetic image; real CdO topography | New operation, Knowledge article, Manual page |
| **7B** | `FeatureDiagnostics`/`ParticleFeature`: per-label morphology + statistics descriptor | Turns segmentation into comparable numbers (size, shape, per-particle channel stats) | New `diagnostics` descriptor (ADR-0019 pattern) | Low-moderate | Known-shape synthetic regions; real CdO particle count sanity-check | New descriptor + Diagnostics panel surfacing (auto, no GUI code) |
| **7C** | Experiment-wide feature aggregation + CSV export + Report section | Compares particle populations across a project (a batch, a condition sweep) | Extends `gui.experiment.ExperimentModel` + `gui.report.ReportModel` (ADR-0029/Phase 4C patterns) | Low | `ExperimentTable`/CSV round-trip tests | New aggregate table, new Report section |
| **7D** (conditional) | Watershed splitting for touching particles | Only if 7A/7B demonstrably under-count on real multi-particle data | **New major dependency (`scikit-image`) - needs its own ADR** | Moderate-high | Synthetic touching-particle case; real data if/when available | New ADR, new operation variant |
| **7E** (conditional, blocked) | Optical-domain / hyperspectral-cube segmentation | Only once Phase 5C delivers real hyperspectral data | None beyond 7A generalized to a cube | Low (reuses 7A) | Real hyperspectral validation | Extends 7A's applicability |

### Phase 8 milestones

| Milestone | Objective | Scientific value | Architectural impact | Complexity | Validation | Deliverables |
|---|---|---|---|---|---|---|
| **8A** | Stand up `snomniman.physics`; implement the shared Drude/Lorentz dielectric-model fitting primitive as a tool over a processed spectrum's raw amplitude/phase (not yet tip-model-corrected) | Extracts physically-labeled resonance parameters, not just phenomenological curve parameters | **New module - own ADR (proposed ADR-0033)** | Moderate | Known-parameter synthetic recovery; internal-consistency check on real CdO spectrum | New module + ADR, Knowledge/Manual pages |
| **8B** | Finite dipole model (FDM) forward + inverse; add tip-geometry as an explicit, honestly-labeled fit parameter (not a metadata guess) | Connects the fitted near-field parameter to a physical `epsilon(omega)` | Extends `physics`; possibly a future additive `Metadata.probe` field (named, not built) | Moderate-high | Forward/inverse synthetic round-trip; real-data accuracy `(user)`-gated | FDM fitting tool, documented assumption-reporting |
| **8C** | Carrier-density estimation workflow (Drude/Lorentz + FDM + explicit user-supplied material constants) | The capability closest to the mentor's original research question | Extends `physics`; no new architecture | Moderate | Synthetic round-trip; absolute-accuracy validation `(user)`-gated (no in-repo ground truth) | Estimation tool with mandatory assumption echo-back |
| **8D** (conditional, deferred) | Lightning rod model (LRM) | Only if FDM proves insufficient for a real question | Extends `physics` | High | Same discipline as 8B, heavier implementation | New fitting mode |
| **8E** | Fringe/dispersion analysis via 2-D FFT | Resolves the Phase 3B-deferred 2-D FFT capability with a concrete consumer | New analysis function (no dependency) | Low-moderate | Synthetic known-wavelength recovery; real-data validation pending a suitable sample | New analysis + Knowledge/Manual pages |
| **8F** (blocked) | Broadband dielectric-function extraction from a real interferogram | Completes the nano-FTIR promise of the project name | None beyond 8A-8C generalized | Low (reuses 8A) | **Hard-blocked on Phase 5C** | N/A until unblocked |

### Phase 9 milestones

| Milestone | Objective | Scientific value | Architectural impact | Complexity | Validation | Deliverables |
|---|---|---|---|---|---|---|
| **9A** | `ai.build_experiment_briefing` over existing `describe`/`diagnostics` facts (no Phase 7/8 dependency - can ship independently, see Section 6.2's sequencing note) | Orientation for a whole project, not just one measurement - directly useful today | New `ai -> pipeline` edge (non-cyclic) | Low-moderate | Same JSON/source-tagging test pattern as `Briefing` | New function, Explorer Experiment-tab integration |
| **9B** | Deterministic outlier detection (z-score/IQR over a project's own metric distribution) | Flags "this measurement looks different from its siblings" honestly, without claiming why | Extends `ai` (new submodule, e.g. `ai.experiment`) | Low | Known-outlier synthetic project | New function + narration |
| **9C** | Briefing narration of Phase 7/8 facts (once they exist) | Completes "the AI's vocabulary is exactly the deterministic engine's vocabulary" for the new fact types | Extension only, no new mechanism | Low | Existing Briefing test pattern, extended | Updated Briefing sections |
| **9D** (each sub-item individually gated) | New `ReasoningRule`s triggered by Phase 7/8 facts | Turns new facts into workflow recommendations, same as `PlaneLevelRule` did for tilt | Uses the existing, unchanged `ai.reasoning` engine | Low per rule, but **each requires its own Scientific Validation study first** | Full lifecycle per rule (literature -> analytical -> synthetic -> real, both branches) | One `docs/<topic>-analysis.md` per candidate rule |
| **9E** (deferred) | Cross-project comparison | Only if Beta Readiness user-testing shows a real need | Unscoped (new loading mechanism) | Unscoped | Unscoped | Deferred - no deliverable until scoped |

### Suggested ordering (a recommendation, not a commitment)

1. **9A** first, deliberately out of the requested 7-8-9 order: it needs nothing new and
   delivers value immediately (Section 6.2's sequencing finding). This is the same kind
   of "ship the reusable low-risk piece first" reasoning that put Line Flatten ahead of
   Harmonic Ranking in the original triage.
2. **7A -> 7B -> 7C**, the settled-engineering track, in parallel with any science-track
   work - the same "product track advances independently of the science track" pattern
   `next-scientific-priorities.md` already established.
3. **8A -> 8C** (skip straight to carrier density's prerequisite chain, since it is the
   capability with the clearest real research motivation), deferring **8B**'s full FDM
   generality only as far as capability 7 needs it, **8D**/**8E**/**8F** named but not
   scheduled.
4. **9B -> 9C** once 7/8 exist to reason over.
5. **9D** items enter the existing Scientific Validation Queue (`scientific-
   validation.md` Section 7) individually, prioritized the same way Harmonic
   Ranking/Reference Normalization were - by real need, not by this document's order.
6. **7D, 7E, 8D, 8F, 9E** stay named-but-unscheduled, each behind its stated blocker
   (a new dependency decision, a data blocker, or a Beta-Readiness-evidence gate).

---

## 9. Governance recap (how this roadmap is meant to be used)

This document is itself governed by the same two systems it plans work for
(CLAUDE.md, "Planning and Governance"):

- **Beta Readiness** (`beta-readiness-v1.md`) still decides *whether* a milestone is
  worth building next - this roadmap does not override it. The still-open user-testing
  protocol should be run before committing hard to this document's suggested ordering.
- **Scientific Validation** (`scientific-validation.md`) still gates every *automated
  judgment* named above - this roadmap proposes tools freely but explicitly refuses to
  propose a single auto-recommendation rule or auto-asserted physical fact without its
  own study, per the brief's own constraint.
- New Scientific Validation Queue entries this document adds (Section 7 of
  `scientific-validation.md` should eventually list these): the Phase 9D candidate rules
  named in Section 5.3.3 (e.g. "recommend segmentation on bimodal histograms," "recommend
  a Drude fit on free-carrier-like decay"), and any future auto-classification of a
  detected feature's physical identity (Section 3.1's explicit out-of-scope item).

---

## References

Starting-point citations for the Phase 8 literature review (Section 4.3), to be
re-verified and expanded at that milestone's own Scientific Validation / operation-DoD
step, per this project's standing discipline of not treating a design document's
citations as a substitute for the real review:

- Otsu, N. (1979). "A threshold selection method from gray-level histograms." *IEEE
  Trans. Systems, Man, and Cybernetics*, 9(1), 62-66.
- Beucher, S. & Meyer, F. (1993). "The morphological approach to segmentation: the
  watershed transformation." In *Mathematical Morphology in Image Processing*.
- Ashcroft, N. W. & Mermin, N. D. (1976). *Solid State Physics*. (Drude model.)
- Wooten, F. (1972). *Optical Properties of Solids*. (Lorentz oscillator model.)
- Keilmann, F. & Hillenbrand, R. (2004). "Near-field microscopy by elastic light
  scattering from a tip." *Phil. Trans. R. Soc. Lond. A*, 362, 787-805. (Already cited
  in this codebase's `harmonic-ranking-analysis.md`.)
- Cvitkovic, A., Ocelic, N. & Hillenbrand, R. (2007). "Analytical model for quantitative
  prediction of material contrasts in scattering-type near-field optical microscopy."
  *Optics Express*, 15(14), 8550-8565. (Finite dipole model.)
- Hauer, B., Engelhardt, A. P. & Taubner, T. (2012). "Quasi-analytical model for
  scattering infrared near-field microscopy on layered systems." *Optics Express*,
  20(12), 13173-13188.
- Govyadinov, A. A., Mastel, S., Golmar, F., Chuvilin, A., Carney, P. S. & Hillenbrand,
  R. (2014). "Recovery of permittivity and depth from near-field data as a step toward
  infrared nanotomography." *ACS Nano*, 8(7), 6911-6921. (Lightning rod model.)
- Immerkaer, J. (1996). "Fast noise variance estimation." *Computer Vision and Image
  Understanding*, 64(2), 300-302. (Already shipped in this codebase's harmonic
  signal/noise classification, ADR-0026 - reused here as the precedent for
  single-image noise estimation, not re-derived.)

See also (this codebase's own governing documents, unchanged by this milestone):
[`scientific-validation.md`](scientific-validation.md),
[`beta-readiness-v1.md`](beta-readiness-v1.md),
[`architecture.md`](architecture.md) (Section 10, "Extending the system"),
[`ai-scientist-v1.md`](ai-scientist-v1.md),
[`scientific-reasoning.md`](scientific-reasoning.md),
[`diagnostics-engine.md`](diagnostics-engine.md),
[`phase6-spectral-lineshape-analysis.md`](phase6-spectral-lineshape-analysis.md) (the
direct precedent for Phase 8's "tool, not judgment" split and its
analysis-not-`ProcessingStep` placement),
[`next-scientific-priorities.md`](next-scientific-priorities.md) (the "possible vs.
recommend" framing this document applies throughout).
