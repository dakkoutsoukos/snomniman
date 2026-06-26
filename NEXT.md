# NEXT.md - Immediate Priorities

Single source of truth for "what should the next session work on?" Keep current:
when a task is done, move it to `LOG.md` and update this file.

**Last updated:** 2026-06-26 (comparative exploration: side-by-side + synced cursor)

---

## Current Phase

**Phase 1 is COMPLETE** (backend + Zarr round-trip) and the **read-only Measurement
Explorer** is now both quantitatively trustworthy *and* comparative:
- **Quantitative visualization:** every image has a colorbar + histogram with units,
  interactive contrast (default / full-range / exact min-max, display-only), and a
  cross-channel cursor readout beneath the image.
- **Comparative exploration:** side-by-side panes (presets: Amplitude/Phase,
  Optical/Topography, Sample/Reference, Harmonic series) with **synchronized zoom,
  pan and cursor** (one crosshair marks the same point in every pane + a shared
  readout), plus a clickable **harmonic contact sheet**.

These closed Must-haves #1 and #2 from `docs/product-review-v0.1.md`. Verified on the
real CdO measurement. `ruff`, `mypy --strict`, and `pytest` (124 passed) are green;
the backend remains Qt-free (subprocess-checked). Committed as milestones on `main`.

Launch: `python -m snomniman.gui [measurement-directory]` (requires the `gui`
extra: `uv sync --extra gui`).

Implemented:
- Backend (no Qt): `snomniman.core`; `snomniman.io` (gsf, neasnom, registry,
  zarrstore); `snomniman.viz` (**render** - display-ready data + `level_range`
  contrast modes: honest amplitude/phase, colormaps, ranges, extent, scale bar).
- GUI (PySide6 + PyQtGraph, read-only): `snomniman.gui` (**model** - Qt-free
  presenter; **imageview** - colorbar/histogram/contrast/readout;
  **panels/window** widgets; **colormap**; **app/__main__** entry point).

**Still NOT implemented (out of scope so far):** any processing/derivation,
editing, export, AI, batch, or writing derived datasets.

---

## Immediate Tasks

Ordered. `(user)` = needs a human action.

**A. Phase 1 entry infra**
1. [x] Install `uv`; `uv sync`; `uv run pytest`/`ruff`/`mypy` green. *(done 2026-06-22)*
2. [x] `git init` (branch `main`) + initial baseline commit. *(done 2026-06-22)*
3. [x] **Add CI** (pytest + ruff + mypy + the dependency/Qt-free guard).
   *(done 2026-06-23)* — `.github/workflows/ci.yml` runs on push and pull_request.

**B. Sample data**
4. [x] **Real neaSNOM measurement data provided** *(done 2026-06-23)* - GSF
   measurement directory present at `SNOM Sample Files/` (150x150px, 10 µm scan,
   5973 cm^-1, CdO NPs). See `docs/measurement-discovery.md`. Phase 1 is unblocked.

**C. Phase 1 implementation - first milestone [DONE 2026-06-25]:**
5. [x] **Dataset model** - `snomniman.core.Dataset` (+ `DataKind`/capabilities),
   canonical nm units, lower-left/x-right/y-up convention, complex amplitude/phase
   views, raw-array immutability.
6. [x] **Metadata schema** - typed `Metadata` (conventions explicit, OHD-6) +
   verbatim vendor header; JSON round-trip.
7. [x] **Provenance schema** - `StepRecord` + multi-input `ProvenanceNode` DAG
   (OHD-2/OHD-5) + software-version capture + DAG (de)serialization.
8. [x] **GSF measurement-directory reader** - `snomniman.io.neasnom` (OHD-9):
   channel discovery, geometry validation, complex assembly, documented flip to
   canonical origin, m->nm, `.txt` + GSF-header metadata; `RawSource` directory
   manifest anchor; reader registry + sniffing.
9. [x] **Golden-file tests** - real directory -> expected `Dataset`;
   raw-immutability invariant; backend stays Qt-free. *(Zarr round-trip: see D.10)*

**D. Phase 1 close-out / Phase 2 entry:**
10. [x] **Zarr persistence + round-trip** - canonical Zarr writer/reader
    implemented (`snomniman.io.zarrstore`: `write_zarr`/`read_zarr`); the
    `Dataset -> Zarr -> Dataset` invariant test asserts loss-less preservation of
    data, coords, units, conventions, metadata, provenance, and source on both a
    synthetic dataset and the real golden measurement. *Closed the last Phase-1
    DoD item (OHD-3). (done 2026-06-25)*

