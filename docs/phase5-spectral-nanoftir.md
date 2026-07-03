# Phase 5 - Spectral & nano-FTIR Support (Research & Design)

**Status:** Research -> Design proposal, largely implemented. **Phase 5A (Spectral
Processing Foundations, sec 6.1) shipped 2026-07-02** exactly per this design - no
architectural deviation, see the implementation note at the end of sec 6.1.
**Phase 5B (Hyperspectral Data Model & Viewer, sec 6.2) shipped 2026-07-02** -
see the implementation note at the end of sec 6.2 (confirms `is_hyperspectral`
as designed, and records one real Preview-path bug found and fixed during
implementation). Phases 5C-5D remain unimplemented/blocked as described below.
**Date:** 2026-07-02
**Stance:** a researcher who has just finished a full imaging + processing +
batch + reporting workday (Phases 1-4C) asks the next question: *the sample also
has a vibrational fingerprint - how do I get an actual spectrum out of this
instrument, and how do I map it across the sample?*

This document is the research-and-design milestone the user commissioned for
**Phase 5 - Spectral & nano-FTIR Support**. It contains **no code** and proposes
**no redesign of settled architecture** (OHD-1..9, `decisions.md`); every
recommendation below is either a documented-but-unbuilt extension point
(`docs/data-model.md` anticipated `SPECTRUM`/`LINE_SCAN`/`INTERFEROGRAM`/
`HYPERSPECTRAL` since Phase 0) or a small, precedented, additive change following
a pattern the codebase already uses at least once. It is held to the project
maxim - *"two things we can defend over four we can't."*

> **Naming note.** This is the second time "Phase 5" appears for this topic.
> `docs/roadmap.md` sec "Phase 5 - nano-FTIR spectroscopy [NOT STARTED]" was
> written during Phase-0 planning, before the iterative work-breakdown that
> actually happened (Phases 1, 2A/B/C, 3A/B/C, 4A/B/C, tracked in `LOG.md`/
> `NEXT.md`) existed. That numbering is stale but, by coincidence, lands on the
> same number as the current sequence's natural next milestone after 4C - this
> document is the authoritative Phase 5 planning artifact going forward
> (the same relationship `beta-readiness-v1.md` has to `product-review-v0.1.md`).
> Point spectroscopy (single spectrum + line-of-spectra) already shipped ahead of
> this numbered phase, as a "vertical slice" validating that the anticipated data
> model held up against real data (`docs/point-spectrum-discovery.md`). This
> document covers what point spectroscopy deliberately left out: **interferometric
> nano-FTIR** (the FFT half), **hyperspectral cubes** (the 2-D chemical-mapping
> half), and the processing/analysis/viewer work both require.

---

## 0. The thesis, in one paragraph

