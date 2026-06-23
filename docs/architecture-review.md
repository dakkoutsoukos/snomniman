# Architecture Review (pre-Phase-1)

**Status:** HISTORICAL SNAPSHOT (2026-06-19). All findings are now resolved and
applied - see `decisions.md` "Decision Closure" (OHD-1..9). This document is
preserved as the original adversarial analysis; references to the package name
`snom` and to "open questions" predate the rename to `snomniman` and the OHD
closure, and are intentionally left unchanged as a record.
**Reviewer role:** senior scientific-software architect (adversarial pass)
**Scope:** vision/architecture/data-model/roadmap/decisions as they stood before any implementation.

This is a problem-finding review. Its success is measured by whether it changes
the design before code is written. Items are rated **Likelihood (L)** and
**Impact (I)** as Low / Med / High, and tagged with a recommended action.
Findings are ID'd (R = architectural, S = scientific, M = model, F = format,
P = roadmap) for cross-reference.

> **Note on the four open questions:** the user's answers are now treated as
> inputs (external raw refs + later bundle; rename away from `snom`; lock and
> carry conventions; one real file per DataKind as Phase-1 validation). They are
> folded in below and, where warranted, themselves critiqued.

---

## TL;DR - changes worth making before Phase 1

In rough priority order. Each is cheap now and expensive after readers/datasets/pipelines exist.

1. **Make the provenance graph multi-input (a DAG), not a single-source linear chain.** Referencing, background subtraction, and spectrum/interferogram averaging are core SNOM/nano-FTIR operations and all take a *second* measurement as input. The current `Pipeline = one RawSource + ordered steps` cannot represent their provenance. Design the schema for named auxiliary inputs now even if Phase 1 only exercises the linear path. (M1 / R1)
2. **Decide how complex data is stored on disk.** Classic netCDF has no complex type; "complex supported" (data-model.md sec 10) is only true for some backends with caveats. Pick an encoding (zarr is complex-native + chunked + JSON attrs; or HDF5-via-h5py; or split real/imag) before writing the I/O layer. (M2 / F1)
3. **Treat unwrapped phase as a first-class real channel.** Phase unwrapping is a core operation and unwrapped phase (which exceeds +/-pi across polariton fringes) is *not* recoverable from the angle of a complex number. Complex-as-canonical is lossy here. (S1 / M3)
4. **Replace DataKind-as-dispatch with capability-based dispatch.** Keep a `kind` hint for UX, but have steps require named axes/channels (e.g. "needs a `wavenumber` dim", "needs a 2D spatial grid"), so new modalities (pump-probe delay, polarization, QCL line stacks, approach-curve maps) don't require core edits. (M4 / R2)
5. **Add an explicit spatial-referencing model (affine).** A rotated scan cannot be represented by 1D x/y coordinate vectors; data-model.md sec 5 assumes it can. Store origin + pixel size + rotation + axis directions, and *lock* the origin/axis convention. (S2 / M5)
6. **Make metadata/calibration edits tracked operations.** A wavenumber recalibration or phase-offset reference changes results; if it is a silent metadata edit, "reproduce from raw + history" is false. (S3 / R3)
7. **Define a step-versioning + determinism policy now.** State whether old step versions stay executable, and soften the "bit-identical" reproducibility claim to "bit-identical for steps declared deterministic on matching lib/platform; otherwise reproducible to a documented tolerance." (R4 / S4)
8. **Adopt copy-on-write semantics for the immutable model, and plan intermediate-result caching.** Full deep copies per step will not scale to hyperspectral cubes, and interactive re-runs need cached pipeline prefixes. This is an architectural stance, not premature optimization. (R5)
9. **Reframe Phase 1 as a vertical slice** (one reader -> one Dataset -> one viewer -> one real file) instead of building core+full-IO breadth first. (P1) Matches the user's strongest suggestion.
10. **Pick the package name** (rename away from `snom`) and **convert docs to ASCII** to stop terminal/editor garbling on Windows. (R6 / docs hygiene)

---

## 1. Architectural Risks

