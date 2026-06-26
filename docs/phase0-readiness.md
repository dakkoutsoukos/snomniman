# Phase 0 Readiness

**Status:** Phase 0 COMPLETE. Phase 1 is fully unblocked and ready to begin.
**Last updated:** 2026-06-23

This document answers: **is the project ready to begin Phase 1, and what remains?**
All Outstanding Human Decisions are resolved (`decisions.md` -> "Decision Closure").

---

## Completed

**Decisions** - all nine OHDs resolved and applied throughout the repo:
- OHD-1 name **SNOMNIMAN / `snomniman`** (package renamed from `snom`)
- OHD-2 **provenance DAG** (multi-input)
- OHD-3 **Zarr** canonical store; vendor reads via readers (GSF directory for neaSNOM; h5py for future HDF5 formats)
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
  the superseded `h5netcdf`; `h5py` retained for future HDF5-based vendor reads),
  `.gitignore`, `README.md`, tests.

## Remaining Human Decisions

**None.** OHD-1..9 are closed (see `decisions.md`). No design decision blocks
Phase 1.

## Remaining Infrastructure Tasks

**All done (as of 2026-06-23):**
- [x] `uv` installed (0.11.23); `uv sync` green; `pytest` / `ruff` / `mypy` pass.
- [x] CI workflow added (`.github/workflows/ci.yml`; push + PR triggers).
- [x] `git init` + initial baseline commit on branch `main`.
- [x] Real neaSNOM measurement data present at `SNOM Sample Files/` (GSF directory
      format; see `docs/measurement-discovery.md`).

## Risks

- No remaining Phase 1 gates. All infrastructure and sample data are in place.
- No open architectural or scientific risks: the OHD closure settled the items the
  review flagged (provenance DAG, Zarr/complex storage, unwrapped phase, affine/
  convention values, dispatch model, metadata-as-provenance, traceability).
- **Format assumption corrected (non-blocking):** the neaSNOM reader targets GSF
  measurement directories, not HDF5 single files. This is contained within the
  reader implementation and requires no architecture changes (see
  `docs/measurement-discovery.md`).

## Recommended Next Action

**Begin Phase 1** - the backend vertical slice is fully unblocked:
Dataset model -> Metadata schema -> Provenance schema -> GSF measurement-directory
reader -> golden-file tests (`roadmap.md` Phase 1; `NEXT.md`).

Phase 0 is **complete** with respect to its purpose (decisions resolved, repo
consistent and documented). The remaining items are infrastructure and a sample
file, not design - so Phase 1 implementation can begin.
