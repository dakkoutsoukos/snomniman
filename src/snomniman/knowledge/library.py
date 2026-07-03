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
_GRIFFITHS = (
    "Griffiths & de Haseth, Fourier Transform Infrared Spectrometry, 2nd ed., Wiley "
    "(2007) - the standard FTIR apodization/zero-fill/phase-correction chain."
)
_MERTZ = (
    "Mertz, Infrared Phys. 7, 17 (1967) - auxiliary computation (phase "
    "correction) for Fourier spectrometry."
)
_HARRIS = (
    "Harris, Proc. IEEE 66(1), 51 (1978) - on the use of windows for harmonic "
    "analysis with the DFT (apodization window definitions)."
)


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
        related_manual_pages=("troubleshooting.cannot_edit_raw_data",),
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
        related_manual_pages=("explorer.provenance",),
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
    Article(
        article_id="concept.point_spectrum",
        category=CONCEPT,
        title="Point spectra and point-spectroscopy line scans",
        summary=(
            "Instead of imaging one wavenumber over many (x, y) pixels, point spectroscopy "
            "fixes the tip at one or more spatial positions and sweeps the excitation "
            "wavenumber, recording a full optical spectrum at each position."
        ),
        explanation=(
            "An s-SNOM image holds one value per (x, y) pixel at a fixed excitation "
            "wavenumber; point spectroscopy holds one full spectrum - amplitude and phase "
            "versus wavenumber, for every optical harmonic - at each of one or more fixed "
            "spatial positions. A single position produces a `SPECTRUM` dataset (dims "
            "`(wavenumber,)`); several positions along a line produce a `LINE_SCAN` dataset "
            "with a spectral axis (dims `(s, wavenumber)`) - a spectrum at every point along "
            "the line, not a reduction to one number per position. The height channel `Z` is "
            "recorded at every spectral sample too, since AFM feedback stays active through "
            "the sweep, so it can vary slightly across a sweep even at one position."
        ),
        scientific_background=(
            "This is a direct-detection wavenumber sweep (e.g. a tunable QCL/"
            "\"Piano\" source demodulated with PsHet, ADR concept.pseudoheterodyne) - each "
            "wavenumber is measured directly, one at a time. That is scientifically distinct "
            "from interferometric nano-FTIR, which records one interferogram (signal vs. "
            "optical path difference, `INTERFEROGRAM`, dims `(opd,)`) and recovers the full "
            "spectrum by Fourier transform. Both eventually describe the same physical "
            "quantity - a complex near-field response versus wavenumber - and share the same "
            "`SPECTRUM`/`LINE_SCAN`/`HYPERSPECTRAL` representation once in the frequency "
            "domain, but SNOMNIMAN does not yet read or FFT an interferogram; do not assume a "
            "point spectrum in the application was acquired interferometrically."
        ),
        practical_guidance=(
            "Use a point spectrum to identify a vibrational resonance (a peak/dip in "
            "amplitude or phase versus wavenumber) at a location of interest before deciding "
            "which harmonic and wavenumber to image at scale; a line of point spectra lets "
            "you compare that resonance across a small set of positions (e.g. on and off a "
            "nanostructure) without a full hyperspectral image acquisition."
        ),
        common_mistakes=(
            "Assuming a point-spectroscopy line scan is a spatial image - its second axis is "
            "wavenumber, not a second spatial coordinate, so 2-D image operations (plane "
            "leveling, spatial harmonic signal/noise classification, line/ROI profiles) do "
            "not apply to it.",
            "Calling this acquisition \"nano-FTIR\" - it is a direct wavenumber sweep, not an "
            "interferogram.",
        ),
        related_concepts=(
            "concept.spectral_axis",
            "concept.pseudoheterodyne",
            "concept.harmonics",
            "concept.near_field_microscopy",
            "concept.interferogram",
        ),
        related_manual_pages=("getting_started.opening_a_spectrum",),
        references=(_HUTH,),
    ),
    Article(
        article_id="concept.spectral_axis",
        category=CONCEPT,
        title="The spectral (wavenumber) axis",
        summary=(
            "Spectral datasets are indexed by wavenumber (cm^-1), not by a spatial "
            "coordinate - the canonical spectral unit, distinct from and never auto-converted "
            "to the canonical spatial unit (nm)."
        ),
        explanation=(
            "A spectral axis records where in the excitation range each sample was taken - "
            "its range (minimum/maximum wavenumber), its point count, and its mean sampling "
            "step (the spacing between consecutive wavenumbers), which together set the "
            "spectral resolution actually achieved during acquisition. Wavenumber (cm^-1, "
            "proportional to photon energy) is the standard vibrational-spectroscopy unit; "
            "it is nonlinearly related to wavelength, so SNOMNIMAN keeps a dedicated "
            "wavenumber unit rather than folding it into the nm length-unit converter."
        ),
        practical_guidance=(
            "Read the reported spectral range and sampling as what the instrument actually "
            "swept, not as a guarantee of resolving a feature narrower than the sampling "
            "step - a 1 cm^-1 step cannot resolve structure finer than that."
        ),
        related_concepts=("concept.point_spectrum",),
    ),
    Article(
        article_id="concept.interferogram",
        category=CONCEPT,
        title="Interferograms and the zero-path-difference (ZPD)",
        summary=(
            "An interferogram is the raw signal recorded against optical path "
            "difference (OPD), before Fourier transformation - the actual 'FTIR' "
            "half of nano-FTIR that a point spectrum's direct wavenumber sweep "
            "never records."
        ),
        explanation=(
            "As an interferometer's moving mirror scans, the detector (or a "
            "demodulated near-field signal) is recorded as a function of the "
            "resulting optical path difference (OPD), not of wavenumber directly. "
            "This signal - the interferogram, `INTERFEROGRAM`, dims `(opd,)` - is "
            "not yet a spectrum: it must be Fourier-transformed to recover amplitude "
            "and phase versus wavenumber (`spectrum.fft_interferogram`). Its most "
            "important sample is the zero-path-difference (ZPD) point, where the two "
            "interferometer arms are exactly equal length and the signal reaches its "
            "burst maximum; every other OPD sample is referenced relative to it. Real "
            "acquisitions are commonly asymmetric ('single-sided'): a short segment "
            "before ZPD and a much longer one after, to keep the scan fast while "
            "still capturing enough of the burst to estimate the interferometer's "
            "instrumental phase."
        ),
        scientific_background=(
            "Conventional FTIR spectrometry is built entirely on this interferogram "
            "-> spectrum pipeline (apodize, zero-fill, phase-correct, Fourier "
            "transform); nano-FTIR reuses the identical computation on a near-field "
            "interferogram (Huth et al., Nano Lett. 12, 3973, 2012). This is "
            "scientifically distinct from the direct wavenumber-sweep point "
            "spectroscopy SNOMNIMAN already supports (concept.point_spectrum): a "
            "sweep measures each wavenumber directly, one at a time, and needs no "
            "Fourier transform at all."
        ),
        practical_guidance=(
            "Inspect an interferogram before processing it - a well-registered ZPD "
            "should show a clear, symmetric burst; a badly asymmetric or missing "
            "burst usually means the ZPD is mis-located, which is exactly what phase "
            "correction (concept.apodization; spectrum.fft_interferogram's "
            "`phase_correction` parameter) is designed to compensate for."
        ),
        common_mistakes=(
            "Treating an interferogram as if it were already a spectrum - its axis "
            "is optical path difference (cm), not wavenumber, and its values carry "
            "no direct per-wavenumber meaning until Fourier-transformed.",
            "Assuming the ZPD is always the interferogram's first sample - real, "
            "asymmetric single-sided acquisitions place it wherever the OPD "
            "coordinate is closest to zero, not necessarily at index 0.",
        ),
        related_concepts=("concept.apodization", "concept.point_spectrum", "concept.spectral_axis"),
        related_operations=("spectrum.fft_interferogram",),
        references=(_GRIFFITHS, _HUTH),
    ),
    Article(
        article_id="concept.apodization",
        category=CONCEPT,
        title="Apodization (interferogram windowing)",
        summary=(
            "Multiplying an interferogram by a tapering window before the Fourier "
            "transform trades spectral resolution for suppressed sidelobe ringing - "
            "a routine, deterministic step in every FTIR processing chain."
        ),
        explanation=(
            "An interferogram is necessarily recorded over a finite OPD range; "
            "truncating it abruptly (no window, 'boxcar') is equivalent to "
            "convolving the true spectrum with a sinc function, whose slowly "
            "decaying sidelobes ring broadly across the whole spectrum. A tapering "
            "window (Hann, Hamming, the 3-term Blackman-Harris window) that decays "
            "smoothly toward the edges of the recorded OPD range suppresses this "
            "ringing at the cost of a wider main lobe (lower resolution) - a "
            "well-characterized trade-off, not a free improvement. The window is "
            "coherent-gain normalized (rescaled to unit mean) so the recovered peak "
            "amplitude is comparable across window choices; only the sidelobe/"
            "resolution trade-off differs between them."
        ),
        mathematical_background=(
            "The window must be centered on the zero-path-difference (ZPD) sample, "
            "not on the array's geometric center: a real interferogram is commonly "
            "acquired asymmetrically about ZPD (a short segment before it, a longer "
            "one after), so a window's peak (value 1) is placed at the ZPD sample "
            "and evaluated outward to whichever array edge is reached first. "
            "Centering a symmetric window on the array instead would apodize a "
            "single-sided interferogram (ZPD at its very first sample) down to zero "
            "at that highest-amplitude sample - discarding essentially the entire "
            "signal."
        ),
        practical_guidance=(
            "The 3-term Blackman-Harris window (the default) gives strong sidelobe "
            "suppression (~-67 dB), the usual choice when a weak near-field "
            "resonance sits near a much stronger far-field background; boxcar (no "
            "apodization) keeps maximum resolution when sidelobe ringing is "
            "acceptable or a very clean, well-registered interferogram is available."
        ),
        common_mistakes=(
            "Expecting apodization to change *where* a resonance appears - it "
            "changes lineshape (width, sidelobes), not peak position.",
            "Using boxcar with a large zero-fill factor and reading the resulting "
            "many small ripples as real spectral features - they are sinc-sidelobe "
            "ringing from the unwindowed truncation, resolved (not created) by the "
            "finer sampling.",
        ),
        related_concepts=("concept.interferogram",),
        related_operations=("spectrum.fft_interferogram",),
        references=(_HARRIS, _GRIFFITHS),
    ),
    Article(
        article_id="concept.hyperspectral_cube",
        category=CONCEPT,
        title="Hyperspectral cubes",
        summary=(
            "A full spectrum - amplitude and phase versus wavenumber - at every "
            "pixel of a 2-D scan: nano-FTIR's single most distinctive capability, "
            "nanoscale-resolved chemical identification rather than contrast at one "
            "frequency."
        ),
        explanation=(
            "A hyperspectral dataset (`HYPERSPECTRAL`, dims `(y, x, wavenumber)`) "
            "carries a spatial grid and a spectral axis *together* - the data model "
            "already derives both capabilities (`SPATIAL_2D` and `SPECTRAL`) "
            "independently, so a hyperspectral cube needs no new representation, "
            "only a workspace that browses it two ways: a **band map** (one "
            "wavenumber, shown as an ordinary 2-D image - concept.band_map) and a "
            "**per-pixel or per-ROI spectrum** (one location, shown as a curve "
            "versus wavenumber). Clicking a pixel on the band map shows that "
            "pixel's spectrum; selecting a rectangle or polygon ROI shows the mean "
            "spectrum over that region, and multiple ROIs can be overlaid to "
            "compare a resonance across locations (e.g. on versus off a "
            "nanostructure)."
        ),
        scientific_background=(
            "Recording two-dimensional arrays of thousands of spectra with "
            "spatial resolution and precision better than 30 nm is the "
            "literature's own framing of why hyperspectral nano-FTIR matters; the "
            "resulting cube is explored via band maps and region comparison to "
            "build a compositional picture, not read from a single frequency."
        ),
        practical_guidance=(
            "Browse several bands (not just one) before concluding two regions "
            "differ chemically - a single band map is one frequency's contrast, "
            "not a compositional map. Use an ROI-averaged spectrum rather than a "
            "single noisy pixel spectrum when comparing a resonance across "
            "locations."
        ),
        common_mistakes=(
            "Assuming a hyperspectral measurement is spectral in the same sense "
            "as a point spectrum - it is a genuine third state (both a spatial "
            "grid and a spectral axis together), never an overload of the "
            "point-spectroscopy dispatch: routing it through the plain 2-D image "
            "path (or the point-spectrum curve path) would try to render or plot "
            "a whole 3-D array where a 2-D or 1-D one is expected.",
            "Reading a whole-cube value distribution as if it summarized 'the "
            "measurement' - a histogram that mixes every wavenumber and every "
            "pixel together is scientifically misleading; the honest summary is "
            "always per-band.",
        ),
        related_concepts=(
            "concept.band_map",
            "concept.point_spectrum",
            "concept.interferogram",
            "concept.spectral_axis",
        ),
        related_manual_pages=("getting_started.opening_a_spectrum",),
        references=(_HUTH,),
    ),
    Article(
        article_id="concept.band_map",
        category=CONCEPT,
        title="Band maps",
        summary=(
            "A single-wavenumber slice of a hyperspectral cube, shown as an "
            "ordinary 2-D image - the spatial contrast at one frequency, not a "
            "summary of the whole spectrum."
        ),
        explanation=(
            "A band map answers 'what does the sample look like at this one "
            "wavenumber?' - it reuses the same colormap/levels/extent/scale-bar "
            "display logic every 2-D channel image already uses, applied to one "
            "band instead of a whole channel. It is a projection, not a "
            "computation: no new pixel value is derived, the cube is simply "
            "indexed at one wavenumber."
        ),
        practical_guidance=(
            "Step through wavenumbers to find where spatial contrast appears or "
            "disappears - that is usually where a vibrational resonance is "
            "active. A single band map cannot distinguish 'no signal here' from "
            "'no resonance at this particular frequency here'; compare several "
            "bands, or an ROI-averaged spectrum, before drawing a chemical "
            "conclusion."
        ),
        common_mistakes=(
            "Treating one band map as a complete compositional map - it is one "
            "frequency's contrast; two materials can look identical at one band "
            "and differ sharply at another.",
        ),
        related_concepts=("concept.hyperspectral_cube",),
    ),
    Article(
        article_id="concept.processing_recipe",
        category=CONCEPT,
        title="Processing recipes",
        summary=(
            "A recipe captures a completed processing history once - an ordered list of "
            "operations and their parameters - and replays it on another compatible "
            "measurement through the exact same steps, unchanged."
        ),
        explanation=(
            "A recipe is not a new kind of computation: it is a portable, re-bindable "
            "projection of a provenance chain. Capturing a recipe reads a measurement's "
            "history - which operations were applied, in what order, with what parameters - "
            "and detaches it from that one dataset. Replaying a recipe reruns each step "
            "through the same registered operation and the same parameter validation a "
            "manual Preview uses, producing an ordinary derived dataset with a complete, "
            "correct provenance record - indistinguishable from applying the same steps by "
            "hand. A recipe therefore repeats a judgment the researcher already made and "
            "accepted on the first scan; it makes no new scientific decision of its own."
        ),
        scientific_background=(
            "Applying an identical processing chain across a set of sibling scans (a power "
            "series, a time series, a sample series) is a correctness property, not only a "
            "convenience: inconsistent manual processing between scans is a real source of "
            "artifact when the results are later compared. A recipe turns 'the same "
            "processing on every scan' from a hope into a guarantee."
        ),
        practical_guidance=(
            "Build and accept a processing chain on one measurement as usual, then save it "
            "as a recipe from its history. Load or select that recipe on another compatible "
            "measurement and Preview it exactly as you would any operation - if a step does "
            "not apply (e.g. a required channel is missing), the recipe reports which step "
            "failed rather than silently skipping it or guessing a substitute."
        ),
        common_mistakes=(
            "Assuming a recipe can capture a chain that combines two different measurements "
            "(e.g. one ending in a two-input arithmetic difference) - only a single-input "
            "chain is portable, since the second measurement is specific to the one dataset "
            "it was compared against.",
            "Expecting a recipe to choose which processing a new measurement needs - it only "
            "repeats a sequence the researcher already authored and accepted; choosing what "
            "to apply next remains the researcher's judgment (or a separately-validated AI "
            "recommendation), never the recipe's.",
        ),
        related_concepts=("concept.provenance", "concept.immutable_measurements"),
        related_operations=("image.plane_level", "image.line_flatten", "image.fix_zero"),
        related_manual_pages=("workspace.recipes",),
    ),
    Article(
        article_id="concept.scientific_reporting",
        category=CONCEPT,
        title="Scientific reports and publication packages",
        summary=(
            "A report is an assembled, not invented, document: every fact in it - "
            "measurement identity, diagnostics, processing history, batch outcomes, "
            "region/profile statistics - was already computed and validated elsewhere; "
            "the report only arranges and attributes it."
        ),
        explanation=(
            "Three reports serve three purposes from the same underlying facts. The "
            "Experiment Report summarizes a whole project - every measurement, its "
            "diagnostics, its processing history, any recipes/batch runs applied, and "
            "any region/profile/histogram measurements taken - for a lab record or a "
            "collaborator update. The Publication Package is a curated subset of the "
            "same facts (metadata, tables, a list of already-exported figures) shaped "
            "for assembling a paper or its supplementary information. The "
            "Reproducibility Report answers one question for a single measurement - "
            "'exactly how was this result produced?' - by rendering its provenance "
            "chain in plain language, plus the exact machine-readable provenance JSON "
            "as an appendix (the same serialization the project file itself uses, not "
            "a second representation). None of the three computes a new number, and "
            "none contains AI-generated interpretation - a report is deterministic: the "
            "same project state always produces the same report."
        ),
        scientific_background=(
            "Reproducibility depends on more than correct numbers - it depends on "
            "being able to reconstruct, months or years later, exactly what was done "
            "to produce a figure or a conclusion. Grounding a report entirely in the "
            "provenance DAG (rather than a parallel, hand-maintained lab notebook) "
            "means the report can never silently drift from what the software "
            "actually did."
        ),
        practical_guidance=(
            "Generate a report from the Experiment tab at any point in a session; it "
            "reflects the project's state at that moment (recipes and batch runs "
            "performed earlier in the *same* session are included, since the recipe "
            "each measurement's processing chain matches is detected directly from its "
            "provenance, not from a separate log). Export figures via the existing "
            "Export -> Figure... action first if you want the Publication Package to "
            "list them. Markdown and HTML are both supported; a laid-out PDF document "
            "is not - export any individual figure as vector PDF instead, and paste "
            "the report text into a manuscript or lab notebook as needed."
        ),
        common_mistakes=(
            "Expecting a report to explain *why* a result matters - it states facts, "
            "never interpretation; scientific judgment remains the researcher's.",
            "Assuming 'applied recipes' reflects every recipe ever run on a "
            "measurement - it reflects what the measurement's *current* provenance "
            "chain matches, which is exactly and only what actually produced the "
            "active dataset.",
        ),
        related_concepts=("concept.provenance", "concept.processing_recipe"),
        related_manual_pages=("export.reports",),
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
        related_manual_pages=("workspace.image.plane_level",),
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
        related_manual_pages=("workspace.image.line_flatten",),
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
        related_manual_pages=("workspace.image.arithmetic",),
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
        related_manual_pages=("workspace.image.fix_zero",),
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
        related_manual_pages=("workspace.image.phase_offset",),
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
        related_manual_pages=("workspace.image.normalize_amplitude",),
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
        related_manual_pages=("workspace.image.reference_normalize",),
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
        related_manual_pages=("workspace.image.phase_unwrap",),
        references=(_GHIGLIA,),
    ),
    Article(
        article_id="operation.image.region_phase_reference",
        category=OPERATION,
        title="Region Phase Reference",
        summary=(
            "Re-references a complex channel's phase to the circular mean of a user-selected "
            "rectangular region (substrate or known material); the amplitude is preserved exactly."
        ),
        explanation=(
            "The absolute optical phase in s-SNOM is arbitrary - it depends on interferometer "
            "path length, the demodulation reference, and drift - so only phase *contrast* "
            "relative to a chosen datum is physically interpretable. This operation subtracts the "
            "circular mean of a reference region from every pixel: phi_result = phi - phi_ref, "
            "where phi_ref = circular_mean(phi over the region). After the operation the reference "
            "region has mean phase ≈ 0, and every other pixel shows its phase contrast relative "
            "to that material. The amplitude is unchanged; the new reference is recorded in the "
            "dataset's conventions."
        ),
        scientific_background=(
            "The reference region is typically a substrate (SiO2, gold, CdO substrate area) or a "
            "known-material patch visible in the field of view. Referencing to a substrate region "
            "converts the arbitrary absolute phase into a publication-standard quantity: the "
            "optical phase contrast relative to that material. This is the form reported in "
            "essentially all quantitative nano-FTIR and IR s-SNOM figures (Huth et al., Nano "
            "Lett. 2012; Basov et al., Science 2016; Huber et al., Nano Lett. 2008). The "
            "global-mean form (image.phase_offset reference='mean') removes a global offset but "
            "mixes substrate and sample contributions; a substrate-region datum is clean, "
            "reproducible, and directly comparable across measurements on the same substrate."
        ),
        mathematical_background=(
            "phi_ref = angle(mean(O_region)), the circular mean: the angle of the mean complex "
            "vector over the reference region. This is the correct average of a cyclic quantity - "
            "an arithmetic mean of wrapped angles is wrong near the ±pi branch cut (e.g. +179° "
            "and -179° should average to 180°, not 0°). The output is O * exp(-i * phi_ref); "
            "amplitude |O| is unchanged; phase becomes angle(O) - phi_ref."
        ),
        practical_guidance=(
            "Draw an ROI on a clean substrate or reference material area (avoid features, "
            "domain walls, or defects). Apply this operation before comparing phase across "
            "measurements: each measurement referenced to the same substrate type gives "
            "cross-measurement phase contrast. Use image.phase_offset for a quick global "
            "offset removal when a clean substrate region is not available."
        ),
        common_mistakes=(
            "Placing the reference region on a feature or domain boundary rather than a clean "
            "substrate - the region's mean then reflects sample contrast, not a neutral datum.",
            "Reading absolute phase from the output as a calibrated quantity - it is phase "
            "contrast relative to the reference region, not an absolute phase.",
            "Comparing measurements referenced to different substrates without correcting for "
            "the differing dielectric backgrounds.",
        ),
        related_concepts=(
            "concept.phase", "concept.complex_signals", "concept.near_field_microscopy"
        ),
        related_operations=(
            "image.phase_offset", "image.reference_normalize", "image.phase_unwrap"
        ),
        related_diagnostics=(),
        related_manual_pages=("workspace.image.region_phase_reference",),
        references=(
            "Huth et al., Nano Lett. 12, 3973 (2012) - nano-FTIR phase referencing.",
            "Basov et al., Science 354, aag1992 (2016) - polariton phase maps.",
            _KEILMANN,
            _OCELIC,
        ),
    ),
    Article(
        article_id="operation.image.region_amplitude_reference",
        category=OPERATION,
        title="Region Amplitude Reference",
        summary=(
            "Normalizes a complex channel's amplitude to the mean amplitude of a user-selected "
            "rectangular region (substrate or known material); the phase is preserved exactly."
        ),
        explanation=(
            "s-SNOM amplitude is reported in arbitrary units that depend on detector gain, "
            "demodulation, and alignment, so raw amplitude values are not comparable across "
            "harmonics, sessions, or instruments. This operation divides every pixel by the mean "
            "amplitude of a reference region: A_result = |O| / A_ref, where A_ref is the mean "
            "of |O| over the reference region. After the operation the reference region has mean "
            "amplitude ≈ 1.0 by construction; every other pixel shows its amplitude contrast "
            "relative to that material. The phase is unchanged."
        ),
        scientific_background=(
            "Self-normalization to a substrate or reference-material region converts s-SNOM "
            "amplitude from arbitrary instrument units to a dimensionless ratio relative to a "
            "known material - making amplitudes comparable across harmonics, measurements, and "
            "instruments (Dai et al., Science 2014; Woessner et al., Nature Materials 2015). "
            "The whole-image normalizations (image.normalize_amplitude peak/mean) are useful for "
            "display, but they mix substrate and sample contributions; a substrate-region datum "
            "is quantitatively cleaner and reproduces the ratio reported in published polariton "
            "and chemical-contrast studies."
        ),
        mathematical_background=(
            "A_ref = mean(|O_region|) over finite pixels in the reference region. "
            "Output: O_result = O / A_ref. Amplitude |O_result| = |O| / A_ref (dimensionless "
            "ratio relative to the reference material); phase angle(O_result) = angle(O) "
            "(unchanged). A_ref must be positive; a zero-amplitude reference region is rejected."
        ),
        practical_guidance=(
            "Choose a reference region on a substrate or material whose response is a known, "
            "stable baseline (e.g. SiO2, gold, or a large flat area of the dominant material). "
            "Avoid bright features in the region - they pull the mean amplitude up and "
            "over-suppress the rest of the image. Apply the same region bounds consistently "
            "across a dataset for cross-measurement comparison. The normalized amplitude is "
            "dimensionless; do not compare it to uncalibrated amplitudes from other sessions "
            "unless both are referenced to the same material."
        ),
        common_mistakes=(
            "Choosing a reference region that contains a feature or bright spot - the inflated "
            "mean amplitude then suppresses the rest of the image.",
            "Treating the result as a calibrated absolute amplitude - it is a ratio relative to "
            "the chosen reference region, not an SI-calibrated quantity.",
            "Referencing different measurements to different substrates, then comparing the "
            "resulting amplitude maps as if they share a common scale.",
        ),
        related_concepts=(
            "concept.complex_signals", "concept.near_field_microscopy", "concept.harmonics"
        ),
        related_operations=("image.normalize_amplitude", "image.reference_normalize"),
        related_diagnostics=(),
        related_manual_pages=("workspace.image.region_amplitude_reference",),
        references=(
            "Dai et al., Science 343, 1125 (2014) - hBN phonon polaritons.",
            "Woessner et al., Nature Materials 14, 421 (2015) - graphene polaritons.",
            _KEILMANN,
        ),
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
        related_manual_pages=("workspace.image.crop",),
    ),
    Article(
        article_id="operation.spectrum.fft_interferogram",
        category=OPERATION,
        title="FFT Interferogram (nano-FTIR)",
        summary=(
            "Apodizes, zero-fills, phase-corrects, and Fourier-transforms a "
            "real-valued interferogram into a complex spectrum - the actual "
            "Fourier-transform computation nano-FTIR is named for."
        ),
        explanation=(
            "Reads a real-valued channel indexed by optical path difference (OPD) "
            "and produces a new complex channel indexed by wavenumber: the raw "
            "measurement (`INTERFEROGRAM`) becomes a `SPECTRUM`. The chain is the "
            "standard conventional-FTIR sequence - apodize (window the interferogram "
            "to suppress truncation ringing), zero-fill (interpolate more spectral "
            "points; adds no new resolution), phase-correct (Mertz method: estimate "
            "and remove instrumental phase error from a short segment around the "
            "zero-path-difference sample), forward FFT - applied unmodified to the "
            "near-field variant. This is the first operation whose output data kind "
            "differs from its input's; the processing engine already supported this "
            "(a step's `_execute` may return any `DataKind`), it simply had no prior "
            "operation exercising it."
        ),
        scientific_background=(
            "Conventional Fourier-transform infrared spectrometry is built on "
            "exactly this pipeline (Griffiths & de Haseth 2007 ch. 3); nano-FTIR "
            "reuses the identical computation on a near-field interferogram (Huth "
            "et al., Nano Lett. 12, 3973, 2012). Apodization window definitions and "
            "the coherent-gain normalization follow Harris (1978); the phase-"
            "correction method follows Mertz (1967)."
        ),
        mathematical_background=(
            "With OPD sampled uniformly in centimetres, wavenumber [cm^-1] = 1 / "
            "OPD [cm] falls directly out of the standard DFT frequency relation - no "
            "unit conversion is needed. The window is centered on the zero-path-"
            "difference sample (not the array's geometric center - see "
            "concept.apodization) and coherent-gain normalized; zero-filling pads "
            "the apodized signal to `zero_fill` times its length before the real-"
            "input FFT (`numpy.fft.rfft`); Mertz phase correction estimates a "
            "low-resolution phase spectrum from a short segment symmetric about the "
            "ZPD sample and multiplies the full spectrum by its (interpolated) "
            "conjugate phasor."
        ),
        practical_guidance=(
            "The defaults (3-term Blackman-Harris apodization, no zero-fill, Mertz "
            "phase correction) are a reasonable general starting point; increase "
            "`zero_fill` (e.g. to 2 or 4) to interpolate a smoother-looking peak "
            "without acquiring more data, and reserve boxcar apodization for cases "
            "where maximum resolution matters more than sidelobe suppression. This "
            "milestone handles one interferogram at a time (dims exactly `(opd,)`, "
            "real-valued); a hyperspectral interferometric cube and a complex "
            "(heterodyne-demodulated) interferogram are both deliberately out of "
            "scope for now."
        ),
        common_mistakes=(
            "Expecting this step to accept a hyperspectral interferometric cube "
            "(dims `(y, x, opd)`) or a complex-valued interferogram channel - both "
            "are explicitly out of scope for this milestone and are refused with a "
            "clear reason, not silently reshaped or coerced.",
            "Reading zero-fill as adding real spectral resolution - it only "
            "interpolates the existing information more finely (concept.apodization "
            "has the sidelobe-vs-resolution trade-off that genuinely limits "
            "resolution).",
        ),
        related_concepts=("concept.interferogram", "concept.apodization", "concept.point_spectrum"),
        related_manual_pages=("workspace.spectrum.fft_interferogram",),
        references=(_GRIFFITHS, _MERTZ, _HARRIS, _HUTH),
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
        related_manual_pages=("explorer.diagnostics",),
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
        related_manual_pages=("explorer.diagnostics",),
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
        related_manual_pages=("explorer.diagnostics",),
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
        related_manual_pages=("explorer.diagnostics",),
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
        related_manual_pages=("explorer.diagnostics",),
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
        related_manual_pages=("ai.scientific_briefing",),
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
        related_manual_pages=("ai.suggested_next_steps",),
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
        related_manual_pages=("ai.reasoning_and_provenance",),
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
        related_manual_pages=("ai.reasoning_and_provenance",),
    ),
)


#: The full initial library.
ARTICLES: tuple[Article, ...] = _CONCEPTS + _OPERATIONS + _DIAGNOSTICS + _AI


__all__ = ["ARTICLES"]
