# Packaging Notes - Phase 1 (Standalone Executable)

**Status:** Implemented and validated. **Date:** 2026-07-03.

This is the implementation record for **Phase 1** of
[`docs/deployment-strategy.md`](deployment-strategy.md): a standalone
`SNOMNIMAN.exe` that launches on a Windows machine with no Python, no `uv`, no
PowerShell, and no virtual environment. It is **not** the installer milestone
(Phase 2) - there are no shortcuts, no Start Menu entry, and no uninstaller
yet; this milestone proves the freeze itself works end to end against
SNOMNIMAN's real dependency stack and real sample data.

Per `deployment-strategy.md` Section 2.3, the tool choice was **PyInstaller,
`--onedir`** - already investigated and justified there. This document covers
what implementing that choice actually required.

---

## 1. What was added

| Path | Purpose |
|---|---|
| `pyproject.toml` | New `[project.gui-scripts]` entry (`snomniman-gui = "snomniman.gui.app:run"`) - a proper installed launcher, no console window. New `packaging` dependency group (`pyinstaller>=6.10`), **not** part of the default `dev` group, so ordinary backend dev/CI never installs it. |
| `packaging/snomniman_entry.py` | The PyInstaller freeze entry point. Not part of the `snomniman` package on purpose: PyInstaller analyzes a plain script, and `snomniman.gui.__main__` uses a relative import (`from .app import run`) that fails when a file is executed directly outside its package. This script does the absolute-import equivalent and is the one place the frozen build and the `python -m snomniman.gui` dev workflow diverge - both end up calling the identical `snomniman.gui.app.run`. |
| `packaging/make_icon.py` | One-off script (Pillow, already a transitive dependency via matplotlib) that generated `packaging/snomniman.ico` - no icon asset existed before this milestone. Draws a simple probe-tip-meets-near-field-wave mark rather than depending on an external design tool. Not part of the build; rerun manually only if the icon needs regenerating. |
| `packaging/snomniman.ico` | The generated application icon (7 sizes, 16-256 px), used for the `.exe` itself, its taskbar entry, and its window icon. |
| `packaging/snomniman.spec` | The PyInstaller build spec (see Section 2). |
| `packaging/make_version_info.py`, `packaging/version_info.txt` | Generates the Windows version-info resource from `pyproject.toml`'s version, embedded via `EXE(version=...)`. Added in the follow-up release-readiness audit (`docs/release-readiness-v1.md`) after that audit found the exe shipped with **no** version resource at all (blank publisher, `0.0.0.0`) - a real, visible red flag on a researcher's or IT department's file Properties dialog. |
| `packaging/build/`, `packaging/dist/` | PyInstaller's working directory and output. Already git-ignored (the repo's existing `build/`/`dist/` patterns match at any depth). |

No application code changed. No existing module, GUI behavior, or scientific
logic was touched.

---

## 2. The PyInstaller spec

`packaging/snomniman.spec` (onedir, windowed, icon-bearing):

```python
a = Analysis(
    [ENTRY],           # packaging/snomniman_entry.py
    pathex=[SRC],      # <repo>/src, so `snomniman` resolves like the editable install
    ...
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="SNOMNIMAN",
          console=False, icon=ICON)
coll = COLLECT(exe, a.binaries, a.datas, name="SNOMNIMAN")
```

Build with (packaging env synced via `uv sync --extra gui --group packaging`):

```
.venv/Scripts/pyinstaller.exe packaging/snomniman.spec --noconfirm \
    --distpath packaging/dist --workpath packaging/build
```

Output: `packaging/dist/SNOMNIMAN/SNOMNIMAN.exe` + a `_internal/` folder
(the onedir layout - everything the exe needs, alongside it, not embedded).

**`console=False`** (no console window) is the production setting. During
development the spec was temporarily flipped to `console=True` so PyInstaller
build/runtime errors surfaced as visible tracebacks instead of disappearing
silently; every fix in Section 3 was diagnosed that way before flipping back.

---

