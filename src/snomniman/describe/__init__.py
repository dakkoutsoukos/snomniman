"""snomniman.describe - the Scientific Description API (depends on core + processing).

A Qt-free, **read-only** layer that projects the scientific core (``Dataset``,
``Metadata``, the provenance DAG, ``RawSource``) and the processing registry into
structured, typed, JSON-serializable *descriptors*.  It performs no scientific
computation and never mutates its inputs; it answers, in one canonical place:

- What kind of measurement is this? Is it raw or derived?
- What channels exist, and what does each hold?
- What are the dimensions, capabilities, and active conventions?
- Where did the data come from, and what was done to it (the lineage)?
- What processing operations are registered, and what parameters do they take?

**Present-day consumers** are the reason it exists: the Measurement Explorer,
publication/provenance export, future reports, debugging, and tests all need these
answers and would otherwise each re-derive them.  A future AI layer is simply one
more client of the same API - but the API exists because it improves *today's*
architecture, not because AI may use it later.

It is the data-tier counterpart to the GUI's presentation-tier view-objects: it
reports honest values (``None`` for unknown), leaving formatting to the consumer.

See ``docs/description-api.md`` (ADR-0018).
"""

from .descriptors import (
    ChannelDescription,
    ConventionsDescription,
    GeometryDescription,
    LineageStep,
    MeasurementDescription,
    MetadataSummary,
    OperationDescription,
    OperationParameter,
    ProvenanceSummary,
    SourceDescription,
)
from .summarize import (
    describe_channels,
    describe_measurement,
    describe_operation,
    describe_operations,
    summarize_metadata,
    summarize_provenance,
)

__all__ = [
    "ChannelDescription",
    "ConventionsDescription",
    "GeometryDescription",
    "LineageStep",
    "MeasurementDescription",
    "MetadataSummary",
    "OperationDescription",
    "OperationParameter",
    "ProvenanceSummary",
    "SourceDescription",
    "describe_channels",
    "describe_measurement",
    "describe_operation",
    "describe_operations",
    "summarize_metadata",
    "summarize_provenance",
]
