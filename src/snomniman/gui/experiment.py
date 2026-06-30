"""The experiment-level presenter: many measurements, read as one experiment (Qt-free).

Where :class:`~snomniman.gui.model.ExplorerModel` presents *one* measurement,
``ExperimentModel`` presents a *project* of measurements as a single experiment. It
is a thin, read-only **aggregator**: it composes facts the per-measurement models
and the backend already produce - render data (``viz``), per-pixel values, region /
line measurements (``viz.measure`` via each ``ExplorerModel``), and diagnostics
(``snomniman.diagnostics``) - into experiment-wide views:

* a **browser** overview (one cheap, metadata-only row per measurement);
* **cross-measurement comparison** panes + a combined cursor readout (rendered by
  each measurement's own model, shown through the existing comparison viewer);
* an **experiment diagnostics** table (best/worst scans at a glance); and
* **cross-measurement statistics** - the same ROI or line evaluated on every
  selected measurement.

It computes no new science and creates nothing: no new datasets, no provenance
nodes, no processing (Phase 2B is read-only; derived/difference datasets are the
separate Phase 2C). Like ``model.py`` it imports no GUI toolkit, so all of this is
unit-testable without a display, and the widgets that consume it stay thin (Rule 4).
``diagnose`` results are cached per dataset (datasets are immutable, so the cache is
always valid) to keep repeated experiment views cheap.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

import numpy as np

from snomniman import viz
from snomniman.core import Dataset
from snomniman.diagnostics import diagnose
from snomniman.diagnostics.descriptors import HARMONIC_SIGNAL, MeasurementDiagnostics
from snomniman.viz import RenderData

from .model import CursorReadout, CursorValue, ExplorerModel, MeasurementSession, PaneSpec

#: A region geometry in canonical nm: a rectangle ``(x0, y0, x1, y1)`` or polygon vertices.
RegionGeometry = tuple[float, float, float, float] | Sequence[tuple[float, float]]

# --------------------------------------------------------------------------- #
# View value objects (plain data the widgets render verbatim)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ExperimentRow:
    """One measurement's at-a-glance summary for the experiment browser.

    Deliberately **cheap** - every field comes from metadata / channel structure,
    never from ``diagnose`` - so the browser stays fast as it refreshes. The
    heavier, diagnose-backed quality numbers live in :class:`ExperimentTable`
    (the Experiment diagnostics view), computed only when that view is opened.
    """

    index: int
    measurement_id: str
    title: str
    datetime: str | None
    processing: str  # "raw" / "N steps"
    harmonics: str  # optical signal orders, e.g. "2, 3" (or "-")
    has_reference: bool


@dataclass(frozen=True)
class ComparisonPane:
    """One pane of a cross-measurement comparison: which measurement, its spec + render."""

    index: int  # the measurement this pane shows
    spec: PaneSpec  # label carries the measurement title (disambiguates identical channels)
    render: RenderData


@dataclass(frozen=True)
class ExperimentColumn:
    """A column header for an experiment table (a quantity compared across measurements)."""

    label: str
    unit: str | None = None


@dataclass(frozen=True)
class ExperimentCell:
    """One table cell: display ``text`` plus an optional numeric key for sorting."""

    text: str
    value: float | None = None  # numeric sort key; None sorts as missing/last


@dataclass(frozen=True)
class ExperimentTableRow:
    """One measurement's row in an experiment table."""

    measurement_id: str
    title: str
    cells: tuple[ExperimentCell, ...]


@dataclass(frozen=True)
class ExperimentTable:
    """A sortable, exportable comparison: rows = measurements, columns = quantities."""

    title: str
    columns: tuple[ExperimentColumn, ...]
    rows: tuple[ExperimentTableRow, ...]


# --------------------------------------------------------------------------- #
# The presenter
# --------------------------------------------------------------------------- #


