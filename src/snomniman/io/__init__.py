"""snomniman.io - import and export (depends on snomniman.core).

Houses the reader *registry* (format id -> reader), concrete readers (first
target: a real neaSNOM imaging dataset), and writers for the canonical project
store (**Zarr**) and exporting derived data. A registry, not a plugin system
(ADR-0006). Vendor parsing is validated against real files (Rule 6), HDF5-based
vendor files may be read with h5py, and unknown header fields are preserved
verbatim rather than discarded.
"""
