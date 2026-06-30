"""Tests for the two-input arithmetic operation (image.arithmetic) - ADR-0030.

This is the first multi-input operation, so these validate both the operation's
science (known-answer differences on real and complex-amplitude channels) and the
multi-input framework it exercises: a result that references *both* parents (and
both raw sources) in its provenance DAG, and a compatibility gate that refuses
mismatched grids/channels rather than silently reconciling them.
"""

from __future__ import annotations

import numpy as np
import pytest

import snomniman.processing.image  # noqa: F401  (registers image ops, incl. arithmetic)
from snomniman.core import Capability, Dataset, ProvenanceNode, RawSource, StepRecord
from snomniman.core.exceptions import ProcessingError
from snomniman.processing import get_step


def _raw_node(node_id: str, source: RawSource | None = None) -> ProvenanceNode:
    sources = {"measurement": source} if source is not None else {}
    return ProvenanceNode(
        node_id=node_id,
        record=StepRecord(step_id="io.read", step_version=1, deterministic=True),
        sources=sources,
    )


def _variant(
    ds: Dataset, *, node_id: str = "raw_b", source: RawSource | None = None, **deltas: float
) -> Dataset:
    """A compatible second measurement: same grid, with channels shifted by *deltas*."""
    data = ds.data.copy(deep=True)
    for channel, delta in deltas.items():
        data[channel] = data[channel] + delta
    return Dataset(data, kind=ds.kind, metadata=ds.metadata, provenance=_raw_node(node_id, source))


def _scaled(ds: Dataset, *, node_id: str = "raw_b", **factors: float) -> Dataset:
    data = ds.data.copy(deep=True)
    for channel, factor in factors.items():
        data[channel] = data[channel] * factor
    return Dataset(data, kind=ds.kind, metadata=ds.metadata, provenance=_raw_node(node_id))


def _arith(a: Dataset, b: Dataset, **params: object) -> Dataset:
    return get_step("image.arithmetic")(**params).apply({"primary": a, "secondary": b})


# -- science: known-answer differences --------------------------------------- #


def test_a_minus_b_real_channel(synthetic_dataset: Dataset) -> None:
    b = _variant(synthetic_dataset, Z=10.0)  # B.Z = A.Z + 10
    result = _arith(synthetic_dataset, b, channel="Z", mode="a_minus_b")
    assert "Z_diff" in result.channel_names
    assert result.is_complex("Z_diff") is False
    np.testing.assert_allclose(result.channel("Z_diff").values, -10.0)
    assert result.metadata.channel("Z_diff").value_unit == "nm"


def test_b_minus_a_real_channel(synthetic_dataset: Dataset) -> None:
    b = _variant(synthetic_dataset, Z=10.0)
    result = _arith(synthetic_dataset, b, channel="Z", mode="b_minus_a")
    np.testing.assert_allclose(result.channel("Z_diff").values, 10.0)


def test_absolute_difference(synthetic_dataset: Dataset) -> None:
    b = _variant(synthetic_dataset, Z=10.0)
    result = _arith(synthetic_dataset, b, channel="Z", mode="absolute_difference")
    np.testing.assert_allclose(result.channel("Z_diff").values, 10.0)


def test_default_mode_is_a_minus_b(synthetic_dataset: Dataset) -> None:
    b = _variant(synthetic_dataset, Z=10.0)
    result = _arith(synthetic_dataset, b, channel="Z")  # mode omitted
    np.testing.assert_allclose(result.channel("Z_diff").values, -10.0)


def test_complex_channel_differences_amplitude(synthetic_dataset: Dataset) -> None:
    b = _scaled(synthetic_dataset, O2=2.0)  # |B.O2| = 2 |A.O2|
    result = _arith(synthetic_dataset, b, channel="O2", mode="a_minus_b")
    expected = -np.abs(np.asarray(synthetic_dataset.channel("O2").values))  # |A| - 2|A| = -|A|
    assert result.is_complex("O2_diff") is False
    np.testing.assert_allclose(result.channel("O2_diff").values, expected, rtol=1e-6)
    assert result.metadata.channel("O2_diff").value_unit == "a.u."


