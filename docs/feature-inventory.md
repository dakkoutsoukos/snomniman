# SNOMNIMAN - Implemented Feature Inventory

> **Status: analysis only (no code changes).** A point-in-time, evidence-based baseline
> of *what is actually built*, for planning future development. **Date:** 2026-06-29
> (post harmonic-signal-classification; 415 tests green; HEAD `f0b2887`).
>
> **Basis:** direct reading of `src/snomniman/**` and `tests/**`. Every claim is grounded
> in source. **Confidence convention:** each feature is *Confirmed in source code* unless
> tagged `[INFERRED]` or `[UNCERTAIN]`; Section 7 lists the exceptions. Per the project
> rule, where documentation and code disagreed, the **code** reality is reported.
>
> This is a snapshot and will age as code changes - re-derive it from source before
> trusting it for a new planning cycle. It does not propose work; the product/science
> backlogs live in `beta-readiness-v1.md` and `scientific-validation.md`.

---

## 1. Executive Summary

SNOMNIMAN is a **single-measurement, read-first desktop Explorer** for neaSNOM s-SNOM
imaging data, backed by a clean, fully Qt-free scientific core. Today a researcher can:
launch the app on one neaSNOM GSF measurement directory; browse channels grouped by
physical meaning; view any channel in physical units with honest contrast/colormap/scale
bar; compare channels side-by-side (synchronized) or as a harmonic contact sheet; read
typed metadata and the full provenance lineage; read a deterministic **Scientific
Briefing** with grounded **Suggested Next Steps**; take quantitative **line/region
measurements**; apply any of **five processing operations** through one generic,
preview-driven **Processing Workspace** (never mutating raw data); consult an in-app
**Knowledge Center**; and export a **provenance-bearing publication figure**.

The **backend is materially more complete than the GUI exposes.** A loss-less Zarr project
store (`read_zarr`/`write_zarr`) and a GSF writer exist but are **not wired into any GUI
action**. The `pipeline` (Project/replay) and `batch` packages are **docstring-only stubs
with no implementation**. The provenance DAG itself is implemented (in `core`). In its own
roadmap's terms the product is pre-beta: it loads -> inspects -> analyzes -> exports
*figures*, but **cannot export processed data, save/reopen a project, or open more than one
measurement per launch**.

**Scope reality:** one vendor format (neaSNOM GSF imaging), imaging only (no
spectra/nano-FTIR reader), one measurement at a time.

---

## 2. Complete Feature Inventory

### A. Application Shell & Entry

| Feature | Description | UI location | Source | Status / Limitations |
|---|---|---|---|---|
| GUI entry point | `python -m snomniman.gui [dir]`; folder chooser if no path | launch | `gui/app.py`, `gui/__main__.py` | Complete. Opens **exactly one** measurement; **no menu bar**, no File/Open/Recent (verified: no `QMenu`/`menuBar`/`QAction`). |
| Identity header | Title + "facts line" (kind, raw/derived, pixels, um field, cm^-1, detection, source, date, vendor) | top of window | `gui/window.py` `_facts_line`, `model.identity()` | Complete. |
| Conventions status bar | "nm - lower-left origin - phase as imported" | status bar | `gui/window.py`, `model.conventions_summary` | Complete. |
| Derivation history / Back | Linear stack; "Back to <title>" after an operation is accepted | view-controls row | `gui/window.py` `_history`, `_navigate_back` | Complete. In-session only; not persisted. |
| Dark theme | Configured pyqtgraph palette | global | `gui/app.py` `_configure` | Complete. Not user-configurable. |

### B. Measurement Loading & Data Model

