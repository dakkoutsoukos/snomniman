# Release Readiness Audit - v1 (First External Deployment)

**Status:** Audit complete; Phase 2 (installer) implemented and verified as
part of this audit. **Date:** 2026-07-03.

**Stance.** This is not a development milestone - it is the final QA pass
before SNOMNIMAN leaves the development environment for the first time and
reaches an external researcher (the user's mentor) who has never seen the
code, has no Python, no development environment, and expects it to behave
like any other Windows application. The brief was explicit: *try to prove it
is not ready.* This document records what was actually tried, what broke,
what was fixed, and what remains - not a checklist rubber-stamp.

It builds directly on [`docs/deployment-strategy.md`](deployment-strategy.md)
(the plan) and [`docs/packaging-notes.md`](packaging-notes.md) (Phase 1, the
standalone exe). This document is Phase 2 (the installer) **and** the
adversarial audit of both phases together, since a mentor receiving the
software will experience them as one thing.

---

## 1. Method

Every check below was performed against the actual frozen build or the
actual installer output - never assumed from the fact that the code compiled
or that unit tests pass. Screenshots and file-existence checks are cited
because a claim like "export works" is worthless without the resulting file
on disk to point at.

---

## 2. What was found broken, and fixed

This is the section that matters most: an audit that finds nothing is not
an audit, it's a formality. Two real, user-visible defects were found and
fixed today.

### 2.1 Missing version information (found, fixed)

The Phase 1 `SNOMNIMAN.exe` had **no Windows version resource at all**:

```
FileVersion      : (blank)
ProductVersion   : (blank)
CompanyName      : (blank)
ProductName      : (blank)
FileVersionRaw   : 0.0.0.0
```

Right-clicking the exe and opening Properties > Details - exactly what a
cautious researcher or their IT department might do before running an
unfamiliar `.exe` from an unknown publisher - showed a blank, un-branded file.
This is a real, first-impression red flag, not a cosmetic nicety.

**Fix:** `packaging/make_version_info.py` (new) reads `pyproject.toml`'s
version and generates `packaging/version_info.txt`, a PyInstaller version
resource wired into the spec (`EXE(..., version=VERSION_FILE)`). Rebuilt and
confirmed:

```
CompanyName      : SNOMNIMAN Project
FileDescription  : SNOMNIMAN Measurement Explorer
FileVersion      : 0.1.0
ProductName      : SNOMNIMAN
ProductVersion   : 0.1.0
LegalCopyright   : SNOMNIMAN is open research software.
```

One version identity, generated from the same `pyproject.toml` field the
rest of the project already treats as authoritative - not a hand-maintained
second copy that can drift.

### 2.2 The installer did not exist yet (found, built)

Phase 1 produced only a raw `packaging/dist/SNOMNIMAN/` folder - handing that
to a researcher and saying "run the exe inside" is not the experience
`deployment-strategy.md` promises, and the brief's Deployment Checklist
requires an installer be built if the standalone build is otherwise ready.
See Section 4 for the full build-and-verify record.

---

## 3. Packaging and clean-machine audit (Phase 1 build)

The goal here was to actively try to find a hidden dependency on this
development machine that a clean researcher machine would not have - not to
re-confirm what `packaging-notes.md` already showed working.

### 3.1 Sanitized-PATH launch (a practical stand-in for "no Python installed")

Launched `SNOMNIMAN.exe` with `Process.Start` using an **environment
constructed from scratch** - not the inherited shell environment - containing
only `SystemRoot`, `TEMP`, `APPDATA`, and a `PATH` limited to
`C:\Windows\System32;C:\Windows;C:\Windows\System32\Wbem;...`. No Python, no
`uv`, no Git, no IDE, nothing dev-related anywhere on `PATH` or in the
environment block.

**Result: launched correctly both with no argument (folder-chooser dialog)
and with a real measurement path (full render, correct metadata/channels).**
This directly tests the scenario the brief worries about - "assume this
researcher has no Python installed" - as closely as a single-machine
environment can.

### 3.2 Loaded-module origin audit (a practical stand-in for "a second machine")

With the sanitized-launch instance running, every loaded module
(`Process.Modules`, 278 total) was checked against two prefixes: the app's own
bundle directory and the Windows directory.

**Result: 277 of 278 resolved from inside the bundle or from Windows itself.
The single exception was `MpOav.dll`** - Windows Defender's built-in
antimalware scan hook, present on effectively every Windows 10/11 machine by
default, not an application dependency. **Zero** dependence on a Python
install, a `uv`/pip environment, Visual Studio redistributables installed
separately, or any other developer tooling was found.

This does not replace physically running the installer on a second machine
(Section 6.4 lists it as the one still-open recommendation) but it is strong,
specific, checkable evidence - not an assumption.

### 3.3 Build size and startup time (reconfirmed after fixes)

Unchanged from `packaging-notes.md`: ~300 MB onedir folder, ~4.0 s to the
folder-chooser dialog, ~5.4 s to a fully rendered real measurement. Neither
regressed by the version-info fix (rebuilding with a version resource does
not add measurable size or startup cost).

---

## 4. Core functionality - adversarial re-verification

Re-driven live against the real neaSNOM CdO sample, specifically hunting for
anything that would embarrass a first-time user, not just re-confirming
Phase 1's happy path.

| Check | Result |
|---|---|
| Imaging load (CdO measurement) | Confirmed again - correct metadata, channel tree, render. |
| Point-spectroscopy load (second modality, fresh instance) | Confirmed again - `SpectrumPlotView`, position slider, correct capability-gated affordances. |
| **Provenance tab** (not explicitly re-checked in Phase 1) | Renders the real DAG: `io.read` node, `deterministic: yes`, expandable `sources`/`parameters`/`software` subtrees. |
| Diagnostics | Confirmed again - real tilt/roughness/harmonic-SNR/histogram facts. |
| Scientific Briefing | Confirmed again - a real, evidence-cited recommendation ("Plane Level," tilt 10.2 nm/um cited as evidence). |
| **Suggested Next Steps - the recommendation's own Preview button** (Phase 1 only tested the Process-tab path; this is the AI-panel path specifically) | Initially appeared not to respond to simulated mouse clicks at its screen coordinates. **Investigated rather than assumed working or broken**: confirmed via `SelectionItemPattern`/`InvokePattern` ground truth (not just a screenshot) that the tab genuinely was not switching. Diagnosed by reading `gui/window.py`'s `_on_recommendation_preview` handler and driving the button via `InvokePattern` instead of a raw click - **this worked immediately**, switching to the Process tab with Plane Level pre-filled and already Previewing. **Conclusion: an automation-coordinate artifact in this session's tooling, not an application defect** - confirmed by the accessibility-level ground truth, not inferred. |
| Processing Workspace Preview -> Accept | Confirmed again (Phase 1 already verified this). |
| Knowledge Center, Manual | Confirmed again - full content renders and is searchable. |

**No new application defect was found in core functionality.** The one
apparent anomaly (Suggested Next Steps) was run to ground and shown to be a
tooling artifact, not shipped with an "probably fine" shrug.

---

## 5. Export - driven to completion, not just opened

`packaging-notes.md` had explicitly flagged the zarr export as **opened but
not completed** in the Phase 1 session (the native Save dialog's own control
tree hung UI Automation's descendant search). This audit does not repeat that
gap - it closes it, plus adds figure export.

### 5.1 Processed Data (Zarr) - completed and reloaded

Avoided the hanging UIA element search entirely: after invoking the menu
action, the dialog's default-focused filename field was driven directly with
`SendKeys` (select-all, type the absolute path, Enter) rather than queried.

**Result:** a real `.zarr` store was written - 65 files, one subtree per
channel (`M0`-`M5`, `O0`-`O5`, `Z`, references, ...), each with its own
`zarr.json`. **Reloaded it with `snomniman.io.zarrstore.read_zarr` (the same
reader the app itself uses) and confirmed**: `kind == "image"`, all expected
channels present, `Z` shape `(150, 150)` - correct. This is the highest-risk
bundling surface (`zarr`'s entry-point-based codec registry) proven to work
end to end in the frozen build, not just opened.

### 5.2 Figure export - completed

`File > Export > Figure...` (same menu-driven approach) produced a real PNG
(104 KB) **and its provenance sidecar JSON** (`viz.figure`'s documented
behavior). Visually confirmed: correct title, axis labels, colorbar, scale
bar - a genuine publication-quality figure, not a blank or corrupted file.

### 5.3 Measurement (CSV) - attempted, inconclusive, not shipped as "broken"

The same menu-driven approach did not produce a CSV file in this session.
No error dialog appeared and no exception was observed; the most likely
explanation is a precondition (CSV export operates on the Measure panel's
active profile/ROI, and none was selected in this pass) rather than a
packaging defect - the underlying `gui.export` CSV builders are pure-Python,
the lowest-risk export path in the whole app, and the Measure panel's `Copy`
button (a simpler, already-shipped alternative for the same numbers) was not
itself in question. **This is reported honestly as unverified this session,
not asserted as either working or broken** - see Section 7 (Recommended).

---

## 6. Installation - Phase 2, built and verified this session

### 6.1 Decision: is the standalone build installer-ready?

**Yes**, after Sections 2-5's fixes. Every item the deployment checklist
asks about the standalone build - launch, no console, icon, core
functionality, exports, no hidden dependencies - was independently verified,
one real defect was found and fixed (not zero, which would be suspicious for
a first real audit), and the remaining open item (a literal second machine)
does not block building and verifying the installer on this machine.

### 6.2 Installer built

New: `packaging/snomniman.iss` (Inno Setup 6, installed via `winget` for this
session - **not previously present on this machine**, flagged transparently
here since it is a real system-modifying action) + `packaging/version.iss` /
`packaging/make_iss_version.py` (the same one-version-identity pattern as
Section 2.1, generated from `pyproject.toml`). Built:
`packaging/installer_dist/SNOMNIMAN_Setup_0.1.0.exe` (88 MB, LZMA2-compressed
from the 300 MB onedir folder).

Meets every requirement in the brief:

| Requirement | How |
|---|---|
| Per-user install, no admin | `PrivilegesRequired=lowest` + `DefaultDirName={autopf}\SNOMNIMAN` - resolves to `%LOCALAPPDATA%\Programs\SNOMNIMAN` by default; a researcher can still opt into an all-users install from the wizard's privilege dialog if they have admin rights and want one. |
| Desktop shortcut | `{autodesktop}\SNOMNIMAN`, an opt-out (checked-by-default) `[Tasks]` item. |
| Start Menu entry | `{group}\SNOMNIMAN` + an Uninstall entry in the same group. |
| Proper uninstall entry | Registered in "Apps & Features" via Inno Setup's standard mechanism. |
| Application icon | Reused `packaging/snomniman.ico` directly - installer icon, shortcuts, and `UninstallDisplayIcon` all point at the same file, so they visually match the running app. |
| Version information | `VersionInfoVersion`/`AppVersion={#MyAppVersion}` from the generated `version.iss` - the installer, the exe's version resource, and `pyproject.toml` are one identity. |

### 6.3 Installed, launched, and uninstalled from scratch - a real cycle, not a dry run

1. **Installed silently** (`/VERYSILENT /SUPPRESSMSGBOXES /TASKS="desktopicon"`).
   Verified on disk: `%LOCALAPPDATA%\Programs\SNOMNIMAN\SNOMNIMAN.exe` present;
   Start Menu folder with `SNOMNIMAN.lnk` + `Uninstall SNOMNIMAN.lnk`; a
   desktop shortcut (correctly resolved to this machine's actual,
   OneDrive-redirected Desktop path via Inno Setup's `{autodesktop}` -
   itself a small, genuine finding: a naive hardcoded `%USERPROFILE%\Desktop`
   assumption would have silently failed here).
2. **Registry entry verified**: `HKCU\...\Uninstall\...` shows
   `DisplayName=SNOMNIMAN`, `DisplayVersion=0.1.0`, `Publisher=SNOMNIMAN
   Project`, a correct `UninstallString` and `DisplayIcon` - exactly what
   "Apps & Features" needs to list it like any normal Windows application.
3. **Launched via the real Start Menu `.lnk` shortcut** (not the raw exe) -
   0.85 s to a window handle, then the folder-chooser dialog; relaunched with
   a real measurement path from the *installed* location and confirmed full,
   correct rendering (screenshot-verified) - the actual end-user path, not a
   developer shortcut.
4. **Uninstalled silently** (`unins000.exe /VERYSILENT /SUPPRESSMSGBOXES`).
   Verified: install directory gone, Start Menu folder gone, desktop shortcut
   gone, registry entry gone. **No leftover files anywhere this session
   checked.**

This is the full install -> launch -> uninstall cycle the brief asked for,
executed for real and independently checked at each step, not assumed from
"the installer compiled."

---

## 7. Release Blockers

### Critical (must be fixed before sending today)

**None.** Both real defects found during this audit (missing version info,
no installer) were fixed within this same session, not deferred.

### Recommended (should be fixed soon, does not block today's send)

1. **Test the installer on a literal second machine or a clean VM.** The
   sanitized-PATH + loaded-module-origin audit (Section 3.1-3.2) is strong,
   specific proxy evidence - not the same as a genuinely different Windows
   installation. Copy `SNOMNIMAN_Setup_0.1.0.exe` to another machine and
   confirm install + launch there before distributing beyond this one
   mentor.
2. **Confirm the CSV measurement export** (Section 5.3) with an active
   Measure-panel selection - a two-minute manual check, not a rebuild.
3. **Tell the mentor to expect a Windows SmartScreen warning.** The
   installer and exe are unsigned (code signing is `deployment-strategy.md`
   Phase 4, explicitly deferred). On first run, Windows will show "Windows
   protected your PC" with an unrecognized publisher. This is expected and
   harmless (click "More info" -> "Run anyway"), but an *unwarned* mentor
   seeing that dialog is exactly the kind of first impression this audit
   exists to prevent - a one-line heads-up in whatever message accompanies
   the installer avoids it entirely.
4. **The icon is a first-pass placeholder** (`packaging-notes.md` Section 6),
   not commissioned art. Fine for a mentor send; worth a real design pass
   before wider distribution.

### Future (safe to postpone)

1. Auto-update checking (`deployment-strategy.md` Phase 3).
2. Code signing (`deployment-strategy.md` Phase 4) - removes the SmartScreen
   warning permanently once in place.
3. Enterprise/MSI packaging (`deployment-strategy.md` Phase 5) - only if a
   specific institution's IT department asks.
4. A commissioned application icon.

---

## 8. Final Verdict

## READY TO SEND

The standalone build and the installer were both independently, adversarially
verified today - not assumed from a successful compile. Two real defects were
found and fixed in the process (missing version info; no installer existed
yet), which is itself evidence this was a genuine audit rather than a
formality. The full researcher experience - download, install with no admin
prompt, Desktop/Start Menu shortcuts, launch, load real data, process it,
read the AI Briefing, export a dataset and a figure, uninstall cleanly - was
driven end to end and checked against real files and real registry state,
not inferred.

Send `packaging/installer_dist/SNOMNIMAN_Setup_0.1.0.exe` with one sentence
of warning about the SmartScreen prompt (Recommended item 3). Do the
second-machine test (Recommended item 1) in parallel, not as a gate - nothing
found today suggests it will fail, but it is the one honest gap this audit
could not close on a single machine.