### R1 - Provenance pipeline is single-source and linear (coupling / correctness) - L: High, I: High
**Why it matters.** `Pipeline` is defined as "an ordered list of ProcessingSteps
bound to a RawSource" (architecture.md sec 3; data-model.md sec 9). But the
roadmap itself schedules **self-referencing** (Phase 2), **reference
normalization** and **averaging** (Phase 4) - operations whose inputs include a
*second* dataset (a reference material spectrum, a background image, N repeat
acquisitions). A linear single-source chain cannot record where that second
input came from, so its provenance - and thus reproducibility - is lost exactly
for the operations that dominate real nano-FTIR work.
**Mitigation.** Model provenance as a DAG: a step may declare named auxiliary
inputs, each resolving to a `(RawSource + sub-pipeline)` reference (or a sibling
pipeline within a Project). Keep the single linear chain as the common 90% path,
but bake named auxiliary inputs into the `Pipeline`/`StepRecord` *schema* now.
Retrofitting a serialized schema after project files exist in the wild is the
expensive case. (See M1.)

### R2 - DataKind enum as a dispatch axis (coupling / maintenance) - L: High, I: Med
**Why it matters.** "Processing steps declare which kinds they accept"
(data-model.md sec 2). A closed enum used for dispatch becomes a modification
magnet: every new modality forces edits to the enum and to every `match kind`
site (open/closed violation, drift risk). DataKind also conflates three
orthogonal things: array shape, which physical axes are present, and acquisition
modality.
**Mitigation.** Dispatch on *capabilities* - presence of named dimensions and
their physical type (spatial / spectral / temporal-delay / distance / opd /
polarization) and required channels - not on the enum. Keep `kind` as a UX hint
only. (See M4.)

### R3 - Metadata is mutable input but is outside provenance (correctness) - L: Med, I: High
**Why it matters.** Calibration values (wavenumber axis, phase reference,
tapping amplitude, scan size) live in `Metadata` and materially change results.
If a user corrects a calibration via a metadata edit that is not a tracked step,
the dataset's result is no longer reproducible from "raw + history."
**Mitigation.** Separate *as-imported* metadata (immutable) from corrections, and
represent corrections as tracked processing steps (e.g. `meta.recalibrate`).
The reproducibility guarantee must explicitly cover metadata-affecting edits.

### R4 - "Reproduce in 3 years" overclaims bit-identical results (correctness / testing) - L: Med, I: Med
**Why it matters.** architecture.md sec 5 and data-model.md sec 11 promise
"identical results (hash-verified)." FFT, interpolation, threaded BLAS, and
floating-point reduction order are not guaranteed bit-identical across
library/CPU/platform versions. Environment capture (ADR-0013) aids debugging but
does not guarantee bit reproducibility. An over-promised invariant will fail in
CI on another machine and erode trust in the provenance system.
**Mitigation.** Each step declares `deterministic: bool`. Scope the hash-match
invariant to deterministic steps on matching lib/platform; otherwise assert
"reproducible to a documented numerical tolerance." Define a step-versioning
policy: either old step versions remain executable (immutable semantics; v2 for
new behavior) or reproduction is pinned to the recorded `snom`/env version. Pick
one before steps proliferate.

### R5 - Per-step full-copy immutability will not scale (performance / scaling) - L: Med, I: High
**Why it matters.** Every step returns a new full `Dataset` (ADR-0004). A
hyperspectral cube (e.g. 256 x 256 x 512 complex128 ~ 537 MB) through a 10-step
chain, with replay re-running from raw on every interactive parameter tweak,
multiplies memory and latency. "Optimize later" (Rule 1/7) is fine for kernels,
but the *immutability semantics* are an architectural choice made now.
**Mitigation.** Define logical immutability via **copy-on-write**: steps never
mutate, but unchanged channels are shared by reference, not deep-copied. Plan an
intermediate-result cache keyed by pipeline-prefix hash so editing step 8 reuses
steps 1-7. Leave a lazy/dask backend possible (xarray supports it) without
committing to it. None of this is kernel optimization; it is the contract steps
are written against.

### R6 - Two leak risks: xarray in the public API, and `snom.io` naming - L: Med, I: Med
**Why it matters.** (a) data-model.md exposes `dataset.data: xarray.Dataset`
directly. If raw xarray objects flow through the codebase and public API, xarray
becomes part of the contract and its (fast-moving) API breakage ripples
everywhere - undermining ADR-0001's "thin wrapper." (b) `snom.io` shadows stdlib
`io` (low risk under Python 3 absolute imports, but a papercut).
**Mitigation.** Keep `Dataset` a genuine boundary: expose typed accessors;
treat direct xarray access as an "escape hatch," not the main API. Consider
`snom.readers`/`snom.formats` instead of `snom.io`.

