"""The curated knowledge library - SNOMNIMAN's initial scientific teaching content.

Concise, accurate, interconnected articles, not textbook chapters. Each helps a
researcher understand a measurement or an analysis step. The set is *initial*, not
exhaustive; it is designed to grow (one article per new operation/diagnostic). A
no-drift test asserts every registered ``ProcessingStep`` has an operation article.

Editing guidance: keep articles short and defensible (the project maxim). State only
what is scientifically accurate; leave a field empty rather than pad it. Cross-link
liberally via ``related_*`` (integrity-checked - no dangling links).
"""

from __future__ import annotations

from .article import AI, CONCEPT, DIAGNOSTIC, OPERATION, Article

# Common references (kept short; cited where directly relevant).
_KEILMANN = "Keilmann & Hillenbrand, Phil. Trans. R. Soc. A 362, 787 (2004) - s-SNOM review."
_OCELIC = "Ocelic, Huber & Hillenbrand, Appl. Phys. Lett. 89, 101124 (2006) - PsHet detection."
_HUTH = "Huth et al., Nano Lett. 12, 3973 (2012) - nano-FTIR."
_GHIGLIA = "Ghiglia & Pritt, Two-Dimensional Phase Unwrapping, Wiley (1998)."
_GWYDDION = "Necas & Klapetek, Cent. Eur. J. Phys. 10, 181 (2012) - Gwyddion SPM analysis."
_WSXM = "Horcas et al., Rev. Sci. Instrum. 78, 013705 (2007) - WSxM SPM software."
_IMMERKAER = "Immerkaer, Comput. Vis. Image Underst. 64, 300 (1996) - single-image noise sigma."
_MORAN = "Moran, Biometrika 37, 17 (1950); Cliff & Ord, Spatial Processes (1981)."


# --------------------------------------------------------------------------- #
# Core concepts
# --------------------------------------------------------------------------- #

