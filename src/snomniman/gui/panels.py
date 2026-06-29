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
    """The project's measurements: a list with the active one selected, plus actions.

    Pure presentation - it lists the measurement labels the window builds, marks the
    active one, and emits intent signals (activate / add / remove / rename). It holds
    no session state and never touches a Dataset (Rule 4). Scales from one
    measurement (a single quiet row, so the app feels unchanged) to many.
    """

    measurementActivated = QtCore.Signal(int)  # the user picked a measurement to work on
    addRequested = QtCore.Signal()  # "Add Measurement..."
    removeRequested = QtCore.Signal(int)  # close the measurement at this row
    renameRequested = QtCore.Signal(int)  # rename the measurement at this row

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self._list = QtWidgets.QListWidget()
        self._list.itemSelectionChanged.connect(self._on_selection)
        layout.addWidget(self._list, 1)

        tools = QtWidgets.QHBoxLayout()
        for label, slot in (
            ("Add...", lambda: self.addRequested.emit()),
            ("Rename", self._emit_rename),
            ("Close", self._emit_remove),
        ):
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(slot)
            tools.addWidget(button)
        tools.addStretch(1)
        layout.addLayout(tools)

    def set_measurements(self, labels: Sequence[str], active: int) -> None:
        """Replace the list; select ``active`` (signals are suppressed during refresh)."""
        self._list.blockSignals(True)
        self._list.clear()
        for label in labels:
            self._list.addItem(label)
        if 0 <= active < len(labels):
            self._list.setCurrentRow(active)
        self._list.blockSignals(False)

    def _on_selection(self) -> None:
        row = self._list.currentRow()
        if row >= 0:
            self.measurementActivated.emit(row)

    def _emit_rename(self) -> None:
        row = self._list.currentRow()
        if row >= 0:
            self.renameRequested.emit(row)

    def _emit_remove(self) -> None:
        row = self._list.currentRow()
        if row >= 0:
            self.removeRequested.emit(row)


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
