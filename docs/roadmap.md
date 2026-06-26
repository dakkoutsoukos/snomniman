# Roadmap

**Status:** Phase 0 complete (decisions + documentation); Phase 1 ready to begin.
**Last updated:** 2026-06-23

Phased plan from foundation to a publication-grade tool. Sequenced so a real file
reaches the data model early (the vertical slice, ADR-0015), then the
reproducibility backbone exists before features pile on it, with scientific
correctness validated as we go. Optimization and extensibility are deliberately
late (Rules 1, 7).

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

## Phase 1 - Vertical slice: neaSNOM imaging reader (backend only)  [ADR-0015]

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

## Phase 2 - Core data model & I/O (breadth)

- Full `snomniman.core`: complex + unwrapped-phase accessors, channel state, the
  hybrid dispatch capabilities, typed exceptions.
- `snomniman.io`: registry hardened; readers for more modalities (point spectra,
  approach curves, hyperspectral); canonical **Zarr** persistence with round-trips.
- Synthetic dataset generators (image, spectrum, interferogram).

**Exit:** the supported DataKinds load and round-trip; generators back the suite.

## Phase 3 - Processing & provenance DAG

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

## Phase 4 - Interactive GUI (imaging): the Measurement Explorer

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

## Phase 5 - nano-FTIR spectroscopy

- `snomniman.processing.spectrum`: apodization, zero-fill, phase correction, FFT;
  reference normalization; baseline; atmospheric (H2O/CO2) correction (needs a
  reference line-list / clean reference - confirm availability); averaging.
- Spectral viewer in the GUI.

**Exit (Rule 6):** FFT pipeline validated against synthetic interferograms with
known spectra AND cross-checked against neaPLOT.

## Phase 6 - Hyperspectral & batch

- Hyperspectral cubes: spectral/spatial slicing, per-pixel spectra, band maps;
  viewer support. (Memory: copy-on-write + caching.)
- `snomniman.batch`: apply a DAG across a folder headlessly; per-result provenance
  + a run manifest.

**Exit:** a DAG defined interactively runs unchanged over a folder, emitting
reproducible outputs + manifest.

## Phase 7 - Publication export & polish

- `snomniman.viz`: vector figure export (PDF/SVG), physical sizing, scale bars,
  cyclic colormaps for phase; data export (CSV/Zarr/HDF5); human-readable
  provenance report.
- Performance profiling and targeted optimization **only now** (Rule 1).

**Exit:** publication-quality figure + data + provenance report from a project.

## Phase 8+ - Extensibility (only when justified)

Deferred until a concrete need exists (Rule 7): scripting API, additional vendor
readers, optional plugin/entry-point discovery, end-user packaging/installers.
Each will get an ADR before implementation.

---

## Cross-cutting risks & dependencies

- **Phase 1 is fully unblocked.** Real GSF measurement data is present; `uv`,
  CI, and git are in place. Implementation can begin.
- **Vendor format details are not assumed** (Rule 6); parsing is validated, and
  unknown fields are preserved verbatim. The neaSNOM format is GSF
  measurement directories (see `docs/measurement-discovery.md`).
- **Scientific conventions are settled** (OHD-6) and stored in metadata; readers
  convert to canonical (nm, lower-left origin) and record conversions in provenance.
- Documentation is ASCII/UTF-8 and internally consistent; the package is
  `snomniman` throughout.
