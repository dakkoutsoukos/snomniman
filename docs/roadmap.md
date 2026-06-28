# Roadmap

**Status:** **Foundational development COMPLETE.** Phase 1 done; the Measurement
Explorer (read-only + processing), the Description API, the Diagnostics Engine, the AI
Scientist (Briefing + Reasoning Rule Engine), and the Knowledge Center are all shipped
(373 tests green). The bottleneck is no longer architecture - it is choosing which
workflow gaps and scientific capabilities to close next.
**Last updated:** 2026-06-28

The original phased plan (Phases 0-8, below) remains the **long-arc structural map**
and its exit criteria still stand. But near-term sequencing is now set by the two
governance documents, not by the phase list:

- **[`beta-readiness-v1.md`](beta-readiness-v1.md)** - the authoritative **Product
  Roadmap**: which validated *workflow gaps* block a researcher's full day.
- **[`scientific-validation.md`](scientific-validation.md)** - the **Scientific
  Validation Phase**: how a *scientific capability* is proposed, validated, and only
  then implemented.

---

## Current driver: Beta Readiness + Scientific Validation

With the foundation complete, work is driven by validated workflow blockers and
scientific evidence - **not** by speculative feature ideas or speculative
infrastructure. The permanent priority loop:

1. **Close beta-blocking workflow gaps** identified by
   [`beta-readiness-v1.md`](beta-readiness-v1.md) (the product priority).
2. **Validate** any new scientific capability through the Scientific Validation
   process ([`scientific-validation.md`](scientific-validation.md)) - the scientific
   gate. **Honest deferral is a successful outcome.**
3. **Implement only validated capabilities** - and extend an existing abstraction, not
   a new subsystem (Rule 7).
4. **Gather researcher feedback** (the Beta Readiness user-testing protocol).
5. **Repeat** - re-run the review (`beta-readiness-v2`, ...) and watch the switch-back
   points disappear.

**The current product priority** (Beta Readiness Section 3, Critical - the open-beta
gate; each reuses an abstraction that already exists):

1. **Export the processed dataset** - wire `io.write_zarr` / `write_gsf` into the GUI
   (C1/G1). Also closes most of the Phase 4 reproducibility gap.
2. **Export measurement numbers** - profile samples + region statistics to CSV +
   clipboard (C2/G2).
3. **`image.line_flatten`** - the one missing table-stakes operation; a registered
   `ProcessingStep` that the generic Workspace surfaces with no GUI code (C4/G4).
4. **Open more than one measurement** - a File menu / Open / Recent so a multi-scan
   session is possible (C3/G3).

Then the reproducibility close-out (project save/reopen by serializing the provenance
DAG -> meets the Phase 4 exit criterion) and the daily-ergonomics polish (H1-H5). See
[`beta-readiness-v1.md`](beta-readiness-v1.md) Section 7 for the full ordered backlog.

### The Scientific Validation Phase (formerly the "Scientific Knowledge Phase")

Scientific capabilities enter through [`scientific-validation.md`](scientific-validation.md),
**not** the phase list. The phase was renamed from "Scientific Knowledge" to
**Scientific Validation** because the discipline that governs what enters the engine is
*validation*, not *accumulation*: a judgment ships because analytical, synthetic, and
real-data evidence justify it (Rule 6; the maxim - *"two things we can defend over four
we can't"*), and **declining to ship is a legitimate, valuable outcome**. ("Knowledge"
also collided with the shipped Knowledge Center, `snomniman.knowledge` - a different,
teaching subsystem.) The first milestone, phase-wrapping
([`phase-wrapping-analysis.md`](phase-wrapping-analysis.md)), is the worked exemplar:
defensible criterion, rule deferred for want of real wrapping data. The seeded
**Future Validation Queue** (harmonic ranking, phase-wrapping recommendation, reference-
normalization criteria, poor-scan / drift / tip-artifact detection) lives in
`scientific-validation.md`.

---

## How we work (per significant feature)

1. **Design** - explain the proposed approach.
2. **Implications** - what architecture/abstractions it touches.
3. **Risks** - scientific (units/conventions), structural (drift), reproducibility.
4. **Implement** - fit it into the existing architecture; refactor as needed.
5. **Test** - unit + invariant + (where scientific) synthetic/golden/reference validation.
6. **Document** - update `/docs` when architecture or data model changes; record
   decisions in `decisions.md`; append to `LOG.md`; refresh `NEXT.md`.

**Definition of done:** code + tests green, `ruff` clean, `mypy` clean, docs
updated if architecture changed, and (for scientific code) a validation test with
a known answer.

