# Point Spectrum Discovery

**Status:** Completed 2026-07-02. First real-data validation exercise for the
**second data modality** (point spectroscopy), mirroring `measurement-discovery.md`'s
role for the first (imaging). This document records what was observed when the real
point-spectroscopy sample was inspected, and whether the existing architecture
generalized to it. **It generalized without redesign.**

---

## The Question

CLAUDE.md's Phase 1 architecture (`DataKind`, `Capability`, `Dataset`, `Metadata`,
provenance) was designed from the start to anticipate more than imaging -
`docs/data-model.md` sec 2 already tabulated `SPECTRUM`, `LINE_SCAN`, `INTERFEROGRAM`,
and `HYPERSPECTRAL` `DataKind`s, and `core.dataset._derive_capabilities` already
derived `Capability.SPECTRAL` (`"wavenumber" in coords`) and `Capability.SPATIAL_1D`
(`"s" in coords`) - but no reader, Explorer view, or AI Scientist text had ever
produced or consumed them. This milestone's question: does that anticipated
architecture actually hold up against a **real** point-spectroscopy file, or does it
need to change?

## What Was Observed

The sample dataset's only point-spectroscopy measurement:

```
SNOM Sample Files/2026-06-16 14928/2026-06-16 212518 PH PSP CdO Dense ROI 2/
```

**It is not a single isolated spectrum.** The vendor's "Point Spectroscopy" mode, as
actually used for this acquisition, swept a tunable laser ("Piano") across a
wavenumber range **at 100 distinct spatial positions along a real 2 µm line** -
producing a spectrum at every position, not one spectrum total.

**Measurement parameters (from the `Spectra.txt` header):**

| Parameter | Value |
|---|---|
| Scan type | Point Spectroscopy (PsHet) |
| Sample | CdO nanoparticles (Dense ROI 2) |
| Positions | 100, along a 2 µm line (20 nm pitch) |
| Wavenumber sweep | 5920 - 6120 cm^-1, 1 cm^-1 steps, 201 points |
| Laser | Piano, MIR detector |
| Software version | 2.2.14109.0 |

**File format.** A single `<measurement> Spectra.txt`: the same `#`-prefixed vendor
header grammar as the imaging `.txt` (reused verbatim - see
`io/_neasnom_header.py`), followed by a tab-delimited table:

```
Row  Column  Omega  Wavenumber  Z          O0A       O0P  O1A  O1P  ...  O5A  O5P
0    0       0      5920        8.022e-07  64.53029  0    ...
0    0       1      5921        8.023e-07  63.12548  0    ...
...
0    99      200    6120        8.322e-07  67.45950  0    ...
```

`Row` is always 0 (a single line, not a 2-D area); `Column` indexes the 100 spatial
positions; `Omega`/`Wavenumber` index the spectral sweep (**verified identical at
every position**, columns 0/50/99 checked byte-for-byte); `Z` (height) genuinely
varies *within* one position's sweep, not just between positions - AFM feedback stays
active throughout, so it is stored as `(position, wavenumber)`, never reduced.

**A vendor side-export exists but is out of scope.** The directory also contains
ordinary-looking per-position GSF channel maps (`M.gsf`, `M0A.gsf` .. `M5P.gsf`,
`O0A.gsf` .. `O5P.gsf`, `Z.gsf`, all 100x1 - confirmed via their GSF headers:
`XRes=100, YRes=1, XReal=2E-6`, matching the `Spectra.txt` header's own geometry
independently). This reader does not ingest them; they are a possible future
companion-dataset increment, not silently discarded without comment (Rule 4).

## Empirically Verified: No Silent Misclassification, But a Routing Gap

Before writing the new reader, the *existing* imaging reader was run directly against
this real PSP directory to check for a possible scientific-correctness bug:

```
ReaderError: unrecognized channel token 'M' (...); this directory may be a
non-imaging neaSNOM modality not supported by neasnom.image.gsf.v1
```

It already **failed loud**, not silent - `io/neasnom.py` had a defensive comment
("some acquisitions name it `'<dir> Spectra.txt'` - a different modality") and its
`_group_channels` already rejected the bare `M` token. However, `io.registry.sniff()`
still **routed** this directory to the imaging reader id (it only checked for
`*.gsf` + `*.txt` + GSF magic, which this directory also has), so `io.read()` raised
instead of dispatching correctly. This was a real, if narrowly-scoped, bug this
milestone fixes: `sniff()` now content-checks for a `*Spectra.txt` file whose header
names "Point Spectroscopy" *before* the imaging check.

## Conclusion: No Architectural Redesign

Per the task's own instruction ("only propose architectural changes if the current
model genuinely cannot represent spectra; if changes appear necessary, stop and
explain why - do not redesign first"): **no such stop was needed.**

- `DataKind.SPECTRUM` (dims `(wavenumber,)`, a single position) and
  `DataKind.LINE_SCAN` (dims `(s, wavenumber)`, several positions along a line) were
  **already the documented target shapes** in `docs/data-model.md` sec 2, written
  before any reader existed. The new reader (`io/neasnom_spectrum.py`) selects
  between them purely by how many positions the real file actually has - zero new
  `DataKind`/`Capability` members.
