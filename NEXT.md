# NEXT.md - Immediate Priorities

Single source of truth for "what should the next session work on?" Keep current:
when a task is done, move it to `LOG.md` and update this file.

**Last updated:** 2026-07-02f (shipped **Phase 5B - Spectral Visualization &
Hyperspectral Workspace**: a complete spectroscopy workflow, not just a plot -
`ExplorerModel.is_hyperspectral` (a genuine third dispatch state, confirmed
necessary from live source, never an overload of `is_spectral`); `band_map`/
`pixel_spectrum`/`rect_spectrum`/`polygon_spectrum`; a new `HyperspectralView`
widget (`gui/hyperspectral.py`) linking a band map (the **unmodified**
`ChannelImageView`) to a spectrum plot (an additively multi-curve-extended
`SpectrumPlotView`) - click a pixel, see its spectrum live; select an ROI, see
the mean spectrum. The Measurements framework gained a `spectral` mode
(`SpectralRegionReport`, a separate "Overlay ROI spectra" action, CSV export)
so spectral ROIs are recorded/exportable exactly like image ones. Report/
Export/Knowledge integration completes the loop (honest per-band facts, GSF
band export, `wavenumber_index` persisted across save/reopen). **Found and
fixed a real bug during implementation**: Preview crashed for any non-2-D-image
focus channel (incl. Phase 5A's own `spectrum.fft_interferogram`) via an
uncaught `DatasetError` - fixed with a capability-aware dispatch, reusing the
existing spectrum viewer for curve-shaped previews (no new surface). Validated
against a synthetic hyperspectral cube with a known embedded resonance (Rule 6)
plus a manual visual verification via a live, screenshotted window. No AI
reasoning, spectral diagnostics, resonance fitting, or vendor readers
(deliberately out of scope). See `LOG.md` entry "2026-07-02f". Earlier: Phase 5A
Spectral Processing Foundations; Scientific Reporting (Phase 4C); Batch
Processing (Phase 4B); Processing Recipes (Phase 4A, ADR-0031); Point Spectrum
vertical slice (second data modality); Phase 3C region-aware ops; Phase 3B
scientific analysis toolbox; Phase 3A core operations; Phase 2C multi-input/
arithmetic; Phase 2B experiment analysis; Phase 2A multi-measurement projects;
complete research workflow. Governance: the Scientific Validation Phase + Beta
Readiness Review remain the planning systems). **2026-07-02g (no ship, revisit
only):** re-ran Phase 5C's data-validation gate - re-inventoried all real
sample data plus a repo-wide search for new interferogram/hyperspectral files;
found none; reconfirmed the architecture holds against real data (791 tests
green, incl. the real-PSP-data golden spectral tests). Phase 5C stays
hard-blocked, unchanged; no code/ADR. See `LOG.md` entry "2026-07-02g".
**2026-07-03 (shipped, user-commissioned, ADR-0032):** the **SNOMNIMAN
Manual** - a second Qt-free leaf package, `snomniman.manual`, the software
counterpart to the Knowledge Center (teaches *how*, never *why*). Structured
`ManualPage`s (41 initial, one per registered operation plus Explorer panels/
AI/export/settings/shortcuts/troubleshooting), cross-linked to Knowledge by
plain string id with **no new import edge** between the two leaf packages (a
dedicated cross-package test checks both link directions instead). A new
**Manual** Explorer tab, reachable via a "How to use this" button next to
every existing "Learn more" button, one corner-widget button that opens the
right page for whichever Inspect tab is active, and a global `Help > Manual`
(`F1`) entry point that focuses search - "nothing more than one search
away." Individual toolbar-button/dialog-level entry points are a documented,
deliberate deferral, not a gap. 819 tests green. See `docs/manual-system.md`,
`LOG.md` entry "2026-07-03".

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
  they are documented Manual pages reachable via search/tree/the corner-widget button,
  just not an inline control. Revisit only if real usage shows the three existing entry
  points (per-operation buttons, the tab corner button, `Help > Manual`/F1) aren't enough.

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