### R7 - The viz "backend-neutral render model" risks a leaky over-abstraction - L: Med, I: Med
**Why it matters.** architecture.md sec 3 has `viz` produce backend-neutral
render models feeding *both* matplotlib (static) and PyQtGraph (interactive).
These libraries differ deeply (LUTs, colorbars, interactivity, complex display).
A unified abstraction tends to a lowest-common-denominator layer that fights both
- itself a premature generalization (Rule 7).
**Mitigation.** Scope `viz` to *display-ready data* only: array + physical extent
+ recommended colormap/limits + units + scale-bar spec (pure data). Let each
frontend render directly. Do not build a scene-graph/render abstraction now.

### R8 - "No scientific logic in GUI" is enforced only by discipline - L: Med, I: Med
**Why it matters.** The import guard catches Qt leaking *into* the backend, not
logic leaking *into* the GUI. The latter is the more likely drift and is not
automatable.
**Mitigation.** Keep the guard, but add: (a) a thin "view-model"/controller
convention so widgets call backend commands only; (b) `pytest-qt` for GUI tests
later; (c) code-review checklist item. Accept this is a discipline control, and
say so.

---

## 2. Scientific Risks

### S1 - Complex-as-canonical loses unwrapped phase - L: High, I: High
"Amplitude and phase are one complex quantity ... amplitude/phase are views"
(data-model.md sec 1, 4). True for *wrapped* phase. But phase unwrapping is a
core SNOM step (architecture.md sec 3 lists it), and unwrapped phase routinely
exceeds +/-pi (polariton fringes, thick-sample dispersion). `angle(z)` only ever
returns the principal value, so storing complex and deriving phase **discards the
unwrap**. *Mitigation:* support a real, possibly-unwrapped phase channel as
first-class (with an `unwrapped: bool`/branch metadata); complex stays the
default only for raw demodulated optical channels. (See M3.)

### S2 - Coordinate conventions are under-specified and assume axis-aligned grids - L: High, I: High
data-model.md sec 5 says scan rotation is "reflected in the physical x/y
coordinates" - but a rotated scan grid cannot be expressed by 1D x and y
coordinate vectors; you need 2D coordinate arrays or an explicit affine. Origin
(top-left vs bottom-left), axis directions (y up vs down), fast/slow axis, and
trace/retrace are all left implicit. These silently transpose/flip images,
leveling, and exports. *Mitigation:* an explicit spatial-referencing model
(origin, pixel size, rotation, axis directions = a pixel->physical affine),
**locked** to one convention and carried with every dataset. (See M5.)

### S3 - Reproducibility depends on metadata that is editable off-the-record
See R3. Scientifically: a recalibrated wavenumber axis or a re-chosen phase
reference changes the published numbers. If not tracked, the provenance lies.

### S4 - "Deterministic" is asserted but never defined
See R4. Which steps are bit-deterministic? FFT/interp/fitting generally are not
across environments. Random-seeded steps (denoising, ICA, fit init) must capture
seeds in `params`. Without a determinism contract, the hash invariant is a
landmine.

### S5 - Units strategy: risk is *implicit* units, not the absence of pint - L: Med, I: Med
Deferring pint (ADR-0008) is reasonable. The real hazard is silent unit
mismatches at boundaries, plus the **nonlinear** wavenumber<->wavelength
conversion (reciprocal, not scalar) and rad/deg, cm^-1/um/THz. *Mitigation:* a
single units chokepoint; readers convert to canonical on import, exporters at the
edge; a validation pass asserting every array carries units; tested converters
incl. the reciprocal cases; keep the pint door open behind the chokepoint.

