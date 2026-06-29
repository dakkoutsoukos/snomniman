# Reference-Normalization Recommendation Analysis (a Scientific Validation milestone)

> **Question:** *Under what deterministic conditions should SNOMNIMAN recommend reference
> normalization (`image.reference_normalize`)? Distinguish "possible" from "appropriate"
> from "strongly recommended" - and can the recommendation criterion be validated on real
> data on both branches (correctly recommending where it helps AND declining where it does
> not)?*
>
> **Status: Outcome 2 (DEFERRED).** No code. The *decline* side is deterministically
> defensible and validated (a redundant, weak, noisy, or empty reference). The *positive*
> side - "this reference is a meaningful common-mode response, so normalizing improves
> interpretation" - **cannot be validated on present data**: every available real
> measurement is "Self-Reference Off" and its `R-` channels are near-copies of the signal
> (`O/R ~ 1`), so normalization would *erase* contrast, not improve it. Appropriateness
> turns on experimental design (was a genuine reference measured on a known substrate?)
> that the data does not encode. The evidence-based `ReferenceNormalizeRule` refinement is
> therefore deferred. **A secondary, important finding:** the *existing* flat-0.85 rule is
> itself unvalidated and over-recommends on the available data (see §7).

This is the third Scientific Validation milestone ([`scientific-validation.md`](scientific-validation.md)),
the Candidate-3 study triaged in [`next-scientific-priorities.md`](next-scientific-priorities.md).
It builds directly on the harmonic signal/noise primitive validated in
[`harmonic-ranking-analysis.md`](harmonic-ranking-analysis.md) (ADR-0026) and follows the
nine-section template. Its conclusion mirrors phase-wrapping (Outcome 2): a sound criterion
whose *positive* branch lacks a real measurement to validate it.

---

## 1. Scientific question

`image.reference_normalize` divides each complex optical signal channel by its
same-harmonic reference (`O{n} / R_O{n}`): amplitude becomes a dimensionless ratio, phase
becomes a difference relative to the reference. The operation *exists, is capability-gated,
and is analytically validated* (`(O/R)*R == O` to machine precision). The open question is
purely about **recommendation** - when the engine should propose it. Three statements,
which the brief rightly demands be kept distinct:

| Statement | Meaning | Verdict (preview) |
|---|---|---|
| **Possible** | References exist and complex optical signals are still raw. | **True & shipped** - structural trigger; the operation runs. |
| **Appropriate** | The reference is a *meaningful, independent common-mode response*, so dividing removes the shared system response and reveals material contrast. | **Not deterministically decidable** from the measurement (it is an experimental-design fact); the data can flag clear *in*appropriateness but cannot confirm appropriateness. |
| **Strongly recommended** | Appropriate **and** it materially improves quantitative interpretation. | **Not justified deterministically** - requires appropriateness, which is unestablished. |

An experienced researcher recommends normalization when the reference is a genuine
common-mode measurement (e.g. on a known substrate such as Au/Si) shared across
acquisitions, **and** the reference is strong enough that the division is well-posed. They
decline when the reference is near the noise floor (division injects noise), when the
"reference" is not actually an independent reference (dividing is meaningless), or when the
signals are already normalized.

---

## 2. Literature review

- **The operation is standard practice.** Dividing a near-field spectrum/image by a
  reference taken on a non-resonant material removes the common instrumental and
  illumination response, yielding relative amplitude `|O|/|R|` and referenced phase
  `arg(O) - arg(R)` (Keilmann & Hillenbrand 2004; for nano-FTIR, Huth et al. 2012). PsHet
  detection (Ocelic, Huber & Hillenbrand 2006) already provides background-free amplitude
  and phase; reference *normalization* is a further, deliberate step taken when a
  meaningful reference exists.
- **The failure mode is well understood qualitatively.** Where the reference amplitude
  approaches zero, the quotient amplifies noise without bound; where the reference phase is
  undefined (near-zero amplitude), the referenced phase is random. This is the basis of the
  caveat already in the shipped rule.
- **What the literature does *not* provide** is a single-measurement, deterministic test
  for "is this `R-` channel a *meaningful* reference?" That is an experimental-design fact
  (what was R measured on?), not a property recoverable from the array alone. The closest
  deterministic surrogates are reference *quality* (is R above the noise floor?) and
  reference *redundancy* (is R merely a copy of the signal?), both borrowed below from
  established image statistics rather than invented here.

---

## 3. Candidate diagnostics

