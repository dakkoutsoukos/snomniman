# Data Model

**Status:** Phase 0 complete; all OHD decisions applied. **Last updated:** 2026-06-23

Authoritative description of how near-field data, metadata, and processing history
are represented in SNOMNIMAN. The conventions here are settled scientific
decisions (see `decisions.md`, ADR-0014 / OHD-6); they are explicit and travel
with every dataset.

---

## 1. Principles

1. **A near-field dataset is a labeled N-D array.** Named dimensions, physical
   coordinates, per-array units, and rich metadata - represented with `xarray`
   (ADR-0001).
2. **Raw is immutable.** A loaded raw `Dataset` is never modified in place;
   processing returns new `Dataset`s (Rule 5, ADR-0004).
3. **Amplitude and phase are one complex quantity; unwrapped phase is its own
   channel.** Optical (and optionally mechanical) channels are stored as complex
   `s * e^(i*phi)` where both exist (ADR-0002); amplitude/phase are derived views.
   **Unwrapped phase is a first-class channel** (OHD-4) produced only by an
   explicit, recorded operation. **Phase is preserved exactly as imported** - no
   silent invert/re-reference/unwrap/normalize (OHD-6D).
4. **Nothing from the instrument is silently discarded.** The full original
   header is preserved verbatim alongside the typed metadata.
5. **Conventions are explicit, stored in metadata, and travel with the data**
   (ADR-0014 / OHD-6A). Every array declares its units; the dataset declares its
   coordinate convention; convention changes are recorded, never silent.

## 2. DataKind + capabilities (hybrid dispatch, OHD-8)

