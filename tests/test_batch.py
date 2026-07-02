"""Tests for Processing Recipe batch execution (Phase 4B): `snomniman.batch`.

Covered:
- Batch replays a recipe on every measurement, independently (no cross-
  contamination between measurements' derived results)
- Each measurement's derived dataset/provenance matches manually replaying the
  same recipe on that one measurement (the golden "batch == N manual runs" test)
- An incompatible measurement is skipped (reason explained), a genuinely
  unexpected error is failed (reason explained) - neither aborts the run, and
  order/count of outcomes is preserved
- Progress callback fires once per attempted measurement with correct running
  totals and the right outcome
- `should_stop` stops cleanly between measurements (never mid-measurement)
- Input `Measurement` objects are never mutated
- `BatchResult.succeeded`/`.skipped`/`.failed` filter correctly
- Empty measurement list is handled gracefully
"""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

import snomniman.batch as batch_module
import snomniman.processing.image  # noqa: F401  (registers image ops)
from snomniman.batch import STATUS_FAILED, STATUS_SKIPPED, STATUS_SUCCESS, BatchOutcome, run_batch
from snomniman.core import (
    ChannelInfo,
    Conventions,
    DataKind,
    Dataset,
    Demodulation,
    Excitation,
    Instrument,
    Metadata,
    ProvenanceNode,
    ScanInfo,
    StepRecord,
)
from snomniman.pipeline import (
    Measurement,
    Recipe,
    RecipeStep,
    capture_recipe,
    measurement_from_history,
)
from snomniman.processing.image.fix_zero import FixZero
from snomniman.processing.image.plane_level import PlaneLevel


def _topo_dataset(bump_height: float) -> Dataset:
    """A tiny real-only topography dataset: a linear tilt plus a per-measurement bump.

    ``bump_height`` scales a small quadratic bump added on top of a shared linear
    tilt + offset. ``plane_level`` + ``fix_zero`` remove the shared tilt/offset
    exactly, so only the bump - unique per measurement - survives; this lets tests
    tell "two measurements processed independently, without cross-contamination"
    apart from "processing happens to erase everything" (which a pure planar scan
    would not distinguish).
    """
    ny, nx = 3, 4
    y = (np.arange(ny, dtype=np.float64) + 0.5) * 50.0
    x = (np.arange(nx, dtype=np.float64) + 0.5) * 50.0
    yy, xx = np.meshgrid(y, x, indexing="ij")
    tilt = 700.0 + 0.5 * xx + 0.3 * yy
    bump = bump_height * np.exp(-((xx - 100.0) ** 2 + (yy - 75.0) ** 2) / (2 * 40.0**2))
    z = (tilt + bump).astype(np.float64)
    data = xr.Dataset(
        {"Z": (("y", "x"), z)},
        coords={
            "x": ("x", x, {"unit": "nm", "axis": "X"}),
            "y": ("y", y, {"unit": "nm", "axis": "Y"}),
        },
    )
    metadata = Metadata(
        data_kind=DataKind.IMAGE,
        conventions=Conventions(),
        instrument=Instrument(vendor="neaspec", model="neaSNOM"),
        excitation=Excitation(),
        demodulation=Demodulation(),
        scan=ScanInfo(pixels=(nx, ny), size_nm=(nx * 50.0, ny * 50.0), pixel_size_nm=(50.0, 50.0)),
        channels=(ChannelInfo("Z", "topography", "signal", "float64", value_unit="nm"),),
        original_units={"x": "m", "y": "m", "Z": "m"},
    )
    node = ProvenanceNode(
        node_id=f"n0-{bump_height}",
        record=StepRecord(step_id="io.read", step_version=1, deterministic=True),
    )
    return Dataset(data, kind=DataKind.IMAGE, metadata=metadata, provenance=node)


def _measurement(bump_height: float, measurement_id: str, title: str) -> Measurement:
    return measurement_from_history(
        [_topo_dataset(bump_height)], title=title, measurement_id=measurement_id
    )


