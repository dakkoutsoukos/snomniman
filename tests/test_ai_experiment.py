"""Tests for snomniman.ai.experiment - the Experiment Briefing + outlier detection
(Phase 9A/9B, docs/phase7-9-master-roadmap.md Section 5).

Grounding is verified the same way test_ai_briefing.py verifies the single-measurement
Briefing: every statement cites only `description`/`diagnostics`. Outlier arithmetic is
checked against an independently computed mean/std/z-score, not just "it ran."
"""

from __future__ import annotations

import math

import numpy as np
import xarray as xr

from snomniman.ai import (
    FACT,
    ExperimentBriefing,
    OutlierReport,
    build_experiment_briefing,
    detect_outliers,
)
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
from snomniman.pipeline import Measurement, Project

_ALLOWED_SOURCES = {"description", "diagnostics"}

#: A fixed, zero-mean, non-planar 3x4 pattern (checkerboard): a plane fit over it
#: recovers ~zero tilt, so the post-fit RMS roughness scales with the amplitude it
#: is multiplied by - giving fully controllable, predictable roughness per fixture.
_PATTERN = np.array(
    [[1.0, -1.0, 1.0, -1.0], [-1.0, 1.0, -1.0, 1.0], [1.0, -1.0, 1.0, -1.0]]
)


def _topo_dataset(noise_amplitude: float) -> Dataset:
    ny, nx = _PATTERN.shape
    y = (np.arange(ny, dtype=np.float64) + 0.5) * 50.0
    x = (np.arange(nx, dtype=np.float64) + 0.5) * 50.0
    z = 800.0 + noise_amplitude * _PATTERN
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
        node_id="n0", record=StepRecord(step_id="io.read", step_version=1, deterministic=True)
    )
    return Dataset(data, kind=DataKind.IMAGE, metadata=metadata, provenance=node)


def _measurement(measurement_id: str, title: str, noise_amplitude: float) -> Measurement:
    return Measurement(measurement_id, title, (_topo_dataset(noise_amplitude),))


def _project(*noise_amplitudes: float) -> Project:
    measurements = tuple(
        _measurement(f"measurement-{i:04d}", f"m{i}", amp)
        for i, amp in enumerate(noise_amplitudes)
    )
    return Project(title="Test experiment", measurements=measurements)


# -- Experiment Briefing ------------------------------------------------------ #


def test_experiment_briefing_reports_measurement_count_and_composition() -> None:
    project = _project(1.0, 2.0, 3.0)
    briefing = build_experiment_briefing(project)
    assert isinstance(briefing, ExperimentBriefing)
    assert briefing.n_measurements == 3
    assert briefing.context.measurement_ids == (
        "measurement-0000",
        "measurement-0001",
        "measurement-0002",
    )
    summary = next(s for s in briefing.sections if s.title == "Experiment Summary")
    text = " ".join(st.text for st in summary.statements)
    assert "3 measurement(s)" in text
    assert "3 image" in text


def test_experiment_briefing_every_statement_is_grounded() -> None:
    project = _project(1.0, 2.0, 3.0)
    briefing = build_experiment_briefing(project)
    for section in briefing.sections:
        for st in section.statements:
            assert st.kind == FACT
            assert st.sources, f"statement not grounded: {st.text!r}"
            assert set(st.sources) <= _ALLOWED_SOURCES


def test_experiment_briefing_context_has_one_entry_per_measurement() -> None:
    project = _project(1.0, 2.0)
    briefing = build_experiment_briefing(project)
    assert set(briefing.context.per_measurement) == {"measurement-0000", "measurement-0001"}
    for entry in briefing.context.per_measurement.values():
        assert "description" in entry and "diagnostics" in entry


def test_experiment_briefing_to_dict_round_trips_through_json() -> None:
    import json

    project = _project(1.0, 2.0, 3.0)
    briefing = build_experiment_briefing(project, title="My experiment")
    payload = json.loads(json.dumps(briefing.to_dict()))
    assert payload["title"] == "My experiment"
    assert payload["n_measurements"] == 3


def test_experiment_briefing_narrates_a_flagged_outlier() -> None:
    # Three consistent measurements + one wildly rougher one -> the Cross-Measurement
    # Observations section should name it, not just detect_outliers() in isolation.
    project = _project(1.0, 1.0, 1.0, 1.0, 30.0)
    briefing = build_experiment_briefing(project)
    observations = next(s for s in briefing.sections if s.title == "Cross-Measurement Observations")
    text = " ".join(st.text for st in observations.statements)
    assert "m4" in text  # the 5th measurement (index 4), the outlier
    assert "standard deviations" in text


# -- detect_outliers ----------------------------------------------------------- #


def test_detect_outliers_flags_a_clear_outlier() -> None:
    project = _project(1.0, 1.0, 1.0, 1.0, 30.0)
    report = detect_outliers(project)
    assert isinstance(report, OutlierReport)
    roughness_rows = [m for m in report.metrics if m.metric == "topography.rms_roughness"]
    assert len(roughness_rows) == 5

    values = [row.value for row in roughness_rows]
    expected_mean = float(np.mean(values))
    expected_std = float(np.std(values))
    for row in roughness_rows:
        assert math.isclose(row.project_mean, expected_mean, rel_tol=1e-9)
        assert math.isclose(row.project_std, expected_std, rel_tol=1e-9)
        expected_z = (row.value - expected_mean) / expected_std
        assert math.isclose(row.z_score, expected_z, rel_tol=1e-9)

    outlier_row = next(row for row in roughness_rows if row.measurement_id == "measurement-0004")
    assert outlier_row.flagged is True
    assert outlier_row in report.flagged
    for row in roughness_rows:
        if row.measurement_id != "measurement-0004":
            assert row.flagged is False


def test_detect_outliers_skips_metric_with_too_few_measurements() -> None:
    # Only 2 measurements: below _MIN_MEASUREMENTS_FOR_STATISTICS (3).
    project = _project(1.0, 5.0)
    report = detect_outliers(project)
    assert report.metrics == ()
    assert report.flagged == ()
    assert report.note is not None
    assert "topography.rms_roughness" in report.note


def test_detect_outliers_no_flags_when_all_similar() -> None:
    project = _project(1.0, 1.05, 0.95, 1.02)
    report = detect_outliers(project)
    assert report.flagged == ()


def test_outlier_report_to_dict_round_trips_through_json() -> None:
    import json

    project = _project(1.0, 1.0, 1.0, 1.0, 30.0)
    report = detect_outliers(project)
    payload = json.loads(json.dumps(report.to_dict()))
    assert payload["threshold"] == 2.0
    assert len(payload["flagged"]) >= 1
    assert all(row["measurement_id"] == "measurement-0004" for row in payload["flagged"])
