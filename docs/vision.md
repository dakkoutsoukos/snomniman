# Vision

**Status:** Phase 0 (foundation) - **Last updated:** 2026-06-19

---

## 1. One-paragraph pitch

A modern, open, desktop application for analyzing **scattering-type scanning
near-field optical microscopy (s-SNOM)** and **nano-FTIR** data. It imports
instrument datasets (imaging, point spectroscopy, hyperspectral, approach
curves), visualizes them interactively, applies transparent and reproducible
processing pipelines, supports batch analysis, and exports publication-quality
figures and data. It is intended to be a long-lived scientific platform - a
modern replacement for, and eventual improvement on, neaPLOT - built around
scientific correctness, reproducibility, maintainability, extensibility, and
user experience.

## 2. Who it is for

- **Primary:** researchers and students acquiring and analyzing s-SNOM /
  nano-FTIR data (mid-IR / THz near-field spectroscopy and imaging, polariton
  imaging, nanoscale chemical mapping, phase-resolved optical contrast).
- **Secondary:** lab PIs and collaborators who need to *reproduce* a figure or
  re-run an analysis months or years later, and method developers who want to
  prototype new processing steps.

The user is assumed to be domain-expert but not necessarily a software engineer.
The tool should be powerful for experts and legible to newcomers.

## 3. The problem

Near-field datasets are multi-channel, complex-valued (amplitude **and** phase),
and come in several distinct shapes (2D maps, spectra, 3D hyperspectral cubes,
approach curves). Analysis typically involves a sequence of transformations -
leveling, phase correction, normalization/referencing, FFT of interferograms,
baseline and atmospheric correction - each with parameters and conventions that
materially change the scientific result.

Relative to typical vendor analysis software (e.g., neaPLOT), the common pain
points we aim to remove are:

- **Opaque provenance.** It is often hard to recover *exactly* which operations
  and parameters produced a published figure.
- **Limited reproducibility.** Re-deriving a result from raw data + history is
  not a first-class, guaranteed operation.
- **Weak batch / automation.** Applying the same workflow across many datasets
  is manual and error-prone.
- **Dated, closed UX and extensibility.** Hard to script, extend, or audit.

> We make claims about neaPLOT cautiously and only where we are confident.
> The goal is to *exceed* it on the axes below, not to disparage it.

## 4. Product principles

These derive directly from the project's development rules and are binding on
all design decisions.

1. **Scientific correctness first.** Units, coordinate conventions,
   normalization, and complex-valued semantics are explicit and validated, not
   assumed. An algorithm that "runs" is not assumed correct (Rule 6).
2. **Reproducibility is structural, not optional.** Raw data is never modified;
   every result is reconstructable from *raw + recorded processing history +
   parameters + environment* (Rule 5).
3. **Backend first.** All scientific functionality exists and is testable
   without launching the GUI. The GUI is a consumer (Rule 4).
4. **One coherent architecture.** Features extend existing abstractions rather
   than spawning parallel implementations; documentation is the single source of
   truth (Rules 1-3).
5. **Transparency.** Every transformation applied to data is visible, named, and
   inspectable by the user - the processing history is a first-class artifact,
   not a hidden side effect.
6. **Simplicity that can evolve.** No plugin systems, cloud, or distributed
   infrastructure until a concrete need exists (Rule 7). Refactor continuously
   (Rule 8).

### How it should *feel*

- *VS Code for SNOM analysis* - fast, scriptable, keyboard-friendly, transparent.
- *napari for near-field microscopy* - fluid interactive visualization of
  multi-dimensional data.
- Modern scientific software, not legacy vendor software.

## 5. What success looks like

- **Reproducibility:** any figure can be regenerated from a saved project +
  original raw files, byte-for-byte where the operations are deterministic, with
  a human-readable record of every step and parameter.
- **Correctness:** core processing steps are validated against synthetic data
  with analytically known answers and cross-checked against trusted references
  (including neaPLOT outputs on the same files).
- **Workflow speed:** common import -> process -> figure tasks are faster and have
  fewer manual steps than the incumbent workflow.
- **Batch:** a processing pipeline defined interactively can be applied,
  unchanged, to an entire folder of datasets headlessly.
- **Extensibility:** a new file format reader or processing step can be added by
  implementing one well-defined interface, without touching unrelated code.
- **Trust:** a collaborator can open a project and *understand exactly* what was
  done to the data.

## 6. Non-goals (for now)

- Not an acquisition/instrument-control system (read/analyze, do not drive
  hardware).
- Not a physical near-field modeling/simulation package (e.g., finite-dipole or
  point-dipole tip models). Simulation outputs may be *imported* for comparison,
  but **simulation is never promoted to a measured device spec.**
- Not a cloud service, collaboration server, or distributed compute system.
- No plugin marketplace, scripting-language sandbox, or general workflow engine
  until concretely justified.
- Not tied to a single vendor at the abstraction level, even though the first
  concrete readers target neaspec/neaSNOM data.

## 7. Scope boundaries (the contract)

The platform owns: **import, representation, visualization, processing,
provenance, batch, and export** of near-field optical microscopy data. Anything
outside that - acquisition, modeling, publishing - is either out of scope or an
explicitly justified future extension recorded in `decisions.md`.

See also: [`architecture.md`](architecture.md), [`data-model.md`](data-model.md),
[`roadmap.md`](roadmap.md), [`decisions.md`](decisions.md),
[`architecture-review.md`](architecture-review.md).
