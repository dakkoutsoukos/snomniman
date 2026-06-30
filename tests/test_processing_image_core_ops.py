"""Tests for the Phase 3A core scientific operations (image domain).

Covers the three operations that form SNOMNIMAN's first scientific toolbox - one per
track: ``image.fix_zero`` (topography datum), ``image.phase_offset`` (s-SNOM phase
re-referencing), and ``image.normalize_amplitude`` (s-SNOM amplitude). Each is tested
with a known answer (Rule 6), non-mutation of the input, recorded provenance, the
metadata it updates, and refusal of invalid inputs. The phase test specifically pins
the *circular*-mean correctness (cyclic phase is averaged as a complex vector).
"""

from __future__ import annotations

import numpy as np
import pytest

import snomniman.processing.image  # noqa: F401  (registers image ops)
from snomniman.core import Dataset, ProvenanceNode, StepRecord
from snomniman.core.exceptions import ProcessingError
from snomniman.processing import get_step


def _apply(step_id: str, dataset: Dataset, **params: object) -> Dataset:
    return get_step(step_id)(**params).apply({"primary": dataset})


def _zeroed_channel(ds: Dataset, channel: str) -> Dataset:
    """A copy of *ds* with *channel* set to all zeros (for the zero-amplitude guard)."""
    data = ds.data.copy(deep=True)
    data[channel] = data[channel] * 0
    return Dataset(
        data,
        kind=ds.kind,
        metadata=ds.metadata,
        provenance=ProvenanceNode("raw_z", StepRecord("io.read", 1, True)),
    )


# --------------------------------------------------------------------------- #
# image.fix_zero
# --------------------------------------------------------------------------- #


def test_fix_zero_minimum_sets_min_to_zero(synthetic_dataset: Dataset) -> None:
    original = np.asarray(synthetic_dataset.channel("Z").values, dtype=np.float64)
    result = _apply("image.fix_zero", synthetic_dataset, channel="Z", reference="minimum")
    values = np.asarray(result.channel("Z").values, dtype=np.float64)
    assert np.isclose(np.nanmin(values), 0.0)
    np.testing.assert_allclose(values, original - np.nanmin(original))


def test_fix_zero_mean_and_median(synthetic_dataset: Dataset) -> None:
    mean_zeroed = _apply("image.fix_zero", synthetic_dataset, channel="Z", reference="mean")
    assert np.isclose(np.nanmean(mean_zeroed.channel("Z").values), 0.0, atol=1e-9)
    median_zeroed = _apply("image.fix_zero", synthetic_dataset, channel="Z", reference="median")
    assert np.isclose(np.nanmedian(median_zeroed.channel("Z").values), 0.0, atol=1e-9)


def test_fix_zero_default_reference_is_minimum(synthetic_dataset: Dataset) -> None:
    result = _apply("image.fix_zero", synthetic_dataset, channel="Z")  # reference omitted
    assert np.isclose(np.nanmin(result.channel("Z").values), 0.0)


def test_fix_zero_does_not_mutate_input(synthetic_dataset: Dataset) -> None:
    before = np.array(synthetic_dataset.channel("Z").values, copy=True)
    _apply("image.fix_zero", synthetic_dataset, channel="Z", reference="minimum")
    np.testing.assert_array_equal(synthetic_dataset.channel("Z").values, before)


def test_fix_zero_records_provenance(synthetic_dataset: Dataset) -> None:
    result = _apply("image.fix_zero", synthetic_dataset, channel="Z")
    assert result.provenance.record.step_id == "image.fix_zero"


def test_fix_zero_rejects_complex_and_missing_channel(synthetic_dataset: Dataset) -> None:
    with pytest.raises(ProcessingError, match="requires a real-valued channel"):
        _apply("image.fix_zero", synthetic_dataset, channel="O2")
    with pytest.raises(ProcessingError, match="not found"):
        _apply("image.fix_zero", synthetic_dataset, channel="NOPE")


# --------------------------------------------------------------------------- #
# image.phase_offset
# --------------------------------------------------------------------------- #


def test_phase_offset_constant_shifts_phase_and_keeps_amplitude(
    synthetic_dataset: Dataset,
) -> None:
    o2 = np.asarray(synthetic_dataset.channel("O2").values)
    result = _apply(
        "image.phase_offset", synthetic_dataset, channel="O2",
        reference="constant", value_rad=0.5,
    )
    out = np.asarray(result.channel("O2").values)
    np.testing.assert_allclose(out, o2 * np.exp(-0.5j), rtol=1e-5, atol=1e-6)
    np.testing.assert_allclose(np.abs(out), np.abs(o2), rtol=1e-5)  # amplitude preserved


