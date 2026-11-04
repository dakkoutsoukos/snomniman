# NEXT.md - Immediate Priorities

Single source of truth for "what should the next session work on?" Keep current:
when a task is done, move it to `LOG.md` and update this file.

**Last updated:** 2026-07-20b (user-commissioned: **implemented the ready
parts of `docs/phase7-9-master-roadmap.md`** - Phase 7A-7C, Phase 8A, Phase
9A-9C, ADR-0033. Renumbered from the brief's "Phase 6/7/8" because Phase 6
is already the shipped spectral lineshape analysis track below.
**Phase 7 (Automated Scientific Feature Analysis) - DONE, no ADR:**
`image.threshold_segment` (Otsu/percentile/fixed thresholding +
`scipy.ndimage` connected-component labeling; watershed deliberately
deferred, needs `scikit-image`); `diagnostics.FeatureDiagnostics`/
`ParticleFeature` (area/diameter/perimeter/aspect ratio/orientation/
per-region source-channel stats + a size histogram); `ExperimentModel.
feature_table()` + `ReportModel`'s new "Feature analysis" section (absent,
not empty, when nothing is segmented). **Phase 9A/9B/9C - DONE, no ADR:**
`ai.experiment.build_experiment_briefing`/`detect_outliers` (a new
`ai -> pipeline` edge, deliberately independent of `gui.experiment.
ExperimentModel`, which stays a presentation aggregator); the
single-measurement Briefing now narrates Phase 7 features too. **Phase 8A -
DONE, ADR-0033:** the new `snomniman.physics` module,
`fit_dielectric_model` (Drude/Lorentz-oscillator fit to a measured complex
near-field spectrum). **A real identifiability bug was caught by Rule-6
synthetic testing before shipping**, not just a tolerance issue: the Drude
plasma frequency, Lorentz oscillator strength, and `eps_inf` are each
exactly degenerate with the fit's free complex scale/offset (a scalar
prefactor only) and are **not identifiable** from this practical fit -
`DielectricFit` reports only the genuinely shape-identifiable `gamma`
(Drude) / `omega_to`+`gamma` (Lorentz). This is also why Phase 8B (finite
dipole model) is scientifically *necessary*, not just more accurate, for
the plasma frequency/carrier density. **Phase 8B (FDM), 8C (carrier
density), 7D/7E (watershed/hyperspectral segmentation), and every Phase 9D
auto-recommendation rule remain designed, not implemented** - honestly
deferred pending real reference data, tip-geometry metadata (still no
`core.metadata` field for it), or their own Scientific Validation study.
925 tests pass (60 new); `ruff`, `mypy --strict`, and the Qt-free invariant
green. No GUI panel for physics fitting yet (backend-only, matching the
Phase 5A precedent). See `LOG.md` entry "2026-07-20b" for the full record.
**2026-07-14d (shipped **Phase 6 stage 4 - Spectral Peak
Fits reporting + Knowledge/Manual - PHASE 6 NOW FULLY SHIPPED, stages
1-4**).** Per explicit user direction, the Explorer tracks exactly **one**
active lineshape fit (no history/session list): `gui/report.py`'s
`ReportModel` gained an optional `active_lineshape_fit` slot, composed
verbatim into a new "Spectral peak fit (active)" section in both the
Experiment Report and the Publication Package (absent, not empty, when no
fit is active); `window.py` sets it right after a successful fit and clears
it at the same point `SpectrumPlotView` clears its own fit display (a new
curve), so the two never drift apart. New Knowledge article
`concept.lorentzian_lineshape` (why a low R^2/structured residual means the
model doesn't apply, not a bug) and Manual page
`explorer.spectrum_lineshape_fit`. 7 new tests; full suite **865 passed, 0
failed**; `ruff`/`mypy --strict` clean. See `LOG.md` entry "2026-07-14d" for
the full stage 1-4 summary and the closed scope ledger (N-ary averaging,
Gaussian/Voigt/multi-peak fitting, auto-recommendation, and a fit-history
list all remain deliberately deferred, named rather than silently missing -
`docs/phase6-spectral-lineshape-analysis.md` Section 4). Earlier Phase 6
stages (1: `spectrum.ratio`/`spectrum.savgol_smooth`, 2: `viz.measure.
fit_lineshape`, 3: the fitting UI + dual axis, live-verified against real
point-spectroscopy sample data) are `LOG.md` entries "2026-07-14"/"b"/"c".
Earlier still: Phase 5B (Spectral Visualization & Hyperspectral Workspace,
`LOG.md` "2026-07-02f"), Phase 5A (Spectral Processing Foundations,
"2026-07-02e"), Phase 5C re-confirmed hard-blocked ("2026-07-02g"),
Scientific Reporting (Phase 4C), Batch Processing (Phase 4B), Processing
Recipes (Phase 4A, ADR-0031), the Point Spectrum vertical slice (second data
modality), Phase 3C region-aware ops, Phase 3B scientific analysis toolbox,
Phase 3A core operations, Phase 2C multi-input/arithmetic, Phase 2B
experiment analysis, Phase 2A multi-measurement projects, the complete
research workflow. Governance: the Scientific Validation Phase + Beta
Readiness Review remain the planning systems.
**2026-07-03 (shipped, user-commissioned, ADR-0032):** the **SNOMNIMAN
Manual** - a second Qt-free leaf package, `snomniman.manual`, the software
counterpart to the Knowledge Center (teaches *how*, never *why*). Structured
`ManualPage`s (41 initial, one per registered operation plus Explorer panels/
AI/export/settings/shortcuts/troubleshooting), cross-linked to Knowledge by
plain string id with **no new import edge** between the two leaf packages (a
dedicated cross-package test checks both link directions instead). A new
**Manual** Explorer tab is the primary entry point (click it, like
Knowledge); a "How to use this" button next to every existing "Learn more"
button and a global `Help > Manual` (`F1`) entry point that focuses search
reach it directly from context - "nothing more than one search away." (A
permanent per-tab corner button was tried and removed the same day on user
feedback - redundant with clicking the tab it sat on.) Individual
toolbar-button/dialog-level entry points are a documented, deliberate
deferral, not a gap. 818 tests green. See `docs/manual-system.md`, `LOG.md`
entries "2026-07-03"/"2026-07-03b".
**2026-07-03c (user-commissioned, new track): Deployment Strategy (design) +
Phase 1 packaging (shipped).** `docs/deployment-strategy.md` designed the full
Version-1 path from developer-run project to installable Windows app
(PyInstaller onedir + Inno Setup + staged updates + a 5-phase roadmap; no ADR
yet). **Phase 1 (standalone executable) is shipped same day**:
`packaging/snomniman.spec` builds a real `SNOMNIMAN.exe` (PyInstaller
`--onedir`) that launches with no Python/uv/PowerShell/venv - validated live
against real neaSNOM sample data (CdO imaging + point-spectroscopy), exercising
Diagnostics, the Scientific Briefing, a full Processing Preview->Accept cycle,
Knowledge Center, and Manual, all inside the frozen build. See "Deployment
track" below and `docs/packaging-notes.md`, `LOG.md` entry "2026-07-03c".
**2026-07-03d (user-commissioned, adversarial audit): Release Readiness v1 +
Phase 2 (installer), both shipped same day.** Found and fixed two real
defects (no exe version resource; no installer yet), closed Phase 1's two
open gaps (a clean-machine proxy audit; zarr + figure export driven to
completion), then built and fully verified an Inno Setup installer
(per-user/no-admin, shortcuts, uninstall entry) through a real install ->
launch -> uninstall cycle. **Verdict: READY TO SEND** to the first external
(mentor) recipient. See "Deployment track" below,
`docs/release-readiness-v1.md`, `LOG.md` entry "2026-07-03d".

---

## How work is chosen now

**Foundational development is complete.** The architecture, the Measurement Explorer
(read-only + processing), the Description API, the Diagnostics Engine, the AI Scientist
(Briefing + the Reasoning Rule Engine), and the Knowledge Center are all shipped - 373
tests green; `ruff`, `mypy --strict`, and the Qt-free invariant clean. (Full shipped
detail is in `LOG.md` and the project-state memory; it is no longer enumerated here.)

Work is now driven by **two permanent planning systems**, not by feature ideas:

- **Product Roadmap -> [`docs/beta-readiness-v1.md`](docs/beta-readiness-v1.md):** which
  validated *workflow gaps* block a researcher's full day without neaPLOT.
- **Scientific Validation -> [`docs/scientific-validation.md`](docs/scientific-validation.md):**
  whether a *scientific capability* is justified by deterministic evidence.

Implement only at their intersection - *needed* **and** *validated*. See `CLAUDE.md`
("Planning and Governance") and `docs/roadmap.md` ("Current driver").

---

## Workflow automation track (Phase 4) - COMPLETE

`docs/phase4-workflow-automation.md` is the research-and-design blueprint (user-
commissioned); it introduced no new scientific judgment at any stage, so none of
4A/4B/4C entered the Scientific Validation gate - the whole track is reproducibility
infrastructure, judged only by whether it reuses existing abstractions (Rule 7).

- **Phase 4A - Processing Recipes. DONE (2026-07-02b, ADR-0031).** Capture a
  measurement's processing history as a portable `Recipe`, save/load it as a
  `.snomrecipe` file, browse/inspect/execute it in the same Processing Workspace
  through the same Preview -> Accept lifecycle. See `LOG.md` entry "2026-07-02b".
- **Phase 4B - Batch Processing. DONE (2026-07-02c, no ADR).** `snomniman.batch.
  run_batch` replays a `Recipe` over selected (or all) project measurements,
  headlessly, per-measurement success/skipped/failed outcomes + a run summary
  (elapsed time, stopped-early flag). Closed the documented **#1 daily-adoption
  gap** (Workflow C, `beta-readiness-v1.md`). See `LOG.md` entry "2026-07-02c".
- **Phase 4C - Scientific Reporting. DONE (2026-07-02d, no ADR).** `gui/report.py`'s
  `ReportModel` composes the Experiment Report / Publication Package /
  Reproducibility Report from facts already computed by `describe`/`diagnostics`/
  `ExperimentModel`/the provenance DAG/`BatchResult` - no new science, no AI
  interpretation, no PDF (deferred, documented). See `LOG.md` entry "2026-07-02d".

**Phase 4 is now fully shipped end-to-end** (Define -> Execute -> Document). The
natural next step is the Beta Readiness user-testing protocol with the complete
multi-scan workday available - let real friction choose the next priority rather
than guessing further ahead.

---

## Spectral / nano-FTIR track (Phase 5) - IN PROGRESS

`docs/phase5-spectral-nanoftir.md` is the research-and-design blueprint (user-
commissioned); it found the data model already handles hyperspectral/interferometric
capabilities correctly (no redesign needed), so none of 5A-5D reopen a settled
decision - only additive `Capability`/`Metadata` fields and new, precedented modules.

- **Phase 5A - Spectral Processing Foundations. DONE (2026-07-02e, no ADR).**
  `spectrum.fft_interferogram` (apodization/zero-fill/Mertz phase correction/
  forward FFT), `Capability.INTERFEROMETRIC`, `Metadata.interferometer`. Validated
  synthetically only; real-interferogram cross-validation stays `(user)`-gated.
  `spectrum.reference_normalize` (5A's other originally-scoped op) was **not**
  part of this increment - open for a follow-up. See `LOG.md` entry "2026-07-02e".
- **Phase 5B - Spectral Visualization & Hyperspectral Workspace. DONE
  (2026-07-02f, no ADR).** `ExplorerModel.is_hyperspectral` confirmed as a
  genuine third dispatch state (never an overload of `is_spectral`); `band_map`/
  `pixel_spectrum`/`rect_spectrum`/`polygon_spectrum`; the new `HyperspectralView`
  widget (linked band map + spectrum, click-to-inspect, multi-curve ROI
  overlay); Measurements framework `spectral` mode (`SpectralRegionReport`,
  "Overlay ROI spectra", CSV export); Report/Export/Knowledge integration
  (honest per-band facts, GSF band export, `wavenumber_index` persisted across
  save/reopen). Found and fixed a real Preview-crash bug (any non-2-D-image
  focus channel, incl. `spectrum.fft_interferogram`) along the way. Validated
  against a synthetic hyperspectral cube (Rule 6) + a manual visual check via a
  live screenshotted window. See `LOG.md` entry "2026-07-02f".
- **Phase 5C - Real-Data Readers. HARD-BLOCKED `(user)`, revisited and
  reconfirmed (2026-07-02g).** A full re-inventory of `SNOM Sample Files/` plus a
  repo-wide search found no new sample data since 5B: still exactly 3 imaging
  (`2D (PsHet)`) + 1 point-spectroscopy (`Point Spectroscopy (PsHet)`, a direct
  wavenumber sweep, **not** interferometric) measurement, no `opd`-domain
  interferogram export, no hyperspectral-cube export. Re-ran the full suite (791
  tests, incl. the real-PSP-data golden spectral tests) to reconfirm the
  architecture still holds against real data with zero change needed. No reader
  was implemented (nothing to validate one against - Rule 6); no code/ADR
  resulted. See `docs/phase5-spectral-nanoftir.md` sec 6.3 "Revisit note" and
  `LOG.md` entry "2026-07-02g". This remains the load-bearing blocker for turning
  either 5A or 5B into a real researcher workflow against actual instrument data.
- **Phase 5D - Spectral Diagnostics & Reasoning.** The *fact* half (a resonance/
  peak-identification diagnostic, reusing `viz.measure.analyze_profile` verbatim
  - already proven generic enough for a hyperspectral pixel/ROI curve, not just
  a line profile) can be validated synthetically now that 5A/5B produce real
  spectra to test against. The *recommendation* half is a **Scientific
  Validation Phase candidate**, not a direct product feature - enters the
  Validation Queue below, unstarted.

---

## Spectral lineshape analysis track (Phase 6) - COMPLETE (stages 1-4)

`docs/phase6-spectral-lineshape-analysis.md` is the research-and-design
blueprint (user-commissioned, from the user's mentor's real CdO point-
spectroscopy figure); it expands Phase 5D's originally narrower scope
(resonance *detection*) into a full ratio -> smooth -> fit -> report
workflow, deliberately deferring N-ary spectrum averaging, Gaussian/Voigt/
multi-peak fitting, and any auto-recommendation (stays behind the Scientific
Validation Phase gate - this whole track is user-invoked Category-A tooling,
judged only by Rule 6 synthetic validation, same as Phase 5A/5B).

- **Stage 1 - `spectrum.ratio` + `spectrum.savgol_smooth`. DONE (2026-07-14,
  no ADR).** `spectrum.ratio`: 2-input amplitude ratio between two spectral
  measurements (the second real consumer of the ADR-0030 2-input `InputSpec`
  pattern, after `image.arithmetic`; deliberately distinct from the
  still-open `spectrum.reference_normalize` same-measurement O/R division).
  `spectrum.savgol_smooth`: single-input Savitzky-Golay smoothing of a
  real-valued channel (`scipy.signal.savgol_filter`, no new dependency;
  closest precedent `image.line_flatten`). Both validated with known-answer
  tests (`(A/B)*B == A`; exact polynomial reproduction under `mode="interp"`)
  and auto-surface in the Processing Workspace with zero new GUI code. New
  Knowledge articles + Manual pages satisfy the no-drift tests. See `LOG.md`
  entry "2026-07-14".
- **Stage 2 - `viz.measure.fit_lineshape` (Lorentzian + linear baseline).
  DONE (2026-07-14b, no ADR).** The load-bearing analysis primitive (Section
  3.3 of the design doc: an **analysis**, not a `ProcessingStep` - binding
  for any future Gaussian/Voigt/multi-peak work), `scipy.optimize.curve_fit`
  bounded least squares, fit quality computed within the fit window only,
  `fit_curve`/`residuals` spanning the full input array. Validated with a
  known-good synthetic round-trip (`R^2 > 0.99`) *and* a known-bad-fit
  double-peak case (`R^2 < 0.6`, Rule 6). See `LOG.md` entry "2026-07-14b".
- **Stage 3 - `SpectrumPlotView` dual axis + lineshape-fitting UI. DONE
  (2026-07-14c, no ADR).** A wavenumber/wavelength dual axis (custom
  `pg.AxisItem`, shared tick positions, nonlinear-conversion labels) plus a
  "Fit window" region + "Fit Lorentzian" button calling the new
  `ExplorerModel.fit_spectrum_lineshape` and rendering the result (fit
  overlay, residual sub-plot, readout). **Deviated from the design doc's
  "third `MeasurementController` mode" sketch**, found by reading the actual
  controller code: `MeasurementController` is concretely ROI/
  `ChannelImageView`-shaped, not generic, so this landed as an additive
  `SpectrumPlotView` capability instead - smaller, more honest, now settled
  (see `LOG.md` for the full reasoning; do not revisit without a concrete
  third shape that needs unification, Rule 7). A curve change clears the fit
  result but keeps the window region ("geometry persists, results update",
  the same philosophy every other measurement here follows); re-fitting is
  always an explicit click, never silent recomputation. 15 new tests; full
  suite 859 passed; live-verified against real point-spectroscopy sample
  data (offscreen + screenshotted) - dual axis, fit toggle, and a real fit
  against the real O2A curve (R^2 = 0.56, honest not inflated) all confirmed
  working. See `LOG.md` entry "2026-07-14c".
- **Stage 4 - Spectral Peak Fits reporting + remaining Knowledge/Manual
  coverage. DONE (2026-07-14d, no ADR).** Per explicit user direction, kept
  to **one active fit, no history**: `gui/report.py`'s `ReportModel` gained
  an optional `active_lineshape_fit` slot composed verbatim into a new
  "Spectral peak fit (active)" section (Experiment Report + Publication
  Package, absent not empty when nothing is active); `window.py` sets it
  after a successful fit and clears it at the exact point the widget clears
  its own fit display, so the two can't drift apart. New Knowledge article
  `concept.lorentzian_lineshape` (states plainly that a low R^2/structured
  residual means the model doesn't apply, not a bug) and Manual page
  `explorer.spectrum_lineshape_fit`. 7 new tests; full suite 865 passed, 0
  failed. **Phase 6 is now fully shipped end-to-end, stages 1-4.** See
  `LOG.md` entry "2026-07-14d" for the complete scope ledger (what shipped
  vs. what stays deliberately deferred - N-ary averaging, Gaussian/Voigt/
  multi-peak, auto-recommendation, a fit-history list).
- **Real-data note.** Unlike Phase 5C (hard-blocked, zero interferogram/
  hyperspectral files exist), a real point-spectroscopy sample already
  exists (`...212518 PH PSP CdO Dense ROI 2`) and was used to live-verify
  stage 3 end to end. Reproducing the mentor's own figure numbers (the
  specific timestamps `173339`/`174013`/`182452`/`190507`) stays
  `(user)`-gated - no
  raw file behind those exists in this repository.

---

## Deployment track (packaging & distribution) - PHASE 1+2 SHIPPED

`docs/deployment-strategy.md` is the user-commissioned research/design
blueprint (no ADR yet - per `docs/roadmap.md`'s existing Phase 8+ placeholder,
the ADR is a deliverable of implementing each phase, not of the design). It
recommends **PyInstaller `--onedir`** for freezing and **Inno Setup**
(per-user install, no admin) for the installer, a staged update mechanism
(manual -> in-app GitHub-Releases check -> deferred background auto-update),
and a five-phase roadmap. This track is orthogonal to the product/science
tracks below - it does not change what SNOMNIMAN does, only how a researcher
gets and runs it.

- **Phase 1 - Standalone Executable. DONE (2026-07-03c, no ADR yet).**
  `packaging/snomniman.spec` builds a real onedir `SNOMNIMAN.exe` (~300 MB,
  ~4-5 s cold start) that launches with no Python/uv/PowerShell/venv. New:
  `packaging/snomniman_entry.py` (the freeze entry point), a
  `[project.gui-scripts]` entry, a generated `packaging/snomniman.ico`, and a
  `packaging` uv dependency group (not part of default `dev`). Validated live
  against real neaSNOM sample data (not synthetic): CdO imaging load,
  point-spectroscopy load (second modality), Diagnostics, Scientific
  Briefing, a full Processing Workspace Preview -> Accept cycle (provenance
  recorded), Knowledge Center, Manual, and the Export dialog opening
  correctly. See `docs/packaging-notes.md`, `LOG.md` entry "2026-07-03c".
- **Release Readiness Audit v1. DONE (2026-07-03d, `docs/release-readiness-v1.md`).**
  A user-commissioned adversarial "prove it's NOT ready" pass before the
  first external (mentor) recipient. Found and fixed two real defects: the
  exe shipped with **no Windows version resource** (fixed:
  `packaging/make_version_info.py` generates one from `pyproject.toml`), and
  **the installer didn't exist yet** (fixed: see Phase 2 below). Closed
  Phase 1's two open gaps: a sanitized-PATH launch + a 278-loaded-module
  origin audit (only Windows Defender's own DLL was external) stood in for a
  literal second machine; the zarr export was driven to a completed,
  independently-reloaded write, and figure export too (a real PNG +
  provenance sidecar). **Verdict: READY TO SEND** to the one mentor this
  milestone targets - see `LOG.md` entry "2026-07-03d" for the full record.
- **Phase 2 - Installer. DONE (2026-07-03d, no ADR yet).**
  `packaging/snomniman.iss` (Inno Setup 6) wraps the Phase 1 onedir build:
  per-user install with no admin prompt (`PrivilegesRequired=lowest` +
  `{autopf}`), Desktop + Start Menu shortcuts, a proper Apps-and-Features
  uninstall entry, the existing icon, one version identity
  (`packaging/make_iss_version.py`, same pattern as the exe's own version
  resource). Verified a complete real install -> launch (from the actual
  Start Menu shortcut) -> uninstall cycle - files/shortcuts/registry all
  confirmed present after install and completely gone after uninstall.
  Built: `packaging/installer_dist/SNOMNIMAN_Setup_0.1.0.exe` (88 MB).
- **v0.2.0 rebuild. DONE (2026-07-15, packaging only, no ADR).** User asked
  for a new build to send the mentor now that Phase 6 (spectral lineshape
  analysis) is complete. Bumped `pyproject.toml` to `0.2.0` (an initial
  build was cut as `1.2.0` on a misreading of "v1.2," then corrected once
  the user clarified they hadn't meant to skip versions; that build was
  discarded). Rebuilt `packaging/dist/SNOMNIMAN/SNOMNIMAN.exe` and
  `packaging/installer_dist/SNOMNIMAN_Setup_0.2.0.exe`; re-ran the same
  install -> launch -> uninstall verification as the v0.1.0 audit (version
  resource, Start Menu shortcuts, Apps-and-Features entry, and a clean
  uninstall all confirmed). See `LOG.md` entry "2026-07-15".
- **Immediate next steps** (both `(user)`, Recommended not Critical per the
  audit): (1) test the installer on a literal second machine/clean VM before
  distributing beyond this one mentor; (2) confirm CSV measurement export
  with an active Measure-panel selection (unverified, not known-broken, this
  session). Also: warn the mentor in advance about the expected Windows
  SmartScreen prompt (unsigned exe) before sending. (3) `docs/phase6-spectral-
  lineshape-analysis.md`'s header still says "Status: Design proposal, no
  code" - stale since Phase 6 shipped; fix next session.
- **Phases 3-5 (auto-update checking, code signing, enterprise/MSI).** Not
  started; deliberately sequenced after Phase 2 per the deployment strategy's
  own roadmap. Code signing (Phase 4) is what removes the SmartScreen warning
  permanently. Phase 5 (enterprise/MSI) is conditional - only build it if a
  specific lab's IT department actually asks (Rule 7).

---

## Product track - Beta Readiness blockers (the open-beta gate)

Beta Readiness Section 3, Critical. Each **reuses an abstraction that already exists** -
no new subsystem, and (for operations) no GUI code. Ordered. `(user)` = needs a human action.

> **The Critical cluster (C1-C4) + H1 is now COMPLETE (2026-06-29).** The strongest next step
> is the **user-testing protocol** (Beta Readiness Section 5) - a real workday is now possible
> end-to-end (multi-measurement, process, measure, save/reopen, export). After that, the **High**
> tier (H2-H5). Watching real users will re-order the remaining backlog better than any internal
> critique.

1. **C1 - Export the processed dataset. DONE (2026-06-29, ADR-0027).** GUI "Export ->
   Processed Data (Zarr)" wires `io.write_zarr` (loss-less); "Export -> Channel (GSF)" adds
   `io.export_channel_gsf` (one real grid + a provenance sidecar). Closes most of the Phase 4
   reproducibility gap. (G1)
2. **C2 - Export measurement numbers. DONE (2026-06-29, ADR-0027).** The Measure panel gained
   `Copy` + `Export CSV...`; Qt-free `gui.export` builders turn `ProfileSet` / `RegionReport`
   into CSV (provenance header, unit-bearing columns) over the validated `viz.measure`
   numbers. (G2)
3. **C4 - `image.line_flatten`. DONE (2026-06-28).** Registered `ProcessingStep` for
   per-scan-line median/mean/polynomial baseline removal (the genuinely-new flattening
   verb, distinct from `image.plane_level`; no `polynomial_flatten`, Rule 2). Validated
   analytically + on real CdO data, Knowledge article added, auto-surfaced in the
   Workspace/Diagnostics/Briefing with no GUI code. No auto-recommendation rule (needs a
   validated line-artifact diagnostic - a future science-track study). See `LOG.md`. (G4)
4. **C3 - Open more than one measurement. DONE (2026-06-29, ADR-0028).** `Project` is now a
   collection of `Measurement`s (the old single-measurement Project promoted to `Measurement`);
   a Measurement Manager dock + File New/Close Project, Add/Close Measurement; switching
   preserves each measurement's history/view/overlays with no disk reload; `.snomproj` schema v2
   with v1 migration; sequential never-reused ids. **This closes the whole Critical cluster
   (C1-C4 + H1).** (G3)

The **High** tier: **H1 project save/reopen - DONE (2026-06-29, ADR-0027):** `snomniman.pipeline`
`Project` + `save_project`/`load_project` (a `.snomproj` bundle of Zarr stores + manifest) reopen
a whole session with its provenance DAG intact -> meets the Phase 4 exit criterion. Remaining:
H2 keyboard navigation + persist representation, H3 background subtraction + height zero/offset,
H4 absolute-value profile + on-profile readout, H5 verbatim vendor-header view + metadata
search/copy. Full ordered backlog: [`docs/beta-readiness-v1.md`](docs/beta-readiness-v1.md)
Section 7.

---

## Science track - the Scientific Validation Queue

Candidate expert judgments. **Do not implement ahead of validation.** Each enters
through [`docs/scientific-validation.md`](docs/scientific-validation.md) (Question ->
Literature -> Candidate Diagnostics -> Analytical -> Synthetic -> Real-data -> Decision)
and ends in one of three outcomes - validate-and-implement / defer / stop. **Honest
deferral is success.**

> **Triage (2026-06-28), all three resolved:** **Line Flatten** = Category A (settled
> science; **shipped** via the product track, C4); **Harmonic ranking** = Category B
> (**shipped** - Outcome 1, ADR-0026); **Reference normalization criteria** = Category B
> (**DEFERRED** - Outcome 2, 2026-06-29: decline conditions defensible, positive branch
> unvalidatable on present data). The shared single-scan noise-floor primitive is shipped by
> harmonic ranking; reference normalization reused it but found quality necessary-not-
> sufficient (the deeper obstacle was reference *identity*, not strength).

- **Harmonic ranking** - **DONE (2026-06-28, Outcome 1).**
  [`docs/harmonic-ranking-analysis.md`](docs/harmonic-ranking-analysis.md) (ADR-0026): the
  signal-vs-noise *classification* (spatial coherence + single-image SNR) is validated on
  both branches and shipped in `diagnostics` (meets M4); the *informativeness ranking /
  best-harmonic recommendation* was **rejected** (the metrics conflate near-field with
  far-field background), so no reasoning rule. Produced the single-image noise-floor
  primitive the next study reuses.
- **Reference-normalization criteria - DONE (2026-06-29, Outcome 2: DEFERRED).**
  [`docs/reference-normalization-analysis.md`](docs/reference-normalization-analysis.md): the
  *decline* conditions (redundant / weak / noisy / empty reference) are defensible and
  validated, but the *positive* "appropriate" branch cannot be validated - all real data is
  PsHet "Self-Reference Off" with `R-` channels that are near-copies of the signal
  (`O/R ~ 1`, normalization erases contrast); appropriateness is experimental-design
  metadata the array lacks. No code.
- **Reference-normalization rule: WITHDRAWN (2026-06-29, honesty fix done).** The unvalidated
  flat-0.85 `ReferenceNormalizeRule` over-recommended on the available data, so its positive
  recommendation was **withdrawn** (`evaluate` returns `None`; the operation stays available;
  a regression test pins it). See the LOG entry. A *positive* rule remains deferred until a
  genuinely-referenced golden measurement validates the appropriateness branch `(user)`; if
  that arrives, restore it as a confidence-graded rule (recommend on a non-redundant,
  high-quality reference; decline on redundant/weak/noisy/empty) reusing the ADR-0026
  primitive + a redundancy metric.
- **Phase-wrapping recommendation** - **Outcome 2 already reached**
  ([`docs/phase-wrapping-analysis.md`](docs/phase-wrapping-analysis.md)): criterion
  defensible, rule deferred. Building the *diagnostic fact* (residues + unwrap-range +
  amplitude mask, with the synthetic known-answers as tests) is justified now; the
  *recommendation rule* is **blocked on a genuinely-wrapping real golden measurement**
  (nano-FTIR phase / interferometric / dispersive sample). `(user)`
- **Poor-scan / drift / tip-artifact detection** - revisit the metrics `diagnostics`
  currently defers (SNR / clipping / drift, ADR-0019) through the validation process;
  investigate honestly rather than guess (likely Outcome-2/3 candidates).

The canonical queue lives in `docs/scientific-validation.md` Section 7.

---

## Also pending (pulled in only when the loop calls for it)

- **Phase 2C - Multi-input processing & difference datasets. DONE (2026-06-29, ADR-0030).** The
  processing framework now supports multiple inputs (`InputSpec` + `check_compatibility`); the first
  multi-input op is the general two-input `image.arithmetic` (A-B / B-A / |A-B|). A two-parent
  derived dataset lives in the **primary** measurement's history while recording both parents in its
  DAG; no core/provenance/persistence change was needed (multi-input from the start). Further
  arithmetic modes (sum / ratio / normalized difference) extend the existing op's mode enum - no new
  framework work. **The processing foundation is complete.**
- **Scientific toolbox (Phase 3+, ongoing).** Phase 3A shipped `image.fix_zero` /
  `image.phase_offset` / `image.normalize_amplitude`; Phase 3B shipped the read-only analysis tools
  (line-profile features, region comparison, histogram) in Diagnostics + Measurements; Phase 3C
  shipped `image.region_phase_reference` / `image.region_amplitude_reference` + `ROI_RECTANGLE`
  hint (2026-06-30). Deferred from Phase 3C (later refinement phase): `image.region_plane_level` +
  `image.region_fix_zero` (topography region ops). Candidates for subsequent increments, **ordered
  by real-user feedback** (run the Beta Readiness user-testing protocol first): despike / scar
  removal; further `image.arithmetic` modes (sum / ratio / normalized difference); **frequency
  analysis** (2-D FFT / power spectrum / radial PSD) only if users need it (would add a spectral
  display surface); experiment-level comparison of the Phase 3B value objects. Histogram is in
  **Diagnostics**; other analysis-only views belong there too, not the Processing Workspace.
- **Concrete AI narrative provider** - ONE real provider behind the existing
  `NarrativeProvider` seam as an optional extra (`uv sync --extra ai`), lazy-imported,
  never required for backend/CI; tests mock it, CI never calls a network. A major
  dependency -> needs its own ADR. Suggestions/rules stay deterministic (ADR-0023); a
  provider only *phrases* them. **Not a beta blocker** (AI rule 2: AI never gates
  understanding).
- **Whole modalities / batch.** Point spectroscopy (`SPECTRUM`/`LINE_SCAN`) is now
  shipped end-to-end (`docs/point-spectrum-discovery.md`); the interferogram -> FFT
  -> `SPECTRUM` math (`INTERFEROGRAM` -> FFT, distinct from the direct wavenumber
  sweep already shipped) is shipped (Phase 5A); the `HYPERSPECTRAL` viewer/workspace
  (band map + linked spectrum, ROI measurements) is shipped against synthetic data
  too (Phase 5B, see "Spectral / nano-FTIR track" above). Remaining: real
  interferogram/hyperspectral **readers** (Phase 5C, hard-blocked on real sample
  data `(user)`). The `snomniman.batch` engine is now **shipped** (Phase 4B, see
  "Workflow automation track" above), built directly on the Phase 4A `Recipe` runner.
  Deliberate future phases - no reader/AI work ahead of a real sample file (Rule 6).
- **Read-only refinements** - mirror a measurement overlay into every comparison pane; a
  measurement "snap to pixel" / numeric-entry mode; free-form comparison layout; "Learn
  more" deep-links from diagnostics rows / harmonics / provenance / metadata (mechanism
  already generic).
- **Manual - toolbar/dialog-level entry points (deliberately deferred, ADR-0032).**
  Individual toolbar buttons (Single/Compare presets/Contact sheet/Export figure...) and
  dialogs (Save/Open/Batch) do not yet have their own inline "How to use this" button -
  they are documented Manual pages reachable via search/tree, just not an inline
  control. Revisit only if real usage shows the existing entry points (the tab itself,
  per-operation buttons, `Help > Manual`/F1) aren't enough.

---

## Blockers

- **Product track: none.** The Critical cluster (C1-C4) + H1 is **complete**; the next step
  is user-testing, then the High tier (H2-H5) - all reuse existing abstractions.
- **Science track:** the phase-wrapping *recommendation* is blocked on a
  genuinely-wrapping real golden measurement `(user)`; other queue items are unblocked
  investigations.

---

## Open Questions

**None architectural.** All OHD-1..9 are settled (`docs/decisions.md`); do not reopen a
settled decision without a new ADR. The open *questions* are now scientific (the
Validation Queue) and are resolved through evidence, not decision.

---

## Before committing to the order: watch real users

Run the Beta Readiness **user-testing protocol** (Section 5): put the running Explorer in
front of two or three neaPLOT users, ask them to finish a real analysis on their own data,
and record every forced exit to another tool (and at which task). Their forced exits will
order this backlog faster than any internal critique. This is the strongest validation
step and nothing here substitutes for it.

---

## Design docs to consult before GUI/AI work

- **`docs/product-philosophy.md`** - the identity/soul ("everything is a derivation of an
  immutable measurement") and the decision litmus. Check every UI/AI/workflow decision
  against it (and Rule 9).
- **`docs/measurement-explorer.md`** - the interaction-design blueprint / North Star.
- **`docs/phase2-vision.md`** - the broader UX experience blueprint.

**Working rule (user direction):** the design layer is complete - **no new design
documents unless implementation exposes a real problem.** (Governance/validation docs
requested explicitly, like this milestone's, are the exception.) The high-leverage work
is product depth and validated science, not more design.

---

## Definition of Done (per task)

Tests green (unit + invariant; for scientific code a synthetic/golden/reference
validation with a known answer), `ruff` clean, `mypy --strict` clean, the Qt-free
invariant green, docs updated if the design changed, `LOG.md` appended, this file
refreshed. For a **science-track** item, the validation document with its recorded
Outcome *is* the deliverable (code only on Outcome 1).

---

## Toolchain reminders

`uv` lives in the Python Scripts dir (may not be on PATH); invoke via its full path or
add that dir to PATH. Run checks with `uv run pytest` / `uv run ruff check .` /
`uv run mypy .`. The `.venv` interpreter also works directly:
`.venv/Scripts/python.exe -m {pytest,ruff,mypy}`. GUI deps: `uv sync --extra gui`;
headless GUI tests use `QT_QPA_PLATFORM=offscreen`. The 192 MB sample folder is
git-ignored (golden tests skip when absent).
</content>
