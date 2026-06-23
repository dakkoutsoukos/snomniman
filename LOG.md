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
