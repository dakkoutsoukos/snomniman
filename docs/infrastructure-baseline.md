# Infrastructure Baseline

**Status:** Established 2026-06-22. Reproducible dev environment verified; repo
under version control with an initial baseline commit.

This records the first verified, reproducible development baseline for SNOMNIMAN
before Phase 1 implementation. It is an infrastructure record, not an architecture
document; no architecture decisions were changed.

---

## Environment

- **OS:** Windows 11 (win32).
- **Python:** CPython 3.13.7 (`C:\Users\dakko\AppData\Local\Programs\Python\Python313`).
- **uv:** 0.11.23 (installed via `pip install uv`; on this machine the uv
  executable lives in the Python Scripts directory).
- **Virtual environment:** `.venv` created by `uv sync` (git-ignored).
- **Lockfile:** `uv.lock` generated and committed for reproducibility.

Key resolved package versions (42 resolved, 34 installed + the editable
`snomniman` project):

| Package | Version |
|---|---|
| numpy | 2.5.0 |
| scipy | 1.18.0 |
| xarray | 2026.4.0 |
| zarr | 3.2.1 |
| h5py | 3.16.0 |
| matplotlib | 3.11.0 |
| pytest | 9.1.1 |
| ruff | 0.15.18 |
| mypy | 2.1.0 |

Reproduce the environment with:

```bash
uv sync                 # backend + dev tools (default group)
uv sync --extra gui     # also the Qt GUI dependencies
```

## Validation Results

All run via `uv run` against the project venv (working dir = project root).

| Check | Command | Result |
|---|---|---|
| Tests | `uv run pytest` | **3 passed** in 0.05s (`tests/test_smoke.py`) |
| Lint | `uv run ruff check .` | **All checks passed** |
| Types | `uv run mypy .` | **Success: no issues found in 10 source files** |

Notes:
- mypy emits one **informational** note ("unused section(s): module =
  ['pyqtgraph.*', 'scipy.*', 'zarr.*']") because those override entries target
  libraries not yet imported by any code. The note does not affect the result
  (exit 0); the entries are intentionally retained for imminent Phase 1/2 use.
- **Update 2026-06-25 (Phase 1 code landed):** with application code present,
  `mypy --strict` checks **27 source files**, exit 0; `pytest` reports **55
  passed**. Two tooling changes were required: (1) mypy `python_version` raised
  `3.11 -> 3.12` because numpy 2.5's type stubs use PEP 695 `type` statements that
  mypy parses only at >=3.12 (runtime floor stays 3.11 via `requires-python`;
  ruff still targets py311). (2) The unused-override note now narrows to
  `['pyqtgraph.*']` only (scipy/zarr resolve once imported); pyqtgraph is the
  optional GUI extra, retained for the GUI phase.
- The LF -> CRLF warnings from `git add` on Windows are Git's autocrlf notice;
  the repository stores LF. (A `.gitattributes` enforcing `eol=lf` is an optional
  future nicety; not added to keep this baseline minimal.)

## Backend Separation Validation (Rule 4)

The backend/Qt-free invariant passes both as a unit test
(`tests/test_smoke.py::test_backend_is_qt_free`) and via an explicit check under
the venv: importing `snomniman.core`, `snomniman.io`, `snomniman.processing`,
`snomniman.pipeline`, and `snomniman.batch` loads **no** Qt toolkit modules
(`PySide6`/`PyQt5`/`PyQt6`/`shiboken6`/`pyqtgraph`). Backend remains
GUI-independent.

## Repository State

- **Git initialized** at the project root on branch **`main`** (`git init -b main`).
- **Initial commit created** with the complete Phase 0 baseline (this commit):
  docs, package scaffold (`src/snomniman/**`), tests, `pyproject.toml`, `uv.lock`,
  and the orientation/infra docs. The commit hash is reported to the operator
  (see `git log --oneline -1`).
- **Committed:** source, tests, all `/docs`, `CLAUDE.md`/`LOG.md`/`NEXT.md`,
  `pyproject.toml`, `.gitignore`, and `uv.lock`.
- **Excluded** (git-ignored): `.venv/`, `.obsidian/` (stray editor state),
  `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`.

## Continuous Integration

**Status:** Added 2026-06-23. GitHub Actions workflow at `.github/workflows/ci.yml`.

The CI workflow runs on every `push` and `pull_request` and enforces the same
gates verified locally above.

| Step | Command | What it enforces |
|---|---|---|
| Install dependencies | `uv sync` | Lockfile-exact environment installs cleanly |
| Lint | `uv run ruff check .` | Style and import correctness |
| Type check | `uv run mypy .` | Static type safety (strict mode) |
| Tests | `uv run pytest` | Correctness + backend Qt-free invariant (Rule 4) |

The backend/Qt-free invariant (`test_backend_is_qt_free`) is part of the pytest
suite, so the Tests step also enforces the GUI/backend separation automatically.

CI uses `ubuntu-latest` with Python 3.13 (matching the local CPython 3.13.7
baseline) and installs `uv` via `astral-sh/setup-uv@v5`.

---

## Remaining Phase 1 Blockers

- **Genuine blocker:** a real **neaSNOM imaging** sample file (the golden file)
  is required to implement and validate the Phase 1 reader. The Dataset/Metadata/
  Provenance schemas can be built and unit-tested with synthetic data in the
  meantime.
- **Done (2026-06-23):** CI workflow added at `.github/workflows/ci.yml` — runs
  `pytest` + `ruff` + `mypy` on push and pull_request.

No decision or architecture blockers remain - all OHDs are resolved
(`decisions.md`). The repository is reproducible, validated, and under version
control, and is ready for Phase 1 implementation.