| Feature | Description | UI | Source | Status / Limitations |
|---|---|---|---|---|
| neaSNOM GSF reader | Directory of `.gsf` + `.txt` -> validated `Dataset`; assembles complex `O{n}`/`M{n}=A*e^(iP)`, real `Z`, references `R_*` | open dialog | `io/neasnom.py`, `io/gsf.py` | Complete & golden-tested. **Only vendor reader.** |
| Reader registry + sniffing | Content-sniff (GSF magic + `.txt`) -> dispatch | internal | `io/registry.py` | Complete; **only `neasnom.image.gsf.v1` registered**. The Zarr store is deliberately *not* in the registry, so the GUI cannot open a saved project. |
| Canonical conventions | nm units; lower-left/x-right/y-up (GSF rows flipped, recorded); phase as imported | - | `io/neasnom.py` `_orient`, `_build_axes` | Complete (OHD-6). |
| Immutable Dataset | Read-only backing arrays; typed metadata; capabilities derived | - | `core/dataset.py` | Complete; raw-immutability enforced by freezing arrays. |
| Capability detection | SPATIAL_2D/1D, SPECTRAL, COMPLEX_OPTICAL/MECHANICAL, TOPOGRAPHY, REFERENCE, MULTI_HARMONIC | drives availability | `core/dataset.py` `_derive_capabilities`, `core/capabilities.py` | Complete. SPECTRAL/SPATIAL_1D are defined but no reader produces them. |
| Clean modality rejection | Point-spectra/PSP directories raise `ReaderError` rather than mis-read | error dialog | `io/neasnom.py`, golden test | Complete. |

### C. Metadata

| Feature | Description | UI | Source | Status / Limitations |
|---|---|---|---|---|
| Typed metadata model | Instrument, Excitation, Demodulation, ScanInfo, Acquisition, per-channel ChannelInfo, conventions, original units, **verbatim raw header** | - | `core/metadata.py` | Complete; missing values stored `None`, never guessed. |
| Metadata Inspector | 4-column tree (Field/Value/Unit/Source) in groups; each value tagged with origin (`.txt`/GSF/convention) | **Metadata** tab | `gui/panels.py` `MetadataInspector`, `model.metadata_sections` | Complete. **No search box; no copy button** beyond Qt text-selection. The verbatim vendor header is parsed/stored but **not surfaced** in the UI. |

### D. Image Visualization

| Feature | Description | UI | Source | Status / Limitations |
|---|---|---|---|---|
| Physical-units image | nm extent (um ticks), lower-left origin, aspect-locked | main view (Single) | `gui/imageview.py`, `viz/render.py` | Complete. |
| Representation honesty | Complex -> amplitude **or** phase; phase fixed to +/-pi, cyclic `twilight` map; topography `afmhot`; amplitude `viridis` | Representation toggle | `viz/render.py`, `gui/colormap.py` | Complete. Colormaps are fixed per kind; not user-selectable. |
| Colorbar + histogram | `HistogramLUTItem` with unit, value distribution | Single view | `gui/imageview.py` | Complete (full mode only). |
| Contrast controls | "Default" (robust 1-99 %) / "Full range" / exact min-max spinboxes with span-adaptive decimals | Single view | `gui/imageview.py`, `viz.level_range` | Complete. Display-only; never alters data. |
| Scale bar | Snaps to 1/2/5 x 10^k, ~20 % of field, nm/um label | image overlay | `viz.pick_scale_bar` | Complete. |
| Cursor readout | Hover -> x,y nm + current channel value (+ phase if complex + Z height) | under image | `model.cursor_readout`, `window._on_cursor_moved` | Complete. |

### E. Navigation / Comparison

| Feature | Description | UI | Source | Status / Limitations |
|---|---|---|---|---|
| Channel browser | Tree grouped Optical/Mechanical/Topography/References, sorted by harmonic; amp/phase toggle shown only when applicable | left dock | `gui/panels.py`, `model.channel_groups` | Complete. |
| Comparison view | Synced **zoom/pan + one crosshair** across panes; shared value readout; 4 presets: Amplitude/Phase, Optical/Topography, Sample/Reference, Harmonic series | **Compare** buttons | `gui/comparison.py`, `model.comparison_layout` | Complete. Presets degrade gracefully when channels absent. Preset-driven (no free-form layout). |
| Contact sheet | Thumbnail of every optical harmonic; click to open | **Contact sheet** button | `gui/comparison.py` `ContactSheet` | Complete. |
| Default channel pick | Opens O2 (best contrast), else higher harmonic, else Z | on load | `model._default_channel` | Complete. `[INFERRED behavior from code]` |

