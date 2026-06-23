# Phase 0 Readiness

**Status:** Phase 0 COMPLETE (decisions + documentation). Phase 1 ready to begin
once the mechanical infra and the neaSNOM sample file are in place.
**Last updated:** 2026-06-22

This document answers: **is the project ready to begin Phase 1, and what remains?**
All Outstanding Human Decisions are resolved (`decisions.md` -> "Decision Closure").

---

## Completed

**Decisions** - all nine OHDs resolved and applied throughout the repo:
- OHD-1 name **SNOMNIMAN / `snomniman`** (package renamed from `snom`)
- OHD-2 **provenance DAG** (multi-input)
- OHD-3 **Zarr** canonical store; vendor reads via readers (h5py for HDF5)
- OHD-4 **unwrapped phase** a first-class channel
- OHD-5 full **reproducibility/traceability** (sources, DAG, steps, params,
  software + operation versions)
- OHD-6 **scientific conventions** in metadata: canonical unit **nm**, origin
  **lower-left / x-right / y-up**, phase **preserved as imported**
- OHD-7 metadata/calibration edits are **provenance-tracked**
- OHD-8 **hybrid dispatch** (DataKind + capabilities)
- OHD-9 first reader = **real neaSNOM imaging dataset**

**Design & documentation**
- Foundational docs updated and internally consistent: `vision`, `architecture`,
  `data-model`, `roadmap`, `decisions`, `architecture-review` (historical),
  `CLAUDE.md`, `README.md`.
- All docs ASCII/UTF-8; the package is `snomniman` throughout.

**Code & tooling scaffold**
- `src/snomniman/{core,io,processing,pipeline,viz,batch,gui}` - docstring-only, no
  application logic; imports verified, backend Qt-free invariant holds.
- `pyproject.toml` updated (name `snomniman`; deps now include **zarr**, dropped
  the superseded `h5netcdf`; `h5py` retained for vendor reads), `.gitignore`,
  `README.md`, tests.

## Remaining Human Decisions

**None.** OHD-1..9 are closed (see `decisions.md`). No design decision blocks
Phase 1.

## Remaining Infrastructure Tasks

(No decisions; mechanical, plus one user-provided input.)
- **Install `uv`** (absent on this machine), then `uv sync` and confirm
  `uv run pytest` / `ruff` / `mypy` are green. *(user may need to run the install)*
- **Add a CI workflow** (tests + lint + types + the dependency/Qt-free guard).
- **`git init`** and an initial commit (recommended before Phase 1 code).
- **Provide a real neaSNOM imaging sample file** - the golden file for Phase 1.
  *(user-provided)*

## Risks

- **Sample data is the only remaining Phase-1 gate.** Phase 1's reader cannot be
  validated (Rule 6) without a real neaSNOM imaging file. Likelihood medium,
  impact high if delayed - mitigated by keeping the slice backend-only so the
  data model can be built and unit-tested with synthetic data while the golden
  file is sourced.
- **`uv` not installed** blocks full toolchain verification; low risk, easily
  cleared.
- No open architectural or scientific risks: the OHD closure settled the items the
  review flagged (provenance DAG, Zarr/complex storage, unwrapped phase, affine/
  convention values, dispatch model, metadata-as-provenance, traceability).

## Recommended Next Action

1. **Infra (Claude, no decisions):** install/verify the `uv` toolchain, add CI,
   `git init` + initial commit.
2. **User:** provide a real neaSNOM imaging file (the golden file).
3. **Begin Phase 1** - the backend vertical slice, in order: Dataset model ->
   Metadata schema -> Provenance schema -> the neaSNOM imaging reader ->
   golden-file tests (`roadmap.md` Phase 1; `NEXT.md`).

Phase 0 is **complete** with respect to its purpose (decisions resolved, repo
consistent and documented). The remaining items are infrastructure and a sample
file, not design - so Phase 1 implementation can begin.
