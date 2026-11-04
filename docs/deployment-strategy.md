# Deployment Strategy - Version 1

**Status:** Research -> Design proposal. **No implementation. No packaging code
written.** **Date:** 2026-07-03.

**Stance:** SNOMNIMAN has grown from a Python project into a desktop application
with a complete research workflow (`CLAUDE.md` project status). The remaining gap
to a *product* is not a feature - it is that using it still requires a developer
environment (`uv`, a venv, `python -m snomniman.gui <dir>`). This document is the
user-commissioned milestone to close that gap: design, not build, the path from
"researcher clones a repo and runs a command" to "researcher downloads an
installer, double-clicks an icon, and updates like any other Windows application."

This document proposes **no architecture change**. Packaging is additive
infrastructure around the existing application; it touches nothing in
`core/io/processing/describe/diagnostics/ai/knowledge/manual/pipeline/viz/batch/gui`.
It is a sanctioned exception to "no new design documents unless implementation
exposes a real problem" (`NEXT.md`), exactly like `phase4-workflow-automation.md`
and `phase5-spectral-nanoftir.md` were. Per `docs/roadmap.md` ("Phase 8+ -
Extensibility... end-user packaging/installers... each will get an ADR before
implementation"), this is the research/design half; a real ADR (or several, one
per genuinely new dependency: the freezer, the installer tool, an update
mechanism) is the deliverable of implementing Phase 1 of the roadmap below, not
of this document.

---

## 1. The target experience, restated as requirements

The commissioning brief's flow -

```
download SNOMNIMAN_Setup.exe -> double-click -> desktop + Start Menu shortcuts
-> double-click icon -> app launches -> "Version 1.2 is available" -> Update
-> app restarts -> projects and settings preserved
```

- translates into five hard requirements that every choice below is checked against:

