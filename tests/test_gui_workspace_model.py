"""Qt-free tests for the generic Processing Workspace presenter (ExplorerModel).

These exercise the *backend* of the registry-driven workspace - the operation
catalogue, automatic parameter-form generation, per-dataset availability and
disabled-operation explanations, the preview lifecycle (change summary +
provenance), and the cardinal immutability invariant - all without a display, so
they run in CI without the ``gui`` extra (like ``test_gui_model.py``).

The window-level wiring is covered by ``test_gui_process.py``.
"""

from __future__ import annotations

import numpy as np
import pytest

from snomniman.core import Dataset
from snomniman.core.exceptions import ProcessingError
from snomniman.gui.model import (
    FIELD_CHANNEL,
    FIELD_ENUM,
    FIELD_FLOAT,
    ExplorerModel,
    OperationOption,
)

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _catalog(model: ExplorerModel) -> dict[str, OperationOption]:
    return {opt.step_id: opt for opt in model.operation_catalog()}


# --------------------------------------------------------------------------- #
# Registry discovery + grouping
# --------------------------------------------------------------------------- #


def test_catalog_discovers_all_registered_image_operations(synthetic_dataset: Dataset) -> None:
    catalog = _catalog(ExplorerModel(synthetic_dataset))
    expected = {
        "image.crop",
        "image.line_flatten",
        "image.phase_unwrap",
        "image.plane_level",
        "image.reference_normalize",
    }
    assert expected <= set(catalog)


def test_catalog_groups_by_namespace(synthetic_dataset: Dataset) -> None:
    for opt in ExplorerModel(synthetic_dataset).operation_catalog():
        if opt.step_id.startswith("image."):
            assert opt.group == "Image"


def test_catalog_derives_human_titles(synthetic_dataset: Dataset) -> None:
    catalog = _catalog(ExplorerModel(synthetic_dataset))
    assert catalog["image.plane_level"].title == "Plane Level"
    assert catalog["image.reference_normalize"].title == "Reference Normalize"


# --------------------------------------------------------------------------- #
# Automatic parameter-form generation (from ParameterSpec, no per-op code)
# --------------------------------------------------------------------------- #


def test_plane_level_fields_channel_and_order(synthetic_dataset: Dataset) -> None:
    opt = ExplorerModel(synthetic_dataset).operation_option("image.plane_level")
    fields = {f.name: f for f in opt.fields}
    assert fields["channel"].kind == FIELD_CHANNEL
    assert fields["order"].kind == FIELD_ENUM
    assert fields["order"].choices == (1, 2, 3)
    assert fields["channel"].default == "Z"


def test_plane_level_channel_choices_are_real_only(synthetic_dataset: Dataset) -> None:
    opt = ExplorerModel(synthetic_dataset).operation_option("image.plane_level")
    channel = {f.name: f for f in opt.fields}["channel"]
    # Only the real-valued channel (Z); complex channels are excluded.
    assert channel.choices == ("Z",)


def test_phase_unwrap_channel_choices_are_complex_only(synthetic_dataset: Dataset) -> None:
    opt = ExplorerModel(synthetic_dataset).operation_option("image.phase_unwrap")
    channel = {f.name: f for f in opt.fields}["channel"]
    assert channel.kind == FIELD_CHANNEL
    assert set(channel.choices) == {"O2", "O3", "R_O2", "M1"}
    assert "Z" not in channel.choices


def test_crop_fields_are_four_floats(synthetic_dataset: Dataset) -> None:
    opt = ExplorerModel(synthetic_dataset).operation_option("image.crop")
    assert [f.name for f in opt.fields] == ["x_min", "x_max", "y_min", "y_max"]
    assert all(f.kind == FIELD_FLOAT and f.required for f in opt.fields)


def test_reference_normalize_has_no_fields(synthetic_dataset: Dataset) -> None:
    opt = ExplorerModel(synthetic_dataset).operation_option("image.reference_normalize")
    assert opt.fields == ()


# --------------------------------------------------------------------------- #
# Availability + disabled-operation explanations
# --------------------------------------------------------------------------- #


def test_all_image_ops_available_on_full_dataset(synthetic_dataset: Dataset) -> None:
    catalog = _catalog(ExplorerModel(synthetic_dataset))
    for step_id in (
        "image.crop",
        "image.line_flatten",
        "image.phase_unwrap",
        "image.plane_level",
    ):
        assert catalog[step_id].available, step_id
    assert catalog["image.reference_normalize"].available


def test_reference_normalize_unavailable_without_references(
    topography_dataset: Dataset,
) -> None:
    opt = ExplorerModel(topography_dataset).operation_option("image.reference_normalize")
    assert not opt.available
    assert not opt.applicable
    # The explanation names the missing capabilities in human terms.
    joined = " ".join(opt.missing).lower()
    assert "reference" in joined
    assert "optical" in joined


