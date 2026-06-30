# LOG.md - Engineering Journal

Permanent, **append-only** project history. This is not a scratchpad.

**Conventions:**
- One section per session, headed `## YYYY-MM-DD` (add a short tag if multiple
  sessions share a date). **Newest entries go at the bottom** (chronological;
  append, do not rewrite past entries).
- Each entry uses the fixed sub-headings: Completed, Decisions, Issues Found,
  Documentation Updated, Next Recommended Actions.
- Keep entries factual and concise. Current priorities live in `NEXT.md`, not here.

---

## 2026-06-19 - Project inception (architecture, review, orientation)

This initial entry covers everything from an empty directory through the
foundational design, the adversarial review, and the orientation files.

### Completed
- **Project scaffold** at the repo root: `src/`-layout package (import name
  currently `snom`) with empty, docstring-only subpackages: `core`, `io`,
  `processing`, `pipeline`, `viz`, `batch`, `gui`. No application code.
- **Tooling/config:** `pyproject.toml` (Python >= 3.11; `uv`; `ruff`; `mypy`
  strict; `pytest`; GUI deps as an optional `gui` extra; dev tools in a
  dependency group), `.gitignore`, `README.md`.
- **Five foundational design docs:** `docs/vision.md`, `docs/architecture.md`,
  `docs/data-model.md`, `docs/roadmap.md`, `docs/decisions.md`
  (ADR-0001 through ADR-0013).
- **Testing strategy established** and a first suite: `tests/conftest.py`,
  `tests/test_smoke.py`. Includes the **backend/GUI-separation invariant**
  (`test_backend_is_qt_free`, encoding Rule 4 as an executable test), plus
  version and backend-import smoke tests. Verified imports and the Qt-free guard
  pass under the system Python 3.13.7 (`uv`/`pytest` not yet installed, so the
  full suite has not been run under the managed env).
- **Adversarial architecture review:** `docs/architecture-review.md` - a
  pre-Phase-1 problem-finding pass (architectural, scientific, data-model stress
  test, file-format strategy, roadmap, ADR audit, prioritized questions).
- **Orientation files:** `CLAUDE.md`, `LOG.md` (this file), `NEXT.md`.

### Decisions
- **User answers to the four open questions:**
  1. Project model = **external raw files referenced by path + SHA256** + a
     manifest + derived results; add a self-contained export bundle later.
  2. **Rename away from `snom`** (collision risk); candidates `snomkit` /
     `snomlab` / `nanosnom` - final name not yet chosen.
  3. **Lock and carry scientific conventions** (phase in radians with a defined
     reference; amplitude in a.u. unless calibrated; explicit canonical z unit;
     explicit image origin/axis direction; fixed complex conversion convention).
  4. **One real file per DataKind** is required Phase-1 validation material.
- **ADR-0001..0013** recorded in `decisions.md`. The review's ADR audit marks
  Keep/Modify/Reconsider (notably: Modify 0002/0004/0005/0009; Reconsider 0010
  naming).
- **Roadmap reorder accepted in principle:** Phase 1 becomes a thin **vertical
  slice** (one reader -> Dataset -> one viewer -> one real file) rather than
  building core + full I/O breadth first.

### Issues Found
From the architecture review (IDs reference `docs/architecture-review.md`):
- **M1/R1** Provenance is single-source and linear; cannot represent
  referencing, background subtraction, or averaging (all multi-input). Needs a
  DAG schema with named auxiliary inputs - decide before Phase 1.
- **M2/F1** Complex data is not storable in classic netCDF; `data-model.md`
  sec 10 ("complex supported") is incorrect. Choose zarr / HDF5-via-h5py /
  split-real-imag before writing writers.
- **M3/S1** Complex-as-canonical loses unwrapped phase; needs a first-class real
  phase channel.
- **M4/R2** `DataKind` enum used for dispatch is brittle; move to capability/
  axis-based dispatch.
- **M5/S2** Rotated scans cannot be expressed by 1-D x/y coordinates; need an
  explicit affine spatial-referencing model + a locked origin/axis convention.
- **R3** Metadata/calibration edits are currently off-provenance; must be tracked
  to keep "reproduce from raw + history" true.
- **R4/S4** Reproducibility text overclaims bit-identical results; define a
  determinism + step-versioning policy.
- **R5** Per-step full-copy immutability will not scale to hyperspectral cubes;
  adopt copy-on-write + intermediate-result caching as the contract.
- **R6** xarray leak risk in the public API; `snom.io` shadows stdlib `io`.
- **R7** The viz "backend-neutral render model" risks an over-abstraction; scope
  it to display-ready data.
From the documentation audit (this session):
- **Naming inconsistency:** code/`README.md`/`pyproject.toml` use `snom` as if
  settled, but the rename is decided. `decisions.md` ADR-0010 still "Proposed".
- **Stale ADR statuses:** `decisions.md` does not yet reflect the user's four
  answers (e.g., ADR-0009 external-refs accepted; ADR-0010 rename decided).
- **Missing cross-references:** `vision/architecture/data-model/roadmap/decisions`
  do not yet link to `architecture-review.md`; the roadmap is not yet reordered.
- **Unicode garbling:** several docs use box-drawing/arrows/`micro`/subscripts
  that render badly in Windows terminals. (This LOG, `CLAUDE.md`, `NEXT.md`, and
  the review are ASCII-safe.)

### Documentation Updated
- **Created:** `docs/architecture-review.md`, `CLAUDE.md`, `LOG.md`, `NEXT.md`.
- **Not yet changed (pending):** `vision.md`, `architecture.md`, `data-model.md`,
  `roadmap.md`, `decisions.md` - the review-driven revisions and audit
  corrections are deferred (not speculative); they are enumerated as tasks in
  `NEXT.md`.

### Next Recommended Actions
See `NEXT.md` for the authoritative list. In brief: answer the 7 Critical design
questions; pick the package name; apply the review-accepted revisions and audit
corrections to the design docs; rename the package; ASCII-convert the older docs;
install `uv` and verify the toolchain; gather the Phase-1 sample files; then
begin the Phase-1 vertical slice.

---

## 2026-06-19 - Phase 0 hardening pass

Closing Phase 0: documentation consistency, decision application, and readiness.
No architecture review, no redesign, no application code (by task scope).

### Completed
- Documentation **consistency pass** across all docs so they tell one story.
- **Applied accepted findings/decisions** (no new architecture work): external raw
  references + manifest (ADR-0009); rename away from `snom` agreed (ADR-0010, name
  still pending); conventions explicit + carried (new ADR-0014); Phase 1 = thin
  vertical slice (new ADR-0015); roadmap reordered accordingly.
- **ASCII/encoding cleanup** of `architecture.md`, `data-model.md`, `decisions.md`,
  `roadmap.md` (removed box-drawing/arrows/emoji/Unicode that garbled on Windows).
- **Decisions audit:** every ADR now has an explicit
  `[ACCEPTED]`/`[PENDING DECISION]`/`[DEFERRED]` status; obsolete "Open questions"
  retired; new **Outstanding Human Decisions** section (OHD-1..OHD-9) isolates
  only items needing user input, with recommendations.
- **Factual corrections:** netCDF cannot store complex (encoding -> OHD-3);
  rotated scans need affine referencing, not 1-D coords (-> OHD-6); reproducibility
  wording scoped to deterministic steps vs documented tolerance.
- Created `docs/phase0-readiness.md`.

### Decisions
- Applied (already accepted): ADR-0009 (external refs), ADR-0010 (rename agreed),
  ADR-0014 (conventions carried), ADR-0015 (vertical slice).
- Deliberately NOT decided: OHD-1..OHD-9 still require user input; recommendations
  recorded only. The 7 Critical (OHD-1..OHD-7) gate Phase 1.

### Issues Found
- No new architecture issues (no new review performed, per scope).
- Prior documentation-audit issues are now fixed: stale ADR statuses updated,
  cross-references to `architecture-review.md` added, Unicode garbling removed.
- Residual minor (tracked in `phase0-readiness.md`, not blocking): `README.md`
  still says `snom` without a provisional note and omits the newer files from its
  doc table.

### Documentation Updated
- Rewritten (ASCII + consistency): `decisions.md`, `data-model.md`,
  `architecture.md`, `roadmap.md`.
- Created: `docs/phase0-readiness.md`.
- Refreshed: `LOG.md` (this entry), `NEXT.md`.
- Untouched by design: `vision.md`, `CLAUDE.md`, `architecture-review.md`,
  `README.md`, and all source/tests (no application code changed).

### Readiness status
Phase 0 foundation is complete and internally consistent. Phase 0 **closes** once
OHD-1..OHD-7 are resolved (or deferred), the package is renamed, and the toolchain
is green under CI. Full detail: `docs/phase0-readiness.md`.

### Next Recommended Actions
Per `NEXT.md`: user answers OHD-1..OHD-9 (or accepts recommendations) and gathers
sample files; then install/verify the `uv` toolchain, rename the package, add CI
and `git init`; then begin the Phase 1 vertical slice.

---

## 2026-06-22 - OHD application; Phase 0 complete

All nine Outstanding Human Decisions were accepted by the user and applied across
the repository. No architecture review, no reopened decisions, no Phase 1 features.

### Completed
- **Renamed the package `snom` -> `snomniman`** (OHD-1): `src/snom` -> `src/snomniman`,
  all 8 `__init__.py` docstrings, `pyproject.toml` (name, wheel packages, isort,
  dependencies), and `tests/` (imports + the Qt-free backend list). Verified
  `import snomniman` works and the backend Qt-free invariant still passes.
- **Dependencies updated for OHD-3:** added `zarr` (canonical store), removed the
  superseded `h5netcdf`, kept `h5py` (vendor HDF5 reading).
- **Applied OHD-2..9 in the docs:** provenance DAG (2); Zarr canonical store,
  vendor reads via readers (3); first-class unwrapped-phase channel (4); full
  traceability - sources/DAG/steps/params/software + operation versions (5);
  conventions stored in metadata, canonical unit nm, origin lower-left/x-right/
  y-up, phase preserved as imported (6); metadata/calibration edits are
  provenance-tracked (7); hybrid DataKind + capabilities dispatch (8); first
  reader = real neaSNOM imaging dataset (9).
- **Closed OHD-1..9 in `decisions.md`:** statuses set to ACCEPTED, added a
  "Decision Closure" table, and added ADR-0016 (metadata-as-provenance) and
  ADR-0017 (hybrid dispatch).
- **Redefined Phase 1** (roadmap + NEXT) as the backend-only neaSNOM imaging
  vertical slice: Dataset model -> Metadata schema -> Provenance schema -> reader
  -> golden-file tests. No GUI, no advanced processing, no visualization.
- `phase0-readiness.md` now reports **Phase 0 complete** (zero remaining decisions).

### Decisions
- OHD-1..9 resolved and applied; no human decisions remain open.

### Issues Found
- None new (no review). Consistency verified: the package is `snomniman`
  throughout; remaining lowercase `snom` is intentional only - the `snom` keyword
  in `pyproject.toml`, the "name `snom` rejected" note in ADR-0010, and this LOG's
  earlier (historical, append-only) entries.

### Documentation Updated
- Rewritten: `decisions.md`, `data-model.md`, `architecture.md`, `roadmap.md`,
  `phase0-readiness.md`, `CLAUDE.md`, `README.md`, `NEXT.md`.
- Code/config: `src/snomniman/**` (renamed), `pyproject.toml`,
  `tests/test_smoke.py`, `tests/conftest.py`.
- Appended: this `LOG.md` entry.
- Untouched: `vision.md` (no package-name references; conventions live in
  data-model/decisions) and `architecture-review.md` (historical artifact; one
  hygiene line updated previously).

### Readiness status / Next
Phase 0 complete (decisions + documentation). Remaining before Phase 1 code:
install `uv`, add CI, `git init`, and obtain a real neaSNOM imaging golden file.
Then implement the Phase 1 slice in the order above.

---

## 2026-06-22 - Infrastructure baseline (uv toolchain, validation, git)

Infrastructure only: established a reproducible environment and the first
version-control checkpoint. No architecture changes, no reopened decisions, no
Phase 1 features.

### Completed
- Installed **uv 0.11.23** (via `pip install uv`); Python is CPython 3.13.7.
- `uv sync` created `.venv` and installed the stack (numpy 2.5.0, scipy 1.18.0,
  xarray 2026.4.0, zarr 3.2.1, h5py 3.16.0, matplotlib 3.11.0; dev: pytest 9.1.1,
  ruff 0.15.18, mypy 2.1.0) + editable `snomniman` 0.1.0; generated `uv.lock`.
- Validation under the real toolchain: `uv run pytest` -> **3 passed**;
  `uv run ruff check .` -> **all passed**; `uv run mypy .` -> **success, no issues
  in 10 files** (one benign informational unused-override note, retained).
- Backend/Qt-free invariant confirmed (the unit test plus an explicit import check
  of core/io/processing/pipeline/batch under the venv).
- `git init -b main`; staged the Phase 0 state (24 files incl. `uv.lock`; `.venv`/
  `.obsidian`/caches excluded); created the **initial baseline commit**.
- Added `.obsidian/` to `.gitignore` (stray editor state) and ASCII-fixed one
  `.gitignore` comment; created `docs/infrastructure-baseline.md`.

### Decisions
- None changed (infrastructure only). No OHDs reopened.

### Issues Found
- `uv` not on PATH after `pip install` (its Scripts dir is not on PATH) - resolved
  by invoking the explicit executable path; not a project issue.
- A stray `.obsidian/` directory was present in the project - now git-ignored.
- mypy informational note (overrides for not-yet-imported libs) - benign, retained.

### Documentation Updated
- Created `docs/infrastructure-baseline.md`; appended this `LOG.md` entry; updated
  `NEXT.md`; edited `.gitignore`.

### Readiness status / Next
Reproducible environment verified and committed; Phase 0 fully closed. The only
remaining Phase 1 gate is a real neaSNOM imaging golden file (CI is a recommended,
non-blocking add). Begin Phase 1 with the Dataset model + Metadata + Provenance
schemas, which are buildable now with synthetic data.

---

## 2026-06-23 - CI workflow

Infrastructure only: added GitHub Actions CI. No architecture changes, no
reopened decisions, no Phase 1 features.

### Completed
- Created `.github/workflows/ci.yml`: triggers on `push` and `pull_request`;
  uses `ubuntu-latest` with Python 3.13 (matching the local CPython 3.13.7
  baseline); installs `uv` via `astral-sh/setup-uv@v5`.
- CI runs the four gates in sequence: `uv sync`, `uv run ruff check .`,
  `uv run mypy .`, `uv run pytest`. The pytest step includes the
  `test_backend_is_qt_free` invariant, so Rule 4 is enforced automatically in CI.

### Decisions
- None (infrastructure only). No OHDs reopened.

### Issues Found
- None.

### Documentation Updated
- Created `.github/workflows/ci.yml`.
- Updated `docs/infrastructure-baseline.md`: added CI section; updated the
  "Remaining blockers" entry from "recommended, non-blocking" to done.
- Updated `NEXT.md`: marked task A.3 (CI) complete; updated "last updated" date.
- Appended this `LOG.md` entry.

### Readiness status / Next
All Phase 0 infrastructure is complete: environment, version control, and CI.
The only remaining Phase 1 gate is the real neaSNOM imaging golden file.
Phase 1 Dataset / Metadata / Provenance schemas can be built now with synthetic data.

---

## 2026-06-23 - AI Architecture Principles

Project guidance only: no architecture decisions changed, no OHDs reopened, no
Phase 1 features, no AI implementation.

### Completed
- Added "AI Architecture Principles" section to `CLAUDE.md`: position in the
  layer stack; scientific core as source of truth; structured output preference;
  provenance requirements for AI actions; what AI is not.
- Added two new "Never do" rules to `CLAUDE.md`: AI output must not silently
  override the scientific core; AI integration must not bypass provenance.
- Added `docs/ai-principles.md` placeholder row to the Documentation Hierarchy
  table (to be written when AI design begins).
- Added a forward-reference paragraph to `docs/architecture.md` section 2
  (layered architecture) describing the future AI layer position.
- Updated the project status block and stale Practical Notes in `CLAUDE.md`
  (removed "uv not yet installed" and "repo not yet git init-ed"; updated date).

### Decisions
- AI is a first-class analysis subsystem, not a UI add-on or chatbot.
- Scientific core (raw data, metadata, provenance) remains authoritative; AI
  consumes but does not override it.
- AI-generated outputs should be structured and provenance-recordable.
- A detailed `docs/ai-principles.md` will be written when AI design begins.
  No ADR needed yet (no architectural change; this is directional guidance only).

### Issues Found
- None.

### Documentation Updated
- `CLAUDE.md`: new AI Architecture Principles section; two new Never-do rules;
  Documentation Hierarchy table; status block; Practical Notes.
- `docs/architecture.md`: forward-reference paragraph in section 2.
- Appended this `LOG.md` entry.

### Readiness status / Next
Phase 0 fully closed; CI in place; AI direction recorded. Only remaining Phase 1
gate is the neaSNOM golden file. Phase 1 Dataset/Metadata/Provenance schemas
are buildable now with synthetic data.

---

## 2026-06-23 - Measurement discovery; Phase 1 unblocked

Documentation and validation exercise: first real neaSNOM measurement data
inspected. No architecture decisions changed, no OHDs reopened, no code written.

### Completed
- Inspected real neaSNOM measurement data at `SNOM Sample Files/2026-06-16 14928/`.
  Four complete measurement runs confirmed present; one run analysed in detail.
- Identified format: **GSF (Gwyddion Simple Field)**, not HDF5. Each channel is a
  separate `.gsf` file within a measurement directory. A `.txt` parameter file
  provides instrument metadata alongside the channel files.
- Confirmed channel naming convention matches `data-model.md`: O{n}A/P, M{n}A/P,
  R- reference prefix, Z topography. Complex assembly from amplitude+phase pairs
  confirmed.
- Confirmed spatial units in GSF headers are meters (XYUnits=m); canonical nm
  conversion required on import (OHD-6B). Phase stored as-imported (OHD-6D
  directly confirmed).
- Corrected stale "HDF5 / h5py" assumption in `architecture.md`, `data-model.md`,
  `decisions.md`, `phase0-readiness.md`; updated reader description to
  "GSF measurement-directory reader" in `roadmap.md`, `NEXT.md`, `decisions.md`.
- Cleared all Phase 1 gate/blocker entries (sample data, uv, CI, git all done).
- Created `docs/measurement-discovery.md` (historical record of this exercise).
- Added `docs/measurement-discovery.md` entry to Documentation Hierarchy tables
  in `CLAUDE.md` and cross-referenced from `decisions.md` ADR-0009/ADR-0012.

### Decisions
- No new decisions. The format correction (GSF directory vs. HDF5 single file) is
  contained within the reader implementation and requires no new ADR.
- One implementation detail deferred to Phase 1: how `RawSource` anchors a
  measurement directory (directory path + per-file hash manifest vs. `.txt` hash).

### Issues Found
- The assumption that the neaSNOM first reader would target a single HDF5 file was
  incorrect. The actual format is a directory of GSF files. Corrected throughout.
- No architecture or data-model issues: the reader registry design (ADR-0006)
  absorbs the format difference cleanly.

### Documentation Updated
- Created: `docs/measurement-discovery.md`.
- Updated: `docs/architecture.md`, `docs/data-model.md`, `docs/decisions.md`,
  `docs/roadmap.md`, `docs/phase0-readiness.md`, `NEXT.md`, `CLAUDE.md`.
- Appended: this `LOG.md` entry.

### Readiness status / Next
Phase 1 is fully unblocked. All gates are cleared. Implementation can begin in
the planned order: Dataset model -> Metadata schema -> Provenance schema ->
GSF measurement-directory reader -> golden-file tests.

---

## 2026-06-25 - Phase 1 vertical slice implemented (neaSNOM GSF reader -> Dataset)

First application code. The full Phase 1 vertical slice is implemented and
validated end-to-end against the real neaSNOM measurement directory: a GSF
measurement directory loads into a validated `Dataset` with correct dims,
canonical-nm coordinates, complex channels, typed `Metadata`, a `RawSource`
anchor, and a single-node provenance DAG. No GUI, no processing algorithms, no
visualization (per ADR-0015 scope).

### Completed
- **`snomniman.core` (8 modules):** `exceptions` (typed error hierarchy);
  `units` (canonical nm + explicit length conversion, unknown-unit guard);
  `datakind` (`DataKind` enum); `capabilities` (`Capability` enum); `metadata`
  (typed `Metadata` + `Conventions`/`Instrument`/`Excitation`/`Demodulation`/
  `ScanInfo`/`Acquisition`/`ChannelInfo`, JSON round-trip, verbatim raw header);
  `rawsource` (`RawSource` with single-file *and* directory-manifest hashing -
  resolves the deferred Phase-1 anchor question); `provenance` (`StepRecord`,
  multi-input `ProvenanceNode` DAG, software-version capture, DAG (de)serialize);
  `dataset` (`Dataset` - xarray-backed, capability derivation, complex
  amplitude/phase views, raw-array immutability).
