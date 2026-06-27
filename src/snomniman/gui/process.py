"""The Processing Workspace: one generic, registry-driven interface to every operation.

This panel exposes *every* registered :class:`~snomniman.processing.ProcessingStep`
through a single interface - an operation list, an auto-generated parameter form, a
preview, and a provenance preview - with **no operation-specific UI code**. A newly
registered operation appears here automatically: its availability, parameter editor,
preview, and provenance preview are all derived from the processing registry,
``ParameterSpec``, and the dataset's capabilities (projected by the Qt-free
:class:`~snomniman.gui.model.ExplorerModel`).

The widget is deliberately thin (Rule 4): it renders the model's view-objects and
emits signals describing user intent. It holds no scientific logic - it does not know
what any operation does, only how to turn a field descriptor into a control and a
control back into a value. The window runs the computation and owns dataset/history.
"""

from __future__ import annotations

from typing import Any

from PySide6 import QtCore, QtWidgets

from .model import (
    FIELD_BOOL,
    FIELD_CHANNEL,
    FIELD_ENUM,
    FIELD_FLOAT,
    FIELD_INT,
    OperationField,
    OperationOption,
    OperationPreview,
)

_MUTED = "color: #9aa0a6;"
_INT_MAX = 2_147_483_647


class ProcessingWorkspace(QtWidgets.QWidget):
    """A universal, registry-driven interface to the deterministic processing engine.

    Workflow (identical for every operation)::

        1. Select an operation       -> operationSelected(step_id)
        2. The window shows it        -> show_operation(option) builds the form
        3. Configure parameters + Preview -> previewRequested(step_id, params)
        4. The window runs the step, shows before/after + the change/provenance
           summary -> show_preview(preview); the Apply/Cancel buttons appear.
        5. Apply   -> previewAccepted   (the window commits the derivation)
           Cancel  -> previewCancelled  (the window discards it)
    """

    #: Emitted when an operation is selected in the list. Arg: step_id.
    operationSelected: QtCore.Signal = QtCore.Signal(str)
    #: Emitted on Preview. Args: step_id, params (a JSON-scalar dict).
    previewRequested: QtCore.Signal = QtCore.Signal(str, object)
    #: Emitted when the user accepts the current preview (commits the derivation).
    previewAccepted: QtCore.Signal = QtCore.Signal()
    #: Emitted when the user cancels the current preview.
    previewCancelled: QtCore.Signal = QtCore.Signal()

    def __init__(self) -> None:
        super().__init__()
        self._step_id: str | None = None
        self._fields: dict[str, tuple[OperationField, QtWidgets.QWidget]] = {}

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(6)

        intro = QtWidgets.QLabel(
            "Every operation is a transparent derivation of the immutable measurement. "
            "Pick one, set its parameters, preview the exact effect, then accept."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(_MUTED)
        outer.addWidget(intro)

        outer.addWidget(_section_label("Available operations"))
        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setMaximumHeight(170)
        self._tree.currentItemChanged.connect(self._on_item_changed)
        outer.addWidget(self._tree)

        # Everything below scrolls so a long parameter form / summary never overflows.
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        body = QtWidgets.QWidget()
        self._body = QtWidgets.QVBoxLayout(body)
        self._body.setContentsMargins(0, 0, 0, 0)
        self._body.setSpacing(6)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        self._title = QtWidgets.QLabel()
        title_font = self._title.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 1)
        self._title.setFont(title_font)
        self._title.setWordWrap(True)
        self._body.addWidget(self._title)

        self._detail = QtWidgets.QLabel()
        self._detail.setWordWrap(True)
        self._detail.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self._body.addWidget(self._detail)

        self._form_box = QtWidgets.QGroupBox("Parameters")
        self._form = QtWidgets.QFormLayout(self._form_box)
        self._form.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self._body.addWidget(self._form_box)

        self._buttons = self._build_buttons()
        self._body.addLayout(self._buttons)

        self._preview_box = QtWidgets.QGroupBox("Preview")
        pv = QtWidgets.QVBoxLayout(self._preview_box)
        self._preview_info = QtWidgets.QLabel()
        self._preview_info.setWordWrap(True)
        self._preview_info.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self._preview_info.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        pv.addWidget(self._preview_info)
        self._preview_box.setVisible(False)
        self._body.addWidget(self._preview_box)

        self._body.addStretch(1)
        self._show_placeholder()

    # -- construction ---------------------------------------------------------

    def _build_buttons(self) -> QtWidgets.QHBoxLayout:
        row = QtWidgets.QHBoxLayout()
        self._preview_btn = QtWidgets.QPushButton("Preview")
        self._preview_btn.setToolTip("Compute a before/after comparison without committing")
        self._preview_btn.clicked.connect(self._on_preview_clicked)
        self._preview_btn.setEnabled(False)
        row.addWidget(self._preview_btn)

        self._apply_btn = QtWidgets.QPushButton("Accept")
        self._apply_btn.setToolTip("Commit this derivation as a new dataset (the original is kept)")
        self._apply_btn.setVisible(False)
        self._apply_btn.clicked.connect(lambda: self.previewAccepted.emit())
        row.addWidget(self._apply_btn)

        self._cancel_btn = QtWidgets.QPushButton("Cancel")
        self._cancel_btn.setToolTip("Discard the preview and return to the measurement")
        self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(lambda: self.previewCancelled.emit())
        row.addWidget(self._cancel_btn)
        row.addStretch(1)
        return row

    # -- public interface (called by the window) ------------------------------

    def set_catalog(self, options: list[OperationOption]) -> None:
        """Populate the operation list from the registry-driven catalogue.

        Operations are grouped by their logical namespace; unavailable ones stay
        visible but disabled (the detail panel explains why when selected).
        """
        self._tree.blockSignals(True)
        self._tree.clear()
        groups: dict[str, QtWidgets.QTreeWidgetItem] = {}
        for opt in options:
            parent = groups.get(opt.group)
            if parent is None:
                parent = QtWidgets.QTreeWidgetItem([opt.group])
                parent.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
                self._tree.addTopLevelItem(parent)
                parent.setExpanded(True)
                groups[opt.group] = parent
            label = opt.title if opt.available else f"{opt.title}  (unavailable)"
            item = QtWidgets.QTreeWidgetItem([label])
            item.setData(0, QtCore.Qt.ItemDataRole.UserRole, opt.step_id)
            if not opt.available:
                item.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.NoItemFlags)
                item.setForeground(0, QtCore.Qt.GlobalColor.gray)
            parent.addChild(item)
        self._tree.blockSignals(False)
        self._show_placeholder()

    def show_operation(self, option: OperationOption) -> None:
        """Render an operation's description, availability, and parameter form."""
        self._step_id = option.step_id
        self._title.setText(option.title)
        self._detail.setText(_detail_text(option))
        self._build_form(option)
        self._preview_box.setVisible(False)
        self._preview_info.clear()
        self._set_buttons_preview(active=False)
        self._preview_btn.setEnabled(option.available)

    def current_params(self) -> dict[str, Any]:
        """Read the parameter form back into a JSON-scalar dict for the engine."""
        params: dict[str, Any] = {}
        for name, (field, widget) in self._fields.items():
            params[name] = _read_widget(field, widget)
        return params

    def show_preview(self, preview: OperationPreview) -> None:
        """Show the change/provenance summary and switch to Accept/Cancel."""
        self._preview_info.setText(_preview_html(preview))
        self._preview_box.setVisible(True)
        self._set_buttons_preview(active=True)

    def set_preview_mode(self, active: bool) -> None:
        """Lock the catalogue + form during a preview; restore them afterwards."""
        self._set_buttons_preview(active)
        self._tree.setEnabled(not active)
        self._form_box.setEnabled(not active)
        if not active:
            self._preview_box.setVisible(False)
            self._preview_info.clear()
            self._preview_btn.setEnabled(self._step_id is not None)

    # -- internals ------------------------------------------------------------

    def _set_buttons_preview(self, active: bool) -> None:
        self._preview_btn.setEnabled(not active and self._step_id is not None)
        self._apply_btn.setVisible(active)
        self._cancel_btn.setVisible(active)

    def _show_placeholder(self) -> None:
        self._step_id = None
        self._clear_form()
        self._title.setText("No operation selected")
        self._detail.setText("Select an operation above to see what it does and configure it.")
        self._form_box.setVisible(False)
        self._preview_box.setVisible(False)
        self._set_buttons_preview(active=False)
        self._preview_btn.setEnabled(False)

    def _build_form(self, option: OperationOption) -> None:
        self._clear_form()
        if not option.fields:
            self._form_box.setVisible(True)
            self._form.addRow(QtWidgets.QLabel("This operation takes no parameters."))
            return
        for field in option.fields:
            widget = _make_widget(field)
            self._fields[field.name] = (field, widget)
            label = field.name + (" *" if field.required else "")
            row = QtWidgets.QLabel(label)
            row.setToolTip(field.description)
            widget.setToolTip(field.description)
            self._form.addRow(row, widget)
        self._form_box.setVisible(True)

    def _clear_form(self) -> None:
        self._fields.clear()
        while self._form.count():
            item = self._form.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def _on_item_changed(
        self, current: QtWidgets.QTreeWidgetItem | None, _previous: QtWidgets.QTreeWidgetItem | None
    ) -> None:
        if current is None:
            return
        step_id = current.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(step_id, str):
            self.operationSelected.emit(step_id)

    def _on_preview_clicked(self) -> None:
        if self._step_id is None:
            return
        self.previewRequested.emit(self._step_id, self.current_params())