- `Capability.SPECTRAL`/`SPATIAL_1D` were already derived correctly by
  `core.dataset._derive_capabilities` from the `wavenumber`/`s` coordinate names.
- The spatial axis of the line reuses `ScanInfo` as-is (`pixels=(100, 1)`), mirroring
  exactly how the vendor's own companion GSF side-export already represents it.
- **One small additive gap**, not a redesign: `Metadata` had no field for spectral-
  axis geometry (wavenumber range/sampling/point count) - the spectral analogue of
  `ScanInfo`. A `SpectralInfo` dataclass (default `None`) was added, following the
  exact pattern of `ScanInfo`; every existing imaging construction path is
  unaffected.

## A Real Correctness Bug the New Modality Surfaced

Extending `diagnostics.harmonic_diagnostics` to a genuinely different 2-D array shape
exposed a pre-existing gating bug rather than a new-modality-specific one:
`_classify_harmonic`'s spatial-coherence/SNR classification (validated in
`harmonic-ranking-analysis.md` **only for true `(y, x)` spatial images**) gated on
`amplitude.ndim == 2` alone. A `(position, wavenumber)` array is also 2-D, so it was
silently fed through the spatially-calibrated classifier - a scientifically invalid
result (mixing a spatial axis with a spectral one). Fixed by gating on
`Capability.SPATIAL_2D` instead of shape alone; a `(position, wavenumber)` array now
honestly reports `"unknown"`. A regression test (`test_diagnostics.py`) pins this
with a smooth synthetic field that *would* have classified "signal" under the old,
wrong gate. This is exactly the kind of finding the vertical slice was meant to
surface (Rule 1: scientific correctness first).

## What Was Built (additive only; see `LOG.md` for the full list)

- `core.metadata.SpectralInfo` (+ `Metadata.spectral`).
- `io/_neasnom_header.py`: the vendor `#`-header grammar, factored out of
  `io/neasnom.py` so the new reader reuses it rather than duplicating it.
- `io/neasnom_spectrum.py`: the new reader (`neasnom.spectrum.txt.v1`).
- `io/registry.py`: content-based `sniff()` routing fix (point-spectroscopy checked
  before the imaging GSF check).
- `describe.SpectralGeometryDescription` (+ `MetadataSummary.spectral`) - the
  `describe`/`diagnostics`/`ai.briefing` layers otherwise needed **no changes** to
  generalize: `describe_measurement`'s `dims`/`capabilities` are already axis-name-
  agnostic, and `topography_diagnostics`/`channel_statistics`/`histogram` already
  degrade to `None`/shape-agnostic correctly for a dataset with no `(y, x)` grid.
- `ai/briefing.py`: a spectral-range summary line; an honest "height recorded" line
  (not "roughness, profiles", which need `SPATIAL_2D`) when topography exists without
  a 2-D grid.
- `knowledge`: two new concept articles (`concept.point_spectrum`,
  `concept.spectral_axis`), explicit that this acquisition (direct wavenumber sweep,
  PsHet) is scientifically distinct from interferometric nano-FTIR.
- `gui/spectrumview.py` (`SpectrumPlotView`): a new pyqtgraph curve view, a 4th page
  in the Explorer's existing `QStackedWidget`, reusing the existing `ChannelBrowser`
  for channel/representation selection and adding a position selector (shown only for
  a `LINE_SCAN`).
- `gui/model.py`/`gui/window.py`: capability-gated dispatch (`is_spectral`) so the
  image-only affordances - Measure, Comparison, Contact sheet, GSF/figure export,
  cross-measurement comparison - are disabled with an honest message rather than left
  to crash for a spectral active measurement.

## Documented Scope Boundary (deliberate, not an oversight)

Per the milestone's explicit constraints ("not a spectroscopy feature sprint"):
- No spectral fitting, peak-finding, baseline correction, or new AI reasoning.
- No ingestion of the companion per-position GSF side-export.
- Measure (line/ROI), Comparison, Contact sheet, GSF channel export, and figure
  export remain image-only; a spectral measurement shows a friendly "not available"
  message for the export actions rather than attempting and failing. Zarr export
  (project save/reopen) works unchanged - the store is channel/dim-agnostic.
- Cross-measurement comparison excludes spectral measurements from the selection
  (the comparison viewer renders every pane through the image-only `render_spec`).

## Success Criteria (from the task brief) - all met

A researcher can open the real PSP measurement, see metadata (including a new
"Spectral axis" section), see its (single, `io.read`) provenance node, zoom/pan the
spectrum curve, switch channel/representation/position, read a Scientific Briefing
that states the spectral range/sampling and channels present, and reach the two new
Knowledge Center articles - all verified against the real sample file, with a live
(offscreen, screenshotted) window: opening the measurement, switching to phase
representation, and moving the position slider all worked, with the plotted curve
changing correctly at every step.