- **`snomniman.io` (3 modules):** `gsf` (pure Gwyddion Simple Field reader/writer,
  correct 1-4 NUL 4-byte alignment, little-endian float32, native top-to-bottom
  order); `neasnom` (measurement-directory reader: channel discovery, geometry
  validation, complex assembly `O{n}=A*exp(iP)`, documented vertical flip to the
  canonical lower-left/y-up origin, m->nm conversion, `.txt` + GSF-header metadata
  extraction, provenance node); `registry` (reader registry + content sniffing,
  ADR-0006).
- **Tests (52 new; 55 total):** `test_gsf` (11), `test_core_dataset` (9),
  `test_metadata` (4), `test_provenance` (6), `test_rawsource` (4),
  `test_neasnom_golden` (18). Golden tests assert channel count/names (32 from 56
  files), dims (150x150), nm coordinates, amplitude/phase faithfulness to the raw
  files, lower-left orientation, m->nm topography, full metadata, and provenance
  JSON round-trip - all against the real CdO measurement.
- **Gates green:** `ruff` clean, `mypy --strict` exit 0 (27 files), `pytest`
  55 passed, backend Qt-free invariant holds (io imports numpy/xarray, no Qt).

### Decisions
- **`RawSource` directory anchor (deferred Phase-1 detail, now resolved):** a
  measurement directory is anchored by a **sorted manifest of (relative-name,
  per-file sha256)** over the consumed files (the `.gsf` channels + `.txt`),
  hashed into one stable, order-independent sha256. Not an ADR (an implementation
  of the existing ADR-0009 design); recorded here.
- **Canonical orientation conversion is explicit and recorded:** GSF stores rows
  top-to-bottom; the reader applies `flipud` to reach the canonical lower-left/
  y-up convention (OHD-6C) and records the transformation in the `io.read`
  provenance node's params. Phase is preserved exactly as imported (OHD-6D): no
  invert/re-reference/unwrap/normalize.
- **Complex assembly + reference handling:** `O{n}`/`M{n}` assembled complex from
  A/P pairs; `R-` files become `R_*` reference channels; `Z` variants (`raw`/`C`/
  `H`/`CH`) map to `Z`/`Z_C`/`Z_H`/`Z_CH`. Channel name -> capability derivation
  drives the hybrid dispatch set (ADR-0017).
- **mypy `python_version` 3.11 -> 3.12 (tooling only):** numpy 2.5's stubs use
  PEP 695 `type` statements that mypy parses only at >=3.12. Runtime floor stays
  3.11 (`requires-python`) and ruff still targets py311, so 3.11-incompatible
  syntax in our own code is still caught. No architecture/decision impact.

### Issues Found
- **Reader robustness (caught by testing all four runs, fixed):** the
  channel-name prefix must come from the **directory name**, not the `.txt`
  stem - one acquisition names its parameter file `"<dir> Spectra.txt"`. With the
  fix, the three imaging runs load (incl. one 400x300, proving dims are not
  hardcoded) and the non-imaging "PSP ... Spectra" point-spectra run is **rejected
  cleanly** with a clear error rather than mis-read. Phase 1 targets imaging only;
  other modalities are future readers.
- **Pre-existing mypy/numpy-stub incompatibility surfaced:** the prior "mypy
  green" was on an empty scaffold that never imported numpy. Resolved via the
  `python_version` bump above.
- No architecture issues. The data model, layering, OHDs, and ADRs all held
  against real data with no redesign - the slice's purpose, achieved.

### Documentation Updated
- Created source: `src/snomniman/core/{exceptions,units,datakind,capabilities,
  metadata,rawsource,provenance,dataset}.py`; `src/snomniman/io/{gsf,neasnom,
  registry}.py`; populated `core/__init__.py` and `io/__init__.py` exports.
- Created tests: `tests/test_{gsf,core_dataset,metadata,provenance,rawsource,
  neasnom_golden}.py`; added fixtures to `tests/conftest.py`.
- `pyproject.toml`: mypy `python_version` 3.11 -> 3.12 (documented inline).
- `LOG.md` (this entry); `NEXT.md` (Phase 1 -> done, Phase 2 next);
  `docs/infrastructure-baseline.md` (mypy note); `CLAUDE.md` status block.

### Next Recommended Actions
Phase 1 exit criteria are met **except** the Zarr round-trip (the slice does not
yet persist to the canonical store). Recommended next: (1) implement the Zarr
writer/reader and add the `Dataset -> Zarr -> Dataset` round-trip invariant to
fully close the Phase-1 DoD; then (2) begin Phase 2 (core breadth: channel state,
unwrapped-phase accessor, more readers, synthetic generators). See `NEXT.md`.

---

## 2026-06-25 - Phase 2 UX vision (product design; no code)

Product-design exercise per user request: design the interactive experience
before any GUI code. No application code, no architecture change, no decisions
reopened.

### Completed
- Created **`docs/phase2-vision.md`** - the experience blueprint for the
  interactive application. Implementation-agnostic (no widgets/Qt/mockups). Seven
  required sections plus framing: experience pillars + two mantras ("nothing is
  hidden, nothing is silent"; "explore before you process"); 6 user personas
  (Newcomer, Power User, PI/Reviewer, Facility staff, Collaborator, Future Self);
  9 primary workflows (goal / sequence / pain-to-eliminate); information
  architecture (always-visible vs on-demand, progressive disclosure); viewer
  vision (synchronized cross-channel cursor, honest complex/phase rendering,
  multi-harmonic contact sheet, in-place metadata/provenance inspection);
  AI experience (structured, provenance-aware, augment-not-interrupt, grounded in
  Dataset/Metadata/Provenance); publication workflow (figures carry provenance);
  long-term vision; and a build-sequencing note (read-only exploration first).
- Grounded every UX promise in an existing backend guarantee (provenance DAG,
  raw immutability, explicit conventions OHD-6, structured AI per `CLAUDE.md`).
- ASCII-clean (Windows-terminal convention); cautious neaPLOT framing per
  `vision.md`.

### Decisions
- None. This is directional product guidance, not an architecture decision; no
  ADR and no OHD change. The roadmap's phase numbering is unchanged (the GUI
  remains a later phase in `roadmap.md`); the user's "Interactive Data
  Exploration" framing is captured as the recommended first GUI increment inside
  `phase2-vision.md` Section 8, not as a roadmap rewrite.

### Issues Found
- None.

### Documentation Updated
- Created: `docs/phase2-vision.md`.
- Updated: `CLAUDE.md` (Documentation Hierarchy row); `NEXT.md` (pointer to the
  UX blueprint for the GUI phase); this `LOG.md` entry.

### Next Recommended Actions
Unchanged from the entry above: close the Phase-1 DoD with the Zarr round-trip
(`NEXT.md` D.10), then proceed with core breadth (Phase 2 in `roadmap.md`). When
GUI work begins, `docs/phase2-vision.md` is the experience blueprint; build the
read-only exploration increment first.

---

## 2026-06-25 - Product philosophy (identity / mental model; no code)

Product-philosophy exercise per user request: define the conceptual interaction
model and identity that should unify every future feature. No application code, no
architecture change, no decisions reopened.

