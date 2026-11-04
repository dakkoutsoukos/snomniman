# Phase 6 - Spectral Lineshape Analysis (Research & Design)

**Status:** Design proposal, no code. Written at explicit user request (a
governance/validation-track design doc, the documented exception to NEXT.md's
"no new design documents unless implementation exposes a real problem" rule).
**Date:** 2026-07-14
**Origin:** the user's mentor (Vanderbilt) shared a reference figure, "CdO NPs
on CaF2 Point Spectroscopy" - a real analysis workflow from his own research,
given for inspiration, not as a feature request to copy verbatim. This document
extracts the *scientific* workflow from that figure, checks it against
SNOMNIMAN's existing architecture, and scopes a defensible first increment.

---

## 0. What the figure actually shows (read before everything else)

An AI-generated first pass at this figure over-read it (see the transcript
this document supersedes) - it inferred spectrum averaging, baseline
subtraction, Savitzky-Golay smoothing, and Lorentzian fitting as separate,
independent steps, and speculated about Gaussian/Voigt/multi-peak fitting and
publication figure generation. Re-reading the actual image narrows this
considerably:

1. **Four topography maps** (Z raw height, GSF-style 2-D scans) at two ROIs,
   each showing an overview + a zoom, with point-spectroscopy acquisition
   locations marked and labeled by timestamp (`173339`, `174013`, `182452`,
   `190507`). This is **navigation/registration context**, not a new analysis
   - SNOMNIMAN already renders topography and can already mark positions on a
   scan (the existing `SpectrumPlotView` position slider is the point-index
   analogue). No new capability needed here.
2. **One ratio, computed once per plot**: `average of 173339 & 174013 / 182452`
   - two point-spectra (both near ROI2) are averaged together, then the
   *result* is divided by a third point-spectrum's amplitude (near ROI3,
   evidently a lower-signal/substrate-like location). The y-axis is literally
   labeled "amplitude ratio (NP / substrate)".
3. **A Savitzky-Golay envelope** (`savgol mean`, window 81) plotted alongside
   the raw ratio - a smoothing pass, not a separate baseline-subtraction step.
4. **A single joint fit**: "Lorentz peak + linear baseline" over a restricted
   *fit window* (shaded region, e.g. 5600-6100 cm^-1), reported as one model
   with two parts (`baseline a, b` + the Lorentzian `x0`, FWHM, amplitude `A`),
   not two sequential operations. Fit quality is reported (`R^2`, `SSR/dof`,
   raw-vs-fit RMS) alongside the parameters and their uncertainties.
5. **A residual subplot** (`envelope - fit`) under each spectrum.
6. **A dual x-axis** (wavenumber cm^-1 on the bottom, wavelength um on top -
   `10000 / wavenumber_cm1`), on both the fit plot and the residual plot.
7. **A summary table** of `center x0` and `FWHM`, per harmonic (`O2A`, `O3A`),
   each value shown in both cm^-1 and its um-converted counterpart.

Two things are genuinely absent from the figure that the AI's first pass
invented: there is **one lineshape (Lorentzian) and one peak per fit** - no
Gaussian/Voigt, no simultaneous multi-peak fitting - and there is **no
separate baseline-subtraction step** - the baseline is a linear term fit
*jointly* with the peak, not removed beforehand.

---

## 1. Scope decisions (from user clarification, this session)

| Question | Decision |
|---|---|
| Sequencing | Design doc first (this document), then implement in stages. |
| Data source | The figure is the user's mentor's real research, given as a *reference target*, not accompanied by the underlying point-spectrum files in this repo today. |
| Lineshape scope | **Lorentzian, single-peak, first pass only.** Gaussian/Voigt/multi-peak are explicitly deferred to a later, separately-scoped increment. |
| N-ary averaging | **Deferred entirely.** The user's own reasoning (recorded verbatim, and endorsed here): averaging N spectra is a genuine architecture extension (today's multi-input processing, ADR-0030, is 2-input only) with exactly one prospective consumer right now - not enough to justify the extension under Rule 7. Ship the single-spectrum-pair workflow first; revisit N-ary `InputSpec` only if a second real consumer (batch averaging, PCA, clustering, spectral subtraction) shows up. |