Per the brief, these **reuse** the harmonic primitive (ADR-0026) applied to the *reference*
channel; no new noise estimator is introduced.

| Diagnostic | What it measures | Role |
|---|---|---|
| **Reference signal classification** (coherence + single-image SNR on `R_O{n}`) | Is the reference above the noise floor? (`signal`/`weak`/`noise`/`empty`) | **Decline** support: a `noise`/`weak`/`empty` reference is an unsafe divisor. |
| **Reference near-zero fraction** | Fraction of `R` pixels at/below `R`'s own noise floor (where `O/R` blows up) | **Decline** support: high fraction -> noise amplification. |
| **Reference redundancy** = `corr(|O|, |R|)` and the coefficient of variation of `|O/R|` | Is `R` merely a near-copy of `O` (so `O/R ~ const`)? | **Decline** support: `corr -> 1`, `CV -> 0` means normalization erases contrast. |
| **Channel state / provenance** | Are signals already `normalized`? | **Decline** support (already in the trigger). |
| A **positive** "this reference is meaningful" test | Confirm appropriateness from the array | **None found.** Quality + non-redundancy are *necessary* but not *sufficient* (§5); appropriateness needs reference-identity metadata the data lacks. |

The decisive structural point, established in §5: **reference quality and non-redundancy are
necessary conditions for appropriateness, but no deterministic *sufficient* condition
exists.** The diagnostics can defensibly say "do not normalize"; they cannot defensibly say
"do normalize."

---

## 4. Analytical validation

The complex quotient `O/R = (|O|/|R|) * exp(i(arg O - arg R))` makes the regimes exact:

- **Well-posed** where `|R|` is bounded away from zero and `R` is a *distinct* common-mode
  factor: the ratio is finite and carries the relative response. The implemented operation
  is exact here (`(O/R)*R == O`).
- **Ill-posed (noise amplification)** as `|R| -> 0`: `|O|/|R| -> infinity` and `arg(R)`
  becomes undefined, so both normalized amplitude and phase are dominated by noise. The
  reference near-zero fraction directly counts this regime.
- **Redundant (contrast erasure)** when `R = c * O` (a scalar common-mode times the signal,
  the limiting case of a "self-referenced" or copied channel): `O/R = 1/c` is *constant* -
  the spatial contrast is removed entirely. `corr(|O|,|R|) = 1` and `CV(|O/R|) = 0` detect
  this exactly.

These three closed-form regimes are what the candidate diagnostics must separate; the
synthetic check confirms they do.

---

## 5. Synthetic validation

Known-answer cases (96x96; smooth complex signal `O`; `scratchpad/synth_reference.py`).
Reference classification reuses the shipped primitive; redundancy uses `corr(|O|,|R|)` and
`CV(|O/R|)`:

| Reference case | R class | R SNR | R near-zero | corr(\|O\|,\|R\|) | CV(\|O/R\|) | blow-up | phase(O/R) std | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---|
| **A. strong, independent** | signal | huge | 0 % | **0.49** | **0.19** | 0 % | 0.27 | **appropriate** (contrast survives) |
| **B. weak / noisy** | noise | 0.45 | 18.8 % | 0.16 | 1.54 | 0.8 % | 1.43 | **decline** (noise injected) |
| **C. copy of signal** | **signal** | 98 | 0 % | **1.00** | **0.00** | 0 % | 0.00 | **decline / redundant** (contrast erased) |
| **N. pure noise** | noise | 0.15 | 18.8 % | -0.01 | 1.69 | 0.7 % | 1.83 | **decline** |

Two known-answer facts settle the design:

1. **Reference quality alone is not sufficient.** Cases **A** (appropriate) and **C**
   (redundant) are *identical* on every quality metric - both `signal`-class, high SNR,
   0 % near-zero. Only the **redundancy** metrics separate them (A: corr 0.49 / CV 0.19;
   C: corr 1.00 / CV 0.00). A quality-graded positive confidence would therefore rate the
   redundant case **C** exactly as highly as the appropriate case **A** - and be wrong.
2. **The decline conditions are cleanly detectable.** Weak/noisy (B, N) and redundant (C)
   references are each flagged deterministically (by class/near-zero, and by corr/CV
   respectively).

But note what synthetic data *cannot* do: case **A** is *constructed* to be a meaningful
reference. On real data we cannot construct intent - we can only observe quality and
redundancy, and "non-redundant + high-quality" still does not prove a channel is a
*meaningful* reference (it could be any unrelated strong channel). The positive branch thus
needs **real** validation, which §6 shows is unavailable.

---

