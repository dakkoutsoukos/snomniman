"""snomniman.io - import and export (depends on snomniman.core).

Houses the reader *registry* (format id -> reader), concrete readers (first
target: a real neaSNOM imaging dataset), and writers for the canonical project
store (**Zarr**) and exporting derived data. A registry, not a plugin system
(ADR-0006). Vendor parsing is validated against real files (Rule 6), HDF5-based
vendor files may be read with h5py, and unknown header fields are preserved
verbatim rather than discarded.
"""

from __future__ import annotations

from .export import GSF_EXPORT_FORMAT, export_channel_gsf
from .gsf import GsfFile, parse_gsf, read_gsf, write_gsf
from .neasnom import READER_ID, read_neasnom_measurement
from .neasnom_spectrum import (
    READER_ID as NEASNOM_SPECTRUM_READER_ID,
)
from .neasnom_spectrum import (
    read_neasnom_spectrum_measurement,
)
from .registry import available_readers, get_reader, read, register, sniff
from .zarrstore import STORE_FORMAT, STORE_SCHEMA_VERSION, read_zarr, write_zarr

__all__ = [
    "GSF_EXPORT_FORMAT",
    "NEASNOM_SPECTRUM_READER_ID",
    "READER_ID",
    "STORE_FORMAT",
    "STORE_SCHEMA_VERSION",
    "GsfFile",
    "available_readers",
    "export_channel_gsf",
    "get_reader",
    "parse_gsf",
    "read",
    "read_gsf",
    "read_neasnom_measurement",
    "read_neasnom_spectrum_measurement",
    "read_zarr",
    "register",
    "sniff",
    "write_gsf",
    "write_zarr",
]
