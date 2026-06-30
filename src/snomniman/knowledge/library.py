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
    Article(
        article_id="concept.histogram",
        category=CONCEPT,
        title="Value distribution (histogram)",
        summary=(
            "The distribution of a channel's values - how often each value occurs - revealing "
            "populations, spread, outliers, and the dynamic range, with robust percentiles."
        ),
        explanation=(
            "A histogram bins the values currently on screen and counts how many pixels fall in "
            "each bin. Its shape is informative: a single hump is one population; two humps "
            "(bimodal) usually mean two materials or phases. The percentiles (P5/P25/median/"
            "P75/P95) give a robust range that ignores a few extreme pixels, and showing the "
            "current contrast limits over the distribution makes clear how much of the data the "
            "colour scale actually spans (the dynamic range). It is a read-only analysis, not a "
            "display control: it describes the data, it does not change it."
        ),
        scientific_background=(
            "Height/amplitude/phase distributions and 'statistical quantities' are a staple of "
            "SPM analysis (Gwyddion, bearing analysis). SNOMNIMAN bins by the Freedman-Diaconis "
            "rule (robust to outliers) by default and reports the descriptive variability set "
            "(mean, median, std, RMS, count) alongside the percentiles."
        ),
        practical_guidance=(
            "Read the Distribution section of the Diagnostics tab for the channel on screen. A "
            "bimodal distribution suggests setting contrast or a threshold between the two "
            "populations; use the percentiles for a robust display range rather than min/max."
        ),
        common_mistakes=(
            "Interpreting the histogram of wrapped phase as if it were linear - phase is cyclic, "
            "so a split peak at +/-pi is one population, not two.",
            "Reading fine structure into a histogram with too few samples or bins.",
        ),
        related_concepts=("concept.topography", "concept.complex_signals"),
        references=(_GWYDDION,),
    ),
    Article(
        article_id="concept.profile_analysis",
        category=CONCEPT,
        title="Line-profile feature analysis",
        summary=(
            "Quantitative features extracted from a line profile: peak/step heights, peak width "
            "(FWHM), peak spacing (a feature period), and the profile's descriptive statistics."
        ),
        explanation=(
            "A line profile turns a path across the image into a 1-D curve; feature analysis "
            "then reads the science off it. Peak height gives a feature's amplitude or a step "
            "height; the full width at half maximum (FWHM) gives a feature's size and, on a "
            "sharp edge, the spatial resolution; the spacing between successive peaks is a "
            "period - for s-SNOM polariton/plasmon imaging that period is the fringe spacing, "
            "which sets the polariton wavevector. The descriptive statistics (mean, median, "
            "std, RMS, count) summarize the whole profile."
        ),
        scientific_background=(
            "Peak detection by prominence and width-at-half-maximum is standard profilometry "
            "(Gwyddion/Origin profile tools; SciPy find_peaks/peak_widths). Fringe-period -> "
            "wavevector is the basis of near-field polariton interferometry (Keilmann & "
            "Hillenbrand)."
        ),
        practical_guidance=(
            "Draw a line across the features of interest in the Measure tab; the panel marks "
            "detected peaks and reports spacing and FWHM. For polariton fringes, read the mean "
            "peak spacing as the fringe period; for resolution, read the FWHM of a sharp edge."
        ),
        common_mistakes=(
            "Confusing FWHM with the full feature width - FWHM is measured at half height.",
            "Reading peak spacing from a noisy profile without enough prominence to separate "
            "real peaks from noise.",
        ),
        related_concepts=("concept.phase", "concept.near_field_microscopy"),
        references=(_KEILMANN,),
    ),
    Article(
        article_id="concept.region_comparison",
        category=CONCEPT,
        title="Region comparison (contrast)",
        summary=(
            "Comparing two regions' statistics - the difference and ratio of their means, with "
            "the underlying descriptive statistics - to quantify contrast between materials."
        ),
        explanation=(
            "s-SNOM contrast is inherently relative: the meaningful quantity is how one region "
            "differs from another (e.g. a feature versus its substrate), not a single absolute "
            "value. Region comparison reports the difference (additive contrast) and the ratio "
            "(multiplicative contrast) of two regions' mean values, and exposes the mean, "
            "standard deviation, and pixel count of each region so the contrast number is "
            "auditable - a large difference between two noisy or tiny regions means less than "
            "the same difference between two clean, well-sampled ones."
        ),
        scientific_background=(
            "Quantifying near-field contrast as a region-to-region ratio/difference is standard "
            "s-SNOM practice (Keilmann & Hillenbrand). Reporting variability (std) and sample "
            "count alongside the contrast follows ordinary measurement-uncertainty practice."
        ),
        practical_guidance=(
            "Place a region on each material (e.g. feature and substrate) in the Measure tab, "
            "then Compare regions. Report the ratio or difference together with each region's "
            "mean +/- std and pixel count."
        ),
        common_mistakes=(
            "Quoting a contrast ratio without its regions' spread and sample count.",
            "Taking a ratio when the reference region's mean is ~0 (it is undefined; use the "
            "difference instead).",
        ),
        related_concepts=("concept.complex_signals", "concept.near_field_microscopy"),
        references=(_KEILMANN,),
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
        article_id="operation.image.arithmetic",
        category=OPERATION,
        title="Arithmetic (two-measurement)",
        summary=(
            "Combines one channel of two compatible measurements pixel-by-pixel - currently the "
            "difference forms A - B, B - A, and |A - B| - producing a new derived dataset."
        ),
        explanation=(
            "This is the first operation that takes two measurements as input. It evaluates one "
            "channel of measurement A and the same channel of measurement B on each pixel and "
            "combines them, recording both measurements as parents in the result's provenance. "
            "It works on the channel's real value view - the values of a real channel (e.g. Z) "
            "or the amplitude of a complex channel - and produces a single real-valued result "
            "channel. The two measurements must share the same grid (dimensions, pixel spacing, "
            "and extent) and the chosen channel; mismatches are refused rather than reconciled, "
            "because aligning or resampling data is a separate, explicit operation."
        ),
        scientific_background=(
            "Comparing two scans - before vs. after a stimulus, two tip conditions, two "
            "harmonics on a shared grid - is a routine analysis. A difference image makes the "
            "spatial change explicit; the absolute difference highlights where two scans differ "
            "regardless of sign. The operation is intentionally general (a two-input "
            "combination) so further modes (sum, ratio, normalized difference) extend it rather "
            "than spawning new operation types."
        ),
        mathematical_background=(
            "For the chosen channel with value views a(x,y) and b(x,y): A - B = a - b; "
            "B - A = b - a; |A - B| = abs(a - b). For a complex channel the value view is the "
            "amplitude |.|; phase differencing is cyclic and re-referencing and is deliberately "
            "not performed here. The result inherits A's coordinates and is real-valued."
        ),
        practical_guidance=(
            "Open or add both measurements to the project, make A the active measurement, then "
            "choose Arithmetic and pick B as the second input. Preview shows A versus the "
            "result before you accept; the difference is then a normal derived dataset in A's "
            "history that you can measure, process further, save, and export. If the two scans "
            "are not on the same grid, register/crop them to a common grid first (a separate "
            "step) - SNOMNIMAN never silently resamples."
        ),
        common_mistakes=(
            "Differencing two scans of different regions or sampling - a meaningful difference "
            "requires the same physical grid; the operation refuses mismatched grids.",
            "Reading a phase difference into the amplitude difference of a complex channel - "
            "this combines amplitudes, not phase.",
            "Expecting alignment: drift between two scans is not corrected here; align first.",
        ),
        related_concepts=("concept.provenance",),
        related_operations=("image.reference_normalize",),
        related_diagnostics=(),
        references=(_GWYDDION,),
    ),
    Article(
        article_id="operation.image.fix_zero",
        category=OPERATION,
        title="Fix Zero (height datum)",
        summary=(
            "Shifts a real channel so its minimum, mean, or median is zero - setting a "
            "defined height datum without removing tilt or curvature."
        ),
        explanation=(
            "AFM/SPM height is recorded relative to an arbitrary scanner origin, so a zero "
            "datum is chosen before reading feature heights and depths. Fix Zero subtracts a "
            "single constant from the channel (default: the minimum, so heights are measured "
            "upward from the lowest point), leaving tilt, curvature, and every height "
            "difference unchanged. It is the right tool once tilt has been handled (or when "
            "the data is already flat); use plane leveling or line flattening to remove form."
        ),
        scientific_background=(
            "Shifting the minimum (or mean / median) to zero is the standard offset step in "
            "scanning-probe software (Gwyddion 'Fix Zero' / 'Shift Minimum to Zero'; WSxM). "
            "The minimum datum is conventional for reading absolute feature heights; the mean "
            "gives a zero-mean map for roughness and comparison; the median is robust to a few "
            "extreme pixels."
        ),
        mathematical_background=(
            "For datum d in {min, mean, median} over finite pixels, the output is z - d(z). "
            "Only a constant is removed, so the result is information-preserving."
        ),
        practical_guidance=(
            "Use the default minimum datum to read heights from the lowest point; use mean for "
            "zero-mean comparison. Run it after plane leveling / line flattening, not instead "
            "of them - Fix Zero does not remove tilt or bow."
        ),
        common_mistakes=(
            "Expecting it to flatten tilt or curvature - it only removes a constant offset.",
            "Comparing absolute heights across scans without first fixing a common datum.",
        ),
        related_concepts=("concept.topography",),
        related_operations=("image.plane_level", "image.line_flatten"),
        related_diagnostics=("rms_roughness",),
        references=(_GWYDDION, _WSXM),
    ),
    Article(
        article_id="operation.image.phase_offset",
        category=OPERATION,
        title="Phase Offset (re-reference)",
        summary=(
            "Re-references a complex channel's phase by subtracting a constant (the circular "
            "mean, or a chosen value); the amplitude is preserved exactly."
        ),
        explanation=(
            "In s-SNOM the absolute optical phase is arbitrary - it depends on interferometer "
            "path length, the demodulation reference, and drift - so only phase contrast "
            "relative to a chosen datum is interpretable. Phase Offset rotates the channel by a "
            "constant (O -> O * exp(-i*dphi)), shifting the phase while leaving the amplitude "
            "untouched, and records the new reference in the dataset's conventions. It is the "
            "explicit, provenance-tracked phase re-referencing the project's phase convention "
            "requires (phase is never changed silently)."
        ),
        scientific_background=(
            "Because s-SNOM phase is relative, removing a global phase offset is a routine "
            "first step (Keilmann & Hillenbrand). The default datum is the circular mean - the "
            "angle of the (amplitude-weighted) mean complex value - which is the correct way to "
            "average a cyclic quantity; an arithmetic mean of wrapped angles is wrong near the "
            "+/-pi wrap. Referencing instead to a known substrate region is the richer form."
        ),
        mathematical_background=(
            "dphi = angle(mean(O)) for the circular mean, or a supplied constant; the output is "
            "O * exp(-i*dphi). Amplitude |O| is unchanged; phase becomes angle(O) - dphi."
        ),
        practical_guidance=(
            "Use the default mean datum to remove a global phase offset; use a constant to align "
            "to a value measured elsewhere. To compare phase across measurements, re-reference "
            "each to the same datum first. Region-based (substrate) referencing is planned."
        ),
        common_mistakes=(
            "Averaging wrapped phase angles arithmetically - always average phase as a complex "
            "vector (this operation does).",
            "Reading absolute phase as physical - only phase contrast is meaningful.",
        ),
        related_concepts=("concept.phase", "concept.complex_signals"),
        related_operations=("image.reference_normalize", "image.phase_unwrap"),
        related_diagnostics=(),
        references=(_KEILMANN, _OCELIC),
    ),
    Article(
        article_id="operation.image.normalize_amplitude",
        category=OPERATION,
        title="Normalize Amplitude",
        summary=(
            "Divides a complex channel by its peak (default) or mean amplitude, mapping "
            "amplitude to a common dimensionless scale; the phase is preserved exactly."
        ),
        explanation=(
            "s-SNOM amplitude is reported in arbitrary units that depend on detector gain, "
            "demodulation, and alignment, so a single scan's absolute amplitude has no absolute "
            "meaning - only relative amplitude (contrast) is interpretable. Normalize Amplitude "
            "divides the channel by a single positive scalar (O -> O / s), rescaling amplitude "
            "to a common scale while leaving the phase untouched, so amplitude becomes "
            "comparable across channels, harmonics, and measurements."
        ),
        scientific_background=(
            "Peak normalization (divide by max |O|, mapping into [0, 1]) is the common display "
            "and figure-preparation default (e.g. ImageJ/Fiji); dividing by the mean gives "
            "contrast around 1. The most quantitative form normalizes to the mean amplitude of "
            "a known substrate region (self-normalization), which is planned for a later phase."
        ),
        mathematical_background=(
            "s = max(|O|) or mean(|O|) over finite pixels; the output is O / s. The amplitude "
            "becomes dimensionless; the phase angle(O) is unchanged."
        ),
        practical_guidance=(
            "Use peak normalization to put amplitude in [0, 1] for display or comparison; use "
            "the mean for relative contrast. Normalize each measurement consistently before "
            "comparing amplitude contrast across scans."
        ),
        common_mistakes=(
            "Treating normalized amplitude as a calibrated quantity - it is a dimensionless "
            "ratio, not an absolute optical amplitude.",
            "Comparing amplitudes normalized by different data without a common reference.",
        ),
        related_concepts=("concept.complex_signals", "concept.near_field_microscopy"),
        related_operations=("image.reference_normalize",),
        related_diagnostics=(),
        references=(_KEILMANN,),
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