### F. Scientific Briefing & AI Scientist

| Feature | Description | UI | Source | Status / Limitations |
|---|---|---|---|---|
| Scientific Briefing | Deterministic fact sections: Summary / Observations / Enables - incl. tilt, roughness, **harmonic signal/noise**, invalid pixels | **Briefing** tab | `ai/briefing.py`, `gui/briefing.py` | Complete; facts only. |
| Suggested Next Steps | Ranked recommendation **cards** (strength badge, rationale, evidence, considerations, expected outcome) -> **Preview** into Workspace; **Learn more** | Briefing tab | `ai/recommend.py`, `ai/reasoning.py`, `gui/briefing.py` | Complete. **Two rules only**: level-dominant-tilt, normalize-with-reference. No rule for unwrap/line_flatten/crop (deferred by design). |
| Copy briefing | Facts + suggestions -> clipboard as text | "Copy briefing" button | `gui/briefing.py` `as_text` | Complete. |
| Narrative provider seam | `NarrativeProvider` protocol + grounded prompt builder; `MockNarrativeProvider` | "Interpretation (AI)" box | `ai/provider.py` | Seam only. **No real provider; none configured in the app** - the box always reports "no provider configured". |

### G. Analysis / Measurements (read-only)

| Feature | Description | UI | Source | Status / Limitations |
|---|---|---|---|---|
| Line profile | Draggable line; bilinear sampling; per-channel normalized curves + length/dx/dy | **Measure** tab | `gui/measurement.py`, `viz/measure.py`, `model.line_profile` | Complete. Profile plot normalizes each curve 0-1. |
| Rectangle stats | count, area, mean, median, min, max, std per visible channel | Measure tab | `viz.rect_mask`/`region_stats` | Complete. |
| Polygon stats | Even-odd ray-cast mask; same stats | Measure tab | `viz.polygon_mask` | Complete. |
| Measurement session | Rename / hide-show / delete / clear; multiple overlays; recompute on channel change; reports across current+phase+Z | Measure tab | `gui/measurement.py` | Complete. **Numbers cannot be exported** (no CSV/clipboard on the stats table). |
| Diagnostics panel | Topography (tilt x/y, range, roughness), Optical harmonics (amplitude, decay, **coherence + signal/noise class**), per-channel stats, operation applicability (+ "needs ...") | **Diagnostics** tab | `diagnostics/*`, `model.diagnostics_report` | Complete. |

### H. Processing (derivations; raw never mutated)

| Feature | Description | UI | Source | Status / Limitations |
|---|---|---|---|---|
| Generic Processing Workspace | Registry-driven list (grouped, with "unavailable" + reason), **auto-built parameter form**, Preview -> "what changes / what stays / provenance to be recorded" -> Accept/Cancel | **Process** tab | `gui/process.py`, `model.operation_catalog`/`preview_operation` | Complete. New ops appear with zero GUI code. Single-input only (`{"primary": ds}`). |
| `image.plane_level` | Subtract fitted polynomial surface (order N) from a real channel | Workspace | `processing/image/plane_level.py` | Complete (params: channel, order). |
| `image.line_flatten` | Per-scan-line median/mean/poly baseline removal | Workspace | `processing/image/line_flatten.py` | Complete (params: method, channel, order). |
| `image.reference_normalize` | Complex division O{n}/R_O{n} | Workspace | `processing/image/reference_normalize.py` | Complete (no params; needs COMPLEX_OPTICAL+REFERENCE). |
| `image.phase_unwrap` | New continuous-phase channel (sequential 1-D unwrap) | Workspace | `processing/image/phase_unwrap.py` | Complete (param: channel). |
| `image.crop` | Restrict to nm rectangle, preserve absolute coords | Workspace | `processing/image/crop.py` | Complete (x/y min/max). |
| Provenance recording | Every op -> new Dataset with StepRecord (id, version, params, software, deterministic) referencing inputs | Provenance tab | `processing/step.py`, `core/provenance.py` | Complete. |

