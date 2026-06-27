# NEXT.md - Immediate Priorities

Single source of truth for "what should the next session work on?" Keep current:
when a task is done, move it to `LOG.md` and update this file.

**Last updated:** 2026-06-27 (scientific vocabulary: reference_normalize, phase_unwrap, crop)

---

## Current Phase

**Phase 1 is COMPLETE** (backend + Zarr round-trip) and the **read-only Measurement
Explorer is COMPLETE**: understand -> compare -> measure -> publish, all without
ever changing the measurement.
- **Quantitative visualization:** colorbar + histogram with units, interactive
  contrast (display-only), cross-channel cursor readout under the image.
- **Comparative exploration:** side-by-side presets with synchronized
  zoom/pan/cursor (crosshair in every pane + shared readout) + harmonic contact sheet.
- **Quantitative measurement:** draggable line / rectangle / polygon overlays
  (read-only, amber, live): line **profile** across every visible channel with
  length/dx/dy, **ROI statistics** per channel, a session history (rename/hide/delete).
- **Publication export:** save the current view (single / comparison / harmonic /
  measurement) as a publication figure (PDF/PNG/SVG) with colorbars, scale bar,
  overlays, and a **provenance sidecar** (measurement + sha256, channels, ranges,
  colormaps, conventions, software versions, timestamp) that **regenerates** the
  figure. `viz.figure` (Qt-free matplotlib).

These closed Must-haves #1-#4 from `docs/product-review-v0.1.md`. Verified on the real
CdO measurement (publication figures render at quality; a region's Z height reads
835.9 nm). `ruff`, `mypy --strict`, and `pytest` (157 passed) are green; the backend
stays Qt-free. Committed on `main`.

**The project is now ready for PROCESSING** - the first features that *change* data
(as recorded, non-destructive derivations).

Launch: `python -m snomniman.gui [measurement-directory]` (requires the `gui`
extra: `uv sync --extra gui`).

Implemented:
- Backend (no Qt): `snomniman.core`; `snomniman.io` (gsf, neasnom, registry,
  zarrstore); `snomniman.viz` (**render** - display-ready data + `level_range`
  contrast modes: honest amplitude/phase, colormaps, ranges, extent, scale bar).
- GUI (PySide6 + PyQtGraph, read-only): `snomniman.gui` (**model** - Qt-free
  presenter; **imageview** - colorbar/histogram/contrast/readout;
  **panels/window** widgets; **colormap**; **app/__main__** entry point).

**Now implemented since:** processing engine + a growing operation vocabulary
(`image.plane_level` with full Explorer Preview->Accept/Cancel; plus
`image.reference_normalize`, `image.phase_unwrap`, `image.crop` - first-class in the
engine/provenance/Description API/Diagnostics/AI, validated, but not yet wired into
the Explorer preview UI), provenance-preserving figure export, the Scientific
Description API, the Scientific Diagnostics Engine (+ Explorer Diagnostics tab), and
the AI Scientist v1 - a deterministic **Scientific Briefing** (+ Explorer Briefing
tab; provider seam, no model SDK).
**Still NOT implemented (out of scope so far):** a generic Explorer operation panel
(registry/`param_specs`-driven) to preview the newer ops; a concrete AI narrative
provider (only the seam exists); AI recommendations/execution; batch; further
operations (`image.line_flatten`, masking, background subtraction); and Zarr-export of
derived datasets from the GUI.

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
14. [x] **Line profile + distance + ROI statistics** (mean/median/min/max/std,
    area) across every visible channel; draggable read-only overlays + a session
    history (rename/hide/delete). *Done 2026-06-26:* `viz.measure` (validated math)
    + model methods + `gui.measurement` (controller/panel).
15. [x] **Provenance-preserving export** - save the current view as a publication
    figure (PDF/PNG/SVG) with colorbars/scale bar/overlays + a provenance sidecar
    that regenerates it. *Done 2026-06-26:* `viz.figure` (FigureSpec, render, export,
    render_from_record) + model `figure_spec` + GUI "Export figure...".
    **This completes the read-only Explorer.**
16. [x] **Processing engine framework** - `ProcessingStep` ABC + `ParameterSpec` +
    step registry (`register`/`get_step`/`list_steps`). Every future operation
    must use this machinery. `ProcessingError` added to `snomniman.core`.
    39 tests covering registration, param validation, immutability, provenance
    (step_id/version/params/software/inputs), multi-input DAG, JSON serialization,
    and chained DAG round-trip. `docs/processing-engine.md` created.
    *Done 2026-06-26.*
17. [x] **First processing derivation: `image.plane_level`** - polynomial plane /
    surface fit (order 1-3) on a real-valued channel; Preview → Accept/Cancel
    workflow in the Explorer; linear history stack with "Back" navigation.
    Validated analytically (tilted plane residual ≈ 0, paraboloid residual ≈ 0).
    33 GUI integration tests + 23 backend tests. *Done 2026-06-26.*