### Completed
- Created **`docs/product-philosophy.md`** - the project's highest-level *design*
  (identity/soul) document. Implementation-agnostic (no Qt/widgets/classes/screens).
  Six required topics plus framing and a decision-litmus:
  - **Core mental model (chosen and justified):** *"Everything is a derivation of
    an immutable measurement."* Central object = the **Measurement** (immutable
    truth); central relationship = **derivation** (every result is recorded and
    traceable to its source) - the Git-like soul. Rejected alternatives with
    reasons: Dataset (architecture's term, not the scientist's), Experiment (too
    broad; ELN scope is out per `vision.md`), Knowledge graph (an emergent
    structure, not an object the user holds).
  - **9 enduring principles** (measurement is sacred; nothing hidden/silent;
    explore before process; provenance is the product; every result explains
    itself; AI augments never owns; reproducibility is structural; legible+
    powerful; honesty about kind).
  - **Human + AI collaboration:** Data -> AI -> Human understanding; AI carries
    breadth/recall/first-drafts/vigilance, the human keeps judgment/hypothesis/
    decision/authority. "AI proposes, the scientist disposes, the measurement is
    the arbiter."
  - **Scientific trust** (immutability, provenance, explicit assumptions,
    transparent processing, inspectable AI, reversibility, validated correctness).
  - **Product identity** paragraph ("...turns a near-field measurement into
    understanding you can defend").
  - **Anti-goals** (identity boundaries, distinct from `vision.md` scope non-goals):
    never a black box / silent processor / AI oracle / vendor cage / menu labyrinth
    / destructive editor / figure factory.
- Positioned it as the apex design doc above `vision.md`/`phase2-vision.md` while
  leaving `CLAUDE.md` as the operational constitution; added a "Relationship to
  other documents" altitude table so the docs complement rather than duplicate.
- ASCII-clean; all cross-references resolve.

### Decisions
- The **core mental model** is now explicitly chosen: *measurement + derivation*.
  This is directional identity, not an architecture decision - it already matches
  the settled provenance-DAG/immutability design (OHD-2/OHD-4..7), so no ADR and no
  OHD change. It is the lens future decisions are checked against.

### Issues Found
- None. The chosen mental model is consistent with the existing architecture and
  data model (immutable raw + provenance DAG); no contradictions surfaced.

### Documentation Updated
- Created: `docs/product-philosophy.md`.
- Updated: `CLAUDE.md` (Documentation Hierarchy - added as the apex design doc);
  `NEXT.md` (pointer); this `LOG.md` entry.

### Next Recommended Actions
Unchanged: close the Phase-1 DoD (Zarr round-trip, `NEXT.md` D.10), then Phase 2
core breadth. `docs/product-philosophy.md` is now the lens for every future
architectural, UI, AI, and workflow decision; `phase2-vision.md` remains the
experience blueprint for the GUI phase.

---

## 2026-06-25 - Measurement Explorer interaction-design blueprint (no code)

Interaction-design exercise per user request: the blueprint for the central GUI
experience, before any GUI code. No application code, no architecture change, no
decisions reopened. Framed as the **last design doc before building**.

### Completed
- Created **`docs/measurement-explorer.md`** - the interaction-design blueprint for
  the **Measurement Explorer** (the name now adopted for SNOMNIMAN's central GUI
  experience). Interaction-design altitude only (no Qt/widgets/menus/layouts; a
  vocabulary check confirms none). Nine required sections:
  1. Explorer philosophy (looking *through* the software at the measurement;
     explore before you process; safe/immediate/alive/honest).
  2. The first five minutes (a concrete narrative grounded in the real CdO scan).
  3. Information hierarchy (always-visible scientific frame / quickly-accessible /
     rarely-needed).
  4. Navigation model (one metaphor: "you are always somewhere in the derivation
     graph of a measurement"; channels/harmonics/references/space/metadata/
     provenance/derived datasets/across-measurements).
  5. AI integration built on the user's insight that **an AI result is just
     another derivation of the measurement** - same graph, same provenance; in
     context; proposes-not-asserts.
  6. Transparency as an interaction guarantee (where from / how produced / what
     assumptions; never lost).
  7. Future growth (hyperspectral, point spectra, pipelines, AI analyses,
     publication, batch all absorbed as new measurement-kinds or derivations - the
     concepts are closed under these additions).
  8. Better than neaPLOT - by *experience* per workflow (cautious framing per
     `vision.md`): friction today -> how removed -> why fundamentally better.
  9. Product North Star (what a researcher remembers after eight hours).
- Adopted the user's **"Measurement Explorer"** naming for the central experience;
  noted it as the heart of the interactive GUI phase in `roadmap.md` (no phase
  renumbering).
- Grounded throughout in the real measurement (O0-O5/M0-M5, references, topography,
  nm coords) and kept strictly consistent with `product-philosophy.md`.
- ASCII-clean; all cross-references resolve.

### Decisions
- None (directional design). The "AI-as-derivation" framing is not a new decision -
  it is the existing provenance-DAG model (OHD-2/OHD-5) plus the AI principles in
  `CLAUDE.md`, restated as experience. No ADR, no OHD change.
- Naming: the interactive imaging GUI's first surface is "the Measurement Explorer."
  Captured in this doc and referenced from `roadmap.md`; phase numbers unchanged.

### Issues Found
- None. The blueprint is consistent with the architecture, data model, and
  philosophy; every Explorer concept maps to an existing backend capability.

### Documentation Updated
- Created: `docs/measurement-explorer.md`.
- Updated: `CLAUDE.md` (Documentation Hierarchy row); `roadmap.md` (Explorer name +
  pointer on the interactive-GUI phase); `NEXT.md` (pointer); this `LOG.md` entry.

### Next Recommended Actions
The design layer is now complete enough to build against. Highest-leverage next
step is **implementation, not more docs**: close the Phase-1 Zarr round-trip
(`NEXT.md` D.10), then build the **read-only Measurement Explorer** per
`docs/measurement-explorer.md`. Recommended working rule going forward: no new
design documents unless implementation exposes a real problem.

---

## 2026-06-25 - Canonical Zarr store; Phase 1 COMPLETE

Closed the final Phase-1 Definition-of-Done item: the canonical
`Dataset -> Zarr -> Dataset` round-trip (OHD-3). Backend only - no GUI, no
processing algorithms, no AI, no architecture change, no decisions reopened.

### Completed
- **`snomniman.io.zarrstore` (new module):** `write_zarr(dataset, path,
  *, overwrite=True) -> Path` and `read_zarr(path) -> Dataset`, the canonical
  project store. Labeled arrays are written via `xarray.Dataset.to_zarr`
  (complex64 channels, per-array units/attrs, dtypes, and dims handled natively
  by Zarr); the SNOMNIMAN-level semantics that are not plain array data
  (`DataKind`, typed `Metadata`, the provenance DAG, the `RawSource` anchor) are
  serialized into **one JSON document** stored under the reserved Zarr group
  attribute `"snomniman"` (format marker `snomniman.dataset`, `schema_version` 1).
- **Wiring:** exported `read_zarr`, `write_zarr`, `STORE_FORMAT`,
  `STORE_SCHEMA_VERSION` from `snomniman.io`. The store is intentionally **not**
  registered in the vendor reader registry (that registry imports foreign files;
  this is our own canonical format).
- **Tests (19 new; 74 total):** `tests/test_zarr_roundtrip.py`. A deep
  equivalence helper asserts kind, derived capabilities, `is_raw`, channel set +
  dtypes + **bit-identical** values, `xarray.testing.assert_identical` (names,
  dims, coords, values, units/attrs), full typed-metadata equality (incl. the
  explicit conventions, nested verbatim header, per-channel descriptors),
  provenance-DAG equality (`serialize_dag`), and `RawSource` equality - on both a
  content-rich **synthetic** dataset (complex + multi-harmonic + reference +
  float64/float32 topography, non-default conventions, a 2-node DAG) and the real
  **golden** CdO measurement. Plus guards: `overwrite=False` refuses an existing
  store (`FileExistsError`); a non-store path and a foreign (non-SNOMNIMAN) Zarr
  both raise `ReaderError`; loaded datasets remain immutable; amplitude/phase
  views stay consistent after a round-trip.
- **Gates green:** `ruff` clean, `mypy --strict` no issues (29 files), `pytest`
  74 passed, backend Qt-free invariant still holds (`zarrstore` imports only
  `json`/`pathlib`/`xarray`/`snomniman.core` - no Qt).

### Decisions
- **Sidecar-as-JSON-string (implementation detail, not an ADR):** the non-array
  scientific state is stored as a single JSON string in the Zarr group attrs
  rather than as nested Zarr attributes. Rationale: fully deterministic, immune to
  attribute-encoding quirks, self-contained, version-tagged, and human-inspectable
  in `zarr.json`. The per-array units/attrs that Zarr handles cleanly are left to
  Zarr. Reuses the existing `Metadata.to_dict`/`serialize_dag`/`RawSource.to_dict`
  serializers - no parallel implementation (Rule 2).
- **Derived-not-stored:** the capability set and the amplitude/phase views are
  recomputed on load (they are pure functions of the array data), so they cannot
  drift from the data they describe. `DataKind` is *not* derivable and is
  persisted explicitly.
- **Eager load + freeze:** `read_zarr` calls `.load()` so the reconstructed
  dataset holds real numpy arrays, which the `Dataset` constructor freezes -
  giving the same raw-immutability guarantee as a fresh import. Lazy/chunked
  streaming is a deliberate future optimization (R5), not Phase 1.
- **Zarr v3:** stores are written `consolidated=False` (consolidated metadata is
  not part of the Zarr v3 spec and otherwise warns).

### Issues Found
- None architectural. Empirically de-risked before implementing: zarr 3.2.1 +
  xarray round-trip **complex64/float64/float32** exactly; coordinate and variable
  `attrs` (including `None`-valued ones) survive; `to_zarr` writes correctly from
  read-only (frozen) arrays; with dask absent, `open_zarr().load()` returns real
  numpy arrays (so freezing enforces immutability). The data model, layering,
  OHDs, and ADRs held against the real-data round-trip with no redesign.

### Documentation Updated
- Created: `src/snomniman/io/zarrstore.py`; `tests/test_zarr_roundtrip.py`.
- Updated: `src/snomniman/io/__init__.py` (exports); `CLAUDE.md` (status block ->
  Phase 1 COMPLETE); `NEXT.md` (D.10 done, DoD all met, blockers none); this
  `LOG.md` entry. The persistence-layer implementation notes for future
  developers live in the `zarrstore` module docstring (store layout, the reserved
  `"snomniman"` group attribute, derived-not-stored facets, eager-load+freeze,
  the Zarr v3 `consolidated=False` note).

### Next Recommended Actions
**Phase 1 is complete.** Per the user's working rule (no new design docs), the
next high-leverage work is the first *experience*: build the **read-only
Measurement Explorer** (open a measurement -> browse channels -> inspect
metadata/provenance) per `docs/measurement-explorer.md`, judged against
`docs/product-philosophy.md`. Alternatively, extend backend core breadth (Phase 2
in `roadmap.md`: channel state, unwrapped-phase accessor, more readers, synthetic
generators). No Phase-1 items remain.

---

## 2026-06-25 - Read-only Measurement Explorer (first GUI experience)

The project's first user-facing experience: a read-only **Measurement Explorer**
that opens a neaSNOM measurement directory as one coherent, understandable object
(not 56 files). Strictly read-only - no processing, editing, export, AI authoring,
or dataset writing (per the milestone scope). Built against
`docs/measurement-explorer.md` and `docs/product-philosophy.md`.

### Completed
- **`snomniman.viz.render` (new, Qt-free backend):** `RenderData` value object +
  `prepare_channel`/`available_representations`/`default_representation`/
  `pick_scale_bar`. This is where the *scientific display decisions* live and are
  unit-tested headlessly: complex channels shown honestly as **amplitude** (viridis)
  or **phase** (cyclic `twilight`, fixed -pi..pi, flagged `cyclic`); topography in
  `afmhot`; robust percentile ranges; physical pixel-edge extent honoring the
  lower-left origin (OHD-6C). Phase shown exactly as imported (OHD-6D).
- **`snomniman.gui.model.ExplorerModel` (new, Qt-free presenter):** the testable
  core of the experience - channel grouping by physical meaning
  (optical/mechanical/topography/references), a sensible default channel (O2
  amplitude), identity, typed metadata arranged into readable sections (each value
  with its unit and *source*), provenance/lineage in plain language, and a
  cross-channel cursor readout. Holds one immutable `Dataset` and only ever reads.
- **`snomniman.gui` widgets (PySide6 + PyQtGraph):** `ChannelImageView`
  (physical-nm image, lower-left orientation verified, recommended colormap/range,
  physical scale bar, hover->coordinate), `ChannelBrowser` (grouped tree + an
  amplitude/phase toggle shown only when there is a choice), `MetadataInspector`,
  `ProvenanceInspector`, `MeasurementExplorerWindow` (identity frame + image +
  docks + conventions/readout status bar), `colormap.lookup_table` (matplotlib name
  -> LUT), and the `app.run` / `__main__` entry point
  (`python -m snomniman.gui [dir]`).
- **Verified on the real CdO measurement** (rendered offscreen): opens to O2
  amplitude with the nanoparticle near-field contrast (viridis); amplitude/phase
  toggle gives honest cyclic phase; topography in nm; the cursor readout reports
  `O2 amplitude / O2 phase / Z height` at one pixel; the identity frame shows
  `150x150 px, 10x10 um, 5973 cm^-1, PsHet, ...`; conventions and "this is the raw
  measurement" provenance are always visible.
- **Tests (+26; 100 total):** `test_viz_render` (8), `test_gui_model` (13,
  Qt-free, run in CI), `test_gui_window` (6, skip without the `gui` extra; headless
  offscreen otherwise). They cover representation honesty, scale-bar rounding,
  channel grouping/identity/metadata/provenance, cursor readout, channel switching,
  and the cardinal invariant **exploration never mutates the Dataset** (arrays
  unchanged and still frozen after a full browse) at both the model and window
  levels.
- **Gates green:** `ruff` clean, `mypy --strict` no issues (40 files), `pytest`
  100 passed.

### Decisions
- **GUI Rule added to `CLAUDE.md` (Rule 9, user-requested):** "Every GUI feature
  must justify its existence by improving a researcher's understanding of a
  measurement." Guards the Explorer against becoming a menu labyrinth.
- **Display logic lives in `viz` (Qt-free), not in widgets.** The honest
  amplitude/phase/colormap/range/extent/scale-bar decisions are in `viz.render`
  and tested without a display; the widgets are thin consumers (Rule 4). The model
  (channel grouping, identity, sections, readout) is a Qt-free presenter in `gui`,
  so the bulk of the experience is unit-tested headlessly and runs in CI.
- **`ChannelImageView` uses composition** (wraps a `PlotWidget`) rather than
  subclassing it, so the typed Qt surface stays clean under strict mypy.
- **Qt-free invariant hardened (strengthened, not weakened):**
  `test_backend_is_qt_free` now imports the backend in a **subprocess** and checks
  that process's `sys.modules`. This makes the invariant about what the backend
  itself imports - immune to a GUI test importing Qt earlier in the same pytest
  session - which the prior whole-`sys.modules` check could not distinguish.
- **Tick labels shown in um, data/coords/hover in nm.** Axis tick text is scaled
  for readability only; the scale bar and cursor readout are the authoritative
  physical references, and the model stays entirely in canonical nm.

### Issues Found
- Pre-empted the Qt-free false-positive (a GUI test importing PySide6 would have
  polluted the shared `sys.modules` the old invariant inspected) by moving the
  check to a subprocess. No scientific-logic leak into widgets (enforced by Rule 4
  and the mutation tests). matplotlib 3.11 removed `cm.get_cmap`; used
  `matplotlib.colormaps[name]`.

### Documentation Updated
- Created: `src/snomniman/viz/render.py`; `src/snomniman/gui/{model,colormap,
  imageview,panels,window,app,__main__}.py`; `tests/test_{viz_render,gui_model,
  gui_window}.py`.
- Updated: `src/snomniman/viz/__init__.py`, `src/snomniman/gui/__init__.py`
  (exports/docstring); `tests/conftest.py` (offscreen platform, `qapp` +
  `synthetic_dataset` fixtures); `tests/test_smoke.py` (subprocess invariant);
  `.github/workflows/ci.yml` (install the `gui` extra + Qt offscreen libs so mypy
  and the GUI tests run in CI); `CLAUDE.md` (Rule 9 + status);
  `docs/architecture.md` (viz/gui now implemented); `NEXT.md`; this `LOG.md` entry.

### Next Recommended Actions
The first experience exists and is verified. Recommended next (still pre-processing,
to deepen *understanding* before any transformation): a harmonic **contact sheet**
(all O-orders at a glance), **signal-with-reference** side-by-side, per-region
**statistics**, and an optional **AI orientation** paragraph - each an Explorer
addition that must pass Rule 9. Only after exploration feels complete should
processing (leveling, normalization, explicit phase unwrap) begin - and every such
step must be an explicit, provenance-recorded derivation (never silent).

---

## 2026-06-26 - Product review of the Measurement Explorer v0.1 (no code)

Product-critique exercise per user request: now that a real experience exists, step
out of the builder role and evaluate it as a working SNOM researcher would. No code,
no architecture change, no decisions reopened.

### Completed
- Created **`docs/product-review-v0.1.md`** - a deliberately critical, researcher's-
  perspective review of the running Explorer (opened on the real CdO measurement),
  covering all nine requested categories: first impression, per-workflow friction,
  experiential neaPLOT comparison (cautious framing per `vision.md`), scientific
  confidence, AI readiness, low-effort polish, a Must/Should/Nice backlog, things to
  remove/suppress, and the vision test with ranked obstacles.
- **Central finding (uncomfortable truth):** v0.1 is an excellent place to
  *understand* a measurement and not yet a place to *do* anything with it - it wins
  the first five minutes but cannot finish an analysis. Top gaps: no colorbar /
  contrast control; no analysis actions (leveling, normalization, line profiles, ROI
  stats); no multi-channel comparison; cursor readout misplaced/too sparse; no
  provenance-preserving export.
- Vision test answered honestly: a daily neaPLOT user would **not** switch today;
  the seven obstacles are ranked, and most are weeks of conventional product work
  (the hardest, differentiating part - making a measurement understood - is done).

### Decisions
- None. This is product direction, not an architecture decision; no ADR, no OHD
  change. The review is intended as the product backlog for the next iterations and
  supersedes the ad-hoc "F." list in `NEXT.md` as the prioritization source.

### Issues Found
- No software defects (this was a UX/product critique, not a code review). The
  findings are experiential gaps, not bugs; the backend and its tests are unaffected.

### Documentation Updated
- Created: `docs/product-review-v0.1.md`.
- Updated: `CLAUDE.md` (Documentation Hierarchy row); `NEXT.md` (points the next
  priorities at the review's Must-have list); this `LOG.md` entry.

### Next Recommended Actions
Per the review and the user's guidance: (1) commit the GUI milestone + this review;
(2) put the Explorer in front of two or three neaPLOT users and watch them narrate;
(3) work the review's **Must have** list - starting with a colorbar + visible
contrast control, the synchronized multi-channel view, and a relocated cross-channel
cursor readout - before any processing or AI. Each new GUI element must pass Rule 9.

---

## 2026-06-26 - Milestone commits + quantitative image visualization

Two parts: (a) committed the work so far as two clean milestones, and (b)
implemented the highest-priority UX gap from the v0.1 review - making every
displayed image quantitatively trustworthy. No processing, no AI, no architecture
change; the Explorer stays strictly read-only.

### Completed
- **Committed two milestones** (history: Phase 0 scaffold -> these):
  `feat(core): complete Phase 1 scientific backend` (core, io incl. Zarr store,
  golden tests) and `feat(explorer): first read-only Measurement Explorer` (viz,
  gui, product docs incl. the v0.1 review). The 192 MB real sample folder is
  **git-ignored** (golden tests skip when absent, by design); `uv.lock` unchanged.
- **Quantitative visualization system** (closes review Must-have #1):
  - **Colorbar + histogram** via a PyQtGraph `HistogramLUTItem` beside the image:
    shows the value->color mapping with the channel's unit on its axis, the value
    distribution, and where the levels clip; levels are draggable.
  - **Interactive contrast**: Default (robust percentile) and Full-range buttons +
    exact min/max spin boxes, all kept in sync with the histogram. Backed by the
    new Qt-free `viz.level_range(values, mode)` (default/full), so the contrast
    logic is unit-tested without a display. **Display-only - never touches data.**
  - **Channel-aware defaults** unchanged and honored (amplitude viridis / phase
    cyclic twilight at -pi..pi / topography afmhot; robust default range).
  - **Cursor readout relocated** from the window status bar to a strip directly
    beneath the image (cross-channel: amplitude / phase / Z height at the pixel).
  - Trimmed the active-channel caption (the colorbar now carries the range; dropped
    the range numbers and the colormap name as engineer-facing noise, per the
    review's "things to remove").
- **Verified on the real CdO measurement** (offscreen): O2 amplitude opens at its
  robust range with the histogram/colorbar; switching to Z updates levels to nm and
  the colormap to afmhot; Full-range widens 712..913 -> 680..966 nm; the readout
  sits under the image.
- **Tests (+7; 107 total):** `viz.level_range` (default vs full, guards) and
  GUI-level checks that levels match the channel default on load, update on channel
  switch, that Full-range widens and Default restores, that manual levels apply, and
  that **changing contrast never modifies the Dataset** (arrays unchanged + still
  frozen). `ruff` clean, `mypy --strict` clean (40 files), `pytest` 107 passed.

### Decisions
- **`ChannelImageView` rebuilt around a `GraphicsLayoutWidget`** (image + histogram
  + readout in one graphics scene); the histogram item owns the image LUT/levels, so
  the widget no longer sets them directly. Contrast modes live in Qt-free `viz`
  (tested); the widget is still thin (Rule 4) and earns its place under Rule 9
  (every element improves quantitative interpretation).
- **Axis tick labels in um, all data/levels/readout in nm**, as before; the colorbar
  axis shows the channel unit (a.u. / rad / nm) with SI auto-prefix disabled.

### Issues Found
- None. The level-sync between histogram drag, the spin boxes, and the buttons uses
  a single re-entrancy guard to avoid feedback loops; verified by the round-trip of
  Default -> Full -> Default restoring the exact default levels.

### Documentation Updated
- Created: (none new) - extended `src/snomniman/viz/render.py` (`level_range`),
  `src/snomniman/gui/imageview.py` (rewrite), `src/snomniman/gui/window.py`
  (readout -> image, trimmed caption); `src/snomniman/viz/__init__.py` exports;
  `tests/test_viz_render.py`, `tests/test_gui_window.py`. Updated `.gitignore`
  (ignore the sample folder). This `LOG.md` entry; `NEXT.md`.

### Next Recommended Actions
Per the v0.1 review, the next Must-haves (still pre-processing): **multi-channel
comparison** (side-by-side + synchronized cross-channel cursor + harmonic contact
sheet), then **line profile + ROI statistics**, then **provenance-preserving
export**. Recommended before more building: real user validation (watch 2-3 neaPLOT
users narrate). Re-run the product review as `product-review-v0.2.md` once these
land and watch the obstacle list shrink.

---

## 2026-06-26 - Comparative exploration (side-by-side, synced cursor, contact sheet)

Implemented the next Must-have from the v0.1 review: make comparison effortless,
because near-field analysis is fundamentally comparative. Strictly read-only - no
processing, AI, derived datasets, or export. ("Explore before you process.")

### Completed
- **Model (Qt-free, tested):** `PaneSpec` (channel + representation), four
  comparison presets (`comparison_layout`): Amplitude/Phase, Optical/Topography,
  Sample/Reference, Harmonic series - each anchored on the current channel and
  degrading gracefully when a channel is absent; `harmonic_panes()` (optical orders
  for the contact sheet); `values_at(specs, x, y)` - the synchronized-cursor readout
  reporting every visible channel's value at one physical point; `render_spec`.
  Refactored the value/nearest-pixel helpers so single- and comparison-mode readouts
  share one implementation.
- **`ChannelImageView` gained a `compact` mode** (for comparison panes): drops the
  histogram/contrast bar/readout strip, adds a pane title and a crosshair, plus
  `link_view` (shared zoom/pan) and `set_crosshair`. Full single-view mode is
  unchanged (colorbar/histogram/contrast/readout).
- **`snomniman.gui.comparison` (new):** `ComparisonView` - a grid of compact panes
  with **synchronized zoom, pan and cursor** (one crosshair marks the same physical
  point in every pane) and a single shared readout; `ContactSheet` - a clickable
  thumbnail of every harmonic for orientation (click selects that channel).
- **Window integration:** a view-control row (Single | the four Compare presets |
  Contact sheet) over a `QStackedWidget` (single / comparison / contact). Selecting a
  channel (browser or thumbnail) returns to the single detailed view.
- **Verified on the real CdO measurement** (offscreen): Amplitude/Phase shows O2
  amplitude (viridis) beside O2 phase (twilight) with the crosshair on the same
  particle in both and a shared readout (`O2 amplitude 5.756 a.u. / O2 phase 2.718
  rad`); Optical/Topography pairs O2 + Z; the contact sheet shows O0..O5 at a glance
  (O2/O3 strong contrast, O5 noise) - directly answering "which harmonic best reveals
  my sample?".
- **Tests (+17; 124 total):** model preset/`values_at`/contact-set logic (Qt-free,
  run in CI) and GUI checks for correct pane pairing, **synchronized zoom/pan**,
  **synchronized cursor** (crosshair in every pane + shared readout), contact-sheet
  build + navigation, return-to-single, and that **no comparison interaction mutates
  the Dataset**. `ruff` clean, `mypy --strict` clean (42 files), `pytest` 124 passed.

### Decisions
- **One image widget, two modes.** Rather than a parallel light pane class,
  `ChannelImageView` gained a `compact` flag - reuses the tested render path; the
  panes stay thin and earn their place under Rule 9 (each improves comparison).
- **Comparison view-state derivation lives in the Qt-free model** (presets,
  `values_at`), so the headline logic is unit-tested without a display; the widgets
  are pure presentation (Rule 4). Presets anchor on the current channel and only
  include channels that exist.
- **Contact sheet reuses `harmonic_panes()`** (DRY with the Harmonic-series preset);
  thumbnails are axis-free and non-interactive except a click-to-select.

### Issues Found
- None. Synchronized navigation uses PyQtGraph view-linking (`setXLink`/`setYLink`);
  the synchronized cursor is driven model-side (`values_at`) so it is exact and
  tested. No scientific logic leaked into widgets.

### Documentation Updated
- Created: `src/snomniman/gui/comparison.py`; `tests/test_gui_comparison.py`.
- Updated: `src/snomniman/gui/{model,imageview,window}.py`;
  `tests/test_gui_model.py`. This `LOG.md` entry; `NEXT.md`.

### Next Recommended Actions
Remaining read-only Must-haves before processing: **line profile + ROI statistics**,
then **provenance-preserving export**. Then the first processing derivations
(leveling, reference normalization) as explicit, recorded steps. Strongly recommended
first: real user validation. Re-run the review as `product-review-v0.2.md`.

---

## 2026-06-26 - Quantitative measurement tools (line profiles, distance, ROI stats)

The Explorer becomes a measurement instrument: a researcher can ask "how wide /
how tall / what is the profile / what are the statistics of this region" without
changing anything. Measurements are read-only *observations*, not processing -
they never touch the Dataset and create no derived datasets.

### Completed
- **`snomniman.viz.measure` (new, Qt-free, validated with known answers):**
  `sample_line` (bilinear profile along a segment), `distance`, `rect_mask`,
  `polygon_mask` (even-odd ray casting), `region_stats`
  (count/area/mean/median/min/max/std), `pixel_area`. Physical points map to
  fractional pixel indices by interpolation against the canonical coordinate axes,
  so offset/non-square grids are handled. 10 known-answer tests (Rule 6).
- **Model methods (Qt-free, tested):** `line_profile(specs, p0, p1) -> ProfileSet`,
  `rect_statistics` / `polygon_statistics -> RegionReport`, `pixel_area_nm2`,
  `single_view_specs` (the channels a single-view measurement reports: current +
  phase + topography). Each computes across every visible channel.
- **`snomniman.gui.measurement` (new):** `MeasurementController` places draggable,
  distinctly-styled (amber) line / rectangle / polygon overlays on the single
  image, recomputes results **live** while dragging via the model, and owns a
  session **history** (rename / hide / delete / clear). `MeasurementPanel` shows
  the active measurement's **profile plot** (one normalized curve per visible
  channel + a colored legend with each channel's real range) with the line's
  length / dx / dy, or a **statistics table** (per-channel mean/median/min/max/std)
  with the region's pixel count and area. Added as a "Measure" tab in the right dock.
- **Survives channel changes + read-only:** measurements persist and recompute for
  the new channel; placing one focuses the single view (the measurement surface).
- **Verified on the real CdO measurement** (offscreen): a line reads 12700 nm with
  O2-amplitude / O2-phase / Z profiles; a rectangle reports 5152 px, ~22.9 um^2,
  with means O2 amplitude 6.18 a.u., O2 phase 2.50 rad, **Z height 835.9 nm** -
  directly answering how-large / how-tall / profile / region-statistics.
- **Tests (+22; 146 total):** `viz.measure` known-answer math; model
  profile/statistics (values match the channel, area = count x pixel area); GUI
  placement (line profiles every visible channel; rect/polygon stats), history
  rename/hide/delete, focus-on-add, survive-channel-change, and that **no
  measurement modifies the Dataset**. `ruff` clean, `mypy --strict` clean (46
  files), `pytest` 146 passed.

### Decisions
- **Measurement != processing (philosophy made concrete).** Measurements extract
  information; processing derives new data. This milestone stays entirely on the
  read-only side: no Dataset mutation, no provenance nodes, no derived datasets -
  measurements are session-scoped exploration artifacts.
- **The validated math lives in Qt-free `viz.measure`** (Rule 6), the orchestration
  in the Qt-free model, the interaction in the widget (Rule 4). Overlays use a
  distinct amber pen so a measurement never reads as data.
- **Scope: measurements are placed on the single image** (one clear measurement
  surface) and report across the single view's channels (amplitude + phase +
  topography), which satisfies "for every visible channel". Mirroring an overlay
  into each comparison pane is a deliberate later refinement (the multi-channel
  results are already present); recorded in `NEXT.md`.

### Issues Found
- A benign PySide6/pyqtgraph teardown message ("C++ object already deleted") is
  emitted from an `atexit` callback during interpreter shutdown after the GUI
  tests; it is ignored (does not affect results or exit code).

### Documentation Updated
- Created: `src/snomniman/viz/measure.py`; `src/snomniman/gui/measurement.py`;
  `tests/test_viz_measure.py`; `tests/test_gui_measurement.py`.
- Updated: `src/snomniman/viz/__init__.py`, `src/snomniman/gui/{model,imageview,
  window}.py`; `tests/test_gui_model.py`. This `LOG.md` entry; `NEXT.md`.

### Next Recommended Actions
The read-only exploration set is now broad (understand -> compare -> measure). The
last read-only Must-have is **provenance-preserving export** of the current view
(captioned figure + the numbers, not a screenshot). After that the project is
**ready for processing derivations** - leveling, reference normalization, explicit
phase unwrap - each an explicit, recorded, non-destructive step that returns a new
Dataset whose provenance appends one StepRecord (OHD-2/5/6D); the Zarr store already
persists the resulting DAG. Strongly recommended first: real user validation, then
`product-review-v0.2.md`.

---

## 2026-06-26 - Provenance-preserving publication export (read-only Explorer COMPLETE)

A publication figure is one of the most important *derivations* of a measurement,
so it must never become an orphan. This adds figure export that carries complete
provenance and is regenerable from the original measurement. Read-only: a figure
only shows data (fetched from the immutable Dataset at render time), never changes
it. This **completes the read-only Explorer** (understand -> compare -> measure ->
communicate).

### Completed
- **`snomniman.viz.figure` (new, Qt-free, matplotlib):** a serializable
  `FigureSpec` (panels with channel/representation/colormap/levels/units, shared
  extent, scale bar, measurement overlays, conventions, source path+sha256,
  SNOMNIMAN + software versions, timestamp) with `to_dict`/`from_dict`;
  `render_figure` (standalone `Figure` + Agg canvas - panels via imshow with the
  lower-left convention, per-panel colorbar with units, scale bar, title; amber
  measurement overlays; a normalized **profile subplot** for measurement figures);
  `export` (saves the figure + a `<name>.provenance.json` sidecar);
  `render_from_record` (regenerates the figure from a saved record);
  `provenance_record` / `provenance_caption`.
- **Model:** `figure_spec(panels, overlays, *, kind, title)` builds the spec from
  the current view, filling colormap/unit/extent/conventions/source/versions from
  the dataset (Qt-free, tested).
- **Controller:** `overlay_specs()` reads the visible measurements' geometry into
  `OverlaySpec`s for drawing on the figure.
- **GUI:** an "Export figure..." control gathers the current view's panels (single /
  comparison / harmonic series) + their display levels + measurement overlays,
  builds the spec, and saves via a file dialog (PDF / PNG / SVG) + the provenance
  sidecar.
- **Presets via the current view:** single panel, comparison, harmonic series, and
  a measurement figure (panel + overlay + profile subplot) all fall out of which
  view is active and whether measurements exist.
- **Verified on the real CdO measurement:** a measurement figure (O2 amplitude +
  line overlay + profile subplot, 2 um scale bar, a.u. colorbar) and a 3-panel
  comparison (O2 amplitude / O2 phase twilight / Z afmhot, each with a titled
  colorbar in correct units) render at publication quality; the provenance caption
  records measurement + sha256, panels + colormaps + ranges, overlays, conventions,
  software versions and timestamp.
- **Tests (+11; 157 total):** figure spec JSON round-trip; render produces the
  expected axes for single/comparison/measurement layouts; provenance record +
  caption content; **reproducibility** (regenerate from the saved record); export
  writes the figure + provenance and **does not mutate the Dataset**; model
  `figure_spec`; and a GUI export smoke test (file dialog stubbed). `ruff` clean,
  `mypy --strict` clean (48 files), `pytest` 157 passed.

### Decisions
- **The provenance record is the FigureSpec.** Reproducibility = keep the original
  measurement + the saved spec, then `render_from_record`. The figure file (PDF/
  PNG/SVG) is the self-contained visual; the JSON explains and regenerates it.
- **Export lives in `viz`** (the architecture's home for "matplotlib export for
  publication figures"); the GUI only gathers the current view and calls it. Pure
  matplotlib `Figure` + Agg (no pyplot global state, no Qt) so it is headless and
  tested. Added `mpl_toolkits.*` to the mypy missing-stub overrides
  (`AnchoredSizeBar`).
- **Export is observational, not transformational** - no Dataset mutation, no
  provenance DAG node, no derived dataset. A figure is a recorded derivation in the
  philosophical sense, captured here as a self-describing artifact + sidecar.

### Issues Found
- None. matplotlib 3.11 renders crisp text headless (its own font stack), so the
  exported figures are fully legible (unlike the Qt offscreen screenshots).

### Documentation Updated
- Created: `src/snomniman/viz/figure.py`; `tests/test_viz_figure.py`.
- Updated: `src/snomniman/viz/__init__.py`; `src/snomniman/gui/{model,measurement,
  window}.py`; `tests/test_gui_model.py`, `tests/test_gui_window.py`;
  `pyproject.toml` (mypy override). This `LOG.md` entry; `NEXT.md`.

### Next Recommended Actions
**The read-only Explorer is complete** (understand / compare / measure / publish),
all without ever changing the measurement. The project is now genuinely **ready for
processing derivations** - leveling, reference normalization, explicit phase unwrap -
the first features that create a *recorded* derivation: each returns a new Dataset
whose provenance appends one `StepRecord`, never silent (OHD-2/5/6D); the Zarr store
already persists the resulting DAG, and `figure_spec`/provenance can later cite the
processing node. Strongly recommended first: real user validation, then
`product-review-v0.2.md`.

---

## 2026-06-26 - Processing engine framework

The generic machinery that every future scientific derivation will use. This
establishes the pattern before any algorithm: subclass, register, validate,
apply - and every result carries complete provenance automatically. No
scientific algorithms implemented (by design: the framework comes first).

### Completed
- **`ProcessingError` added to `snomniman.core.exceptions`** and exported from
  `snomniman.core`. Architecture.md already listed it as a core exception; it
  was not yet defined.
- **`snomniman.processing.step` (new):** `ParameterSpec` frozen dataclass
  (`name`, `description`, `py_type`, `required`, `default`) and `ProcessingStep`
  ABC. The ABC provides: `__init__(**params)` with `validate()` (checks unknown
  names, types, missing required); `apply(inputs)` which calls `_execute()`,
  builds the `StepRecord` + `ProvenanceNode` (UUID node_id, named inputs,
  software versions, UTC timestamp), and constructs the immutable output
  `Dataset` with `source=None`; `_execute()` abstract, returning
  `(xr.Dataset, DataKind, Metadata)`. Class variables `step_id`, `version`,
  `description`, `deterministic` declared on the ABC; defaults provided for
  `version=1` and `deterministic=True`.
- **`snomniman.processing.registry` (new):** `register(cls)` (decorator or
  direct call; guards against missing `step_id`/`description` and duplicate
  registration), `get_step(step_id)` (raises `ProcessingError` on unknown),
  `list_steps()` (sorted list). Module-level `_REGISTRY` dict; no entry-point
  discovery (Rule 7).
- **`snomniman.processing.__init__` (updated):** exports `ParameterSpec`,
  `ProcessingStep`, `register`, `get_step`, `list_steps`.
- **`docs/processing-engine.md` (new):** processing philosophy, operation
  lifecycle, parameter system, preview model, provenance integration, extension
  model (template code), dependency rules, and explicit scope boundaries (no
  algorithms, no GUI, no AI, no pipeline replay).
- **Tests (+39; 196 total):** `tests/test_processing.py`. Four synthetic
  operations (`_AddConstant`, `_ScaleOptional`, `_NoParams`, `_CombineAdd`)
  exercise the framework without touching the global registry (monkeypatch
  fixture isolates state). Tests cover: registration/list/lookup; duplicate-
  registration and unknown-step guards; missing-step_id and missing-description
  guards; parameter validation (valid, missing required, wrong type, unknown);
  no-params and optional-params patterns; multi-type params (`(int, float)`);
  `validate` as standalone classmethod; `apply` returns Dataset; input arrays
  unchanged and still frozen after apply; empty-inputs guard; result values
  differ from input; step_id/version/params/deterministic/software all recorded;
  inputs map references parent provenance nodes; is_raw=False for derived;
  source=None for derived; multi-input (both nodes named); chained steps build
  a 3-node DAG; UUID node_ids are unique across calls; params JSON-serializable;
  params JSON round-trip; provenance DAG serializes/deserializes after a step;
  chained DAG serializes to 3 nodes.
- **Gates green:** `ruff` clean, `mypy --strict` no issues (51 files),
  `pytest` 196 passed, backend Qt-free invariant still holds.

### Decisions
- **`ParameterSpec.py_type` is always a tuple** (`tuple[type[Any], ...]`).
  Single-type params use a one-element tuple (`(float,)`); multi-type params
  use `(int, float)`. This makes isinstance calls mypy-clean with no casts or
  ignores, and keeps the field semantics unambiguous.
- **UUID node_ids** for processing steps (the reader uses `"n0"`; processing
  steps generate `str(uuid.uuid4())`). Node IDs are opaque identifiers; UUID
  ensures they are globally unique across calls.
- **`source=None` for all derived Datasets.** Only raw-import Datasets carry a
  `RawSource`; derived datasets reference their ancestry through the provenance
  DAG, not through the source field.
- **Registry is module-level state; test isolation via monkeypatch.** Rather
  than a dependency-injected registry object, the global `_REGISTRY` dict is the
  canonical registry, and tests patch it with `monkeypatch.setattr`. This keeps
  production code clean and tests isolated.

### Issues Found
- None. The framework design (ClassVar attributes, validate classmethod,
  functional apply, UUID node_ids) worked cleanly with `mypy --strict` and the
  test suite on the first pass.

### Documentation Updated
- Created: `src/snomniman/processing/step.py`;
  `src/snomniman/processing/registry.py`; `docs/processing-engine.md`;
  `tests/test_processing.py`.
- Updated: `src/snomniman/core/exceptions.py` (ProcessingError);
  `src/snomniman/core/__init__.py` (export ProcessingError);
  `src/snomniman/processing/__init__.py` (exports). This `LOG.md` entry;
  `NEXT.md`.

### Next Recommended Actions
**The processing engine is ready.** The next step is implementing the first
real processing derivation using this framework. Recommended starting point:
`image.plane_level` - polynomial plane fit and subtraction on the topography
(Z) channel. Validate with a synthetic tilted-plane dataset that has a known
analytical answer (Rule 6). After that: `image.reference_normalize`
(sample / reference complex division, OHD-6D). Each operation is a concrete
`ProcessingStep` subclass; no new framework code needed.

---

## 2026-06-26 - First processing derivation: image.plane_level + Explorer preview/navigation

Implemented the first production processing operation and integrated it into
the Explorer as a full Preview → Accept/Cancel → Back navigation workflow.

### Completed
- **`snomniman.processing.image.plane_level` (new):** `PlaneLevel` step
  (`step_id="image.plane_level"`, `version=1`, `deterministic=True`) using
  ordinary least squares via `numpy.linalg.lstsq`. Parameters: `channel` (str,
  default `"Z"`) and `order` (int 1-3, default 1). The design matrix supports
  order 1 (plane, 3 coefficients), order 2 (paraboloid, 6), and order 3 (10).
  `fit_surface()` is exported separately for direct use and tests.  The step
  validates order range (1-3) in its `validate()` override - error raised at
  construction time, not at apply time. `@register` decorator registers
  `PlaneLevel` in the global step registry when the module is imported.
  Sub-package `snomniman.processing.image` created with `__init__.py` that
  re-exports `PlaneLevel`.
- **`PaneSpec.label` (model.py):** Added optional `label: str | None = None`
  field to `PaneSpec` (frozen dataclass, backward-compatible). When set,
  `title` returns the label instead of the auto-generated channel+representation
  string. Used by the preview comparison to show "Z (original)" vs
  "Z (leveled, order 1)".
- **`_step_description` for `"image.plane_level"`** (model.py): Added human
  description used in the Provenance inspector tab.
- **`MeasurementController.set_model` (measurement.py):** New method that
  clears all session measurements and updates `_model`/`_specs` to a new
  `ExplorerModel`. Called when the window switches to a derived model after
  accepting a derivation.
- **`snomniman.gui.process.ProcessPanel` (new):** Thin panel (Rule 4 - no
  science) with a channel selector (real-valued channels only), an order
  SpinBox (1-3), and three buttons: "Preview" → emits `previewRequested(channel,
  order)`; "Apply" (preview mode only) → emits `previewAccepted()`; "Cancel"
  (preview mode only) → emits `previewCancelled()`. `set_channels(channels)` and
  `set_preview_mode(active)` are the public interface.
- **Explorer window (window.py) - processing workflow:**
  - `_on_preview_requested(channel, order)`: runs `PlaneLevel.apply()` on the
    current model's dataset, builds a temporary `ExplorerModel` for the preview,
    creates two labeled `PaneSpec` objects ("original" vs "leveled"), shows
    them in `ComparisonView` via `renders.__getitem__` (pre-computed RenderData
    dict), calls `_process.set_preview_mode(True)`.
  - `_on_preview_accepted()`: wraps the preview Dataset in a new
    `ExplorerModel` with title `"<old title> → plane leveled (<channel>)"`,
    calls `_update_model(new_model)` to push old model to history.
  - `_on_preview_cancelled()`: discards the preview, calls `_show_single()`.
  - `_update_model(new_model, push_history=True)`: replaces `self._model`,
    calls `_measure.set_model(new_model)`, `_refresh_navigation()`, `_load()`.
  - `_navigate_back()`: pops the history stack, calls `_update_model(prev,
    push_history=False)`.
  - `_refresh_navigation()`: shows/hides `_back_btn` and updates its text
    (`"← Back to <prev title>"`).
  - `_real_channels()`: filters the current model's channels to real-valued only
    (used to populate the process panel selector).
  - `_back_btn`: a `QPushButton` in the view controls bar (leftmost, initially
    hidden). `_process`: `ProcessPanel` added as "Process" tab in the inspect
    dock (after Metadata, Provenance, Measure).
- **Validate on real CdO data (golden, manual):** The plane level preview opens
  the CdO measurement's Z channel (topography, ~400-1200 nm range with
  significant tilt), computes the polynomial surface, and the comparison view
  shows both panes correctly. Accept switches to the derived model (title
  updates; back button appears). Back navigation restores the raw measurement.
- **Tests (new):**
  - `tests/test_processing_image.py` (23 tests): 3 fit_surface known-answer
    tests (plane, paraboloid, cubic residuals ≈ 0 analytically); 2 PlaneLevel
    correctness tests (tilt removed, paraboloid removed); 5 immutability /
    channel isolation tests; 5 provenance tests; 2 default-parameter tests;
    4 validation tests (order 0, order 4, missing channel, complex channel);
    1 registry test.
  - `tests/test_gui_process.py` (33 tests): panel existence + tab membership;
    channel selector shows Z not O2/O3/M1; preview switches to comparison view,
    shows 2 panes with labels, doesn't change model, disables preview button;
    cancel restores single view without model change; accept updates model,
    records step_id/params, returns to single view, restores buttons; back
    button hidden initially, appears after accept (with prev title in text),
    hidden after back; navigate back restores original model and clears history;
    cardinal immutability invariants through full accept + back cycle.
- **Gates green:** `ruff` clean, `mypy --strict` no issues (56 files),
  `pytest` 245 passed, backend Qt-free invariant holds.

### Decisions
- **`processing.image` NOT auto-imported from `processing/__init__.py`.**
  The circular-import risk (and ruff import-sort conflict) outweigh the
  convenience of auto-registration. Sub-packages must be imported explicitly
  by callers that need their operations. The window imports `PlaneLevel`
  directly (`from snomniman.processing.image.plane_level import PlaneLevel`)
  in `_on_preview_requested`; the test file imports it at the top. Pipeline
  replay (future) will handle bulk registration.
- **Preview uses pre-computed `RenderData` dict (`renders.__getitem__`).**
  The `ComparisonView.set_panes(specs, renderer)` renderer is supplied as
  `dict.__getitem__` on a pre-built `{PaneSpec: RenderData}` dict. Clean,
  ruff-compliant, no lambda assignment.
- **History stack is linear (back = undo one step).** The "Back" button pops
  exactly one entry. Deeper history is trivially supported by the same mechanism
  as more operations are chained.
- **Comparison cursor during preview shows original-model values for both
  panes.** Both preview specs share `channel="Z"`; `values_at` queries the
  original model for both. This is a known, acceptable limitation of the first
  iteration - the preview is primarily visual. A future improvement would split
  the cursor readout between original and derived models.

### Issues Found
- **ruff E731 (lambda assignment):** Replaced `renderer = lambda s: renders[s]`
  with `renders.__getitem__` - cleaner and ruff-compliant.
- **Qt `isVisible()` unreliable for non-shown widgets:** `isVisible()` requires
  the full ancestor chain to be visible. Fixed GUI tests to use
  `widget.testAttribute(Qt.WidgetAttribute.WA_WState_Hidden)` via the
  `_is_shown()` helper (checks the widget's OWN explicit hide state, not
  ancestors).

### Documentation Updated
- Created: `src/snomniman/processing/image/__init__.py`;
  `src/snomniman/processing/image/plane_level.py`;
  `src/snomniman/gui/process.py`;
  `tests/test_processing_image.py`; `tests/test_gui_process.py`.
- Updated: `src/snomniman/processing/__init__.py` (comment + remove image
  auto-import); `src/snomniman/gui/model.py` (PaneSpec.label, _step_description);
  `src/snomniman/gui/measurement.py` (set_model); `src/snomniman/gui/window.py`
  (process panel, history, preview/accept/cancel/back); `LOG.md`; `NEXT.md`.

### Next Recommended Actions
The derivation workflow is now a template other operations can follow. The
next processing derivation is `image.reference_normalize` (sample / reference
complex division, OHD-6D): `step_id="image.reference_normalize"`, takes two
inputs (`"sample"` and `"reference"`), divides complex channel by reference
channel. After that, a plausible third would be `image.phase_unwrap`. The
Explorer workflow (Process panel → Preview → Accept/Cancel → Back) already
handles single-input steps; reference normalization would require a "pick
reference" UI in the Process panel. No framework changes needed - the
multi-input `apply({"sample": ds, "reference": ref_ds})` contract is already
implemented.

---

## 2026-06-26 - Scientific Description API (snomniman.describe)

A new Qt-free backend layer that projects the scientific core + the processing
registry into structured, JSON-serializable descriptors. Built deliberately for
*present-day* consumers (Explorer, export, reports, debugging, tests), not for a
future AI - AI will simply be one more client of the same API (Rule 7). No AI, no
LLM, no prompts, no new processing algorithms; the processing engine is unchanged.

### Completed
- **`snomniman.describe` (new package):**
  - `descriptors.py` - ten frozen, JSON-serializable value objects with `to_dict()`:
    `ChannelDescription`, `ConventionsDescription`, `GeometryDescription`,
    `MetadataSummary`, `SourceDescription`, `LineageStep`, `ProvenanceSummary`,
    `OperationParameter`, `OperationDescription`, and the aggregate
    `MeasurementDescription`. Honest values (`None` for unknown - never an
    "unknown" placeholder; formatting is a consumer concern).
  - `summarize.py` - pure, read-only projection functions: `describe_channels`,
    `summarize_metadata`, `summarize_provenance` (walks the DAG topologically),
    `describe_operations` / `describe_operation` (the registry catalogue), and
    `describe_measurement` (the one-call aggregate). No computation, no mutation.
  - Depends on `core` + `processing` only (the `pipeline` tier); Qt-free.
- **First live consumer wired:** `ExplorerModel.provenance_summary` /
  `provenance_steps` now source their facts from `describe.summarize_provenance`
  and only format the wording (backend owns the facts, the GUI owns the words).
  Output is byte-identical, so the existing GUI tests pass unchanged - evidence the
  seam is not shelfware.
- **Qt-free invariant extended:** `snomniman.describe` added to `BACKEND_PACKAGES`
  in `tests/test_smoke.py`, so the subprocess check guards it.
- **Tests (+11; 256 total):** `tests/test_describe.py` - channel/metadata/
  provenance projections on the synthetic dataset; raw vs post-`PlaneLevel`
  lineage; the operation catalogue (registry isolated via monkeypatch) + the real
  `image.plane_level` schema; the aggregate; a JSON round-trip; the cardinal
  non-mutation invariant (describing never changes the dataset, arrays stay frozen);
  and a golden test on the real CdO measurement (capabilities, channel count,
  directory-source sha256, full JSON-serializability).
- **Gates green:** `ruff` clean, `mypy --strict` no issues (60 files), `pytest`
  256 passed, backend Qt-free invariant holds.

### Decisions
- **ADR-0018 (new): the Scientific Description API.** A read-only projection layer,
  justified by present-day consumers, not by future AI. Named for what it does
  (description/introspection) - explicitly **not** a "Knowledge Layer" / "Reasoning
  Layer" (it does no reasoning) - and it excludes GUI/Explorer state and all
  AI-specific concepts. Alternatives rejected: defer until the first AI feature
  (the consumers exist today); a broader AI-oriented "Knowledge Layer" (speculative,
  Rule 7); introspection on `Dataset` itself (the operation catalogue needs
  `processing`, which `core` must never import).
- **`viz` deliberately does not consume `describe`.** `viz` stays `core`-only (it
  sits below `processing`); figure export keeps building its provenance record
  directly from the `Dataset`. `describe` is for consumers already above
  `processing` (`gui`, `batch`, future `ai`).
- **Summary, not archive.** `MetadataSummary` omits the verbatim vendor header and
  other bulk; the full `Metadata` / `Dataset` remain the source of truth.
- **Scope held (user direction).** The original "Knowledge Layer" brief was
  rescoped and renamed before any code; "Explorer state" was dropped (it would
  invert the dependency graph / pull Qt into the backend, Rule 4). The architectural
  pushback was explicitly requested and endorsed by the user.

### Issues Found
- **Honest limitation (documented, not fixed here):** per-dataset operation
  *applicability* is shallow - `describe_operations()` lists the catalogue but does
  not precisely answer "which apply to *this* dataset", because `ProcessingStep`
  does not declare required capabilities as data (e.g. `PlaneLevel` enforces
  "real-valued channel" internally). Deepening that is a separate, future refinement
  to the processing engine and was intentionally out of scope (this layer consumes;
  it must not modify the engine).
- No architecture issues. The layering, OHDs, and ADRs held; the new layer slots in
  at the `pipeline` tier with no cycle and no Qt.

### Documentation Updated
- Created: `src/snomniman/describe/{__init__,descriptors,summarize}.py`;
  `tests/test_describe.py`; `docs/description-api.md`.
- Updated: `src/snomniman/gui/model.py` (provenance via `describe`);
  `tests/test_smoke.py` (Qt-free list); `docs/decisions.md` (ADR-0018);
  `docs/architecture.md` (the `describe` layer + AI-layer note); `CLAUDE.md` (status,
  architecture summary, module list, Qt-free list, doc-hierarchy row); this `LOG.md`
  entry; `NEXT.md`.

### Next Recommended Actions
The description seam now exists and has a live consumer. Per the agreed roadmap, the
next high-leverage work is **more processing operations** (so there is more for a
future AI to reason about, and more for `describe_operations` to expose): start with
`image.reference_normalize` (multi-input sample / reference complex division,
OHD-6D), then `image.phase_unwrap` (first-class unwrapped-phase channel, OHD-4). A
natural, separately-justified refinement that would deepen `describe`: have
`ProcessingStep` declare `required_capabilities` as data, enabling precise
per-dataset applicability. **AI remains deliberately deferred** until the operation
set is rich enough to orchestrate - at which point it consumes `snomniman.describe`
without an architectural redesign.

---

## 2026-06-26 - Scientific Diagnostics Engine (snomniman.diagnostics)

The first subsystem that *measures the measurement*: deterministic, reproducible,
scientifically defensible facts about a dataset, computed once in a Qt-free backend
and surfaced in the Explorer. This is the factual foundation a future AI Scientist
will reason over - but it ships justified by a present-day consumer (the Explorer's
Diagnostics panel, Rule 9), not by the AI (Rule 7).

### Decisions (the forks, settled with the user)
- **Wire into the Explorer this milestone**, not backend-only. A diagnostics package
  whose only consumer is a future AI is the speculative-infrastructure trap; the
  Explorer makes it earn its place today.
- **Defensible facts only (Rule 6).** Ship tilt, height range, RMS roughness,
  per-channel statistics, dynamic range, invalid-pixel counts, and harmonic
  amplitude decay. **No SNR** (needs a noise model / signal-free region), **no
  clipping** (needs an ADC limit absent from metadata), **no drift** (ill-posed from
  one image). Deferred, not guessed. Decay ratio replaces "SNR" as an honest proxy.
- **Extend `ProcessingStep` now.** Steps declare `required_capabilities`
  (implementing the ADR-0017 hybrid-dispatch intent the docstring already promised);
  `image.plane_level` declares `SPATIAL_2D`. Applicability is now a data-driven fact.
- **Sibling of `describe`, not an input to it.** `describe` stays a pure projection
  (ADR-0018 intact); consumers compose description + diagnostics. (The original
  prompt suggested folding diagnostics into the Description API; rejected to preserve
  the no-computation contract.)

### Completed
- New package `snomniman.diagnostics` (`descriptors.py` + `diagnose.py`): frozen,
  JSON-serializable descriptors (`ChannelStatistics`, `TopographyDiagnostics`,
  `HarmonicDiagnostics`/`HarmonicAmplitude`, `OperationApplicability`,
  `MeasurementDiagnostics`) and pure functions (`channel_statistics`,
  `topography_diagnostics`, `harmonic_diagnostics`, `operation_applicability`,
  `diagnose`). Mirrors the `describe` descriptor pattern (`to_dict` + `_jsonify`).
- `ProcessingStep.required_capabilities` class field (default `()`), documented;
  `image.plane_level` declares `(Capability.SPATIAL_2D,)`.
- Explorer **Diagnostics tab** (`gui/diagnostics.py` `DiagnosticsPanel` +
  `ExplorerModel.diagnostics_report` formatting + `window` wiring). Backend computes,
  GUI formats (Rule 4).
- Updated the now-stale `describe.describe_operations` comment to point applicability
  at `diagnostics` (code/doc drift fixed).

### Validation (Rule 6 - known answers only)
- Synthetic tilted plane -> exact slope (per-um) and ~0 roughness after detilt.
- Constant field -> zero dynamic range; injected NaN/inf -> exact invalid counts.
- Harmonic decay ratio analytically equal to 1.0 on the fixture; reference/mechanical
  channels correctly excluded.
- Applicability: `image.plane_level` applicable to a 2-D image, inapplicable to a
  line scan (missing `spatial_2d`), and `already_applied` after a derivation.
- JSON round-trip and non-mutation invariants.

### Tests / gates
- 274 tests pass (was 256; +18 across backend diagnostics and the GUI panel).
  `snomniman.diagnostics` added to the Qt-free backend list in `test_smoke.py`.
  `ruff` clean; `mypy --strict` clean (66 source files).

### Documentation
- New `docs/diagnostics-engine.md`; ADR-0019 in `decisions.md`; `architecture.md`
  layer + module entry; `CLAUDE.md` status/stack/responsibilities/Rule-4 list/doc
  table; this entry; `NEXT.md` refreshed.

### Next recommended
- The project compass is now real: *every scientific operation and observation is
  deterministic; only interpretation is left to reviewable AI.* With diagnostics in
  place, the AI Scientist can finally be designed to **reason over verified facts**
  (`describe` + `diagnostics`) and emit reviewable recommendations the deterministic
  engine alone executes. Still gated behind a richer operation vocabulary
  (`image.reference_normalize`, `image.phase_unwrap`) - design-first, with an ADR.

---

## 2026-06-27 - AI Scientist v1: the Scientific Briefing (snomniman.ai)

The first AI capability - and deliberately the smallest, safest, most useful one:
**measurement orientation** ("tell me about this measurement"), not recommendations
and not execution. Everything built over the prior milestones now has a natural AI
consumer, and the AI reasons over validated facts instead of pixels.

### Decisions (the forks, settled with the user)
- **No model SDK this milestone.** Ship the deterministic Briefing + the provider
  *seam* only (protocol + grounded prompt builder + a network-free mock). A concrete
  provider (Anthropic/OpenAI/local) arrives later as an *optional* extra,
  lazy-imported, never required for backend/CI. Zero new dependency now (so no major
  dependency to justify beyond the new layer itself).
- **The briefing is always useful (deterministic fallback).** Facts always render;
  the optional AI narrative layers on top only when a provider is configured. Adopted
  as a permanent product principle: *AI enhances understanding; it never gates it.*
- **Renamed to "Scientific Briefing"** (not "AI Scientist") in the GUI - a briefing,
  not a chatbot: no input box, no history, no agent behaviour.

### Completed
- New Qt-free package `snomniman.ai` (depends on `describe` + `diagnostics` + `core`):
  - `report.py` - frozen, JSON-serializable `Briefing` / `BriefingSection` /
    `BriefingStatement` (kind=fact|interpretation, source-tagged) / `BriefingContext`
    (the exact describe+diagnostics payload = grounding + audit trail).
  - `provider.py` - `NarrativeProvider` Protocol, `MockNarrativeProvider`
    (network-free), `ORIENTATION_SYSTEM` + `build_orientation_prompt` (embeds the
    facts verbatim; forbids invention; testable offline).
  - `briefing.py` - `build_briefing(dataset, *, title, provider=None)` composing three
    deterministic fact sections (Measurement Summary, Scientific Observations, What
    This Measurement Enables).
- Explorer **Briefing tab** (`gui/briefing.py` `BriefingPanel` +
  `ExplorerModel.scientific_briefing` + window wiring): collapsible fact sections, an
  "Interpretation (AI)" area that shows a clear "no provider configured - facts are
  complete and authoritative" note in this build, and a "Copy briefing" action.
- Two permanent AI rules added to `CLAUDE.md` (reason only over deterministic facts;
  always have a deterministic fallback).

### Grounding (and an honest limitation)
- By construction: a provider receives ONLY the facts payload; the prompt forbids
  invention; the briefing stores `context` so any statement is auditable against it.
- NOT done: per-sentence machine verification of a free-text narrative (would need an
  NLI checker). Stated plainly in the docs rather than overclaimed; candidate future.

### Tests / gates
- 289 tests pass (was 274; +15 across `test_ai_briefing.py` and `test_gui_briefing.py`).
  `snomniman.ai` added to the Qt-free backend invariant. Deterministic facts asserted
  exactly; every fact statement checked to cite only description/diagnostics; provider
  seam exercised with the mock; prompt builder checked to embed facts + "do not
  invent"; JSON round-trip + non-mutation invariants. No external API in any test.
  `ruff` clean; `mypy --strict` clean (73 source files).

### Documentation
- New `docs/ai-scientist-v1.md`; ADR-0020 in `decisions.md`; `architecture.md` layer +
  module entry; `CLAUDE.md` status/stack/responsibilities/Rule-4 list/two AI
  rules/doc table; this entry; `NEXT.md` refreshed.

### Next recommended
- A concrete `NarrativeProvider` (optional `ai` extra, lazy import) so the
  interpretation renders when a key is configured - small, isolated change behind the
  existing seam. Separately, the deterministic operation vocabulary
  (`image.reference_normalize`, then `image.phase_unwrap`) so a *later* AI milestone
  can offer reviewable recommendations the deterministic engine alone executes.
  Design-first, with an ADR. Real-user validation still strongly recommended.

---

## 2026-06-27 - Scientific vocabulary: reference_normalize, phase_unwrap, crop

"Teach SNOMNIMAN more science, not more software." Three new deterministic
`ProcessingStep` operations, each a verb the whole system gains at once - they appear
automatically in the Description API catalogue, the Diagnostics applicability report,
and the AI Scientist's briefing with **zero changes to those layers** (proven by new
tests). No new infrastructure, no new abstractions; the architecture is treated as
complete.

### Completed (all in `snomniman.processing.image`)
- `image.reference_normalize` (req: `complex_optical` + `reference`) - divides each
  complex optical signal channel by its matching reference (`O{n}/R_O{n}`); amplitude
  -> ratio, phase -> difference. The phase re-reference is **explicit and recorded**
  (OHD-6D): `conventions.phase_reference` is updated; channel `state` -> normalized.
  Single-input (signal + reference live in one measurement), not the two-dataset case.
- `image.phase_unwrap` (req: `spatial_2d`; channel param) - appends an unwrapped-phase
  channel `{ch}_phase_unwrapped` (rad, state unwrapped, OHD-4); raw phase untouched
  (OHD-6D). 2-D unwrap = sequential `numpy.unwrap` x then y (no new dependency; exact
  for smooth fields, documented limitation on true 2-D residues).
- `image.crop` (req: `spatial_2d`; x/y min/max nm) - slices every channel to a
  rectangular region, preserves absolute coordinates, updates scan geometry
  (pixels/size/offset/center).

### Decisions
- **No `image.polynomial_flatten` (Rule 2).** `image.plane_level` already *is*
  polynomial surface flattening (orders 1-3); a separate polynomial_flatten would
  duplicate it. The genuinely-new flattening verb is `image.line_flatten` (per-scan-
  line subtraction) - proposed as next, not built as a duplicate.
- **GUI preview deferred deliberately.** The Explorer's Preview->Accept/Cancel flow is
  bound to `_on_preview_requested(channel, order)` with 30+ tests; exposing arbitrary
  operations needs a registry-driven, `param_specs`-built parameter form + per-op
  preview rendering - a real UI task (NEXT.md), not engine work. The new ops are
  first-class everywhere else today. (Respects "do not redesign the GUI".)

### Validation (Rule 6 - known answers)
- reference_normalize: `(O/R)*R == O` to complex64 precision; normalized phase ==
  `angle(O)-angle(R)`; state + phase_reference updated; missing-pair raises.
- phase_unwrap: analytical wrapped ramp recovered exactly (up to a constant); new
  channel added, raw retained; real channel rejected.
- crop: exact sub-region equality, geometry update (pixels/size/offset), empty-region
  and inverted-bounds errors.
- Propagation: explicit tests that all four ops appear in Diagnostics applicability
  AND the AI briefing's "What This Measurement Enables" with no diagnostics/AI change.
- Immutability + provenance step_id/params asserted for every op.

### Tests / gates
- 305 tests pass (was 289; +14 op tests +2 propagation tests). `ruff` clean;
  `mypy --strict` clean (77 source files); Qt-free invariant green.

### Documentation
- `docs/processing-engine.md` - new "Registered operations (the scientific
  vocabulary)" table + the polynomial_flatten/line_flatten Rule-2 note + Explorer
  exposure status. `docs/ai-scientist-v1.md` - vocabulary grows automatically.
  `CLAUDE.md` status (op list + 305). This entry; `NEXT.md` refreshed.

