"""Tests for the hyperspectral band-map render layer (snomniman.viz.render.prepare_band).

The hyperspectral analogue of test_viz_render.py's prepare_channel coverage - same
colormap/levels/extent logic, applied to one wavenumber slice instead of a whole
2-D channel. Also regression-pins that the shared _representation/_finalize_render
refactor underneath both functions left prepare_channel's own output unchanged.
"""

from __future__ import annotations

import numpy as np
import pytest

from snomniman.core import Capability, Dataset
from snomniman.viz import AMPLITUDE, REAL, prepare_band, prepare_channel


def test_hyperspectral_fixture_derives_both_capabilities(hyperspectral_dataset: Dataset) -> None:
    assert hyperspectral_dataset.has_capability(Capability.SPATIAL_2D)
    assert hyperspectral_dataset.has_capability(Capability.SPECTRAL)


def test_prepare_band_matches_direct_slice(hyperspectral_dataset: Dataset) -> None:
    rd = prepare_band(hyperspectral_dataset, "O2", 12, AMPLITUDE)
    expected = np.abs(hyperspectral_dataset.channel("O2").isel(wavenumber=12).values)
    np.testing.assert_allclose(rd.values, expected)
    assert rd.values.shape == (4, 5)  # (y, x) - the cube's spatial shape, sliced


def test_prepare_band_known_peak_pixel_stands_out(hyperspectral_dataset: Dataset) -> None:
    # The embedded resonance (pixel y=2, x=3) is the brightest pixel at its peak band.
    rd = prepare_band(hyperspectral_dataset, "O2", 12, AMPLITUDE)
    y_idx, x_idx = np.unravel_index(np.argmax(rd.values), rd.values.shape)
    assert (int(y_idx), int(x_idx)) == (2, 3)


def test_prepare_band_off_peak_is_flat(hyperspectral_dataset: Dataset) -> None:
    # Far from the resonance (24 cm-1 = 6 half-widths away), every pixel is at or
    # very near the baseline - the Lorentzian's tail hasn't fully vanished, so a
    # loose tolerance (not exact equality) is the honest expectation here.
    rd = prepare_band(hyperspectral_dataset, "O2", 0, AMPLITUDE)
    np.testing.assert_allclose(rd.values, 0.2, atol=0.03)


def test_prepare_band_extent_matches_prepare_channel(hyperspectral_dataset: Dataset) -> None:
    band = prepare_band(hyperspectral_dataset, "O2", 12, AMPLITUDE)
    whole = prepare_channel(hyperspectral_dataset, "O2", AMPLITUDE)
    assert band.extent_nm == whole.extent_nm
    assert band.colormap == whole.colormap
    assert band.unit == whole.unit


def test_prepare_band_rejects_a_channel_with_no_wavenumber_dimension(
    hyperspectral_dataset: Dataset,
) -> None:
    # Z is a plain 2-D real channel in this hyperspectral dataset (topography
    # doesn't vary by wavenumber) - it has no band to slice.
    with pytest.raises(ValueError, match="wavenumber"):
        prepare_band(hyperspectral_dataset, "Z", 0, REAL)


def test_prepare_band_rejects_dataset_without_wavenumber(synthetic_dataset: Dataset) -> None:
    with pytest.raises(ValueError, match="wavenumber"):
        prepare_band(synthetic_dataset, "O2", 0)


def test_prepare_channel_unchanged_by_the_shared_refactor(synthetic_dataset: Dataset) -> None:
    # Regression: prepare_channel's own behavior must be untouched by extracting
    # the shared _representation/_finalize_render helpers.
    rd = prepare_channel(synthetic_dataset, "O2", AMPLITUDE)
    np.testing.assert_allclose(rd.values, np.abs(synthetic_dataset.channel("O2").values))
    assert rd.title == "O2 amplitude (a.u.)"