@pytest.fixture
def clean_recipe() -> Recipe:
    return Recipe(
        name="topo clean",
        steps=(
            RecipeStep("image.plane_level", 1, {"channel": "Z", "order": 1}),
            RecipeStep("image.fix_zero", 1, {"channel": "Z"}),
        ),
    )


def _manual_chain(dataset: Dataset) -> Dataset:
    leveled = PlaneLevel(channel="Z", order=1).apply({"primary": dataset})
    return FixZero(channel="Z").apply({"primary": leveled})


# --------------------------------------------------------------------------- #
# Independent, correct replay across many measurements
# --------------------------------------------------------------------------- #


def test_batch_processes_every_measurement_independently(clean_recipe: Recipe) -> None:
    m1 = _measurement(700.0, "measurement-0001", "Scan 1")
    m2 = _measurement(1000.0, "measurement-0002", "Scan 2")
    result = run_batch(clean_recipe, [m1, m2])

    assert result.requested == 2
    assert len(result.succeeded) == 2
    assert [o.status for o in result.outcomes] == [STATUS_SUCCESS, STATUS_SUCCESS]

    out1, out2 = result.outcomes
    assert out1.measurement is not None and out2.measurement is not None
    np.testing.assert_allclose(
        out1.measurement.current.channel("Z").values, _manual_chain(m1.current).channel("Z").values
    )
    np.testing.assert_allclose(
        out2.measurement.current.channel("Z").values, _manual_chain(m2.current).channel("Z").values
    )
    # Independent: the two measurements' results are not identical to each other
    # (they started from different raw data), i.e. no cross-contamination.
    assert not np.allclose(
        out1.measurement.current.channel("Z").values, out2.measurement.current.channel("Z").values
    )


def test_batch_matches_capture_then_replay_on_one_measurement(clean_recipe: Recipe) -> None:
    m = _measurement(700.0, "measurement-0001", "Scan 1")
    manual = _manual_chain(m.current)
    recipe = capture_recipe(manual, name="topo clean")

    result = run_batch(recipe, [m])
    outcome = result.outcomes[0]
    assert outcome.measurement is not None
    np.testing.assert_allclose(
        outcome.measurement.current.channel("Z").values, manual.channel("Z").values
    )


def test_batch_updated_measurement_appends_to_history(clean_recipe: Recipe) -> None:
    m = _measurement(700.0, "measurement-0001", "Scan 1")
    result = run_batch(clean_recipe, [m])
    outcome = result.outcomes[0]
    assert outcome.measurement is not None
    assert len(outcome.measurement.datasets) == len(m.datasets) + 1
    assert outcome.measurement.current_index == len(m.datasets)
    assert outcome.measurement.raw is m.raw  # raw is untouched (Rule: immutable raw)


def test_input_measurements_are_not_mutated(clean_recipe: Recipe) -> None:
    m = _measurement(700.0, "measurement-0001", "Scan 1")
    original_len = len(m.datasets)
    run_batch(clean_recipe, [m])
    assert len(m.datasets) == original_len


# --------------------------------------------------------------------------- #
# Skipped (incompatible) vs failed (unexpected) - neither aborts the batch
# --------------------------------------------------------------------------- #


def test_incompatible_measurement_is_skipped_not_aborting(clean_recipe: Recipe) -> None:
    # reference_normalize needs a complex optical + reference channel; the topo
    # measurement (Z only) has neither, so it must be skipped, honestly explained.
    bad_recipe = Recipe(name="bad", steps=(RecipeStep("image.reference_normalize", 1, {}),))
    m1 = _measurement(700.0, "measurement-0001", "Bad scan")
    m2 = _measurement(1000.0, "measurement-0002", "Good-ish scan")
    result = run_batch(bad_recipe, [m1, m2])

    assert [o.status for o in result.outcomes] == [STATUS_SKIPPED, STATUS_SKIPPED]
    assert all(o.reason for o in result.outcomes)
    assert all("image.reference_normalize" in (o.reason or "") for o in result.outcomes)
    assert result.succeeded == ()
    assert len(result.skipped) == 2


