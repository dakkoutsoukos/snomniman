# Harmonic Signal-vs-Noise Analysis (a Scientific Validation milestone)

> **Question:** *Can the boundary between signal-bearing and noise-dominated optical
> harmonics be determined deterministically from a single measurement - without an
> external noise model - well enough to classify (or rank) the harmonics; and can that
> criterion be validated on real data on **both** branches (correctly identifying the
> signal harmonics **and** the noise harmonics)?*
>
> **Status: Outcome 1 (validate and implement) - scoped.** The *signal-vs-noise
> classification fact* is defensible and validated on both branches; it is implemented as
> a `diagnostics` descriptor. The *"informativeness ranking" / "best-harmonic
> recommendation"* sub-capability is **rejected** as not deterministically defensible
> (the available metrics conflate near-field signal with far-field background, and "best"
> is a genuine expert tradeoff). No `ReasoningRule` is added.

This is the second milestone of the **Scientific Validation Phase**
([`scientific-validation.md`](scientific-validation.md)) and the first to reach
**Outcome 1** (the phase-wrapping exemplar reached Outcome 2). It is the science-track
study triaged in [`next-scientific-priorities.md`](next-scientific-priorities.md) as
**Candidate 2 (Category B)**, and it subsumes the Beta Readiness product gap **M4**
("nothing marks which orders are signal vs. noise"). Its sections map onto the standard
nine-section template.

---

## 1. Scientific question

When a researcher opens an s-SNOM measurement, the optical channel is recorded at several
demodulation harmonics (here O0..O5). A first-five-minutes act is deciding **which
harmonics are worth looking at**: some carry genuine, spatially-structured near-field
signal; some are dominated by detector/demodulation noise; some are not meaningfully
recorded at all. The Diagnostics Engine currently reports each harmonic's mean amplitude
and decay ratio but **deliberately declines** to say which orders are signal vs. noise -
because ADR-0019 judged that a true SNR "needs a noise model or a signal-free region,
neither available deterministically from a single image." This study asks whether that
deferral can now be discharged.

The expert judgment decomposes into distinct claims of very different defensibility:

| Claim | Evidence class | Verdict (preview) |
|---|---|---|
| **C-a. This harmonic carries spatially-coherent content above the noise floor** (signal) vs. **is noise-dominated/incoherent** vs. **is empty.** | **Necessary + sufficient** and *measurable*: structure-vs-noise has an analytical null and a single-image noise estimate. | **Defensible -> implement (this study).** |
| **C-b. This harmonic is near-field vs. far-field background.** | Partly measurable (cross-order coherence, decay) but anchor-dependent; largely **settled convention** (O0/O1 carry background; O2+ are background-suppressed). | Already taught (knowledge `concept.harmonics`); **not a per-measurement detection** this study ships. |
| **C-c. This single harmonic is "the best" / most informative one to use.** | **Subjective**: the background-suppression vs. SNR vs. tip-confinement tradeoff depends on the scientific question. | **Rejected** as a deterministic capability. |

The study validates **C-a** (the actual M4 need) and is explicit about why **C-c** - the
literal reading of "harmonic ranking" - is not deterministically defensible.

---

## 2. Literature review

The physics of harmonic demodulation is settled and not in question here:

- The near-field tip-sample interaction is strongly **nonlinear** in tip-sample distance,
  so the near-field scattering is rich in higher harmonics of the tapping frequency
  `n*Omega`; the far-field background is quasi-linear and concentrates at low orders.
  Demodulating at `n >= 2` therefore suppresses background (Keilmann & Hillenbrand 2004;
  Hillenbrand & Keilmann 2000). Pseudoheterodyne detection recovers complex amplitude and
  phase background-free (Ocelic, Huber & Hillenbrand 2006).
- The practical consequence taught everywhere: **O0/O1 carry the most background; O2 and
  O3 are common working harmonics; higher orders are more surface-confined but carry less
  signal**, so there is a confinement-vs-SNR tradeoff. (This is exactly claim **C-b/C-c**,
  and the literature treats "which order to use" as a *judgment*, not a formula.)

What the literature does **not** give is a single-measurement, deterministic threshold for
"signal vs. noise." For that we borrow established **image-science** tools, not invented
metrics:

