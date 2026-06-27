# Architecture

**Status:** Phase 0 complete; all OHD decisions applied. **Last updated:** 2026-06-23

Authoritative description of the system's structure, written before
implementation. When the architecture changes, this file changes in the same
commit, with rationale in [`decisions.md`](decisions.md).

---

## 1. Architectural goals and constraints

| Goal | Source | Architectural consequence |
|---|---|---|
| Scientific functionality independent of GUI | Rule 4 | Backend packages have **no Qt imports**; GUI depends on backend, never the reverse. |
| Reproducibility from raw + provenance | Rule 5 / OHD-5 | Raw data immutable; processing = serializable steps over a provenance DAG; sources, params, software + operation versions captured. |
| One coherent architecture | Rules 1-2 | Layered packages with a strict, acyclic dependency graph; new features extend abstractions. |
| Scientific correctness | Rule 6 | Explicit units/coords/conventions stored in metadata; validation against synthetic + reference data. |
| Avoid premature generalization | Rule 7 | Registry/dispatch instead of plugin systems; no cloud/distributed layers. |
| Maintainability | Rules 3, 8 | Small modules, single source of truth in `/docs`, continuous refactoring. |

## 2. Layered architecture

Dependencies point downward only (higher layers may import lower; never the
reverse). `core` imports nothing else in the project. There are no cycles.

```text
  +-------------------------------------------------------------+
  |                       snomniman.gui                         |   PySide6 + PyQtGraph
  |                 (views, widgets, app shell)                 |   NO scientific logic
  +-------------------------------------------------------------+
        | consumes
        v
  +----------------+   +-------------------+   +----------------+
  | snomniman.batch|-->| snomniman.pipeline|   | snomniman.viz  |
  | headless runs  |   | provenance DAG,   |   | display-ready  |
  | over many srcs |   | replay, (de)ser.  |   | data + mpl     |
  +----------------+   +-------------------+   | static export  |
                            | uses             +----------------+
                            v                          |
                     +-------------------+              |
                     |snomniman.processing|             |
                     | ProcessingStep ABC|              |
                     | step registry,    |              |
                     | concrete ops      |              |
                     +-------------------+              |
                            |                           |
  +----------------+   +-------------------+            |
  | snomniman.io   |-->|  snomniman.core   |<-----------+
  | reader registry|   | Dataset, DataKind+|
  | readers/writers|   | capabilities,     |
  +----------------+   | Metadata, units,  |
                       | RawSource,        |
                       | provenance VOs    |
                       +-------------------+
```

**Dependency rule (enforced):** `core` depends on nothing internal; nothing in the
backend imports `gui`; no cycles. Checked in CI (a dependency/import test; the
Qt-free part is already enforced by `tests/test_smoke.py`).

**Scientific Description API:** `snomniman.describe` is a Qt-free, read-only layer
(depends on `core` + `processing`; the `pipeline` tier) that projects the core and
the step registry into structured, JSON-serializable descriptors. It is consumed by
`gui`/`batch` (and later `ai`); `viz` stays `core`-only and does not use it. It adds
no state and performs no scientific computation. Full detail:
`docs/description-api.md` (ADR-0018).