class ExperimentModel:
    """Read-only presenter aggregating a project's measurements as one experiment."""

    def __init__(self, sessions: Sequence[MeasurementSession]) -> None:
        self._sessions: list[MeasurementSession] = list(sessions)
        # diagnose() is deterministic per dataset; cache by dataset identity so the
        # browser / diagnostics views stay cheap across refreshes. Datasets are
        # immutable, so a cache entry never goes stale.
        self._diag_cache: dict[int, MeasurementDiagnostics] = {}

    def set_sessions(self, sessions: Sequence[MeasurementSession]) -> None:
        """Point at the project's current sessions (keeps the diagnose cache)."""
        self._sessions = list(sessions)

    @property
    def count(self) -> int:
        return len(self._sessions)

    def titles(self) -> list[str]:
        return [s.title for s in self._sessions]

    # -- experiment browser (Part 3: cheap, metadata-only) --------------------

    def browser_rows(self) -> list[ExperimentRow]:
        """One summary row per measurement (no diagnose - kept cheap for frequent refresh)."""
        rows: list[ExperimentRow] = []
        for index, s in enumerate(self._sessions):
            ds = s.model.dataset
            rows.append(
                ExperimentRow(
                    index=index,
                    measurement_id=s.measurement_id,
                    title=s.title,
                    datetime=ds.metadata.acquisition.datetime,
                    processing=_processing_label(len(s.history)),
                    harmonics=_harmonics_label(ds),
                    has_reference=_has_reference(ds),
                )
            )
        return rows

    # -- cross-measurement comparison (Part 1: reuses the comparison viewer) ---

    def shared_channels(self, indices: Sequence[int]) -> list[str]:
        """Channels present in *every* selected measurement (ordered by the first)."""
        models = [self._sessions[i].model for i in indices if 0 <= i < self.count]
        if not models:
            return []
        common = set(models[0].dataset.channel_names)
        for m in models[1:]:
            common &= set(m.dataset.channel_names)
        return [c for c in models[0].dataset.channel_names if c in common]

    def comparison_panes(
        self, indices: Sequence[int], channel: str, representation: str
    ) -> list[ComparisonPane]:
        """A pane per selected measurement showing ``channel`` (rendered by its own model).

        Each pane's :class:`PaneSpec` is labelled with the measurement title, which
        both names the pane and disambiguates otherwise-identical specs so a
        dict-based renderer (the existing comparison-viewer contract) has unique keys.
        """
        panes: list[ComparisonPane] = []
        for i in indices:
            if not 0 <= i < self.count:
                continue
            m = self._sessions[i].model
            if channel not in m.dataset.channel_names:
                continue
            rep = self._valid_rep(m, channel, representation)
            spec = PaneSpec(channel, rep, label=f"{self._sessions[i].title}: {channel}")
            panes.append(ComparisonPane(index=i, spec=spec, render=m.render_spec(spec)))
        return panes

    def comparison_readout(
        self, indices: Sequence[int], channel: str, representation: str, x_nm: float, y_nm: float
    ) -> CursorReadout:
        """Each selected measurement's value of ``channel`` at one physical point."""
        values: list[CursorValue] = []
        in_bounds = False
        rx, ry = x_nm, y_nm
        for i in indices:
            if not 0 <= i < self.count:
                continue
            s = self._sessions[i]
            if channel not in s.model.dataset.channel_names:
                continue
            rep = self._valid_rep(s.model, channel, representation)
            readout = s.model.values_at([PaneSpec(channel, rep)], x_nm, y_nm)
            if readout.in_bounds:
                in_bounds = True
                rx, ry = readout.x_nm, readout.y_nm
                values.extend(
                    CursorValue(label=f"{s.title}: {v.label}", value=v.value, unit=v.unit)
                    for v in readout.values
                )
        return CursorReadout(in_bounds=in_bounds, x_nm=rx, y_nm=ry, values=tuple(values))

    # -- experiment diagnostics (Part 4: reuses diagnose, cached) -------------

    def diagnostics_table(self) -> ExperimentTable:
        """Project-wide diagnostics: roughness, tilt, signal harmonics, reference, per scan.

        Reuses the Scientific Diagnostics Engine (``diagnose``) for each measurement
        (cached). Sorting the rendered table lets a researcher find the smoothest /
        flattest / highest-contrast scans, or spot incomplete ones.
        """
        diags = [(s, self._diagnostics(s.model.dataset)) for s in self._sessions]
        topo_unit = next(
            (d.topography.unit for _, d in diags if d.topography and d.topography.unit), None
        )
        columns = (
            ExperimentColumn("Processing"),
            ExperimentColumn("Roughness Sq", topo_unit),
            ExperimentColumn("Tilt", f"{topo_unit}/um" if topo_unit else "/um"),
            ExperimentColumn("Signal harmonics"),
            ExperimentColumn("Reference"),
        )
        rows = tuple(
            ExperimentTableRow(
                measurement_id=s.measurement_id,
                title=s.title,
                cells=(
                    ExperimentCell(_processing_label(len(s.history)), float(len(s.history))),
                    _roughness_cell(diag),
                    _tilt_cell(diag),
                    _signal_harmonics_cell(diag),
                    _reference_cell(s.model.dataset),
                ),
            )
            for s, diag in diags
        )
        return ExperimentTable("Experiment diagnostics", columns, rows)

    # -- cross-measurement statistics (Part 5: reuses viz.measure) ------------

    def compare_region(
        self,
        indices: Sequence[int],
        kind: str,
        geometry: RegionGeometry,
        channel: str,
        representation: str,
    ) -> ExperimentTable:
        """The same region's statistics for ``channel``, on every selected measurement.

        ``kind`` is ``"rectangle"`` (``geometry`` = ``(x0, y0, x1, y1)`` in nm) or
        ``"polygon"`` (``geometry`` = a vertex list). The region is evaluated against
        each measurement's own grid (the ``viz`` masks clip to it), so a measurement
        that does not cover the region simply yields no finite pixels - honest, not
        an error. Whether the region is *meaningful* across these scans is the
        researcher's scientific call.
        """
        rows: list[ExperimentTableRow] = []
        unit: str | None = None
        for i in indices:
            if not 0 <= i < self.count:
                continue
            s = self._sessions[i]
            if channel not in s.model.dataset.channel_names:
                continue
            spec = PaneSpec(channel, self._valid_rep(s.model, channel, representation))
            if kind == "rectangle":
                x0, y0, x1, y1 = cast("tuple[float, float, float, float]", geometry)
                report = s.model.rect_statistics([spec], x0, y0, x1, y1)
            else:
                vertices = list(cast("Sequence[tuple[float, float]]", geometry))
                report = s.model.polygon_statistics([spec], vertices)
            stat = report.rows[0]
            unit = stat.unit
            st = stat.stats
            rows.append(
                ExperimentTableRow(
                    measurement_id=s.measurement_id,
                    title=s.title,
                    cells=(
                        _num_cell(st.mean),
                        _num_cell(st.median),
                        _num_cell(st.minimum),
                        _num_cell(st.maximum),
                        _num_cell(st.std),
                    ),
                )
            )
        columns = (
            ExperimentColumn("Mean", unit),
            ExperimentColumn("Median", unit),
            ExperimentColumn("Min", unit),
            ExperimentColumn("Max", unit),
            ExperimentColumn("Std", unit),
        )
        return ExperimentTable(f"{channel} {kind} statistics", columns, tuple(rows))

    def compare_profile(
        self,
        indices: Sequence[int],
        p0: tuple[float, float],
        p1: tuple[float, float],
        channel: str,
        representation: str,
    ) -> ExperimentTable:
        """The same line's profile summary for ``channel``, on every selected measurement."""
        rows: list[ExperimentTableRow] = []
        unit: str | None = None
        for i in indices:
            if not 0 <= i < self.count:
                continue
            s = self._sessions[i]
            if channel not in s.model.dataset.channel_names:
                continue
            spec = PaneSpec(channel, self._valid_rep(s.model, channel, representation))
            profile = s.model.line_profile([spec], p0, p1)
            curve = profile.curves[0]
            unit = curve.unit
            samples = np.asarray(curve.samples, dtype=np.float64)
            rows.append(
                ExperimentTableRow(
                    measurement_id=s.measurement_id,
                    title=s.title,
                    cells=(
                        _num_cell(profile.distance_nm),
                        _num_cell(_nan_stat(np.nanmean, samples)),
                        _num_cell(_nan_stat(np.nanmin, samples)),
                        _num_cell(_nan_stat(np.nanmax, samples)),
                    ),
                )
            )
        columns = (
            ExperimentColumn("Length", "nm"),
            ExperimentColumn("Mean", unit),
            ExperimentColumn("Min", unit),
            ExperimentColumn("Max", unit),
        )
        return ExperimentTable(f"{channel} line profile", columns, tuple(rows))

    # -- internals ------------------------------------------------------------

    def _diagnostics(self, dataset: Dataset) -> MeasurementDiagnostics:
        key = id(dataset)
        cached = self._diag_cache.get(key)
        if cached is None:
            cached = diagnose(dataset)
            self._diag_cache[key] = cached
        return cached

    @staticmethod
    def _valid_rep(model: ExplorerModel, channel: str, representation: str) -> str:
        """The requested representation if available for ``channel``, else its default."""
        available = viz.available_representations(model.dataset, channel)
        if representation in available:
            return representation
        return viz.default_representation(model.dataset, channel)


