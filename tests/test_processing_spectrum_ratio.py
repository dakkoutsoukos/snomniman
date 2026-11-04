"""Tests for spectrum.ratio - the spectral analogue of image.arithmetic.

Mirrors ``test_processing_image_arithmetic.py``'s structure: known-answer ratios
on real and complex-amplitude channels, provenance referencing both parents, and
a compatibility gate that refuses mismatched wavenumber axes/channels rather than
silently reconciling them (docs/phase6-spectral-lineshape-analysis.md sec 2/3.1).
"""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

import snomniman.processing.spectrum  # noqa: F401  (registers spectrum ops, incl. ratio)
from snomniman.core import (
    Capability,
    ChannelInfo,
    DataKind,
    Dataset,
    Metadata,
    ProvenanceNode,
    RawSource,
    StepRecord,
)
from snomniman.core.exceptions import ProcessingError
from snomniman.processing import get_step

_WN = 5920.0 + np.arange(30, dtype=np.float64)


def _raw_node(node_id: str, source: RawSource | None = None) -> ProvenanceNode:
    sources = {"measurement": source} if source is not None else {}
    return ProvenanceNode(
        node_id=node_id,
        record=StepRecord(step_id="io.read", step_version=1, deterministic=True),
        sources=sources,
    )


def _spectrum_dataset(
    values: np.ndarray,
    *,
    wn: np.ndarray = _WN,
    channel: str = "O2",
    node_id: str = "n0",
    source: RawSource | None = None,
    harmonic: int | None = 2,
) -> Dataset:
    """A single-position SPECTRUM Dataset, dims exactly ``(wavenumber,)``."""
    data = xr.Dataset(
        {channel: ("wavenumber", values)},
        coords={"wavenumber": ("wavenumber", wn, {"unit": "cm-1", "long_name": "wavenumber"})},
    )
    is_complex = np.iscomplexobj(values)
    metadata = Metadata(
        data_kind=DataKind.SPECTRUM,
        channels=(
            ChannelInfo(
                channel, "optical", "signal",
                "complex64" if is_complex else "float64",
                harmonic=harmonic,
                amplitude_unit="a.u." if is_complex else None,
                phase_unit="rad" if is_complex else None,
                value_unit=None if is_complex else "a.u.",
            ),
        ),
    )
    return Dataset(
        data, kind=DataKind.SPECTRUM, metadata=metadata, provenance=_raw_node(node_id, source)
    )


def _ratio(a: Dataset, b: Dataset, **params: object) -> Dataset:
    return get_step("spectrum.ratio")(**params).apply({"primary": a, "secondary": b})


# -- science: known-answer ratios --------------------------------------------- #


def test_real_channel_ratio() -> None:
    a = _spectrum_dataset(np.full(30, 4.0), harmonic=None)
    b = _spectrum_dataset(np.full(30, 2.0), node_id="raw_b", harmonic=None)
    result = _ratio(a, b, channel="O2")
    assert "O2_ratio" in result.channel_names
    assert result.is_complex("O2_ratio") is False
    np.testing.assert_allclose(result.channel("O2_ratio").values, 2.0)
    assert result.metadata.channel("O2_ratio").value_unit == "a.u."


def test_complex_channel_ratio_is_amplitude_ratio() -> None:
    a = _spectrum_dataset((3.0 * np.exp(1j * 0.4 * np.ones(30))).astype(np.complex64))
    b = _spectrum_dataset(
        (1.5 * np.exp(1j * 1.9 * np.ones(30))).astype(np.complex64), node_id="raw_b"
    )
    result = _ratio(a, b, channel="O2")
    np.testing.assert_allclose(result.channel("O2_ratio").values, 2.0, rtol=1e-5)


def test_inputs_are_not_mutated() -> None:
    a = _spectrum_dataset(np.full(30, 4.0), harmonic=None)
    b = _spectrum_dataset(np.full(30, 2.0), node_id="raw_b", harmonic=None)
    a_before = np.array(a.channel("O2").values, copy=True)
    b_before = np.array(b.channel("O2").values, copy=True)
    _ratio(a, b, channel="O2")
    np.testing.assert_array_equal(a.channel("O2").values, a_before)
    np.testing.assert_array_equal(b.channel("O2").values, b_before)


# -- provenance: both parents referenced -------------------------------------- #


def test_provenance_references_both_parents() -> None:
    a = _spectrum_dataset(np.full(30, 4.0), harmonic=None)
    b = _spectrum_dataset(np.full(30, 2.0), node_id="raw_b", harmonic=None)
    result = _ratio(a, b, channel="O2")
    node = result.provenance
    assert node.record.step_id == "spectrum.ratio"
    assert set(node.inputs) == {"primary", "secondary"}
    assert node.inputs["primary"] is a.provenance
    assert node.inputs["secondary"] is b.provenance
    node_ids = {n.node_id for n in node.iter_nodes()}
    assert {"n0", "raw_b"} <= node_ids


# -- compatibility: refuse, never reconcile ----------------------------------- #


def test_different_wavenumber_axis_is_refused() -> None:
    a = _spectrum_dataset(np.full(30, 4.0), harmonic=None)
    b = _spectrum_dataset(np.full(30, 2.0), wn=_WN + 1.0, node_id="raw_b", harmonic=None)
    step = get_step("spectrum.ratio")(channel="O2")
    problems = step.check_compatibility({"primary": a, "secondary": b})
    assert any("wavenumber" in p for p in problems)
    with pytest.raises(ProcessingError, match="incompatible inputs"):
        step.apply({"primary": a, "secondary": b})


def test_missing_channel_is_refused() -> None:
    a = _spectrum_dataset(np.full(30, 4.0), harmonic=None)
    b = _spectrum_dataset(np.full(30, 2.0), node_id="raw_b", channel="O3", harmonic=None)
    step = get_step("spectrum.ratio")(channel="O2")
    problems = step.check_compatibility({"primary": a, "secondary": b})
    assert any("not in measurement B" in p for p in problems)
    with pytest.raises(ProcessingError, match="incompatible inputs"):
        step.apply({"primary": a, "secondary": b})


def test_complex_vs_real_channel_is_refused() -> None:
    a = _spectrum_dataset((3.0 * np.exp(1j * 0.4 * np.ones(30))).astype(np.complex64))
    b = _spectrum_dataset(np.full(30, 2.0), node_id="raw_b", harmonic=None)
    step = get_step("spectrum.ratio")(channel="O2")
    problems = step.check_compatibility({"primary": a, "secondary": b})
    assert any("complex in one measurement" in p for p in problems)


def test_required_capabilities() -> None:
    assert get_step("spectrum.ratio").required_capabilities == (Capability.SPECTRAL,)
