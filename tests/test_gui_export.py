"""Tests for the measurement CSV builders (Qt-free; run in CI without the gui extra).

These exercise the formatting layer directly on constructed result value objects, so
they need no display: correct provenance header, column headers with units, data
values, NaN handling, and the clipboard (tab) delimiter.
"""

from __future__ import annotations

import numpy as np

from snomniman.gui.experiment import (
    ExperimentCell,
    ExperimentColumn,
    ExperimentTable,
    ExperimentTableRow,
)
from snomniman.gui.export import (
    ExperimentExportContext,
    ExportContext,
    experiment_table_to_csv,
    profile_to_csv,
    region_to_csv,
)
from snomniman.gui.model import (
    ProfileCurve,
    ProfileSet,
    RegionReport,
    RegionStatRow,
)
from snomniman.viz import RegionStats

_CONTEXT = ExportContext(
    measurement="CdO raw -> plane level (Z)",
    source_path="data/2026-06-16 CdO",
    source_sha256="ab" * 32,
    conventions="nm - lower-left origin - phase as imported",
    provenance=("io.read", "image.plane_level"),
    snomniman_version="0.1.0",
    created_at="2026-06-29T12:00:00+00:00",
)


def _profile() -> ProfileSet:
    return ProfileSet(
        positions_nm=np.array([0.0, 10.0, 20.0]),
        distance_nm=20.0,
        dx_nm=20.0,
        dy_nm=0.0,
        curves=(
            ProfileCurve("O2 amplitude", "a.u.", np.array([1.0, 2.0, np.nan])),
            ProfileCurve("Z", "nm", np.array([100.0, 110.0, 120.0])),
        ),
    )


def _region() -> RegionReport:
    stats = RegionStats(
        count=12, area_nm2=24000.0, mean=1.5, median=1.4, minimum=0.5, maximum=2.5, std=0.3
    )
    return RegionReport("rectangle", 12, 24000.0, (RegionStatRow("O2 amplitude", "a.u.", stats),))


# -- profile ----------------------------------------------------------------- #


def test_profile_header_carries_provenance() -> None:
    text = profile_to_csv(_profile(), _CONTEXT)
    assert "# Measurement: CdO raw -> plane level (Z)" in text
    assert "# Provenance: io.read -> image.plane_level" in text
    assert "# Geometry: length 20 nm; dx 20 nm; dy 0 nm" in text
    assert f"sha256 {'ab' * 6}" in text  # truncated source hash
    assert "SNOMNIMAN 0.1.0; exported 2026-06-29" in text


def test_profile_table_has_unit_columns_and_values() -> None:
    lines = profile_to_csv(_profile(), _CONTEXT).splitlines()
    rows = [line for line in lines if not line.startswith("#")]
    assert rows[0] == "distance_nm,O2 amplitude [a.u.],Z [nm]"
    assert rows[1] == "0,1,100"
    assert rows[2] == "10,2,110"
    # The NaN amplitude sample becomes an empty cell (Excel/pandas read it as blank).
    assert rows[3] == "20,,120"


def test_profile_clipboard_delimiter_is_tab() -> None:
    text = profile_to_csv(_profile(), _CONTEXT, delimiter="\t")
    data = [line for line in text.splitlines() if not line.startswith("#")]
    assert data[0] == "distance_nm\tO2 amplitude [a.u.]\tZ [nm]"
    assert data[1] == "0\t1\t100"


# -- region ------------------------------------------------------------------ #


def test_region_header_and_table() -> None:
    text = region_to_csv(_region(), _CONTEXT)
    assert "# SNOMNIMAN rectangle region statistics export" in text
    assert "# Region: 12 pixels; area 24000 nm^2" in text
    rows = [line for line in text.splitlines() if not line.startswith("#")]
    assert rows[0] == "channel,unit,mean,median,min,max,std,count,area_nm2"
    assert rows[1] == "O2 amplitude,a.u.,1.5,1.4,0.5,2.5,0.3,12,24000"


# -- experiment comparison table (Phase 2B) ---------------------------------- #


_EXP_CONTEXT = ExperimentExportContext(
    project="CdO experiment",
    measurement_count=2,
    conventions="nm - lower-left origin - phase as imported",
    snomniman_version="0.1.0",
    created_at="2026-06-29T12:00:00+00:00",
)


def _experiment_table() -> ExperimentTable:
    return ExperimentTable(
        title="Experiment diagnostics",
        columns=(
            ExperimentColumn("Roughness Sq", "nm"),
            ExperimentColumn("Signal harmonics"),
            ExperimentColumn("Reference"),
        ),
        rows=(
            ExperimentTableRow(
                "measurement-0001", "CdO full",
                (ExperimentCell("1.23", 1.23), ExperimentCell("O2, O3", 2.0),
                 ExperimentCell("yes", 1.0)),
            ),
            ExperimentTableRow(
                "measurement-0002", "Topo only",
                (ExperimentCell("-", None), ExperimentCell("none", 0.0),
                 ExperimentCell("no", 0.0)),
            ),
        ),
    )


def test_experiment_export_header_and_table() -> None:
    text = experiment_table_to_csv(_experiment_table(), _EXP_CONTEXT)
    assert "# SNOMNIMAN experiment export - Experiment diagnostics" in text
    assert "# Project: CdO experiment" in text
    assert "# Measurements: 2" in text
    rows = [line for line in text.splitlines() if not line.startswith("#")]
    assert rows[0] == "measurement,Roughness Sq [nm],Signal harmonics,Reference"
    # Categorical cells export their text; a comma inside a cell is csv-quoted.
    assert rows[1] == 'CdO full,1.23,"O2, O3",yes'
    assert rows[2] == "Topo only,-,none,no"


def test_experiment_export_clipboard_delimiter_is_tab() -> None:
    text = experiment_table_to_csv(_experiment_table(), _EXP_CONTEXT, delimiter="\t")
    rows = [line for line in text.splitlines() if not line.startswith("#")]
    assert rows[0] == "measurement\tRoughness Sq [nm]\tSignal harmonics\tReference"
    # With a tab delimiter the comma in "O2, O3" needs no quoting.
    assert rows[1] == "CdO full\t1.23\tO2, O3\tyes"
