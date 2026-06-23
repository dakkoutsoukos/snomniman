# NEXT.md - Immediate Priorities

Single source of truth for "what should the next session work on?" Keep current:
when a task is done, move it to `LOG.md` and update this file.

**Last updated:** 2026-06-22 (after the infrastructure baseline)

---

## Current Phase

**Phase 0 fully closed** (decisions + documentation + reproducible toolchain +
version-control baseline). **Phase 1 (vertical slice) is ready to implement.**

All Outstanding Human Decisions (OHD-1..9) are resolved; the package is
`snomniman`; the `uv` environment is installed and verified (pytest/ruff/mypy
green); the repo is under git on `main` with an initial baseline commit. **No
application code exists yet.**

Phase 1 is the **backend-only vertical slice**: a real **neaSNOM imaging** reader
into a validated `Dataset`. **No GUI, no advanced processing, no visualization**
beyond what validates the slice.

---

## Immediate Tasks

Ordered. `(user)` = needs a human action.

**A. Phase 1 entry infra**
1. [x] Install `uv`; `uv sync`; `uv run pytest`/`ruff`/`mypy` green. *(done 2026-06-22)*
2. [x] `git init` (branch `main`) + initial baseline commit. *(done 2026-06-22)*
3. [ ] **Add CI** (pytest + ruff + mypy + the dependency/Qt-free guard).
   Recommended, non-blocking - the toolchain is already verified locally.

**B. Sample data**
4. [ ] **Provide a real neaSNOM imaging file** `(user)` - the golden file Phase 1
   validates against. This is the only remaining gate.

**C. Phase 1 implementation - first milestone, in this order:**
5. **Dataset model** - `snomniman.core.Dataset` (+ `DataKind`/capabilities) for an
   imaging dataset, with canonical units (nm) and the lower-left/x-right/y-up
   convention. *(buildable now with synthetic data; not blocked by sample file)*
6. **Metadata schema** - typed `Metadata` storing conventions explicitly (OHD-6) +
   the verbatim vendor header.
7. **Provenance schema** - `StepRecord` + provenance DAG node (OHD-2/OHD-5).
8. **One real neaSNOM imaging reader** - `snomniman.io` reader (OHD-9) -> `Dataset`
   with correct dims, coords, canonical units, channels, metadata; unknown header
   fields preserved verbatim. *(gated on the golden file)*
9. **Golden-file tests** - real file -> expected `Dataset`; Zarr round-trip and
   raw-immutability invariants; backend stays Qt-free.

**Toolchain reminders:** `uv` lives in the Python Scripts dir (not on PATH on this
machine); invoke via its full path or add that dir to PATH. Run checks with
`uv run pytest` / `uv run ruff check .` / `uv run mypy .`.

---

## Blockers

- **A real neaSNOM imaging sample file (OHD-9 deliverable)** - the only remaining
  Phase-1 gate. Mitigation: build and unit-test the Dataset / Metadata / Provenance
  schemas with synthetic data while the golden file is sourced.

(`uv` install and git initialization are done; CI is recommended but not blocking.)

---

## Open Questions

**None.** All Outstanding Human Decisions (OHD-1..9) are resolved - see
`docs/decisions.md` ("Decision Closure"). Do not reopen settled decisions; a new
direction needs a new ADR.

---

## Definition of Done

**Phase 1 (vertical slice) is done when:**
- A real neaSNOM imaging file loads into a `Dataset` with correct dims,
  coordinates, canonical units (nm), channels, and metadata, **validated by
  golden-file tests** against known values / neaPLOT.
- The Dataset, Metadata, and Provenance schemas exist and are exercised by the slice.
- Zarr round-trip (save/load) and raw-immutability tests pass.
- The backend remains Qt-free (invariant green); `ruff` and `mypy` clean.