### Next recommended
- `image.line_flatten` (the genuinely-new flattening verb). Then the **generic
  operation panel** for the Explorer (registry + `param_specs`-driven form + per-op
  preview) so the new verbs are usable in the GUI. Then a concrete AI
  `NarrativeProvider` (optional extra). Design-first; real-user validation.

---

## 2026-06-27 - Generic, registry-driven Processing Workspace (ADR-0021)

Committed the scientific-vocabulary milestone (reference_normalize, phase_unwrap,
crop) as `feat(processing): add reference normalize, phase unwrap, and crop`, then
built the milestone the user identified as the real bottleneck: **not another
algorithm, but the universal interface to algorithms**. The Explorer's Process tab is
now one generic, registry-driven Processing Workspace that exposes *every* registered
operation. The plane-level-specific panel/wiring is gone; the next operation needs no
GUI code. No new architectural layer; the engine and Explorer were not redesigned.

### Completed
- **`ParameterSpec` UI hints (backend, `snomniman.processing.step`):** added two
  optional, defaulted fields - `choices` (a fixed enum; now also enforced by
  `validate()`) and `channel_role` (`CHANNEL_ANY`/`CHANNEL_REAL`/`CHANNEL_COMPLEX`,
  marking a `str` param as naming a channel of that kind). They are pure UI/validation
  hints - they never change a computed result. Annotated `image.plane_level.channel`
  (`real`) + `order` (`choices=(1,2,3)`, which let the redundant custom order-range
  `validate` override be removed - Rule 8) and `image.phase_unwrap.channel`
  (`complex`). Exported the channel-role constants from `snomniman.processing`.