SNOMNIMAN's imaging platform is mature end-to-end (Phases 1-4C): load, browse,
process, batch, report, all provenance-bearing. Point spectroscopy proved the
architecture's hybrid dispatch model (`DataKind` + `Capability`) *already*
anticipated spectral data correctly at the `core` layer - a real point-spectroscopy
file loaded, rendered, and diagnosed with zero core changes. Phase 5 asks whether
that holds for the two things point spectroscopy deliberately did not attempt:
turning a **raw interferogram** into a spectrum (the actual "FTIR" in nano-FTIR,
via a numerical Fourier-transform pipeline that does not exist anywhere in the
codebase today), and a **hyperspectral cube** (a full spectrum at every pixel of a
2-D scan - the technique's single most scientifically distinctive capability:
spatially-resolved chemical identification at nanoscale resolution). The answer,
argued in Section 3: **the data model still holds** (no `Capability`/`DataKind`
redesign; one new capability derivation is the only enum-level change needed); the
**processing/viewer/diagnostics layers need real, additive work** (a wholly new
numerical domain - FFT/apodization/phase correction - and a wholly new GUI surface
- a linked band-map + spectrum viewer); and **the readers for both real file
formats are honestly blocked** on real vendor sample data that does not yet exist
in this repository, exactly as happened twice before (Phase 1's imaging reader,
the point-spectroscopy vertical slice) and exactly as Rule 6 requires ("never
build a reader/viewer/AI feature ahead of real data").

---

## 1. The load-bearing distinction (read before everything else)

The task asks for a clear line between imaging, spectroscopy, hyperspectral
analysis, and future physics modeling. The existing `Capability` model already
draws exactly this line - it was just never populated past the first two rows:

| Regime | Capability signature | Spatial view | Spectral view | Status |
|---|---|---|---|---|
| **Imaging** | `SPATIAL_2D`, no `SPECTRAL` | one image per channel | none | Shipped (Phases 1-4C) |
| **Point spectroscopy** | `SPECTRAL` (+ `SPATIAL_1D` for a line), no `SPATIAL_2D` | none (or a 1-D position axis) | one curve (or curve-per-position) | Shipped (vertical slice) |
| **Hyperspectral imaging** | `SPATIAL_2D` **and** `SPECTRAL` together | a "band map" per wavenumber | a curve per pixel | **This document, 5B** |
| **Interferometric acquisition** | raw: a new `INTERFEROMETRIC` capability (opd-domain, not yet spectral); after FFT: `SPECTRAL` (+ `SPATIAL_2D` if a hyperspectral interferometric cube) | as above, once FFT'd | as above, once FFT'd | **This document, 5A/5C** |
| **Future physics modeling** (finite-dipole fitting, permittivity extraction, polariton dispersion) | consumes facts `diagnostics` produces; adds none itself | n/a | n/a | **Explicitly out of scope** - a later, separately-validated concern |

The critical finding driving this whole document: `ExplorerModel.is_spectral`
(the property every current spectral GUI branch keys on) is defined as
`Capability.SPECTRAL in caps and Capability.SPATIAL_2D not in caps` - **a
hyperspectral dataset would evaluate this to `False`** (it has both capabilities)
and silently fall through to the plain 2-D image path, which has no notion of a
`wavenumber` dimension and would misrender or crash. This is not a redesign
signal - it is the same *shape* of gating bug the point-spectroscopy milestone
already found and fixed once (`diagnostics._classify_harmonic` gating on `ndim`
instead of `Capability.SPATIAL_2D`, `point-spectrum-discovery.md`). The fix is the
same discipline applied prospectively: hyperspectral needs its **own** dispatch
state (`is_hyperspectral`), never an overload of `is_spectral`. This single
recommendation is the architectural hinge the rest of the design turns on.

---

## 2. Deliverable 1 - Scientific Workflow Survey

### 2.1 Method

Real nano-FTIR/hyperspectral/point-spectroscopy workflows, ranked by scientific
importance - not software features. Sourced from published nano-FTIR methodology,
the neaspec/attocube technology description, and phonon-polariton near-field
literature (a common nano-FTIR/s-SNOM application), cross-checked against what the
existing codebase and Knowledge articles already say. neaPLOT itself has almost no
public documentation (confirmed by search) - consistent with the project's
existing caution about neaPLOT comparisons; this survey leans on the science, not
vendor-software specifics.

### 2.2 The workflows, ranked

**W1 - Point spectrum at a location of interest.** *(Rank 1 - shipped)*
- *Goal:* identify a vibrational/phonon resonance (a peak or dip in amplitude or
  phase vs. wavenumber) at one spot before deciding what to image at scale.
- *Status:* shipped end-to-end (`docs/point-spectrum-discovery.md`). Not
  re-covered here except where hyperspectral/interferogram work extends it.

**W2 - Hyperspectral chemical/band mapping.** *(Rank 1 of what remains - the
technique's signature capability)*
- *Goal:* a full spectrum at *every pixel* of a 2-D scan, from which a researcher
  extracts a "band map" (amplitude/phase at one wavenumber, shown as an ordinary
  2-D image) or a compositional map (clustering pixels by spectral similarity).
- *Why it matters:* this is nano-FTIR's most distinctive scientific promise -
  nanoscale-resolved chemical identification, not just topography/near-field
  contrast at one frequency. Recording "two-dimensional arrays of several
  thousand... spectra... in a few hours" with "spatial resolution and precision
  better than 30 nm" is the literature's own framing of why this matters; the data
  cube is then typically explored via band maps and multivariate/cluster analysis
  to produce a compositional map.
- *Current SNOMNIMAN support:* none - `ExplorerModel` has no method that slices a
  cube to one wavenumber or extracts a per-pixel spectrum (confirmed: every
  spatial method assumes exactly one spatial dimensionality).

**W3 - ROI-averaged spectra from a cube.** *(Rank 2)*
- *Goal:* rather than one pixel's noisy spectrum, average the spectrum over a
  hand-drawn region (e.g. "on the nanostructure" vs. "off it") for a
  higher-SNR comparison.
- *Current SNOMNIMAN support:* the region-mask machinery (`rect_mask`/
  `polygon_mask`/`region_stats`) is **already fully generic 2-D** and reusable
  per-wavenumber-slice with no modification - a strong, concrete reuse point.

**W4 - Spectral comparison (across positions, samples, or on/off a feature).**
*(Rank 2)*
- *Goal:* overlay two or more spectra (e.g. a resonance on vs. off a
  nanostructure, or across different samples) to compare peak position/shape.
- *Current SNOMNIMAN support:* none - `SpectrumPlotView` renders exactly **one**
  curve; there is no overlay/legend/multi-curve mechanism at all today.

**W5 - Resonance/peak identification.** *(Rank 2)*
- *Goal:* locate a vibrational or phonon-polariton resonance's position, width,
  and prominence from a spectrum - the quantitative fact a researcher reports
  ("the C=O stretch is at 1735 cm^-1, FWHM 12 cm^-1"). Phonon-polariton work
  specifically looks for characteristic resonance line shapes and shifts near a
  material's Reststrahlen band.
- *Current SNOMNIMAN support:* **zero spectral diagnostics exist** - but
  `viz.measure.analyze_profile`/`_detect_peaks` are already a fully generic 1-D
  peak-finder (`scipy.signal.find_peaks`), used today for line-profile features -
  the single strongest reuse opportunity in this whole survey.

**W6 - Interferogram -> spectrum processing (apodization, phase correction,
zero-fill, FFT).** *(Rank 1 of the processing chain - the prerequisite for
everything genuinely "FTIR")*
- *Goal:* the actual Fourier-transform computation nano-FTIR is named for: an
  interferogram (signal vs. optical path difference) is apodized (windowed),
  zero-filled, phase-corrected (commonly the Mertz method), and Fourier-
  transformed into a complex spectrum (amplitude + phase vs. wavenumber).
  Conventional FTIR literature describes exactly this pipeline; nano-FTIR is a
  near-field variant of the same underlying computation.
- *Current SNOMNIMAN support:* **none whatsoever** - confirmed by an
  implementation-wide search: no FFT, apodization, or windowing code exists
  anywhere in `src/snomniman`. This is the first genuinely new numerical/
  signal-processing domain since Phase 1's image ops.

**W7 - Spectral reference normalization.** *(Rank 3)*
- *Goal:* divide a sample spectrum by a reference spectrum (e.g. gold or doped
  silicon) to remove the wavenumber-dependent instrument response, following the
  same normalization logic Huth et al. established for nano-FTIR (already the
  project's `_HUTH` citation in `knowledge/library.py`).
- *Current SNOMNIMAN support:* none for spectra (the existing
  `image.reference_normalize` op is `SPATIAL_2D`-gated); the *concept* -
  divide-by-reference - is already validated science in the codebase for images,
  so a spectral analogue is a natural, low-risk extension, not new science.

**W8 - Atmospheric (water vapor / CO2) correction.** *(Rank 4 - deferred detail)*
- *Goal:* mid-IR spectra are contaminated by atmospheric water vapor/CO2
  absorption lines; correction methods range from simple reference subtraction to
  more advanced multispectral least-squares fitting.
- *Current SNOMNIMAN support:* none. **Deferred** in this design (see Section 6):
  it needs either a validated reference line-list or a clean reference spectrum,
  which the existing `roadmap.md` placeholder itself already flagged as an open
  question ("needs a reference line-list / clean reference - confirm
  availability"). Not blocking 5A-5D.

**W9 - Spectral export for downstream tools (Origin, Python).** *(Rank 5 -
logistics, but the established "switch-back point" pattern)*
- *Goal:* get a processed spectrum or ROI-averaged spectrum out as CSV, and a
  processed cube out as Zarr (or a per-band GSF slice for Gwyddion/neaPLOT-style
  tools).
- *Current SNOMNIMAN support:* Zarr export already works for any `Dataset`
  regardless of dims (confirmed: `write_zarr`/`read_zarr` are channel/dim-
  agnostic - `data-model.md` sec 10's own claim, and the mechanism by which
  point-spectroscopy already round-trips without a Zarr-layer change); CSV/GSF
  export are currently hard-blocked for any spectral measurement in `window.py`
  and need small, real extensions once there's something to export.

### 2.3 Ranked summary

| # | Workflow | Value | Reuse available | Phase 5 driver |
|---|----------|:---:|---|:---:|
| W1 | Point spectrum at a location | High | Shipped | Done |
| W2 | Hyperspectral band/chemical mapping | **Highest remaining** | `prepare_channel`/`RenderData` per-slice | **Yes (5B)** |
| W3 | ROI-averaged cube spectra | High | `rect_mask`/`polygon_mask`/`region_stats` (as-is) | Yes (5B) |
| W4 | Spectral comparison (overlay) | High | None (new viewer feature) | Yes (5B) |
| W5 | Resonance/peak identification | High | `analyze_profile`/`_detect_peaks` (as-is) | Yes (5D, validation-gated) |
| W6 | Interferogram -> spectrum (FFT) | **Highest - the prerequisite** | None (net-new numerics) | **Yes (5A)** |
| W7 | Spectral reference normalization | Medium-high | `image.reference_normalize`'s *concept* | Yes (5A) |
| W8 | Atmospheric correction | Medium | None; needs a reference line-list | Deferred |
| W9 | Spectral export | Medium (the switch-back point) | Zarr (as-is); GSF/CSV (small extension) | Yes (5A/5B, incidental) |

---

## 3. Deliverable 2 - Architecture Analysis

### 3.1 What already works (zero change needed)

1. **The hybrid dispatch model already derives hyperspectral capabilities
   correctly.** `core.dataset._derive_capabilities` checks `{"x","y"} <= coords`
   (-> `SPATIAL_2D`) and `"wavenumber" in coords` (-> `SPECTRAL`) **independently**
   - a dataset with `x`, `y`, **and** `wavenumber` coordinates already derives
   `{SPATIAL_2D, SPECTRAL}` together, today, with the code exactly as it stands.
   This is the single most important validation finding: **the `core` layer needs
   no change for hyperspectral data** - exactly the same conclusion the
   point-spectroscopy milestone reached for point/line spectra.
2. **`DataKind.HYPERSPECTRAL` and `DataKind.INTERFEROGRAM` already exist** in the
   enum (`core/datakind.py`), reserved since Phase 0, unused until now.
3. **A `ProcessingStep` may already change `DataKind` between input and output.**
   `ProcessingStep._execute` returns `(xr.Dataset, DataKind, Metadata)` - the
   `DataKind` is not fixed by the step's input. An FFT step turning an
   `INTERFEROGRAM` into a `SPECTRUM` (or `HYPERSPECTRAL`) is therefore an
   **already-supported pattern**, not a special case requiring engine changes.
4. **The provenance DAG, `Recipe`, and `snomniman.batch` are already
   modality-agnostic.** None of them inspect dims/`DataKind` - a recipe capturing
   "FFT -> reference-normalize" on one nano-FTIR measurement replays across many
   via the unchanged `apply_recipe`/`run_batch`, and `gui/report.py`'s three
   reports compose over whatever facts exist, with **zero changes required** to
   any of Phase 4's three milestones. This is a direct, concrete payoff of
   Phase 4's investment.
5. **The canonical Zarr store is channel/dim-agnostic** (`write_zarr`/`read_zarr`
   persist whatever `xarray.Dataset` structure is handed to them; the
   SNOMNIMAN-level semantics are a JSON sidecar attribute, independent of array
   shape) - a hyperspectral cube or an interferogram dataset is expected to
   round-trip with no store-layer change, exactly as point spectra already do.
   (Flagged in Section 6 as the first thing a Phase 5 test suite should confirm
   with a synthetic cube, per Rule 6 - expected, not yet verified.)
6. **`viz.measure`'s two families of primitives are already exactly what
   hyperspectral/spectral analysis needs, unmodified:**
   - `rect_mask`/`polygon_mask`/`region_stats` - generic over any 2-D array +
     coordinate grid; reusable per-wavenumber-slice for an ROI-averaged spectrum
     (W3) with no change.
   - `analyze_profile`/`_detect_peaks` - generic over any `(positions, values)`
     1-D pair; reusable verbatim for spectral peak/resonance detection (W5) by
     passing `(wavenumber_cm1, amplitude)` instead of `(distance_nm, samples)`.
7. **`describe`/`diagnostics` already degrade honestly for shapes they don't
   understand** (the exact discipline point spectroscopy validated and then
   hardened): `topography_diagnostics` requires `SPATIAL_2D`;
   `_classify_harmonic` requires `SPATIAL_2D` (post-fix); a hyperspectral or
   interferogram dataset will fall through the same honest `None`/`"unknown"`
   paths already proven correct, needing no new defensive code, only new
   *positive* descriptors added alongside.
8. **The Knowledge Center / project maxim already anticipated this exact split**
   - `concept.point_spectrum`'s own `scientific_background` states nano-FTIR
     "does not yet read or FFT an interferogram" and that the two share the same
     `SPECTRUM`/`LINE_SCAN`/`HYPERSPECTRAL` representation "once in the frequency
     domain" - this document is that forward reference being discharged.

### 3.2 What naturally extends (small, additive, precedented)

1. **`Metadata.spectral: SpectralInfo`** already covers the *spectral axis*
   geometry; `data-model.md` sec 6 already sketches (but never implemented) an
   `interferometer` metadata section (`mirror_velocity`, `spectral_resolution_cm1`,
   `zero_fill`, `apodization`). Add it exactly the way `SpectralInfo` was added
   next to `ScanInfo`: a new optional dataclass, default `None`, zero impact on
   every existing construction path.
2. **A `Capability.INTERFEROMETRIC`** (or similarly named) member, derived from
   an `opd` coordinate, exactly mirroring how `SPECTRAL`/`SPATIAL_1D` were added
   originally. This is the **one** enum-level change this document proposes - it
   lets a future `spectrum.fft_interferogram` op declare
   `required_capabilities=(Capability.INTERFEROMETRIC,)` the same way every image
   op already declares its requirements.
3. **`ExplorerModel.is_hyperspectral`** (new, alongside the existing
   `is_spectral`) - the third dispatch state Section 1 identified as load-bearing:
   `Capability.SPATIAL_2D in caps and Capability.SPECTRAL in caps`. `window.py`'s
   eleven existing `is_spectral` branches are the direct template for the
   parallel `is_hyperspectral` gating a new viewer page needs (a new
   `_image_only_buttons`-style disablement list, a new stack page, the same
   "friendly message, not a crash" discipline for exports that don't yet apply).
4. **`ExplorerModel.band_map(wavenumber_index)`** - slices one channel to one
   wavenumber and hands the result through the *existing* `prepare_channel`
   machinery unmodified (colormap/levels/extent/scale-bar logic is already
   correct for any 2-D array; only the slicing step is new).
   **`ExplorerModel.pixel_spectrum(x_index, y_index)`** - the mirror-image
   operation, returning a `SpectrumCurve` (same value object point spectroscopy
   already introduced) from one spatial pixel of a cube.
5. **A `processing.spectrum` subpackage**, structurally identical to
   `processing.image`: `ProcessingStep` subclasses + `@register`, e.g.
   `spectrum.fft_interferogram`, `spectrum.reference_normalize`,
   `spectrum.crop_range`. No processing-framework change - this is exactly the
   "no GUI code needed for a new operation" story Phase 1's Processing Workspace
   already delivers, applied to a new domain.
6. **New `describe`/`diagnostics` descriptors** (a `ResonancePeak`/
   `SpectralDiagnostics`-shaped fact), following `HistogramData`'s/
   `SpectralGeometryDescription`'s exact pattern (a frozen, JSON-serializable
   dataclass; `None` fields where genuinely unknown).
7. **New Knowledge articles** (`concept.interferogram`, `concept.apodization`,
   `concept.hyperspectral_cube`, one `operation.spectrum.*` per new op) following
   the existing category/cross-link/no-drift conventions exactly.
8. **`ai/briefing.py`'s spectral-range sentence** (already the only spectral-aware
   AI code, a single `_fact(...)` line) is the template for a hyperspectral
   band-count/range sentence and, later, a resonance call-out - same pattern,
   more facts.
9. **A per-band GSF export** (`io.export_channel_gsf` applied to one wavenumber
   slice of a hyperspectral channel) - a small, real extension of the existing
   image-export mechanism, not a new export format.

### 3.3 What requires genuine, new work (no existing code to extend)

1. **The FFT/apodization/phase-correction numerics themselves.** Confirmed by an
   implementation-wide search: zero prior art. This is Phase 5's real
   engineering content and its first genuinely new scientific-computation domain
   since Phase 1's image operations - it needs the full validation discipline
   (Rule 6: synthetic interferograms with a known analytic spectrum, to a
   documented numerical tolerance) before it can be trusted on real data.
2. **A linked band-map + spectrum viewer.** `SpectrumPlotView` is a single-curve
   widget with no 2-D display and no overlay mechanism; there is no existing
   widget that shows an image and a curve side by side, linked by pixel
   selection. This is the one genuinely new GUI surface Phase 5 needs (thin,
   presentation-only per Rule 4 - it renders `band_map`/`pixel_spectrum` output,
   computes nothing).
3. **Multi-curve overlay/comparison in the spectral viewer** (W4) - a smaller,
   related GUI extension to the same widget family.

### 3.4 Architecture verdict

No settled decision (OHD-1..9) is reopened. The `core` data model needs exactly
one small, precedented enum addition (`Capability.INTERFEROMETRIC`) and one
additive metadata dataclass (`Metadata.interferometer`); everything else in
Sections 3.1-3.2 is composition of what already exists. The genuinely new work -
FFT numerics and a linked band-map/spectrum viewer - is real, bounded, and does
not touch anything upstream of `processing`/`gui`. This is the cleanest possible
outcome the task's "avoid speculative redesign" constraint could hope for, and it
mirrors the point-spectroscopy milestone's own conclusion almost exactly.

---

## 4. Deliverable 3 - Data Model Design

**What is a spectral measurement?** Unchanged from the shipped model: a `Dataset`
whose `data_vars` carry a `wavenumber` (and, for a line/cube, a spatial)
coordinate instead of - or alongside - `x`/`y`. Phase 5 adds two shapes to the
existing table (`data-model.md` sec 2 already names both `DataKind`s; only the
dims below are new detail):

| `DataKind` | Dims (per channel) | Capabilities derived | Content |
|---|---|---|---|
| `INTERFEROGRAM` | `(opd,)` or `(y, x, opd)` for a hyperspectral-interferometric acquisition | `INTERFEROMETRIC` (new) [+ `SPATIAL_2D`] | raw signal vs. optical path difference - **not yet a spectrum** |
| `HYPERSPECTRAL` | `(y, x, wavenumber)` | `SPATIAL_2D` + `SPECTRAL` (both already derived correctly) | a complex spectrum at every pixel |

**How should hyperspectral cubes be represented?** Exactly like an image dataset,
with one more dimension per channel: `O2` becomes a 3-D `(y, x, wavenumber)`
array instead of 2-D `(y, x)`, keeping the existing per-channel-variable pattern
(ADR-0003) rather than adding a `channel` dimension. Complex assembly, amplitude/
phase views, and channel `state` tracking are unchanged - they operate per-array
regardless of how many dimensions that array has.

**How should point spectra differ from images?** Unchanged from the shipped
answer (`SPECTRUM`/`LINE_SCAN`, no `SPATIAL_2D`); hyperspectral differs from both
by carrying **both** a spatial and a spectral axis simultaneously, which is
exactly the compound-capability case Section 3.1 confirms the model already
handles.

**How should spectral datasets integrate with `Measurement`?** No change:
`Measurement.datasets` is already a plain tuple of `Dataset`s regardless of kind.
A nano-FTIR measurement's `.raw` is an `INTERFEROGRAM` dataset; after an FFT step
is accepted, `.current` is a `SPECTRUM`/`HYPERSPECTRAL` dataset, appended to
history exactly like any derived image dataset. `Recipe`/`snomniman.batch`
already replay this generically (Section 3.1 point 4).

**How should provenance work?** No new concept. The FFT step is one more
`StepRecord` node (`step_id="spectrum.fft_interferogram"`, params = apodization
function, zero-fill factor, phase-correction method) referencing the raw
`INTERFEROGRAM` node as its `primary` input - a single-input, `DataKind`-changing
step, already legal (Section 3.1 point 3).

**How should exports work?** Zarr: expected to work unchanged (Section 3.1 point
5, to be confirmed by test). GSF: stays blocked for pure spectra (not a 2-D grid
format); a hyperspectral cube's **single band-map slice** is a normal 2-D grid and
can reuse `io.export_channel_gsf` once `ExplorerModel.band_map` exists. CSV:
extend the existing `profile_to_csv`/`region_to_csv` pattern to a spectrum (a
`wavenumber_cm1` column instead of `distance_nm`) - same provenance-header
convention, same `gui/export.py` module.

---

## 5. Deliverable 4 - User Workflow

1. **Open a nano-FTIR interferogram measurement** (once 5C's reader exists). The
   Explorer shows it exactly as it shows any raw measurement today - identity,
   metadata (now including the interferometer section), a single `io.read`
   provenance node. A new interferogram view (signal vs. OPD, structurally the
   `SpectrumPlotView` pattern with an `opd` x-axis instead of `wavenumber`) lets a
   researcher **inspect the raw interferogram before processing** - checking ZPD
   position/symmetry is itself a legitimate "explore before you process" step.
2. **Apply FFT processing through the same generic Processing Workspace** - no
   new GUI code per operation. Select `spectrum.fft_interferogram`, choose
   apodization/zero-fill/phase-correction parameters, Preview (see the resulting
   spectrum before committing), Accept - identical lifecycle to every existing
   operation.
3. **Browse the resulting spectrum** in the (now dual-mode) spectral viewer: a
   single curve for `SPECTRUM`, or - for a hyperspectral result - the new linked
   band-map + per-pixel-spectrum view (5B): pick a wavenumber, see a 2-D band map
   through the *existing* image-rendering machinery; click a pixel, see its
   spectrum.
4. **Select an ROI on a band map**; get a mean spectrum over that region (reusing
   `rect_mask`/`polygon_mask`/`region_stats` per-slice, W3).
5. **Compare spectra** - overlay two or more curves (a point vs. another point, a
   sample vs. a reference) in the extended spectral viewer (W4).
6. **Read spectral diagnostics** in the existing Diagnostics tab: a resonance's
   position/width/prominence (5D, reusing `analyze_profile` verbatim), degrading
   honestly to absent/`"unknown"` where not applicable - the same pattern
   `harmonic_diagnostics` already uses.
7. **Process further and automate it**: reference-normalize the spectrum (W7);
   capture the whole chain (FFT params + normalization) as a **Recipe** (Phase
   4A, unchanged) and **batch**-replay it (Phase 4B, unchanged) across every
   nano-FTIR measurement in the experiment - zero new automation code, only the
   new ops being registered.
8. **Export**: Zarr (works today, to be confirmed); CSV of a processed spectrum
   or ROI-averaged spectrum (small `gui/export.py` extension); a band map as GSF
   for Gwyddion/neaPLOT-style tools (small extension).
9. **Generate a report** (Phase 4C, unchanged): the Experiment Report/
   Publication Package/Reproducibility Report already compose over whatever
   facts exist for a measurement - a nano-FTIR experiment's report "just works"
   the moment the new facts (spectral diagnostics, FFT provenance) exist, with
   **zero changes needed to `gui/report.py`**.
10. **Compare experiments**: `ExperimentModel.browser_rows()` gains a
    hyperspectral/interferogram-aware summary label (analogous to today's
    "harmonics"/"processing" columns) - a small, additive extension, not a
    redesign of the experiment browser.

This workflow is a straight extension of the existing one at every step except
2 (new operations, same Workspace) and 3/4/5 (the one genuinely new viewer) -
exactly the "feels like a natural extension of today's application" bar the task
sets.

---

## 6. Deliverable 5 - Phase 5 Roadmap

Four milestones emerge from the research, not the task's example labels
verbatim - the split follows the real dependency structure (synthetic-validatable
now vs. blocked on real data vs. validation-gated science).

### 6.1 Phase 5A - Spectral Processing Foundations

- **Objective.** A `processing.spectrum` subpackage: `spectrum.fft_interferogram`
  (apodization window choice, zero-fill factor, phase correction - commonly the
  Mertz method - complex FFT to a complex spectrum) and `spectrum.
  reference_normalize` (divide by a reference spectrum, the Huth et al.
  approach already cited in this codebase). Plus the one `Capability`
  addition (`INTERFEROMETRIC`) and the `Metadata.interferometer` field.
- **Scientific value.** Unlocks the actual Fourier-transform computation
  nano-FTIR is named for - currently the *only* spectral acquisition mode
  supported (PsHet direct wavenumber sweep) is explicitly, deliberately
  distinguished from this in the existing Knowledge article.
- **Complexity.** Medium-High - the first wholly new numerical/signal-processing
  domain in the codebase; no prior art to extend, so correctness rests entirely
  on synthetic validation (a known analytic line shape, inverse-FFT'd into a
  synthetic interferogram, processed, and compared to the known input spectrum
  within a documented tolerance).
- **Architectural impact.** Minimal - one enum member, one additive metadata
  dataclass, a new `ProcessingStep` subpackage following the exact existing
  pattern (registry, `ParameterSpec`, capability-gating).
- **Dependencies.** None to start (buildable and synthetically validatable now).
  **Real-data cross-validation against an actual interferogram is `(user)`-gated**
  - no such sample exists in the repository today (only 3 imaging + 1
  point-spectroscopy measurement are present).

**Implementation note (2026-07-02, no architectural deviation).** The mathematical
foundation - `spectrum.fft_interferogram` (apodization, zero-fill, Mertz phase
correction, forward FFT), `Capability.INTERFEROMETRIC`, and
`Metadata.interferometer` - shipped exactly as designed above; see
`src/snomniman/processing/spectrum/`, `tests/test_processing_spectrum_fft_interferogram.py`
(31 tests, incl. a synthetic-Lorentzian known-answer round trip per Appendix A),
and the new `concept.interferogram` / `concept.apodization` /
`operation.spectrum.fft_interferogram` Knowledge articles. `spectrum.
reference_normalize` was **not** part of this increment (out of scope for the
"mathematical foundation" milestone that commissioned this work) and remains open
for a follow-up increment - it is a smaller, precedented extension (the spectral
analogue of the already-shipped `image.reference_normalize`), not a blocker for
5B/5C/5D.

One genuine numerical finding surfaced during implementation and validation, not
anticipated by the design above: **apodization windows must be centered on the
zero-path-difference (ZPD) sample, not the array's geometric center.** A
textbook-symmetric window (Hann, Hamming, Blackman-Harris) naively applied across
the raw array is zero at both ends; for a single-sided interferogram (ZPD at or
near the array's first sample - the common acquisition geometry `docs/data-model.md`
sec 2 already anticipated with dims `(opd,)`), this silently zeroes out the
highest-amplitude sample and collapses the recovered spectrum. The shipped
`apodization_window` evaluates a symmetric window of length
`2 * max(zpd_index, n - 1 - zpd_index) + 1` and slices out the portion matching the
actual (possibly asymmetric) sample span, so the window's peak lands exactly on
ZPD regardless of where it falls in the array - the standard treatment for
asymmetric interferograms (Griffiths & de Haseth 2007 ch. 3), just not spelled out
in the original design. This is a numerics-level implementation detail, not an
architectural one; no capability/DataKind/metadata shape changed as a result.

### 6.2 Phase 5B - Hyperspectral Data Model & Viewer

- **Objective.** `ExplorerModel.is_hyperspectral` (a genuine third dispatch
  state, never an overload of `is_spectral` - Section 1's central finding),
  `band_map(wavenumber_index)` and `pixel_spectrum(x, y)` methods, and the one
  genuinely new GUI surface: a linked band-map-image + per-pixel-spectrum
  viewer, plus multi-curve overlay in the spectral viewer (W4). Window-level
  gating mirrors the eleven existing `is_spectral` branches exactly (a parallel
  disablement list, a new stack page, honest "not available" messages for
  exports that don't yet apply).
- **Scientific value.** The technique's single most distinctive capability -
  spatially-resolved nanoscale chemical identification - directly serving the
  product's own stated ambition ("nanoscale chemical mapping," CLAUDE.md
  Overview).
- **Complexity.** Medium - mostly GUI; the backend numerics are almost entirely
  reused (`prepare_channel`, `rect_mask`/`polygon_mask`/`region_stats`).
- **Architectural impact.** Low - no `Capability`/`DataKind` change (the
  combination already derives correctly); the new viewer is presentation-only
  (Rule 4).
- **Dependencies.** Benefits from 5A (band maps of a *processed* spectrum) but
  can ship independently against a **synthetic** hyperspectral cube fixture
  first (a small array with a known embedded resonance at known pixels).
  **Real-cube ingestion is 5C**, not this milestone.

**Implementation note (2026-07-02, no architectural deviation).** Shipped
exactly as designed: `ExplorerModel.is_hyperspectral` (confirmed against live
source before implementation - `is_spectral` evaluates `False` for a
hyperspectral dataset, since it has both `SPATIAL_2D` and `SPECTRAL`, so a
genuine third state was required, not an overload); `band_map`/`pixel_spectrum`/
`rect_spectrum`/`polygon_spectrum`/`nearest_pixel` on `ExplorerModel`; a new
`HyperspectralView` widget (`src/snomniman/gui/hyperspectral.py`) composing the
*unmodified* `ChannelImageView` (band map) and an additively-extended
`SpectrumPlotView` (`show_curves` for multi-curve overlay) in a splitter; the
Measurements framework extended with a `spectral` mode
(`MeasurementController.rebind`, `SpectralRegionReport`, a new "Overlay ROI
spectra" action left separate from the unchanged "Compare regions"); Report/
Export/Knowledge integration. Validated against a synthetic hyperspectral cube
fixture with a known embedded resonance (Rule 6) - real-cube ingestion stays
5C, blocked on real sample data as designed. See
`tests/test_gui_hyperspectral.py`, `tests/test_gui_measurement.py`,
`tests/test_gui_model.py`, `tests/test_viz_render_band.py`.

One genuine bug was found and fixed during implementation, not anticipated by
this design: `ExplorerModel.preview_operation`/`preview_recipe` unconditionally
built image-shaped preview panes via `viz.prepare_channel`, which
unconditionally requires `x`/`y` coordinates - for a `SPECTRUM`/`LINE_SCAN`/
`INTERFEROGRAM` focus channel (e.g. previewing Phase 5A's own
`spectrum.fft_interferogram`) this raised an uncaught `DatasetError` from a Qt
slot, crashing the GUI. Fixed with a capability-aware `_view_kind` dispatch in
`_preview_panes`/`_before_panes` (image / hyperspectral-band / spectral-curve /
honest-decline) and a `spectral_panes` field on `OperationPreview`, reusing the
existing spectrum viewer for a curve-shaped preview - no new preview surface.
This was necessary for this milestone's success criterion "process spectral
datasets using the existing processing framework," which the original design
implicitly assumed already worked (it did not, for anything but a plain image).
`spectrum.reference_normalize` (5A's still-open op) and cross-measurement/
Phase-2B comparison for hyperspectral remain explicitly out of scope for 5B.

### 6.3 Phase 5C - Real-Data Readers - blocked on real sample data, `(user)`

- **Objective.** Two new readers (interferogram, hyperspectral), mechanically
  similar to the two existing ones (reusing `io/_neasnom_header.py`'s grammar
  parser), once real vendor exports exist to reverse-engineer the exact table
  format from.
- **Scientific value.** Without this, 5A/5B remain synthetic-only and cannot
  ingest an actual researcher's nano-FTIR/hyperspectral data - this is the
  milestone that makes the rest of Phase 5 real.
- **Complexity.** Low-Medium once real files are available (the header grammar
  and reader-registration pattern are already twice-proven).
- **Architectural impact.** None anticipated - both `DataKind`s already exist;
  likely only additive metadata, following the `SpectralInfo` precedent exactly.
- **Dependencies.** **Hard-blocked.** No interferometric nano-FTIR export and no
  hyperspectral cube export exists anywhere in this repository today (confirmed:
  only 3 imaging + 1 point-spectroscopy directory are present in `SNOM Sample
  Files/`). This is exactly the Rule 6 gate that blocked Phase 1 until a real GSF
  sample arrived and blocked the point-spectroscopy vertical slice until the real
  PSP sample arrived - the same discipline applies here, without exception,
  `(user)` action needed (acquire or export a real interferogram/cube file).

### 6.4 Phase 5D - Spectral Diagnostics & Reasoning - a Scientific Validation Phase candidate

- **Objective.** A resonance/peak-identification **diagnostic** (position,
  width, prominence - reusing `viz.measure.analyze_profile`/`_detect_peaks`
  verbatim, W5) as a new `diagnostics` descriptor. Whether this becomes an
  AI-*recommended* next step (e.g. "a resonance was found near X cm^-1") is a
  **separate, harder question** that must go through the full
  Question -> Literature -> Candidate Diagnostics -> Analytical -> Synthetic ->
  Real-data -> Decision pipeline (`scientific-validation.md`) before any rule is
  written - exactly the discipline `harmonic-ranking-analysis.md` already applied
  once, and which found that a valid *fact* (signal/noise classification) did not
  automatically license a valid *ranking/recommendation*. This milestone should
  enter `next-scientific-priorities.md`'s triage queue, not be implemented
  directly as a product feature.
- **Scientific value.** High if validated - turns a raw spectrum into the actual
  reportable quantity (peak position/width) - but shipping an unvalidated
  recommendation would violate the project's own scientific-honesty discipline.
- **Complexity.** Low for the deterministic *fact* once a real `SPECTRUM` exists
  (the peak-finder is already generic and tested); higher, and separately gated,
  for any *recommendation*.
- **Architectural impact.** None - lands in `diagnostics` as one new descriptor,
  exactly like `HistogramData` before it.
- **Dependencies.** Needs 5A for a real spectrum to analyze in practice, but the
  descriptive fact can be validated analytically/synthetically (known peak
  positions in a synthetic spectrum) before real-data validation, which is gated
  the same way as 5C.

### 6.5 Sequencing

5A and 5B are independent of each other and of 5C - both are buildable and
synthetically validatable **now**. 5C requires real data the project does not yet
have and is the load-bearing blocker for turning either into a real researcher
workflow. 5D's fact half can start once 5A produces real spectra to test against;
its recommendation half is explicitly deferred into the permanent Scientific
Validation queue alongside the project's other open candidates (phase-wrapping,
poor-scan detection). Cross-cutting additions (Knowledge articles, the AI Briefing
sentence, per-band GSF export, CSV export, the experiment-browser summary column)
are small and attach to whichever milestone produces the new data/fact - none is
large enough to warrant its own phase.

---

## 7. Risks, open questions, and the honesty ledger

- **The biggest risk is silently reusing `is_spectral` for hyperspectral data.**
  Section 1 flags this explicitly; the fix (a genuine third dispatch state) is
  cheap and should be treated as non-negotiable before any hyperspectral GUI code
  is written, to avoid repeating the exact gating-bug pattern already found once.
- **FFT correctness is unusually high-stakes for a first attempt.** Apodization
  choice, phase-correction method, and zero-fill factor all change the resulting
  spectrum's lineshape and resolution; Rule 6's synthetic-with-known-answer
  validation is not optional here - recommend an explicit numerical tolerance
  budget be written *before* implementation begins, not discovered after.
- **Real sample data is the load-bearing blocker for 5C**, and by extension for
  ever validating 5A/5D against real data. This should be surfaced to the user
  explicitly (mirroring how `phase-wrapping-analysis.md` and
  `reference-normalization-analysis.md` both flagged real-data gates as honest
  stopping points, not failures).
- **Atmospheric correction (W8) is deliberately left thin** - it needs either a
  validated reference line-list or a demonstrably clean reference spectrum,
  neither of which is available yet; forcing an implementation now would risk
  the same "quality necessary-but-not-sufficient" trap the reference-
  normalization-analysis found for image reference normalization.
- **Open question for the user:** should the interferometric reader (5C) target
  the vendor's native interferogram export format specifically, or a more generic
  "signal vs. OPD" ingestion path that could also accept synthetic/simulated
  interferograms for testing? (Recommendation: build the synthetic-fixture path
  first regardless, since 5A/5B need it anyway; decide the real-reader's exact
  target format once a real file is in hand, per Rule 6.)

---

## 8. Success criterion - the question this document answers

> *Does SNOMNIMAN's imaging-proven architecture actually extend to interferometric
> nano-FTIR and hyperspectral cubes, or does it need to change?*

**It extends.** The `core` data model needs one small capability addition and one
additive metadata field; the provenance DAG, `Recipe`, `snomniman.batch`, and
`gui/report.py` need **no changes at all** and already generalize by construction
- a direct, measurable payoff of Phases 1-4C's own discipline. The genuinely new
work is bounded and honest about what it is: a new numerical domain (FFT/
apodization, validated synthetically first) and one new GUI surface (a linked
band-map/spectrum viewer, presentation-only). What is *not* available - real
interferogram and hyperspectral sample data - is named as a real blocker rather
than worked around, exactly as the project's own precedent requires.

---

## Appendix A - A synthetic interferogram round-trip, made concrete (illustrative, not implementation)

Not code - the shape of the validation a real `spectrum.fft_interferogram`
implementation must pass before touching real data:

```text
known_spectrum = Lorentzian(center=1735 cm^-1, width=12 cm^-1)     # the "truth"
synthetic_interferogram = inverse_fft(known_spectrum) + noise      # the "raw" input
dataset = Dataset(kind=INTERFEROGRAM, data={"O2": synthetic_interferogram}, ...)

processed = FftInterferogram(apodization="blackman_harris_3", zero_fill=2,
                              phase_correction="mertz").apply({"primary": dataset})
# processed.kind == SPECTRUM; processed.channel("O2") is complex, dims (wavenumber,)

recovered_peak = analyze_profile(processed.coordinate("wavenumber"),
                                  abs(processed.channel("O2")))       # reuses viz.measure, unmodified
assert abs(recovered_peak.position - 1735) < documented_tolerance_cm1
```

Everything below the first line already exists and is already tested
(`ProcessingStep.apply`, `Dataset` construction, `viz.measure.analyze_profile`);
only the FFT step and the synthetic-truth generator are new.

## Appendix B - Cross-references

`CLAUDE.md` (Rules 1-9; "nanoscale chemical mapping" in the Overview) -
`docs/data-model.md` sec 2 (`DataKind`/`Capability` table, anticipated since Phase
0) - `docs/point-spectrum-discovery.md` (the first spectral vertical slice; the
precedent this document extends) - `docs/roadmap.md` "Phase 5 - nano-FTIR
spectroscopy" / "Phase 6 - Hyperspectral & batch" (the stale placeholder this
document supersedes) - `docs/scientific-validation.md` (the gate 5D's
recommendation half must clear) - `docs/harmonic-ranking-analysis.md` (the
precedent for "a valid fact is not automatically a valid recommendation") -
`docs/reference-normalization-analysis.md` (the precedent for "quality is
necessary but not sufficient," relevant to W7/W8) - `docs/knowledge-center.md`
(the article pattern new spectral concepts/operations follow) -
`src/snomniman/core/dataset.py` (`_derive_capabilities`) -
`src/snomniman/core/capabilities.py` / `datakind.py` -
`src/snomniman/gui/model.py` (`is_spectral`, `SpectrumCurve`,
`spectrum_curve`/`spectrum_position_count`) - `src/snomniman/gui/spectrumview.py`
(`SpectrumPlotView`) - `src/snomniman/gui/window.py` (the eleven `is_spectral`
branches - the template for `is_hyperspectral` gating) -
`src/snomniman/viz/measure.py` (`analyze_profile`, `rect_mask`/`polygon_mask`/
`region_stats` - the reuse core of 5B/5D) - `src/snomniman/viz/render.py`
(`RenderData`/`prepare_channel` - the reuse core of band maps) -
`src/snomniman/processing/step.py` (`ProcessingStep._execute`'s
`DataKind`-changing contract) - `src/snomniman/diagnostics/diagnose.py`
(`_classify_harmonic`'s `Capability.SPATIAL_2D` gate - the precedent bug/fix
Section 1 generalizes from) - `src/snomniman/knowledge/library.py`
(`concept.point_spectrum`'s own forward reference to interferometric nano-FTIR).
