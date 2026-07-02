"""Side panels for the Explorer: channel browser, metadata and provenance views.

All three are pure presentation: they render the view objects produced by
:class:`~snomniman.gui.model.ExplorerModel` and emit selection signals. They hold
no scientific logic and never touch the Dataset (Rule 4). Progressive disclosure
is honored - the amplitude/phase toggle appears only when a channel actually has
the choice; deeper detail (params, software, sources) nests under its node.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6 import QtCore, QtWidgets

from snomniman.viz import AMPLITUDE, PHASE

from .experiment import ExperimentRow
from .model import ChannelGroup, MetadataSection, ProvenanceStep

_CHANNEL_ROLE = QtCore.Qt.ItemDataRole.UserRole


class ChannelBrowser(QtWidgets.QWidget):
    """A tree of channels grouped by physical meaning, plus an amp/phase toggle."""

    channelSelected = QtCore.Signal(str)
    representationSelected = QtCore.Signal(str)

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.itemSelectionChanged.connect(self._on_selection)
        layout.addWidget(self._tree, 1)
        self._item_by_channel: dict[str, QtWidgets.QTreeWidgetItem] = {}

        self._rep_box = QtWidgets.QGroupBox("Representation")
        rep_layout = QtWidgets.QHBoxLayout(self._rep_box)
        self._rep_buttons: dict[str, QtWidgets.QRadioButton] = {}
        for rep in (AMPLITUDE, PHASE):
            button = QtWidgets.QRadioButton(rep.capitalize())
            button.toggled.connect(self._make_rep_handler(rep))
            self._rep_buttons[rep] = button
            rep_layout.addWidget(button)
        rep_layout.addStretch(1)
        layout.addWidget(self._rep_box)

    def set_groups(self, groups: Sequence[ChannelGroup]) -> None:
        self._tree.blockSignals(True)
        self._tree.clear()
        self._item_by_channel.clear()
        for group in groups:
            header = QtWidgets.QTreeWidgetItem([group.title])
            header.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)  # a label, not selectable
            font = header.font(0)
            font.setBold(True)
            header.setFont(0, font)
            self._tree.addTopLevelItem(header)
            for entry in group.entries:
                child = QtWidgets.QTreeWidgetItem([f"{entry.canonical}    {entry.descriptor}"])
                child.setData(0, _CHANNEL_ROLE, entry.canonical)
                header.addChild(child)
                self._item_by_channel[entry.canonical] = child
            header.setExpanded(True)
        self._tree.blockSignals(False)

    def select(self, canonical: str) -> None:
        item = self._item_by_channel.get(canonical)
        if item is not None:
            self._tree.blockSignals(True)
            self._tree.setCurrentItem(item)
            self._tree.blockSignals(False)

    def set_representations(self, representations: Sequence[str], current: str) -> None:
        """Show the amp/phase toggle only when the channel offers a choice."""
        has_choice = len(representations) > 1
        self._rep_box.setVisible(has_choice)
        for rep, button in self._rep_buttons.items():
            button.setVisible(rep in representations)
            button.blockSignals(True)
            button.setChecked(rep == current)
            button.blockSignals(False)

    def _make_rep_handler(self, representation: str) -> object:
        def handler(checked: bool) -> None:
            if checked:
                self.representationSelected.emit(representation)

        return handler

    def _on_selection(self) -> None:
        items = self._tree.selectedItems()
        if not items:
            return
        canonical = items[0].data(0, _CHANNEL_ROLE)
        if canonical:
            self.channelSelected.emit(str(canonical))


class MeasurementManager(QtWidgets.QWidget):
    """The project's measurements as an experiment overview: a summary table + actions.

    Pure presentation - it renders the per-measurement summary rows the window builds
    (title, time, processing, harmonics, reference), marks the active one, and emits
    intent signals (activate / add / remove / rename / compare). It holds no session
    state and never touches a Dataset (Rule 4). A **single** row is selected to work
    on one measurement (activate); selecting **several** enables a cross-measurement
    Compare without switching the active one. Scales from one quiet row (so the app
    feels unchanged) to a 100-row experiment.
    """

    measurementActivated = QtCore.Signal(int)  # exactly one row selected -> work on it
    compareRequested = QtCore.Signal(list)  # >= 2 rows selected -> compare these indices
    addRequested = QtCore.Signal()  # "Add Measurement..."
    removeRequested = QtCore.Signal(int)  # close the measurement at this row
    renameRequested = QtCore.Signal(int)  # rename the measurement at this row
    batchRequested = QtCore.Signal()  # "Batch..." - the window reads selected_rows() itself

    _COLUMNS = ("Measurement", "Time", "Processing", "Harmonics", "Ref")

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self._table = QtWidgets.QTableWidget(0, len(self._COLUMNS))
        self._table.setHorizontalHeaderLabels(list(self._COLUMNS))
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self._table.itemSelectionChanged.connect(self._on_selection)
        layout.addWidget(self._table, 1)

        tools = QtWidgets.QHBoxLayout()
        self._compare_btn = QtWidgets.QPushButton("Compare")
        self._compare_btn.setToolTip("Select two or more measurements to compare them side by side")
        self._compare_btn.setEnabled(False)
        self._compare_btn.clicked.connect(self._emit_compare)
        for label, slot in (
            ("Add...", lambda: self.addRequested.emit()),
            ("Rename", self._emit_rename),
            ("Close", self._emit_remove),
        ):
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(slot)
            tools.addWidget(button)
        tools.addWidget(self._compare_btn)
        self._batch_btn = QtWidgets.QPushButton("Batch...")
        self._batch_btn.setToolTip(
            "Replay a saved recipe across all measurements, or just the selected ones"
        )
        self._batch_btn.clicked.connect(lambda: self.batchRequested.emit())
        tools.addWidget(self._batch_btn)
        tools.addStretch(1)
        layout.addLayout(tools)

    def set_rows(self, rows: Sequence[ExperimentRow], active: int) -> None:
        """Replace the table; select ``active`` (signals suppressed during refresh)."""
        self._table.blockSignals(True)
        self._table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            cells = (
                row.title,
                row.datetime or "-",
                row.processing,
                row.harmonics,
                "yes" if row.has_reference else "no",
            )
            for c, text in enumerate(cells):
                self._table.setItem(r, c, QtWidgets.QTableWidgetItem(text))
        self._table.resizeColumnsToContents()
        if 0 <= active < len(rows):
            self._table.selectRow(active)
        self._table.blockSignals(False)
        self._update_compare_enabled()

    def selected_rows(self) -> list[int]:
        """The currently selected measurement indices (ascending)."""
        return sorted({index.row() for index in self._table.selectedIndexes()})

    def _on_selection(self) -> None:
        rows = self.selected_rows()
        self._update_compare_enabled()
        if len(rows) == 1:  # a single selection means "work on this measurement"
            self.measurementActivated.emit(rows[0])

    def _update_compare_enabled(self) -> None:
        self._compare_btn.setEnabled(len(self.selected_rows()) >= 2)

    def _emit_compare(self) -> None:
        rows = self.selected_rows()
        if len(rows) >= 2:
            self.compareRequested.emit(rows)

    def _emit_rename(self) -> None:
        rows = self.selected_rows()
        if rows:
            self.renameRequested.emit(rows[0])

    def _emit_remove(self) -> None:
        rows = self.selected_rows()
        if rows:
            self.removeRequested.emit(rows[0])


class MetadataInspector(QtWidgets.QTreeWidget):
    """Typed metadata in readable groups; each value shows its unit and source."""

    def __init__(self) -> None:
        super().__init__()
        self.setColumnCount(4)
        self.setHeaderLabels(["Field", "Value", "Unit", "Source"])
        self.setRootIsDecorated(True)

    def set_sections(self, sections: Sequence[MetadataSection]) -> None:
        self.clear()
        for section in sections:
            header = QtWidgets.QTreeWidgetItem([section.title])
            font = header.font(0)
            font.setBold(True)
            header.setFont(0, font)
            self.addTopLevelItem(header)
            for item in section.items:
                QtWidgets.QTreeWidgetItem(
                    header, [item.label, item.value, item.unit or "", item.source]
                )
            header.setExpanded(True)
        for column in range(self.columnCount()):
            self.resizeColumnToContents(column)


class ProvenanceInspector(QtWidgets.QWidget):
    """The lineage: a plain-language summary plus the derivation graph nodes."""

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        self._summary = QtWidgets.QLabel()
        self._summary.setWordWrap(True)
        self._summary.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self._summary)
        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderLabels(["Derivation step", "Detail"])
        layout.addWidget(self._tree, 1)

    def set_provenance(self, summary: str, steps: Sequence[ProvenanceStep]) -> None:
        self._summary.setText(summary)
        self._tree.clear()
        for step in steps:
            node = QtWidgets.QTreeWidgetItem([f"{step.step_id}", step.description])
            font = node.font(0)
            font.setBold(True)
            node.setFont(0, font)
            self._tree.addTopLevelItem(node)
            QtWidgets.QTreeWidgetItem(
                node, ["deterministic", "yes" if step.deterministic else "no"]
            )
            if step.sources:
                sources = QtWidgets.QTreeWidgetItem(node, ["sources", ""])
                for line in step.sources:
                    QtWidgets.QTreeWidgetItem(sources, ["", line])
            if step.params:
                params = QtWidgets.QTreeWidgetItem(node, ["parameters", ""])
                for key, value in step.params.items():
                    QtWidgets.QTreeWidgetItem(params, [str(key), str(value)])
            software = QtWidgets.QTreeWidgetItem(node, ["software", ""])
            for key, value in step.software.items():
                QtWidgets.QTreeWidgetItem(software, [str(key), str(value)])
            node.setExpanded(True)
        for column in range(self._tree.columnCount()):
            self._tree.resizeColumnToContents(column)


__all__ = [
    "ChannelBrowser",
    "MeasurementManager",
    "MetadataInspector",
    "ProvenanceInspector",
]