**E. First experience - read-only Measurement Explorer [DONE 2026-06-25]:**
11. [x] **`viz.render`** (Qt-free display-ready data) + **`gui` Explorer** (model,
    image view, channel browser, metadata/provenance inspectors, cursor readout,
    scale bar, channel switching, amplitude/phase toggle). Open->browse->inspect,
    strictly read-only. Verified on the real CdO measurement; 26 new tests.

**F. Next - product backlog from the v0.1 review (each must pass Rule 9):**

The authoritative prioritization lives in **`docs/product-review-v0.1.md`** (a
researcher's-perspective critique of the running Explorer). Its **Must have** list,
in impact order:
12. [x] **Colorbar + visible, adjustable contrast/levels** (with a histogram) +
    **relocated cross-channel cursor readout** (was the biggest confidence gap).
    *Done 2026-06-26:* `HistogramLUTItem` colorbar/histogram, default/full/manual
    contrast (display-only, via `viz.level_range`), readout moved under the image.
13. [x] **Multi-channel comparison** - side-by-side panes with a *synchronized
    cross-channel cursor* (crosshair in every pane + shared readout), comparison
    presets, and a harmonic contact sheet. *Done 2026-06-26:* `gui.comparison`
    (`ComparisonView`/`ContactSheet`) + model presets/`values_at`.
14. **Line profile + ROI statistics** (min/max/mean/std, area) - read-only.
    *(Now the top open Must-have.)*
15. **Provenance-preserving export** of the current view (a captioned figure, not a
    bare screenshot).
16. **First processing derivations** - topography leveling + reference normalization,
    as explicit, recorded, non-destructive steps. *Sequence after the exploration
    items above* (explore before you process); each step is provenance-recorded,
    never silent (OHD-6D); the Zarr store already persists the resulting DAG.

See the review's Should/Nice lists for AI orientation, a measurement library,
verbatim-header view, sessions, and a neaPLOT cross-check. **Strongly recommended
first:** watch two or three neaPLOT users narrate opening a measurement (real
user validation) before committing to the order above.

**Toolchain reminders:** `uv` lives in the Python Scripts dir (may not be on PATH);
invoke via its full path or add that dir to PATH. Run checks with
`uv run pytest` / `uv run ruff check .` / `uv run mypy .`. (The `.venv` interpreter
also works directly: `.venv/Scripts/python.exe -m pytest`.)

---

## Blockers

**None.** Phase 1 is complete; the slice runs end-to-end on real data and persists
to / loads from the canonical Zarr store with no loss. No Phase-1 items remain.

---

## Open Questions

**None.** All Outstanding Human Decisions (OHD-1..9) are resolved - see
`docs/decisions.md` ("Decision Closure"). Do not reopen settled decisions; a new
direction needs a new ADR.

---

## Looking ahead (identity, then GUI phase)

Three design docs now guide all future work and should be read before any GUI/AI code:
- **`docs/product-philosophy.md`** - the project's identity/soul: the core mental
  model (*"everything is a derivation of an immutable measurement"*), the enduring
  principles, and a 6-question decision litmus. **Check every future architectural,
  UI, AI, and workflow decision against it.**
- **`docs/measurement-explorer.md`** - the interaction-design blueprint for the
  **Measurement Explorer**, the central GUI experience (first-five-minutes, info
  hierarchy, navigation, AI-as-derivation, transparency, North Star). The spec to
  build the GUI from.
- **`docs/phase2-vision.md`** - the broader UX experience blueprint (personas,
  workflows, publication).

Build the **read-only Measurement Explorer** first (open -> browse channels ->
inspect metadata/provenance); no processing or AI authoring in that first cut.
None of these change the roadmap phase order or any settled decision.

**Working rule going forward (user direction):** the design layer is now complete
enough to build against - **no new design documents unless implementation exposes a
real problem.** The next high-leverage work is code: close D.10 (Zarr), then build
the Explorer.

---

## Definition of Done

**Phase 1 (vertical slice) is done when:** *(all met - Phase 1 COMPLETE)*
- [x] A real neaSNOM imaging file loads into a `Dataset` with correct dims,
  coordinates, canonical units (nm), channels, and metadata, **validated by
  golden-file tests** against known values. *(neaPLOT cross-check deferred.)*
- [x] The Dataset, Metadata, and Provenance schemas exist and are exercised by the slice.
- [x] Zarr round-trip (save/load) and raw-immutability tests pass.
  *(both done; round-trip validated on synthetic + real golden data, task D.10.)*
- [x] The backend remains Qt-free (invariant green); `ruff` and `mypy` clean.
