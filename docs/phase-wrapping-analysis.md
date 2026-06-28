# Phase-Wrapping Detectability Analysis (a Scientific Validation milestone)

> **Question:** *When should an experienced SNOM researcher recommend phase
> unwrapping - and can that judgment be made deterministically, with enough
> scientific confidence to justify an automatic recommendation rule?*
>
> **Status: analysis only.** No code, no diagnostic, no recommendation rule is added
> by this milestone (per the project maxim: a missing rule is preferable to an
> unjustified one). This document records the science, the candidate diagnostics, an
> empirical validation, and a conclusion about whether a rule is warranted **yet**.

This is the first milestone of - and the worked exemplar for - the **Scientific
Validation Phase** ([`scientific-validation.md`](scientific-validation.md), the canonical
methodology; this document predates and motivated its formalization). The deliverable is
not a feature but an answer - *validate one expert judgment, deterministically, or conclude
honestly that we cannot yet*. Its sections map onto the standard validation template; the
conclusion is **Outcome 2** (defensible criterion, recommendation rule deferred).

---

## 1. Scientific background

**Wrapped vs unwrapped phase.** A complex near-field channel `O{n} = A·exp(iφ)` carries
an optical phase `φ`. What an instrument records is the *wrapped* phase
`ψ = atan2(Im, Re) ∈ (-π, π]` - the true phase modulo 2π. The *unwrapped* phase
`φ = ψ + 2π·k(x,y)` (integer field `k`) is recovered by adding/subtracting 2π wherever
the wrapped phase crosses the ±π branch cut. SNOMNIMAN never transforms phase silently
(OHD-6D): `ψ` is stored as imported, and unwrapping is an explicit, recorded operation
(`image.phase_unwrap`) that produces a **new** real channel (OHD-4).

**Why wrapping occurs.** Wrapping happens when the *true* phase spans more than 2π
across the field (a steep ramp, a thick/dispersive sample, a strong resonance, an
interferometric drift). If the true phase stays within a 2π interval, the wrapped phase
is identical to the true phase and there is **nothing to unwrap**.

**The s-SNOM / nano-FTIR specifics (why this is not obvious).**
- The demodulated optical phase of a *single harmonic* `φ_n` is a **relative near-field
  phase**; for many samples it is bounded well within a 2π interval and does **not**
  wrap. (Confirmed empirically in §4.)
- Phase **does** commonly wrap in: nano-FTIR spectral phase across a strong vibrational
  resonance; interferometric/white-light measurements; thick or strongly dispersive
  samples; and topography-correlated phase with large height excursions.
- Therefore "this is a phase channel" is **not** sufficient evidence that unwrapping is
  needed. A blanket "unwrap the phase" recommendation would be wrong most of the time
  for harmonic s-SNOM imaging.

**Common pitfalls (why naive detection fails).**
- **Noise.** A noisy but *bounded* phase has many adjacent samples whose difference
  exceeds π purely by chance. Counting "big jumps" therefore *cannot* distinguish
  genuine wrapping from noise.
- **Phase singularities / optical vortices.** Polariton interference and some near-field
  configurations produce genuine phase vortices (points of `2π` circulation). These are
  *physical*, not artifacts, and are fundamentally **not** unwrappable to a single-valued
  field - "unwrapping" them is ill-defined.
- **Amplitude weighting.** s-SNOM phase is only meaningful where the amplitude is
  significant. In low-amplitude regions the phase is pure noise and must be excluded
  before any wrapping statistic is trusted.

---

## 2. The scientific question, decomposed

*When should an expert recommend unwrapping `O{n}`?*

| Evidence class | Condition |
|---|---|
| **Necessary** | The channel is a phase view of a complex channel, **and** the true phase genuinely spans more than 2π (real wrapping is present, not just noise). |
| **Sufficient** | The wrapped field is **residue-free** (path-independent) over the amplitude-significant region - so unwrapping is unique and the implemented integrator is exact. |
| **Ambiguous** | Moderate residue density: some coherent wrapping plus some noise/singularities. Unwrapping is path-dependent; the simple integrator can streak. *Recommending here is not defensible.* |
| **Impossible / inappropriate** | Noise-dominated phase (high residue density); genuine phase singularities/vortices (residues are physical); or bounded phase that never wraps (nothing to do). |

The "sufficient" row is tied to the **implemented algorithm**: `image.phase_unwrap` uses
sequential 1-D `numpy.unwrap` (along x, then y) - a single integration path. By the
residue theorem this is **exact iff the field is residue-free**, and produces
path-dependent artifacts otherwise. So the only scientifically honest recommendation
criterion is one that fires **only** in the regime where the cheap operation is valid.