18. [x] **Scientific Description API (`snomniman.describe`)** - a Qt-free, read-only
    layer projecting the scientific core + the step registry into structured,
    JSON-serializable descriptors (`describe_measurement` / `describe_channels` /
    `summarize_metadata` / `summarize_provenance` / `describe_operations`). Built for
    *present-day* consumers (Explorer, export, reports, debugging, tests); a future
    AI layer is one more client (Rule 7 - justified by today's architecture, not by
    AI). The Explorer's provenance view is wired as the first live consumer (output
    unchanged). 11 tests incl. a real-data golden, a JSON round-trip, and the
    non-mutation invariant. ADR-0018; `docs/description-api.md`. *Done 2026-06-26.*
19. [x] **Scientific Diagnostics Engine (`snomniman.diagnostics`)** - a Qt-free
    layer that *computes* deterministic facts about a dataset (per-channel
    statistics, topography slope/roughness/height range, optical amplitude decay,
    per-operation applicability) and the Explorer's **Diagnostics tab** that shows
    them. `ProcessingStep` now declares `required_capabilities`
    (`image.plane_level` -> `SPATIAL_2D`) so applicability is a data-driven fact.
    Sibling of `describe` (computation vs projection), justified by the Explorer
    today (Rule 9), not the future AI (Rule 7). Defensible metrics only - SNR,
    clipping, drift deferred rather than guessed (Rule 6). 18 new tests
    (known-answer/analytical); 274 total green. ADR-0019;
    `docs/diagnostics-engine.md`. *Done 2026-06-26.*
20. [x] **AI Scientist v1 - Scientific Briefing (`snomniman.ai`)** - a Qt-free layer
    that composes `describe` + `diagnostics` into a deterministic measurement
    orientation (`build_briefing`): three fact sections (Summary / Observations /
    Enables), each statement source-tagged. Optional AI narrative via a
    `NarrativeProvider` seam (protocol + grounded prompt builder + network-free mock);
    **no model SDK bundled**. Explorer **Briefing** tab (facts always; "no provider
    configured - facts are complete and authoritative" otherwise; copy action).
    Orientation only - no recommendations/execution. Two permanent AI rules added to
    `CLAUDE.md` (reason only over deterministic facts; always a deterministic
    fallback). 15 new tests (no external API); 289 total green. ADR-0020;
    `docs/ai-scientist-v1.md`. *Done 2026-06-27.*
21. **Concrete AI narrative provider** - add ONE real provider behind the existing
    `NarrativeProvider` seam as an *optional* extra (`uv sync --extra ai`),
    lazy-imported, never required for backend/CI; wire a "provider" selection so the
    Briefing's interpretation renders when configured. Tests mock the provider; CI
    never calls a network. (Design note: a major dependency - needs its own ADR.)
22. [x] **Scientific vocabulary: reference_normalize, phase_unwrap, crop** - three
    new `ProcessingStep` operations in `snomniman.processing.image`, each first-class
    everywhere (engine/provenance/Description API/Diagnostics/AI) with NO changes to
    those layers (propagation proven by tests). `image.reference_normalize` is
    single-input (signal + reference share one measurement: `O{n}/R_O{n}`), not the
    two-dataset case the old note assumed; phase re-reference is explicit/recorded
    (OHD-6D). `image.phase_unwrap` adds an unwrapped-phase channel (OHD-4), numpy-only
    2-D unwrap. `image.crop` slices to an nm region and updates scan geometry. 16 new
    tests (analytical/known-answer + propagation); 305 total green. Rule-2 note:
    `polynomial_flatten` NOT added (plane_level already does polynomial surface
    flatten). `docs/processing-engine.md`. *Done 2026-06-27.*
23. **`image.line_flatten`** - per-scan-line polynomial subtraction (removes
    line-to-line offsets/drift); the genuinely-new flattening verb (distinct from the
    surface flatten plane_level already provides). Same pattern: register, declare
    `required_capabilities` (`spatial_2d`), validate analytically.
24. **Generic Explorer operation panel** - make the Process panel registry-driven:
    list registered ops, build a parameter form from each op's `param_specs()`
    (channel combos for `str` channel params, spin boxes for numbers), and route
    Preview->Accept/Cancel through a per-op preview. Replaces the plane-level-specific
    `_on_preview_requested(channel, order)` wiring (and its ~30 tests). A deliberate UI
    task - the only piece of the new vocabulary not yet usable in the GUI.
25. **Concrete AI narrative provider** - add ONE real provider behind the existing
    `NarrativeProvider` seam as an *optional* extra (`uv sync --extra ai`),
    lazy-imported, never required for backend/CI; wire provider selection so the
    Briefing's interpretation renders when configured. Tests mock the provider; CI
    never calls a network. (A major dependency - needs its own ADR.)

**Deferred refinements (read-only, lower priority):** mirror a measurement overlay
into every comparison pane (results are already multi-channel); a measurement
"snap to pixel"/numeric-entry mode; verbatim vendor-header view; measurement export.

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
