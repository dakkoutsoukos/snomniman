# Scientific Description API

**Status:** Implemented. **Last updated:** 2026-06-26

`snomniman.describe` is a Qt-free, **read-only** backend layer that projects the
scientific core and the processing registry into structured, typed,
JSON-serializable *descriptors*. It is the one canonical place that answers, for
any measurement:

- What kind of measurement is this? Is it raw or derived?
- What channels exist, and what does each one hold?
- What are its dimensions, capabilities, and active scientific conventions?
- Where did the data come from, and what was done to it (the lineage)?
- What processing operations are registered, and what parameters do they take?

It performs **no scientific computation** and **never mutates** its inputs. It
reports what the core already knows, in a shape that is easy to consume, compare,
serialize, store, and display.

---

## Why this exists (and why now)

This layer exists because it improves **today's** architecture, not because a
future AI might use it. Several present-day consumers each need the same
structured answers and would otherwise re-derive them independently:

- the **Measurement Explorer** (identity, channels, lineage),
- **publication / provenance export** (what a figure is derived from),
- future **reports** and a future **CLI**,
- **debugging** (a one-call structured dump of any dataset),
- **tests** (assert against a stable, structured projection).

A future **AI** layer is simply one more client of the same API. That is the
point: by building the description seam now, for reasons that stand on their own,
every future processing operation and every future AI capability inherits a mature,
tested way to understand a measurement - without an architectural redesign and
without coupling the core to AI.

This ordering is deliberate. AI should arrive *after* there is something
interesting to reason about (a richer set of processing operations) and *after*
the description seam exists - so AI never has to be retrofitted into the core, and
never has to grow its own private view of the data.

> The consumer is not "future AI"; the consumer is everything that needs a
> structured description of a measurement. AI just happens to be one of those
> consumers later.

---

## What it is not

- **Not** an AI layer, a chatbot, a prompt builder, or an LLM client. It contains
  zero AI concepts. (When AI is built, it will *consume* this API.)
- **Not** a "Knowledge Layer" or "Reasoning Layer". It does no reasoning; it
  produces structured facts. It is named for what it does.
- **Not** a presentation layer. It reports honest values - `None` where a value is
  genuinely unknown, never an `"unknown"` placeholder. Turning `None` into a word,
  choosing colours, or grouping for a sidebar are *presentation* choices that
  belong to a consumer (e.g. the Explorer's view-model).
- **Not** a second copy of `Metadata`/provenance. It is a *summary/projection*: it
  curates the salient fields and deliberately omits bulk (e.g. the verbatim vendor
  header). The full objects remain the source of truth.
- **Not** a place that mutates anything or bypasses provenance.

---

## Position in the architecture

```text
gui      batch      (future) ai          <- consumers of describe
   \        \         /
    \        \       /
     +----- snomniman.describe -----+     <- Scientific Description API
     |   depends on: core, processing |
     +--------------------------------+
              |            |
              v            v
        processing       core
              |            |
              +---> core <-+
```

- **Depends on** `core` (Dataset, Metadata, provenance, RawSource, capabilities)
  and `processing` (the step registry, for the operation catalogue) - nothing else.
  It sits at the same tier as `pipeline`.
- **Consumed by** `gui`, `batch`, the future `ai` layer, reports, and tests.
- **Not consumed by `viz`.** `viz` is intentionally `core`-only (it must stay below
  `processing`), so it keeps building its own figure-provenance record directly
  from the `Dataset`. `describe` is for consumers that already sit above
  `processing`.
- **Qt-free** (Rule 4), enforced by `tests/test_smoke.py::test_backend_is_qt_free`
  (the package is in `BACKEND_PACKAGES`).

---

## The descriptors (`snomniman.describe.descriptors`)

All are frozen dataclasses with a `to_dict()` that returns a JSON-ready dict
(tuples become lists; nested descriptors become nested dicts).

| Descriptor | What it captures |
|---|---|
| `ChannelDescription` | one channel: kind/role/harmonic, complex?, dtype, state, units, available views (`amplitude`/`phase` or `value`) |
| `ConventionsDescription` | the conventions in force (OHD-6): unit, origin, axes, phase unit/reference/sign, `phase_handling = "as imported"` |
| `GeometryDescription` | scan geometry in canonical nm (pixels, size, pixel size, offset, center, rotation) |
| `MetadataSummary` | a curated projection of `Metadata` (instrument/excitation/demodulation/acquisition salient fields + geometry + conventions + original units); omits the verbatim header |
| `SourceDescription` | a raw origin: edge name, path, filename, sha256, reader, directory?, bytes |
| `LineageStep` | one provenance node: step id/version, deterministic?, params, software, applied_at, input edge names, sources, raw? |
| `ProvenanceSummary` | raw? + step count + ordered `LineageStep`s + distinct sources |
| `OperationParameter` | one operation parameter: name, description, accepted type names, required?, default |
| `OperationDescription` | a registered operation: step id/version/description/deterministic + parameter schema |
| `MeasurementDescription` | the top-level aggregate: title, kind, raw?, dims, capabilities, channels, metadata summary, provenance summary |

---

## The functions (`snomniman.describe.summarize`)

| Function | Returns |
|---|---|
| `describe_channels(dataset)` | `tuple[ChannelDescription, ...]` (in data order) |
| `summarize_metadata(metadata)` | `MetadataSummary` |
| `summarize_provenance(node)` | `ProvenanceSummary` (walks the DAG topologically) |
| `describe_operations()` | `tuple[OperationDescription, ...]` (the registry catalogue) |
| `describe_operation(step_id)` | `OperationDescription` (raises `ProcessingError` if unknown) |
| `describe_measurement(dataset, *, title=None)` | `MeasurementDescription` (the aggregate) |

Each is a pure projection. `describe_measurement` is the convenient one-call entry
point; the others exist for consumers that need one facet.

---

## Relationships

### To the `Dataset` (and `core`)
`describe` reads a `Dataset` through its public accessors (`kind`, `capabilities`,
`channel_names`, `is_complex`, `metadata`, `provenance`, `data.sizes`). It adds no
state and holds no reference after returning - the descriptors are plain data.

### To the Measurement Explorer
The Explorer's `ExplorerModel` view-objects (`MetadataSection`, `ProvenanceStep`,
...) are **presentation-tier**: formatted strings, `"unknown"` placeholders, GUI
grouping. `describe`'s descriptors are **data-tier**. They are siblings at
different altitudes, not duplicates. The Explorer's provenance view already sources
its *facts* from `summarize_provenance` and formats the *words* itself - the
intended split: the backend owns the facts, the GUI owns the wording. Other view
sections may converge on `describe` over time where it reduces real duplication.