---

## 3. Candidate diagnostics (from the literature - none invented)

| Diagnostic | What it measures | Verdict |
|---|---|---|
| **Wrapped-edge / discontinuity count** | Fraction of adjacent pixels with `|Δψ| > π`. | *Necessary signal but not defensible alone* - indistinguishable from noise (§1 pitfalls, §4). |
| **Residues (branch points)** - Goldstein, Zebker & Werner 1988; Ghiglia & Pritt 1998 | Sum the wrapped phase gradients around each 2×2 loop; the result is `0` or `±2π`. A nonzero "residue" marks a point where the field is path-dependent (inconsistent). **Zero residues iff the field is uniquely, path-independently unwrappable.** | **The rigorous, defensible core.** Cleanly separates coherent wrapping from noise/singularities (§4). |
| **Unwrap-range ratio** | `range(unwrap_2d(ψ)) / 2π`. `> ~1.5` indicates genuine multi-2π wrapping (something to unwrap); `≈ 0–1` means the phase never wraps. | Defensible as the *presence-of-wrapping* signal (pairs with residues). |
| **Quality / coherence map + amplitude mask** | Restrict all statistics to amplitude-significant pixels (phase is noise where `A → 0`). | Defensible and necessary as a *mask* (standard quality-guided practice). |
| Quality-guided / Lp-norm / branch-cut **unwrapping algorithms** | *How* to unwrap a residue-bearing field. | Out of scope - these are unwrappers, not detectors of whether unwrapping is warranted. |

The defensible combination is therefore: **residue density** + **unwrap-range ratio**,
both computed over the **amplitude-masked** region. Wrap-edge fraction alone is rejected.

---

## 4. Validation (analytical known-answers + the real measurement)

A throwaway investigation (not product code) computed residue density, wrap fraction,
and unwrap-range ratio on analytically-known synthetic fields and on the real
measurement. Results:

**Synthetic (known answers) - the residue diagnostic behaves exactly as theory predicts:**

| Field | residue density | unwrap-range / 2π | Interpretation |
|---|---|---|---|
| Coherent linear ramp, 6 wraps | **0.0000** | 5.96 | clean multi-2π wrapping -> *would recommend* |
| Single phase vortex (`atan2`) | 1 residue (≈5e-5) | 1.00 | one physical singularity -> *not unwrappable* |
| Uniform phase noise | **0.333** | 25.4 | noise -> *reject* |
| Ramp + mild noise (σ=0.3 rad) | 0.0000 | 6.21 | still coherent -> *would recommend* |
| Ramp + heavy noise (σ=1.5 rad) | 0.246 | 19.1 | coherence destroyed -> *reject* |
| Bounded smooth phase (no wrap) | 0.0000 | 0.16 | nothing to unwrap -> *decline* |

This confirms: **residue density separates "coherent, unwrappable wrapping" (≈0) from
"noise / singularities" (large)**, and the **unwrap-range ratio** separates "wraps" from
"does not wrap" - exactly the two facts the decision needs. Wrap-edge fraction alone
fails (0.02 for the clean ramp vs 0.25 for noise, but also 0.06 for ramp+noise) - it does
not cleanly threshold.

**Real measurement (the CdO Dense ROI 2, the 32-channel s-SNOM scan), optical phase
channels (`angle(O{n})`):**

| Channel | residue density | unwrap-range / 2π | Reading |
|---|---|---|---|
| O0 | 0.0000 | 0.00 | flat / uninformative |
| O1 | 0.0000 | 0.38 | **bounded - does not wrap** |
| O2 | 0.0000 | 0.37 | **bounded - does not wrap** |
| O3 | 0.0000 | 0.51 | **bounded - does not wrap** |
| O4 | 0.0002 | 1.76 | apparent wrapping, but **100% of residue cells are in low-amplitude (noisy) regions** |
| O5 | 0.0000 | 0.00 | flat |

**Empirical finding:** on this real s-SNOM measurement, the optical phase of every
informative harmonic (O1–O3) is **bounded within roughly ±π and does not wrap**. The one
channel with an above-threshold unwrap-range (O4) has all of its residues in
low-amplitude noise - i.e. its "wrapping" is not coherent signal. **An automatic
phase-unwrap recommendation would correctly decline on all six channels.** This matches
the physics of §1: demodulated single-harmonic s-SNOM optical phase is usually bounded.

---

## 5. Recommendation criteria (specified, but see the conclusion)