This lands the v1 scope on exactly the part of the figure that is **not**
N-ary: `ratio(spectrum_A, spectrum_B) -> smooth -> fit(Lorentzian + linear
baseline) -> report`. "Average 173339 & 174013 first" is explicitly out of
scope for v1; a researcher instead picks *one* representative point spectrum
(or a single ROI-mean spectrum, once/if that exists for point data) as the
numerator.

---

## 2. Is this a 2-input operation, or does it reuse `image.reference_normalize`?

This distinction matters and the figure resolves it cleanly - it is
**neither** exactly:

- `image.reference_normalize` (shipped) divides a signal channel by its
  **matching reference channel within the same measurement** (`O2 / R_O2`,
  captured simultaneously by the instrument's own reference arm). It is
  single-input.
- The figure's ratio divides **two different point-spectroscopy measurements**
  (an "on-nanoparticle" acquisition by an "on-substrate" acquisition) - two
  separate `Measurement`s, each with their own provenance. This is
  structurally identical to the already-shipped **`image.arithmetic`**
  (ADR-0030): two named inputs (`primary`, `secondary`), a `check_compatibility`
  gate, one combination mode. `image.arithmetic` today only implements
  subtraction modes (A-B / B-A / |A-B|); it was explicitly designed to grow
  more modes ("future modes (sum, ratio, normalized difference, ...) extend
  the same operation rather than adding new step types" - `arithmetic.py`
  docstring).

Two implementation shapes were considered:

- **(a) Extend `image.arithmetic` with a `ratio` mode.** Rejected: that step
  is `SPATIAL_2D`-gated (`required_capabilities = (Capability.SPATIAL_2D,)`)
  and its compatibility check compares `x`/`y` coordinates - neither applies
  to a `SPECTRUM`/`LINE_SCAN` dataset. Bending it to also handle a
  `wavenumber` axis would blur one operation across two data kinds (Rule 2:
  don't duplicate/overload).
- **(b) A new `spectrum.ratio` step, same *pattern* as `image.arithmetic`,
  different module.** This is the one proposed here: identical shape
  (`InputSpec("primary"/"secondary")`, a `check_compatibility` gate, one
  `mode` parameter starting with a single `ratio` value so it can grow the
  same way `image.arithmetic` did), but living in `processing.spectrum`
  alongside `spectrum.fft_interferogram`, gated on `Capability.SPECTRAL`
  instead of `SPATIAL_2D`.

This is genuinely **not** a new architectural mechanism - it is the second
real consumer of the already-justified 2-input pattern (ADR-0030), which is
exactly the kind of reuse Rule 7 favors, in contrast to the N-ary case in
Section 1 which has no second consumer yet.

**Compatibility rule (mirrors `image.arithmetic`'s discipline of refusing
rather than reconciling):** the two spectra must share the same `wavenumber`
coordinate array (same acquisition sweep/settings) and the same requested
channel with matching complex-ness. SNOMNIMAN never silently resamples/
interpolates one spectrum onto another's axis - a mismatch is a clear refusal
message, not a silent approximation. (A real limitation worth naming: if a
researcher's two point spectra were acquired with different wavenumber
sampling, this step declines. Interpolation onto a common axis would be a
separate, explicit, future operation if real data shows this is a frequent
need - not assumed here.)

**Naming note.** Phase 5A's implementation note already flagged
`spectrum.reference_normalize` as "open for a follow-up... the spectral
analogue of the already-shipped `image.reference_normalize`" (i.e. same-
measurement O/R division). That remains a distinct, still-open, smaller
follow-up (Workflow W7 in `docs/phase5-spectral-nanoftir.md`) and should keep
that name when it is eventually built. The step proposed here is
`spectrum.ratio` - a different operation with a different `step_id`, so the
two do not collide.

---

## 3. Architecture placement

Three additive pieces, each locating in an existing module with an existing
precedent - no settled decision (OHD-1..9) reopened, no new subsystem:

### 3.1 `processing.spectrum.ratio` (new `ProcessingStep`)

- **Module:** `src/snomniman/processing/spectrum/ratio.py`.
- **Pattern:** mirrors `image/arithmetic.py` exactly (`InputSpec` pair,
  `check_compatibility`, one `mode` parameter defaulting to - and initially
  only supporting - `"ratio"` i.e. `primary / secondary`).
- **Gate:** `required_capabilities = (Capability.SPECTRAL,)`.
- **Value view:** operates on the amplitude view of a (possibly complex)
  optical channel, same helper shape as `_value_view` in `arithmetic.py`
  (`abs(.)` for complex, real value otherwise) - matches the figure's
  "amplitude ratio," not a complex ratio (phase ratio is not a meaningful
  quantity the figure asks for).
- **Provenance:** a two-parent `StepRecord`, exactly like `image.arithmetic`
  today - already fully supported by the DAG (ADR-0030), no persistence
  change.

### 3.2 `processing.spectrum.savgol_smooth` (new `ProcessingStep`)

- **Module:** `src/snomniman/processing/spectrum/savgol_smooth.py`.
- **Pattern:** single-input, structurally the simplest step in the codebase
  (closest precedent: `image.fix_zero` - one array transform, no shape/kind
  change).
- **Numerics:** `scipy.signal.savgol_filter` (`scipy` is already a project
  dependency, `pyproject.toml` pins `scipy>=1.11`, which has always shipped
  `signal.savgol_filter`; no new dependency).
- **Params:** `window_length` (odd, `int`), `polyorder` (`int`, must be `<
  window_length`) - both exposed via `ParameterSpec`, validated in `_execute`
  exactly like every existing step validates its own preconditions
  (`ProcessingError` with a clear message, not a stack trace).
- **Gate:** `required_capabilities = (Capability.SPECTRAL,)`.
- **Output:** a new `SPECTRUM`/`LINE_SCAN` dataset, same `DataKind`, channel
  `state` becomes `"smoothed"` (mirrors how `reference_normalize` sets
  `state="normalized"`).

### 3.3 A Lorentzian + linear-baseline fit - an **analysis**, not an operation

This is the one placement decision that needs real justification, because two
shapes are architecturally plausible:

- **As a `ProcessingStep`** (produces a new derived `Dataset` holding the fit
  curve + residual as a channel, provenance-tracked, chainable).
- **As a `viz.measure` analysis primitive**, consumed read-only by
  Diagnostics/Measurements/Reporting - never mutating, never entering the
  provenance DAG as a "result," exactly the precedent Phase 3B set for
  line-profile peak analysis and region comparison.

**Decision: analysis, not an operation**, for the same reason Phase 3B chose
that shape and Phase 5D's original scope already anticipated it
(`docs/phase5-spectral-nanoftir.md` sec 6.4: "reusing
`viz.measure.analyze_profile`/`_detect_peaks` verbatim... lands in
`diagnostics` as one new descriptor"). A curve fit's *purpose* here is to
report a number (`center`, `FWHM`, with uncertainty) about a spectrum a
researcher is already looking at - it is an **observation** of the ratio/
smoothed dataset, not a transformation that produces a new immutable
scientific object other steps should chain from. Fitting also needs a
user-chosen fit window and (implicitly) an initial guess - exactly the kind
of "the user selects a region, sees a computed fact" shape `RegionComparison`
already established, not the "accept and it becomes part of history"
shape a `ProcessingStep` implies. If real use later shows researchers want to
*export* the fit curve/residual as its own channel (e.g. to feed a further
processing step), that is a natural, later, additive `ProcessingStep`
extension - not assumed here (Rule 7).

- **Primitive location:** `src/snomniman/viz/measure.py`, alongside
  `analyze_profile`. New function `fit_lineshape(wavenumber_cm1, values, *,
  window, shape="lorentzian", baseline="linear")` and a new frozen,
  JSON-serializable dataclass `LineshapeFit` (center, center uncertainty,
  fwhm, fwhm uncertainty, amplitude, amplitude uncertainty, baseline
  coefficients, `r_squared`, `ssr_per_dof`, `rms`, the residual array, the fit
  window bounds, unit) - same shape discipline as `RegionComparison`/
  `ProfileFeatures` (frozen, `to_dict`-able, GUI-free, unit-tested with known
  answers).
- **Numerics:** `scipy.optimize.curve_fit` (also already covered by
  `scipy>=1.11`) over a `lorentzian(x, center, fwhm, amplitude) + a*x + b`
  model. Uncertainties come from `curve_fit`'s covariance output (standard
  nonlinear-least-squares practice, exactly the quantity the figure itself
  reports as `+/- ...`).
- **`shape="lorentzian"` is the only supported value in v1** - the parameter
  exists so Gaussian/Voigt can be added later as new values without a
  signature break, but nothing beyond Lorentzian ships now (Section 1).

### 3.4 GUI: a genuinely new Measurements mode for point spectroscopy

This is the largest, most honest piece of new work in this document, and it
was almost missed: `docs/point-spectrum-discovery.md` already states that for
a plain `SPECTRUM`/`LINE_SCAN` measurement (not hyperspectral), **Measure
declines entirely** ("image-only affordances... decline with an honest
message rather than crash"). The existing `MeasurementController.spectral`
mode (Phase 5B) is for **hyperspectral** ROI-mean-spectrum reports
(`SpectralRegionReport`), not for fitting a single point-spectrum curve. So
running a Lorentzian fit from the Explorer needs a **third** controller mode
- point-spectrum lineshape fitting on the one curve `SpectrumPlotView`
already shows - not a repurposing of either existing mode. This mirrors the
exact discipline Phase 5B's own Section 1 established for `is_hyperspectral`
("never an overload of `is_spectral`"): a new capability combination gets a
new, named dispatch state, not a bent existing one.

Concretely: a "Fit lineshape" action in the point-spectroscopy view lets a
researcher drag a fit window over the plotted curve (reusing pyqtgraph's
`LinearRegionItem`, already idiomatic for the existing `fit_window`-shaded
region visuals elsewhere in the codebase's plotting), choose which harmonic/
channel to fit, and see the fit curve + residual overlaid - presentation-only
(Rule 4), computing nothing itself, calling `viz.measure.fit_lineshape` and
rendering the `LineshapeFit` result via `SpectrumPlotView.show_curves` (already
multi-curve capable, Phase 5B) plus a small residual sub-plot (new, but a
narrow, self-contained widget addition).

### 3.5 Dual x-axis (wavenumber / wavelength)

`SpectrumPlotView` currently has one bottom axis (`wavenumber`, cm^-1) and no
top axis at all. The figure's top axis (`1e4 / wavenumber_cm1`, in um) is a
small, additive, purely presentational change: pyqtgraph supports a second
`AxisItem` linked to the same `ViewBox` via a fixed nonlinear tick-label
transform. This benefits every spectral view, not just the fit plot, so it is
proposed as a `SpectrumPlotView`-level addition rather than something specific
to the new fit widget.

### 3.6 Reporting: a "Spectral Peak Fits" table

`gui/report.py`'s `ReportModel` already composes sections purely from
already-computed facts (Phase 4C's stated discipline - "it computes nothing
new"). Once a researcher has run one or more lineshape fits via the new
Measurements action (Section 3.4), those `LineshapeFit` results are exactly
the shape `ExperimentTable`/`ReportSection` already renders (a row per
harmonic, columns for center/FWHM in both cm^-1 and its converted um value,
mirroring the figure's own table). This is a small, additive
`_spectral_fits_section()` alongside `experiment_report`'s existing sections -
no change to the `Report`/`ReportSection` data model.

### 3.7 Knowledge / Manual articles

Following the existing no-drift discipline (an `operation.*` Knowledge
article per registered step; a Manual page per registered step and per new
Explorer action): `operation.spectrum.ratio`, `operation.spectrum.
savgol_smooth`, a `concept.lorentzian_lineshape` (or similar) Knowledge
article explaining what a Lorentzian lineshape + linear baseline model means
physically and when it applies (vs. when it doesn't - e.g. asymmetric or
multi-component resonances, which this fit will visibly under-fit via a poor
`R^2`/structured residual, an honest signal the tool should not hide), and a
Manual page for the new "Fit lineshape" Measurements action.

---

## 4. What is explicitly deferred (and why)

| Deferred | Why |
|---|---|
| N-ary spectrum averaging | No second consumer yet for an `InputSpec` extension beyond 2 (Section 1, user's own reasoning). Revisit once averaging, batch-averaging, PCA, clustering, or spectral subtraction independently motivate it. |
| Gaussian / Voigt lineshapes | Out of scope for v1 by explicit user choice; add as new `shape=` values to the same `fit_lineshape` primitive later - no interface break anticipated. |
| Simultaneous multi-peak fitting | Same as above; the figure itself fits `O2A` and `O3A` as two *separate* single-peak fits over two different windows, not one joint multi-peak model - so v1's single-peak scope already covers the figure's actual method. |
| A separate baseline-subtraction processing step | The figure fits the baseline *jointly* with the peak; a pre-subtraction step would be a different (and less faithful) method, not requested. |
| `spectrum.reference_normalize` (same-measurement O/R division) | A distinct, smaller, already-flagged-open follow-up (Phase 5A/W7) - unrelated to this document's ratio step (Section 2's naming note). Not bundled in here to keep this increment's scope legible. |
| Auto-recommendation ("the AI suggests fitting a peak here") | Stays behind the full Scientific Validation Phase gate (`docs/scientific-validation.md`), exactly as Phase 5D's original scope already required. Nothing in this document is a `ReasoningRule` - it is a user-invoked tool the researcher chooses to run, parameterizes (fit window), and interprets (`R^2`), the same standing every Measurements-panel action already has. This is a Category-A engineering increment (Rule 6 synthetic/golden validation), not a Category-B/C science-track item requiring Literature -> Candidate Diagnostics -> ... -> Decision. |
| A dedicated "publication figure" export (raw + smoothed + fit + residual, dual-axis, in one exported image) | The existing per-figure `viz.figure` export plus the new Reporting table already cover the essential output. A composite figure template is real, additive GUI work that should earn its place against actual use (Rule 9) rather than being built speculatively; propose as a fast-follow once the fit tool is in a researcher's hands. |
| Atmospheric (water vapor / CO2) correction | Unrelated to this figure; already deferred in `docs/phase5-spectral-nanoftir.md` (W8) for its own reasons (needs a validated reference line-list). |

---

## 5. Validation plan (Rule 6)

- **`spectrum.ratio`:** `(A / B) * B == A` to floating precision on synthetic
  spectra (mirrors `image.reference_normalize`'s own existing test pattern);
  `check_compatibility` refuses mismatched wavenumber axes/complex-ness with a
  clear reason (tested like `image.arithmetic`'s existing compatibility
  tests).
- **`spectrum.savgol_smooth`:** Savitzky-Golay's own defining property - it
  reproduces a polynomial of degree <= `polyorder` exactly - gives a genuine
  known-answer test (a synthetic polynomial-plus-noise input, filtered output
  matches the noiseless polynomial within numerical tolerance); parameter
  validation errors (even `window_length`, `polyorder >= window_length`) are
  explicit `ProcessingError` cases, tested directly.
- **`fit_lineshape`:** the load-bearing test, following Phase 5A's Appendix A
  shape exactly: construct a synthetic Lorentzian + linear baseline with known
  `center`/`fwhm`/`amplitude`/baseline coefficients, add Gaussian noise at a
  documented SNR, fit it, and assert every recovered parameter is within a
  documented tolerance of the truth - plus a **known-bad-fit** case (fit a
  clearly non-Lorentzian synthetic peak, e.g. a double peak, and assert `R^2`
  drops and residuals show structure), so the tool is validated to fail
  honestly, not just to succeed on an easy case.
- **Real-data smoke test.** Unlike Phase 5C (hard-blocked - no interferogram
  or hyperspectral file exists anywhere in the repo), a real point-
  spectroscopy sample **already exists** in the sample data
  (`...212518 PH PSP CdO Dense ROI 2`, 100 positions x 201 wavenumbers,
  direct wavenumber sweep, per `docs/phase5-spectral-nanoftir.md` sec 6.3's
  inventory). It may not carry the mentor's specific O2A/O3A resonance
  behavior, but it is enough for an honest end-to-end smoke test: run
  `ratio` -> `savgol_smooth` -> `fit_lineshape` against two real positions
  from that file and confirm the pipeline produces finite, sane output rather
  than crashing or silently producing garbage. This is a real-data check
  available today, distinct from (and short of) a true golden-answer
  real-data validation.
- **The mentor's figure itself is a reference target, not a fixture.** No raw
  file behind timestamps `173339`/`174013`/`182452`/`190507` exists in this
  repository. If the user can obtain those underlying point-spectrum files,
  reproducing the figure's own reported numbers (e.g. O2A center
  6095.0 +/- 0.6 cm^-1) becomes the true golden-answer validation - `(user)`-
  gated, exactly like every other real-data milestone this project has run
  (Phase 1's GSF sample, the point-spectroscopy vertical slice, Phase 5C).

---

## 6. Roadmap / sequencing

Proposed as one coherent milestone (not split further), because the three
processing/analysis pieces are tightly sequential (ratio feeds smoothing
feeds fitting) and the GUI work is the genuinely risky part that needs to be
scoped honestly rather than assumed cheap:

1. `processing.spectrum.ratio` + `processing.spectrum.savgol_smooth` (Section
   3.1-3.2) - Category A, synthetic-validated, auto-surface in the existing
   Processing Workspace with zero new GUI code (the existing "no GUI code
   needed for a new operation" story, unchanged).
2. `viz.measure.fit_lineshape` + `LineshapeFit` (Section 3.3) - Category A,
   synthetic-validated (known-good and known-bad cases).
3. The new point-spectrum Measurements mode + dual-axis display (Sections
   3.4-3.5) - the one genuinely new GUI surface, sized similarly to Phase 5B's
   `HyperspectralView` (a new, bounded, presentation-only widget + a new
   `MeasurementController` dispatch state).
4. Reporting table + Knowledge/Manual articles (Sections 3.6-3.7) - small,
   additive, same pattern as every prior milestone's closing step.

No settled decision is reopened; the one real precedent-setting choice this
document makes is Section 3.3's "analysis, not operation" placement, which
should be treated as binding for any future lineshape-fitting work (Gaussian/
Voigt/multi-peak) rather than re-litigated per lineshape.

---

## 7. Success criterion

> *Can a researcher take two point-spectroscopy measurements already open in
> SNOMNIMAN, compute an amplitude ratio, smooth it, fit a Lorentzian + linear
> baseline over a chosen window, see the residual, and get a reportable
> center/FWHM with an honest uncertainty and fit quality - entirely through
> existing interaction patterns (Processing Workspace Preview/Accept for the
> two new operations, a Measurements-panel action for the fit), with nothing
> claimed that real data (not yet in this repo) is needed to actually prove?*

This document argues yes, at the scope in Section 1, using exactly three
small, precedented additions (two `ProcessingStep`s, one `viz.measure`
primitive) plus one genuinely new but bounded GUI surface - and names, rather
than implements around, the one real gap (no raw file behind the mentor's own
figure exists in this repository yet).

---

## Appendix - Cross-references

`CLAUDE.md` (Rules 1-9, the project maxim) - `docs/phase5-spectral-nanoftir.md`
sec 6.4 (Phase 5D's original, narrower scope, expanded here) and sec 6.3
(the real point-spectroscopy sample inventory this document's smoke test
reuses) - `docs/diagnostics-engine.md` / `docs/description-api.md`
(observations vs. operations, the distinction Section 3.3 turns on) -
`docs/point-spectrum-discovery.md` (the existing capability-gated decline
behavior for `SPECTRUM`/`LINE_SCAN` Measure/Comparison, the gap Section 3.4
closes) - `docs/scientific-validation.md` (the gate any future
*recommendation* around this tool would need to clear) -
`docs/harmonic-ranking-analysis.md` / `docs/reference-normalization-analysis.md`
(the precedent for "a valid fact/tool is not automatically a valid
recommendation") - `src/snomniman/processing/image/arithmetic.py` (the
2-input pattern `spectrum.ratio` reuses) -
`src/snomniman/processing/image/reference_normalize.py` (the same-measurement
O/R pattern `spectrum.ratio` is deliberately distinct from) -
`src/snomniman/processing/spectrum/fft_interferogram.py` (the
`processing.spectrum` subpackage precedent) - `src/snomniman/viz/measure.py`
(`analyze_profile`/`RegionComparison`, the analysis-primitive pattern
`fit_lineshape` follows) - `src/snomniman/gui/spectrumview.py`
(`SpectrumPlotView`, `show_curves`) - `src/snomniman/gui/measurement.py`
(`MeasurementController`'s existing `spectral` mode, the template for the new
mode) - `src/snomniman/gui/report.py` (`ReportModel`, the composition-only
discipline the new table section follows).