## 6. Real-data validation (both branches attempted)

Computed on `O{n}` / `R_O{n}` for all three imaging runs (`scratchpad/explore_reference.py`).
Representative values (run 1, 150x150; the two 300x400 runs agree and add the weak-reference
cases):

| Order | \|O\| | \|R\| | R class | R SNR | R near-zero | corr(\|O\|,\|R\|) | \|O/R\| mean | phase(O/R) std |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| O0 | 64.1 | 64.1 | noise | 0.00 | 0.0 % | 0.006 | 1.00 | 0.000 |
| O1 | 63.9 | 63.9 | signal | 5.52 | 0.0 % | 0.938 | 1.00 | 0.018 |
| O2 | 6.19 | 6.20 | signal | 8.54 | 0.0 % | **0.968** | **1.00** | **0.023** |
| O3 | 0.535 | 0.535 | signal | 5.35 | 0.0 % | 0.948 | 1.00 | 0.116 |
| O4 | 0.130 | 0.129 | signal | 2.00 | 0.3 % | 0.752 | 1.08 | 0.317 |
| O5 | 0 | 0 | empty | - | - | - | - | - |

**The "recommend" (positive) branch cannot be validated - the references are redundant.**
For every signal-bearing harmonic, `R` is a near-copy of `O`: `corr(|O|,|R|)` is 0.94-0.97,
`|O/R| ~ 1.00`, and the referenced phase spread is tiny (0.02-0.12 rad). This is exactly
synthetic **case C**: dividing by `R` collapses the data to ~1 and **erases the contrast**.
Normalizing this measurement would not improve interpretation; it would destroy it. The
instrument metadata corroborates this: every imaging run is **PsHet, "Measurement Mode:
Self-Reference Off"**, and the `.txt` parameter file defines **no reference material or
reference position**. The discovery doc's early note "`R-` = reference (used for
normalization)" ([`measurement-discovery.md`](measurement-discovery.md)) was an unvalidated
inference (its sibling suffix guesses carry literal question marks); the data does not
support it - whatever the `R-` channels are instrumentally, they are not independent
normalization references here.

**The "decline" branch *is* validated on real data.** In the two longer runs, `R_O4` is a
genuinely poor divisor - `noise`/`weak` class, SNR 0.56-0.67, **~10 % near-zero**, and
`O/R` shows blown-up pixels (~0.8 %) with destroyed phase (`phase(O/R)` std ~1.3 rad). The
engine could correctly decline there on quality grounds alone. `R_O5` is `empty`; `R_O0` is
`noise`. So the decline conditions occur and are detected on real data; the *appropriate*
condition never occurs.

This is the two-sided requirement of the methodology applied honestly: the decline side
fires on real data, the recommend side cannot - the same gap that deferred phase-wrapping,
here on the positive branch.

---

## 7. Decision

**Outcome 2 - DEFERRED.** No deterministic, evidence-based *positive* recommendation
criterion for reference normalization can be justified or validated on present data; do not
implement the evidence-based `ReferenceNormalizeRule` refinement.

Reasoning, by the three statements of §1:

- **Possible** - already true and shipped. Unchanged.
- **Appropriate** - **not deterministically decidable.** Appropriateness requires the
  reference to be a *meaningful, independent common-mode response*, which is an
  experimental-design fact ("R was measured on Au") not encoded in the array. The data can
  *exclude* appropriateness (redundant, weak, noisy, or empty reference - §5/§6) but cannot
  *establish* it (quality + non-redundancy are necessary, not sufficient - §5, case A vs C).
- **Strongly recommended** - **not justified.** It needs the appropriate branch, which is
  unestablished, and a real measurement where normalization demonstrably helps, which does
  not exist in the available data (all "Self-Reference Off", all `O/R ~ 1`).

Per the methodology, *real-data validation must be two-sided*; only the decline branch
validates, so a recommendation rule is deferred (project maxim: a missing rule beats an
unjustified one).

**Secondary finding (flagged, not fixed in this milestone).** The *existing*
`ReferenceNormalizeRule` (`reasoning.normalize_with_reference`, ADR-0023) fires at a flat
confidence of **0.85** whenever references exist and signals are raw - which, on **every**
available real measurement, recommends an operation that would erase the contrast (`O/R ~
1`), and on weak harmonics would inject noise. That rule was shipped as a "standard-practice
prior" *before* this validation study; the study now shows the prior is **not supported by
the available evidence**. Correcting it is a code change and so is out of scope for a DEFER
outcome (and the brief forbids reasoning-engine redesign here), but it is the **top Future
Work item** (§9) and is flagged in `NEXT.md`: the honest near-term options are to **gate the
rule conservatively** (decline on redundant/weak/empty references - a defensible
decline-only refinement, validated above) or to **withdraw the positive recommendation**
until a genuinely-referenced measurement exists.