### S6 - Amplitude semantics and normalization state are ambiguous - L: Med, I: Med
data-model.md calls amplitude "a.u." but also "dimensionless ratio once
referenced" - those are different states with the same label. Whether a channel
is raw, self-referenced, or normalized-to-material must be explicit state on the
channel (and, per R1, point at the reference's provenance). Otherwise two
"O2A" maps that mean different things look identical.

### S7 - Harmonic order and detection assumptions - L: Low, I: Med
The model assumes amplitude+phase pairs (pseudoheterodyne). Homodyne / self-homodyne
and amplitude-only or real-valued detection exist; `O0` is often an intensity
channel where phase is meaningless. Ensure the channel model permits
amplitude-only and real channels per harmonic (it partly does - keep it explicit).

---

## 3. Data Model Stress Test

Can the current model naturally represent each modality? ("Awkward" = expressible
but with a convention gap or a fight.)

| Modality | Verdict | Notes / awkward fit |
|---|---|---|
| Topography map (Z) | **OK** | Real 2D variable; needs the affine/origin lock (S2). |
| Multi-channel s-SNOM map | **OK with caveat** | Per-channel complex variables fit well; normalization state (S6) and unwrapped-phase channel (S1) needed. |
| Hyperspectral cube | **Awkward** | Shape fits `(y,x,wavenumber)` complex; but memory model (R5) and complex persistence (M2) bite here first. |
| nano-FTIR point spectrum | **Awkward** | The spectrum itself fits; its **referencing to a material spectrum** has no provenance home (R1/M1). Also interferogram->spectrum is a multi-stage transform whose intermediate (the interferogram) should remain reproducible. |
| Approach curve | **OK** | `(z,)` fits; ensure z-axis sign/origin (tip approach vs retract) is explicit. |
| **Future: pump-probe / THz-TDS** | **Gap** | Adds a `delay`/`time` axis; no concept today. Capability dispatch (M4) makes this additive instead of a core change. |
| **Future: polarization-resolved** | **Gap** | Adds a polarization axis or channel family; same fix. |
| **Future: QCL spectral imaging (discrete lines)** | **Ambiguous** | A stack of images at N wavenumbers is hyperspectral-shaped but not FTIR-derived; DataKind conflates shape with modality (R2). |
| **Future: approach-curve map / 3D tip tomography** | **Gap** | `(y,x,z)` and beyond; capability dispatch handles it; enum does not. |

**Conclusion:** the array model (xarray, per-channel complex vars) is sound and
flexible. The *descriptors* on top of it (DataKind enum; "rotation in 1D coords";
complex-only phase) are where the awkwardness lives. Fixing M3/M4/M5 makes the
known and several unknown modalities additive rather than breaking.

### Model-level recommendations
- **M1 - Multi-input provenance schema** (see R1): named auxiliary inputs in `Pipeline`/`StepRecord`.
- **M2 - Complex persistence** (see F1): pick zarr / h5py-complex / split real-imag; stop claiming netCDF "complex supported."
- **M3 - First-class real/unwrapped phase channel** alongside complex optical channels.
- **M4 - Capability/axis-type descriptors** for dispatch; demote DataKind to a hint.
- **M5 - Explicit spatial-referencing (affine) + locked origin/axis convention.**
- **M6 - Metadata schema versioning + corrections-as-steps** (see R3); add `schema_version` to persisted datasets, not just pipelines.
- **M7 - Explicit channel state** (raw / referenced / normalized) and units state (S6).

---

## 4. File Format Strategy Review

### F1 - Persistence format vs complex + large cubes + rich metadata - **change before Phase 1**
data-model.md sec 10 says datasets persist as "HDF5 / netCDF via xarray ...
complex supported." Reality: classic netCDF has **no** complex type; xarray
complex round-trips only via `h5netcdf` with `invalid_netcdf=True` (an HDF5
compound type that is not valid netCDF), or by splitting real/imag. Meanwhile our
own derived store wants: complex-native, chunking for big cubes, and nested-dict
metadata. **Recommendation:** evaluate **zarr** as the primary derived-data store
(complex-native via numpy dtype, chunked, JSON attrs that hold nested metadata
without stringification); keep **h5py** for *reading* vendor HDF5. Decide before
writing `writers/`. At minimum, correct the doc and choose an explicit complex
encoding.

### F2 - Reader registry: extension-based sniffing is insufficient - L: Med, I: Med
`.gsf` is a generic Gwyddion format used by many tools; neaspec `.txt` exports
are header-tagged; HDF5 exports vary by neaSCAN software version across years.
Extension sniffing will misroute. **Recommendation:** content-based sniffing
(magic/header inspection) plus explicit reader id override (already in
`RawSource.reader` - good). Make the reader id carry *format + version*
(`neaspec.gsf.v2`) so one reader does not silently accrete version branches; keep
unknown header fields verbatim (already planned - good). The registry itself
(ADR-0006, not a plugin system) is the right call.

### F3 - External raw refs (confirmed) need a relink story - L: Med, I: Med
The chosen model (reference by path + sha256; bundle later) is correct and
lightweight. The gap: raw files get **moved/renamed**, breaking path refs while
the hash still identifies them. **Recommendation:** store a *relative* path
(to the project root) plus the hash plus enough identity (filename, size) to
support a "relink" UX; define the **manifest** contents now (list of sources with
path+hash+bytes+reader). The later self-contained **export bundle** (raw copied
in + manifest + derived results) is a good Phase-5/6 deliverable; nothing about
it needs to change Phase 1, provided the manifest exists from the start.

### F4 - Project file should reference a content-addressed cache - L: Low, I: Med
With references + replay, derived datasets are recomputable, so caching them is an
optimization, not a source of truth. Keep the source of truth = raw + pipeline
JSON; treat any persisted `Dataset` as a cache keyed by pipeline hash (ties to
R5). This keeps projects small and avoids stale-cache bugs.

---

## 5. Roadmap Review

### P1 - Reorder to a vertical slice first (ordering) - **recommended**
Current order builds `core` + full `io` + round-trip (Phase 1), then pipeline
(Phase 2), then the first real viewer (Phase 3). That defers contact with a real
rendered file to Phase 3 - the opposite of the user's (correct) advice. The data
model is most cheaply validated by pushing one real file all the way to a screen.
**Recommendation:** redefine **Phase 1 = thin vertical slice**: one neaspec
reader (one DataKind) -> `Dataset` -> one minimal interactive viewer -> on one
real file, with round-trip and immutability tests. Defer breadth (more readers,
more steps) to later phases. This front-loads the highest-information validation.

### P2 - Hidden dependency: the DAG/reference decision precedes Phase 2 - **fix**
"Self-referencing" (Phase 2) and "reference normalization / averaging" (Phase 4)
depend on the multi-input provenance schema (M1/R1). That schema must be settled
during Phase 1 (when `Pipeline`/`StepRecord` types are first written), not when
those steps are implemented. Add an explicit Phase-1 milestone: "provenance
schema supports named auxiliary inputs."

### P3 - Missing milestones
- **Persistence/serialization design** (complex encoding, metadata JSON-in-store, schema versioning) - currently bundled invisibly into Phase 1 I/O. Make it explicit (F1/M2/M6).
- **Spatial-referencing/affine** milestone (M5) - needed before any image leveling/rotate is correct.
- **Determinism + step-versioning policy** (R4/S4) - before steps multiply.
- **Metadata-as-provenance** (R3) - before calibration-sensitive steps (FFT, normalization).
- **CI** (lint+type+test+dependency/Qt guard) - Phase 0 mentions a skeleton; make it a gate.
- **End-user packaging/distribution** (PyInstaller/briefcase/conda) - it is a desktop app; absent from the roadmap. Fine to defer, but name it (Phase 6/7).

### P4 - Premature / under-justified items
- The viz "backend-neutral render model" (R7) is the main premature-generalization
  risk in the plan; scope it down.
- "Atmospheric (H2O/CO2) correction" (Phase 4) has a hidden data dependency (line
  lists / a clean reference); flag it rather than assume it is a pure step.
- Hyperspectral + batch (Phase 5) will surface the memory model (R5); make the
  copy-on-write decision in Phase 1-2 even though optimization is later.

### P5 - Sample-data collection is on the critical path (confirmed)
The user's minimum set (image map, hyperspectral, approach curve, plus one
"awkward" edge-case file) is right and should gate Phase 1, not float as
nice-to-have. Add a "point spectrum + its reference measurement" pair explicitly,
because that pair is what exercises M1/R1.

