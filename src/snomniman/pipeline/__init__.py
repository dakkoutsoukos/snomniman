"""snomniman.pipeline - the reproducibility engine (depends on io, processing, core).

Defines the **provenance DAG** (multi-input: sample/reference normalization,
background subtraction, calibration inputs, stitched scans), replay/reconstruction,
JSON (de)serialization, environment/version + operation-version capture, the
``Project`` bundle with its on-disk persistence, and **processing Recipes** (Phase
4A, ADR-0031): a named, portable, replayable projection of a provenance chain. This
is the backbone of OHD-5: any result is reconstructable and auditable from its data
sources, provenance graph, steps, parameters, and software/operation versions.

Project persistence reuses the canonical Zarr store (``snomniman.io``) - a project
is a bundle of Zarr-stored datasets plus a manifest - rather than introducing a
second dataset serialization (ADR-0027). A ``Recipe`` similarly reuses the
processing registry + ``ProcessingStep.apply`` rather than a second processing
engine (ADR-0031): capture projects a dataset's ``StepRecord`` chain into a portable
``(step_id, version, params)`` list, and replay loops ``apply()`` over it.
"""

from __future__ import annotations

from .project import (
    MANIFEST_NAME,
    PROJECT_FORMAT,
    PROJECT_SCHEMA_VERSION,
    Measurement,
    Project,
    load_project,
    measurement_from_history,
    project_from_history,
    save_project,
)
from .recipe import (
    RECIPE_FORMAT,
    RECIPE_SCHEMA_VERSION,
    RECIPE_SUFFIX,
    Recipe,
    RecipeStep,
    apply_recipe,
    capture_recipe,
    delete_recipe,
    duplicated,
    load_recipe,
    matching_recipe_name,
    renamed,
    save_recipe,
    with_step_params,
)

__all__ = [
    "MANIFEST_NAME",
    "PROJECT_FORMAT",
    "PROJECT_SCHEMA_VERSION",
    "RECIPE_FORMAT",
    "RECIPE_SCHEMA_VERSION",
    "RECIPE_SUFFIX",
    "Measurement",
    "Project",
    "Recipe",
    "RecipeStep",
    "apply_recipe",
    "capture_recipe",
    "delete_recipe",
    "duplicated",
    "load_project",
    "load_recipe",
    "matching_recipe_name",
    "measurement_from_history",
    "project_from_history",
    "renamed",
    "save_project",
    "save_recipe",
    "with_step_params",
]