---

## 8. Honest limitations

1. **The core obstacle is metadata, not math.** Whether a reference is *meaningful* is an
   experimental-design fact. No deterministic computation over a single measurement can
   recover it; quality and redundancy are surrogates that only support *declining*.
2. **One sample family, one mode.** All available real data is CdO, PsHet, "Self-Reference
   Off", with redundant `R-` channels. A genuinely-referenced acquisition (a reference on a
   known substrate, or referenced-mode data) is required to exercise the positive branch -
   and to confirm that "non-redundant + high-quality" actually predicts benefit.
3. **The `R-` channels' instrumental meaning is unconfirmed.** The data is consistent with
   a retrace/duplicate rather than an independent reference, but the parameter file does not
   say. The analysis relies only on the deterministic facts (`O/R ~ 1`, quality, near-zero),
   not on an assumed instrument behavior.
4. **Redundancy detection has its own edge.** `corr(|O|,|R|) ~ 1` with `CV(|O/R|) ~ 0` is a
   strong "redundant" signal, but a *genuine* reference that happens to be spatially similar
   to the sample (rare) could read as partly redundant; this is a decline-side
   false-positive risk, acceptable for a conservative gate but noted.
5. **No fact is shipped either.** Unlike harmonic ranking (where the diagnostic fact stood
   on its own), a *reference-quality* fact in isolation is misleading for this purpose
   (high quality != appropriate, §5). So this milestone ships neither a rule nor a
   diagnostic - only the recorded analysis.

---

## 9. Future work

In priority order:

1. **Reconsider the existing flat-0.85 rule (the immediate honesty fix).** Open a focused
   follow-up to either (a) **gate it**: decline (or down-weight to tentative) when the
   reference is redundant (`corr(|O|,|R|)` high / `CV(|O/R|)` ~ 0), weak/noise/empty class,
   or has a high near-zero fraction - all validated decline conditions here; or (b)
   **withdraw the positive recommendation** pending real validation. Either is a small,
   evidence-backed change; (a) would make the rule behave correctly on all currently
   testable cases (it would *decline* on the CdO data, which is the right answer).
2. **Obtain a genuinely-referenced golden measurement** - a reference on a known substrate,
   or a "Self-Reference On" / referenced-mode acquisition - to validate the *positive*
   branch and confirm that "non-redundant + high-quality reference" predicts a beneficial
   normalization. Only then can a positive rule be registered.
3. **If (2) arrives:** ship, first, the deterministic facts (reference-quality via the
   ADR-0026 primitive applied to `R_O{n}`, plus the redundancy metric), with known-answer
   tests; then a confidence-graded `ReasoningRule` that *recommends* only on non-redundant,
   high-quality references and *declines* otherwise - validated on both branches.
4. **Consider recording reference identity in metadata** (what `R-` was measured on) at
   import, if the vendor files expose it; that, not array statistics, is the true signal of
   appropriateness.

---

## References

- F. Keilmann, R. Hillenbrand, "Near-field microscopy by elastic light scattering from a
  tip," *Phil. Trans. R. Soc. Lond. A* **362**, 787-805 (2004). (s-SNOM amplitude/phase;
  reference normalization context.)
- N. Ocelic, A. Huber, R. Hillenbrand, "Pseudoheterodyne detection for background-free
  near-field spectroscopy," *Appl. Phys. Lett.* **89**, 101124 (2006). (PsHet; what the
  measurement already provides before normalization.)
- A. Huth et al., "Nano-FTIR Absorption Spectroscopy of Molecular Fingerprints at 20 nm
  Spatial Resolution," *Nano Lett.* **12**, 3973 (2012). (Reference normalization in
  nano-FTIR practice.)
- J. Immerkaer, "Fast Noise Variance Estimation," *Comput. Vis. Image Underst.* **64**, 300
  (1996). (The single-image noise floor reused for reference quality; ADR-0026.)
- See also [`harmonic-ranking-analysis.md`](harmonic-ranking-analysis.md) (the reused
  primitive), [`phase-wrapping-analysis.md`](phase-wrapping-analysis.md) (the Outcome-2
  precedent), and [`scientific-reasoning.md`](scientific-reasoning.md) (the rule this study
  evaluated).