- **Description API projection:** `describe.OperationParameter` gained `choices` +
  `channel_role`; `_describe_parameter` fills them - so the registry catalogue fully
  reports each operation's parameter schema (the GUI never re-reads `ParameterSpec`).
- **Presenter (`gui.model.ExplorerModel`, Qt-free) - the generic engine:** new
  view-objects (`OperationField`/`OperationOption`/`PreviewPane`/`OperationPreview` +
  `FIELD_*` kinds) and methods: `operation_catalog()` / `operation_option(step_id)`
  (project `describe_operations` + Diagnostics `operation_applicability` + the dataset
  into a grouped, available/explained list with a per-dataset, role-filtered parameter
  form), and `preview_operation(step_id, params)` (build the step, apply to
  `{"primary": ds}`, **diff** the derived vs current dataset to report generically what
  changes / what stays / the provenance to record). The diff is fully generic - no
  step_id is hardcoded; the added-channel "before" view is chosen from the new
  channel's own `derived_from`/`quantity` attrs. Refactored `provenance_steps` to share
  one lineage formatter, and `_step_description` now sources every operation's words
  from its registered `ProcessingStep.description` (single source of truth).
- **Widget (`gui.process.ProcessingWorkspace`, replaces `ProcessPanel`):** a thin,
  generic surface - a grouped operation tree (unavailable ops visible but disabled with
  a plain reason), an auto-generated parameter form (numbers -> spin boxes, `bool` ->
  checkbox, `choices` -> selector, `channel_role` -> filtered channel picker), one
  Preview/Accept/Cancel button set, and a preview panel showing the change summary +
  the provenance to be recorded. No operation-specific code; it maps field descriptors
  to controls and back, and emits intent signals.
- **Window wiring (`gui.window`):** replaced the plane-level handlers
  (`_on_preview_requested(channel, order)`) with generic ones routed through the model;
  the before/after still reuses the comparison view; history/back unchanged.
- **Verified** on the synthetic dataset (offscreen + a probe): all four ops appear
  grouped under "Image" with correct forms (plane_level -> real channel + order 1/2/3;
  phase_unwrap -> complex channel; crop -> four nm bounds; reference_normalize -> no
  params); each previews with an accurate, generic change summary (e.g. crop "restricts
  the field of view to 2x2 (was 4x3)"; reference_normalize surfaces the explicit phase
  re-reference, OHD-6D); the original Dataset stays frozen throughout.

### Decisions
- **ADR-0021** (generic, registry-driven Processing Workspace; no per-operation GUI).
  Key calls recorded there: UI hints belong on `ParameterSpec` not in the GUI (Rule 4 -
  "which channels an operation accepts" is scientific knowledge); "what changes" is
  computed by diffing the actual preview (generic, no per-op upkeep) rather than
  declared; no multi-input form yet (Rule 7 - no multi-input operation exists; the
  single-input `{"primary": ds}` convention covers every step); no new GUI abstraction
  layer (the registry + `ParameterSpec` + the Qt-free presenter already suffice).

### Issues Found
- Adding `choices=(1,2,3)` to `order` made `PlaneLevel.validate`'s range check
  redundant and would have changed its error message; removed the override and updated
  the two order-range tests to match the `choices` message (behaviour preserved:
  order outside {1,2,3} still rejected). No other regressions - the `describe`/JSON and
  AI/diagnostics tests passed unchanged (the new `OperationParameter` fields default to
  `None`).

### Tests / gates
- 318 total (up from 305; net +13): a new Qt-free
  `tests/test_gui_workspace_model.py` (21 tests - catalogue discovery, auto parameter
  forms, channel-role filtering, availability + disabled-operation explanations,
  preview content for all four ops, invalid-param errors, immutability) and a rewritten
  `tests/test_gui_process.py` (18 window-wiring tests - catalogue tree, form building,
  the Preview/Accept/Cancel lifecycle, history, and the *same* workflow driving
  phase_unwrap / reference_normalize / crop end-to-end), replacing the 26
  plane-level-specific tests. Added a shared `topography_dataset` fixture to
  `conftest.py`. `ruff` clean; `mypy --strict` clean (78 files); Qt-free invariant
  green.

### Documentation
- `docs/processing-engine.md` - documented `choices`/`channel_role`, the new
  `validate()` choices rule, a "Processing Workspace" section, and refreshed the
  preview-model + multi-input-example sections to match what shipped.
  `docs/measurement-explorer.md` - Section 7 "Realized" note (the Workspace implements
  "every operation is a derivation"; new operations inherit it). `docs/decisions.md` -
  ADR-0021. `CLAUDE.md` status (Workspace + 318). This entry; `NEXT.md` (task 24 done).

### Next recommended
- `image.line_flatten` (now nearly GUI-free: implement + register + declare
  params/capabilities and it appears in the Workspace automatically). Then a concrete
  AI `NarrativeProvider` (optional extra, its own ADR) - at which point the AI can
  recommend a registered operation and the Workspace already knows how to present it.

---

## 2026-06-27 - AI Suggested Next Steps (deterministic workflow recommendations, ADR-0022)

Committed the generic Processing Workspace (`feat(gui): generic registry-driven
Processing Workspace`), then built the capability the user identified as the moment the
project becomes unique: the AI Scientist now proposes *what to do next*. Opening a
measurement gives a grounded Briefing **and** a ranked list of Suggested Next Steps, each
of which Previews straight into the Workspace. This is the payoff of building the
Workspace first: an AI recommendation needs **no** special execution path.

The defining decision (ADR-0022): the recommendations are **deterministic**, not
LLM-generated. They are produced from `describe` + `diagnostics` (applicability,
topography tilt, channel states, provenance). This is what the two permanent AI rules
require - "is there a tilt worth removing?" is a fact the Diagnostics Engine computes
(rule 1), and deterministic suggestions are the always-available fallback (rule 2) - and
it makes the hard safety rules *structural*: a generator built from applicability cannot
suggest an unavailable or already-applied operation, where a prompt-constrained LLM
could.

### Completed
- **`snomniman.ai.recommend` (new):** `recommend_workflow(dataset) -> WorkflowSuggestions`
  + `Recommendation` / `RecommendationEvidence` (frozen, JSON-serializable, `to_dict`).
  One self-guarding deterministic rule per operation: **plane level** when a measured
  global tilt dominates the *signal* topography (confidence = fraction of the height's RMS
  variation from the tilt; pre-fills `{channel: Z, order: 1}`), and **reference normalize**
  when references exist and optical signals are still raw. Each recommendation carries
  pre-filled `params`, a heuristic `confidence` in [0,1] (documented as a priority, **not**
  a probability; surfaced as strong/moderate/tentative via `strength_label`), a `rationale`,
  source-tagged `evidence`, and an `expected_outcome`. `WorkflowSuggestions` ranks by
  confidence, sets a `note` when empty (e.g. everything applicable is applied), and carries
  the `BriefingContext` grounding for audit. The module imports `processing.image` so it is
  self-sufficient (its job is to recommend *registered* ops).
- **Diagnostics correctness fix:** `topography_diagnostics` now reports the **signal**
  topography (prefers canonical `Z`), never a reference height channel (`R_Z*`). Surfaced by
  the recommender picking `R_Z` on the real 32-channel measurement; also corrects the
  Briefing's topography facts. (Synthetic diagnostics tests unaffected - `Z` is signal-role.)
- **Model + GUI:** `ExplorerModel.workflow_suggestions()`; the **AI Scientist panel**
  (`gui/briefing.py`) renders the briefing facts **and** a "Suggested next steps" section -
  one card per recommendation (title, strength badge, rationale, the deterministic *Why*
  evidence, expected outcome, **Preview** button). The window's `_on_recommendation_preview`
  opens the Process tab, `highlight_operation` + `show_operation` + `apply_params` (new
  `ProcessingWorkspace` methods), then runs the *same* generic `preview_operation` - the AI
  has no bespoke execution path. Suggestions refresh as the dataset is processed (applied
  steps drop out of the list).
- **Verified** on the real CdO measurement (offscreen + screenshots): the panel shows
  Reference Normalize (strong, "6 optical signals still raw: O0-O5") and Plane Level
  (moderate, "tilt 10.2 nm/um, ~51% of height variation") on `Z`; clicking a card's Preview
  lands on the Workspace with the before/after and the change/provenance summary. The raw
  measurement is never mutated.

### Decisions
- **ADR-0022** (AI Suggested Next Steps are deterministic, not LLM-generated). Records the
  rule-1/rule-2 grounding, the structural-vs-hopeful safety argument, confidence-as-priority
  (honesty about kind), recommend-not-execute, and the rejected LLM-generates-then-filter
  alternative. The `NarrativeProvider` seam may later *phrase* suggestions, never choose them.

### Issues Found
- The recommender initially targeted `R_Z` (a reference height) on real data - a diagnostics
  bug (topography picked the first topography channel regardless of role). Fixed by preferring
  the signal topography. Also confirmed the engine depends on the operation registry being
  populated (empty applicability -> no recommendations); made `recommend.py` import the image
  ops so it works standalone and in tests, consistent with how the GUI model registers them.

### Tests / gates
- +19 tests (337 total, up from 318): `tests/test_ai_recommend.py` (14 - content, ranking,
  grounding sources, only-applicable, not-already-applied, no-provenance-contradiction,
  empty+note, signal-topography target, JSON round-trip, immutability, strength tiers, a
  degenerate no-suggestion dataset) and +5 GUI in `tests/test_gui_briefing.py` (model
  suggestions, one Preview button per card, the Preview signal payload, empty-note rendering,
  and the window hand-off opening the Workspace pre-filled). `ruff` clean; `mypy --strict`
  clean (80 files incl. tests); Qt-free invariant green; no network in any test.

### Documentation
- `docs/ai-scientist-v1.md` - new "Suggested Next Steps (v2)" section + the deterministic-vs-
  LLM rationale; Explorer-integration + limitations + testing updated; title/status now cover
  both capabilities. `docs/decisions.md` - ADR-0022. `CLAUDE.md` - status block, module
  responsibility, doc table (AI now Briefing + Suggested Next Steps; recommend-not-execute;
  337). `NEXT.md` (task 25 done) and this entry.

### Next recommended
- `image.line_flatten` (GUI-free via the Workspace) and/or more recommendation rules (phase
  unwrap on a wrapping signal, comparison/exploration suggestions) - each extends the
  deterministic pattern. Then a concrete `NarrativeProvider` (optional extra, own ADR) to
  *phrase* the briefing/suggestions; the suggestions stay deterministic. Real-user validation.