# --------------------------------------------------------------------------- #
# Helpers (plain functions; the presenter stays a thin aggregator)
# --------------------------------------------------------------------------- #


def _processing_label(steps: int) -> str:
    if steps <= 0:
        return "raw"
    return f"{steps} step{'s' if steps != 1 else ''}"


def _optical_signal_orders(ds: Dataset) -> list[int]:
    present = set(ds.channel_names)
    return sorted(
        {
            c.harmonic
            for c in ds.metadata.channels
            if c.kind == "optical"
            and c.role == "signal"
            and c.harmonic is not None
            and c.canonical in present
        }
    )


def _harmonics_label(ds: Dataset) -> str:
    orders = _optical_signal_orders(ds)
    return ", ".join(str(o) for o in orders) if orders else "-"


def _has_reference(ds: Dataset) -> bool:
    present = set(ds.channel_names)
    return any(c.role == "reference" and c.canonical in present for c in ds.metadata.channels)


def _roughness_cell(diag: MeasurementDiagnostics) -> ExperimentCell:
    topo = diag.topography
    if topo is None or topo.rms_roughness is None:
        return ExperimentCell("-", None)
    return ExperimentCell(f"{topo.rms_roughness:.3g}", float(topo.rms_roughness))


def _tilt_cell(diag: MeasurementDiagnostics) -> ExperimentCell:
    topo = diag.topography
    if topo is None:
        return ExperimentCell("-", None)
    return ExperimentCell(f"{topo.slope_magnitude_per_um:.3g}", float(topo.slope_magnitude_per_um))


