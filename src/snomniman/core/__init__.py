"""snomniman.core - the data model (no I/O, no processing, no GUI).

Defines the central ``Dataset`` abstraction (an ``xarray``-backed, SNOM-aware
container), ``DataKind`` + capability descriptors (hybrid dispatch), typed
``Metadata`` (which carries scientific conventions explicitly), ``RawSource``,
unit conventions (canonical spatial unit: nm), and provenance value objects
(``StepRecord``, ``History``) for the multi-input provenance DAG.

Depends on nothing else inside ``snomniman`` (the base of the dependency graph).
See ``docs/data-model.md``.
"""

from __future__ import annotations

from .capabilities import Capability
from .datakind import DataKind
from .dataset import Dataset
from .exceptions import (
    DatasetError,
    MetadataError,
    ProcessingError,
    ReaderError,
    SnomnimanError,
)
from .metadata import (
    SCHEMA_VERSION,
    Acquisition,
    ChannelInfo,
    Conventions,
    Demodulation,
    Excitation,
    Instrument,
    Metadata,
    ScanInfo,
)
from .provenance import (
    READ_STEP_ID,
    ProvenanceNode,
    StepRecord,
    current_software,
    deserialize_dag,
    serialize_dag,
)
from .rawsource import RawSource
from .units import SPATIAL_UNIT, WAVENUMBER_UNIT, length_scale_to_nm, length_to_nm

__all__ = [
    "READ_STEP_ID",
    "SCHEMA_VERSION",
    "SPATIAL_UNIT",
    "WAVENUMBER_UNIT",
    "Acquisition",
    "Capability",
    "ChannelInfo",
    "Conventions",
    "DataKind",
    "Dataset",
    "DatasetError",
    "Demodulation",
    "Excitation",
    "Instrument",
    "Metadata",
    "MetadataError",
    "ProcessingError",
    "ProvenanceNode",
    "RawSource",
    "ReaderError",
    "ScanInfo",
    "SnomnimanError",
    "StepRecord",
    "current_software",
    "deserialize_dag",
    "length_scale_to_nm",
    "length_to_nm",
    "serialize_dag",
]