_CONCEPTS = (
    Article(
        article_id="concept.near_field_microscopy",
        category=CONCEPT,
        title="Scattering-type near-field microscopy (s-SNOM)",
        summary=(
            "An AFM tip illuminated by a focused laser acts as an optical antenna, "
            "concentrating light to a nanoscale spot at its apex; the scattered light "
            "carries the local optical response of the sample far below the diffraction limit."
        ),
        explanation=(
            "In s-SNOM the spatial resolution is set by the tip apex radius (tens of nm), "
            "not by the wavelength. The tip is tapped above the surface; the optical "
            "near-field interaction between tip and sample modulates the scattered light. "
            "Detecting amplitude and phase of that scattered light maps the sample's local "
            "dielectric response (e.g. mid-IR vibrational fingerprints, plasmon/polariton "
            "fields) with nanometre resolution."
        ),
        scientific_background=(
            "The tip-sample system is modelled as a polarizable dipole (or finite-dipole) "
            "whose effective polarizability depends on the sample permittivity. Because the "
            "near-field coupling falls off steeply with tip-sample distance, the signal is "
            "strongly nonlinear in the tapping motion - which is what makes background "
            "suppression by harmonic demodulation possible."
        ),
        related_concepts=("concept.harmonics", "concept.complex_signals", "concept.topography"),
        references=(_KEILMANN,),
    ),
    Article(
        article_id="concept.harmonics",
        category=CONCEPT,
        title="Demodulation harmonics (O0, O1, O2, ...)",
        summary=(
            "The tip taps at frequency Omega; demodulating the detector signal at integer "
            "multiples n*Omega isolates the near-field contribution. Higher harmonics are "
            "more strongly background-suppressed and surface-confined."
        ),
        explanation=(
            "The near-field signal is a strongly nonlinear function of tip-sample distance, "
            "so it is rich in higher harmonics of the tapping frequency; the far-field "
            "background is almost linear and concentrates at low orders. Demodulating at "
            "n>=2 (O2, O3, ...) therefore rejects background. Higher orders are more "
            "confined to the apex (higher resolution) but have lower signal, so there is a "
            "practical trade-off; O2 and O3 are common working harmonics."
        ),
        practical_guidance=(
            "Compare harmonics to judge confinement and background: a feature that persists "
            "and sharpens from O1 -> O2 -> O3 is genuine near-field contrast; one that fades "
            "is likely background. Use the harmonic decay diagnostic and the contact sheet."
        ),
        common_mistakes=(
            "Trusting O0/O1 as near-field signal - they carry the most far-field background.",
            "Reading higher-harmonic noise as structure when the signal has decayed into noise.",
        ),
        related_concepts=("concept.near_field_microscopy", "concept.pseudoheterodyne"),
        related_diagnostics=("harmonic_decay", "harmonic_signal_noise"),
        references=(_KEILMANN,),
    ),
    Article(
        article_id="concept.pseudoheterodyne",
        category=CONCEPT,
        title="Pseudoheterodyne detection (PsHet)",
        summary=(
            "An interferometric detection scheme that recovers near-field amplitude and "
            "phase simultaneously and background-free by modulating a reference mirror and "
            "demodulating at sidebands of the tapping harmonics."
        ),
        explanation=(
            "A reference beam with a sinusoidally oscillating phase is combined with the "
            "tip-scattered light. Demodulating each tapping harmonic at the reference "
            "modulation sidebands yields two quadratures, from which amplitude A_n and phase "
            "phi_n are extracted free of the multiplicative and additive far-field "
            "background. This is why s-SNOM channels are complex-valued."
        ),
        mathematical_background=(
            "The detected sidebands give in-phase and quadrature components; "
            "A_n = sqrt(I^2 + Q^2) and phi_n = atan2(Q, I) reconstruct the complex "
            "near-field signal s_n = A_n * exp(i*phi_n)."
        ),
        related_concepts=(
            "concept.complex_signals",
            "concept.phase",
            "concept.harmonics",
        ),
        references=(_OCELIC,),
    ),
    Article(
        article_id="concept.complex_signals",
        category=CONCEPT,
        title="Complex optical channels",
        summary=(
            "Each near-field optical channel O{n} is complex-valued: it stores amplitude and "
            "phase together as a single complex number, not two unrelated images."
        ),
        explanation=(
            "SNOMNIMAN keeps O{n} (and mechanical M{n}) as complex arrays s = A*exp(i*phi). "
            "Amplitude |s| and phase arg(s) are *views* of the same quantity, so they stay "
            "consistent. This matters because amplitude and phase carry different physics "
            "(roughly, scattering strength vs. optical phase shift / absorption) and many "
            "operations act on the complex value as a whole (e.g. reference normalization is "
            "complex division)."
        ),
        related_concepts=("concept.phase", "concept.pseudoheterodyne"),
        related_operations=("image.reference_normalize", "image.phase_unwrap"),
        related_diagnostics=("dynamic_range",),
    ),
    Article(
        article_id="concept.phase",
        category=CONCEPT,
        title="Optical phase",
        summary=(
            "The phase phi_n = arg(O{n}) is the optical phase of the near-field response. In "
            "nano-FTIR it relates closely to molecular absorption; it is a relative, wrapped "
            "quantity, recorded exactly as measured."
        ),
        explanation=(
            "Phase encodes the optical phase shift imparted by the local sample response; "
            "across a vibrational resonance it tracks absorption (in nano-FTIR, Im of the "
            "response). It is always *relative* to a reference and is recorded wrapped into "
            "(-pi, pi]. SNOMNIMAN never inverts, re-references, or unwraps phase silently "
            "(convention OHD-6D): any such change is an explicit, recorded operation."
        ),
        common_mistakes=(
            "Treating phase as absolute - it is referenced; normalization re-references it.",
            "Unwrapping phase that does not actually wrap, or that is noise (see the analysis).",
        ),
        related_concepts=("concept.complex_signals", "concept.immutable_measurements"),
        related_operations=("image.phase_unwrap", "image.reference_normalize"),
        references=(_HUTH,),
    ),
    Article(
        article_id="concept.topography",
        category=CONCEPT,
        title="Topography (Z) and mechanical channels",
        summary=(
            "The AFM records sample height (Z) simultaneously with the optical signal, plus "
            "mechanical channels M{n} (cantilever motion). Topography provides structural "
            "context for the optical contrast."
        ),
        explanation=(
            "Because optical and topographic data are acquired together, you can ask whether "
            "optical contrast follows edges/height (a possible artifact) or is independent "
            "(more likely intrinsic material contrast). Z is a real-valued height map; "
            "mechanical channels M{n} are demodulated like the optical ones and are useful "
            "for diagnosing the tapping/feedback rather than optical material properties."
        ),
        related_concepts=("concept.near_field_microscopy",),
        related_operations=("image.plane_level", "image.line_flatten"),
        related_diagnostics=("topography_slope", "rms_roughness"),
    ),
    Article(
        article_id="concept.immutable_measurements",
        category=CONCEPT,
        title="The immutable measurement",
        summary=(
            "The raw measurement is never modified. Every result is a new, recorded "
            "derivation of it - the central mental model of SNOMNIMAN."
        ),
        explanation=(
            "Operations never overwrite data; they return new datasets. The original raw "
            "import is always reachable. This makes results reproducible and auditable: you "
            "can always trace a figure back to the exact measurement and the exact steps "
            "that produced it, and you can never silently lose the ground truth."
        ),
        related_concepts=("concept.provenance",),
        references=(),
    ),
    Article(
        article_id="concept.provenance",
        category=CONCEPT,
        title="Provenance (the derivation graph)",
        summary=(
            "Every dataset records where it came from and what was done to it, as a directed "
            "graph of operations, parameters, inputs, and software versions."
        ),
        explanation=(
            "A raw import is one node; each operation adds a node referencing its inputs and "
            "recording the step, its parameters, and the software/operation versions. The "
            "result is a complete, replayable history: 'reproduce this from the raw data and "
            "the recorded steps'. Metadata edits are themselves recorded steps - nothing "
            "changes silently."
        ),
        related_concepts=("concept.immutable_measurements",),
    ),
)