**Scientific Diagnostics Engine:** `snomniman.diagnostics` is a Qt-free layer
(depends on `core` + `processing`; the `pipeline` tier) that **computes** objective,
reproducible facts about a dataset - per-channel statistics, topography slope/
roughness, optical amplitude decay, and per-operation applicability (read from each
step's declared `required_capabilities`). It is the **sibling** of `describe`:
`describe` *projects* what the core already knows (no computation), `diagnostics`
*measures* the dataset (computation). `describe` does not consume `diagnostics`;
consumers (`gui`/`batch`/future `ai`) compose the two. It never mutates a dataset and
adds nothing to the provenance DAG. Full detail: `docs/diagnostics-engine.md`
(ADR-0019).

**Future AI layer:** the long-term architecture adds a `snomniman.ai` analysis
layer that sits above `core` (consuming `Dataset`, `Metadata`, and `Provenance`,
via the `snomniman.describe` projection and the `snomniman.diagnostics` facts)
without modifying them. AI-generated outputs are recorded as provenance nodes. AI
is a first-class analysis subsystem, not a UI add-on. Full principles: `CLAUDE.md`
(AI Architecture Principles section) and `docs/ai-principles.md` (to be written when
AI design begins).

## 3. Module responsibilities

### `snomniman.core` - the data model (no I/O, no processing logic)
- `Dataset`: the central abstraction, wrapping an `xarray.Dataset` and adding SNOM
  domain semantics (data kind + capabilities, channel conventions, complex/
  unwrapped-phase accessors, typed metadata, the provenance node). See
  [`data-model.md`](data-model.md).
- `DataKind` + `Capability`: hybrid dispatch (OHD-8) - `DataKind` classifies for
  humans; capabilities determine supported operations.
- `Metadata`: typed container that stores scientific conventions explicitly
  (units, origin/axes, phase reference) plus the verbatim vendor header.
- `RawSource`: an immutable reference to an origin file (path, sha256, reader id,
  reader params). The anchor of reproducibility.
- `units`: canonical conventions (spatial unit = nm) and explicit conversion
  helpers; conversions applied to data are recorded in provenance.
- `provenance` (value objects): `StepRecord`, `ProvenanceNode` - pure data for the
  DAG. No dependency on `processing` (avoids a cycle).

### `snomniman.io` - import/export (depends on `core`)
- `registry`: maps format identifiers to reader callables; content-based sniffing
  dispatches to a reader (id encodes format+version). A registry, not a plugin
  system (ADR-0006).
- `readers/`: concrete readers. **First target (Phase 1): a GSF measurement-directory
  reader for neaSNOM imaging data** (OHD-9). A neaSNOM measurement is a directory
  of per-channel `.gsf` files (Gwyddion Simple Field format) plus a `.txt` parameter
  file; the reader assembles all channels into a single `Dataset`. `h5py` is retained
  for future HDF5-based vendor formats. Each reader returns a `Dataset` with correct
  dims, coords, canonical units, channels, and a populated `Metadata` + `RawSource`;
  unknown header fields preserved verbatim.
- `writers/`: persistence to the **canonical Zarr store** (OHD-3) and export of
  derived data (CSV, ...).
- **Validation note (Rule 6):** exact vendor formats are *not assumed*; readers
  are validated against real files and cross-checked against neaPLOT.

### `snomniman.processing` - operations (depends on `core`)
- `ProcessingStep` (ABC): the command pattern. A step has a stable `step_id`, a
  `version`, JSON-serializable `params`, named `inputs` (for multi-input ops), a
  `deterministic` flag, declared capability requirements, and
  `apply(...) -> Dataset`. Steps never mutate; they return a new `Dataset` whose
  provenance node appends one `StepRecord`.
- `registry`: `step_id -> ProcessingStep class`, populated by registration.
- Concrete operations by domain:
  - `image/`: crop, rotate, plane/polynomial leveling, line-by-line correction,
    phase offset/unwrap (explicit; produces a first-class unwrapped-phase channel),
    amplitude normalization, self-referencing.
  - `spectrum/`: apodization, zero-fill, phase correction, FFT, reference
    normalization, baseline, atmospheric correction, averaging.
  - `common/`: masking, unit conversion (recorded), statistics/ROI reduction.
  - Phase operations are always explicit and recorded - never silent (OHD-6D).

### `snomniman.describe` - the Scientific Description API (depends on `processing`, `core`)
- A Qt-free, **read-only** projection of the scientific core (`Dataset`, `Metadata`,
  provenance, `RawSource`) and the step registry into structured, typed,
  JSON-serializable *descriptors* (`MeasurementDescription`, `ChannelDescription`,
  `MetadataSummary`, `ProvenanceSummary`, `OperationDescription`, ...).
- Answers "what is this measurement, what does it contain, where did it come from,
  and what operations exist?" in one canonical place. Performs no scientific
  computation and never mutates inputs; reports honest values (`None` for unknown -
  formatting is a consumer concern).
- Exists for present-day consumers (Explorer, publication/provenance export,
  reports, debugging, tests); a future `ai` layer is one more client. It does **not**
  modify the processing engine and registers nothing itself.
- **Implemented.** See `docs/description-api.md` (ADR-0018).

### `snomniman.diagnostics` - the Scientific Diagnostics Engine (depends on `processing`, `core`)
- A Qt-free layer that **computes** objective, reproducible facts about a dataset:
  per-channel statistics (`ChannelStatistics`), topography slope/roughness/height
  range (`TopographyDiagnostics`), optical harmonic amplitude + decay
  (`HarmonicDiagnostics`), and per-operation structural applicability
  (`OperationApplicability`, from each step's declared `required_capabilities`).
- Computation is the line between this and `describe`: `describe` projects what the
  core already knows; `diagnostics` measures the dataset. They are siblings;
  `describe` does not consume `diagnostics`. Never mutates a dataset and adds nothing
  to the provenance DAG (reading a diagnostic is not an operation).
- Produces **facts, not opinions**: no recommendations, no LLM, no providers.
  Scientifically shaky metrics (SNR, clipping, drift) are deferred rather than
  guessed (Rule 6). The future `ai` layer composes these facts with `describe`.
- **Implemented.** See `docs/diagnostics-engine.md` (ADR-0019).

### `snomniman.pipeline` - reproducibility engine (depends on `processing`, `core`)
- The **provenance DAG** (OHD-2): nodes are operations with named inputs, allowing
  multi-input workflows (sample/reference normalization, background subtraction,
  calibration inputs, stitched scans).
- `replay`: reconstructs every derived dataset from sources + the DAG (Rule 5).
- `serialization`: DAG/Project <-> JSON (schemas in `data-model.md`).
- `environment`: captures `snomniman` + library versions and operation versions
  for full traceability (OHD-5).
- `Project`: sources + DAG (+ view state later). References raw files by path +
  hash; **never copies or mutates raw data.**

### `snomniman.viz` - visualization model and static export (depends on `core`)
- Backend-neutral display-ready data (array, physical extent honoring the
  lower-left origin convention, recommended colormap/limits, units, scale-bar
  spec) derived from a `Dataset`/channel.
- `matplotlib` export for publication figures (vector, cyclic colormaps for phase).
- Interactive PyQtGraph adapters consume this data at the `gui` boundary,
  keeping `viz` Qt-free.
- **Implemented:** `render` - the `RenderData` value object + `prepare_channel`
  (honest amplitude/phase, cyclic colormap for phase, robust ranges, lower-left
  pixel-edge extent) + `pick_scale_bar`. matplotlib static export not yet built.

### `snomniman.batch` - headless multi-dataset runs (depends on `pipeline`, `io`, `core`)
- Applies a DAG (or template) across many sources, emitting results + a per-result
  provenance record + a run manifest. Pure backend; no UI.

### `snomniman.gui` - application (depends on all backend; nothing depends on it)
- PySide6 application shell, PyQtGraph viewers, channel/LUT controls, ROI tools,
  and a **provenance panel** exposing/editing the graph.
- Strictly a consumer: it builds steps/graphs and calls the backend. **No
  scientific computation in widgets, dialogs, event handlers, or view classes**
  (Rule 4); every GUI feature must also satisfy Rule 9 (improve understanding).
- **Implemented:** the read-only **Measurement Explorer** - a Qt-free
  `ExplorerModel` presenter plus thin PyQtGraph/PySide6 widgets (image view,
  channel browser, metadata + provenance inspectors, cursor readout) and the
  `python -m snomniman.gui` entry point. Open/browse/inspect only; processing,
  editing, export, and AI authoring are not yet built. The package `__init__` does
  not import Qt, so the presenter and backend import without the `gui` extra.

## 4. Key patterns

### 4.1 Dataset as a labeled-array domain object
`xarray` provides named dimensions, coordinates, alignment, broadcasting, and
chunked (Zarr) I/O. `Dataset` adds the SNOM layer so domain code speaks in
channels (`O2`, `O3`, `Z`), kinds/capabilities, and canonical units. Rationale:
ADR-0001, ADR-0003.

### 4.2 Operations as serializable steps (command pattern)
A step is data (`step_id` + `inputs` + `params`) and behavior (`apply`). Because
the data half is serializable and the behavior is recoverable from the registry,
the provenance DAG is both executable and persistable - giving history, batch,
and reproducibility from one pattern. Rationale: ADR-0005.

### 4.3 Reproducibility via the provenance DAG
```text
sources (RawSource: path, sha256, reader)            [verified by hash]
    |  io.read
    v
Dataset (raw, immutable)  --+
                            |  step(params, inputs={...})   [each appends a StepRecord]
Dataset (raw, immutable)  --+        (multi-input: e.g. normalize sample by reference)
    v
Dataset (result; provenance node records inputs, params, software + op versions)
```
Serializing sources + DAG yields a Project JSON that reconstructs every result on
a machine with the same raw files. For steps declared **deterministic** on a
matching environment the reconstruction is bit-identical (fingerprint match);
otherwise it reproduces to a documented numerical tolerance. "Reproduce this
figure in 3 years" is a supported, auditable operation (OHD-5).

### 4.4 Reader registry (not a plugin system)
Formats register a reader under an id; the registry sniffs and dispatches. Adding
a vendor/format = implementing one reader interface + registering it (Rule 7).
Rationale: ADR-0006.

### 4.5 Backend/GUI separation
Enforced by the dependency graph and a CI import check. Every workflow is
exercisable from Python/pytest with no Qt event loop. The GUI is thin.

## 5. Data flow

- **Interactive:** open file -> `io` reader -> `Dataset` -> `gui` viewer -> user
  adds steps -> `processing` produces new `Dataset`s (nodes in the DAG) ->
  `viz`/`gui` render -> save `Project` (sources + DAG) -> `viz` exports figures.
- **Batch:** load a DAG/template -> `batch` iterates sources -> `pipeline.replay`
  per source -> results + provenance + manifest written by `io`.
- **Reproduce:** open `Project` JSON -> `pipeline.replay` against raw -> results
  (bit-identical for deterministic steps, else within tolerance).

## 6. Testing and validation strategy (Rule 6)

- **Synthetic generators** with analytically known answers (a plane removed
  exactly by leveling; an interferogram whose FFT spectrum is known).
- **Golden-file tests** for the neaSNOM reader (real file -> expected `Dataset`).
- **Invariant/property tests:** raw immutability; non-mutating steps; DAG replay
  determinism (per the deterministic flag); Zarr round-trips.
- **Reference cross-checks:** reader and key processing results vs neaPLOT.
- **Type checking** (`mypy`) and **linting** (`ruff`) are part of "done."
- **Dependency test:** assert the layer import rules hold (no cycles, no Qt in
  backend - already in `tests/test_smoke.py`).

## 7. Technology stack and rationale

| Concern | Choice | Why |
|---|---|---|
| Language | Python >= 3.11 | Scientific ecosystem; team familiarity. |
| Arrays / labeled data | NumPy, **xarray** | Named dims/coords/units/metadata; complex dtype; chunked I/O. |
| Numerics | SciPy | FFT, filtering, interpolation, optimization. |
| Canonical project store | **Zarr** (OHD-3) | complex-native, chunked, JSON attrs; large cubes + rich metadata. |
| Vendor file reading | format-specific readers (GSF for neaSNOM; h5py for HDF5-based formats) | vendor formats independent of the store. |
| Interactive GUI | **PySide6** (Qt) + **PyQtGraph** | Fast multi-dimensional interactive visualization. |
| Static export | matplotlib | Publication-quality vector figures. |
| Packaging / env | **uv** | Fast, reproducible environments and lockfile. |
| Lint / format | **ruff** | Single fast tool. |
| Types | **mypy** (strict) | Catch interface drift early. |
| Tests | **pytest** | Standard, fixtures, parametrization. |

Units are handled initially as **explicit metadata + conversion helpers**;
`pint`/`pint-xarray` is deferred (ADR-0008).

## 8. Cross-cutting concerns

- **Errors:** typed exceptions in `core` (e.g. `SnomnimanError`, `ReaderError`,
  `ProcessingError`); the GUI translates these into user-facing messages.
- **Logging:** standard `logging`; backend never prints. Provenance is *data*,
  not logs.
- **Configuration:** minimal, explicit; no hidden global state in the backend.
- **Injection safety:** metadata and headers from files are treated as **data**,
  never executed or interpreted as commands.

## 9. Explicitly deferred (Rule 7)

Plugin discovery / entry points, a user scripting console, cloud/remote compute,
multi-user collaboration, and performance optimization (until a measured need
exists, per Rule 1). Each remains a candidate recorded in `decisions.md` if and
when a concrete need appears.