---

## Phase 0 - Foundation  [COMPLETE]

**Goal:** a coherent, documented, internally consistent foundation; all
design-blocking decisions resolved.

- [x] `vision`, `architecture`, `data-model`, `roadmap`, `decisions` docs
- [x] Package scaffold renamed to `src/snomniman/{core,io,processing,pipeline,viz,batch,gui}`
- [x] `pyproject.toml` (uv), `ruff`, `mypy`, `pytest` config; `.gitignore`; README
- [x] Adversarial architecture review (`architecture-review.md`)
- [x] Orientation files (`CLAUDE.md`, `LOG.md`, `NEXT.md`)
- [x] Documentation hardening (consistency, ASCII, explicit ADR statuses)
- [x] **All Outstanding Human Decisions (OHD-1..9) resolved and applied**
- [x] Package named/renamed to **SNOMNIMAN / `snomniman`** (OHD-1)

**Phase 1 entry checklist (mechanical infra + inputs, no decisions left):**
- [x] Install `uv`; `uv sync`; `uv run pytest`/`ruff`/`mypy` green; add CI gate *(done 2026-06-22/23)*
- [x] `git init` + initial commit *(done 2026-06-22)*
- [x] Obtain a real **neaSNOM imaging** sample file *(done 2026-06-23 - GSF measurement directory present)*

## Phase 1 - Vertical slice: neaSNOM imaging reader (backend only)  [COMPLETE; ADR-0015]

**Goal:** push one real neaSNOM imaging file all the way into the data model and
lock the core schemas against reality. **No GUI; no advanced processing; no
visualization** beyond what validates the slice.

**First implementation milestone (in this order):**
1. **Dataset model** - `snomniman.core.Dataset` (+ `DataKind`/capabilities), the
   minimum to hold an imaging dataset with canonical units (nm) and the
   lower-left/x-right/y-up convention.
2. **Metadata schema** - typed `Metadata` storing conventions explicitly (OHD-6),
   plus the verbatim vendor header.
3. **Provenance schema** - `StepRecord` + the provenance **DAG** node (OHD-2/OHD-5),
   even though the slice uses a single `io.read` node.
4. **GSF measurement-directory reader** - `snomniman.io` reader (OHD-9) that ingests
   a neaSNOM measurement directory (one `.gsf` file per channel + `.txt` parameters),
   assembles all channels into a `Dataset` with correct dims, coords, canonical units,
   and metadata; unknown header fields preserved verbatim.
5. **Golden-file tests** - real directory -> expected `Dataset`; Zarr round-trip and
   raw-immutability invariants; backend stays Qt-free.

**Gated on:** ~~a real neaSNOM imaging sample file~~ **Gate lifted** - real GSF
measurement data is present. See `docs/measurement-discovery.md`.
**Exit (Rule 6):** the neaSNOM measurement directory loads into a validated `Dataset`,
verified by golden-file tests against known values / neaPLOT; Zarr round-trip and
immutability pass.

## Phase 2 - Core data model & I/O (breadth)  [PARTIAL]

> *Status:* complex + unwrapped-phase accessors, capabilities, and the canonical Zarr
> round-trip are shipped. Readers for further modalities (point spectra, approach
> curves, hyperspectral) and the synthetic generators remain (Phase 5/6 brings the
> spectral modalities; see the Future Validation Queue for which judgments they unlock).

- Full `snomniman.core`: complex + unwrapped-phase accessors, channel state, the
  hybrid dispatch capabilities, typed exceptions.
- `snomniman.io`: registry hardened; readers for more modalities (point spectra,
  approach curves, hyperspectral); canonical **Zarr** persistence with round-trips.
- Synthetic dataset generators (image, spectrum, interferogram).

**Exit:** the supported DataKinds load and round-trip; generators back the suite.

## Phase 3 - Processing & provenance DAG  [PARTIAL]

> *Status:* the `ProcessingStep` ABC + registry, the non-mutating contract, the
> provenance DAG, replay, and serialization are shipped, with four image operations
> (`image.plane_level`, `image.reference_normalize`, `image.phase_unwrap`,
> `image.crop`). Remaining image steps (line-by-line correction -> `image.line_flatten`
> is the next, a Beta Readiness blocker; rotate; background subtraction) and all
> spectrum steps are pending.

- `snomniman.processing`: `ProcessingStep` ABC + registry; non-mutating contract;
  multi-input steps; determinism/operation-versioning (OHD-5).
