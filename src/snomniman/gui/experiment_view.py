"""The Experiment inspector panel: project-wide diagnostics and cross-measurement stats.

Two read-only, sortable tables over the whole experiment (Phase 2B):

* **Experiment diagnostics** - one row per measurement (roughness, tilt, signal
  harmonics, reference), so sorting a column ranks the scans (smoothest, flattest,
  highest-contrast) and surfaces incomplete ones.
* **Cross-measurement statistics** - the active measurement's current overlay
  (line / rectangle / polygon) evaluated on every measurement, exportable as CSV.

Pure presentation: it renders the :class:`~snomniman.gui.experiment.ExperimentTable`
value objects the experiment presenter builds and emits intent signals; it holds no
session state and never touches a Dataset (Rule 4). Numeric columns sort by value
(not by formatted text) via a small comparison item.
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from .experiment import ExperimentTable


class _SortItem(QtWidgets.QTableWidgetItem):
    """A table cell that sorts by a numeric key when present (else by its text)."""

    def __init__(self, text: str, sort_key: float | None) -> None:
        super().__init__(text)
        self._key = sort_key

    def __lt__(self, other: QtWidgets.QTableWidgetItem) -> bool:
        if isinstance(other, _SortItem) and self._key is not None and other._key is not None:
            return self._key < other._key
        return super().__lt__(other)


class ExperimentPanel(QtWidgets.QWidget):
    """Project-wide diagnostics + cross-measurement statistics for the active overlay."""

    compareOverlayRequested = QtCore.Signal()  # evaluate the active overlay across measurements
    exportStatisticsRequested = QtCore.Signal()  # save the cross-measurement stats as CSV
    copyStatisticsRequested = QtCore.Signal()  # copy the cross-measurement stats (TSV)

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        layout.addWidget(
            QtWidgets.QLabel("Experiment diagnostics  -  click a column to rank scans")
        )
        self._diagnostics = _new_table()
        layout.addWidget(self._diagnostics, 1)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        layout.addWidget(line)

        layout.addWidget(QtWidgets.QLabel("Cross-measurement statistics"))
        intro = QtWidgets.QLabel(
            "Place a line / rectangle / polygon on the active measurement (Measure tab), "
            "then evaluate it across every measurement in the experiment."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #9aa0a6;")
        layout.addWidget(intro)
        compare_btn = QtWidgets.QPushButton("Compare active overlay across measurements")
        compare_btn.clicked.connect(self.compareOverlayRequested)
        layout.addWidget(compare_btn)
        self._statistics = _new_table()
        layout.addWidget(self._statistics, 1)

        export_row = QtWidgets.QHBoxLayout()
        copy_btn = QtWidgets.QPushButton("Copy")
        copy_btn.setToolTip("Copy the comparison table (tab-separated) for paste")
        copy_btn.clicked.connect(self.copyStatisticsRequested)
        csv_btn = QtWidgets.QPushButton("Export CSV...")
        csv_btn.setToolTip("Save the cross-measurement comparison as CSV")
        csv_btn.clicked.connect(self.exportStatisticsRequested)
        export_row.addWidget(copy_btn)
        export_row.addWidget(csv_btn)
        export_row.addStretch(1)
        layout.addLayout(export_row)

    def set_diagnostics(self, table: ExperimentTable) -> None:
        _fill_table(self._diagnostics, table)

    def set_statistics(self, table: ExperimentTable) -> None:
        _fill_table(self._statistics, table)


def _new_table() -> QtWidgets.QTableWidget:
    table = QtWidgets.QTableWidget(0, 0)
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSortingEnabled(True)
    return table


def _fill_table(widget: QtWidgets.QTableWidget, table: ExperimentTable) -> None:
    """Render an :class:`ExperimentTable` into ``widget`` (numeric columns sort by value)."""
    widget.setSortingEnabled(False)  # avoid re-sorting while rows are inserted
    headers = ["Measurement"]
    headers.extend(f"{c.label} [{c.unit}]" if c.unit else c.label for c in table.columns)
    widget.setColumnCount(len(headers))
    widget.setHorizontalHeaderLabels(headers)
    widget.setRowCount(len(table.rows))
    for r, row in enumerate(table.rows):
        widget.setItem(r, 0, QtWidgets.QTableWidgetItem(row.title))
        for c, cell in enumerate(row.cells, start=1):
            widget.setItem(r, c, _SortItem(cell.text, cell.value))
    widget.resizeColumnsToContents()
    widget.setSortingEnabled(True)


__all__ = ["ExperimentPanel"]