# --------------------------------------------------------------------------- #
# Field <-> widget mapping (pure presentation: no operation knowledge here)
# --------------------------------------------------------------------------- #


def _make_widget(field: OperationField) -> QtWidgets.QWidget:
    if field.kind == FIELD_BOOL:
        box = QtWidgets.QCheckBox()
        box.setChecked(bool(field.default))
        return box
    if field.kind == FIELD_INT:
        spin = QtWidgets.QSpinBox()
        spin.setRange(-_INT_MAX, _INT_MAX)
        spin.setValue(int(field.default) if isinstance(field.default, int) else 0)
        return spin
    if field.kind == FIELD_FLOAT:
        dspin = QtWidgets.QDoubleSpinBox()
        dspin.setRange(-1e12, 1e12)
        dspin.setDecimals(3)
        dspin.setValue(float(field.default) if isinstance(field.default, (int, float)) else 0.0)
        return dspin
    if field.kind in (FIELD_CHANNEL, FIELD_ENUM):
        combo = QtWidgets.QComboBox()
        for choice in field.choices:
            combo.addItem(str(choice))
        if field.default is not None:
            idx = combo.findText(str(field.default))
            if idx >= 0:
                combo.setCurrentIndex(idx)
        return combo
    line = QtWidgets.QLineEdit()
    if field.default is not None:
        line.setText(str(field.default))
    return line


