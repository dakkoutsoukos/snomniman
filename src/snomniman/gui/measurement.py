"""Interactive quantitative measurements on the image (read-only).

A researcher asks questions *about* a measurement without changing it: how wide is
this particle, how tall, what is the profile across this edge, what are the
statistics of this region. These are **measurements** (observations), not
processing - they never touch the Dataset and never create a derived dataset.

:class:`MeasurementController` places draggable, distinctly-styled overlays (line,
rectangle, polygon) on the single image, recomputes their results live via the
Qt-free model (which does the validated math in :mod:`snomniman.viz.measure`), and
keeps a session history (rename / hide / delete). :class:`MeasurementPanel` shows
the active measurement's profile or statistics across every visible channel
(amplitude, phase, topography) and lists the history. Measurements survive channel
changes - their geometry persists and the results update to the new channel.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

from snomniman.viz import OverlaySpec, ProfileFeatures, RegionComparison

from .export import (
    ExportContext,
    comparison_to_csv,
    profile_to_csv,
    region_to_csv,
)
from .imageview import ChannelImageView
from .model import ExplorerModel, PaneSpec, ProfileSet, RegionReport

SpecsProvider = Callable[[], Sequence[PaneSpec]]

#: Measurement overlays use a distinct amber pen so they never read as data.
_MEASURE_PEN = pg.mkPen("#ffcc33", width=2)
_CURVE_COLORS = ("#46c2ff", "#ffb454", "#7ee787", "#ff7b72", "#d2a8ff", "#79c0ff")
_KIND_LABEL = {"line": "Line", "rectangle": "Rectangle", "polygon": "Polygon"}


class _Measurement:
    """A session measurement: a styled overlay plus its latest computed result."""

    def __init__(self, mid: int, kind: str, name: str, roi: Any) -> None:
        self.id = mid
        self.kind = kind
        self.name = name
        self.visible = True
        self.roi = roi
        self.result: ProfileSet | RegionReport | None = None


class MeasurementController(QtCore.QObject):
    """Creates measurement overlays, recomputes them, and owns the session history."""

    resultChanged = QtCore.Signal()  # the active measurement's result changed
    historyChanged = QtCore.Signal()  # the set/names/visibility changed
    measurementAdded = QtCore.Signal()  # a new measurement was placed (focus its surface)

    def __init__(
        self, model: ExplorerModel, image_view: ChannelImageView, specs: SpecsProvider
    ) -> None:
        super().__init__()
        self._model = model
        self._image = image_view
        self._specs = specs
        self._items: list[_Measurement] = []
        self._active: _Measurement | None = None
        self._next = 1

    # -- history --------------------------------------------------------------

    @property
    def items(self) -> list[_Measurement]:
        return list(self._items)

    @property
    def active(self) -> _Measurement | None:
        return self._active

    def add_line(self) -> None:
        self._add("line")

    def add_rectangle(self) -> None:
        self._add("rectangle")

    def add_polygon(self) -> None:
        self._add("polygon")

    def set_active(self, item: _Measurement) -> None:
        self._active = item
        self.resultChanged.emit()

    def rename(self, item: _Measurement, name: str) -> None:
        item.name = name
        self.historyChanged.emit()

    def set_visible(self, item: _Measurement, visible: bool) -> None:
        item.visible = visible
        item.roi.setVisible(visible)
        self.historyChanged.emit()

    def delete(self, item: _Measurement) -> None:
        self._image.remove_overlay(item.roi)
        self._items.remove(item)
        if self._active is item:
            self._active = self._items[-1] if self._items else None
        self.historyChanged.emit()
        self.resultChanged.emit()

    def clear(self) -> None:
        for item in list(self._items):
            self._image.remove_overlay(item.roi)
        self._items.clear()
        self._active = None
        self.historyChanged.emit()
        self.resultChanged.emit()

    def set_model(self, model: ExplorerModel) -> None:
        """Switch to a new model (e.g. after a processing derivation).

        Clears all session measurements — their geometry is still valid but
        the result values must be recomputed against the new dataset, and the
        old overlays belong to the previous view.
        """
        self.clear()
        self._model = model
        self._specs = model.single_view_specs

    def refresh(self) -> None:
        """Recompute every measurement (e.g. after the active channel changed)."""
        for item in self._items:
            self._recompute(item, emit=False)
        self.resultChanged.emit()

    def overlay_specs(self) -> list[OverlaySpec]:
        """Geometry of the visible measurements, for drawing on an exported figure."""
        view_box = self._image.view_box
        specs: list[OverlaySpec] = []
        for item in self._items:
            if not item.visible:
                continue
            if item.kind == "line":
                p0, p1 = _line_points(item.roi, view_box)
                specs.append(OverlaySpec("line", item.name, (p0, p1)))
            elif item.kind == "rectangle":
                x0, y0, x1, y1 = _rect_bounds(item.roi)
                corners = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
                specs.append(OverlaySpec("rectangle", item.name, corners))
            else:  # polygon
                points = tuple(_poly_vertices(item.roi, view_box))
                specs.append(OverlaySpec("polygon", item.name, points))
        return specs

    # -- session persistence (geometry round-trips with a saved project) ------

    def to_records(self) -> list[dict[str, Any]]:
        """Serialize every measurement (geometry in nm) for the saved session.

        Geometry is read back in canonical nm coordinates - the same read-back the
        figure overlays use - so restoring a project recreates the exact overlays.
        """
        view_box = self._image.view_box
        return [
            {
                "kind": item.kind,
                "name": item.name,
                "visible": item.visible,
                "geometry": _geometry_of(item, view_box),
            }
            for item in self._items
        ]

    def active_geometry(self) -> tuple[str, dict[str, Any]] | None:
        """The active overlay's ``(kind, nm-geometry)``, or ``None`` if there is none.

        Geometry is the same canonical-nm dict :meth:`to_records` records, so the
        experiment presenter can evaluate the *same* ROI/line on every measurement
        (cross-measurement statistics) without the controller knowing about them.
        """
        item = self._active
        if item is None:
            return None
        return item.kind, _geometry_of(item, self._image.view_box)

    def load_records(self, records: Sequence[Mapping[str, Any]]) -> None:
        """Recreate measurements from :meth:`to_records` output (replaces any current)."""
        self.clear()
        for rec in records:
            roi = _make_roi_from_geometry(str(rec["kind"]), dict(rec["geometry"]))
            self._place(str(rec["kind"]), str(rec["name"]), bool(rec.get("visible", True)), roi)

    def export_context(self) -> ExportContext:
        """Identity + provenance facts for a measurement CSV export (from the model)."""
        return self._model.export_context()

    # -- analysis of the active / placed measurements (read-only) --------------

    def profile_features(self) -> ProfileFeatures | None:
        """Peak/width/spacing + descriptive stats of the active line profile, if any."""
        item = self._active
        if item is None or not isinstance(item.result, ProfileSet):
            return None
        return self._model.profile_features(item.result)

    def compare_recent_regions(self) -> RegionComparison | None:
        """Compare the two most recently placed regions (most recent A vs previous B)."""
        reports: list[tuple[str, RegionReport]] = []
        for item in self._items:
            result = item.result
            if isinstance(result, RegionReport):
                reports.append((item.name, result))
        if len(reports) < 2:
            return None
        (name_a, report_a), (name_b, report_b) = reports[-1], reports[-2]
        return self._model.region_comparison(
            report_a, report_b, label_a=name_a, label_b=name_b
        )

    # -- internals ------------------------------------------------------------

    def _add(self, kind: str) -> None:
        roi = _make_roi(kind, self._image.view_box)
        self._place(kind, f"{_KIND_LABEL[kind]} {self._next}", True, roi, focus=True)

    def _place(
        self, kind: str, name: str, visible: bool, roi: Any, *, focus: bool = False
    ) -> None:
        """Adopt a ready-made overlay as a measurement (shared by add + restore)."""
        self._image.add_overlay(roi)
        item = _Measurement(self._next, kind, name, roi)
        item.visible = visible
        roi.setVisible(visible)
        self._next += 1
        roi.sigRegionChanged.connect(lambda *_: self._recompute(item))
        self._items.append(item)
        self._active = item
        self._recompute(item, emit=False)
        if focus:
            self.measurementAdded.emit()
        self.historyChanged.emit()
        self.resultChanged.emit()

    def _recompute(self, item: _Measurement, *, emit: bool = True) -> None:
        specs = self._specs()
        if not specs:
            return
        view_box = self._image.view_box
        if item.kind == "line":
            p0, p1 = _line_points(item.roi, view_box)
            item.result = self._model.line_profile(specs, p0, p1)
        elif item.kind == "rectangle":
            x0, y0, x1, y1 = _rect_bounds(item.roi)
            item.result = self._model.rect_statistics(specs, x0, y0, x1, y1)
        else:  # polygon
            item.result = self._model.polygon_statistics(specs, _poly_vertices(item.roi, view_box))
        if emit and item is self._active:
            self.resultChanged.emit()


# --------------------------------------------------------------------------- #
# ROI construction and geometry read-back (physical nm coordinates)
# --------------------------------------------------------------------------- #


def _make_roi(kind: str, view_box: Any) -> Any:
    (x0, x1), (y0, y1) = view_box.viewRange()
    cx, cy, wx, wy = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
    if kind == "line":
        roi = pg.LineSegmentROI(
            [[cx - 0.25 * wx, cy - 0.1 * wy], [cx + 0.25 * wx, cy + 0.1 * wy]], pen=_MEASURE_PEN
        )
    elif kind == "rectangle":
        roi = pg.RectROI([cx - 0.15 * wx, cy - 0.15 * wy], [0.3 * wx, 0.3 * wy], pen=_MEASURE_PEN)
    else:  # polygon
        roi = pg.PolyLineROI(
            [[cx - 0.2 * wx, cy - 0.15 * wy], [cx + 0.2 * wx, cy - 0.15 * wy], [cx, cy + 0.2 * wy]],
            closed=True,
            pen=_MEASURE_PEN,
        )
    roi.setZValue(20)
    return roi


def _make_roi_from_geometry(kind: str, geometry: Mapping[str, Any]) -> Any:
    """Build an overlay at a stored nm geometry (the inverse of :func:`_geometry_of`)."""
    if kind == "line":
        p0, p1 = geometry["points"]
        roi = pg.LineSegmentROI([list(p0), list(p1)], pen=_MEASURE_PEN)
    elif kind == "rectangle":
        roi = pg.RectROI(list(geometry["pos"]), list(geometry["size"]), pen=_MEASURE_PEN)
    else:  # polygon
        roi = pg.PolyLineROI(
            [list(p) for p in geometry["points"]], closed=True, pen=_MEASURE_PEN
        )
    roi.setZValue(20)
    return roi


def _geometry_of(item: _Measurement, view_box: Any) -> dict[str, Any]:
    """Read one measurement's geometry back as plain nm coordinates (for the session)."""
    if item.kind == "line":
        p0, p1 = _line_points(item.roi, view_box)
        return {"points": [list(p0), list(p1)]}
    if item.kind == "rectangle":
        x0, y0, x1, y1 = _rect_bounds(item.roi)
        return {"pos": [x0, y0], "size": [x1 - x0, y1 - y0]}
    return {"points": [list(p) for p in _poly_vertices(item.roi, view_box)]}