`DataKind` gives a **human-facing classification**; **capabilities** (which named
axes/channels a dataset has) **determine which operations apply**. Operations
declare capability requirements (e.g. "needs a 2D spatial grid", "needs a
`wavenumber` dim"); `DataKind` drives UX and defaults (ADR-0017).

| `DataKind` | Dims (typical) | Per-pixel/point content | Example |
|---|---|---|---|
| `IMAGE` | `(y, x)` | multi-channel 2D maps | s-SNOM amplitude/phase map |
| `LINE_SCAN` | `(s,)` or `(s, wavenumber)` | 1D spatial profile | line across an interface |
| `APPROACH_CURVE` | `(z,)` | signal vs tip-sample distance | near-field decay |
| `INTERFEROGRAM` | `(opd,)` | raw signal vs optical path diff. | nano-FTIR before FFT |
| `SPECTRUM` | `(wavenumber,)` | complex spectrum vs wavenumber | nano-FTIR point spectrum |
| `HYPERSPECTRAL` | `(y, x, wavenumber)` | spectrum per pixel | nano-FTIR hyperspectral cube |

New modalities (pump-probe delay, polarization, discrete-line spectral imaging,
approach-curve maps) add capabilities/axes without enum-driven core edits.

## 3. The `Dataset` abstraction

`snomniman.core.Dataset` wraps an `xarray.Dataset` and adds domain semantics. Each
**channel** is an xarray data variable; **coordinates** are shared axes; metadata
lives in a typed `Metadata` object (mirrored into `attrs` for persistence).
Processing **history** is the node's entry in the provenance DAG.

```text
Dataset
  kind:         DataKind            # human-facing classification
  capabilities: set[Capability]     # drives operation dispatch (OHD-8)
  data:         xarray.Dataset
                  variables: one per channel   (e.g. Z, O2, O3, O2_uphase, M1, ...)
                  coords:    one per dimension  (e.g. x, y, wavenumber, opd, z)
  metadata:     Metadata            # typed; conventions explicit; + verbatim raw header
  source:       RawSource | None    # provenance anchor (None for synthetic)
  history:      ProvenanceNode      # this dataset's node in the DAG (empty for raw)
```

**Why per-channel variables (not a `channel` dimension):** channels differ in
dtype (complex optical vs real topography) and meaning; xarray variables model
this cleanly and keep units/attrs per channel (ADR-0003). Keep `Dataset` a genuine
boundary: prefer typed accessors over exposing the raw `xarray.Dataset` widely.

## 4. Channels and canonical names

Vendor channel labels are mapped to **canonical internal names** on import; the
original labels are kept in metadata. Harmonic order `n` is an integer
(0, 1, 2, 3, 4, ...).

| Canonical | Meaning | dtype | Units | Notes |
|---|---|---|---|---|
| `Z` | topography / height | real | nm | from AFM feedback |
| `M{n}` | mechanical (cantilever) harmonic n | complex | a.u. (amp), rad (phase) | e.g. `M1`; amp drives feedback |
| `O{n}` | optical near-field harmonic n | complex | a.u. (amp), rad (phase) | `O2`,`O3`,`O4` are the useful near-field orders |
| `O{n}A` / `O{n}P` | amplitude / phase **views** of `O{n}` | real | a.u. / rad | derived, not stored separately |
| `O{n}_uphase` | **unwrapped** phase of `O{n}` | real | rad | first-class channel; only via an explicit unwrap step (OHD-4) |
| `R{...}` / error / aux | retrace, error signal, etc. | real | context | preserved if present |

**Complex assembly:** when a reader provides `O{n}A` and `O{n}P` separately, they
are combined into one complex variable `O{n} = O{n}A * exp(i * O{n}P)`.
Amplitude-only channels (e.g. some `O0A` used purely for normalization) remain
real. Accessors `dataset.amplitude("O2")` / `dataset.phase("O2")` return views.
**Phase is preserved exactly as imported (OHD-6D):** invert/re-reference/unwrap/
normalize are explicit, provenance-recorded operations; unwrapping produces a
stored `*_uphase` channel. Each channel carries an explicit **state**
(raw / referenced / normalized / unwrapped).

## 5. Dimensions, coordinates, and units

Conventions are stored explicitly per array (ADR-0014). Conversions are explicit
functions in `snomniman.core.units` and, when applied to data, are recorded in
provenance.

**Canonical length/spatial unit = nanometers (nm)** (OHD-6B). Original units
(e.g. um) are preserved in metadata; any conversion is recorded in provenance.

| Dimension | Symbol | Canonical unit | Notes |
|---|---|---|---|
| lateral X | `x` | nm | fast scan axis |
| lateral Y | `y` | nm | slow scan axis |
| scan distance | `s` | nm | line scans |
| tip-sample distance | `z` | nm | approach curves |
| optical path difference | `opd` | nm | interferograms |
| wavenumber | `wavenumber` | cm^-1 | spectra / hyperspectral (spectral, not length) |

| Quantity | Canonical unit | Notes |
|---|---|---|
| height | nm | |
| optical/mechanical amplitude | a.u. | dimensionless ratio once referenced (state tracked) |
| phase | rad | preserved as imported; reference/sign in metadata; degrees only for display |
| integration time | s | |

**Canonical coordinate convention (OHD-6C):** **origin = lower-left; x increases
to the right; y increases upward.** Vendor coordinate systems are preserved in
metadata; any transformation to the canonical convention is explicit and recorded
in provenance. A rotated scan grid is represented by an explicit affine
(origin + pixel size + rotation + axis directions), not by 1-D coordinate vectors.

## 6. `Metadata`

A typed container holding the conventions (explicitly), a stable core schema, and
the preserved raw header. Missing values are explicit (`None`), never guessed.

```text
Metadata
  data_kind:     DataKind
  conventions:   { spatial_unit: "nm", origin: "lower-left",
                   x_dir: "right", y_dir: "up",
                   phase_unit: "rad", phase_reference, phase_sign }   # OHD-6
  instrument:    { vendor, model, software_version }
  excitation:    { source_type, wavenumber_cm1?, wavelength_nm?, power? }
  demodulation:  { harmonics: [int], detection: pseudoheterodyne|homodyne|... }
  scan:          { size_nm?, center_nm?, rotation_deg?, pixels?, affine? }  # imaging
  interferometer:{ mirror_velocity?, spectral_resolution_cm1?, zero_fill?, apodization? }
  acquisition:   { datetime?, integration_time_s?, tapping_amplitude_nm?, setpoint? }
  channels:      [ ChannelInfo{ canonical, vendor_label, units, dtype, state } ]
  original_units:{ ... }   # vendor units before conversion to canonical
  raw_header:    { ... }   # verbatim original header/attributes, untouched
  schema_version: int
```

`raw_header` is treated strictly as **data** (injection-safe), never executed.
**Metadata and calibration corrections are provenance-tracked operations**
(OHD-7 / ADR-0016): editing a wavenumber calibration or a phase reference is a
recorded step, never a silent mutation, so "reproduce from raw + provenance"
remains true. `schema_version` supports migrations.

## 7. `RawSource`

The reproducibility anchor - an immutable description of where data came from.

```json
{
  "path": "data/2026-06-16 190234 PH CdO Dense ROI 2",
  "sha256": "a1b2...",
  "reader": "neasnom.image.gsf.v1",
  "reader_params": { "channel_map": "default" },
  "bytes": 1048576,
  "imported_at": "2026-06-22T12:00:00Z"
}
```

The hash lets replay verify the raw file is unchanged before reconstructing a
result. Paths are stored relative to the project root (plus size) to support
relinking moved/renamed files. `source` is `None` for synthetic datasets (which
record their generator parameters in provenance).

**Note on the neaSNOM GSF reader:** a neaSNOM measurement is a **directory** of
per-channel `.gsf` files, not a single file. For the GSF measurement-directory
reader, `path` is the measurement directory. The sha256 anchor strategy (directory
manifest vs. `.txt` entry-point hash) is an implementation detail resolved in Phase 1.

## 8. Provenance: DAG, `StepRecord`, `ProvenanceNode`

Provenance is a **DAG** (OHD-2): a step may take multiple named inputs, each
resolving to another `(RawSource + sub-graph)` - this represents sample/reference
normalization, background subtraction, calibration inputs, and stitched scans.
For full traceability (OHD-5) the graph records data sources, steps, parameters,
and software + operation versions.

```json
{
  "step_id": "image.plane_subtract",
  "step_version": 1,
  "deterministic": true,
  "inputs": { "primary": "<node-id>" },
  "params": { "channel": "Z", "order": 1 },
  "applied_at": "2026-06-22T12:01:02Z",
  "input_fingerprint": "sha256:...",
  "output_fingerprint": "sha256:...",
  "software": { "snomniman": "0.1.0", "numpy": "2.x", "scipy": "1.x", "xarray": "2025.x", "zarr": "2.x" },
  "notes": null
}
```

A normalization step, for example, has `inputs: { "sample": ..., "reference": ... }`.
Each step declares `deterministic` (see invariants and ADR-0013).

## 9. Project serialization

A **Project** is the serialized provenance **DAG** plus its referenced sources,
metadata, and (later) view state. Replaying the DAG reconstructs every derived
dataset. Raw files are **referenced, never copied** (ADR-0009).

### Project / graph JSON (sketch)

```json
{
  "schema_version": 1,
  "name": "polariton_study_2026",
  "sources": [
    { "id": "src_sample", "path": "data/sample.gsf", "sha256": "a1b2...", "reader": "neasnom.image.v1" },
    { "id": "src_ref",    "path": "data/ref.gsf",    "sha256": "c3d4...", "reader": "neasnom.image.v1" }
  ],
  "nodes": [
    { "id": "n1", "step_id": "io.read",          "inputs": { "source": "src_sample" }, "params": {} },
    { "id": "n2", "step_id": "io.read",          "inputs": { "source": "src_ref" },    "params": {} },
    { "id": "n3", "step_id": "image.normalize",  "inputs": { "sample": "n1", "reference": "n2" }, "params": {"channel": "O2"} }
  ],
  "snomniman_version": "0.1.0",
  "environment": { "python": "3.13", "numpy": "2.x", "scipy": "1.x", "xarray": "2025.x", "zarr": "2.x" }
}
```

Schema versions are explicit so formats can evolve with migrations.

## 10. Persistence formats

| Artifact | Format | Notes |
|---|---|---|
| Canonical dataset store | **Zarr** (OHD-3) | complex-native, chunked, JSON attrs; suits large cubes + rich metadata. One per dataset |
| Project (a session: datasets + derived + state) | **`.snomproj` bundle** (ADR-0027) | a directory of per-dataset Zarr stores + a `project.json` manifest |
| Provenance DAG / project metadata | JSON | human-readable, diffable, version-controllable |
| Manifest | JSON | raw sources (relative path + sha256 + bytes + reader) |
| Vendor file reading | format-specific readers | Phase 1: GSF measurement directories (neaSNOM); h5py for future HDF5-based formats; vendor formats are independent of the store |
| Exported figures | PDF/SVG/PNG (matplotlib) | vector for publication; provenance sidecar |
| Exported dataset | Zarr (loss-less) / GSF (one real grid + `.provenance.json`) | the whole dataset, or one channel/representation for Gwyddion/neaPLOT |
| Exported measurement | CSV / clipboard TSV | line profiles + region statistics, with a provenance header and physical units |

Raw vendor files are **never overwritten or modified**. A project bundle embeds the
*dataset arrays* (so a session reopens without the vendor files) while still
referencing each raw source by path + sha256.

**Canonical store layout (implemented in `snomniman.io.zarrstore`).** A `Dataset`
is written with `write_zarr` and reconstructed with `read_zarr`. The labeled
arrays go through `xarray.Dataset.to_zarr` (Zarr stores complex64 channels,
per-array units/attrs, dtypes, and dimensions natively). The SNOMNIMAN-level
semantics that are not plain array data - the `DataKind`, the typed `Metadata`
(with its explicit conventions and verbatim header), the provenance DAG, and the
`RawSource` anchor - are serialized into one JSON document held under the reserved
Zarr **group attribute** `"snomniman"` (format marker `snomniman.dataset`, with a
`schema_version`). The capability set and the amplitude/phase views are *derived
on load* (pure functions of the array data), never stored, so they cannot drift.
Stores are written `consolidated=False` (Zarr v3 spec) and loaded eagerly, so the
reconstructed arrays are frozen and immutable exactly as on first import.

**Project bundle layout (implemented in `snomniman.pipeline`, ADR-0027).** A whole
analysis session is a `Project` (the datasets oldest-to-newest, a `current_index`,
and an opaque `session` document). `save_project` writes a `<name>.snomproj`
directory: `datasets/dataset_NN.zarr` (one canonical store per dataset, reusing
`write_zarr`) plus `project.json` (format marker `snomniman.project`, a
`schema_version`, the dataset order, `current_index`, and the `session` blob, which
`pipeline` stores verbatim - the GUI uses it for view/layout and measurement state).
`load_project` restores each dataset with `read_zarr`, so the full provenance DAG and
raw immutability come back intact; the processing history is preserved because it
lives inside each dataset's store, not in the manifest.

## 11. Invariants (enforced by tests)

- A raw `Dataset` loaded from a `RawSource` has empty history and is never mutated
  by any operation.
- Every processing step returns a new `Dataset` whose provenance node is the
  inputs' graph plus exactly one `StepRecord`.
- `Dataset -> Zarr -> Dataset` round-trips data, coordinates, units, conventions,
  and metadata without loss; `Project -> .snomproj -> Project` round-trips every
  dataset (with its provenance DAG), the active selection, and the session state.
- Replaying the provenance DAG on unchanged `RawSource`s reproduces the recorded
  result; for steps declared **deterministic** on a matching environment, output
  fingerprints match bit-for-bit; otherwise results reproduce to a documented
  numerical tolerance.
- Complex channels satisfy `amplitude == abs(O)` and `phase == angle(O)`; an
  unwrapped-phase channel exists only if produced by an explicit unwrap step.
- No coordinate or channel is unitless unless explicitly dimensionless; spatial
  coordinates are in nm (with original units preserved in metadata).

See [`architecture.md`](architecture.md) for how these types are used and
[`decisions.md`](decisions.md) for rationale and the OHD closure.