## 3. Hidden imports and bundled resources

The dependency surface here is non-trivial - `numpy`, `scipy`, `xarray`,
`zarr`, `h5py`, `matplotlib`, `PySide6`, `pyqtgraph` - and the honest finding
of this milestone is: **almost none of it needed manual hidden-import work.**
Two things did the heavy lifting, discovered before writing a single
workaround:

1. **`pyinstaller-hooks-contrib` (2026.6, installed automatically alongside
   PyInstaller 6.21) already ships maintained hooks for every one of the
   nonstandard packages above**: `hook-h5py.py`, `hook-numcodecs.py`,
   `hook-pyqtgraph.py`, `hook-xarray.py`, `hook-zarr.py`. `matplotlib` and
   `scipy` have hooks bundled directly in PyInstaller itself. These hooks
   handle exactly the failure modes `deployment-strategy.md` Section 2.1
   flagged as the real risk: Qt plugin discovery, matplotlib's data files,
   and - the classic PyInstaller/scientific-stack gotcha - packages that
   discover plugins via `importlib.metadata.entry_points()` (`zarr`'s codec
   registry, `xarray`'s backend/chunkmanager registry), which silently return
   nothing in a frozen build unless the package's dist-info metadata is
   explicitly copied in (`copy_metadata`, which `hook-zarr.py`/`hook-xarray.py`
   already do).
2. **SNOMNIMAN's own registry pattern is fully static-import-friendly.**
   Every `ProcessingStep` is registered by an explicit `from .module import
   Class` in `processing/image/__init__.py` / `processing/spectrum/__init__.py`,
   and `gui/model.py` explicitly does `import snomniman.processing.image` /
   `import snomniman.processing.spectrum` to trigger that registration
   (`description-api.md`'s documented pattern: "callers import the step
   registry sub-packages it cares about first"). PyInstaller's static
   modulegraph analysis follows ordinary imports automatically, so every
   registered operation, every Knowledge article, and every Manual page (all
   pure-Python data, no external resource files - confirmed by inspection:
   `find src/snomniman -type f ! -iname "*.py"` returns nothing) was bundled
   correctly with **zero** `hiddenimports` entries added to the spec.

**Two benign warnings**, seen once and not touched:

- `Hidden import "deprecated" not found!` - `hook-numcodecs.py` conditionally
  hidden-imports the `Deprecated` package only for `numcodecs >= 0.15.0`,
  guarding a code path our installed `numcodecs` version doesn't exercise.
  Harmless: nothing in the running app imports it either.
- `Hidden import "scipy.special._cdflib" not found!` - a known cosmetic
  mismatch between PyInstaller's `scipy` hook and current `scipy` binary
  layout; the module the hook expects has been renamed/reorganized upstream.
  No runtime path in this app touches it.

**No `datas`/`--add-data` entries were needed.** SNOMNIMAN bundles no
external resource files of its own (no icons, `.qss`, or data files inside
`src/snomniman` before or after this milestone); the one new resource
(`snomniman.ico`) is consumed directly by the spec's `icon=` argument, not
copied into the app bundle.

---

## 4. Validation

Validated by launching the actual frozen `SNOMNIMAN.exe` (not the dev venv)
against the real neaSNOM sample data
(`SNOM Sample Files/2026-06-16 14928/...`), driving it with real mouse/
keyboard input via Windows UI Automation, and screenshotting the live window
(`PrintWindow`, which captures a window's content even when occluded).

| Check | Result |
|---|---|
| Launch with no argument | Folder-chooser dialog opens (`app.py`'s existing no-path behavior - already worked, unchanged). Time to dialog: **~4.0 s** cold. |
| Open the CdO imaging measurement (`2026-06-16 190234 PH CdO Dense ROI 2`) | Loads and renders correctly - real GSF data, correct metadata (150x150 px, 10x10 um, 5973 cm^-1), correct channel tree (Optical/Mechanical/Topography/References). Time to fully rendered window: **~5.4 s** cold. |
| Diagnostics tab | Real computed facts render: plane tilt (10.2 nm/um), RMS roughness (28.5 nm), per-harmonic SNR/coherence classification, value histogram with percentiles - the full Diagnostics Engine executing scipy/numpy code in the frozen build. |
| Scientific Briefing tab | The deterministic Reasoning Rule Engine produces a real, evidence-backed recommendation ("Plane Level", with the measured tilt cited as evidence) - `ai.reasoning` + `ai.recommend` working end to end. |
| Processing Workspace: select "Plane Level", Preview, Accept | Real before/after comparison rendered (visible tilt removed in the "after" pane); Accept committed the derivation - window title changed to `... -> plane level (Z)`, the Measurements table's Processing column updated to `step`, confirming the provenance-recording accept path executes correctly in the frozen build. |
| Knowledge Center tab | Full curated article list renders and is searchable (Concepts: Apodization, Band maps, Demodulation harmonics, Hyperspectral cubes, Interferograms/ZPD, ...). |
| Manual tab | Full curated how-to-use-it page tree renders (Getting Started: Opening a measurement, Opening a spectrum, Your first five minutes; Explorer: Comparison mode, ...). |
| Open the point-spectroscopy measurement (`2026-06-16 212518 PH PSP CdO Dense ROI 2`) | The second data modality (`DataKind.LINE_SCAN`) loads correctly in a fresh instance: `SpectrumPlotView` with its position slider and curve render; image-only affordances (Amplitude/Phase, Optical/Topography) are correctly greyed out by the existing capability gating - proving `io.neasnom_spectrum` and the spectral GUI path both work unmodified in the frozen build. |
| File > Export > Processed Data (Zarr) | The menu action fires and opens the real native Windows Save dialog (confirmed via `EnumWindows` - a window titled "Export processed data (Zarr)" owned by the SNOMNIMAN process appeared), proving `_export_data_zarr`'s pre-dialog logic (default filename/path computation, `QFileDialog` integration) executes correctly in the frozen build. **Not completed to a written file**: driving the modern Windows common file dialog's internal controls via UI Automation from a non-message-pumping automation script hung repeatedly (a known limitation of automating that specific Windows dialog, not of SNOMNIMAN) and the dialog was closed (`WM_CLOSE`) rather than force through it. |

All of the above ran with `console=True` first (to catch any startup
traceback) and was re-confirmed once more after flipping to the final
`console=False` production build - identical behavior, no console window.

### Known validation gap (honest, not a packaging defect)

The interactive zarr **write** was not driven to completion in this session
(see the Export row above) - only the fact that the export dialog opens
correctly was confirmed. This exercises the same `zarr`/`numcodecs` bundling
that `hook-zarr.py`/`hook-numcodecs.py` are specifically designed for, and
every other zarr-adjacent import path (`xarray.backends.zarr`, which the app
imports on every single launch to build the in-memory `Dataset`) has already
executed successfully hundreds of times across every screenshot above - but
a real write-to-disk-and-reopen round trip through the frozen build's file
dialog is worth a five-minute manual check (click Export > Processed Data
(Zarr), save, reopen the `.zarr` folder) before the Phase 2 installer
milestone. Tracked in `NEXT.md`.

`h5py` is a declared dependency (imports cleanly - no build warnings) but is
not currently called from any code path in `snomniman` (`grep` confirms zero
uses outside the frozen build's own bundling); it is reserved for a future
vendor HDF5 reader, so there was nothing runtime-specific to validate for it
here beyond "it imports," which it does.

---

## 5. Build size and startup time

| Metric | Value |
|---|---|
| `SNOMNIMAN.exe` | 23 MB |
| `_internal/` (dependencies) | 277 MB |
| **Total onedir folder** | **~300 MB** |
| Cold launch to folder-chooser dialog (no data) | ~4.0 s |
| Cold launch to a fully rendered measurement (real CdO data) | ~5.4 s |

300 MB is in the expected range for this dependency depth (numpy + scipy +
xarray + zarr + h5py + matplotlib + a full Qt6 distribution via PySide6 +
pyqtgraph) and in line with `deployment-strategy.md` Section 2.2's estimate
("a few hundred MB... normal for scientific apps"). The 4-5 s startup is
slower than the pure-bootloader best case the strategy document floated
(~1-2 s) but is dominated by importing this exact dependency stack, not by
onedir's extraction step (onedir does not self-extract on every launch -
that cost is onefile-specific and is exactly why onedir was chosen); it is a
reasonable cost for a scientific desktop tool and was not treated as a
problem to solve in this milestone (Rule 7 - no premature optimization
without a reported complaint).

---

## 6. Known limitations (deliberately out of scope for Phase 1)

> **Update (2026-07-03, release-readiness audit):** the four items below that
> were open questions at the end of Phase 1 are now resolved - see
> [`docs/release-readiness-v1.md`](release-readiness-v1.md) for the full
> audit. In order: the installer now exists (Phase 2, same document); the
> zarr export was driven to a completed, reloaded round trip; the missing
> version-info resource (a defect this list didn't originally know to look
> for) was found and fixed; and a clean-machine proxy test (a sanitized-PATH
> launch + a full loaded-module origin audit) substituted for a literal
> second machine, which remains the one still-open recommendation. Left
> below unedited as the historical Phase 1 record.

- **No installer.** No desktop shortcut, no Start Menu entry, no uninstaller.
  A researcher must be handed the whole `packaging/dist/SNOMNIMAN/` folder and
  told to run `SNOMNIMAN.exe` inside it. This is exactly what Phase 2
  (`deployment-strategy.md` Section 3) exists to fix.
- **No auto-update, no code signing.** Explicitly out of scope per this
  milestone's constraints (Phases 3-4).
- **The zarr export write-to-disk path** was opened but not driven to
  completion interactively this session (Section 4) - a quick manual check
  before Phase 2, not a known defect.
- **The icon is a first-pass placeholder**, generated programmatically
  (Section 1) rather than commissioned art. Functionally complete (all 7
  standard sizes present) but a candidate for a real design pass before wide
  distribution.
- **Not yet tested on a second, clean machine.** This build has only been
  validated on the machine it was built on. Per the deployment strategy, the
  real test of "this is an application, not a project" is copying
  `packaging/dist/SNOMNIMAN/` to another Windows machine (or a clean VM) with
  no Python/dev tooling installed and confirming `SNOMNIMAN.exe` still
  launches and behaves identically. Recommended immediately after this
  milestone, before starting Phase 2 (`NEXT.md`).

---

## 7. Future installer considerations (feeding Phase 2)

Notes for whoever builds the Inno Setup installer next, gathered while doing
this milestone:

- The onedir output folder (`packaging/dist/SNOMNIMAN/`) is exactly the unit
  Inno Setup's `[Files]` section should recursively copy - no restructuring
  needed.
- `packaging/snomniman.ico` is ready to reuse directly for the installer's
  own icon, the Start Menu shortcut, and the desktop shortcut (all three
  should point at the same file so they visually match the running app).
  Regenerate via `packaging/make_icon.py` if a professional redesign
  replaces it - keep the filename stable so nothing else needs to change.
  Same finding, restated from `deployment-strategy.md`: no other prerequisite
  gap remains. The two prerequisites that document flagged in Section 2.4
  (a packaged entry point, an app icon) are both now done.
- The build is fully reproducible from a clean checkout:
  `uv sync --extra gui --group packaging` then the one `pyinstaller` command
  in Section 2 - worth wiring into a CI job (Phase 4's "CI builds and signs
  releases automatically") once Phase 2's installer exists to build.
- Startup time (Section 5) means the installer's "Launch SNOMNIMAN now" exit
  checkbox (`deployment-strategy.md` Section 3.3) should probably show a
  brief native "starting..." affordance rather than nothing, since 4-5 s is
  long enough for a researcher to wonder if the click registered - a small
  Phase 2 UX note, not a Phase 1 concern.