---

## 2026-06-27 - Scientific Reasoning Rule Engine (ADR-0023)

Committed the deterministic Suggested Next Steps (`feat(ai): deterministic Suggested Next
Steps`), then - on the user's insight that this is "no longer building software, it's
building scientific reasoning" - refactored the two ad-hoc recommendation functions into a
first-class **Scientific Reasoning Rule Engine**: registered, individually-testable rules
that encode scientific best practice, with explicit triggers, caveats, and full
traceability. A third permanent AI principle + a motto were added to `CLAUDE.md`
(deterministic systems *choose*; AI *explains*).

The user's prompt asked for a fairly elaborate engine (prerequisite chains, mutual
exclusion, dependency reasoning, ordered workflows). I built the parts that are *earned*
now and pushed back (Rule 7 + [[abstractions-need-present-consumer]]) on the rest, in the
open: the prerequisite/exclusion **mechanism** exists and is tested with synthetic rules,
but today's four operations have **no hard prerequisites or exclusions**, so the shipped
rules declare none - and no dependency/ordering *solver* was built (suppress-until-applied
already yields sequencing). I also deferred the phase-unwrap and crop rules as *ungrounded*
(phase-unwrap needs a validated wrapping diagnostic - Rule 6; crop is user-intent-driven) -
demonstrating the engine's own discipline: never recommend without deterministic evidence.

### Completed
- **`snomniman.ai.reasoning` (new):** `ReasoningRule` (declarative ABC: `rule_id`, `step_id`,
  `summary`, `prerequisite_steps`, `excluded_steps`, deterministic `evaluate(ctx) ->
  RuleOutcome | None`), `ReasoningContext` (describe + diagnostics projections + accessors:
  `applicability`, `applied_steps`, `channels`, `field_um`), `RuleOutcome`, and a rule
  registry (`register_rule`/`iter_rules`/`list_rules`) mirroring the processing-step
  registry. Two shipped rules: `reasoning.level_dominant_tilt` (plane level on a dominant
  measured tilt of the *signal* topography) and `reasoning.normalize_with_reference`
  (reference normalize when refs present + signals raw), each enriched with `considerations`
  (deterministic downsides) and interaction-aware, provenance-sourced evidence.
- **`recommend.py` -> pure engine:** evaluates the registered rules, enforces the universal
  guards (applicable + not-already-applied) so rules hold only the scientific trigger,
  honours prerequisites (suppress-until-applied) and exclusions (drop weaker of a
  mutually-excluded pair), ranks by confidence. The recommendation data types moved to
  `report.py`; `Recommendation` gained `rule_id` (traceability) + `considerations`; evidence
  sources widened to diagnostics/description/provenance/metadata. Public API unchanged.
- **GUI:** the AI Scientist card now shows a "Consider:" block (the caveats).
- **Verified** on the real CdO measurement: Reference Normalize (strong, with the
  noise-amplification + phase-re-reference caveats) and Plane Level (moderate, tilt evidence
  + "not in the derivation history" provenance trigger + the order-1 caveat); after applying
  leveling, it drops out and reference-normalize gains "plane leveling has already been
  applied; normalization is a natural next step" (provenance-aware sequencing).

### Decisions
- **ADR-0023** (recommendations as registered reasoning rules). Records the registry design,
  the engine guards, the data-type move + `rule_id`/`considerations`, and the rejected
  alternatives - chiefly the dependency/ordering *solver* (Rule 7) and the ungrounded
  phase-unwrap/crop rules (Rule 6). Third permanent AI rule + motto added to `CLAUDE.md`.

### Issues Found
- The `test_every_recommendation_is_grounded` source set had to widen to include
  `provenance`/`metadata` (rules now emit provenance-sourced triggers). No behaviour
  regressions: the public `recommend_workflow` API is unchanged, so all 14 prior
  recommendation tests passed against the refactor untouched (bar the evidence-source set).

### Tests / gates
- +15 tests (352 total, up from 337): `tests/test_ai_reasoning.py` (per-rule fire/decline,
  the registry, context accessors, and the interaction mechanism - already-applied guard,
  mutual exclusion, prerequisite suppress-until-applied, ordering, duplicate-id rejection -
  using synthetic rules in a monkeypatched registry) plus a GUI considerations check;
  factored a shared `optical_only_dataset` conftest fixture. `ruff` clean; `mypy --strict`
  clean (82 files); Qt-free invariant green; no network in any test.

### Documentation
- Created `docs/scientific-reasoning.md` (philosophy, what a rule is, the lifecycle, the
  shipped rules + the deliberately-deferred ones, the Rule-7 scope note, the extension
  model). `docs/decisions.md` ADR-0023. `CLAUDE.md`: the motto + third permanent AI rule,
  status block, AI module responsibility, doc table (352). `docs/ai-scientist-v1.md` points
  its Suggested-Next-Steps section at the rule engine. This entry; `NEXT.md`.

### Next recommended
- A validated **phase-wrapping diagnostic** (then a phase-unwrap rule "for free"); more rules
  as the vocabulary grows. `image.line_flatten` (GUI-free). A concrete `NarrativeProvider`
  (optional extra, own ADR) to *phrase* the deterministic suggestions. Real-user validation.

---

## 2026-06-27 - Scientific Knowledge Phase begins: phase-wrapping detectability (analysis only)

Committed the Reasoning Rule Engine (`feat(ai): Scientific Reasoning Rule Engine`), then -
on the user's framing that foundational development is done and every future milestone
should "teach SNOMNIMAN one expert judgment, deterministically" - took the first
**Scientific Knowledge** milestone. The deliverable is an *answer*, not a feature: can
phase wrapping be detected deterministically with enough confidence to justify an
automatic phase-unwrap recommendation? **No product code was written** (per the brief and
the project maxim).

The user also asked to enshrine the sentence that drove the previous milestone's pushback;
it is now the **project maxim** at the top of `CLAUDE.md` Core Principles: *"I'd rather the
engine recommend two things it can defend than four it can't"* - scientific honesty over
feature count; a missing capability beats an unjustified one.

### Completed
- Created `docs/phase-wrapping-analysis.md`: the scientific background (wrapped/unwrapped
  phase; why single-harmonic s-SNOM optical phase is often bounded while nano-FTIR /
  interferometric / dispersive phase wraps; the noise/vortex/amplitude pitfalls); the
  candidate diagnostics, grounded in the literature (Goldstein-Zebker-Werner 1988;
  Ghiglia & Pritt 1998) - **residues** (the rigorous path-independence test: zero residues
  <=> uniquely unwrappable) + **unwrap-range ratio** + **amplitude mask**; the rejection of
  wrap-edge count alone (noise-indistinguishable); a validation; specified recommendation
  criteria; and a conclusion.
- **Empirical validation** (throwaway scratch script, not committed, not in `src/`): the
  residue diagnostic behaves exactly as theory predicts on analytical known-answers - a
  coherent 6-wrap ramp is residue-free (density 0, unwrap-range 5.96), a vortex has exactly
  1 residue, uniform noise has residue density 0.33, ramp+heavy-noise 0.25, bounded phase 0.
  On the **real CdO measurement**, every informative optical phase harmonic (O1-O3) is
  **bounded and does not wrap** (unwrap-range ~0.4 x 2pi; residue density 0); O4's apparent
  wrapping has 100% of its residues in low-amplitude noise. So an auto-recommendation would
  correctly decline on all six channels - matching the physics.

### Decisions
- **Conclusion = conditional Outcome 1, honest deferral.** The criterion (residue density +
  unwrap-range ratio + amplitude mask) is scientifically defensible and *analytically*
  validatable. BUT its **positive ("recommend") branch cannot be validated on real data** -
  no available real measurement genuinely wraps. Project Rule 6 needs synthetic AND
  reference validation; only synthetic is achievable today for the positive case.
  Therefore, by the maxim, **defer the auto-recommendation rule**. The *diagnostic fact*
  (does the phase wrap?) is separately defensible and could be built now; the *rule* waits
  for a genuinely-wrapping golden measurement (nano-FTIR / interferometric). `image.phase_unwrap`
  remains available manually in the Workspace regardless. No ADR (no architecture change; a
  research conclusion).

### Issues Found
- None. The investigation strengthened, rather than weakened, the decision to defer: the
  real s-SNOM optical phase here simply does not wrap, so even a perfect rule would have no
  positive examples to fire on. Confirms the earlier (last-milestone) instinct to defer
  phase-unwrap was correct, now with evidence.

### Documentation
- Created `docs/phase-wrapping-analysis.md`. `CLAUDE.md`: the project maxim (Core
  Principles) + doc-table row. This entry; `NEXT.md` (the phase-wrapping task now points at
  the analysis + its deferral). No code, no tests changed (352 still green; gates untouched).

### Next recommended
- If/when a genuinely-wrapping real measurement is available: build the `phase_wrapping`
  diagnostic (residues + unwrap-range + amplitude mask, with the synthetic known-answers as
  tests), then register the phase-unwrap `ReasoningRule`. Otherwise, the next Scientific
  Knowledge milestone is another expert judgment that *is* groundable on present data
  (e.g. poor-scan / drift detection, harmonic-ranking), or `image.line_flatten`. Every
  future milestone: "teach one expert judgment, deterministically - or conclude we can't."

---

## 2026-06-28 - The Knowledge Center (ADR-0024)

Committed the phase-wrapping analysis (`docs: phase-wrapping detectability analysis`),
then built the Knowledge Center: a *living scientific knowledge base integrated into the
product*. The idea (user): SNOMNIMAN should teach the science while the researcher performs
it - click any operation/diagnostic/recommendation/concept and understand it without
leaving the app - and the same curated base grounds the future AI narrator (so AI explains
from a canonical source rather than improvising).

### Completed
- **`snomniman.knowledge` (new Qt-free leaf package, no internal deps):** structured,
  queryable **articles** rather than markdown. `article.py` - the frozen `Article` value
  object (id namespaced by category; required title/summary/explanation; optional
  scientific/mathematical background, when-to-use, common mistakes, references, and
  cross-references to related concepts/operations/diagnostics) + `KnowledgeError`.
  `library.py` - the curated initial content (20 articles: 8 concepts, one per operation
  (4), 4 diagnostics, 4 AI). `query.py` - `get_article`/`find_article`/`articles_in`/
  `article_for_operation`/`article_for_diagnostic`/`search_articles` + `integrity_problems`
  (the no-broken-links check). Articles are held to the project maxim (accurate, concise,
  not padded); the phase-unwrap article ties to the wrapping analysis, the AI articles to
  the permanent rules.
- **Explorer Knowledge panel (`gui/knowledge.py`):** a category tree + search box + a
  `QTextBrowser` article view whose `related` links are clickable and navigate within the
  base. New "Knowledge" tab.
- **"Learn more" deep-links:** the Processing Workspace ("Learn more about this operation")
  and AI Scientist recommendation cards ("Learn more") emit the operation's `step_id`; the
  window resolves it via `article_for_operation` and opens the article in the Knowledge tab.
  The mechanism is generic (a diagnostic row / harmonic / provenance link is the same
  one-liner with `article_for_diagnostic`).
- **AI integration (today):** the deep-link itself - a recommendation points the researcher
  at curated teaching, not model prose. A future provider will ground its explanations in
  these articles (it phrases; the base teaches).
- **Verified** on the real CdO measurement (screenshot): "Learn more" on Reference Normalize
  opens its article (summary, math `O{n}/R_O{n}`, when-to-use, the noise/phase caveats),
  with the browsable Concepts/Operations/Diagnostics/AI tree and working cross-links.

### Decisions
- **ADR-0024** (the Knowledge Center). Structured/queryable articles over a markdown viewer;
  a Qt-free leaf package (teaching content is a distinct responsibility, not a `describe`/`ai`
  projection); AI grounds in the base, never improvises (the deterministic-authority /
  AI-interpreter split). The library is an *initial, curated* set - grown only as accurate
  (the maxim) - with a **no-drift** test requiring an operation article per registered step.

### Issues Found
- Adding a "Learn more" button per recommendation card changed the card's button count;
  updated two `test_gui_briefing` assertions to target the Preview buttons specifically. No
  behaviour regressions. Added `snomniman.knowledge` to the Qt-free invariant's backend list.

### Tests / gates
- +21 tests (373 total, up from 352): `tests/test_knowledge.py` (12 - integrity/no dangling
  links, the **no-drift invariant** that every registered ProcessingStep has an article,
  query API, search, JSON round-trip) and `tests/test_gui_knowledge.py` (9 - panel populate/
  render/search/internal-navigation, the Knowledge tab, and "Learn more" from the Workspace
  and from a recommendation opening the right article). `ruff` clean; `mypy --strict` clean
  (89 files); Qt-free invariant green (now covers `knowledge`); no network in any test.

### Documentation
- Created `docs/knowledge-center.md`. `docs/decisions.md` ADR-0024. `CLAUDE.md`: layer graph
  + module responsibility + the Qt-free rule list + status block (Knowledge Center; 373) +
  doc table. This entry; `NEXT.md`.

### Next recommended
- More "Learn more" sources (diagnostics rows, harmonics, provenance, metadata) - the
  mechanism is generic. More articles as accuracy allows (nano-FTIR, polariton imaging). Then
  the next Scientific Knowledge judgment (poor-scan/drift detection, harmonic ranking), or a
  concrete `NarrativeProvider` that grounds its prose in the knowledge base.

---

## 2026-06-28 - Governance milestone: Scientific Validation Phase + Beta Readiness roadmap (ADR-0025)

A **documentation-and-governance** milestone (no code, no architecture change, no scientific
rule altered). With foundational development complete, the project's bottleneck is no longer
architecture but *deciding what to build*; this milestone establishes the permanent decision
framework. The user had already drafted a **Beta Readiness Review** (`docs/beta-readiness-v1.md`,
the successor to `product-review-v0.1`): an experienced-researcher critique answering "can I use
SNOMNIMAN for a whole day without neaPLOT?" - identifying the beta-blocking workflow cluster
(C1 export data, C2 export numbers, C3 multi-measurement open, C4 `image.line_flatten`), the
neaPLOT switch-back points, a user-testing protocol, and a ~4.0/5 readiness score. This milestone
adopts it as the authoritative product roadmap and pairs it with a formal scientific methodology.

### Completed
- **Created `docs/scientific-validation.md`** - the canonical methodology for how scientific
  capability enters SNOMNIMAN: the lifecycle (Scientific Question -> Literature -> Candidate
  Deterministic Diagnostics -> Analytical -> Synthetic -> Real-data Validation -> Decision ->
  Implementation, **last**), the six permanent engineering principles + the maxim, the **three
  Decision outcomes** (validate-and-implement / defer / stop, with honest deferral a success),
  the rule that diagnostics precede recommendations and real-data validation must be two-sided,
  the reusable **9-section validation template**, a table of *where validated capabilities land*
  (existing layers, Rule 7), and the seeded **Future Validation Queue** (harmonic ranking,
  phase-wrapping recommendation, reference-normalization criteria, poor-scan / drift /
  tip-artifact detection). Phase-wrapping is named as the worked exemplar (Outcome 2).
- **Renamed "Scientific Knowledge Phase" -> "Scientific Validation Phase"** in current docs:
  *validation*, not *accumulation*, is the governing discipline (a judgment ships only when
  evidence justifies it; declining is legitimate), and "Knowledge" collided with the shipped
  Knowledge Center (`snomniman.knowledge`). Historical LOG entries keep their original wording.
- **CLAUDE.md:** new top-level **"Planning and Governance"** section (the two-system table + the
  load-bearing order: Beta Readiness finds gaps -> Scientific Validation justifies science ->
  implement only the intersection -> feedback -> repeat); a governance paragraph in the status
  block; two new doc-hierarchy rows (`beta-readiness-v1.md`, `scientific-validation.md`); the
  phase-wrapping row reworded as the Validation exemplar.
- **roadmap.md:** refreshed the badly-stale header ("Phase 1 ready to begin" -> foundational
  development complete); a **"Current driver"** section (the 5-step priority loop + the Beta
  Readiness Critical cluster as the live product priority); a subsection explaining the rename
  and why validation beats knowledge-accumulation; and honest per-phase status markers
  (1 COMPLETE; 2/3/7 PARTIAL; 4 IN PROGRESS with its exit criterion explicitly *not yet met*;
  5/6 NOT STARTED; 8 DEFERRED). Updated the stale "Phase 1 unblocked" risk bullet.
- **architecture.md:** refreshed the stale status header; added **Section 10 "Extending the
  system: where new capabilities land"** - the fixed mapping of a validated fact/recommendation/
  operation/article/export onto the existing diagnostics / `ai.reasoning` / processing /
  knowledge / io+viz layers, surfaced by the generic registry-driven panels with little GUI code.
- **NEXT.md:** rewritten around the two tracks - a Product track (C1-C4 then H1-H5, each reusing
  an existing abstraction) and a Science track (the Validation Queue, none to be implemented
  ahead of validation) - with the done-items history retired to `LOG.md`, and the durable
  toolchain reminders / design-doc pointers / definition-of-done preserved.
- **decisions.md: ADR-0025** records the governance decision (two planning systems; implement only
  at the intersection; the rename; validated capability extends an existing layer, never a new
  subsystem without its own ADR). Modeled on ADR-0015 (a process ADR).

### Decisions
- **ADR-0025 (governance, not functionality).** Beta Readiness = authoritative product roadmap;
  the Scientific Validation Phase = permanent scientific methodology; the two are complementary
  (need vs justification) and future work lives at their intersection. Recording it as an ADR
  (rather than docs-only) follows Rule 3; alternatives considered: feature-by-feature (rejected -
  the maxim), one combined roadmap (rejected - conflates two authorities), keeping the old name
  (rejected - accumulation framing + name collision).

### Issues Found
- None. This milestone is the doc-side payoff of an already-defended architecture: every
  beta-blocking gap reuses an existing abstraction, and every science-track item routes through
  the same validation gate that (correctly) deferred the phase-unwrap rule.

### Tests / gates
- No code touched; 373 tests still green, gates unaffected. Docs are ASCII/UTF-8.

### Documentation
- Added `docs/scientific-validation.md`; adopted `docs/beta-readiness-v1.md` into the hierarchy.
  Updated `CLAUDE.md`, `docs/roadmap.md`, `docs/architecture.md`, `NEXT.md`, `docs/decisions.md`
  (ADR-0025), and this entry. (Memory: renamed the phase memory to `scientific-validation-phase`,
  added a beta-readiness governance note, refreshed cross-links.)

### Next recommended
- **Product:** start the Beta Readiness Critical cluster - C1 (wire `io.write_zarr` into the GUI
  as "Export data...") is the highest-leverage single change; then C2, C4 (`image.line_flatten`),
  C3. **Science:** the next validation investigation that *is* groundable on present data
  (harmonic ranking is the strongest candidate and a real workflow need). **Strongly recommended
  first:** run the user-testing protocol (Beta Readiness Section 5) with two or three neaPLOT
  users and let their forced exits order the backlog.

---

## 2026-06-28 - Next-priorities triage (Line Flatten / Harmonic Ranking / Reference Normalization)

A Scientific Validation Phase **triage milestone**: classify three candidate capabilities
by the kind of work each requires next (engineering vs. scientific validation vs.
sequencing). Analysis only - no code, no architecture change.

### Completed
- Read the governing docs (`scientific-validation.md`, `beta-readiness-v1.md`,
  `phase-wrapping-analysis.md`, `scientific-reasoning.md`, `diagnostics-engine.md`) and the
  relevant code (`processing/image/reference_normalize.py`, `plane_level.py`,
  `diagnostics/diagnose.py` + `descriptors.py`, `ai/reasoning.py`) to ground the triage.
- Authored `docs/next-scientific-priorities.md`: per-candidate classification, rationale,
  recommended milestone, engineering + scientific effort, risks, dependencies, and a
  prioritized roadmap.

### Decisions (classifications)
- **Line Flatten -> Category A (implement now).** Settled SPM science (per-line
  median/mean/poly row alignment) and a Critical beta blocker (C4/G4). It is a *manual
  operation*, not an automated judgment, so it does **not** pass through the Validation
  Phase - the standard analytical known-answer DoD is the whole scientific requirement
  (as for `plane_level`/`crop`). Any *auto-recommendation* rule for it is a separate,
  future Category-B question (line-artifact detection), deliberately excluded.
- **Harmonic Ranking -> Category B (validate next).** Needed (subsumes Beta Readiness M4;
  named browsing friction) but resting on the exact signal-vs-noise judgment `diagnostics`
  declined to assert (no SNR, ADR-0019). Strongest science-track milestone; plausibly
  validatable on *both* branches with the existing CdO scan (informative O1-O3 vs.
  near-noise O4/O5) - an advantage phase-wrapping lacked.
- **Reference Normalization Criteria -> Category B (validate after harmonic ranking).** The
  operation *and* a recommendation already ship - but `ReferenceNormalizeRule` fires on a
  flat 0.85 prior and never gates on whether the reference is strong enough to trust.
  Validating *when to decline* is justified honesty work, but lower-urgency and
  dependency-coupled: it should reuse the noise-floor / amplitude-significance fact the
  harmonic-ranking study must establish (Rule 7, avoid a parallel noise estimator).