| # | Requirement | Why it is load-bearing |
|---|---|---|
| R1 | No Python, no venv, no shell visible to the researcher | The audience is optical physicists/AFM users, not developers (`docs/vision.md`) |
| R2 | A real Windows install: shortcuts, Start Menu entry, uninstaller | Anything less reads as "a script," not "an application" |
| R3 | Updating never touches user data | Projects, settings, recent-file lists must survive every upgrade (Rule 5's reproducibility promise extends to the *tool*, not just the data) |
| R4 | The install/update path is honest about trust | An unsigned, unverified `.exe` downloaded from the internet is exactly the profile Windows SmartScreen and lab IT policies exist to flag - this cannot be hand-waved away in a v1 plan |
| R5 | The app version is queryable and matches what provenance records | `Provenance` already records "software + operation versions" (`data-model.md`, Rule 5); the packaged app's version string must be the single source of truth the About dialog *and* provenance both read - never two version identities |

Everything below is organized as: investigate options, recommend one, justify
against R1-R5, then place it in a phased roadmap.

---

## 2. Freezing the application (Python -> Windows executable)

### 2.1 What has to survive freezing

The dependency surface is not trivial: `numpy`, `scipy`, `xarray`, `zarr`, `h5py`
(a compiled HDF5 binding), `matplotlib`, and - for the GUI build - `PySide6` +
`pyqtgraph` (a compiled Qt binding with plugins: platform backends, image format
plugins, styles). This is the same class of problem as other Python scientific
desktop tools (napari, Spyder's standalone build) - not a simple "one script,
stdlib-only" freeze. The freezer must find and bundle native shared libraries
(`.pyd`/`.dll`), Qt plugins, and each package's non-Python data files (matplotlib's
`mpl-data`, Qt's platform plugins) correctly, or the app fails only at runtime on
the researcher's machine - the worst possible failure mode for R1.

### 2.2 Comparison

| | **PyInstaller** | **Nuitka** | **Briefcase** (BeeWare) | **cx_Freeze** |
|---|---|---|---|---|
| **What it does** | Bundles the interpreter + bytecode + discovered dependencies into a folder or self-extracting exe | Compiles Python to C, then to a native binary (real ahead-of-time compilation, not just bundling) | Wraps a frozen build (itself often PyInstaller-adjacent per-platform) in a platform-native project/installer scaffold | Bundles the interpreter + dependencies, similar model to PyInstaller but older/simpler |
| **Startup speed** | Onedir: fast (~1-2s). Onefile: slower (self-extracts to a temp dir on every launch) | Fastest of the four - compiled code, no bytecode interpretation overhead | Comparable to PyInstaller (often *is* PyInstaller under the hood on Windows) | Comparable to PyInstaller onedir |
| **Executable size** | Onedir: large folder (few hundred MB with this stack, mostly Qt+numpy/scipy binaries) but normal for scientific apps | Similar order of magnitude; sometimes smaller with `--follow-imports` tuning, sometimes larger due to compiled artifacts | Similar to PyInstaller | Similar, slightly leaner (fewer bundled extras) |
| **Dependency/hook handling** | **Mature, extensive hook library** - `hooks-contrib` ships maintained hooks for `numpy`, `scipy`, `matplotlib`, `h5py`, and PySide6/Qt plugin discovery specifically. This is the single biggest differentiator for *this* stack | Has plugins (`--enable-plugin=pyside6`) and improving numpy/scipy support, but the hook ecosystem for less-common scientific packages (`zarr`, `xarray`, `h5py`'s HDF5 shared libs) is thinner and more failure-prone in practice | Delegates most of the hard bundling problem to the underlying tool it wraps; less battle-tested specifically for `xarray`/`zarr`/`h5py` combinations | Smaller community; hooks for modern packages (`zarr`, `xarray`) are sparse or unmaintained |
| **Update friendliness** | Onedir output is a plain folder an installer can diff/replace file-by-file | Compiled binary is opaque to file-level diffing (irrelevant for full-installer updates, matters only for delta/binary-patch updates) | Same as its underlying tool | Same |
| **Debugging a broken build** | Excellent: `--debug=all`, run the unpacked onedir folder directly, verbose import-tracing (`--log-level DEBUG`), huge Stack Overflow/GitHub-issue corpus for this exact stack | Hardest of the four: failures surface as C-compiler or Nuitka-plugin errors, several steps removed from the Python traceback a researcher (or Claude Code, next session) would recognize | Inherits whatever debugging story its underlying tool has, plus its own scaffolding layer to reason about | Adequate but smaller community means fewer precedents for *this* stack's specific failures |
| **Maturity for PySide6 + numpy/scipy/xarray/zarr/h5py specifically** | **Proven** - this is the default choice for the Python scientific-desktop-app category | Growing but riskier for this exact combination | Less proven for this combination; BeeWare's own GUI story favors Toga, PySide6 is a secondary path | Declining - not actively recommended for new projects with this dependency depth |

### 2.3 Recommendation: **PyInstaller, `--onedir` mode**

Justification against R1-R5:

- **R1/R2** - PyInstaller's onedir output is exactly what an installer needs to
  wrap: a folder with `SNOMNIMAN.exe` plus its dependencies, no visible Python.
- **Hook maturity dominates the decision.** This project's dependency set
  (`h5py`'s bundled HDF5, `zarr`'s codec plugins, `matplotlib`'s data files,
  PySide6's Qt plugin directories) is precisely the set PyInstaller's
  `hooks-contrib` project maintains hooks for today. Nuitka's compilation
  advantage (faster startup, smaller binaries) is real but is the wrong thing to
  optimize first: a research tool that launches in 2 seconds instead of 1 is a
  non-issue; a build that silently fails to find `h5py`'s HDF5 shared library on
  a researcher's machine (a genuinely common PyInstaller/Nuitka failure class
  for compiled scientific extensions) is a support incident. Choose the lower-risk,
  better-precedented option first; Nuitka remains a legitimate future
  re-evaluation once the app is stable and startup time becomes an actual
  reported complaint (not before - Rule 7, avoid solving problems that do not
  exist yet).
- **Onedir over onefile** - onefile's self-extraction-to-temp-on-every-launch
  is a real, measurable startup-latency and antivirus-false-positive cost (a
  self-extracting exe is a heuristic AV trigger) for no benefit once an installer
  already hides the folder structure from the researcher. Onedir gives R4 a
  cleaner story too: an installer that copies a transparent folder of files is
  less suspicious to endpoint security tooling than a single packed blob.
- **Debugging** - when a researcher reports "it won't launch," the ability to
  run the unpacked onedir build directly and get an ordinary Python traceback
  (rather than a compiled-binary crash) is worth more to a small team than any
  size/speed gain.

This choice needs its own ADR at implementation time (new major dependency,
per "Things Claude Must Never Do") but the investigation above is the
justification that ADR would cite.

### 2.4 Prerequisites this exposes (not implemented here)

Two small, honest gaps the app itself has today, noted for the implementer:
- No packaged entry point exists yet - the app launches via
  `python -m snomniman.gui <dir>`. Freezing needs a proper `snomniman-gui`
  console/GUI script (a `[project.scripts]`/`[project.gui-scripts]` entry in
  `pyproject.toml`) as PyInstaller's target, and a launch flow that does not
  require a directory argument on the command line (a File > Open dialog on
  first launch, or reopening the last project - already partially covered by
  the existing recent-projects/save-reopen machinery).
- No application icon exists yet (`.ico` for the exe, shortcuts, and the
  installer). A small, one-time asset need, not a design question.

---

## 3. The installer

### 3.1 Comparison

| | **Inno Setup** | **NSIS** | **WiX (MSI)** |
|---|---|---|---|
| **Output** | A single, modern-UI-styled `.exe` installer | A single `.exe` installer, plainer default UI | A genuine Windows Installer `.msi` package |
| **Scripting** | Pascal-like script (`.iss`), declarative sections for files/shortcuts/registry | NSIS's own scripting language - powerful but more arcane/lower-level | XML - verbose, steep learning curve, but produces the most "properly Windows" artifact |
| **Desktop/Start Menu shortcuts, uninstaller** | Built in, a few lines of script | Built in, more manual scripting | Built in, standard MSI mechanism |
| **Per-user (no admin) install** | **First-class, well-documented mode** - installs to `%LOCALAPPDATA%\Programs\...`, no UAC prompt | Supported but needs more manual script work to do correctly | Possible but MSI's native model leans per-machine; per-user MSI is the more awkward case for WiX specifically |
| **Silent/scripted install (for IT deployment)** | `/VERYSILENT /SUPPRESSMSGBOXES` switches, well documented | `/S` switch, well documented | Native to MSI - `msiexec /quiet` - this is what Group Policy/Intune/SCCM expect natively |
| **Code signing** | Standard Authenticode signing of the output exe, no special handling needed | Same | Same, plus MSI itself can carry a signature |
| **Community/maintenance for this category of app** | Extremely common choice for indie and scientific Windows desktop software; excellent documentation | Also very common (many well-known open-source Windows installers use it) | Common for enterprise-distributed/managed software, less common for indie desktop apps because of the authoring overhead |
| **Best fit** | Best effort-to-polish ratio for a researcher-facing, non-managed install | A viable alternative to Inno Setup with a rougher scripting experience for no clear present benefit | Best when a specific IT department requires MSI for Group Policy/SCCM/Intune deployment |

### 3.2 Recommendation: **Inno Setup**, with WiX/MSI deferred to Phase 5

Justification against R1-R5:

- **R1/R2** - Inno Setup's modern wizard UI (welcome/license/destination/
  shortcuts/finish pages) is the closest out-of-the-box match to the
  commissioning brief's exact flow, with the least scripting effort.
- **R4 (trust)** - critically, **per-user installs avoid the UAC/admin
  prompt entirely.** Many university and lab computers restrict admin rights
  on researcher accounts; a per-machine-only installer would be a real
  switch-back point (the same discipline `beta-readiness-v1.md` applies to
  workflow gaps applies here to the *install* workflow). Inno Setup's per-user
  mode (installing to `%LOCALAPPDATA%\Programs\SNOMNIMAN`) should be the
  **default install mode**, with a per-machine (`Program Files`, admin-elevated)
  option offered for IT-managed lab machines that prefer it. This single design
  choice is why Inno Setup is recommended over WiX for v1: WiX's native model
  fights a per-user default.
- **R5** - Inno Setup reads the same version string used to build the frozen
  app (passed in as a preprocessor define at build time from `pyproject.toml`'s
  `version`), so the installer filename (`SNOMNIMAN_Setup_1.2.0.exe`), the
  Windows "Programs and Features" entry, and the app's own About dialog are
  never three separately-maintained numbers.
- WiX is not rejected outright - it is the right tool **if and when** a specific
  lab's IT department requires MSI-based Group Policy/Intune/SCCM deployment
  (Phase 5, Section 6). Building it speculatively now, with no such requirement
  in evidence, would be exactly the premature generalization Rule 7 warns
  against.

### 3.3 Installer UX detail

- **Shortcuts:** Desktop shortcut (optional checkbox, default checked) + Start
  Menu entry under a "SNOMNIMAN" group. Both point at the frozen `SNOMNIMAN.exe`.
- **Uninstall:** Registered in "Apps & features" (standard Inno Setup
  behavior). The uninstaller removes only the install directory's files - it
  **never** deletes `%APPDATA%\SNOMNIMAN` or `%LOCALAPPDATA%\SNOMNIMAN` by
  default (Section 5), with an explicit, unchecked-by-default "also remove my
  settings and cache" checkbox for a researcher who wants a truly clean wipe.
  User projects (`.snomproj` files, wherever the researcher chose to save them)
  are never touched by the uninstaller under any option - they are the
  researcher's documents, not application state.
- **File associations (future, not v1):** associating `.snomproj` with
  SNOMNIMAN (double-click a project file to launch it directly) is a natural,
  low-risk Inno Setup addition once the installer exists, but is out of scope
  for this document - noted for a future increment, not designed here.
- **Installer UX sequence:** Welcome -> License (project license) -> Install
  location (per-user default, per-machine option) -> Select
  components (none needed for v1 - single build) -> Shortcuts -> Install
  progress -> Finish (with "Launch SNOMNIMAN now" checkbox, default checked) -
  the direct realization of the commissioning brief's flow diagram.

---

## 4. Updates

### 4.1 The constraint unique to this application

A SNOM/nano-FTIR session can be long-running (a researcher mid-scan, or with
unsaved measurement state). Unlike a browser or chat app, an update that
force-restarts the application is not merely an inconvenience - it risks
research work. The update design's first job is therefore **never surprise the
researcher with a restart they did not initiate**, not squeezing out the
lowest-friction update loop possible.

### 4.2 Comparison of mechanisms

| Approach | Friction | Preserves data? | Complexity to build | Verdict |
|---|---|---|---|---|
| **Manual** - researcher re-downloads the installer from GitHub Releases when they remember to | Highest (researcher must think to check) | Yes, trivially (Section 5 keeps app data outside the install dir) | None - this is what exists the moment Phase 2 ships | Right for v1 launch, wrong as the permanent story |
| **In-app "Check for Updates"** - app queries the GitHub Releases API on demand (menu item) and/or once at startup, shows a "Version 1.2 is available" dialog with release notes and a "Download and Install" button | Low - one click, no browser round-trip | Yes | Small - an HTTP GET to a public API + running the downloaded installer's silent switches | **Recommended for Phase 3 (v1)** |
| **Background download + prompt-to-relaunch** - the update downloads silently while the researcher keeps working, then a non-modal "Update ready - restart to apply" notification appears, applied only when the researcher clicks it (or on next manual launch) | Very low | Yes | Moderate - needs a background thread/process and careful handling of "what if the researcher never restarts" | A refinement of the above, appropriate once the simpler flow is validated with real users |
| **Fully silent/automatic** (Squirrel.Windows/Velopack-style: downloads and applies without asking, next launch is just already-new) | Lowest, but removes the researcher's ability to defer an update mid-experiment | Yes, if done correctly | Highest - delta patching, rollback safety, a real update-framework dependency | Explicitly **not** recommended for this application's usage pattern - the "never surprise a researcher mid-session" constraint (4.1) argues against silent auto-apply even once it becomes technically easy |

### 4.3 Recommendation: staged roadmap, not one mechanism

1. **Phase 2 (installer ships): manual only.** GitHub Releases is the
   distribution channel from day one regardless of update mechanism (Section
   6), so "manual" costs nothing extra to support and is the correct fallback
   forever (R2 of the AI principles' spirit applies by analogy here too:
   *the update mechanism enhances convenience, it must never be the only way
   to get a working install*).
2. **Phase 3: in-app "Check for Updates."** Query
   `https://api.github.com/repos/<org>/snomniman/releases/latest` (public,
   unauthenticated, rate limits are generous for this traffic pattern), compare
   its tag against the running app's embedded version (R5), and if newer,
   show the release notes (the GitHub release body, which is already
   maintained as part of tagging a release) with an explicit researcher-
   initiated "Download and Install" action. On click: download the installer
   to a temp directory, launch it with silent switches
   (`/VERYSILENT /SUPPRESSMSGBOXES /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS`),
   and let Inno Setup's own "close and relaunch the running app" behavior
   handle the restart - one dependency (the installer tool) doing one job
   twice (install and update), not a second update-specific tool.
3. **Future (post-v1, not this roadmap's concern): background download +
   prompt-to-relaunch** (Section 4.2's third row), once real usage shows the
   click-through-the-dialog friction of Phase 3 is an actual complaint and not
   a hypothetical one (Rule 7 discipline: earn the added complexity with
   evidence).
4. **Release channels feed the same mechanism** (Section 7): a researcher who
   opted into the beta channel has their update check compare against the
   latest pre-release tag instead of the latest stable tag - no separate
   update system, one settings toggle.

This keeps the update mechanism itself dependency-light (an HTTP GET + running
the existing installer) rather than adopting a dedicated update framework
(Squirrel/Velopack/WinSparkle) before there is evidence the simple approach is
insufficient - the same "activation of latent capability before new
construction" discipline `phase4-workflow-automation.md` applied to recipes/
batch/reporting.

---

## 5. Application data - where SNOMNIMAN writes to disk

Following Windows conventions (the same discipline the project already applies
to scientific conventions in `data-model.md`: be explicit, never assume):

| Kind of data | Location | Rationale |
|---|---|---|
| **Installed program files** (the frozen exe + bundled libraries) | Per-user default: `%LOCALAPPDATA%\Programs\SNOMNIMAN\`. Per-machine option: `%ProgramFiles%\SNOMNIMAN\` | Matches Section 3.2's per-user-by-default decision; this directory is **replaced wholesale on every update and fully removed on uninstall** - nothing a researcher cares about may ever live here |
| **Settings/configuration** (window layout, last-used colormap, UI preferences) | `%APPDATA%\SNOMNIMAN\config\` | Roaming location - follows the researcher across machines on a domain-joined lab network, standard Windows practice for small user preference data |
| **Recent-projects list** | `%APPDATA%\SNOMNIMAN\` (small JSON/text) | Same roaming rationale; already conceptually exists as the save/reopen feature's recent-files tracking - this just gives it a durable, correct home when packaged |
| **Cache** (rendered preview thumbnails, any recomputable intermediate) | `%LOCALAPPDATA%\SNOMNIMAN\cache\` | Local (not roamed - caches are machine-specific and can be large); **safe to delete entirely at any time** - the app must always be able to regenerate its contents, never treat the cache as authoritative data |
| **Logs** | `%LOCALAPPDATA%\SNOMNIMAN\logs\` (rotated, size/age-capped) | Local, diagnostic-only; the first thing to ask a researcher for when something goes wrong |
| **Temp/scratch files** | A subfolder under the OS temp dir (`%TEMP%\SNOMNIMAN\`), cleaned on normal exit | Never the researcher's concern; never a place anything durable is written |
| **User projects** (`.snomproj` bundles) and any exported figures/data | Wherever the researcher chooses to save them (defaults to their Documents folder on first save, exactly as today) | These are the researcher's documents, not application state - SNOMNIMAN must never assume a fixed location for them, and neither install nor uninstall may ever touch them |

**Uninstall stays clean by construction:** because nothing a researcher values
lives under the program-files directory, uninstalling SNOMNIMAN is always safe
by default; the optional "also remove settings and cache" checkbox (Section
3.3) is the only path that touches `%APPDATA%`/`%LOCALAPPDATA%`, and it never
touches user projects regardless.

---

## 6. Versioning and release channels

- **Scheme: Semantic Versioning** (`MAJOR.MINOR.PATCH`), already the shape of
  `pyproject.toml`'s `version = "0.1.0"`. Reserve `MAJOR` bumps for changes
  that break something a researcher would notice across an upgrade (a
  `.snomproj` schema version bump the loader cannot migrate, a fundamental
  workflow change) - not for ordinary feature growth, which this project ships
  at a genuinely high cadence (see `LOG.md`: multiple shipped increments most
  days). Most releases will be `MINOR` bumps (a shipped phase/feature) or
  `PATCH` (a fix, no new capability).
- **Version 1.0.0 marks "installable product," not "feature-complete."**
  Per this document's own framing, crossing from `0.x` to `1.0.0` should happen
  when Phase 2 (Section 8) ships - a real installer exists - regardless of
  which beta-readiness backlog items are still open. The product-readiness
  question (`beta-readiness-v1.md`) and the packaging-readiness question (this
  document) are independent; conflating them would make "ready to package"
  wait on an ever-moving feature target.
- **Release channels:**
  - **Stable** - ordinary GitHub Releases tags (`v1.2.0`), what the default
    updater channel checks against.
  - **Beta/preview** - pre-release tags (`v1.3.0-beta.1`), marked as a GitHub
    "pre-release" (excluded from the "latest" API response Stable checks
    against by design, so Stable users are never accidentally offered a beta).
    A settings toggle ("Receive beta updates") switches which release stream
    the in-app checker follows - no second distribution mechanism.
- **Cadence:** not calendar-driven. A release is cut when a coherent set of
  already-shipped-to-`main` increments (per `LOG.md`) is judged worth
  distributing - realistically every few weeks at the project's current
  velocity, plus out-of-band patch releases for anything that reaches the
  "beta blocker" severity `beta-readiness-v1.md` already uses to triage
  product gaps.
- **Build identity feeds provenance (R5):** the version string baked into the
  frozen executable (via the PyInstaller build reading `pyproject.toml`) is
  the same string the About dialog displays and the same string
  `snomniman.pipeline` provenance already records as the software version
  (`data-model.md`, Rule 5) - one identity, not a packaging-side duplicate of
  a fact the backend already tracks.

---

## 7. Trust and signing (why R4 needs its own section)

An unsigned `.exe`/installer downloaded from the internet triggers Windows
SmartScreen ("Windows protected your PC"), which is precisely the kind of
scary, credibility-destroying first impression that would send a researcher
straight back to neaPLOT (the exact failure mode `beta-readiness-v1.md`
catalogs for in-app workflow gaps applies with even more force to the very
first thing a researcher sees). This cannot be deferred indefinitely, but it
also should not block the first installable build - hence its own phase
(Phase 4, Section 8) rather than folding it into Phase 2.

- **Code signing (Authenticode).** Signing the frozen exe and the installer
  with a code-signing certificate (an OV or, better, an EV certificate - EV
  certs build SmartScreen reputation almost immediately, OV certs need
  download-volume time to accumulate reputation) removes the SmartScreen
  warning and lets "Programs and Features" show a verified publisher name
  instead of "Unknown." This is a real, recurring cost (a certificate must be
  purchased/renewed and its private key protected), which is exactly why it is
  its own phase - Phase 1-3 must work without it, but Phase 4 is not optional
  for a public release the project wants researchers to trust.
- **Reproducible, auditable builds.** Once CI builds releases (a GitHub
  Actions workflow triggered on a version tag, mirroring the existing
  `ci.yml` pattern in `infrastructure-baseline.md`), the built artifact should
  be traceable back to the exact commit that produced it (embed the commit
  hash alongside the version in the About dialog) - the same "never overstate
  reproducibility, but be as transparent as possible about what produced this"
  discipline the project already applies to scientific results, applied to the
  tool that produces them.
- **Signing is a CI secret-management concern**, not a design fork: the same
  Phase-4 CI workflow that builds the installer signs it, using a certificate
  held as a repository secret. No change to the freezing or installer choices
  above is needed to add signing later - it is additive.

---

## 8. Deployment roadmap

| Phase | Deliverable | Justification |
|---|---|---|
| **Phase 1 - Standalone executable** | A PyInstaller `--onedir` build (`SNOMNIMAN.exe` + its folder), zipped, attached to a GitHub Release or shared internally. No shortcuts, no installer, no auto-update. Requires: a packaged entry point + app icon (Section 2.4). | Validates that the freeze itself succeeds against this exact dependency stack (h5py/zarr/xarray/matplotlib/PySide6/pyqtgraph) before investing in installer polish - the highest-uncertainty step, done first and in isolation. Doubles as an internal dogfooding artifact and a CI smoke-test artifact. |
| **Phase 2 - Installer** | Inno Setup wraps the Phase 1 build: per-user install by default (no UAC), desktop + Start Menu shortcuts, standard uninstaller, versioned filename. Distributed via GitHub Releases (manual download - Section 4.3 step 1). | This is the phase that satisfies the commissioning brief's install/launch flow end to end. Crossing this line is what should mint **v1.0.0** (Section 6). |
| **Phase 3 - Automatic update checking** | In-app "Check for Updates" against the GitHub Releases API; researcher-initiated download + silent reinstall + relaunch; settings/projects untouched (Section 5 makes this automatic, not something the updater must itself guarantee). Beta-channel toggle (Section 6). | Completes the commissioning brief's update flow. Deliberately stops short of silent/background auto-apply (Section 4.2's constraint: never surprise a researcher mid-session). |
| **Phase 4 - Signed releases** | Code-signing certificate; CI (GitHub Actions, tag-triggered) builds, signs, and publishes the installer automatically; commit hash embedded alongside version. | Removes the SmartScreen trust barrier (Section 7) and makes releases auditable back to source - both necessary before actively promoting the installer to external labs, not necessary to validate the mechanics internally first. |
| **Phase 5 - Enterprise deployment** | On demand only, when a specific lab/institution IT department requires it: a WiX-built MSI (or the existing Inno installer's silent switches, which already satisfy most IT deployment tools without a rebuild), Group-Policy/Intune/SCCM-friendly per-machine install, centrally managed update cadence (IT may disable in-app auto-update and push versions on its own schedule). | Deliberately last and conditional - building MSI/enterprise tooling speculatively, with no institution asking for it, would be exactly the premature generalization Rule 7 exists to prevent. The per-user Inno installer already satisfies the single-researcher and small-lab cases Phases 1-4 target. |

Each phase is independently useful and independently shippable - Phase 1 alone
is already a meaningful improvement over "clone the repo," and no phase
requires reopening a decision made in an earlier one (the Phase 1 PyInstaller
build is exactly what Phase 2's installer wraps; Phase 3's updater installs
exactly what Phase 2 built; Phase 4 signs exactly what Phase 3 downloads).

---

## 9. What this document deliberately does not do

- **No packaging code, build scripts, `.iss`/spec files, or CI workflow
  changes.** Per the commissioning constraint, this is strategy only.
- **No ADR yet.** Per `docs/roadmap.md`'s existing placeholder ("each will get
  an ADR before implementation"), the ADR(s) for the frozen-app dependency
  (PyInstaller) and the installer tool (Inno Setup) are written when Phase 1/2
  are actually implemented, citing the investigation in Sections 2-3 as their
  justification - the same pattern `ADR-0031` cited
  `phase4-workflow-automation.md`'s design work.
- **No commitment on when Phase 1 begins.** That is a Beta Readiness /
  product-priority call (`beta-readiness-v1.md`, `NEXT.md`), not something this
  design document decides - this document only ensures that when the project
  is ready to start, the path is already fully reasoned through rather than
  improvised.
- **No macOS/Linux packaging.** SNOMNIMAN's user base and the commissioning
  brief are both Windows-specific; nothing above assumes cross-platform reach,
  and extending to another OS is out of scope until a concrete need exists
  (Rule 7).
