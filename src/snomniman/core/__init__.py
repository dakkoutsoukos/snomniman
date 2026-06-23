"""snomniman.core - the data model (no I/O, no processing, no GUI).

Defines the central ``Dataset`` abstraction (an ``xarray``-backed, SNOM-aware
container), ``DataKind`` + capability descriptors (hybrid dispatch), typed
``Metadata`` (which carries scientific conventions explicitly), ``RawSource``,
unit conventions (canonical spatial unit: nm), and provenance value objects
(``StepRecord``, ``History``) for the multi-input provenance DAG.

Depends on nothing else inside ``snomniman`` (the base of the dependency graph).
See ``docs/data-model.md``.
"""
