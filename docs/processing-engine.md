# Processing Engine

**Status:** Implemented. **Last updated:** 2026-06-28

The processing engine is the generic framework that every future scientific
derivation in SNOMNIMAN will use. It establishes the pattern once, so that
leveling, reference normalization, filtering, phase unwrapping, masking,
cropping, drift correction, and AI-assisted derivations all fit the same
machinery - and every one of them is auditable, replayable, and reproducible.

---

## Processing philosophy

> "Everything is a derivation of an immutable measurement."

A processing operation is a recorded transformation: given one or more input
Datasets and a set of parameters, it produces a new Dataset. The inputs are
never modified. The output's provenance graph records *exactly* what was done
and references its inputs, making the transformation fully auditable.

Three consequences flow from this:

1. **Raw data is sacred.** No operation modifies an existing Dataset or its
   backing arrays. "Apply leveling" always produces a *new* Dataset; the
   original remains untouched.

2. **Every operation is explicit.** Phase operations (invert, re-reference,
   unwrap, normalize) are always recorded steps - never silent transformations
   (OHD-6D). Unwrapped phase is a first-class channel produced only by an
   explicit, recorded operation (OHD-4).

3. **Provenance is structural, not optional.** The provenance DAG is not
   audit-trail metadata appended afterwards; it is built by `apply()` itself,
   so there is no path through the processing engine that bypasses recording.

---

## Operation lifecycle

A single processing step passes through four phases:

```text
1. Define      Subclass ProcessingStep; set step_id, version, description,
               deterministic; implement param_specs() and _execute().

2. Register    Call register(MyStep) (or use it as a decorator). The step
               becomes discoverable via get_step("my.step_id").

3. Instantiate MyStep(param1=value1, ...)
               __init__ calls validate(), which checks types, required
               params, and unknown names; raises ProcessingError on failure.

4. Apply       step.apply({"primary": dataset})
               Calls _execute() to produce the raw xr.Dataset + kind +
               metadata; then builds the StepRecord + ProvenanceNode;
               then constructs and returns the new, frozen Dataset.
```

The returned Dataset is immediately frozen (arrays read-only). Its
provenance node records: `step_id`, `step_version`, `deterministic`,
`params` (a JSON-serializable dict), `applied_at` timestamp, `software`
versions (snomniman, numpy, scipy, xarray, zarr), and `inputs` (a mapping
of input-name → input's ProvenanceNode).

---

## Parameter system

Each operation declares its parameters via `param_specs()`, returning a
list of `ParameterSpec` objects:

```python
@dataclass(frozen=True)
class ParameterSpec:
    name: str
    description: str
    py_type: tuple[type[Any], ...]   # accepted Python types for isinstance()
    required: bool = True
    default: Any = None              # used when required=False
    choices: tuple[Any, ...] | None = None   # fixed allowed values (an enum)
    channel_role: str | None = None          # marks a str param as naming a channel
```

`ProcessingStep.validate()` enforces these rules:

- **No unknown names** - any key not in `param_specs` raises `ProcessingError`.
- **Correct type** - `isinstance(value, spec.py_type)` must hold.
- **In `choices`** - if `choices` is set, a value outside it raises `ProcessingError`.
- **Required params present** - missing required params raise `ProcessingError`.

`params` returned by `validate()` (and stored as `step.params`) must be
JSON-serializable Python scalars (str, int, float, bool, None). No NumPy
scalars, no ndarrays. This constraint keeps the provenance DAG fully
serializable without any special encoding.

### Declarative UI hints (`choices`, `channel_role`)

`choices` and `channel_role` are optional, declarative hints that let a *generic*
parameter editor build the correct control with **no operation-specific code** -
they never change an operation's computed result:

- `choices` - a fixed set of allowed values (e.g. `image.plane_level`'s
  `order=(1, 2, 3)`). A consumer renders a selector; `validate()` also enforces it.
- `channel_role` - one of `CHANNEL_ANY` / `CHANNEL_REAL` / `CHANNEL_COMPLEX`
  (`snomniman.processing`). It marks a `str` parameter as naming a channel of that
  kind, so a consumer can offer a channel picker filtered to the channels the
  operation accepts (`image.plane_level.channel` is `real`;
  `image.phase_unwrap.channel` is `complex`). The dataset is not available at
  `validate()` time, so the operation still validates the chosen channel in
  `_execute`; `channel_role` only drives the *form*.

Why on `ParameterSpec` and not in the GUI: which channels an operation can accept
is *scientific* knowledge, and Rule 4 keeps such knowledge out of GUI code. The
operation declares it as data; the Description API projects it
(`OperationParameter.choices` / `.channel_role`); the Explorer's Processing
Workspace consumes it. See "Processing Workspace" below.

---

## Preview model

The engine has no special preview state - it is purely functional, so a preview is
just an `apply()` whose result has not been committed. To preview a step, the caller:

1. Builds the step from the registry with the chosen params.
2. Calls `step.apply({"primary": dataset})` to produce the derived Dataset.
3. Renders it (and, in the Explorer, diffs it against the current dataset to
   summarise what changes).
4. If the researcher accepts, that *same* derived Dataset is committed; if they
   cancel, it is simply discarded.

This is exactly what the Explorer's Processing Workspace does (the live dataset is
small enough to apply in full). There are no "preview mode" flags, callbacks, or
side channels: the backend knows nothing about preview vs commit. Previewing on a
spatially-cropped slice first (identical behaviour, less compute) is a future
optimisation for large/hyperspectral data, not a change to this contract.

