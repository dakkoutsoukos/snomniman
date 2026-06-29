"""snomniman.pipeline - the reproducibility engine (depends on io, processing, core).

Defines the **provenance DAG** (multi-input: sample/reference normalization,
background subtraction, calibration inputs, stitched scans), replay/reconstruction,
JSON (de)serialization, environment/version + operation-version capture, and the
``Project`` bundle with its on-disk persistence. This is the backbone of OHD-5:
any result is reconstructable and auditable from its data sources, provenance
graph, steps, parameters, and software/operation versions.

Project persistence reuses the canonical Zarr store (``snomniman.io``) - a project
is a bundle of Zarr-stored datasets plus a manifest - rather than introducing a
second dataset serialization (ADR-0027).
"""

from __future__ import annotations

from .project import (
    MANIFEST_NAME,
    PROJECT_FORMAT,
    PROJECT_SCHEMA_VERSION,
    Project,
    load_project,
    project_from_history,
    save_project,
)

__all__ = [
    "MANIFEST_NAME",
    "PROJECT_FORMAT",
    "PROJECT_SCHEMA_VERSION",
    "Project",
    "load_project",
    "project_from_history",
    "save_project",
]
