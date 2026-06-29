# NEXT.md - Immediate Priorities

Single source of truth for "what should the next session work on?" Keep current:
when a task is done, move it to `LOG.md` and update this file.

**Last updated:** 2026-06-28 (shipped the harmonic signal-vs-noise classification - Candidate 2,
the first Scientific-Validation **Outcome 1**, ADR-0026; earlier: beta blocker C4
`image.line_flatten`. Governance: the Scientific Validation Phase + Beta Readiness Review remain
the planning systems)

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

1. **C1 - Export the processed dataset.** Wire the existing `io.write_zarr` (and/or
   `write_gsf`) into the GUI as "Export data...". Without it a beta tester cannot keep
   their work; also closes most of the Phase 4 reproducibility gap. (G1)
2. **C2 - Export measurement numbers.** Profile samples + region statistics to CSV +
   copy-to-clipboard on the stats table; reuses `viz` `ProfileSet` / `RegionReport`. (G2)
3. **C4 - `image.line_flatten`. DONE (2026-06-28).** Registered `ProcessingStep` for
   per-scan-line median/mean/polynomial baseline removal (the genuinely-new flattening
   verb, distinct from `image.plane_level`; no `polynomial_flatten`, Rule 2). Validated
   analytically + on real CdO data, Knowledge article added, auto-surfaced in the
   Workspace/Diagnostics/Briefing with no GUI code. No auto-recommendation rule (needs a
   validated line-artifact diagnostic - a future science-track study). See `LOG.md`. (G4)
4. **C3 - Open more than one measurement.** A File menu / Open / Recent so a multi-scan
   session is possible without relaunching. GUI-only. (G3)

Then the **High** tier: H1 project save/reopen (serialize the provenance DAG -> meets the
Phase 4 exit criterion; follows C1), H2 keyboard navigation + persist representation, H3
background subtraction + height zero/offset, H4 absolute-value profile + on-profile
readout, H5 verbatim vendor-header view + metadata search/copy. Full ordered backlog:
[`docs/beta-readiness-v1.md`](docs/beta-readiness-v1.md) Section 7.

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
- **Reference-normalization rule: gate or withdraw (the new next science item, an honesty
  fix).** The study found the existing flat-0.85 `ReferenceNormalizeRule` is unvalidated and
  **over-recommends** on the available data. A small follow-up should make it conservative -
  decline (or down-weight to tentative) on a redundant (`corr(|O|,|R|)` high / `CV(|O/R|)` ~
  0), weak/noise/empty, or high-near-zero reference (all deterministically detectable and
  validated) - rather than fire a flat prior. The *positive* branch stays deferred until a
  genuinely-referenced golden measurement exists `(user)`.
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

- **Product track: none.** The Critical cluster (C1-C4) reuses existing abstractions and
  can start immediately.
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