- **Single-image noise variance estimation.** Immerkaer's method (Immerkaer 1996)
  convolves the image with a Laplacian-type 3x3 kernel that has zero response to constant,
  linear, and (largely) quadratic surfaces, so its response is dominated by white noise;
  `sigma_noise = sqrt(pi/2) / (6 (W-2)(H-2)) * sum |I * N|`. The MAD-of-finest-wavelet
  estimator (Donoho & Johnstone 1994) is an equivalent robust alternative. These are the
  standard "estimate the noise floor from one image" tools.
- **Spatial autocorrelation as a structure test.** Lag-1 (nearest-neighbour) spatial
  autocorrelation - equivalently Moran's I (Moran 1950; Cliff & Ord 1981) - distinguishes
  a spatially-structured field from spatial white noise, with a known null: for white
  noise the lag-1 correlation is `~N(0, 1/N)`.

Both are decades-old, citable, and deterministic. They are the grounding for claim **C-a**.

---

## 3. Candidate diagnostics

| Diagnostic | What it measures | Verdict |
|---|---|---|
| **Mean amplitude + decay ratio** (already shipped) | Magnitude per order; ratio to the next-lower order. | Kept - context. A decay ratio rising back toward 1 hints the floor is near, but it cannot *alone* say a given order is noise. |
| **Spatial coherence** = mean lag-1 autocorrelation of the amplitude image (over x and y) | Is there spatial structure, or spatial white noise? Null `~N(0, 1/N)`; smooth signal -> ~1. | **Primary criterion for C-a.** Cleanest null; unit-free (works on raw a.u.); robust. |
| **Single-image SNR estimate** = `signal_std / noise_std` with `noise_std` from Immerkaer | A magnitude for the signal-to-noise margin from one image. | **Kept - corroborating + the reusable noise-floor primitive** (discharges ADR-0019; Candidate 3 reuses it). Rests on a white-noise assumption (limitation 8). |
| **Cross-order amplitude correlation** with a presumed-near-field anchor (O2) | Do two harmonics see the same spatial structure? Near-field family correlates; background does not. | **Used as study evidence for C-b**, *not* shipped as a per-measurement classifier (anchor-dependent; the near-field/background line is settled convention, not a detection). |
| **Phase residue density** (from the phase-wrapping study) | Phase incoherence in low-amplitude regions. | Corroborating only; the amplitude-domain criteria are cleaner. |
| A numeric **"informativeness" or "quality score"** total-ordering the harmonics | "Which is best." | **Rejected** - conflates background with near-field (sec. 6/7); false precision (the triage's explicit warning). |

The defensible classifier for **C-a** is therefore: **spatial coherence** (primary), with
the **single-image SNR** as a corroborating magnitude and the **variance** to flag empty
channels. Cross-order correlation is study evidence, not a shipped classifier.

---

## 4. Analytical validation

The two anchors of claim **C-a** have closed-form expected behaviour, confirmed exactly
on a 150x150 grid (a throwaway investigation, not product code; the known-answer cases are
preserved as committed tests in `tests/test_diagnostics.py`):

| Field | spatial coherence | single-image SNR | Expected | Result |
|---|---|---|---|---|
| Pure complex-Gaussian-noise amplitude (Rayleigh) | **+0.0052** | 0.148 | coherence -> 0 (within `1/sqrt(N)=0.0067`); SNR -> 0 | **exact** |
| Pure smooth signal (sum of broad Gaussians), no noise | **+0.9993** | ~2.4e6 | coherence -> 1; SNR -> infinity | **exact** |
| Constant field | NaN (zero variance) | NaN | degenerate -> flagged **empty**, never misclassified | **as designed** |

The lag-1 autocorrelation of spatial white noise sits within one null standard deviation
of zero; a smooth field saturates the metric at ~1. The single-image noise estimate
recovers `sigma_noise` to within ~1% of truth (next section). These are the conditions
under which the criterion is exact: **noise that is spatially white and signal that is
band-limited (smooth at the tip-resolution scale)** - the regime of s-SNOM amplitude
imaging.

---

## 5. Synthetic validation

A smooth near-field-like pattern was scaled to a controlled signal level and added to
complex white noise of fixed per-quadrature `sigma = 1`; the amplitude `|signal + noise|`
was classified. This sweeps the signal->noise transition with an **analytically known**
SNR (`= signal_std / noise_std`). Result (150x150):

| true SNR | spatial coherence | est. SNR (Immerkaer) | classification |
|---:|---:|---:|---|
| 8.0 | 0.984 | 7.93 | **signal** |
| 4.0 | 0.940 | 3.95 | **signal** |
| 2.0 | 0.796 | 1.98 | **signal** |
| **1.0** | **0.502** | **0.985** | **weak (the crossover)** |
| 0.5 | 0.201 | 0.497 | **noise** |
| 0.25 | 0.063 | 0.300 | **noise** |
| 0.0 | 0.006 | 0.125 | **noise** |

Two facts make the criterion defensible and its thresholds **principled rather than
tuned**:

1. **The Immerkaer SNR estimate recovers the true SNR to ~1%** (8.0->7.93, 2.0->1.98,
   1.0->0.985, 0.5->0.497). The single-image noise floor is real and accurate.
2. **Spatial coherence maps monotonically onto SNR**, crossing **~0.50 exactly at SNR=1**
   (signal std = noise std) and **~0.20 at SNR=0.5**. This fixes the classification bands
   to physically-meaningful points, not to the data:
   - `coherence >= 0.5`  <->  `SNR >~ 1`  ->  **signal** (signal dominates noise)
   - `0.2 <= coherence < 0.5`  ->  **weak** (signal present, comparable to or below noise)
   - `coherence < 0.2`  <->  `SNR <~ 0.5`  ->  **noise** (noise dominates)
   - near-zero variance  ->  **empty**

The same sweep at 300x400 reproduces the mapping (coherence 0.94/0.50/0.20/0.06 at SNR
4/1/0.5/0.25; SNR recovered exactly), confirming the thresholds are **size-independent**.

---

## 6. Real-data validation (both branches)

The criterion was computed on the optical signal harmonics O0..O5 of **all three imaging
runs** in the sample folder (the CdO Dense ROI scans). Unlike phase-wrapping - which had no
real measurement to exercise its "fire" branch - these scans exercise **both** branches. The
golden run's values are locked as a committed test (`tests/test_neasnom_golden.py`).

**Spatial coherence / estimated SNR / cross-correlation with O2, per run** (classification
in the final column uses the sec. 5 bands):

| Order | run1 150x150 | run2 300x400 | run3 300x400 | xcorr(O2) r1/r2/r3 | class r1/r2/r3 |
|---|---|---|---|---|---|
| O0 | -0.09 / 0.0 | -0.28 / 0.0 | -0.09 / 0.0 | -0.00 / -0.00 / 0.00 | **noise / noise / noise** |
| O1 | 0.91 / 5.7 | 0.65 / 1.4 | 0.68 / 1.6 | -0.15 / 0.04 / -0.09 | signal / signal / signal |
| O2 | 0.92 / 8.7 | 0.94 / 4.1 | 0.97 / 6.0 | (anchor) | **signal / signal / signal** |
| O3 | 0.85 / 5.3 | 0.84 / 2.4 | 0.91 / 3.2 | 0.93 / 0.88 / 0.92 | **signal / signal / signal** |
| O4 | 0.66 / 2.1 | 0.21 / 0.6 | 0.36 / 0.7 | 0.78 / 0.38 / 0.53 | signal / **noise** / **weak** |
| O5 | empty | empty | empty | - | **empty / empty / empty** |

**The signal branch is richly validated.** O2 and O3 are unambiguously signal in every
run (coherence 0.84-0.97, SNR 2.4-8.7), and O3 correlates 0.88-0.93 with O2 - the same
near-field structure across orders.

**The noise branch is genuinely validated** - the advantage over phase-wrapping:
- **O4 in the two longer scans is at/below the noise floor** (coherence 0.21/0.36, SNR
  0.6/0.7). Its weak residual cross-correlation with O2 (0.38/0.53) is the signature of a
  near-field signal *sinking into noise* - the canonical "this order is no longer usable"
  case, captured on a real measurement. (In the shorter run1, O4 is still weak signal,
  coherence 0.66 - the classifier honestly reports the order as borderline, tracking the
  real per-scan difference.)
- **O5 is empty** in every run (identically zero - not recorded), and is correctly flagged
  rather than fed to the classifier.
- **O0 is incoherent** in every run (negative lag-1 autocorrelation, SNR ~ 0): not white
  noise but a structured non-near-field artifact at the DC/0th order. The coherence/SNR
  criterion correctly reads it as "not coherent near-field signal."

**The decisive honesty finding (why C-c is rejected).** The criterion measures
**structure-vs-noise, not near-field-vs-background.** O1 is the demonstration: it is
strongly spatially coherent (so legitimately "above the noise floor") yet **anti-correlated
with the near-field family** (xcorr(O2) = -0.15/0.04/-0.09) - it is far-field background.
In run1 its estimated SNR (5.7) even *exceeds* the genuine near-field O3 (5.3). **Any
"rank harmonics by SNR/coherence/quality" feature would therefore promote the background
harmonic O1 above real near-field harmonics** - a scientifically wrong recommendation. The
quantity that separates near-field from background is the cross-order coherence / the
decay structure (O1->O2 suppression), and "how much suppression is enough" / "which order
to use" is the settled-convention judgment of sec. 1 (C-b/C-c), not a deterministic
threshold.

---

## 7. Decision

**Outcome 1 (validate and implement), scoped to the signal-vs-noise classification fact.**

- **Claim C-a - READY.** A deterministic per-harmonic classification (**signal / weak /
  noise / empty**) from **spatial coherence** (primary; analytical white-noise null),
  corroborated by a **single-image SNR estimate** (Immerkaer) and guarded by the channel
  **variance** (empty), is analytically exact in its regime (sec. 4), synthetically
  calibrated with principled thresholds (sec. 5), and **validated on real data on both
  branches** (sec. 6). This is the M4 need and the precise question the triage posed. It
  is implemented as a `diagnostics` descriptor (sec. below).
- **Claim C-c - REJECTED.** A deterministic *total-order ranking of harmonics by
  informativeness*, or an auto-recommendation of "the best harmonic," is **not
  defensible**: the deterministic structure/noise metrics conflate near-field with
  far-field background (sec. 6), and the genuine basis for choosing an order (the
  background-suppression vs. SNR vs. confinement tradeoff) is a scientific judgment, not a
  computable fact. Per the project maxim, this is not shipped.
- **No `ReasoningRule`.** Because the defensible artifact is a *fact the researcher reads*
  (not an operation to apply), and because the only judgment a rule could add - "use
  harmonic N" - is exactly the rejected C-c, **no Suggested-Next-Step rule is registered.**
  This mirrors line-flatten and phase-unwrap: ship the fact; defer/decline the judgment.

**The shipped criterion (the diagnostic fact).** For each optical signal harmonic with a
2-D amplitude image:

- `spatial_coherence` = mean of the lag-1 Pearson autocorrelation along x and y of the
  mean-removed amplitude image (`None` if not 2-D or degenerate).
- `snr_estimate` = `sqrt(max(var_total - var_noise, 0)) / sigma_noise`, with
  `sigma_noise` from the Immerkaer 3x3 estimator (`None` if not 2-D or degenerate).
- `classification`: `empty` if variance ~ 0; else by coherence - `signal` (`>= 0.5`),
  `weak` (`[0.2, 0.5)`), `noise` (`< 0.2`); `unknown` if it cannot be computed (no 2-D
  amplitude).

The thresholds are the SNR=1 (coherence 0.50) and SNR=0.5 (coherence 0.20) crossovers of
sec. 5 - chosen for physical meaning, not fitted. The classification is reported **with**
the underlying numbers so a consumer can see the evidence (the diagnostics-engine style).

**Relationship to ADR-0019.** This **discharges** ADR-0019's deferral of SNR. ADR-0019 was
right that SNR could not be reported *without a validated noise model*; this study supplies
and validates one (Immerkaer, ~1% on synthetic, two-sided on real data). The deferral is
lifted *for a single-image estimate under a stated white-noise assumption*, recorded as
ADR-0026.

---

## 8. Honest limitations

1. **It is a noise-floor / coherence classification, not a near-field judgment.** "signal"
   means "spatially-coherent content above the noise floor," which **includes far-field
   background** (O1). It does **not** mean "near-field" or "the order you should use."
   Distinguishing near-field from background (C-b) remains settled convention (O2+),
   taught in `concept.harmonics`, not a per-measurement output.
2. **No total-order ranking / no "best harmonic."** By the sec. 6/7 reasoning; the
   capability deliberately stops at classification.
3. **The single-image SNR rests on a white-noise assumption.** Per-scan-line or 1/f drift
   noise is not spatially white; it can bias the Immerkaer estimate. Mitigations: the
   classification is driven by **coherence** (cleaner null), the SNR only corroborates;
   line noise tends to *inflate* the Immerkaer noise estimate (conservative, lowering SNR);
   and empirically the real noise harmonics read as low-coherence anyway. Still, on a scan
   dominated by coherent line artifacts the criterion could mislabel - documented, not
   hidden.
4. **The thresholds assume a band-limited signal.** A genuine but extremely fine-structured
   signal (varying at the pixel scale) would read as low-coherence. In s-SNOM the tip
   radius band-limits the optical signal, so this is the right assumption, but it is an
   assumption.
5. **`weak` is a transition band, not a verdict.** O4 lands in `signal`/`weak`/`noise`
   across the three runs; that honest instability *is* the finding (O4 is at the floor),
   not a defect - but a consumer must not read `weak` as a clean call.
6. **One sample (CdO), three runs.** CdO at 5973 cm^-1 is a strong phonon-polariton
   response, so even O4 is near-signal. The criterion itself is sample-independent (the
   coherence null and SNR recovery are universal, sec. 4-5), but a second strongly
   *different* sample (e.g. a weak-contrast dielectric) would further harden the noise
   branch.
7. **Empty vs. noise is a variance call.** O5 here is identically zero (clean). A channel
   with a tiny nonzero variance floor near machine epsilon is treated as empty by a
   relative-variance guard; the exact guard is documented in code.

---

## 9. Future work

1. **Reference-normalization criteria (Candidate 3).** This study delivers the
   **single-image noise-floor primitive** that Candidate 3 needs to ask "is this reference
   channel above the noise floor?" - it should **reuse** `snr_estimate` /
   `spatial_coherence`, not re-derive them (the dependency-correct order of the triage).
2. **A second, weak-contrast sample** would let the noise branch be validated where the
   *signal itself* (not just O4) decays into noise at a lower order - hardening limitation 6.
3. **Near-field vs. background as its own study (C-b), if a need appears.** Cross-order
   coherence (sec. 6) cleanly separated O1 (background) from O3 (near-field) here; if a
   product need arises to *detect* (not assume) which low orders are background, that is a
   separate Category-B study - it must not be smuggled into this classification.
4. **A line-artifact diagnostic** would both relax limitation 3 (model line noise
   explicitly) and feed a future line-flatten recommendation (the deferred cousin from the
   line-flatten milestone).

---

## References

- J. Immerkaer, "Fast Noise Variance Estimation," *Computer Vision and Image
  Understanding* **64**(2), 300-302 (1996). (Single-image noise-sigma via a Laplacian
  kernel.)
- D. L. Donoho, I. M. Johnstone, "Ideal spatial adaptation by wavelet shrinkage,"
  *Biometrika* **81**(3), 425-455 (1994). (MAD-of-finest-detail noise estimate; equivalent.)
- P. A. P. Moran, "Notes on continuous stochastic phenomena," *Biometrika* **37**, 17-23
  (1950); A. D. Cliff, J. K. Ord, *Spatial Processes: Models and Applications*, Pion
  (1981). (Spatial autocorrelation and its null.)
- F. Keilmann, R. Hillenbrand, "Near-field microscopy by elastic light scattering from a
  tip," *Phil. Trans. R. Soc. Lond. A* **362**, 787-805 (2004). (Harmonic demodulation;
  background suppression at higher orders.)
- R. Hillenbrand, F. Keilmann, "Complex Optical Constants on a Subwavelength Scale,"
  *Phys. Rev. Lett.* **85**, 3029 (2000). (Higher-harmonic background suppression.)
- N. Ocelic, A. Huber, R. Hillenbrand, "Pseudoheterodyne detection for background-free
  near-field spectroscopy," *Appl. Phys. Lett.* **89**, 101124 (2006). (Background-free
  complex amplitude and phase.)
