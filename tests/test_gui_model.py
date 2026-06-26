"""Tests for the Qt-free Explorer presenter (snomniman.gui.model).

These exercise the full read-only experience logic without a display: channel
grouping, identity, metadata sections, provenance, cursor readout, channel
switching, and - critically - that exploring never modifies the Dataset.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from snomniman.core import Dataset
from snomniman.gui.model import ExplorerModel
from snomniman.viz import AMPLITUDE, PHASE

_REPO_ROOT = Path(__file__).resolve().parents[1]
_GOLDEN_DIR = (
    _REPO_ROOT / "SNOM Sample Files" / "2026-06-16 14928" / "2026-06-16 190234 PH CdO Dense ROI 2"
)


@pytest.fixture
def golden_model() -> ExplorerModel:
    if not _GOLDEN_DIR.is_dir():
        pytest.skip("real neaSNOM sample data not present")
    return ExplorerModel.open_measurement(_GOLDEN_DIR)


# -- defaults + channel switching ------------------------------------------- #


def test_default_channel_is_o2_amplitude(synthetic_dataset: Dataset) -> None:
    model = ExplorerModel(synthetic_dataset)
    assert model.current_channel == "O2"
    assert model.current_representation == AMPLITUDE


def test_set_channel_and_representation(synthetic_dataset: Dataset) -> None:
    model = ExplorerModel(synthetic_dataset)
    model.set_representation(PHASE)
    assert model.current_representation == PHASE
    # Switching channel resets to the new channel's natural representation.
    model.set_channel("Z")
    assert model.current_channel == "Z"
    assert model.current_representation == "real"
    with pytest.raises(KeyError):
        model.set_channel("nope")
    with pytest.raises(ValueError, match="not available"):
        model.set_channel("Z")  # real channel
        model.set_representation(PHASE)


def test_render_follows_current_state(synthetic_dataset: Dataset) -> None:
    model = ExplorerModel(synthetic_dataset)
    model.set_representation(PHASE)
    rd = model.render()
    assert rd.channel == "O2" and rd.representation == PHASE and rd.cyclic is True


# -- channel grouping mirrors physics --------------------------------------- #


def test_channel_groups(synthetic_dataset: Dataset) -> None:
    groups = {g.title: g for g in ExplorerModel(synthetic_dataset).channel_groups()}
    assert set(groups) == {
        "Optical (near-field)", "Mechanical (cantilever)", "Topography", "References"
    }
    optical = [e.canonical for e in groups["Optical (near-field)"].entries]
    assert optical == ["O2", "O3"]  # sorted by harmonic
    assert groups["References"].entries[0].canonical == "R_O2"
    assert groups["Topography"].entries[0].descriptor == "height"


def test_golden_channel_groups_complete(golden_model: ExplorerModel) -> None:
    groups = {g.title: g for g in golden_model.channel_groups()}
    optical = [e.canonical for e in groups["Optical (near-field)"].entries]
    assert optical == [f"O{n}" for n in range(6)]  # O0..O5 in order
    total = sum(len(g.entries) for g in groups.values())
    assert total == 32  # every channel is browsable, none orphaned


# -- identity + metadata reflect the Dataset -------------------------------- #


def test_identity_reflects_metadata(golden_model: ExplorerModel) -> None:
    ident = golden_model.identity()
    assert ident.is_raw is True
    assert ident.kind == "image"
    assert ident.pixels == (150, 150)
    assert ident.wavenumber_cm1 == pytest.approx(5973.0)
    assert ident.detection == "PsHet"
    assert ident.vendor == "neaspec"


def test_metadata_sections_reflect_dataset(golden_model: ExplorerModel) -> None:
    sections = {s.title: s for s in golden_model.metadata_sections()}
    assert "Conventions" in sections and "Excitation" in sections
    conv = {i.label: i for i in sections["Conventions"].items}
    assert conv["Spatial unit"].value == "nm"
    assert "lower-left" in conv["Origin"].value
    exc = {i.label: i for i in sections["Excitation"].items}
    assert exc["Wavenumber"].value == "5973" and exc["Wavenumber"].unit == "cm^-1"
    # Every value carries a source (the provenance of the metadata).
    for s in sections.values():
        for item in s.items:
            assert item.source


def test_unknown_metadata_shown_as_unknown(synthetic_dataset: Dataset) -> None:
    # synthetic_dataset has no acquisition date -> shown as "unknown", never guessed.
    sections = {s.title: s for s in ExplorerModel(synthetic_dataset).metadata_sections()}
    date = {i.label: i for i in sections["Acquisition"].items}["Date"]
    assert date.value == "unknown"


# -- provenance ------------------------------------------------------------- #


def test_provenance_visible(golden_model: ExplorerModel) -> None:
    assert "raw measurement" in golden_model.provenance_summary()
    steps = golden_model.provenance_steps()
    assert len(steps) == 1
    step = steps[0]
    assert step.step_id == "io.read"
    assert "Imported" in step.description
    assert step.sources and "reader neasnom.image.gsf.v1" in step.sources[0]
    assert "numpy" in step.software


# -- cursor readout --------------------------------------------------------- #


def test_cursor_readout_in_and_out_of_bounds(golden_model: ExplorerModel) -> None:
    rd = golden_model.render()
    x0, x1, y0, y1 = rd.extent_nm
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    readout = golden_model.cursor_readout(cx, cy)
    assert readout.in_bounds is True
    labels = [v.label for v in readout.values]
    assert "O2 amplitude" in labels and "O2 phase" in labels
    assert "Z height" in labels  # topography context at the same pixel
    # Outside the field -> no values, flagged out of bounds.
    assert golden_model.cursor_readout(x1 + 1000.0, cy).in_bounds is False


# -- the cardinal invariant: exploration never mutates ---------------------- #


def test_exploring_does_not_modify_dataset(golden_model: ExplorerModel) -> None:
    ds = golden_model.dataset
    before = {name: ds.channel(name).values.copy() for name in ds.channel_names}
    # Drive a full exploration session.
    for group in golden_model.channel_groups():
        for entry in group.entries:
            golden_model.set_channel(entry.canonical)
            for rep in golden_model.representations():
                golden_model.set_representation(rep)
                golden_model.render()
                golden_model.cursor_readout(0.0, 0.0)
    for name, arr in before.items():
        np.testing.assert_array_equal(ds.channel(name).values, arr, err_msg=name)
        # The raw arrays are still frozen (immutable) after all that exploring.
        assert ds.channel(name).data.flags.writeable is False


def test_open_measurement_classmethod(golden_model: ExplorerModel) -> None:
    assert golden_model.title.startswith("2026-06-16")
    assert golden_model.dataset.is_raw is True
