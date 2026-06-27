# Processing Engine

**Status:** Implemented. **Last updated:** 2026-06-26

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
```

`ProcessingStep.validate()` enforces three rules:

- **No unknown names** - any key not in `param_specs` raises `ProcessingError`.
- **Correct type** - `isinstance(value, spec.py_type)` must hold.
- **Required params present** - missing required params raise `ProcessingError`.

`params` returned by `validate()` (and stored as `step.params`) must be
JSON-serializable Python scalars (str, int, float, bool, None). No NumPy
scalars, no ndarrays. This constraint keeps the provenance DAG fully
serializable without any special encoding.

---

## Preview model

The engine has no special preview state. To preview a step before committing,
the caller:

1. Creates a spatially-cropped copy of the input Dataset (a sliced xr.Dataset
   wrapping a new xarray.Dataset slice).
2. Calls `step.apply({"primary": cropped})` to produce the preview result.
3. Renders the result.
4. If the researcher accepts, calls `step.apply({"primary": full_dataset})`.

`apply()` on a small slice is identical in behaviour to `apply()` on the full
data - the engine is purely functional. There are no "preview mode" flags,
callbacks, or side channels.

This means the GUI preview layer is entirely in the GUI (future work). The
backend knows nothing about preview vs commit.

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

**Multi-input example** (reference normalization, future):

```python
step = ReferenceNormalize(harmonic=2)
result = step.apply({
    "sample":    dataset_sample,
    "reference": dataset_reference,
})
# result.provenance.inputs == {
#     "sample":    dataset_sample.provenance,
#     "reference": dataset_reference.provenance,
# }
```

The DAG serializes this multi-input structure without losing any edge.

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