- Image steps: crop, rotate, leveling, line correction, explicit phase
  offset/unwrap (-> first-class unwrapped-phase channel), normalization,
  self-referencing.
- `snomniman.pipeline`: provenance DAG, replay, JSON (de)serialization,
  environment/operation-version capture, `Project`.

**Exit:** load -> build DAG (incl. a sample/reference normalization) -> save ->
reload -> replay reproduces the recorded result (bit-identical for deterministic
steps); leveling removes a synthetic plane to tolerance.

## Phase 4 - Interactive GUI (imaging): the Measurement Explorer  [IN PROGRESS]

> *Status:* the Explorer is shipped well past read-only - browse/compare, measure,
> diagnostics, AI Briefing + Suggested Next Steps, the generic Processing Workspace,
> and provenance-bearing figure export. **The exit criterion below is not yet met:**
> the GUI cannot persist or reopen a project/dataset. Closing that is the top Beta
> Readiness priority (C1 export data, H1 project save/reopen).

The central GUI experience is the **Measurement Explorer** - the surface where a
researcher opens, navigates, and *understands* a measurement. Its interaction
design is specified in [`measurement-explorer.md`](measurement-explorer.md)
(read it before any GUI code). Build the **read-only Explorer first** (open ->
browse channels -> inspect metadata/provenance), then add processing/AI/export as
further derivations.

- `snomniman.gui`: PySide6 shell; PyQtGraph image viewer (the first viewer);
  channel selector; LUT/scale; ROI; **provenance panel**; project save/open.
- All actions route through the backend (no scientific logic in the GUI).

**Exit:** an interactive imaging session is saved and exactly reproduced from the
project + raw files.

## Phase 5 - nano-FTIR spectroscopy  [NOT STARTED]

- `snomniman.processing.spectrum`: apodization, zero-fill, phase correction, FFT;
  reference normalization; baseline; atmospheric (H2O/CO2) correction (needs a
  reference line-list / clean reference - confirm availability); averaging.
- Spectral viewer in the GUI.

**Exit (Rule 6):** FFT pipeline validated against synthetic interferograms with
known spectra AND cross-checked against neaPLOT.

## Phase 6 - Hyperspectral & batch  [NOT STARTED]

> *Status:* `snomniman.batch` is an empty stub; hyperspectral readers are not built.

- Hyperspectral cubes: spectral/spatial slicing, per-pixel spectra, band maps;
  viewer support. (Memory: copy-on-write + caching.)
- `snomniman.batch`: apply a DAG across a folder headlessly; per-result provenance
  + a run manifest.

**Exit:** a DAG defined interactively runs unchanged over a folder, emitting
reproducible outputs + manifest.

## Phase 7 - Publication export & polish  [PARTIAL]

> *Status:* provenance-bearing vector figure export (PDF/SVG/PNG, scale bars, cyclic
> phase colormaps, a regeneratable sidecar) is shipped. Data export (CSV/Zarr/HDF5 from
> the GUI - a Beta Readiness blocker, C1/C2) and any performance optimization (Rule 1)
> are pending.

- `snomniman.viz`: vector figure export (PDF/SVG), physical sizing, scale bars,
  cyclic colormaps for phase; data export (CSV/Zarr/HDF5); human-readable
  provenance report.
- Performance profiling and targeted optimization **only now** (Rule 1).

**Exit:** publication-quality figure + data + provenance report from a project.

## Phase 8+ - Extensibility (only when justified)  [DEFERRED by design]

Deferred until a concrete need exists (Rule 7): scripting API, additional vendor
readers, optional plugin/entry-point discovery, end-user packaging/installers.
Each will get an ADR before implementation.

---

## Cross-cutting risks & dependencies

- **The current risk is data coverage, not infrastructure.** Foundational
  development is complete. The live constraint is that some scientific judgments
  cannot be validated on the data in hand (e.g. no genuinely-wrapping measurement to
  validate the phase-unwrap recommendation's positive branch). Such capabilities are
  **deferred**, not guessed (the maxim); see [`scientific-validation.md`](scientific-validation.md).
- **Vendor format details are not assumed** (Rule 6); parsing is validated, and
  unknown fields are preserved verbatim. The neaSNOM format is GSF
  measurement directories (see `docs/measurement-discovery.md`).
- **Scientific conventions are settled** (OHD-6) and stored in metadata; readers
  convert to canonical (nm, lower-left origin) and record conversions in provenance.
- Documentation is ASCII/UTF-8 and internally consistent; the package is
  `snomniman` throughout.