def test_inputs_are_not_mutated(synthetic_dataset: Dataset) -> None:
    b = _variant(synthetic_dataset, Z=10.0)
    a_before = np.array(synthetic_dataset.channel("Z").values, copy=True)
    b_before = np.array(b.channel("Z").values, copy=True)
    _arith(synthetic_dataset, b, channel="Z", mode="a_minus_b")
    np.testing.assert_array_equal(synthetic_dataset.channel("Z").values, a_before)
    np.testing.assert_array_equal(b.channel("Z").values, b_before)


# -- provenance: both parents (and both sources) are referenced -------------- #


def test_provenance_references_both_parents(synthetic_dataset: Dataset) -> None:
    b = _variant(synthetic_dataset, node_id="raw_b", Z=10.0)
    result = _arith(synthetic_dataset, b, channel="Z", mode="a_minus_b")
    node = result.provenance
    assert node.record.step_id == "image.arithmetic"
    assert set(node.inputs) == {"primary", "secondary"}
    assert node.inputs["primary"] is synthetic_dataset.provenance
    assert node.inputs["secondary"] is b.provenance
    # Both parent nodes are reachable in the derived dataset's DAG.
    node_ids = {n.node_id for n in node.iter_nodes()}
    assert {"n0", "raw_b"} <= node_ids


def test_provenance_carries_both_raw_sources(synthetic_dataset: Dataset) -> None:
    src_a = RawSource(path="/data/A", sha256="a" * 64, reader="test", bytes=1, is_directory=True)
    src_b = RawSource(path="/data/B", sha256="b" * 64, reader="test", bytes=1, is_directory=True)
    a = Dataset(
        synthetic_dataset.data,
        kind=synthetic_dataset.kind,
        metadata=synthetic_dataset.metadata,
        provenance=_raw_node("raw_a", src_a),
    )
    b = _variant(synthetic_dataset, node_id="raw_b", source=src_b, Z=10.0)
    result = _arith(a, b, channel="Z", mode="a_minus_b")
    paths = {s.path for s in result.provenance.iter_sources()}
    assert paths == {"/data/A", "/data/B"}


# -- compatibility: refuse, never reconcile ---------------------------------- #


def test_incompatible_dimensions_are_refused(synthetic_dataset: Dataset) -> None:
    small_data = synthetic_dataset.data.isel(x=slice(0, 2), y=slice(0, 2))
    small = Dataset(
        small_data,
        kind=synthetic_dataset.kind,
        metadata=synthetic_dataset.metadata,
        provenance=_raw_node("raw_small"),
    )
    step = get_step("image.arithmetic")(channel="Z", mode="a_minus_b")
    problems = step.check_compatibility({"primary": synthetic_dataset, "secondary": small})
    assert any("size" in p for p in problems)
    with pytest.raises(ProcessingError, match="incompatible inputs"):
        step.apply({"primary": synthetic_dataset, "secondary": small})


def test_missing_channel_is_refused(
    synthetic_dataset: Dataset, optical_only_dataset: Dataset
) -> None:
    # optical_only has no Z channel (same grid); differencing Z must be refused.
    step = get_step("image.arithmetic")(channel="Z", mode="a_minus_b")
    problems = step.check_compatibility(
        {"primary": synthetic_dataset, "secondary": optical_only_dataset}
    )
    assert any("not in measurement B" in p for p in problems)
    with pytest.raises(ProcessingError, match="incompatible inputs"):
        step.apply({"primary": synthetic_dataset, "secondary": optical_only_dataset})


def test_required_capabilities(synthetic_dataset: Dataset) -> None:
    assert get_step("image.arithmetic").required_capabilities == (Capability.SPATIAL_2D,)
