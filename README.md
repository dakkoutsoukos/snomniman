# SNOMNIMAN

Reproducible analysis of scattering-type SNOM (s-SNOM) and nano-FTIR data - a
modern, open desktop platform intended as a successor to neaPLOT. Python package:
`snomniman`.

> **Status: active development (pre-alpha, v0.2.0).** The backend (readers, processing
> pipeline, provenance DAG, batch runs, export) and the PySide6 GUI are implemented, along
> with spectral lineshape fitting, particle segmentation and a first Drude/Lorentz dielectric
> fit. Per `NEXT.md` (2026-07-20), 925 tests pass, with `ruff` and `mypy --strict` clean.
> The finite-dipole model, carrier-density analysis and watershed/hyperspectral segmentation
> are designed but not implemented. See [`NEXT.md`](NEXT.md) and [`LOG.md`](LOG.md).
>
> Developed by Demetrios Koutsoukos as AI-directed engineering with Claude Code, under the
> governance rules in [`CLAUDE.md`](CLAUDE.md). Real instrument data is not included in this
> repository; tests that need it skip when it is absent.

## Why

Near-field datasets are multi-channel and complex-valued (amplitude **and**
phase), come in several shapes (images, spectra, hyperspectral cubes, approach
curves), and are analyzed through sequences of convention-sensitive
transformations. SNOMNIMAN makes that analysis **transparent, reproducible, and
batchable**, with publication-quality export - backend-first, so every scientific
operation is testable without launching the UI.

## Documentation (single source of truth)

Start with `CLAUDE.md`, then `NEXT.md`, then `LOG.md`.

| Document | Purpose |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Project constitution: goals, principles, the 8 Rules, architecture/data-model summary. Read first. |
| [`NEXT.md`](NEXT.md) | Immediate priorities, blockers, open questions. Read second. |
| [`LOG.md`](LOG.md) | Append-only engineering journal / history. |
| [`docs/vision.md`](docs/vision.md) | Why, who, principles, success criteria, non-goals |
| [`docs/architecture.md`](docs/architecture.md) | Layered design, modules, patterns, tech stack |
| [`docs/data-model.md`](docs/data-model.md) | Datasets, channels, units, metadata, provenance schema |
| [`docs/roadmap.md`](docs/roadmap.md) | Phased plan and exit criteria |
| [`docs/decisions.md`](docs/decisions.md) | ADRs + the OHD Decision Closure |
| [`docs/architecture-review.md`](docs/architecture-review.md) | Historical adversarial review (findings now settled) |
| [`docs/phase0-readiness.md`](docs/phase0-readiness.md) | Phase 0 readiness: what is done and what remains |

## Core principles

Scientific correctness - reproducibility (raw is immutable; results reconstruct
from the provenance DAG) - backend independent of the GUI - one coherent
architecture - transparency of every transformation - simplicity that can evolve.

## Project layout

```text
SNOM/
  docs/                  authoritative design documents
  src/snomniman/         the package
    core/                data model (Dataset, DataKind + capabilities, Metadata, units, provenance VOs)
    io/                  reader registry, readers (neaSNOM imaging first), Zarr writers
    processing/          ProcessingStep abstraction + concrete operations
    pipeline/            provenance DAG, replay, (de)serialization, Project
    viz/                 display-ready data + matplotlib static export
    batch/               headless multi-dataset runs
    gui/                 PySide6 + PyQtGraph app (consumes backend only)
  tests/                 pytest; includes a backend-stays-GUI-free guard
```

## Development setup

Requires Python >= 3.11 and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync                 # backend + dev tools
uv sync --extra gui     # also install the Qt GUI dependencies

uv run pytest           # tests
uv run ruff check .     # lint
uv run mypy             # type-check
```

The scientific backend installs and tests **without** the `gui` extra, by design.
