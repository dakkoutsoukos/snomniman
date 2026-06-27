# The Scientific Diagnostics Engine (`snomniman.diagnostics`)

> Status: **implemented** (ADR-0019). Qt-free backend; consumed today by the
> Measurement Explorer's Diagnostics panel; a future client is the AI Scientist.

## Philosophy

The processing engine performs deterministic scientific **operations** (it
transforms a measurement into a new, provenance-bearing measurement). The
diagnostics engine performs deterministic scientific **observations** (it measures
properties *of* a measurement and reports numbers). A future AI Scientist will
**reason over those observations** - and it must never re-derive a fact from raw
arrays when a deterministic algorithm can establish it.

This is the load-bearing distinction:

> **Every scientific operation is deterministic. Every scientific observation is
> deterministic. Only the interpretation is left to (reviewable, optional) AI.**

The engine produces **facts, not opinions**. It makes no recommendations, calls no
LLM, and knows nothing about providers or prompts. "This scan is tilted by
3.8 nm/um" is a diagnostic; "you should plane-level it" is an interpretation that
belongs to a later, explicitly-reviewable layer.

## Position in the architecture

```
gui            -> consumes all backend layers
batch          -> pipeline, io, core
pipeline       -> processing, core
describe       -> processing, core      (projection: what the core already knows)
diagnostics    -> processing, core      (computation: measured facts about a dataset)
processing     -> core
io             -> core
viz            -> core
core           -> (nothing internal)
```

`diagnostics` and `describe` are **siblings**, both depending on `processing` + `core`
and both consumed by `gui`/`batch`/(future) `ai`:

- `describe` is a **pure projection** - it reports structure the core already holds
  (kind, channels, conventions, lineage, the operation catalogue) and performs *no*
  scientific computation (ADR-0018).
- `diagnostics` performs **computation** - slope, roughness, statistics, amplitude
  decay - and returns the numbers.

`describe` does **not** consume `diagnostics` (that would smuggle computation into the
projection layer and break ADR-0018). Consumers compose the two: the Explorer shows
the description *and* the diagnostics; the AI will be handed both.

It is Qt-free (Rule 4), never mutates a dataset (Rule 4/Reproducibility), and adds
nothing to the provenance DAG - reading a diagnostic is not an operation.

## Descriptors (outputs)

All are frozen, typed, and JSON-serializable via `to_dict` (mirroring `describe`).

| Descriptor | What it reports |
|---|---|
| `ChannelStatistics` | Per channel: count, finite/invalid counts, min/max/mean/std, dynamic range. Complex channels are summarized by their amplitude view (`view="amplitude"`); phase is cyclic and deliberately not summarized this way (OHD-6D). |
| `TopographyDiagnostics` | Plane slope (x/y and magnitude, per micrometre), height range, and RMS roughness after plane removal, for the real topography channel. |
| `HarmonicDiagnostics` / `HarmonicAmplitude` | Optical signal harmonics present, mean amplitude each, and the decay ratio vs the next-lower order. |
| `OperationApplicability` | Per registered step: whether it structurally applies (declared capabilities ⊆ dataset capabilities), which capabilities are missing, and whether it already appears in the provenance DAG. |
| `MeasurementDiagnostics` | The aggregate: minimal identity (`title`, `is_raw`) plus all of the above. Deliberately does **not** repeat the structural summary - that is `describe`'s job. |

## Functions (entry points)

- `channel_statistics(dataset, name)`
- `topography_diagnostics(dataset)` - `None` if there is no real topography channel or no 2-D scan
- `harmonic_diagnostics(dataset)` - `None` if no optical signal harmonic is present
- `operation_applicability(dataset)` - reads the registry; caller imports the op sub-packages
- `diagnose(dataset, *, title=None)` - the full report

## Scientific choices and honest limitations

- **Slope / roughness** use an ordinary least-squares plane over the finite pixels.
  Slopes are reported per micrometre (the natural SNOM tilt scale) in the height
  unit. Roughness is the residual standard deviation after plane removal (an
  Sq-like measure with global tilt removed). Validated against synthetic planes
  with exact known slopes (`tests/test_diagnostics.py`).
- **No SNR.** A genuine signal-to-noise ratio needs a noise model or a signal-free
  region; neither is available deterministically from a single image. Reporting a
  number anyway would violate Rule 6. The **amplitude-decay ratio** is reported
  instead - a measurable, convention-free proxy for harmonic confidence.
- **No clipping / saturation / drift (yet).** Clipping needs the instrument's
  ADC/dynamic-range limit (often absent from metadata); drift from a single image
  is ill-posed. These are deferred rather than guessed. Invalid (NaN/inf) pixel
  counts *are* reported, since those are unambiguous.
- **Applicability is structural, not advisory.** `applicable=True` means the dataset
  has the capabilities the step declares - not that the step is a good idea. Whether
  to apply it is an interpretation for the user (and, later, the AI).

## Extension model

Add a diagnostic by:

1. Adding a frozen, `to_dict`-able descriptor in `descriptors.py`.
2. Adding a pure function in `diagnose.py` that computes it (no mutation, no AI).
3. Wiring it into `diagnose` and, if user-facing, into
   `ExplorerModel.diagnostics_report` (the GUI formats; the backend computes).
4. Adding a **known-answer** test (synthetic/analytical/real CdO). No heuristic
   assertions - if you cannot state the exact expected value, the diagnostic is not
   yet deterministic enough to ship.

Make a step's applicability computable by declaring its `required_capabilities`
on the `ProcessingStep` subclass (e.g. `image.plane_level` requires
`Capability.SPATIAL_2D`).

## Relationship to the future AI Scientist

The AI Scientist is **not** part of this milestone. When it arrives it will consume
`describe` (structure) + `diagnostics` (facts) and produce *reviewable
recommendations*, which the deterministic processing engine alone executes. Building
diagnostics first means the AI reasons over validated observations instead of
inferring facts from pixels - a system that is both more reliable and easier to
explain. See `CLAUDE.md` (AI Architecture Principles).