---

## Provenance integration

Every `apply()` call builds a `ProvenanceNode` that:

- References its named input nodes (enabling multi-input derivations such as
  sample/reference normalization or background subtraction).
- Records a `StepRecord` with step_id, version, params, software versions,
  and a UTC timestamp.
- Assigns a UUID as `node_id` (unique across every call to `apply()`).

The resulting provenance DAG is serializable with `serialize_dag()` /
`deserialize_dag()` (from `snomniman.core`) and is stored in the canonical
Zarr project store alongside the data.

**Multi-input example.** The first registered multi-input operation is
`image.arithmetic` (ADR-0030), which combines one channel of two measurements
(`image.reference_normalize` is single-input because signal and reference share one
measurement):

```python
step = get_step("image.arithmetic")(channel="Z", mode="a_minus_b")
result = step.apply({"primary": dataset_a, "secondary": dataset_b})
# result.provenance.inputs == {
#     "primary":   dataset_a.provenance,
#     "secondary": dataset_b.provenance,
# }
```

The DAG serializes this multi-input structure without losing any edge - it was a
multi-parent DAG from the start (OHD-2), so no schema change was needed; a derived
two-parent dataset reopens with both parents and both raw sources intact. The result
lives in the *primary* measurement's history (the secondary input is referenced by
provenance, not owned).

---

## Registered operations (the scientific vocabulary)

The engine is intentionally small; the *vocabulary* is what grows. Each registered
operation is a verb the whole system gains at once - it appears automatically in the
Description API's operation catalogue, in the Diagnostics Engine's applicability
report, and in the AI Scientist's briefing, with **no changes to those layers**
(verified by tests). Implemented in `snomniman.processing.image`:

| step_id | required capabilities | what it does |
|---|---|---|
| `image.plane_level` | `spatial_2d` | Subtract a fitted polynomial **surface** (order 1-3: plane / paraboloid / cubic) from a real channel. |
| `image.line_flatten` | `spatial_2d` | Subtract an independent **per-scan-line** baseline (median / mean / polynomial order 1-3) from a real channel - removes line-to-line offset/slope striping that a single global surface fit cannot. Complementary to `image.plane_level`. |
| `image.reference_normalize` | `complex_optical`, `reference` | Divide each complex optical signal channel by its matching reference (`O{n} / R_O{n}`); amplitude becomes a ratio, phase a difference (explicit, recorded re-reference - OHD-6D). Single-input (signal + reference share one measurement). |
| `image.phase_unwrap` | `spatial_2d` | Add an unwrapped-phase channel `{channel}_phase_unwrapped` for a complex channel; raw phase untouched (OHD-6D), unwrapped phase is its own channel (OHD-4). 2-D unwrap = sequential `numpy.unwrap` (x then y): exact for smooth fields, can mis-handle true 2-D residues (documented limitation; no extra dependency). |
| `image.crop` | `spatial_2d` | Restrict every channel to a rectangular nm region; coordinates sliced (absolute positions preserved), scan geometry updated. |