### I. Provenance & Reproducibility

| Feature | Description | UI | Source | Status / Limitations |
|---|---|---|---|---|
| Provenance DAG | Multi-input nodes, serialize/deserialize, software-version capture | **Provenance** tab | `core/provenance.py` | Implemented in **core** (despite the `pipeline` docstring claiming to own it). |
| Provenance Inspector | Plain-language summary + node tree (deterministic flag, sources w/ sha256, params, software) | Provenance tab | `gui/panels.py`, `model.provenance_steps` | Complete. |
| Description API | Qt-free structured projection (channels, metadata summary, geometry, lineage, operation catalogue) | feeds GUI/AI | `describe/*` | Complete (pure projection; ADR-0018). |

### J. Export

| Feature | Description | UI | Source | Status / Limitations |
|---|---|---|---|---|
| Publication figure export | PDF/PNG/SVG of Single / Comparison / Harmonic-series / Measurement (with profile subplot); scale bar, colorbars, measurement overlays | "Export figure..." | `gui/window.py`, `viz/figure.py` | Complete. |
| Figure provenance sidecar | `<figure>.provenance.json` (full `FigureSpec` + human caption) -> **regenerable** | written beside figure | `viz/figure.py` `export`, `render_from_record` | Complete. |
| **Data export** | Save processed dataset (Zarr/GSF) | - | `io/zarrstore.py`, `io/gsf.write_gsf` | **Backend exists, NOT in GUI.** No "Export data" action (beta blocker C1). |

### K. Knowledge Center

| Feature | Description | UI | Source | Status / Limitations |
|---|---|---|---|---|
| Article base | Curated concepts, one per operation, diagnostics (incl. harmonic signal/noise), AI philosophy | **Knowledge** tab | `knowledge/library.py` | Complete; integrity + no-drift tested. |
| Browse / search / cross-link | Category tree, live search, `QTextBrowser` with internal links | Knowledge tab | `gui/knowledge.py`, `knowledge/query.py` | Complete. |
| "Learn more" deep-links | From Workspace + recommendation cards -> operation article | Process/Briefing | `window._on_operation_learn_more` | Complete. **Only operations deep-link**; diagnostics rows/harmonics do not (mechanism is generic but unwired). |

### L. Persistence (backend only)

| Feature | Source | Status |
|---|---|---|
| Zarr project store (loss-less round-trip) | `io/zarrstore.py` | **Implemented, unused by GUI.** |
| GSF writer | `io/gsf.py` `write_gsf` | Implemented; used in tests/fixtures, not in GUI. |

---

## 3. Hidden / Non-obvious Features

- **Figure regeneration from a sidecar** - `viz.render_from_record` rebuilds a figure from
  its `.provenance.json`. No UI; backend/scriptable only.
- **Preview "diff" engine** - the "what changes / what stays" summary is computed
  *generically* by diffing datasets (`model._diff_summary`), incl. added-channel
  provenance and phase-re-reference detection - not hand-written per operation.
- **"Why unavailable" explanations** - disabled operations show the exact missing
  capability or "no eligible channel for X" (`model._blocked_reason`).
- **Capability-filtered channel pickers** - operation channel parameters auto-filter to
  real/complex channels of *this* dataset (`model._channels_for_role`).
- **Synchronized multi-pane cursor + linked zoom/pan** across comparison panes
  (`imageview.link_view`, `comparison.set_crosshair`).