# --------------------------------------------------------------------------- #
# Processing operations (one per registered ProcessingStep)
# --------------------------------------------------------------------------- #

_OPERATIONS = (
    Article(
        article_id="operation.image.plane_level",
        category=OPERATION,
        title="Plane Level",
        summary=(
            "Subtracts a fitted polynomial surface (order 1 = a plane) from a real-valued "
            "channel, removing global tilt or bow so true height features stand out."
        ),
        explanation=(
            "Topography often carries a global tilt (sample not perfectly level) or a gentle "
            "bow. Plane leveling fits a low-order polynomial surface by least squares and "
            "subtracts it, flattening the background. It acts on a real channel (usually Z) "
            "and leaves all other channels unchanged."
        ),
        mathematical_background=(
            "Ordinary least-squares fit of a polynomial surface z_fit(x,y) (order 1: a+bx+cy; "
            "order 2: + dx^2+exy+fy^2; ...), then z -> z - z_fit."
        ),
        practical_guidance=(
            "Use order 1 to remove instrument tilt - the safe default. Use it when the "
            "topography slope is a large fraction of the height variation (see the plane-slope "
            "diagnostic). Avoid high orders unless you understand the sample's true curvature."
        ),
        common_mistakes=(
            "High polynomial orders can subtract genuine sample curvature, not just tilt.",
            "Leveling a channel that has no meaningful tilt, hiding real large-scale structure.",
            "Expecting it to remove per-scan-line striping - that is line flattening's job.",
        ),
        related_concepts=("concept.topography",),
        related_operations=("image.line_flatten",),
        related_diagnostics=("topography_slope", "rms_roughness"),
    ),
    Article(
        article_id="operation.image.line_flatten",
        category=OPERATION,
        title="Line Flatten",
        summary=(
            "Removes per-scan-line baseline offsets (horizontal striping) by subtracting a "
            "median, mean, or low-order polynomial from each scan line independently."
        ),
        explanation=(
            "Raster topography is acquired one line at a time, so drift, feedback settling, "
            "and tip changes give successive lines slightly different baselines - seen as "
            "horizontal stripes. Line flattening estimates and subtracts a baseline for each "
            "scan line separately (a row of constant y along the fast scan axis x), removing "
            "line-to-line offsets that a single global surface fit cannot. It acts on a real "
            "channel (usually Z) and leaves all other channels unchanged."
        ),
        scientific_background=(
            "Median / mean / low-order-polynomial row leveling is the standard, deterministic "
            "baseline-removal family in SPM analysis tools (Gwyddion 'Align Rows'; WSxM). The "
            "median is the robust default: it ignores a few bright or dark feature pixels, so "
            "genuine features in a line do not bias that line's correction."
        ),
        mathematical_background=(
            "For each scan line L_i: median subtracts median(L_i); mean subtracts the line "
            "mean; polynomial fits p(x) of degree d along the line by least squares and "
            "subtracts it (removing per-line offset and slope/bow). Non-finite pixels are "
            "ignored when estimating the baseline; an all-invalid line is left unchanged."
        ),
        practical_guidance=(
            "Use it when topography shows horizontal striping that plane leveling leaves "
            "behind. Start with the median method (robust); use polynomial order 1 when each "
            "line also carries a slope. A common workflow is to line-flatten to remove "
            "striping, then plane-level to remove global tilt."
        ),
        common_mistakes=(
            "Using the mean method when strong features are present - they bias each line's "
            "correction; prefer the robust median.",
            "Over-flattening: a real feature spanning many lines can be partly removed, "
            "leaving faint vertical banding (the classic row-leveling trade-off).",
            "Expecting it to remove global tilt or bow - that is plane leveling; the two are "
            "complementary, not interchangeable.",
        ),
        related_concepts=("concept.topography",),
        related_operations=("image.plane_level",),
        related_diagnostics=("rms_roughness",),
        references=(_GWYDDION, _WSXM),
    ),
    Article(
        article_id="operation.image.reference_normalize",
        category=OPERATION,
        title="Reference Normalize",
        summary=(
            "Divides each complex optical channel by its matching reference channel "
            "(O{n}/R_O{n}), removing the common system response so harmonics can be compared "
            "quantitatively."
        ),
        explanation=(
            "A reference (e.g. on a known substrate) carries the instrument and illumination "
            "response common to all measurements. Dividing the signal by the reference (a "
            "complex division) cancels that common factor: amplitude becomes a dimensionless "
            "ratio and phase becomes referenced to the reference. This is standard practice "
            "before quantitative amplitude/phase comparison."
        ),
        mathematical_background=(
            "Per harmonic: O{n}_norm = O{n} / R_O{n}. Amplitude |O|/|R|; phase arg(O) - arg(R)."
        ),
        practical_guidance=(
            "Apply it deliberately when you have a genuine, independent reference (e.g. "
            "measured on a known substrate) that shares the instrument/illumination response. "
            "SNOMNIMAN does NOT auto-recommend it: whether a reference is meaningful is an "
            "experimental-design fact the measurement does not encode (Scientific Validation "
            "Outcome 2). Avoid it when the reference is weak, noisy, or a near-copy of the "
            "signal."
        ),
        common_mistakes=(
            "Where the reference amplitude is near zero, division amplifies noise.",
            "Forgetting that phase is now reference-relative, not absolute.",
            "Normalizing by a reference that is a near-copy of the signal (e.g. a retrace, or "
            "a 'Self-Reference Off' acquisition) yields O/R ~ 1 and erases contrast rather "
            "than revealing it.",
        ),
        related_concepts=("concept.complex_signals", "concept.phase"),
    ),
    Article(
        article_id="operation.image.phase_unwrap",
        category=OPERATION,
        title="Phase Unwrap",
        summary=(
            "Produces a new continuous-phase channel from a complex channel by removing 2*pi "
            "jumps. Only appropriate when the phase genuinely wraps and is not just noise."
        ),
        explanation=(
            "Wrapped phase lives in (-pi, pi]; if the true phase spans more than 2*pi it "
            "shows artificial jumps at the branch cut. Unwrapping adds/subtracts 2*pi to "
            "restore continuity, producing a new real channel (the raw phase is untouched). "
            "SNOMNIMAN uses sequential 1-D unwrapping, which is exact only when the field is "
            "free of phase residues (path-independent)."
        ),
        mathematical_background=(
            "phi = psi + 2*pi*k(x,y). The 1-D method integrates wrapped differences along x "
            "then y; it is exact iff the wrapped field has zero residues (Goldstein/Ghiglia-Pritt)."
        ),
        practical_guidance=(
            "Only unwrap phase that actually wraps. Single-harmonic s-SNOM optical phase is "
            "often bounded and needs no unwrapping; nano-FTIR / interferometric phase may. "
            "Restrict attention to amplitude-significant regions - phase is noise where "
            "amplitude is near zero. See docs/phase-wrapping-analysis.md."
        ),
        common_mistakes=(
            "Unwrapping noise or bounded phase, which manufactures meaningless ramps.",
            "Unwrapping a field with phase singularities/vortices, where the 1-D method streaks.",
        ),
        related_concepts=("concept.phase", "concept.complex_signals"),
        references=(_GHIGLIA,),
    ),
    Article(
        article_id="operation.image.crop",
        category=OPERATION,
        title="Crop",
        summary=(
            "Restricts every channel to a rectangular region given in nanometres, preserving "
            "absolute coordinates and updating the scan geometry."
        ),
        explanation=(
            "Cropping focuses analysis on a sub-region (e.g. a single feature) and reduces "
            "data size. Coordinates are sliced, not re-based, so absolute positions are "
            "preserved and the cropped dataset still relates correctly to the original."
        ),
        practical_guidance=(
            "Driven by your scientific intent (which region matters) - there is no automatic "
            "recommendation for it. Use it before measurement/statistics to isolate a feature."
        ),
        related_concepts=("concept.immutable_measurements",),
    ),
)