**On the two flattening verbs (Rule 2):** `image.plane_level` and
`image.line_flatten` are deliberately *distinct* operations, not a duplicated pair.
`image.plane_level` fits **one global polynomial surface** (orders 1-3: plane /
paraboloid / cubic), removing sample tilt and broad bow. `image.line_flatten`
removes an **independent per-scan-line** baseline (median / mean / polynomial),
removing the line-to-line offset/slope striping a single surface cannot represent
(median is the robust default; the methodology is standard SPM row-leveling -
Gwyddion "Align Rows", WSxM). A separate `image.polynomial_flatten` is *not* added:
it would merely duplicate `image.plane_level`. The two real verbs are complementary
- line-flatten to remove striping, plane-level to remove global tilt. (Validated on
the real CdO scan: plane leveling leaves ~70% of the per-line baseline spread, which
line flattening removes; see the operation's tests.)

**Explorer exposure.** Every operation is usable through the engine (`apply`), is
first-class in Description/Diagnostics/AI, **and is exposed in the Explorer's
Processing Workspace automatically** (see below) - no per-operation GUI code.

---

## Processing Workspace (the one generic GUI surface)

The Explorer exposes *every* registered operation through a single, registry-driven
**Processing Workspace** (`snomniman.gui.process.ProcessingWorkspace`, fed by the
Qt-free `ExplorerModel`). There is **no operation-specific UI**: adding a step makes
it appear with discoverability, a parameter editor, preview, provenance preview, and
accept/cancel - for free.

Everything the workspace shows is a projection of the engine + the dataset:

- **Discovery & grouping** - the operation list comes from `describe_operations()`,
  grouped by step_id namespace (`image.*` -> "Image"), titled from the step_id
  (`image.plane_level` -> "Plane Level").
- **Availability & "why unavailable"** - from the Diagnostics Engine's
  `operation_applicability` (capability test); unavailable operations stay visible
  and explain which capabilities the measurement lacks.
- **Parameter form** - generated from each `ParameterSpec`: numbers -> spin boxes,
  `bool` -> checkbox, `choices` -> a selector, `channel_role` -> a channel picker
  filtered (real/complex) for the current dataset. No hardcoded layouts.
- **Preview / Accept / Cancel** - identical for every operation. The model runs
  `step.apply({"primary": dataset})` on the live dataset (the engine is purely
  functional; previewing is just applying without committing), then **diffs** the
  derived dataset against the current one to report, generically, *what will change*
  (recomputed/added/removed channels, field-of-view changes, channel-state and
  phase-reference changes) and *what stays the same*. Before/after panes reuse the
  comparison view.
- **Provenance preview** - the exact `StepRecord` (step_id, params, input dataset)
  that Accept will record; Accept simply adopts the previewed derived dataset.

The raw measurement is never mutated: a preview is a throwaway derived Dataset, and
Accept records a new node in the provenance DAG (the original remains reachable via
the Explorer's history). Multi-input operations are not yet surfaced in the form (no
registered operation is multi-input today); when one exists, the workspace gains an
auxiliary-input picker - the rest of the flow is unchanged.

---

## Extension model

To add a new operation:

1. **Create the class** in the relevant sub-package (`image`, `common`, or a
   new domain sub-package). Subclass `ProcessingStep`.

2. **Set the four class variables:**
   - `step_id`: dot-namespaced, stable identifier (e.g. `"image.plane_level"`).
     Never change a published step_id; create a new one with a new version if
     behaviour changes.
   - `version`: start at 1; bump on every behaviour change.
   - `description`: one sentence for the UI and provenance panel.
   - `deterministic`: `True` iff identical params + input → bit-identical output.

3. **Declare parameters** via `param_specs()` (return `[]` for no params).

4. **Implement `_execute(inputs)`**, which receives the named input Datasets
   and returns `(xr.Dataset, DataKind, Metadata)`. Rules:
   - Never modify any input Dataset or its backing arrays.
   - Return a fresh xr.Dataset with valid coordinates for the output kind.
   - Access validated params via `self._params`.

5. **Register** the class by calling `register(MyStep)` at module import
   time (or use it as a `@register` decorator).

6. **Write tests:**
   - A known-answer test validating the computation (Rule 6).
   - A non-mutation test confirming the input Dataset is unchanged after apply.
   - A provenance test confirming the step_id and params are recorded.

7. **Add a Knowledge Center article** for the operation (the no-drift invariant,
   ADR-0024, requires one article per registered operation).

**Multi-input operations (ADR-0030).** A single-input step needs none of this - it
inherits the default `"primary"` slot. To consume **more than one** Dataset:

- **Declare the input slots** via `input_specs()` (an `InputSpec(name, description)`
  per slot - the dataset counterpart of `ParameterSpec`). The slot names are the keys
  of the `inputs` mapping. By convention `"primary"` is the active measurement; extra
  slots become dataset pickers in the Workspace (candidates supplied by the window).
- **Declare compatibility** via `check_compatibility(inputs) -> tuple[str, ...]` -
  return one human-readable reason per problem (e.g. mismatched dimensions / units /
  missing channel), or `()` if the inputs combine. `apply` enforces it (raises
  `ProcessingError`); the GUI surfaces the reasons and disables Preview. **Never
  silently resample or align** - refuse instead (registration is a separate, explicit
  operation). See `image.arithmetic` for the worked example.
- A multi-parent result is appended to the **primary** measurement's history but
  records every input in its provenance DAG; persistence and the provenance inspector
  need no special handling (the DAG was multi-input from the start).

**Template:**

```python
from snomniman.processing import ParameterSpec, ProcessingStep, register

@register
class PlaneLevel(ProcessingStep):
    step_id = "image.plane_level"
    version = 1
    description = "Remove a fitted plane from the topography channel."
    deterministic = True

    @classmethod
    def param_specs(cls) -> list[ParameterSpec]:
        return [
            ParameterSpec("channel", "Channel to level.", (str,)),
        ]

    def _execute(self, inputs):
        primary = inputs["primary"]
        channel = self._params["channel"]
        # ... fit and subtract plane ...
        return new_xr_dataset, primary.kind, primary.metadata
```

---

## Dependency rules

`snomniman.processing` depends on `snomniman.core` only. It never imports
`snomniman.gui`, `snomniman.viz`, `snomniman.pipeline`, `snomniman.io`, or
any Qt library. This is enforced by the CI Qt-free invariant
(`tests/test_smoke.py::test_backend_is_qt_free`).

---

## What is NOT in the processing engine

- **Scientific algorithms.** The engine is machinery only. Algorithms
  (leveling, normalization, etc.) live in operation sub-packages
  (`processing.image`, `processing.common`, etc.) as concrete steps.
- **GUI.** No widget, dialog, or event handler lives here.
- **AI.** AI inference steps will use the same `ProcessingStep` pattern,
  but with `deterministic=False` and a `model_id` parameter. The AI
  layer is not yet designed.
- **Pipeline replay / DAG persistence.** DAG serialization is in `snomniman.core`
  (`serialize_dag`/`deserialize_dag`); DAG traversal and replay are
  `snomniman.pipeline`'s responsibility (future).
- **Preview state.** Preview is purely GUI-side; the engine is functional.