- **Span-adaptive contrast precision** - spinbox decimals/step scale to the value range
  (`imageview._configure_spinboxes`).
- **Workspace lock during preview** - catalogue + form disable while a preview is pending
  (`process.set_preview_mode`).
- **Verbatim vendor header is captured** in metadata but **never displayed** (parsed in
  `neasnom._parse_param_file`, stored in `raw_header`).
- **`MockNarrativeProvider`** - a working, network-free narrative path exists for
  tests/demos but is not wired into the app.
- **Amplitude-/phase-only fallback** - a channel with only A or only P loads as a real
  channel (`neasnom._assemble_channel`).

---

## 4. Scientific Capabilities (implemented)

1. **Complex near-field reconstruction** - `O{n}=A*e^(iP)`, `M{n}` from paired GSF;
   amplitude/phase as derived views (`core/dataset.py`, `io/neasnom.py`).
2. **Convention normalization** - nm conversion, lower-left reorientation, phase preserved
   as imported (`io/neasnom.py`).
3. **Topography geometry** - least-squares plane slope (per um), height range, detilted RMS
   roughness (`diagnostics/diagnose.py`).
4. **Harmonic amplitude/decay** - mean amplitude + decay ratio per order.
5. **Harmonic signal-vs-noise classification** - spatial coherence + single-image
   Immerkaer SNR -> signal/weak/noise/empty, validated on both branches
   (`diagnostics/diagnose.py`; `docs/harmonic-ranking-analysis.md`).
6. **Channel statistics** - finite-aware min/max/mean/std/range, invalid-pixel counts;
   amplitude view for complex.
7. **Plane leveling** & **per-line flattening** (deterministic baseline removal).
8. **Reference normalization** - complex division by reference.
9. **Phase unwrapping** - sequential 1-D (residue-free regime).
10. **Crop** - coordinate-preserving spatial restriction.
11. **Quantitative measurement** - bilinear line profiles, rectangle/polygon region
    statistics, physical areas.
12. **Deterministic reasoning** - grounded recommendations for leveling &
    reference-normalization (`ai/reasoning.py`).
13. **Operation applicability** - capability-based, computed without execution.

**Deliberately *not* present (validated deferrals):** auto-recommendation for phase-unwrap,
line-flatten, crop; "best-harmonic" ranking; any SNR beyond the validated single-image
harmonic estimate (per `docs/phase-wrapping-analysis.md`, `docs/harmonic-ranking-analysis.md`).

---

## 5. User Workflow Coverage

**Load - [COMPLETE].** Launch on one neaSNOM GSF directory (folder chooser). *Stops at:*
one measurement per launch (no multi-open/Recent); only neaSNOM GSF imaging; cannot reopen
a saved project.

**Inspect - [COMPLETE] (strongest area).** Browse grouped channels; amplitude/phase;
physical-units view with colorbar/contrast/scale-bar/cursor; compare (4 presets, synced)
and contact sheet; metadata; full provenance; deterministic Briefing; Knowledge. *Stops
at:* verbatim header not shown; metadata not searchable.

**Analyze - [COMPLETE].** Diagnostics (tilt, roughness, harmonic signal/noise,
applicability); line/region measurements; five processing operations via previewed,
provenance-recorded derivations; grounded suggestions. *Stops at:* measurement numbers
can't be exported; only 2 of 5 ops auto-recommended (by design); no
histogram/FFT/filtering/background-subtraction tools.

**Export - [PARTIAL].** Publication figures (PDF/PNG/SVG) **with regenerable provenance**.
*Stops hard here:* **cannot export the processed dataset** (Zarr/GSF backend unused),
**cannot save/reopen a project** (no DAG persistence in GUI), **cannot export measurement
tables**.

**Net:** a researcher can fully *understand, measure, reproducibly process, and publish a
figure of* one measurement - but **cannot keep their processed results or numbers**, which
is the decisive gap before a real workday.

---

## 6. Missing Major Capability Categories (gaps only)