# --------------------------------------------------------------------------- #
# Diagnostics
# --------------------------------------------------------------------------- #

_DIAGNOSTICS = (
    Article(
        article_id="diagnostic.topography_slope",
        category=DIAGNOSTIC,
        title="Plane slope (topography tilt)",
        summary=(
            "The gradient of a least-squares plane fitted to the topography, reported per "
            "micrometre - how tilted the surface is overall."
        ),
        explanation=(
            "A plane a + b*x + c*y is fitted to the height by least squares; the slope "
            "magnitude sqrt(b^2 + c^2) (scaled to per-micrometre) quantifies global tilt. A "
            "large tilt relative to the surface roughness suggests plane leveling will help."
        ),
        practical_guidance=(
            "Compare the tilt's height swing across the field to the roughness: if tilt "
            "dominates, level it (order 1)."
        ),
        related_operations=("image.plane_level",),
        related_concepts=("concept.topography",),
    ),
    Article(
        article_id="diagnostic.rms_roughness",
        category=DIAGNOSTIC,
        title="RMS roughness (detilted)",
        summary=(
            "The standard deviation of the topography after removing the fitted plane - an "
            "Sq-like roughness with global tilt taken out."
        ),
        explanation=(
            "Subtracting the fitted plane removes tilt so the residual reflects genuine "
            "surface texture; its standard deviation is the RMS roughness. Detilting first "
            "avoids reporting a large 'roughness' that is really just tilt."
        ),
        common_mistakes=(
            "Comparing roughness values computed over different areas or pixel sizes as if equal.",
        ),
        related_operations=("image.plane_level",),
        related_concepts=("concept.topography",),
    ),
    Article(
        article_id="diagnostic.harmonic_decay",
        category=DIAGNOSTIC,
        title="Harmonic amplitude decay",
        summary=(
            "The mean optical amplitude at each harmonic and its ratio to the next lower "
            "order - a convention-free proxy for near-field confinement and background "
            "suppression."
        ),
        explanation=(
            "Genuine near-field signal falls off from lower to higher harmonics in a "
            "characteristic way; a decay ratio well below 1 indicates the expected "
            "background suppression at higher orders. SNOMNIMAN reports amplitudes and "
            "decay ratios rather than an SNR, because a true SNR needs a noise model or a "
            "signal-free region that is not available deterministically."
        ),
        practical_guidance=(
            "If higher harmonics do not decay sensibly, suspect background or that the signal "
            "has reached the noise floor."
        ),
        related_concepts=("concept.harmonics",),
        related_diagnostics=("harmonic_signal_noise",),
    ),
    Article(
        article_id="diagnostic.harmonic_signal_noise",
        category=DIAGNOSTIC,
        title="Harmonic signal-vs-noise classification",
        summary=(
            "Each optical harmonic is classified signal / weak / noise / empty from the "
            "spatial coherence of its amplitude image and a single-image SNR estimate - a "
            "deterministic answer to 'which orders are signal vs. noise?'."
        ),
        explanation=(
            "Genuine near-field signal is spatially structured (neighbouring pixels are "
            "correlated); detector/demodulation noise is spatially white. The classifier "
            "measures the amplitude image's spatial coherence (mean nearest-neighbour "
            "autocorrelation; ~1 for smooth signal, ~0 for white noise) and corroborates it "
            "with a single-image SNR estimate, then labels each order: signal (coherent, "
            "above the noise floor), weak (signal comparable to noise - a transition), noise "
            "(noise-dominated or incoherent), or empty (not meaningfully recorded). It is a "
            "noise-floor classification, not a near-field-vs-background or 'best harmonic' "
            "judgement: a low order dominated by far-field background is still 'signal' here."
        ),
        scientific_background=(
            "Validated analytically (white noise -> coherence 0; smooth signal -> 1), "
            "synthetically (coherence ~0.5 at SNR=1), and on real data on both branches - "
            "strong signal (O2/O3) and genuine noise (high orders at the floor). The noise "
            "floor uses Immerkaer's single-image estimate; spatial coherence is the lag-1 "
            "case of Moran's I, whose white-noise null is known. See "
            "docs/harmonic-ranking-analysis.md."
        ),
        mathematical_background=(
            "coherence = mean lag-1 Pearson autocorrelation over x and y of the mean-removed "
            "amplitude; sigma_noise from a Laplacian 3x3 kernel (Immerkaer); SNR = "
            "sqrt(max(var_total - sigma_noise^2, 0)) / sigma_noise. Bands: signal "
            "(coherence >= 0.5 ~ SNR>=1), weak ([0.2, 0.5)), noise (< 0.2)."
        ),
        practical_guidance=(
            "Use it to skip noise/empty orders quickly. It does not tell you the best working "
            "harmonic - choosing between the signal-bearing orders is still the "
            "confinement-vs-background-vs-SNR judgement of the harmonics concept (often O2/O3)."
        ),
        common_mistakes=(
            "Reading 'signal' as 'near-field' or 'the order to use' - it only means 'above the "
            "noise floor' (O0/O1 background can read as signal).",
            "Trusting it on a scan dominated by coherent per-line or drift artifacts, which "
            "are not spatially white.",
        ),
        related_concepts=("concept.harmonics", "concept.complex_signals"),
        related_diagnostics=("harmonic_decay", "dynamic_range"),
        references=(_IMMERKAER, _MORAN, _KEILMANN),
    ),
    Article(
        article_id="diagnostic.dynamic_range",
        category=DIAGNOSTIC,
        title="Dynamic range and channel statistics",
        summary=(
            "Per-channel min/max/mean/std over finite values (amplitude view for complex "
            "channels), plus a count of invalid (NaN/inf) pixels."
        ),
        explanation=(
            "Basic statistics summarise a channel's value distribution and flag problems "
            "(e.g. invalid pixels, a collapsed range). For complex channels the statistics "
            "describe the amplitude; phase is cyclic and is not summarised this way."
        ),
        common_mistakes=(
            "Interpreting amplitude statistics in absolute units before normalization (they "
            "are in arbitrary units until referenced).",
        ),
        related_concepts=("concept.complex_signals",),
    ),
)