- **None is Category C.** "Wait" is expressed as sequencing within B (Candidate 3 behind
  Candidate 2), not by forcing a justified capability into C.
- **Key cross-cutting finding:** Candidates 2 and 3 reduce to one unsolved primitive - a
  deterministic single-scan noise-floor estimate - which fixes their order.

### Issues Found
- None. The triage confirms the dual-track governance: one item is build-ready settled
  science (product track), two are validation studies (science track) in dependency order.

### Tests / gates
- No code touched; 373 tests still green, gates unaffected. Doc is ASCII/UTF-8.

### Documentation Updated
- Added `docs/next-scientific-priorities.md`; pointer added to `NEXT.md` (science track);
  this entry. (Memory index refreshed.) Not yet wired into the `CLAUDE.md` hierarchy table
  or `decisions.md` - left for explicit sign-off.

### Next Recommended Actions
- **Product:** implement `image.line_flatten` (Candidate 1) - the build-ready item.
- **Science:** open `docs/harmonic-ranking-analysis.md` (Candidate 2) from the validation
  template; ship the diagnostic *fact* before any rule/marking. Reference-normalization
  criteria follows it.

---

## 2026-06-28 - `image.line_flatten` (Beta Readiness C4 / the Candidate-1 engineering milestone)

Implemented the line-by-line flattening operation classified Category A (ready for
implementation) by `docs/next-scientific-priorities.md`. The milestone's purpose was to
prove the architecture absorbs another mature scientific operation with **zero
architectural change** - confirmed: implement + register, and it appeared everywhere.

### Completed
- **`snomniman.processing.image.line_flatten`** - a `flatten_lines()` algorithm helper +
  the `LineFlatten` `ProcessingStep` (`step_id="image.line_flatten"`, `SPATIAL_2D`,
  params `channel` / `method` (median|mean|polynomial) / `order`; median is the robust
  default). Registered in `processing/image/__init__.py`. Mirrors `plane_level.py`.
- **Algorithm (established SPM methodology, not invented):** subtract a per-scan-line
  baseline - median (robust, the Gwyddion "Align Rows" default), mean, or a per-line
  least-squares polynomial (offset+slope/bow). NaN-robust (finite-only baseline; all-NaN
  line passes through). Cited Necas & Klapetek (Gwyddion) and Horcas et al. (WSxM).
- **Knowledge Center article** `operation.image.line_flatten` (purpose / intuition / math
  / when-to / when-not / comparison-with-Plane-Level / mistakes / refs), with bidirectional
  cross-links to `image.plane_level` and `concept.topography`. No-drift invariant green.
- **Tests** (`tests/test_processing_image_line_flatten.py`, ~33 cases): analytical
  known-answers (pure offsets -> 0 all methods; offset+slope -> 0 poly1; quadratic -> 0
  poly2; feature recovered with known per-line baseline; NaN handling), a combined
  tilt+offset+feature synthetic (striping collapses, feature survives), immutability +
  frozen-arrays + channel isolation, provenance (id/version/params/input), defaults,
  validation (bad method/order, missing/complex channel, unknown param), registry, and a
  real-CdO comparison of raw / plane-leveled / line-flattened. Extended the
  vocabulary-growth assertions in `test_diagnostics`, `test_gui_workspace_model`,
  `test_ai_briefing` to include the new op.

### Decisions
- **Distinct verb, not a `plane_level` parameter (Rule 2).** Plane leveling fits one
  global surface; line flattening removes independent per-line baselines - complementary,
  not duplicative. Did **not** add `polynomial_flatten` (would duplicate plane_level).
- **No reasoning rule (deliberate, on-discipline).** An *auto-recommendation* for line
  flattening needs a validated line-artifact diagnostic (a separate Category-B study, the
  cousin of phase-wrapping/poor-scan detection). Per the maxim, the operation ships as a
  manual verb; Suggested Next Steps does **not** recommend it - exactly as crop/phase_unwrap.
- **Fast axis = x (horizontal scan lines)**, matching the neaSNOM raster; documented as an
  assumption. No `direction` param yet (Rule 7 - add when a real need appears).

### Integration (auto-propagated, no subsystem code)
Registering the step alone made it appear in: the processing registry (`get_step`), the
Description API operation catalogue, Diagnostics applicability, the generic Processing
Workspace (discovery + auto-built median/poly form + preview/provenance/accept/cancel +
history), the AI Briefing "Enables" section, and (via the no-drift article) the Knowledge
Center. **No GUI code, no new infrastructure** - the success criterion of this milestone.