def _signal_harmonics_cell(diag: MeasurementDiagnostics) -> ExperimentCell:
    harm = diag.harmonics
    if harm is None:
        return ExperimentCell("-", None)
    signal = [a.order for a in harm.amplitudes if a.classification == HARMONIC_SIGNAL]
    if not signal:
        return ExperimentCell("none", 0.0)
    return ExperimentCell(", ".join(f"O{o}" for o in signal), float(len(signal)))


def _reference_cell(ds: Dataset) -> ExperimentCell:
    has = _has_reference(ds)
    return ExperimentCell("yes" if has else "no", 1.0 if has else 0.0)


def _num_cell(value: float | None, fmt: str = "{:.4g}") -> ExperimentCell:
    if value is None or not np.isfinite(value):
        return ExperimentCell("-", None)
    return ExperimentCell(fmt.format(value), float(value))


def _nan_stat(fn: object, samples: np.ndarray) -> float | None:
    """Apply a nan-aware reducer, returning ``None`` for an all-NaN / empty line."""
    if samples.size == 0 or not np.any(np.isfinite(samples)):
        return None
    return float(fn(samples))  # type: ignore[operator]


__all__ = [
    "ComparisonPane",
    "ExperimentCell",
    "ExperimentColumn",
    "ExperimentModel",
    "ExperimentRow",
    "ExperimentTable",
    "ExperimentTableRow",
]