If/when a rule is implemented, the scientifically defensible criterion is:

- **Necessary (presence):** `unwrap_range_ratio > 1.5` over the amplitude-masked region
  (the true phase genuinely spans multiple 2π).
- **Sufficient (well-posed):** `residue_density ≈ 0` over the amplitude-masked region
  (path-independent; the implemented 1-D integrator is exact).
- **Mask:** compute both only where amplitude exceeds a percentile (e.g. the upper
  ~60%), because phase is meaningless where `A → 0`.
- **Confidence:** highest when `residue_density == 0` and the unwrap-range ratio is
  clearly `> 1.5`; decreasing as residue density rises; **decline** (no recommendation)
  once residue density crosses a strict, small threshold, or the unwrap-range ratio is
  near 1 (no real wrapping).
- **Assumptions:** the target is a single-harmonic optical/mechanical phase; the simple
  sequential unwrapper is the executor (hence the residue-free gate); vortices and
  noise both correctly fall in the "decline" region.

This criterion is **safe by construction**: it fires only where the implemented
operation is exact, and declines on noise, vortices, and non-wrapping phase alike.

---

## 6. Conclusion

**Outcome: a deterministic criterion is scientifically defensible and
analytically validatable - but an automatic recommendation *rule* is deferred, on
honest grounds, until its positive branch can be validated on real wrapping data.**

1. **The science is sound.** Residue density (Goldstein 1988; Ghiglia & Pritt 1998) plus
   the unwrap-range ratio, over an amplitude mask, deterministically distinguish
   "coherent, uniquely-unwrappable wrapping" from "noise / singularities / no wrapping."
   This is validated against analytical known-answer synthetic fields (§4).
2. **The honest gap is real-data validation of the *recommend* branch.** Every real
   measurement available to the project (the CdO scan) has **bounded, non-wrapping**
   optical phase. We can validate that the rule correctly *declines* on real data; we
   **cannot** yet validate that it correctly *recommends* on real data, because we have
   no real measurement that genuinely wraps (this would need e.g. nano-FTIR spectral
   phase, an interferometric/white-light scan, or a thick/dispersive sample). Project
   Rule 6 requires synthetic **and** reference validation; only the former is achievable
   today for the positive case.
3. **Therefore, by the project maxim, defer the rule and (optionally) build only the
   fact.** A missing rule is preferable to a rule whose central behaviour we cannot
   reproduce on a real measurement. The *diagnostic* itself (residue density +
   unwrap-range ratio + amplitude mask) is, separately, a defensible deterministic
   **observation** - it would let the Briefing/Diagnostics state, truthfully, "the
   optical phase does not wrap (no unwrapping needed)" or "the phase wraps coherently."
   Building that fact is justified now; registering an *auto-recommendation* on it
   should wait for a genuinely-wrapping golden measurement.

**Practical consequence.** `image.phase_unwrap` remains fully available to the
researcher in the Processing Workspace (manual, explicit, recorded). What this analysis
declines to do - until the evidence exists - is have the AI Scientist *recommend* it
automatically. That is the correct outcome: SNOMNIMAN will not assert an expert judgment
it cannot defend on real data.

### Concrete next steps (when prioritised)
1. Add a **`phase_wrapping` diagnostic** to `snomniman.diagnostics` (residue density,
   unwrap-range ratio, amplitude-masked), with the §4 synthetic cases as known-answer
   tests (Rule 6). It reports a fact; it makes no recommendation.
2. Obtain a **genuinely-wrapping real measurement** (nano-FTIR phase or interferometric
   scan) as a golden reference for the positive branch.
3. Only then register a `ReasoningRule` for `image.phase_unwrap` using the §5 criterion -
   a ten-line `@register_rule` once the fact and its golden validation exist.

---

## References

- R. M. Goldstein, H. A. Zebker, C. L. Werner, "Satellite radar interferometry:
  Two-dimensional phase unwrapping," *Radio Science* **23**(4), 713–720 (1988). (Residues
  / branch cuts; the path-independence theorem.)
- D. C. Ghiglia, M. D. Pritt, *Two-Dimensional Phase Unwrapping: Theory, Algorithms, and
  Software*, Wiley (1998). (The standard reference; residue theory, quality maps,
  quality-guided and Lp-norm unwrapping.)
- F. Keilmann, R. Hillenbrand, "Near-field microscopy by elastic light scattering from a
  tip," *Phil. Trans. R. Soc. Lond. A* **362**, 787–805 (2004). (s-SNOM optical
  amplitude/phase as the demodulated near-field response.)