### To the Processing Engine
`describe_operations()` reflects whatever is registered in
`snomniman.processing`'s step registry. The caller imports the operation
sub-packages it cares about first (e.g. `import snomniman.processing.image`),
exactly as the GUI and the future pipeline replay engine do. `describe` **does not
modify the processing engine** and registers nothing itself.

### To a future AI layer
The future `ai` layer will consume these descriptors (and the JSON they emit) as
its grounding context, and will record its own outputs as provenance nodes (per the
AI principles in `CLAUDE.md`). Because the descriptors are structured and
serializable, AI context, report content, and Explorer state can all be built on
the same honest projection. No part of `describe` anticipates AI beyond being clean,
structured, and stable.

---

## Honest limitations (recorded, not hidden)

- **Per-dataset operation applicability is shallow.** `describe_operations()`
  lists the *catalogue*; it does not yet answer "which of these apply to *this*
  dataset?" with precision, because `ProcessingStep` does not declare its required
  capabilities as data (e.g. `PlaneLevel` enforces "real-valued channel" inside
  itself). Deepening this means steps declaring `required_capabilities`, a separate
  refinement to the processing engine that is intentionally **out of scope** here
  (this layer consumes; it must not modify the engine). When that lands,
  `describe` can join the capability set to the catalogue without an API redesign.
- **Summary, not archive.** `MetadataSummary` omits the verbatim vendor header and
  other bulk. Consumers needing everything read `Dataset.metadata` /
  `Metadata.to_dict()` directly.

---

## Extension model

To expose a new facet:

1. Add a frozen descriptor in `descriptors.py` with a `to_dict()` returning a
   JSON-ready dict (reuse `_jsonify`).
2. Add a pure projection function in `summarize.py` that reads only `core` /
   `processing` and constructs the descriptor. No computation, no mutation.
3. Export both from `__init__.py`.
4. Add tests: a projection test on the synthetic dataset (and golden where
   relevant), a JSON round-trip, and - for any function touching a `Dataset` - the
   cardinal non-mutation assertion.

Keep the layer honest: if a value is unknown, report `None`; if a fact requires
computation, it belongs in `processing` (as a recorded step), not here.