def _read_widget(field: OperationField, widget: QtWidgets.QWidget) -> Any:
    if field.kind == FIELD_BOOL and isinstance(widget, QtWidgets.QCheckBox):
        return widget.isChecked()
    if field.kind == FIELD_INT and isinstance(widget, QtWidgets.QSpinBox):
        return widget.value()
    if field.kind == FIELD_FLOAT and isinstance(widget, QtWidgets.QDoubleSpinBox):
        return float(widget.value())
    if field.kind == FIELD_ENUM and isinstance(widget, QtWidgets.QComboBox):
        # Preserve the original value type (e.g. int order), not the display string.
        idx = widget.currentIndex()
        return field.choices[idx] if 0 <= idx < len(field.choices) else None
    if field.kind == FIELD_CHANNEL and isinstance(widget, QtWidgets.QComboBox):
        return widget.currentText()
    if isinstance(widget, QtWidgets.QLineEdit):
        return widget.text()
    return None


# --------------------------------------------------------------------------- #
# Text rendering (the model owns the facts; here we only format)
# --------------------------------------------------------------------------- #


def _detail_text(option: OperationOption) -> str:
    lines = [option.description, ""]
    if option.requirements:
        lines.append("Requires: " + "; ".join(option.requirements))
    determinism = "deterministic" if option.deterministic else "non-deterministic"
    lines.append(f"Version {option.version} - {determinism}")
    if option.already_applied:
        lines.append("Note: this operation already appears in the derivation history.")
    if not option.applicable:
        lines.append("")
        lines.append("Unavailable - this measurement is missing:")
        lines.extend(f"  - {m}" for m in option.missing)
    elif option.blocked_reason is not None:
        lines.append("")
        lines.append(f"Unavailable - {option.blocked_reason}.")
    return "\n".join(lines)


def _preview_html(preview: OperationPreview) -> str:
    parts = ["<b>What will change</b>"]
    parts.append("<ul>" + "".join(f"<li>{_esc(c)}</li>" for c in preview.changes) + "</ul>")
    parts.append("<b>What stays the same</b>")
    parts.append("<ul>" + "".join(f"<li>{_esc(u)}</li>" for u in preview.unchanged) + "</ul>")
    prov = preview.provenance
    params = ", ".join(f"{k}={v!r}" for k, v in prov.params.items()) or "(none)"
    parts.append("<b>Provenance to be recorded</b>")
    parts.append(
        "<div style='font-family: monospace;'>"
        f"new dataset &larr; <b>{_esc(prov.step_id)}</b>"
        f"<br>&nbsp;&nbsp;parameters: {_esc(params)}"
        f"<br>&nbsp;&nbsp;from: {_esc(preview.title)}"
        "</div>"
    )
    return "".join(parts)


def _esc(text: object) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _section_label(text: str) -> QtWidgets.QLabel:
    label = QtWidgets.QLabel(text)
    font = label.font()
    font.setBold(True)
    label.setFont(font)
    return label


__all__ = ["ProcessingWorkspace"]