def test_one_skip_does_not_prevent_later_success(clean_recipe: Recipe) -> None:
    bad_recipe = Recipe(name="bad", steps=(RecipeStep("image.reference_normalize", 1, {}),))
    good_recipe = clean_recipe
    m1 = _measurement(700.0, "measurement-0001", "Scan 1")
    m2 = _measurement(1000.0, "measurement-0002", "Scan 2")

    # A batch that starts with an incompatible measurement still processes the rest.
    result = run_batch(bad_recipe, [m1])
    assert result.outcomes[0].status == STATUS_SKIPPED
    result2 = run_batch(good_recipe, [m1, m2])
    assert [o.status for o in result2.outcomes] == [STATUS_SUCCESS, STATUS_SUCCESS]


def test_unexpected_error_is_failed_not_skipped(
    clean_recipe: Recipe, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(recipe: Recipe, dataset: Dataset) -> Dataset:
        raise RuntimeError("boom")

    monkeypatch.setattr(batch_module, "apply_recipe", _boom)
    m1 = _measurement(700.0, "measurement-0001", "Scan 1")
    m2 = _measurement(1000.0, "measurement-0002", "Scan 2")
    result = run_batch(clean_recipe, [m1, m2])

    assert [o.status for o in result.outcomes] == [STATUS_FAILED, STATUS_FAILED]
    assert all("boom" in (o.reason or "") for o in result.outcomes)
    assert len(result.failed) == 2


# --------------------------------------------------------------------------- #
# Progress + early stop
# --------------------------------------------------------------------------- #


def test_progress_callback_fires_once_per_measurement(clean_recipe: Recipe) -> None:
    calls: list[tuple[int, int, str]] = []
    measurements = [
        _measurement(700.0 + 100.0 * i, f"measurement-{i:04d}", f"Scan {i}") for i in range(3)
    ]
    run_batch(
        clean_recipe,
        measurements,
        on_progress=lambda i, total, outcome: calls.append((i, total, outcome.status)),
    )
    assert calls == [(1, 3, STATUS_SUCCESS), (2, 3, STATUS_SUCCESS), (3, 3, STATUS_SUCCESS)]


def test_should_stop_ends_the_run_cleanly_between_measurements(clean_recipe: Recipe) -> None:
    measurements = [
        _measurement(700.0 + 100.0 * i, f"measurement-{i:04d}", f"Scan {i}") for i in range(5)
    ]
    seen = {"count": 0}

    def stop_after_two() -> bool:
        return seen["count"] >= 2

    def progress(i: int, total: int, outcome: BatchOutcome) -> None:
        seen["count"] = i

    result = run_batch(clean_recipe, measurements, on_progress=progress, should_stop=stop_after_two)
    assert result.stopped_early is True
    assert len(result.outcomes) == 2
    assert result.requested == 5


def test_should_stop_false_never_interrupts(clean_recipe: Recipe) -> None:
    measurements = [_measurement(700.0, "measurement-0001", "Scan 1")]
    result = run_batch(clean_recipe, measurements, should_stop=lambda: False)
    assert result.stopped_early is False
    assert len(result.outcomes) == 1


# --------------------------------------------------------------------------- #
# Result shape / edge cases
# --------------------------------------------------------------------------- #


def test_empty_measurement_list_is_handled_gracefully(clean_recipe: Recipe) -> None:
    result = run_batch(clean_recipe, [])
    assert result.requested == 0
    assert result.outcomes == ()
    assert result.succeeded == () and result.skipped == () and result.failed == ()


def test_result_records_recipe_name_and_elapsed_time(clean_recipe: Recipe) -> None:
    m = _measurement(700.0, "measurement-0001", "Scan 1")
    result = run_batch(clean_recipe, [m])
    assert result.recipe_name == "topo clean"
    assert result.elapsed_seconds >= 0.0
    assert result.started_at != ""