### Real-data validation (CdO Z, 150x150, nm)
Per-line baseline spread (std of per-row medians) / overall std: raw 29.5 / 41.0; plane
level o1 20.7 / 28.5 (leaves ~70% of striping - a global surface cannot remove per-line
offsets); line_flatten median 0.0 / 28.5 (zeroes each line's median); line_flatten poly1
5.2 / 21.4 (removes per-line offset+slope, lowest std). Confirms the two operations are
complementary and where each is appropriate. Raw never mutated.

### Tests / gates
- 406 tests pass (was 373; +33), `ruff` clean, `mypy --strict` clean (91 files), Qt-free
  invariant green. Docs ASCII/UTF-8.

### Documentation Updated
- `docs/processing-engine.md` (ops table + the two-flattening-verbs note, now implemented;
  date). LOG (this entry), NEXT (C4 done), project-state memory.

### Next Recommended Actions
- **Product (Beta Readiness Critical):** C1 export the processed dataset (wire
  `io.write_zarr`/`write_gsf` into the GUI), C2 export measurement numbers (CSV/clipboard),
  C3 open multiple measurements. C4 is now done.
- **Science:** open the **harmonic-ranking** validation study (`docs/next-scientific-priorities.md`
  Candidate 2) - the next science-track milestone; ship the diagnostic fact before any rule.

---

## 2026-06-28 - Harmonic signal-vs-noise classification (Candidate 2 / first Outcome-1 study; ADR-0026)

The science-track Candidate 2 (`docs/next-scientific-priorities.md`), worked through the
full Scientific Validation lifecycle (`docs/scientific-validation.md`) to a recorded
Outcome. It is the **first study to reach Outcome 1** (validate-and-implement) - the
phase-wrapping exemplar reached Outcome 2 - and it demonstrates the validation process
flowing into deterministic capability with **no architectural change** (Rule 7).

### The study (docs/harmonic-ranking-analysis.md)
Question: can the boundary between signal-bearing and noise-dominated optical harmonics be
drawn deterministically from a single measurement, validatable on both branches? Worked
the 9-section template: literature (Immerkaer 1996 single-image noise; Moran/Cliff-Ord
spatial autocorrelation; Keilmann/Hillenbrand demodulation), candidate diagnostics,
analytical + synthetic + **two-sided real-data** validation across all three CdO imaging
runs.

### Decision (two distinct claims)
- **Signal-vs-noise classification - READY (Outcome 1), implemented.** Per harmonic:
  spatial coherence (lag-1 autocorrelation; analytical white-noise null), a single-image
  SNR estimate (Immerkaer), and a label `signal`/`weak`/`noise`/`empty`/`unknown`.
  Thresholds tied to the synthetic SNR=1 (coherence ~0.5) / SNR=0.5 (~0.2) crossovers -
  calibrated, not fitted. Meets Beta Readiness M4.
- **"Informativeness ranking / best-harmonic recommendation" - REJECTED.** The decisive
  honesty finding: spatial coherence/SNR measure structure-vs-noise, **not**
  near-field-vs-background. Real O1 (far-field background, anti-correlated with the
  near-field family) reads as high-SNR "signal" and in run1 outscores genuine near-field
  O3 - so a quality-ranking would promote the background order. "Best harmonic" is the
  confinement-vs-SNR expert tradeoff, not a deterministic fact. **No `ReasoningRule`
  added** (ship the fact, decline the judgment - as with phase-unwrap/line-flatten).
- **Discharges ADR-0019's SNR deferral.** ADR-0019 declined SNR for want of a validated
  noise model; this study supplies one (recovers true SNR to ~1% on synthetic data;
  validated two-sided on real data). The deferral is lifted only now that evidence exists.

### Validation results
- Analytical: white noise -> coherence +0.005 (null ~0.0067), SNR 0.15; smooth signal ->
  coherence 0.999; constant -> empty.
- Synthetic SNR sweep: SNR estimate tracks truth (8.0->7.93, 1.0->0.985, 0.5->0.497);
  coherence crosses ~0.50 at SNR=1; size-robust at 150x150 and 300x400.
- Real CdO (3 runs): O2/O3 signal everywhere (coherence 0.84-0.97, SNR 2.4-8.7); O4 is the
  transition (signal in the short run, noise/weak in the two longer runs, SNR 0.6-0.7) -
  a genuine signal->noise crossover on real data; O0 incoherent DC artifact -> noise; O5
  not recorded -> empty. **Both branches validated** (the bar phase-wrapping could not clear).

### Implementation (extends existing abstractions only)
- `diagnostics`: `HarmonicAmplitude` gains `spatial_coherence` / `snr_estimate` /
  `classification`; `harmonic_diagnostics` computes them via `_spatial_coherence`,
  `_immerkaer_noise_sigma`, `_spatial_snr`, `_classify_harmonic`. Constants exported.
- `ai.briefing`: Scientific Observations now lists which orders carry coherent signal vs.
  are noise/empty (replacing the old "strongest amplitude" line, which pointed at the O0
  artifact).
- `knowledge`: new `diagnostic.harmonic_signal_noise` article; cross-linked from
  `concept.harmonics` / `diagnostic.harmonic_decay`; integrity + no-drift green.
- `gui.model`: the Optical harmonics diagnostics rows render the class + coherence
  (display only).
- No reasoning rule, no new operation, no GUI subsystem code.

### Tests / gates
- 415 tests pass (was 406; +9 net incl. the now-runnable real golden cases), `ruff` clean,
  `mypy --strict` clean (91 files), Qt-free invariant green. Known-answer tests:
  analytical (white/smooth/checkerboard/constant), synthetic SNR crossover, small-image
  "unknown", two-sided real-CdO golden, briefing + GUI integration.

### Documentation Updated
- New `docs/harmonic-ranking-analysis.md`; `decisions.md` (ADR-0026); `diagnostics-engine.md`
  (descriptor + SNR-deferral discharge); `scientific-validation.md` (queue: Outcome 1);
  `next-scientific-priorities.md` (Candidate 2 done); `CLAUDE.md` (doc hierarchy). LOG (this
  entry), NEXT, project memory.

### Next Recommended Actions
- **Science:** Candidate 3 - **reference-normalization criteria**
  (`docs/reference-normalization-analysis.md`), which should now **reuse** this study's
  single-image noise-floor primitive (`snr_estimate`/`spatial_coherence`) to ask "is this
  reference channel above the noise floor?" rather than re-derive it.
- **Product (Beta Readiness Critical):** C1 export the processed dataset, C2 export
  measurement numbers (CSV/clipboard), C3 open multiple measurements.

---

## 2026-06-29 - Reference-normalization recommendation criteria (Candidate 3 / Outcome 2: DEFERRED, no code)

The third Scientific Validation study (`docs/scientific-validation.md`), Candidate 3 of the
triage, building on the Candidate-2 harmonic signal/noise primitive (ADR-0026). Worked the
full 9-section lifecycle to a recorded Outcome. **Outcome 2 (DEFERRED) - no code shipped.**

### The question (docs/reference-normalization-analysis.md)
`image.reference_normalize` already exists and is validated; the open question was *when to
recommend it*. Decomposed (as the brief required) into possible / appropriate / strongly
recommended, and asked whether a deterministic, two-sided-validatable recommendation
criterion exists - reusing the harmonic primitive (no new noise estimator).

### Decision: DEFERRED
- **Possible** - already true & shipped (structural trigger).
- **Appropriate** - **not deterministically decidable.** Appropriateness requires the
  reference to be a *meaningful, independent common-mode response* (an experimental-design
  fact not in the array). The data can *exclude* appropriateness (redundant/weak/noisy/empty
  reference) but cannot *establish* it.
- **Strongly recommended** - not justified; needs the appropriate branch + real benefit,
  neither validatable on present data.
- Per the methodology's two-sided rule (decline AND fire must validate on real data), only
  the decline side validates -> defer the rule. Mirrors phase-wrapping (Outcome 2), on the
  positive branch.

### Decisive evidence (the real `R-` channels are not usable references)
- **All three imaging runs are PsHet, "Measurement Mode: Self-Reference Off"**, and the
  `.txt` defines **no reference material/position**. The discovery doc's early "`R-` =
  reference" was an unvalidated inference.
- For every signal-bearing harmonic, `R_O{n}` is a **near-copy of `O{n}`**:
  `corr(|O|,|R|)` 0.94-0.97, **`|O/R| ~ 1.00`**, referenced-phase spread 0.02-0.12 rad ->
  normalization would **erase contrast**, not improve it (synthetic "case C").
- The *decline* branch IS real-data-validated: `R_O4` in the two longer runs is
  `noise`/`weak` class, SNR 0.56-0.67, ~10% near-zero -> `O/R` blow-up + destroyed phase.
- Synthetic known-answers confirmed the crux: a strong **independent** reference (case A)
  and a strong **copy** reference (case C) are **identical on every quality metric**
  (signal-class, high SNR, 0% near-zero); only redundancy (`corr` / `CV(|O/R|)`) separates
  them. So reference *quality alone cannot justify a positive recommendation*, and case A
  does not occur in any available real measurement.

### Secondary finding (flagged, not fixed - DEFER ships no code)
The existing `ReferenceNormalizeRule` fires at a flat **0.85** whenever references exist and
signals are raw - which on **every** available real measurement recommends an operation that
erases contrast (and injects noise on weak harmonics). It was shipped (ADR-0023) as a
"standard-practice prior" before this validation; the prior is **not supported by the
evidence**. Top Future Work: gate it conservatively (decline on redundant/weak/noisy/empty
references - all deterministically detectable and validated here) or withdraw the positive
recommendation until a genuinely-referenced golden measurement exists. Not changed this
milestone (DEFER discipline + the brief forbids reasoning-engine redesign).

### No code, by design
No rule, no diagnostic, no operation change. A *reference-quality fact* in isolation would
be misleading (high quality != appropriate), so unlike harmonic ranking, nothing is shipped
- only the recorded analysis. 415 tests remain green (unchanged); `ruff`/`mypy`/Qt-free
unaffected (no source touched).

### Documentation Updated
- New `docs/reference-normalization-analysis.md` (Outcome 2). `scientific-reasoning.md`
  (validation note on the rule + deferred-items bullet), `ai-scientist-v1.md` (caveat),
  `scientific-validation.md` (queue -> Outcome 2), `next-scientific-priorities.md`
  (Candidate 3 done), `CLAUDE.md` (doc hierarchy). LOG (this entry), NEXT, project memory.

### Next Recommended Actions
- **Science (honesty fix):** a small follow-up to **gate or withdraw** the flat-0.85
  `ReferenceNormalizeRule` (decline on redundant/weak/noisy/empty references - the validated
  decline conditions). `(user)` to obtain a genuinely-referenced measurement to ever validate
  the positive branch.
- **Product (Beta Readiness Critical):** C1 export the processed dataset, C2 export
  measurement numbers (CSV/clipboard), C3 open multiple measurements.

---

## 2026-06-29 - Withdraw the unjustified reference-normalization recommendation (align with validation)

Brought the Scientific Reasoning Engine into line with the Reference-Normalization validation
(Outcome 2, same day): the unvalidated flat-0.85 positive recommendation is withdrawn. No
architecture change, no operation removed, no new heuristic or confidence score - the goal is
scientific honesty.

### Change
- `ai/reasoning.py`: `ReferenceNormalizeRule.evaluate` now returns `None` for every
  measurement (the positive path - the flat 0.85 "standard-practice" prior - is removed). The
  rule stays registered as the documented, tested home for a future positive criterion; its
  docstring records the deterministic decline conditions (redundant / weak / noisy / empty
  reference) that remain the basis, and why no positive criterion is yet defensible.
- Behavior: reference normalization is no longer in Suggested Next Steps; the operation
  remains fully available in the Processing Workspace and still reports as applicable. When
  evidence is insufficient to recommend, the engine recommends nothing rather than assert an
  unjustified positive (the maxim; AI rule 3 - deterministic systems choose, AI never invents
  authority).

### Propagation (no per-surface code)
- Suggested Next Steps: no reference-normalize card (real CdO now suggests only plane level).
- AI Briefing: unchanged facts; the operation still appears in "Enables" as applicable.
- Knowledge Center: the `operation.image.reference_normalize` article's guidance updated -
  apply deliberately with a genuine reference; not auto-recommended; avoid on weak/redundant
  references (a 'Self-Reference Off' / retrace yields O/R ~ 1).

### Tests
- Updated the rule/recommendation tests to the new behavior and added regression tests that
  pin reference normalization is **never** auto-recommended (unit: the rule evaluates to None
  even when references are present + signals raw; engine: recommend_workflow never includes
  it) while it stays applicable/available. Operation-level tests unchanged (operation intact).
- 413 tests pass (was 415; -2 net: 3 positive-path rule tests collapsed into 1 withdrawal
  test, 1 recommend test swapped for the regression test). `ruff` clean, `mypy --strict` clean
  (91 files), Qt-free invariant green. Real-data check: CdO suggests only plane level;
  reference_normalize not recommended but still applicable.

### Documentation
- `scientific-reasoning.md` (shipped-rules section + deferred item -> withdrawn),
  `ai-scientist-v1.md` (rule list + limitations), `knowledge/library.py` (article guidance).
  LOG (this entry), NEXT. The validation record (`reference-normalization-analysis.md`) is
  unchanged - it is the historical Outcome-2 analysis; this entry records the alignment its
  Future Work item #1 called for.

### Next
- A *positive* reference-normalization rule remains deferred until a genuinely-referenced
  golden measurement validates the appropriateness branch `(user)`.

---

## 2026-06-29 - Complete the research workflow: project save/reopen + data/measurement export (ADR-0027)

The first **end-to-end** product milestone: close the Beta Readiness Critical cluster so a
researcher can finish a real analysis and resume it later. Implemented C1 (export the
processed dataset), C2 (export measurement numbers), and H1 (project save/reopen) - each
*exposing a backend capability that already existed* (the Zarr store, the GSF writer, the
provenance DAG, the measurement engine), with **no new scientific subsystem** and no
architecture redesign (one new acyclic dependency edge, `pipeline -> io`). C3
(multi-measurement) and AI/spectral/batch were explicitly out of scope.

### Completed
- **`snomniman.pipeline.project` (implements the long-stubbed package):** `Project`
  (datasets oldest->newest + `current_index` + an opaque `session` mapping),
  `save_project`/`load_project`/`project_from_history`. A project saves as a
  `<name>.snomproj` **bundle** - one canonical Zarr store per dataset (reusing
  `io.write_zarr`/`read_zarr` verbatim) plus a `project.json` manifest (format marker
  `snomniman.project`, schema_version, dataset order, current index, the session blob).
  Because every dataset serializes its own provenance DAG, the **processing history
  round-trips for free**; raw immutability is restored exactly as on first import. Overwrite
  is refused unless the target is empty or an existing project bundle (never clobbers
  unrelated dirs).
- **`snomniman.io.export.export_channel_gsf`:** export one channel as a Gwyddion Simple
  Field grid - a complex channel as amplitude/phase/real, float32, flipped back to GSF
  top-to-bottom (the exact inverse of the reader's import flip), with a header built from the
  canonical nm coordinates - plus a `<file>.provenance.json` sidecar embedding the serialized
  DAG, source anchor, and conventions (a GSF file cannot hold a DAG), mirroring the figure
  export. Zarr stays the loss-less path; GSF is the lossy single-grid interchange path.
- **`snomniman.gui.export` (Qt-free):** `profile_to_csv` / `region_to_csv` + `ExportContext` -
  a commented provenance header (measurement, source+sha, geometry/region, conventions,
  provenance chain, version) then a clean table with explicit unit-bearing column headers;
  delimiter-parameterized (`,` for a file, tab for clipboard). Numbers come from the validated
  `viz.measure` backend; NaN -> blank cell.
- **GUI wiring (`window.py`, `measurement.py`, `app.py`):** a **File menu** (New, Open
  Measurement, Open Project, Save Project, Save Project As, an Export submenu - Processed Data
  (Zarr) / Channel (GSF) / Measurement (CSV) / Figure - and Exit) with the standard shortcuts;
  `current_project()` bundles the history + current + view + measurements; `load_project_object`
  rebuilds the whole session (history stack, active dataset, channel/representation/view, and
  the measurement overlays); the Measure panel gained `Copy` + `Export CSV...`; the
  MeasurementController gained `to_records()`/`load_records()` (geometry persisted in canonical
  nm). `python -m snomniman.gui <path>` now opens a `.snomproj` bundle or a raw measurement.
- **Verified end-to-end on the real CdO measurement** (headless): load (32 channels) -> plane
  level Z -> save project -> reopen -> the derived dataset returns with `[io.read,
  image.plane_level]` provenance and bit-identical Z -> export Zarr (reloadable) + GSF (round-
  trips to float32). The offscreen GUI tests cover the same path through the window (save in
  one window, reopen in a fresh one, measurements + channel restored).

### Decisions
- **ADR-0027.** Project persistence lives in `pipeline` (its constitutional home) and reuses
  the Zarr store, adding the single acyclic edge `pipeline -> io` (no second dataset
  serialization, Rule 2). GSF channel export lands in `io`; measurement CSV is Qt-free
  presenter logic in `gui`. Derived datasets are **stored faithfully** rather than replayed
  (reproducibility first; the DAG is still fully persisted, so replay stays a future
  optimization). Persistent "Recent Projects" deferred (needs a settings store - out of scope).
- **"New" == "Open Measurement"** in this single-measurement app (both start a fresh analysis
  from a raw directory); kept as separate menu items per the brief.

### Issues Found
- A PySide6 wrapper-lifetime quirk: re-wrapping the File QMenu via `action.menu()` in a test
  hit "C++ object already deleted." Fixed by holding Python references to the menus on the
  window (`self._file_menu`/`self._export_menu`) - the established in-package test style.
- No scientific-logic leak into Qt: the CSV builders and the project/export logic are Qt-free
  and unit-tested headlessly; the widgets only choose a destination/delimiter (Rule 4).

### Tests / gates
- +34 tests (447 total, up from 413): `test_project_store.py` (14 - round-trip incl. a derived
  2-node DAG + the real golden measurement, session/current restore, overwrite + foreign-dir +
  bad-manifest + validation guards), `test_io_export.py` (8 - amplitude/phase/real round-trip,
  header + units, sidecar, invalid-representation guards, non-mutation), `test_gui_export.py`
  (4 - CSV headers/units/values/NaN/tab, Qt-free), `test_gui_session.py` (8 - File menu, save
  then reopen restores history+channel+measurements, the open handler, records round-trip, and
  the three exports through the window). `ruff` clean; `mypy --strict` clean (63 files); the
  Qt-free invariant green (pipeline now imports io - both Qt-free).

### Documentation Updated
- `docs/decisions.md` (ADR-0027 + date), `docs/architecture.md` (layer graph `pipeline -> io`,
  Section 3 pipeline/io/viz/gui, Section 10 export row, status/date), `docs/data-model.md`
  (Section 10 persistence formats + the `.snomproj` bundle layout + the Project round-trip
  invariant), `CLAUDE.md` (status block, layer graph, io/pipeline module lines, 447),
  `docs/beta-readiness-v1.md` (C1/C2 + H1 marked done). `LOG.md` (this entry), `NEXT.md`,
  project memory.

### Next Recommended Actions
- **Product (Beta Readiness):** C3 - open more than one measurement at once (a multi-measurement
  session); then the High tier (H2 keyboard navigation, H3 background subtraction + height
  zero/offset, H4 absolute-value profile, H5 verbatim vendor-header view). Strongly recommended:
  run the user-testing protocol now that a full workday is possible end-to-end.
- **Science:** the open Validation Queue items (poor-scan/drift detection; the deferred
  phase-wrapping and positive reference-normalization rules await a suitable golden measurement).

---

## 2026-06-29b - Multi-measurement projects (Phase 2A, ADR-0028)

Closed beta blocker **C3** (open more than one measurement). Implemented after a written design
proposal that the user reviewed and approved with two refinements (sequential local ids over
UUIDs; an explicit "one-measurement project == the prior app" success criterion). The work is a
*promotion*, not a rewrite: reading the code showed the original `Project` already modeled one
measurement's derivation history, so it became a `Measurement` and a new `Project` was defined
above it as a collection of measurements.

### Completed
- **Backend (`pipeline/project.py`):** new immutable `Measurement` (stable `measurement_id`,
  `title`, datasets-history, `current_index`, opaque `session`; `.current`/`.raw`) - the promoted
  single-measurement `Project`. `Project` refactored to hold `measurements` + active
  `current_index` + a project-level `session` (`.current_measurement`/`.current_dataset`). Added
  `measurement_from_history`; kept `project_from_history` (now a one-measurement project).
- **Persistence (same file):** schema `1 -> 2`; bundle nests
  `measurements/measurement_NN/datasets/dataset_NN.zarr` (ordinal paths; stable ids in the
  manifest). `save_project`/`load_project` extended; **v1 bundles load via migration** into a
  one-measurement project (the v1 `session` re-homed onto the measurement). No second format,
  no new module, no new layer edge (reuses `pipeline -> io`).
- **GUI session split (`gui/model.py`, `gui/window.py`):** new Qt-free `MeasurementSession`
  (one measurement's live working state: model, history, captured `view_state` +
  `measure_records`, id, title). The window holds `_sessions` + `_active_index`; `_model` and
  `_history` became **properties delegating to the active session**, so the ~30 methods that
  read/assign them are unchanged (behaviour-preserving for one measurement). `current_project()`
  now bundles every session as a `Measurement`; `load_project_object()` rebuilds sessions.
- **Manager + File workflow (`gui/panels.py`, `gui/window.py`):** a **Measurement Manager** dock
  (left, above Channels) lists measurements, marks the active one, and offers Add / Rename /
  Close (pure presentation, signal-based, Rule 4). File menu gained New Project / Add
  Measurement / Close Measurement / Close Project (kept Open Measurement/Project, Save/Save As,
  Export). **Switching** captures the outgoing session's view + overlays and restores the
  incoming one's with **no disk reload** (reuses `MeasurementController.to_records/load_records/
  set_model`). Sequential, never-reused ids (`measurement-0001`) via a persisted per-project
  counter in the project `session`. The "m/n" window-title hint appears only when n > 1, so a
  one-measurement project looks like the prior app.

### Decisions
- **ADR-0028.** Promote `Project` -> `Measurement`; `Project` becomes a collection. Evolve the
  `.snomproj` format in place (schema v2 + v1 migration), not a second format (Rule 2/7).
  Sequential project-local ids (a persisted monotonic counter), **not UUIDs** (user direction;
  ids are never shared/networked, and non-reuse keeps them safe as stable handles for later
  cross-measurement/batch work). The GUI owns mutable working state and materializes immutable
  snapshots at save (the ADR-0027 pattern); `Measurement`/`Project` stay frozen + Qt-free.
  Lazy-loading datasets (memory at 100+ measurements) **deferred** (Rule 7) - an honest known
  limitation with a localized future seam.

### Issues Found
- One mismatched signal wiring caught by `mypy --strict` (manager `removeRequested` -> the
  renamed `close_measurement`); fixed before any test run. No scientific-logic leak into Qt -
  the session/switch logic is exercised through Qt-free seams (`add_measurement_model`,
  `switch_to`, `close_measurement`, `rename_measurement`) and unit-tested headlessly.

### Tests / gates
- 458 tests (up from 447). `test_project_store.py` rewritten for the two-level model + new tests
  (multi-measurement round-trip, single-measurement equivalence, **v1 migration**, Measurement
  guards). `test_gui_session.py` extended: add-and-activate, **switch preserves per-measurement
  channel + overlays**, close-and-reactivate, rename, multi-measurement save/reopen (asserts the
  id counter round-trips). `ruff` clean; `mypy --strict` clean (98 files); Qt-free invariant
  green (`Measurement`/`Project` add no Qt; the Manager widget lives in `gui`).

### Documentation Updated
- `docs/decisions.md` (ADR-0028), `docs/architecture.md` (pipeline `Measurement`+`Project`
  description; gui multi-measurement + Manager), `docs/data-model.md` (Section 10 table + bundle
  layout + round-trip invariant). `LOG.md` (this entry), `NEXT.md`, `CLAUDE.md` status, project
  memory.

### Next Recommended Actions
- **Product (Beta Readiness):** with C1-C4 + H1 + C3 done, the Critical cluster is closed - run
  the **user-testing protocol** (a full workday is now possible: multi-measurement, process,
  measure, save/reopen, export). Then the High tier (H2 keyboard nav, H3 background subtraction +
  height zero/offset, H4 absolute-value profile, H5 verbatim vendor-header view).
- **Later phases now have a home:** cross-measurement comparison, batch (`snomniman.batch`),
  and experiment-wide statistics build on the `Project`/`Measurement` foundation.
- **Science:** unchanged - the open Validation Queue items await suitable golden measurements.

---

## 2026-06-29c - Experiment analysis (Phase 2B, ADR-0029)

Built experiment-level analysis on the 2A multi-measurement foundation, after a written design
proposal the user reviewed and approved. The proposal's headline call - **defer Difference Views to
a separate Phase 2C** - was accepted: 2B is a coherent, releasable, **read-only** experiment-analysis
layer; the one write-path part (multi-input difference datasets + the two-parent provenance topology)
gets its own milestone. The whole phase adds **one Qt-free presenter and reuses every existing
system** (Rule 7); no backend, provenance, or processing change.

### Completed
- **`ExperimentModel` (`gui/experiment.py`, Qt-free, NEW):** a thin experiment-level presenter that
  *aggregates* existing per-measurement capabilities over the project's sessions - never new science.
  `browser_rows()` (cheap, metadata-only); `shared_channels` / `comparison_panes` / `comparison_readout`
  (cross-measurement compare, reusing each model's `render_spec` / `values_at`); `diagnostics_table()`
  (reuses `diagnose`, **cached per dataset**); `compare_region` / `compare_profile` (reuse
  `viz.measure` via each `ExplorerModel`). Value objects: `ExperimentRow`, `ComparisonPane`,
  `ExperimentTable`/`Column`/`Cell`/`Row`. Creates nothing.
- **Export (`gui/export.py`):** `experiment_table_to_csv` + `ExperimentExportContext` reusing the
  existing provenance-header + CSV style (cell text is exported; the numeric `value` is a GUI sort key).
- **Widgets / wiring:** the **Measurement Manager became the experiment browser** (a summary
  `QTableWidget` - Measurement / Time / Processing / Harmonics / Ref - with multi-select; one row
  selected = activate, several = enable **Compare**). Cross-measurement compare **reuses
  `ComparisonView`** (panes pre-rendered each from its own model + a dict renderer; the viewer already
  syncs zoom/pan/cursor); the compare anchors on the first selected measurement so the channel browser
  drives the shared channel/representation; the cursor readout routes through `ExperimentModel`. A new
  **Experiment** inspector tab (`gui/experiment_view.py`, `ExperimentPanel`) shows a **sortable**
  diagnostics table (lazy + cached) and the cross-measurement statistics for the active overlay, with
  Export CSV / Copy. `MeasurementController.active_geometry()` exposes the active overlay's nm geometry
  so the same ROI/line is evaluated on every measurement. Figure export is guarded in compare mode
  (it is not a single-dataset source).

### Decisions
- **ADR-0029.** Read-only experiment analysis via one Qt-free `ExperimentModel` that aggregates
  existing systems (no `snomniman.experiment` backend module yet - one present consumer, Rule 7; no
  second comparison/diagnostics system). **Difference Views deferred to Phase 2C** (multi-input op +
  GUI multi-input surface + grid compatibility + the unresolved two-parent-vs-linear-history
  provenance question). The browser stays cheap (metadata only); diagnose is lazy + cached.

### Issues Found
- mypy `--strict` caught the loose `geometry: object` (untyped unpacking) -> typed it
  `tuple[float,float,float,float] | Sequence[tuple[float,float]]` with a `cast` per branch; and the
  `QTableWidgetItem | None` returns in tests -> a small `_text` guard. No scientific-logic leak into
  Qt: the aggregation is in the Qt-free presenter and unit-tested headlessly.

### Tests / gates
- 478 tests (up from 458). `test_experiment_model.py` (11, **headless/no-qapp**: browser, shared
  channels, compare panes + readout, diagnostics table + cache, region/profile compare),
  `test_gui_experiment.py` (7: browser summary, single-measurement quiet row, enter/exit compare
  mode, lazy diagnostics tab, overlay stats + export), `test_gui_export.py` (+2). `ruff` clean;
  `mypy --strict` clean (102 files); Qt-free invariant green (`gui/experiment.py` imports no Qt; the
  Qt widgets live in `gui/experiment_view.py` + `panels.py`).

### Documentation Updated
- `docs/decisions.md` (ADR-0029), `docs/architecture.md` (gui experiment presenter + browser +
  Experiment tab). No `data-model.md` change (read-only; no new datasets/format/provenance). `LOG.md`
  (this entry), `NEXT.md`, `CLAUDE.md` status, project memory.

### Next Recommended Actions
- **Phase 2C (planned):** Difference Views as derived datasets - the first multi-input
  `ProcessingStep`, the GUI surface to choose a second-measurement input, grid/coordinate
  compatibility (refuse on mismatch), and the design decision for where a two-parent derived dataset
  lives (a derived measurement vs. a results concept). Its own design proposal first.
- **Product (Beta Readiness):** run the user-testing protocol (the experiment workflow is now
  testable end-to-end), then the High tier (H2-H5).
- **Science:** unchanged - the open Validation Queue items await suitable golden measurements.

---

## 2026-06-29d - Multi-input processing & difference datasets (Phase 2C, ADR-0030)

Generalized the processing framework from single-input to **multi-input**, validated by the first
two-input operation. The design proposal's decisive finding - **the engine and the provenance DAG
were already multi-input** (OHD-2) - turned 2C from a redesign into a generalization of existing
seams, with **zero** changes to `core/provenance` or the persistence format. The user approved with
one refinement (a general `image.arithmetic`, not a hardcoded "difference"), which was adopted.

### Completed
- **Framework (`processing/step.py`):** new `InputSpec` (the dataset counterpart of
  `ParameterSpec`); `ProcessingStep.input_specs()` defaulting to a single `"primary"` slot (so every
  existing step is unchanged); `check_compatibility(inputs) -> tuple[str, ...]` (default empty);
  `apply` now validates that provided inputs match the declared slots and **enforces** compatibility
  (raises `ProcessingError`; incompatible inputs are refused, never resampled). Exported `InputSpec`.
- **First multi-input op (`processing/image/arithmetic.py`):** a **general** two-input
  `image.arithmetic` (modes `a_minus_b` / `b_minus_a` / `absolute_difference`; extensible to
  sum/ratio/normalized difference), inputs `primary` (A) + `secondary` (B). Operates on the channel's
  real value view (amplitude for complex; no phase differencing), result a single real `{channel}_diff`
  channel; `required_capabilities=(SPATIAL_2D,)`. `check_compatibility` requires same kind / dims /
  coordinates / channel presence + complex-ness. A Knowledge Center article was added (no-drift).
- **`describe`:** `OperationInputSlot` + `OperationDescription.inputs` (projected from `input_specs()`);
  single-input ops project one `primary` slot (backward compatible).
- **GUI:** `ExplorerModel.preview_operation(step_id, params, inputs=None)` generalized;
  `OperationOption` gained the non-primary input slots; the Processing Workspace renders a dataset
  **picker per extra slot** (candidates supplied by the window from the whole project), gates Preview
  when no second dataset exists, and runs the **same** Preview -> Accept flow; the two-parent result
  appends to the **active (primary) measurement's** history. Incompatible picks surface through the
  existing preview-error path. Single-input operations render exactly as before.

### Decisions
- **ADR-0030.** Declare inputs with `InputSpec`; enforce a per-op `check_compatibility`; a multi-parent
  derived dataset is owned by the **primary** measurement's history (Measurement.datasets is an ordered
  snapshot list, not a single-parent chain) while its DAG records both parents - so provenance,
  persistence, and the inspector need no changes. The first op is a general arithmetic (mode enum), not
  a special "difference" (user refinement). Declarative compatibility deferred (Rule 7). No silent
  resample/align (OHD-6).

### Issues Found
- A pre-existing `_CombineAdd` test step exercised multi-input `apply` but did not declare its slots;
  the new slot-validation correctly flagged it - fixed by giving it `input_specs()` (it now validates
  the new API). The Knowledge no-drift test caught the missing `image.arithmetic` article (added). Both
  are the guardrails working as intended.

### Tests / gates
- 500 tests (up from 478, +22): `test_processing.py` (+5 framework: default/declared slots,
  slot-mismatch, compatibility enforcement + default), `test_processing_image_arithmetic.py` (11:
  known-answer A-B/B-A/|A-B| on real + complex-amplitude, non-mutation, two-parent provenance + both
  sources, compatibility refusals), `test_describe.py` (+2 slot projection), `test_project_store.py`
  (+1 two-parent dataset round-trips with full DAG), `test_gui_arithmetic.py` (3: picker + gating,
  preview/accept appends a two-parent dataset, incompatible refusal). `ruff` clean; `mypy --strict`
  clean (105 files); Qt-free invariant green.

### Documentation Updated
- `docs/decisions.md` (ADR-0030), `docs/architecture.md` (processing multi-input), `docs/processing-
  engine.md` (multi-input example + `InputSpec`/`check_compatibility` extension steps). `LOG.md` (this
  entry), `NEXT.md`, `CLAUDE.md` status, project memory.

### Next Recommended Actions
- **The processing foundation is now complete** (single + multi-input). Future processing operations
  - including more arithmetic modes (sum / ratio / normalized difference) and any other two-input
  combination - extend `image.arithmetic`'s mode enum or add a step with `input_specs()`; no further
  framework work is required.
- **Product (Beta Readiness):** run the user-testing protocol; then the High tier (H2-H5).
- **Science:** unchanged - the open Validation Queue items await suitable golden measurements.

---

## 2026-06-30 - Core scientific operations (Phase 3A)

First expansion of the *scientific toolbox* on the now-complete processing framework (no
architecture change). Driven by a research+design proposal (what researchers do on almost
every dataset) the user reviewed and approved, with one refinement: include amplitude
normalization (so the toolbox spans one universal AFM op + one SNOM phase op + one SNOM
amplitude op). Generic image filters (Gaussian/median blur), FFT/power-spectrum, and
histogram/threshold were **deferred** (resolution loss / analysis-not-derivation - they
belong in Diagnostics, not the Processing Workspace); 2-D polynomial background was found
**already covered** by `image.plane_level` (order 2/3).

### Completed
- **`image.fix_zero`** - shift a real channel so its minimum (default) / mean / median is
  zero (a defined height datum; constant offset only, tilt/curvature untouched). Universal
  AFM step; closes beta-readiness **H3**. `required_capabilities=(SPATIAL_2D,)`.
- **`image.phase_offset`** - re-reference a complex channel's phase by a constant: the
  **circular mean** (default, `angle(mean(O))` - cyclic-correct; an arithmetic mean of
  wrapped angles would be wrong near +/-pi) or a chosen `value_rad`. `O -> O*exp(-i*dphi)`,
  amplitude preserved; updates `phase_reference` and sets the channel `state="referenced"`
  (the explicit, recorded re-reference OHD-6D requires). `required_capabilities=(COMPLEX_OPTICAL,)`.
- **`image.normalize_amplitude`** - divide a complex channel by its peak (default -> [0,1])
  or mean amplitude; phase preserved, amplitude dimensionless, `state="normalized"`.
  `required_capabilities=(COMPLEX_OPTICAL,)`.
- Each is a single-input `ProcessingStep` -> appears in the Processing Workspace, Preview,
  Accept, provenance, persistence, and export **automatically, with no GUI code**. Each
  module docstring documents the scientific rationale + the basis for its default behaviour
  (published practice / Gwyddion / WSxM / ImageJ / common lab workflow) for future
  maintenance, and each has a Knowledge Center article (no-drift invariant).

### Decisions
- **No ADR.** Phase 3A adds settled-science *operations* (Category A in the scientific-
  validation triage), not new abstractions, diagnostics, or recommendation rules - so the
  bar is a known-answer test (Rule 6), not a validation study. No architectural change.
- Region-based (substrate) phase/amplitude referencing - the richest quantitative form -
  is deliberately **deferred**: it needs a region-parameter framework addition; the
  whole-image/constant versions shipped here are valid and complete on their own.

### Tests / gates
- 517 tests (up from 500, +17): `test_processing_image_core_ops.py` - known-answer
  (fix_zero min/mean/median->0; phase_offset constant exact + amplitude preserved + the
  **circular-mean** pin `angle(mean(O'))~0`; normalize_amplitude peak->1 / mean->1 + phase
  preserved), non-mutation, recorded provenance, metadata (phase_reference / channel state /
  amplitude_unit), and validation refusals (wrong channel kind / missing / zero-amplitude).
  `ruff` clean; `mypy --strict` clean (109 files); Qt-free invariant green.

### Documentation Updated
- `CLAUDE.md` (operation vocabulary + 517), `docs/processing-engine.md` (registered-ops
  catalogue: the three new ops + `image.arithmetic`). Three Knowledge Center articles.
  `LOG.md` (this entry), `NEXT.md`, project memory. (No architecture-doc change - none
  needed.)

### Next Recommended Actions
- **Product (Beta Readiness):** run the user-testing protocol - real neaPLOT users will
  confirm/reorder the next operations (and the High tier H2-H5). The toolbox now covers the
  most universal post-load steps on both the topography and optical tracks.
- **Future toolbox:** region-based referencing (Phase 3B, needs a region parameter);
  despike/scar removal; further `image.arithmetic` modes (sum / ratio / normalized
  difference) - each extends the existing framework with no new architecture.
- **Science:** unchanged - the open Validation Queue items await suitable golden measurements.