def test_unavailable_operation_still_listed(topography_dataset: Dataset) -> None:
    # Even unavailable, an operation remains discoverable (visible, with a reason).
    catalog = _catalog(ExplorerModel(topography_dataset))
    assert "image.reference_normalize" in catalog


def test_already_applied_is_reported(synthetic_dataset: Dataset) -> None:
    model = ExplorerModel(synthetic_dataset)
    preview = model.preview_operation("image.plane_level", {"channel": "Z", "order": 1})
    derived = ExplorerModel(preview.dataset)
    assert _catalog(derived)["image.plane_level"].already_applied


# --------------------------------------------------------------------------- #
# Preview lifecycle (change summary + provenance, every operation the same shape)
# --------------------------------------------------------------------------- #


def test_preview_plane_level_before_after_and_provenance(synthetic_dataset: Dataset) -> None:
    model = ExplorerModel(synthetic_dataset)
    preview = model.preview_operation("image.plane_level", {"channel": "Z", "order": 2})
    assert len(preview.panes) == 2
    assert [p.spec.label for p in preview.panes] == ["Z (before)", "Z (after)"]
    assert any("Z" in c for c in preview.changes)
    assert preview.provenance.step_id == "image.plane_level"
    assert preview.provenance.params == {"channel": "Z", "order": 2}
    assert not preview.dataset.is_raw


def test_preview_phase_unwrap_adds_channel(synthetic_dataset: Dataset) -> None:
    preview = ExplorerModel(synthetic_dataset).preview_operation(
        "image.phase_unwrap", {"channel": "O2"}
    )
    assert "O2_phase_unwrapped" in preview.dataset.channel_names
    assert any("O2_phase_unwrapped" in c for c in preview.changes)
    # before = the source's phase; after = the new channel.
    labels = [p.spec.label for p in preview.panes]
    assert labels == ["O2 (before)", "O2_phase_unwrapped (new)"]


def test_preview_crop_reports_shape_change(synthetic_dataset: Dataset) -> None:
    preview = ExplorerModel(synthetic_dataset).preview_operation(
        "image.crop", {"x_min": 0.0, "x_max": 120.0, "y_min": 0.0, "y_max": 120.0}
    )
    assert dict(preview.dataset.data.sizes) == {"x": 2, "y": 2}
    assert any("field of view" in c.lower() for c in preview.changes)


def test_preview_reference_normalize_records_phase_rereference(synthetic_dataset: Dataset) -> None:
    preview = ExplorerModel(synthetic_dataset).preview_operation("image.reference_normalize", {})
    text = " ".join(preview.changes).lower()
    assert "normalized" in text
    assert "phase" in text  # the explicit, recorded re-reference (OHD-6D)


def test_preview_lists_unchanged_facts(synthetic_dataset: Dataset) -> None:
    preview = ExplorerModel(synthetic_dataset).preview_operation(
        "image.plane_level", {"channel": "Z", "order": 1}
    )
    assert any("raw measurement is untouched" in u.lower() for u in preview.unchanged)


# --------------------------------------------------------------------------- #
# Invalid parameters / preconditions raise (nothing is committed)
# --------------------------------------------------------------------------- #


def test_preview_invalid_channel_kind_raises(synthetic_dataset: Dataset) -> None:
    # plane_level needs a real channel; O2 is complex -> ProcessingError.
    with pytest.raises(ProcessingError):
        ExplorerModel(synthetic_dataset).preview_operation(
            "image.plane_level", {"channel": "O2", "order": 1}
        )


def test_preview_invalid_order_raises(synthetic_dataset: Dataset) -> None:
    with pytest.raises(ProcessingError):
        ExplorerModel(synthetic_dataset).preview_operation(
            "image.plane_level", {"channel": "Z", "order": 7}
        )


def test_preview_crop_empty_region_raises(synthetic_dataset: Dataset) -> None:
    with pytest.raises(ProcessingError):
        ExplorerModel(synthetic_dataset).preview_operation(
            "image.crop", {"x_min": 0.0, "x_max": 0.0, "y_min": 0.0, "y_max": 120.0}
        )


# --------------------------------------------------------------------------- #
# Cardinal invariant: previewing never mutates the source dataset
# --------------------------------------------------------------------------- #


def test_preview_does_not_mutate_source(synthetic_dataset: Dataset) -> None:
    model = ExplorerModel(synthetic_dataset)
    before = {n: model.dataset.channel(n).values.copy() for n in model.dataset.channel_names}
    model.preview_operation("image.plane_level", {"channel": "Z", "order": 1})
    model.preview_operation("image.reference_normalize", {})
    model.preview_operation("image.phase_unwrap", {"channel": "O2"})
    for name, arr in before.items():
        np.testing.assert_array_equal(model.dataset.channel(name).values, arr, err_msg=name)
        assert model.dataset.channel(name).data.flags.writeable is False
