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

## Remaining Phase 1 Blockers

- **Genuine blocker:** a real **neaSNOM imaging** sample file (the golden file)
  is required to implement and validate the Phase 1 reader. The Dataset/Metadata/
  Provenance schemas can be built and unit-tested with synthetic data in the
  meantime.
- **Recommended, non-blocking:** add a CI workflow that runs `pytest` + `ruff` +
  `mypy` + the dependency/Qt-free guard (the toolchain is verified locally; CI
  just automates it).

No decision or architecture blockers remain - all OHDs are resolved
(`decisions.md`). The repository is reproducible, validated, and under version
control, and is ready for Phase 1 implementation.