def test_phase_offset_mean_uses_circular_mean(synthetic_dataset: Dataset) -> None:
    o2 = np.asarray(synthetic_dataset.channel("O2").values)
    result = _apply("image.phase_offset", synthetic_dataset, channel="O2", reference="mean")
    out = np.asarray(result.channel("O2").values)
    # Removing the circular mean makes the new circular mean phase zero. (An arithmetic
    # mean of wrapped angles would NOT achieve this - so this pins cyclic correctness.)
    assert abs(float(np.angle(np.mean(out)))) < 1e-5
    np.testing.assert_allclose(np.abs(out), np.abs(o2), rtol=1e-5)  # amplitude preserved


def test_phase_offset_records_reference_and_state(synthetic_dataset: Dataset) -> None:
    result = _apply("image.phase_offset", synthetic_dataset, channel="O2", reference="mean")
    assert result.provenance.record.step_id == "image.phase_offset"
    assert "image.phase_offset" in (result.metadata.conventions.phase_reference or "")
    assert result.metadata.channel("O2").state == "referenced"


def test_phase_offset_does_not_mutate_input(synthetic_dataset: Dataset) -> None:
    before = np.array(synthetic_dataset.channel("O2").values, copy=True)
    _apply("image.phase_offset", synthetic_dataset, channel="O2", reference="mean")
    np.testing.assert_array_equal(synthetic_dataset.channel("O2").values, before)


def test_phase_offset_rejects_real_and_missing_channel(synthetic_dataset: Dataset) -> None:
    with pytest.raises(ProcessingError, match="requires a complex channel"):
        _apply("image.phase_offset", synthetic_dataset, channel="Z")
    with pytest.raises(ProcessingError, match="not found"):
        _apply("image.phase_offset", synthetic_dataset, channel="NOPE")


# --------------------------------------------------------------------------- #
# image.normalize_amplitude
# --------------------------------------------------------------------------- #


def test_normalize_amplitude_max_maps_peak_to_one(synthetic_dataset: Dataset) -> None:
    o2 = np.asarray(synthetic_dataset.channel("O2").values)
    result = _apply("image.normalize_amplitude", synthetic_dataset, channel="O2", reference="max")
    out = np.asarray(result.channel("O2").values)
    assert np.isclose(float(np.max(np.abs(out))), 1.0, rtol=1e-5)
    np.testing.assert_allclose(np.angle(out), np.angle(o2), atol=1e-5)  # phase preserved


def test_normalize_amplitude_mean_maps_mean_to_one(synthetic_dataset: Dataset) -> None:
    result = _apply("image.normalize_amplitude", synthetic_dataset, channel="O2", reference="mean")
    out = np.asarray(result.channel("O2").values)
    assert np.isclose(float(np.mean(np.abs(out))), 1.0, rtol=1e-5)


def test_normalize_amplitude_default_is_max(synthetic_dataset: Dataset) -> None:
    result = _apply("image.normalize_amplitude", synthetic_dataset, channel="O2")  # default
    assert np.isclose(float(np.max(np.abs(result.channel("O2").values))), 1.0, rtol=1e-5)


def test_normalize_amplitude_records_state(synthetic_dataset: Dataset) -> None:
    result = _apply("image.normalize_amplitude", synthetic_dataset, channel="O2")
    assert result.provenance.record.step_id == "image.normalize_amplitude"
    assert result.metadata.channel("O2").state == "normalized"
    assert result.metadata.channel("O2").amplitude_unit == ""


def test_normalize_amplitude_does_not_mutate_input(synthetic_dataset: Dataset) -> None:
    before = np.array(synthetic_dataset.channel("O2").values, copy=True)
    _apply("image.normalize_amplitude", synthetic_dataset, channel="O2")
    np.testing.assert_array_equal(synthetic_dataset.channel("O2").values, before)


def test_normalize_amplitude_rejects_real_missing_and_zero(synthetic_dataset: Dataset) -> None:
    with pytest.raises(ProcessingError, match="requires a complex channel"):
        _apply("image.normalize_amplitude", synthetic_dataset, channel="Z")
    with pytest.raises(ProcessingError, match="not found"):
        _apply("image.normalize_amplitude", synthetic_dataset, channel="NOPE")
    zeroed = _zeroed_channel(synthetic_dataset, "O2")
    with pytest.raises(ProcessingError, match="no positive amplitude"):
        _apply("image.normalize_amplitude", zeroed, channel="O2")
