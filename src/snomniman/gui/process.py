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

from collections.abc import Mapping, Sequence
from typing import Any

from PySide6 import QtCore, QtWidgets

from .model import (
    FIELD_BOOL,
    FIELD_CHANNEL,
    FIELD_ENUM,
    FIELD_FLOAT,
    FIELD_INT,
    RECIPE_STEP_PREFIX,
    InputCandidate,
    OperationField,
    OperationOption,
    OperationPreview,
    RecipeStepView,
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
    #: Emitted by "Learn more" for the shown operation. Arg: step_id.
    learnMoreRequested: QtCore.Signal = QtCore.Signal(str)
    #: Emitted by "How to use this operation" for the shown operation. Arg: step_id.
    manualRequested: QtCore.Signal = QtCore.Signal(str)
    #: Emitted by "Save current history as recipe...".
    recipeSaveRequested: QtCore.Signal = QtCore.Signal()
    #: Emitted by "Load recipe...".
    recipeLoadRequested: QtCore.Signal = QtCore.Signal()
    #: Emitted by "Delete recipe" for the shown recipe. Arg: recipe name.
    recipeDeleteRequested: QtCore.Signal = QtCore.Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._step_id: str | None = None
        self._fields: dict[str, tuple[OperationField, QtWidgets.QWidget]] = {}
        # slot name -> (combobox, candidate keys aligned with combo items)
        self._input_combos: dict[str, tuple[QtWidgets.QComboBox, list[str]]] = {}
        self._inputs_ready = True  # every declared input slot has a chosen dataset
        # The "Recipes" tree group is rebuilt independently of the operation groups
        # (set_catalog() clears the whole tree, so the window re-calls set_recipes()
        # right after); tracked here so it can be found and replaced in place.
        self._recipes_group: QtWidgets.QTreeWidgetItem | None = None

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(6)

        intro = QtWidgets.QLabel(
            "Every operation is a transparent derivation of the immutable measurement. "
            "Pick one, set its parameters, preview the exact effect, then accept. A "
            "Recipe captures a processing history once and replays it identically."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(_MUTED)
        outer.addWidget(intro)

        outer.addWidget(_section_label("Available operations and recipes"))
        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setMaximumHeight(170)
        self._tree.currentItemChanged.connect(self._on_item_changed)
        outer.addWidget(self._tree)

        recipe_row = QtWidgets.QHBoxLayout()
        self._save_recipe_btn = QtWidgets.QPushButton("Save current history as recipe...")
        self._save_recipe_btn.setToolTip(
            "Capture this measurement's processing history and save it for replay"
        )
        self._save_recipe_btn.clicked.connect(lambda: self.recipeSaveRequested.emit())
        recipe_row.addWidget(self._save_recipe_btn)
        self._load_recipe_btn = QtWidgets.QPushButton("Load recipe...")
        self._load_recipe_btn.setToolTip("Load a saved .snomrecipe file into this session")
        self._load_recipe_btn.clicked.connect(lambda: self.recipeLoadRequested.emit())
        recipe_row.addWidget(self._load_recipe_btn)
        recipe_row.addStretch(1)
        outer.addLayout(recipe_row)

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

        learn_row = QtWidgets.QHBoxLayout()
        self._learn_btn = QtWidgets.QPushButton("Learn more about this operation")
        self._learn_btn.setToolTip("Open the Knowledge Center article for this operation")
        self._learn_btn.setVisible(False)
        self._learn_btn.clicked.connect(self._on_learn_clicked)
        learn_row.addWidget(self._learn_btn)
        self._manual_btn = QtWidgets.QPushButton("How to use this operation")
        self._manual_btn.setToolTip("Open the Manual page for this operation")
        self._manual_btn.setVisible(False)
        self._manual_btn.clicked.connect(self._on_manual_clicked)
        learn_row.addWidget(self._manual_btn)
        learn_row.addStretch(1)
        self._body.addLayout(learn_row)

        self._delete_recipe_btn = QtWidgets.QPushButton("Delete this recipe")
        self._delete_recipe_btn.setToolTip("Remove this recipe from the session and its file")
        self._delete_recipe_btn.setVisible(False)
        self._delete_recipe_btn.clicked.connect(self._on_delete_recipe_clicked)
        self._body.addWidget(self._delete_recipe_btn, 0, QtCore.Qt.AlignmentFlag.AlignLeft)

        # Multi-input operations: a dataset picker per non-primary input slot. Hidden
        # for single-input operations, so their workspace looks exactly as before.
        self._inputs_box = QtWidgets.QGroupBox("Inputs")
        self._inputs_form = QtWidgets.QFormLayout(self._inputs_box)
        self._inputs_form.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        self._inputs_box.setVisible(False)
        self._body.addWidget(self._inputs_box)

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
        self._recipes_group = None  # set_catalog() clears the whole tree
        self._show_placeholder()

    def set_recipes(self, names: Sequence[str]) -> None:
        """Populate/refresh the "Recipes" group in the tree, leaving operations intact.

        Called after :meth:`set_catalog` (which clears the whole tree) and whenever
        the saved-recipe library changes (create/load/delete).
        """
        if self._recipes_group is not None:
            index = self._tree.indexOfTopLevelItem(self._recipes_group)
            if index >= 0:
                self._tree.takeTopLevelItem(index)
            self._recipes_group = None
        if not names:
            return
        self._tree.blockSignals(True)
        group = QtWidgets.QTreeWidgetItem(["Recipes"])
        group.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
        self._tree.addTopLevelItem(group)
        group.setExpanded(True)
        for name in names:
            item = QtWidgets.QTreeWidgetItem([name])
            item.setData(0, QtCore.Qt.ItemDataRole.UserRole, f"{RECIPE_STEP_PREFIX}{name}")
            group.addChild(item)
        self._tree.blockSignals(False)
        self._recipes_group = group

    def show_operation(
        self,
        option: OperationOption,
        input_candidates: Mapping[str, Sequence[InputCandidate]] | None = None,
    ) -> None:
        """Render an operation's description, availability, input pickers, and form.

        ``input_candidates`` maps each non-primary input slot to the datasets the
        user may choose (supplied by the window, which owns the project). Single-input
        operations pass nothing and render exactly as before.
        """
        self._step_id = option.step_id
        self._title.setText(option.title)
        self._detail.setText(_detail_text(option))
        self._build_inputs(option, input_candidates or {})
        self._build_form(option)
        self._learn_btn.setVisible(True)
        self._manual_btn.setVisible(True)
        self._delete_recipe_btn.setVisible(False)
        self._preview_box.setVisible(False)
        self._preview_info.clear()
        self._set_buttons_preview(active=False)
        self._preview_btn.setEnabled(option.available and self._inputs_ready)

    def show_recipe(self, name: str, steps: Sequence[RecipeStepView], created_at: str) -> None:
        """Render a saved recipe: its ordered steps, ready to Preview or Delete.

        A recipe has no parameter form of its own (each step's parameters are
        already bound) and no extra dataset inputs (recipes are single-``primary``
        chains) - so this reuses the title/detail/preview machinery every operation
        already uses, with the form and input pickers simply hidden.
        """
        self._step_id = f"{RECIPE_STEP_PREFIX}{name}"
        self._title.setText(f"Recipe: {name}")
        self._detail.setText(_recipe_detail_text(steps, created_at))
        self._clear_inputs()
        self._inputs_box.setVisible(False)
        self._clear_form()
        self._form_box.setVisible(False)
        self._learn_btn.setVisible(False)
        self._manual_btn.setVisible(False)
        self._delete_recipe_btn.setVisible(True)
        self._preview_box.setVisible(False)
        self._preview_info.clear()
        self._inputs_ready = True
        self._set_buttons_preview(active=False)
        self._preview_btn.setEnabled(True)

    def current_params(self) -> dict[str, Any]:
        """Read the parameter form back into a JSON-scalar dict for the engine."""
        params: dict[str, Any] = {}
        for name, (field, widget) in self._fields.items():
            params[name] = _read_widget(field, widget)
        return params

    def current_input_keys(self) -> dict[str, str]:
        """The chosen candidate key for each non-primary input slot (window resolves them)."""
        keys: dict[str, str] = {}
        for name, (combo, candidate_keys) in self._input_combos.items():
            idx = combo.currentIndex()
            if 0 <= idx < len(candidate_keys):
                keys[name] = candidate_keys[idx]
        return keys

    def apply_params(self, params: Mapping[str, Any]) -> None:
        """Set the parameter form from *params* (used by a pre-configured preview)."""
        for name, value in params.items():
            entry = self._fields.get(name)
            if entry is not None:
                _write_widget(entry[0], entry[1], value)

    def highlight_operation(self, step_id: str) -> None:
        """Select an operation in the list without emitting (the window drives the rest)."""
        item = self._find_item(step_id)
        if item is None:
            return
        self._tree.blockSignals(True)
        self._tree.setCurrentItem(item)
        self._tree.blockSignals(False)

    def _find_item(self, step_id: str) -> QtWidgets.QTreeWidgetItem | None:
        for i in range(self._tree.topLevelItemCount()):
            group = self._tree.topLevelItem(i)
            if group is None:
                continue
            for j in range(group.childCount()):
                child = group.child(j)
                if child is not None and child.data(0, QtCore.Qt.ItemDataRole.UserRole) == step_id:
                    return child
        return None

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
        self._inputs_box.setEnabled(not active)
        if not active:
            self._preview_box.setVisible(False)
            self._preview_info.clear()
            self._preview_btn.setEnabled(self._step_id is not None and self._inputs_ready)

    # -- internals ------------------------------------------------------------

    def _set_buttons_preview(self, active: bool) -> None:
        can_preview = not active and self._step_id is not None and self._inputs_ready
        self._preview_btn.setEnabled(can_preview)
        self._apply_btn.setVisible(active)
        self._cancel_btn.setVisible(active)

    def _show_placeholder(self) -> None:
        self._step_id = None
        self._inputs_ready = True
        self._clear_form()
        self._clear_inputs()
        self._title.setText("No operation selected")
        self._detail.setText("Select an operation or recipe above to see what it does.")
        self._learn_btn.setVisible(False)
        self._manual_btn.setVisible(False)
        self._delete_recipe_btn.setVisible(False)
        self._inputs_box.setVisible(False)
        self._form_box.setVisible(False)
        self._preview_box.setVisible(False)
        self._set_buttons_preview(active=False)
        self._preview_btn.setEnabled(False)

    def _build_inputs(
        self, option: OperationOption, candidates: Mapping[str, Sequence[InputCandidate]]
    ) -> None:
        """Build a dataset picker per non-primary input slot; track readiness."""
        self._clear_inputs()
        self._inputs_ready = True
        if not option.inputs:
            self._inputs_box.setVisible(False)
            return
        for slot in option.inputs:
            options = list(candidates.get(slot.name, ()))
            if options:
                combo = QtWidgets.QComboBox()
                for cand in options:
                    combo.addItem(cand.label)
                combo.setToolTip(slot.description)
                self._input_combos[slot.name] = (combo, [c.key for c in options])
                row = QtWidgets.QLabel(f"{slot.name} *")
                row.setToolTip(slot.description)
                self._inputs_form.addRow(row, combo)
            else:
                # No dataset to fill this slot - explain and block Preview.
                self._inputs_ready = False
                hint = QtWidgets.QLabel(
                    "no other dataset available - open or add another measurement"
                )
                hint.setStyleSheet(_MUTED)
                hint.setWordWrap(True)
                self._inputs_form.addRow(QtWidgets.QLabel(f"{slot.name} *"), hint)
        self._inputs_box.setVisible(True)

    def _clear_inputs(self) -> None:
        self._input_combos.clear()
        while self._inputs_form.count():
            item = self._inputs_form.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

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

    def _on_learn_clicked(self) -> None:
        if self._step_id is not None:
            self.learnMoreRequested.emit(self._step_id)

    def _on_manual_clicked(self) -> None:
        if self._step_id is not None:
            self.manualRequested.emit(self._step_id)

    def _on_delete_recipe_clicked(self) -> None:
        if self._step_id is not None and self._step_id.startswith(RECIPE_STEP_PREFIX):
            self.recipeDeleteRequested.emit(self._step_id[len(RECIPE_STEP_PREFIX) :])


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


def _write_widget(field: OperationField, widget: QtWidgets.QWidget, value: Any) -> None:
    """Set a control's value (the inverse of :func:`_read_widget`)."""
    if field.kind == FIELD_BOOL and isinstance(widget, QtWidgets.QCheckBox):
        widget.setChecked(bool(value))
    elif field.kind == FIELD_INT and isinstance(widget, QtWidgets.QSpinBox):
        widget.setValue(int(value))
    elif field.kind == FIELD_FLOAT and isinstance(widget, QtWidgets.QDoubleSpinBox):
        widget.setValue(float(value))
    elif field.kind == FIELD_ENUM and isinstance(widget, QtWidgets.QComboBox):
        if value in field.choices:
            widget.setCurrentIndex(field.choices.index(value))
    elif field.kind == FIELD_CHANNEL and isinstance(widget, QtWidgets.QComboBox):
        idx = widget.findText(str(value))
        if idx >= 0:
            widget.setCurrentIndex(idx)
    elif isinstance(widget, QtWidgets.QLineEdit):
        widget.setText(str(value))


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


def _recipe_detail_text(steps: Sequence[RecipeStepView], created_at: str) -> str:
    lines = [f"Captured {created_at}", f"{len(steps)} step(s), replayed in order:", ""]
    for i, step in enumerate(steps, start=1):
        params = ", ".join(f"{k}={v!r}" for k, v in step.params.items()) or "(no parameters)"
        lines.append(f"{i}. {step.title} - {step.description}")
        lines.append(f"     {params}")
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
