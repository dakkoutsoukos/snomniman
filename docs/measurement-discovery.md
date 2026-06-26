# Measurement Discovery

**Status:** Completed 2026-06-23. First real-data validation exercise before Phase 1 implementation.
**Last updated:** 2026-06-23

This document records what was observed when a real neaSNOM measurement dataset was
inspected for the first time. It is a historical record; the findings below have been
incorporated into the authoritative docs (`architecture.md`, `data-model.md`,
`roadmap.md`, `decisions.md`). No architecture decisions were changed.

---

## What Was Observed

A complete measurement run from a neaSNOM instrument was inspected at:

```
SNOM Sample Files/2026-06-16 14928/2026-06-16 190234 PH CdO Dense ROI 2/
```

**Measurement parameters (from the .txt parameter file):**

| Parameter | Value |
|---|---|
| Scan type | 2D (PsHet - pseudo-heterodyne) |
| Sample | CdO nanoparticles (Dense ROI 2) |
| Scan area | 10 µm x 10 µm |
| Pixels | 150 x 150 |
| Laser | Piano, MIR detector |
| Target wavenumber | 5,973 cm^-1 |
| Tip frequency | 263,293 Hz |
| Tapping amplitude | 53.1 nm |
| Software version | 2.2.14109.0 |

**Measurement directory structure:**

```
2026-06-16 190234 PH CdO Dense ROI 2/
  O0A raw.gsf  O0P raw.gsf
  O1A raw.gsf  O1P raw.gsf
  O2A raw.gsf  O2P raw.gsf      <- primary near-field signals
  O3A raw.gsf  O3P raw.gsf
  O4A raw.gsf  O4P raw.gsf
  O5A raw.gsf  O5P raw.gsf
  M0A raw.gsf  M0P raw.gsf
  ...
  M5A raw.gsf  M5P raw.gsf
  R-O0A raw.gsf  R-O0P raw.gsf  <- reference channels (R- prefix)
  ...
  R-O5A raw.gsf  R-O5P raw.gsf
  R-M0A raw.gsf  R-M0P raw.gsf
  ...
  R-M5A raw.gsf  R-M5P raw.gsf
  Z raw.gsf  Z C.gsf  Z H.gsf  Z CH.gsf       <- topography variants
  R-Z raw.gsf  R-Z C.gsf  R-Z H.gsf  R-Z CH.gsf
  2026-06-16 190234 PH CdO Dense ROI 2.txt    <- instrument parameters
  2026-06-16 190234 PH CdO Dense ROI 2.html   <- summary
  2026-06-16 190234 PH CdO Dense ROI 2.gwy    <- Gwyddion export
  Images/
```

**GSF file format (Gwyddion Simple Field 1.0):**

```
Gwyddion Simple Field 1.0\n
XRes=150
YRes=150
XOffset=5.581E-05
YOffset=9.164E-06
XReal=9.999E-06
YReal=1.00E-05
XYUnits=m
ZUnits=
<NUL byte, padded to next 4-byte boundary>
<float32 binary data, row-major, XRes x YRes values>
```

File size for a 150x150 channel: 90,332 bytes (332-byte header + 90,000 bytes of float32 data = 150*150*4). Format confirmed by binary inspection.

**Channel naming convention (observed):**
- `O` = optical near-field; `M` = mechanical (cantilever); `Z` = topography
- Number suffix = harmonic order (0, 1, 2, 3, 4, 5)
- `A` = amplitude; `P` = phase (both raw, as imported)
- `R-` prefix = reference channel (used for normalization)
- Topography suffixes: `raw`, `C` (corrected?), `H` (height?), `CH`

The naming convention is consistent with the canonical channel names in `data-model.md`.

---

## What Assumptions Were Confirmed

1. **neaSNOM produces imaging datasets** with distinct optical, mechanical, and
   topography channels. OHD-9 (first reader = real neaSNOM imaging dataset) confirmed.
2. **Channels are real-valued amplitude and phase separately** (not interleaved complex).
   The reader must assemble complex channels from `O{n}A` + `O{n}P` pairs, as specified
   in `data-model.md` (ADR-0002): `O{n} = O{n}A * exp(i * O{n}P)`.
3. **Reference channels are present** at the same harmonic orders as the signal channels,
   enabling sample/reference normalization as a natural operation (multi-input DAG node,
   OHD-2).