---

## 6. Decisions Audit (ADR-by-ADR)

| ADR | Verdict | Reasoning |
|---|---|---|
| 0001 xarray core | **Keep** | Right foundation. Add boundary discipline (R6): do not leak raw xarray through the public API. |
| 0002 complex channels | **Modify** | Keep complex as default for raw demodulated optical channels, but add first-class real/unwrapped phase + amplitude-only channels, and document the conversion convention + unwrapped-phase loss (S1/M3/S6/S7). |
| 0003 per-channel variables | **Keep** | Correctly handles heterogeneous dtypes; aligns with capability dispatch. |
| 0004 raw immutability | **Modify** | Keep the guarantee; refine to copy-on-write + intermediate caching (R5). |
| 0005 serializable steps + replay | **Modify** | Strongest idea in the design - but extend from single-source linear chain to a DAG with named auxiliary inputs, and add a step-versioning/determinism policy (R1/R4/M1). |
| 0006 reader registry | **Keep** | Correct (not a plugin system). Add content sniffing + format/version in the reader id (F2). |
| 0007 PySide6+PyQtGraph; mpl export | **Keep** | Good split. But scope `viz` to display-ready data; avoid a unified render abstraction (R7); add pytest-qt later. |
| 0008 lightweight units, defer pint | **Keep** | Deferral is fine; add a units chokepoint + validation + tested reciprocal/phase converters; keep pint adoption path open (S5). |
| 0009 persistence + reference raw | **Modify** | Confirm external refs + later bundle (user). But resolve complex persistence (zarr/h5py/split), add manifest + relink + dataset schema_version, and stop claiming netCDF complex support (F1/F3/F4/M2/M6). |
| 0010 naming `snom` | **Reconsider (change)** | User: avoid `snom`. Candidates: `snomkit` / `snomlab` / `nanosnom`. Verify PyPI/import availability before locking. This blocks the package rename - **Critical**. |
| 0011 py>=3.11, uv/ruff/mypy/pytest | **Keep** | Sound. (Consider 3.12 floor only if a dependency benefits; 3.11 is fine.) |
| 0012 neaspec first, validate | **Keep** | Strongly aligns with the vertical-slice reorder (P1). |
| 0013 environment capture | **Keep** | Useful - but clarify it aids reproducibility/debugging and does not guarantee bit-identical cross-platform results (R4). |