# --------------------------------------------------------------------------- #
# AI Scientist
# --------------------------------------------------------------------------- #

_AI = (
    Article(
        article_id="ai.scientific_briefing",
        category=AI,
        title="The Scientific Briefing",
        summary=(
            "A deterministic orientation to the loaded measurement - what it is, what the "
            "diagnostics say, what it enables - composed entirely from measured facts."
        ),
        explanation=(
            "The briefing answers 'tell me about this measurement.' Every statement is a "
            "deterministic fact drawn from the Description API (structure) and the "
            "Diagnostics Engine (computed facts), each tagged with its source. There is no "
            "model invention; an optional AI narrative may be layered on top, but the facts "
            "stand alone and are authoritative."
        ),
        related_concepts=("concept.provenance",),
        related_diagnostics=("topography_slope", "harmonic_decay"),
    ),
    Article(
        article_id="ai.suggested_next_steps",
        category=AI,
        title="Suggested Next Steps",
        summary=(
            "A ranked list of grounded next operations, produced deterministically by the "
            "Scientific Reasoning Rule Engine - the AI proposes; you decide; the engine "
            "performs."
        ),
        explanation=(
            "Each suggestion points at a registered operation that is applicable now and not "
            "already applied, with the deterministic evidence that triggered it, a caveat or "
            "two, and a one-click Preview into the Processing Workspace. The AI never "
            "executes anything - it recommends, and you accept an explicit, recorded "
            "derivation."
        ),
        related_concepts=("concept.provenance",),
        related_operations=("image.plane_level", "image.reference_normalize"),
    ),
    Article(
        article_id="ai.deterministic_reasoning",
        category=AI,
        title="Deterministic reasoning (the Rule Engine)",
        summary=(
            "Recommendations are generated by registered, individually-testable reasoning "
            "rules over deterministic facts - not by a language model - so identical "
            "measurements always yield identical, explainable recommendations."
        ),
        explanation=(
            "A reasoning rule encodes one piece of scientific best practice: when to "
            "recommend an operation, why, and with what caveats, evaluated against the "
            "deterministic facts. Because rules are generated from applicability and "
            "provenance, they cannot suggest an unavailable or already-applied operation. "
            "Every recommendation is traceable to the rule and the facts that produced it."
        ),
        related_concepts=("concept.provenance",),
        related_operations=("image.plane_level", "image.reference_normalize"),
    ),
    Article(
        article_id="ai.why_ai_does_not_decide",
        category=AI,
        title="Why the AI does not make scientific decisions",
        summary=(
            "SNOMNIMAN's maxim: scientific judgment is deterministic whenever possible; AI "
            "communicates, contextualizes, and teaches - it never replaces scientific "
            "reasoning or becomes a silent authority."
        ),
        explanation=(
            "When a judgment can be made by a deterministic rule over deterministic facts, "
            "it is made that way, so it can be defended and reproduced years later. A "
            "language model may one day phrase explanations more warmly, but it will never "
            "choose, rank, or invent a scientific result. If deterministic evidence is "
            "insufficient, SNOMNIMAN declines to recommend rather than guess - a missing rule "
            "is preferable to an unjustified one."
        ),
        related_concepts=("concept.immutable_measurements", "concept.provenance"),
    ),
)


#: The full initial library.
ARTICLES: tuple[Article, ...] = _CONCEPTS + _OPERATIONS + _DIAGNOSTICS + _AI


__all__ = ["ARTICLES"]
