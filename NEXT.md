# NEXT.md - Immediate Priorities

Single source of truth for "what should the next session work on?" Keep current:
when a task is done, move it to `LOG.md` and update this file.

**Last updated:** 2026-06-29 (shipped **Phase 2B - experiment analysis**, ADR-0029: a read-only,
Qt-free `ExperimentModel` that *aggregates* existing systems into experiment-wide views - an
experiment browser, cross-measurement comparison reusing the comparison viewer, a project-wide
diagnostics table, and cross-measurement ROI/line statistics with CSV export. No backend/provenance/
processing change. **Difference Views deferred to Phase 2C** - planned next. Earlier this date: Phase
2A multi-measurement projects, ADR-0028 (C3 done -> Critical cluster C1-C4 + H1 closed); and the
complete research workflow, ADR-0027 (C1/C2/H1). Governance: the Scientific Validation Phase + Beta
Readiness Review remain the planning systems)

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

- **Phase 2C - Difference Views (planned next; deferred from 2B, ADR-0029).** Difference
  datasets (B - A, |B - A|, ratio) as *derived, provenance-bearing* datasets. This is the
  write-path work 2B excluded: the **first multi-input `ProcessingStep`**, GUI surface to choose
  a second-measurement input, **grid/coordinate compatibility** (refuse on mismatch -
  resampling/registration stays out of scope), and the open **design decision** for where a
  **two-parent** derived dataset lives (a derived measurement vs. a results concept) given a
  `Measurement`'s history is linear. **Write a design proposal first** (same discipline as 2A/2B).
- **Concrete AI narrative provider** - ONE real provider behind the existing
  `NarrativeProvider` seam as an optional extra (`uv sync --extra ai`), lazy-imported,
  never required for backend/CI; tests mock it, CI never calls a network. A major
  dependency -> needs its own ADR. Suggestions/rules stay deterministic (ADR-0023); a
  provider only *phrases* them. **Not a beta blocker** (AI rule 2: AI never gates
  understanding).
- **Whole modalities / batch** - nano-FTIR / hyperspectral readers + spectral viewer
  (Phase 5/6); the `snomniman.batch` engine (Phase 6). Deliberate future phases.
- **Read-only refinements** - mirror a measurement overlay into every comparison pane; a
  measurement "snap to pixel" / numeric-entry mode; free-form comparison layout; "Learn
  more" deep-links from diagnostics rows / harmonics / provenance / metadata (mechanism
  already generic).

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