def _line_points(roi: Any, view_box: Any) -> tuple[tuple[float, float], tuple[float, float]]:
    points = [view_box.mapSceneToView(p) for _, p in roi.getSceneHandlePositions()]
    p0 = (float(points[0].x()), float(points[0].y()))
    p1 = (float(points[1].x()), float(points[1].y()))
    return p0, p1


def _rect_bounds(roi: Any) -> tuple[float, float, float, float]:
    pos, size = roi.pos(), roi.size()
    return float(pos.x()), float(pos.y()), float(pos.x() + size.x()), float(pos.y() + size.y())


def _poly_vertices(roi: Any, view_box: Any) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for _, scene_point in roi.getSceneHandlePositions():
        view_point = view_box.mapSceneToView(scene_point)
        out.append((float(view_point.x()), float(view_point.y())))
    return out


# --------------------------------------------------------------------------- #
# Panel
# --------------------------------------------------------------------------- #

_STAT_COLUMNS = ("Channel", "Mean", "Median", "Min", "Max", "Std", "RMS", "P25", "P75", "Unit")

#: Peak markers use a distinct dashed pen so they never read as data.
_PEAK_PEN = pg.mkPen("#ff7b72", width=1, style=QtCore.Qt.PenStyle.DashLine)


class MeasurementPanel(QtWidgets.QWidget):
    """Tools, the active measurement's profile/statistics, and the history list."""

    def __init__(self, controller: MeasurementController) -> None:
        super().__init__()
        self._c = controller
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        tools = QtWidgets.QHBoxLayout()
        for label, slot in (
            ("+ Line", controller.add_line),
            ("+ Rectangle", controller.add_rectangle),
            ("+ Polygon", controller.add_polygon),
            ("Clear all", controller.clear),
        ):
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(slot)
            tools.addWidget(button)
        tools.addStretch(1)
        layout.addLayout(tools)

        self._readout = QtWidgets.QLabel("Add a measurement to ask a question about the data.")
        self._readout.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self._readout.setWordWrap(True)
        layout.addWidget(self._readout)

        self._profile = pg.PlotWidget()
        self._profile.setLabel("bottom", "distance", units="nm")
        self._profile.setLabel("left", "normalized value")
        self._curves: list[Any] = []
        self._peak_markers: list[Any] = []
        self._comparison: RegionComparison | None = None
        self._table = QtWidgets.QTableWidget(0, len(_STAT_COLUMNS))
        self._table.setHorizontalHeaderLabels(list(_STAT_COLUMNS))
        self._table.verticalHeader().setVisible(False)
        self._result_stack = QtWidgets.QStackedWidget()
        self._result_stack.addWidget(self._profile)
        self._result_stack.addWidget(self._table)
        layout.addWidget(self._result_stack, 1)

        # Quantitative analysis output: profile features (peaks/width/spacing) for a
        # line, or a region-vs-region comparison. Read-only; reuses the viz backend.
        self._analysis = QtWidgets.QLabel("")
        self._analysis.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self._analysis.setWordWrap(True)
        self._analysis.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self._analysis)

        analysis_row = QtWidgets.QHBoxLayout()
        compare_btn = QtWidgets.QPushButton("Compare regions")
        compare_btn.setToolTip("Compare the two most recently placed regions (A = most recent)")
        compare_btn.clicked.connect(self._compare_regions)
        copy_cmp_btn = QtWidgets.QPushButton("Copy comparison")
        copy_cmp_btn.setToolTip("Copy the region comparison (tab-separated) for paste")
        copy_cmp_btn.clicked.connect(self._copy_comparison)
        analysis_row.addWidget(compare_btn)
        analysis_row.addWidget(copy_cmp_btn)
        analysis_row.addStretch(1)
        layout.addLayout(analysis_row)

        export_row = QtWidgets.QHBoxLayout()
        copy_btn = QtWidgets.QPushButton("Copy")
        copy_btn.setToolTip("Copy the active measurement's numbers (tab-separated) for paste")
        copy_btn.clicked.connect(self.copy_active_csv)
        csv_btn = QtWidgets.QPushButton("Export CSV...")
        csv_btn.setToolTip("Save the active measurement's numbers as CSV (Excel / Origin / Python)")
        csv_btn.clicked.connect(self.export_active_csv)
        export_row.addWidget(copy_btn)
        export_row.addWidget(csv_btn)
        export_row.addStretch(1)
        layout.addLayout(export_row)

        layout.addWidget(QtWidgets.QLabel("Measurements (this session)"))
        self._list = QtWidgets.QListWidget()
        self._list.itemSelectionChanged.connect(self._on_select)
        layout.addWidget(self._list)
        history_tools = QtWidgets.QHBoxLayout()
        for label, slot in (
            ("Rename", self._rename),
            ("Hide / show", self._toggle),
            ("Delete", self._delete),
        ):
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(slot)
            history_tools.addWidget(button)
        history_tools.addStretch(1)
        layout.addLayout(history_tools)

        controller.resultChanged.connect(self._refresh_result)
        controller.historyChanged.connect(self._refresh_history)

    # -- history list ---------------------------------------------------------

    def _refresh_history(self) -> None:
        self._list.blockSignals(True)
        self._list.clear()
        for item in self._c.items:
            suffix = "" if item.visible else "   (hidden)"
            self._list.addItem(f"{item.name}  [{item.kind}]{suffix}")
        active = self._c.active
        if active is not None:
            self._list.setCurrentRow(self._c.items.index(active))
        self._list.blockSignals(False)

    def _on_select(self) -> None:
        row = self._list.currentRow()
        items = self._c.items
        if 0 <= row < len(items):
            self._c.set_active(items[row])

    def _selected(self) -> _Measurement | None:
        row = self._list.currentRow()
        items = self._c.items
        return items[row] if 0 <= row < len(items) else None

    def _rename(self) -> None:
        item = self._selected()
        if item is None:
            return
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Rename measurement", "Name:", text=item.name
        )
        if ok and name:
            self._c.rename(item, name)

    def _toggle(self) -> None:
        item = self._selected()
        if item is not None:
            self._c.set_visible(item, not item.visible)

    def _delete(self) -> None:
        item = self._selected()
        if item is not None:
            self._c.delete(item)

    # -- active result --------------------------------------------------------

    def _refresh_result(self) -> None:
        active = self._c.active
        if active is None or active.result is None:
            self._readout.setText("Add a measurement to ask a question about the data.")
            return
        if isinstance(active.result, ProfileSet):
            self._show_profile(active.result)
        else:
            self._show_statistics(active.result)

    def _show_profile(self, profile: ProfileSet) -> None:
        self._result_stack.setCurrentWidget(self._profile)
        for curve in self._curves:
            self._profile.removeItem(curve)
        self._curves = []
        self._clear_peak_markers()
        legend: list[str] = []
        for index, curve in enumerate(profile.curves):
            samples = curve.samples
            lo, hi = float(np.nanmin(samples)), float(np.nanmax(samples))
            normalized = (samples - lo) / (hi - lo) if hi > lo else np.zeros_like(samples)
            color = _CURVE_COLORS[index % len(_CURVE_COLORS)]
            pen = pg.mkPen(color, width=2)
            plotted = self._profile.plot(profile.positions_nm, normalized, pen=pen)
            self._curves.append(plotted)
            legend.append(
                f'<span style="color:{color}">&#9632; {curve.label} '
                f"[{lo:.3g}..{hi:.3g} {curve.unit}]</span>"
            )
        self._readout.setText(
            f"Length: {profile.distance_nm:.1f} nm     &Delta;x: {profile.dx_nm:.1f} nm     "
            f"&Delta;y: {profile.dy_nm:.1f} nm<br>{'   '.join(legend)}"
        )
        self._show_profile_features()

    def _show_profile_features(self) -> None:
        """Mark detected peaks on the primary curve and summarize the profile."""
        features = self._c.profile_features()
        if features is None:
            self._analysis.setText("")
            return
        for peak in features.peaks:
            marker = pg.InfiniteLine(pos=peak.position_nm, angle=90, pen=_PEAK_PEN)
            self._profile.addItem(marker)
            self._peak_markers.append(marker)
        unit = features.unit or ""
        text = (
            f"<b>Profile</b>: n = {features.count}   mean {features.mean:.4g}   "
            f"median {features.median:.4g}   std {features.std:.4g}   "
            f"RMS {features.rms:.4g} {unit}"
        )
        if features.peaks:
            widths = [p.fwhm_nm for p in features.peaks if p.fwhm_nm is not None]
            fwhm = f"; FWHM ~{np.mean(widths):.3g} nm" if widths else ""
            spacing = (
                f"; spacing {features.mean_spacing_nm:.3g} nm"
                if features.mean_spacing_nm is not None
                else ""
            )
            text += f"   |   <b>{len(features.peaks)} peak(s)</b>{spacing}{fwhm}"
        self._analysis.setText(text)

    def _show_statistics(self, report: RegionReport) -> None:
        self._result_stack.setCurrentWidget(self._table)
        self._clear_peak_markers()
        self._table.setRowCount(len(report.rows))
        for row, stat_row in enumerate(report.rows):
            stats = stat_row.stats
            cells = (
                stat_row.label,
                f"{stats.mean:.4g}",
                f"{stats.median:.4g}",
                f"{stats.minimum:.4g}",
                f"{stats.maximum:.4g}",
                f"{stats.std:.4g}",
                f"{stats.rms:.4g}",
                f"{stats.p25:.4g}",
                f"{stats.p75:.4g}",
                stat_row.unit,
            )
            for column, text in enumerate(cells):
                self._table.setItem(row, column, QtWidgets.QTableWidgetItem(text))
        self._table.resizeColumnsToContents()
        self._readout.setText(
            f"{report.kind.capitalize()} region:   {report.count} pixels   "
            f"area {report.area_nm2:.0f} nm&sup2;"
        )
        self._analysis.setText("")

    def _clear_peak_markers(self) -> None:
        for marker in self._peak_markers:
            self._profile.removeItem(marker)
        self._peak_markers = []

    # -- region comparison (read-only) ----------------------------------------

    def _compare_regions(self) -> None:
        comparison = self._c.compare_recent_regions()
        self._comparison = comparison
        if comparison is None:
            self._analysis.setText(
                "Place two regions (rectangle / polygon), then Compare regions."
            )
            return
        unit = comparison.unit or ""
        a, b = comparison.stats_a, comparison.stats_b
        ratio = "n/a" if comparison.ratio is None else f"{comparison.ratio:.4g}"
        self._analysis.setText(
            f"<b>{comparison.label_a} vs {comparison.label_b}</b> "
            f"(current channel): difference {comparison.difference:.4g} {unit}   "
            f"ratio {ratio}<br>"
            f"{comparison.label_a}: mean {a.mean:.4g} &plusmn; {a.std:.4g} (n={a.count})   "
            f"{comparison.label_b}: mean {b.mean:.4g} &plusmn; {b.std:.4g} (n={b.count}) {unit}"
        )

    def _copy_comparison(self) -> None:
        if self._comparison is None:
            return
        text = comparison_to_csv(self._comparison, self._c.export_context(), delimiter="\t")
        QtWidgets.QApplication.clipboard().setText(text)

    # -- export (CSV / clipboard) ---------------------------------------------

    def copy_active_csv(self) -> None:
        """Copy the active measurement's numbers to the clipboard (tab-separated)."""
        text = self._active_csv(delimiter="\t")
        if text is not None:
            QtWidgets.QApplication.clipboard().setText(text)

    def export_active_csv(self) -> None:
        """Save the active measurement's numbers as a CSV file (Excel / Origin / Python)."""
        text = self._active_csv(delimiter=",")
        if text is None:
            QtWidgets.QMessageBox.information(
                self,
                "Export measurement",
                "Add a measurement and select it, then export its numbers.",
            )
            return
        active = self._c.active
        default = f"{active.name}.csv" if active is not None else "measurement.csv"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export measurement", default, "CSV (*.csv)"
        )
        if not path:
            return
        Path(path).write_text(text, encoding="utf-8")

    def _active_csv(self, *, delimiter: str) -> str | None:
        """CSV text for the active measurement's result, or ``None`` if there is none."""
        active = self._c.active
        if active is None or active.result is None:
            return None
        context = self._c.export_context()
        if isinstance(active.result, ProfileSet):
            return profile_to_csv(active.result, context, delimiter=delimiter)
        return region_to_csv(active.result, context, delimiter=delimiter)


__all__ = ["MeasurementController", "MeasurementPanel"]