- **Data/result export** - no processed-data save from the GUI (backend exists, unwired).
- **Project save/reopen** - no DAG serialization to/from disk in the GUI; the Zarr store is
  not openable via the reader path.
- **Multi-measurement sessions** - no File/Open/Recent; one dataset per launch.
- **Batch/headless analysis** - `snomniman/batch` is an **empty stub**.
- **Pipeline/Project/replay** - `snomniman/pipeline` is an **empty stub** (no `Project`, no
  replay engine).
- **Spectral / nano-FTIR / hyperspectral** - no reader, no spectral viewer (capability enum
  exists; nothing produces it).
- **Image processing toolbox** - no FFT/filtering, masking, background subtraction, drift
  correction, alignment/stitching, height zero/offset.
- **Measurement export** - region/profile tables not exportable (CSV/clipboard).
- **Histogram analysis tools** - a histogram is *shown* for contrast, but there are no
  histogram measurement/threshold tools.
- **Segmentation / feature detection / ROI libraries** - none.
- **Quantitative material modeling** - no dielectric/finite-dipole fitting, spectral fitting.
- **Real AI narration** - provider seam only; no concrete model integration.
- **Configuration/preferences** - **no settings system at all** (no `QSettings`, no
  settings file), no colormap/theme/keybinding customization.
- **Annotation/reporting**, **undo/redo** (only linear back through derivations), **session
  persistence**.

---

## 7. Confidence Assessment

**Confirmed in source code (this review):** Section 2 (A-L), Section 3, Section 4, Section
5, and Section 6 - all read directly from the named files. This includes the high-impact
negatives, each verified rather than assumed:

- No menu/Open/multi-measurement, no settings - *verified by absence of
  `QMenu`/`menuBar`/`QAction`/`QSettings` in a repo-wide grep.*
- `pipeline`/`batch` are stubs - *verified: both `__init__.py` are docstring-only; no
  classes/functions.*
- Zarr/GSF writers exist but aren't GUI-wired - *verified: only two `QFileDialog` call
  sites (open-dir, save-figure); the registry registers only the neaSNOM reader.*
- Five operations / two reasoning rules - *verified by grep of
  `step_id`/`required_capabilities` and `@register_rule`.*

**Confirmed via tests (corroborating, not just docs):** harmonic signal/noise
classification, golden neaSNOM load, Zarr round-trip, knowledge no-drift.

**Inferred from implementation (logic clear, runtime not executed):**

- Default-channel selection (O2 -> higher -> Z) and graceful preset degradation - read from
  `model.py` branches, not run.
- Exact rendered appearance of figures/thumbnails - code is unambiguous but not visually
  executed here.

**Uncertain / not line-verified this review:**

- `gui/colormap.py` `lookup_table` and `gui/diagnostics.py` `DiagnosticsPanel` internals -
  inferred from call sites, not opened. `[UNCERTAIN - low risk]`
- `describe/summarize.py` function bodies (`describe_operations`, `summarize_provenance`) -
  inferred from consumers and `describe/descriptors.py`. `[INFERRED]`
- `core/provenance.py`, `core/rawsource.py`, `core/units.py`, `io/gsf.py` internals -
  inferred from their public use across many files that were read; signatures/behavior are
  consistent but not line-verified. `[INFERRED - high confidence]`

No claim here rests on documentation alone; doc-sourced descriptions were cross-checked
against code, and where docs and code diverged (e.g., the `pipeline` docstring claiming to
"define the provenance DAG"), the **code** reality is reported.

---

## See also

- [`beta-readiness-v1.md`](beta-readiness-v1.md) - the product roadmap; maps the Export/
  multi-measurement gaps to beta blockers C1-C4.
- [`scientific-validation.md`](scientific-validation.md) - the scientific methodology; the
  validated-capability deferrals in Section 4.
- [`architecture.md`](architecture.md) - the layer/module structure these features sit in.