4. **Multiple harmonic orders are available** (0-5), matching the `O{n}` / `M{n}` naming
   scheme in `data-model.md`.
5. **Metadata comes from two sources:** per-channel GSF headers (pixel count, physical
   extent in meters, offsets) and the `.txt` parameter file (instrument params: laser,
   tip frequency, tapping amplitude, demodulation mode, software version, etc.).
6. **Spatial units in the GSF header are meters** (`XYUnits=m`); canonical conversion
   to nm is required on import (OHD-6B).
7. **Phase is stored as-imported** (raw values); no silent normalization or inversion
   is applied by the instrument software. OHD-6D is directly confirmed.
8. **The scan was 150x150 pixels over 10 µm x 10 µm** - well within the expected
   range for a near-field imaging measurement.
9. **The project has four measurement runs** in the sample folder, providing redundancy
   and multiple golden-file candidates.

---

## What Assumptions Were Corrected

**Assumption 1 (corrected): The neaSNOM reader would read an HDF5 file via h5py.**

- What was assumed: "vendor HDF5 read via h5py" appeared in `architecture.md` section 3,
  the tech stack table, `data-model.md` section 10, `decisions.md` ADR-0009/OHD-3, and
  `phase0-readiness.md`.
- What was observed: the neaSNOM measurement format is **GSF (Gwyddion Simple Field)**,
  a plain-binary format with a text header. No HDF5, no h5py required for this reader.
- Status: all affected docs updated. `h5py` is retained in `pyproject.toml` as it may
  be needed for other vendor formats in later phases; it is not removed.

**Assumption 2 (corrected): The reader would ingest a single vendor file.**

- What was assumed: `RawSource.path` pointed to a single file; the "golden file"
  was described as a single file to provide.
- What was observed: a neaSNOM measurement is a **directory** containing one `.gsf`
  file per channel. There is no single monolithic measurement file.
- Consequence for Phase 1: the reader accepts a measurement directory, discovers
  all `.gsf` channel files within it, reads the `.txt` parameter file for instrument
  metadata, and assembles a `Dataset`.
- Consequence for `RawSource`: `path` in the Phase 1 implementation will be the
  measurement directory rather than a single file. The sha256 anchor may hash the
  directory manifest (file names + per-file hashes) or the `.txt` parameter file.
  This is an implementation detail resolved in Phase 1, not a new architecture
  decision.

---

## Impact on Phase 1

**No architecture redesign required.** The corrections above are format details:

- The `snomniman.io` reader registry, `ProcessingStep`, `Dataset`, `Metadata`, and
  provenance schemas are all format-agnostic and require no changes.
- The `RawSource` schema is unchanged; `path` pointing to a directory is a
  valid instantiation of the existing design.
- The dependency on `h5py` is unchanged (it stays in `pyproject.toml` for future use).
- The canonical channel names, units conventions, and complex-assembly rule are
  unchanged and correctly anticipated in `data-model.md`.

**Phase 1 is now fully unblocked.** The measurement data is present at
`SNOM Sample Files/`. Implementation can proceed in the planned order:

1. `snomniman.core.Dataset` (+ `DataKind`/capabilities)
2. `Metadata` schema
3. Provenance DAG schema
4. GSF measurement-directory reader (`snomniman.io`)
5. Golden-file tests against the real data

**One implementation detail to resolve in Phase 1** (not a new decision):
how `RawSource` anchors a measurement directory (directory path + per-file hash
manifest, or directory path + `.txt` hash as the entry-point fingerprint).

---

## Why No Architecture Redesign Is Required

The core architecture is format-agnostic by design. The reader registry (ADR-0006)
exists precisely to isolate vendor format details from the rest of the stack.
Changing the first reader from "HDF5 single file" to "GSF measurement directory"
is entirely contained within one reader implementation and does not affect:

- the `Dataset` / `Metadata` / `Provenance` schemas
- the `ProcessingStep` ABC or registry
- the provenance DAG or replay engine
- the `viz`, `batch`, or `gui` layers
- any settled OHD (OHD-1..9)
- any ADR (0001..0017)

The format change is a validation finding, not a design flaw. The architecture was
designed to accommodate multiple vendor formats from the start.