No ADR is *wrong*; the cluster 0002/0004/0005/0009 needs the refinements above
before they are implemented, because they define types and on-disk formats that
are costly to change once data exists.

---

## 7. Questions That Must Be Answered Before Coding

Only questions whose answers change architecture or scientific correctness.

### Critical (block Phase 1 design)
1. **Provenance topology:** do we commit now to a DAG with named auxiliary inputs
   (references, backgrounds, averaging)? (Recommended: yes - it is foundational and
   costly to retrofit.) (R1/M1)
2. **Complex on-disk encoding:** zarr (recommended), HDF5-via-h5py complex, or
   split real/imag? Decides the writer and the persistence invariant. (F1/M2)
3. **Phase representation:** is unwrapped phase a first-class real channel? (Affects
   `Dataset`, channel model, and every phase step.) (S1/M3)
4. **Spatial referencing:** do we support rotated/affine scan geometry from the
   start, and what is the *locked* origin + axis-direction convention? (S2/M5)
5. **Reproducibility contract:** keep old step versions executable, or pin to the
   recorded environment? And what is the determinism guarantee (bit-identical vs
   tolerance)? (R4/S4)
6. **Metadata-as-provenance:** are calibration/metadata corrections tracked steps?
   (Determines whether "reproduce from raw + history" is actually true.) (R3)
7. **Package name** (rename from `snom`); confirm before any imports are written. (0010)

### Important (shape Phase 1-2, not blocking the first commit)
8. Concrete convention *values* (from the instrument/lab): phase reference & sign,
   amplitude units/state, canonical z unit, image origin - the user has agreed to
   lock these; we need the actual values.
9. Which neaspec format/version is the first reader target, and the matching real
   sample file(s) - including a **point spectrum + its reference** pair (P5).
10. Intermediate-result caching strategy for interactive replay (R5).
11. How much of xarray is part of the public API vs an escape hatch (R6).
12. Complex display convention in viewers (amp+phase pair vs amp with phase as hue).

### Can wait (record, decide later)
13. Self-contained export bundle format details (Phase 5/6).
14. Lazy/dask backend for large cubes.
15. End-user packaging/installer strategy.
16. pint adoption.
17. Additional vendor readers / any plugin mechanism.

---

## What is genuinely sound (do not churn these)

So the review is balanced, not destructive: the **load-bearing decisions are
correct** - xarray-backed labeled arrays; complex representation as the *default*
for demodulated optical channels; reproducibility as a serializable, replayable
pipeline; a reader registry rather than a plugin system; a strictly layered,
acyclic, GUI-free backend with the separation encoded as an executable invariant.
Keep all of these. The findings above are refinements to *descriptors and
schemas* (DataKind, phase, coordinates, persistence, provenance topology) and to
*sequencing* (vertical slice first) - precisely the things that are cheap to fix
now and 10x more expensive after readers, datasets, and pipelines exist.

If only three changes are made before Phase 1, make them **M1 (multi-input
provenance), M3 (unwrapped-phase channel), and M2/F1 (complex persistence)** -
these are the ones that would otherwise force a schema/format migration later.

### Minor: documentation hygiene
The existing docs used Unicode box-drawing, arrows, the micro sign, subscripts,
and cm^-1 glyphs that garble in some Windows terminals/editors (the likely source
of the "garbled phrases" observed). Resolved in the 2026-06-19 hardening pass: the
docs were converted to ASCII-safe text (UTF-8).
