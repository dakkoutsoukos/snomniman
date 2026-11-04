"""The Measurement Explorer window: where files become an understood measurement.

Composes the read-only experience from the model and the panels: an always-visible
identity header (the scientific frame), the channel browser, the physical image
view, and the metadata/provenance inspectors, with the conventions and a live
cursor readout in the status bar. It is wiring only - it translates user gestures
into model queries and pushes the results into widgets; it computes nothing
scientific and never modifies the measurement (Rule 4; "explore before you
process").

Processing derivations (plane level, future operations) produce new immutable
Datasets via the processing engine.  The window keeps a linear history stack so
the researcher can navigate back to the original measurement after a derivation.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets

from snomniman import viz
from snomniman.batch import BatchOutcome, BatchResult, run_batch
from snomniman.core import Dataset, current_software
from snomniman.core.exceptions import DatasetError, ProcessingError, ReaderError
from snomniman.io import export_channel_gsf, write_zarr
from snomniman.knowledge import article_for_operation
from snomniman.manual import page_for_operation
from snomniman.pipeline import (
    RECIPE_SUFFIX,
    Measurement,
    Project,
    Recipe,
    delete_recipe,
    load_project,
    load_recipe,
    measurement_from_history,
    save_project,
    save_recipe,
)
from snomniman.viz import LineshapeFit, RenderData

from .briefing import BriefingPanel
from .comparison import ComparisonView, ContactSheet
from .diagnostics import DiagnosticsPanel
from .experiment import ExperimentModel, ExperimentTable
from .experiment_view import ExperimentPanel
from .export import ExperimentExportContext, experiment_table_to_csv
from .hyperspectral import HyperspectralView
from .imageview import ChannelImageView
from .knowledge import KnowledgePanel
from .manual import ManualPanel
from .measurement import MeasurementController, MeasurementPanel
from .model import (
    PRESET_LABELS,
    ExplorerModel,
    InputCandidate,
    MeasurementIdentity,
    MeasurementSession,
    OperationOption,
    OperationPreview,
    PaneSpec,
)
from .model import RECIPE_STEP_PREFIX as _RECIPE_STEP_PREFIX
from .panels import (
    ChannelBrowser,
    MeasurementManager,
    MetadataInspector,
    ProvenanceInspector,
)
from .process import ProcessingWorkspace
from .report import (
    REPORT_FORMAT_HTML,
    REPORT_FORMAT_MARKDOWN,
    Report,
    ReportModel,
    export_report,
)
from .spectrumview import SpectrumPlotView


class MeasurementExplorerWindow(QtWidgets.QMainWindow):
    """The central Explorer surface for one measurement and its derivations."""

    def __init__(self, model: ExplorerModel) -> None:
        super().__init__()
        # The session list is established first: the _model/_history properties read
        # the active session, so it must exist before any other state is touched.
        self._next_seq = 1
        self._sessions: list[MeasurementSession] = [
            MeasurementSession(
                model=model, measurement_id=self._new_measurement_id(), title=model.title
            )
        ]
        self._active_index = 0
        self._project_title = model.title
        self._preview: OperationPreview | None = None
        # The saved project this session is bound to (Save vs Save As), and the
        # active comparison preset (persisted with the active session's view state).
        self._project_path: Path | None = None
        self._comparison_preset: str | None = None
        # Experiment-level state (Phase 2B, read-only): a presenter over all
        # sessions, the active cross-measurement comparison (indices + shared
        # channel), and the last computed cross-measurement statistics table.
        self._experiment = ExperimentModel(self._sessions)
        self._experiment_compare: tuple[int, ...] | None = None
        self._experiment_compare_channel = ""
        self._experiment_stats: ExperimentTable | None = None
        # Candidate datasets for a multi-input operation's extra slots (key -> Dataset),
        # rebuilt whenever an operation is shown in the workspace (ADR-0030).
        self._input_candidate_map: dict[str, Dataset] = {}
        # Processing recipes known to this session (Phase 4A): name -> Recipe, and
        # the .snomrecipe file each was saved to/loaded from (if any).
        self._recipes: dict[str, Recipe] = {}
        self._recipe_paths: dict[str, Path] = {}
        # Batch runs performed this session (Phase 4B) and figures exported this
        # session (existing Export -> Figure...), both consumed only by reports
        # (Phase 4C) - the report is honest that this history is session-local,
        # not persisted provenance.
        self._batch_runs: list[tuple[Recipe, BatchResult]] = []
        self._exported_figures: list[tuple[Path, Path]] = []
        # The Explorer's one active point-spectrum lineshape fit (Phase 6, no
        # history - docs/phase6-spectral-lineshape-analysis.md sec 4):
        # (measurement title, channel/representation label, result). Cleared
        # whenever the spectrum curve is redrawn (mirrors SpectrumPlotView's
        # own "a new curve clears the fit result" rule).
        self._active_lineshape_fit: tuple[str, str, LineshapeFit] | None = None

        self._title = QtWidgets.QLabel()
        self._facts = QtWidgets.QLabel()
        self._active = QtWidgets.QLabel()
        self._back_btn = QtWidgets.QPushButton()
        self._image = ChannelImageView()
        self._spectrum = SpectrumPlotView()
        self._hyperspectral = HyperspectralView()
        self._comparison = ComparisonView()
        self._contact = ContactSheet()
        self._stack = QtWidgets.QStackedWidget()
        self._manager = MeasurementManager()
        self._browser = ChannelBrowser()
        self._metadata = MetadataInspector()
        self._provenance = ProvenanceInspector()
        self._conventions = QtWidgets.QLabel()
        self._diagnostics = DiagnosticsPanel()
        self._briefing = BriefingPanel()
        self._process = ProcessingWorkspace()
        self._knowledge = KnowledgePanel()
        self._manual = ManualPanel()
        self._experiment_panel = ExperimentPanel()
        # Measurements are read-only observations placed on the single image (or,
        # for a hyperspectral measurement, the band map); they report across the
        # active view's channels (current + phase + topography), or - in spectral
        # mode - a mean spectrum per ROI.
        initial_image_view = (
            self._hyperspectral.band_view if model.is_hyperspectral else self._image
        )
        self._measure = MeasurementController(
            model, initial_image_view, model.single_view_specs, spectral=model.is_hyperspectral
        )
        self._measure_panel = MeasurementPanel(self._measure)

        self._build_menu()
        self._build_layout()
        self._wire()
        self._load()
        self._refresh_manager()

    # -- active session (the model/history the single set of widgets is bound to) --

    @property
    def _active_session(self) -> MeasurementSession:
        return self._sessions[self._active_index]

    @property
    def _model(self) -> ExplorerModel:
        return self._active_session.model

    @_model.setter
    def _model(self, value: ExplorerModel) -> None:
        self._active_session.model = value

    @property
    def _history(self) -> list[ExplorerModel]:
        return self._active_session.history

    @_history.setter
    def _history(self, value: list[ExplorerModel]) -> None:
        self._active_session.history = value

    def _new_measurement_id(self) -> str:
        """Mint the next stable, project-local measurement id (never reused)."""
        mid = f"measurement-{self._next_seq:04d}"
        self._next_seq += 1
        return mid

    # -- construction ---------------------------------------------------------

    def _build_menu(self) -> None:
        """The File menu: open/save a project, open a measurement, and the exports.

        Every action delegates to a handler; the menu holds no logic itself. Project
        save/open reuse the pipeline persistence (a bundle of Zarr stores); the
        exports reuse the existing io/viz writers.
        """
        file_menu = self.menuBar().addMenu("&File")
        export_menu = QtWidgets.QMenu("&Export", self)
        # Hold Python references so the QMenu wrappers stay valid (and testable).
        self._file_menu = file_menu
        self._export_menu = export_menu
        self._menu_action(file_menu, "&New Project", self._new_project, "Ctrl+N")
        self._menu_action(file_menu, "Open &Project...", self._open_project, "Ctrl+Shift+O")
        file_menu.addSeparator()
        self._menu_action(file_menu, "Open &Measurement...", self._open_measurement, "Ctrl+O")
        self._menu_action(file_menu, "&Add Measurement...", self._add_measurement, "Ctrl+Shift+A")
        self._menu_action(file_menu, "&Close Measurement", self._close_active_measurement)
        file_menu.addSeparator()
        self._menu_action(file_menu, "&Save Project", self._save_project, "Ctrl+S")
        self._menu_action(file_menu, "Save Project &As...", self._save_project_as, "Ctrl+Shift+S")
        file_menu.addSeparator()
        file_menu.addMenu(export_menu)
        self._menu_action(export_menu, "Processed &Data (Zarr)...", self._export_data_zarr)
        self._menu_action(export_menu, "&Channel (GSF)...", self._export_channel_gsf)
        self._menu_action(export_menu, "&Measurement (CSV)...", self._export_measurement_csv)
        self._menu_action(export_menu, "&Figure...", self._export_figure)
        file_menu.addSeparator()
        self._menu_action(file_menu, "Close &Project", self._close_project)
        self._menu_action(file_menu, "E&xit", self.close, "Ctrl+Q")

        help_menu = self.menuBar().addMenu("&Help")
        self._menu_action(help_menu, "&Manual", self._open_manual, "F1")

    def _menu_action(
        self, menu: QtWidgets.QMenu, text: str, slot: Any, shortcut: str | None = None
    ) -> QtGui.QAction:
        action = menu.addAction(text)
        action.triggered.connect(slot)
        if shortcut is not None:
            action.setShortcut(shortcut)
        return action

    def _build_layout(self) -> None:
        central = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(central)
        outer.setContentsMargins(8, 8, 8, 4)
        outer.setSpacing(4)

        title_font = self._title.font()
        title_font.setPointSize(title_font.pointSize() + 4)
        title_font.setBold(True)
        self._title.setFont(title_font)
        self._facts.setStyleSheet("color: #9aa0a6;")
        self._active.setStyleSheet("color: #c8c8c8;")
        outer.addWidget(self._title)
        outer.addWidget(self._facts)
        outer.addWidget(self._build_view_controls())
        self._stack.addWidget(self._image)  # page 0: single channel
        self._stack.addWidget(self._comparison)  # page 1: side-by-side comparison
        self._stack.addWidget(self._contact)  # page 2: harmonic contact sheet
        self._stack.addWidget(self._spectrum)  # page 3: point-spectroscopy curve
        self._stack.addWidget(self._hyperspectral)  # page 4: hyperspectral band map + spectrum
        outer.addWidget(self._stack, 1)
        outer.addWidget(self._active)
        self.setCentralWidget(central)

        measurements = QtWidgets.QDockWidget("Measurements")
        measurements.setWidget(self._manager)
        measurements.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, measurements)

        channels = QtWidgets.QDockWidget("Channels")
        channels.setWidget(self._browser)
        channels.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, channels)
        # Measurements on top, the channel browser below it (one left column).
        self.splitDockWidget(measurements, channels, QtCore.Qt.Orientation.Vertical)
        self.resizeDocks([measurements, channels], [150, 460], QtCore.Qt.Orientation.Vertical)

        tabs = QtWidgets.QTabWidget()
        self._inspect_tabs = tabs
        tabs.addTab(self._metadata, "Metadata")
        tabs.addTab(self._provenance, "Provenance")
        tabs.addTab(self._diagnostics, "Diagnostics")
        tabs.addTab(self._experiment_panel, "Experiment")
        tabs.addTab(self._briefing, "Briefing")
        tabs.addTab(self._measure_panel, "Measure")
        tabs.addTab(self._process, "Process")
        tabs.addTab(self._knowledge, "Knowledge")
        tabs.addTab(self._manual, "Manual")
        inspect = QtWidgets.QDockWidget("Inspect")
        inspect.setWidget(tabs)
        inspect.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, inspect)
        self.resizeDocks([channels, inspect], [260, 380], QtCore.Qt.Orientation.Horizontal)

        self.statusBar().addWidget(self._conventions)

    def _build_view_controls(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(bar)
        row.setContentsMargins(0, 2, 0, 2)

        self._back_btn.setVisible(False)
        self._back_btn.clicked.connect(self._navigate_back)
        row.addWidget(self._back_btn)
        row.addSpacing(8)

        single = QtWidgets.QPushButton("Single")
        single.setToolTip("Show one channel with full colorbar and contrast controls")
        single.clicked.connect(self._show_channel_view)
        row.addWidget(single)
        row.addSpacing(12)
        row.addWidget(QtWidgets.QLabel("Compare:"))
        # Multi-pane comparison/contact sheet are 2-D-image-only (they render every pane
        # through the image ``render_spec``); disabled for a spectral active measurement
        # rather than left to crash when clicked (see ``_refresh_view_controls``).
        self._image_only_buttons: list[QtWidgets.QPushButton] = []
        for preset, label in PRESET_LABELS.items():
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(lambda _checked=False, p=preset: self._show_comparison(p))
            row.addWidget(button)
            self._image_only_buttons.append(button)
        contact = QtWidgets.QPushButton("Contact sheet")
        contact.setToolTip("Thumbnails of every harmonic; click one to inspect it")
        contact.clicked.connect(self._show_contact)
        row.addWidget(contact)
        self._image_only_buttons.append(contact)
        row.addStretch(1)
        export = QtWidgets.QPushButton("Export figure...")
        export.setToolTip("Save the current view as a publication figure + provenance")
        export.clicked.connect(self._export_figure)
        row.addWidget(export)
        return bar

    def _wire(self) -> None:
        # Measurement Manager: switch / add / close / rename / compare across the project.
        self._manager.measurementActivated.connect(self.switch_to)
        self._manager.compareRequested.connect(self.compare_measurements)
        self._manager.addRequested.connect(self._add_measurement)
        self._manager.removeRequested.connect(self.close_measurement)
        self._manager.renameRequested.connect(self._rename_measurement)
        self._manager.batchRequested.connect(self._on_batch_requested)
        # Experiment panel: project-wide diagnostics (lazy) + cross-measurement stats.
        self._inspect_tabs.currentChanged.connect(self._on_inspect_tab_changed)
        self._experiment_panel.compareOverlayRequested.connect(self._compare_overlay)
        self._experiment_panel.exportStatisticsRequested.connect(self._export_experiment_stats)
        self._experiment_panel.copyStatisticsRequested.connect(self._copy_experiment_stats)
        # Scientific reporting (Phase 4C): deterministic documents over this project.
        self._experiment_panel.experimentReportRequested.connect(self._on_generate_experiment_report)
        self._experiment_panel.publicationPackageRequested.connect(
            self._on_generate_publication_package
        )
        self._experiment_panel.reproducibilityReportRequested.connect(
            self._on_generate_reproducibility_report
        )
        self._browser.channelSelected.connect(self._on_channel_selected)
        self._browser.representationSelected.connect(self._on_representation_selected)
        self._image.cursorMoved.connect(self._on_cursor_moved)
        self._comparison.cursorMoved.connect(self._on_comparison_cursor)
        self._contact.channelSelected.connect(self._on_channel_selected)
        # Measurements live on the single image; adding one focuses that view.
        self._measure.measurementAdded.connect(self._show_channel_view)
        self._spectrum.positionChanged.connect(self._on_spectrum_position_changed)
        self._spectrum.fitRequested.connect(self._on_spectrum_fit_requested)
        self._hyperspectral.wavenumberChanged.connect(self._on_hyperspectral_wavenumber_changed)
        self._hyperspectral.pixelClicked.connect(self._on_hyperspectral_pixel_clicked)
        self._hyperspectral.band_view.cursorMoved.connect(self._on_hyperspectral_cursor_moved)
        # Processing signals (generic, registry-driven workspace)
        self._process.operationSelected.connect(self._on_operation_selected)
        self._process.previewRequested.connect(self._on_preview_requested)
        self._process.previewAccepted.connect(self._on_preview_accepted)
        self._process.previewCancelled.connect(self._on_preview_cancelled)
        # Processing recipes (Phase 4A): create/load/delete, then Preview -> Accept
        # reuses the same generic pathway above.
        self._process.recipeSaveRequested.connect(self._save_recipe_as)
        self._process.recipeLoadRequested.connect(self._load_recipe_dialog)
        self._process.recipeDeleteRequested.connect(self._delete_recipe_dialog)
        # AI Scientist: a suggested next step hands off to the Processing Workspace.
        self._briefing.recommendationPreviewRequested.connect(self._on_recommendation_preview)
        # Knowledge Center: "Learn more" from the Workspace or a recommendation opens the article.
        self._process.learnMoreRequested.connect(self._on_operation_learn_more)
        self._briefing.learnMoreRequested.connect(self._on_operation_learn_more)
        # Manual: "How to use this" from the Workspace or a recommendation opens the page.
        self._process.manualRequested.connect(self._on_operation_manual)
        self._briefing.manualRequested.connect(self._on_operation_manual)
        # Cross-links between Knowledge and Manual (each panel emits an id; the window
        # is the only place that knows both panels, exactly like the deep-links above).
        self._knowledge.manualPageRequested.connect(self._on_open_manual_page)
        self._manual.knowledgeArticleRequested.connect(self._on_open_knowledge_article)

    # -- loading / refreshing -------------------------------------------------

    def _load(self) -> None:
        self.setWindowTitle(f"{self._model.title} - SNOMNIMAN Measurement Explorer")
        self._title.setText(self._model.title)
        self._facts.setText(_facts_line(self._model.identity()))
        self._conventions.setText("Conventions:  " + self._model.conventions_summary())
        self._browser.set_groups(self._model.channel_groups())
        self._metadata.set_sections(self._model.metadata_sections())
        self._provenance.set_provenance(
            self._model.provenance_summary(), self._model.provenance_steps()
        )
        self._diagnostics.set_report(self._model.diagnostics_report())
        self._briefing.set_briefing(self._model.scientific_briefing())
        self._briefing.set_suggestions(self._model.workflow_suggestions())
        self._process.set_catalog(self._model.operation_catalog())
        self._process.set_recipes(sorted(self._recipes))
        self._browser.select(self._model.current_channel)
        self._show_channel_view()

    def _on_channel_selected(self, canonical: str) -> None:
        # Selecting a channel (from the browser or a contact-sheet thumbnail) opens
        # it in the single, detailed view - or, in cross-measurement compare, changes
        # the shared channel for every pane (when the channel is shared). Cross-
        # measurement comparison reuses the image-only ComparisonView, so a spectral
        # active measurement always falls back to its own (spectrum) channel view.
        self._model.set_channel(canonical)  # the anchor measurement has this channel
        if (
            self._experiment_compare is not None
            and not self._model.is_spectral
            and not self._model.is_hyperspectral
        ):
            if canonical in self._experiment.shared_channels(list(self._experiment_compare)):
                self._experiment_compare_channel = canonical
                self._show_experiment_comparison()
            else:
                self._show_channel_view()  # not shared by all -> fall back to a single view
            return
        self._show_channel_view()

    def _on_representation_selected(self, representation: str) -> None:
        self._model.set_representation(representation)
        if (
            self._experiment_compare is not None
            and not self._model.is_spectral
            and not self._model.is_hyperspectral
        ):
            self._show_experiment_comparison()  # shared representation across panes
            return
        self._show_channel_view()

    # -- model switching (derivation navigation) ------------------------------

    def _update_model(self, new_model: ExplorerModel, *, push_history: bool = True) -> None:
        """Replace the active model; optionally push the old one to the history stack."""
        if push_history:
            self._history.append(self._model)
        self._model = new_model
        self._bind_measure(new_model)
        self._refresh_navigation()
        self._load()
        self._refresh_manager()

    def _bind_measure(self, model: ExplorerModel) -> None:
        """Rebind the Measurements controller + panel to *model*'s right image
        view and mode (a hyperspectral <-> image session switch needs both the
        bound ``ChannelImageView`` instance and the spectral flag to change)."""
        image_view = self._hyperspectral.band_view if model.is_hyperspectral else self._image
        self._measure.rebind(
            model, image_view, model.single_view_specs, spectral=model.is_hyperspectral
        )
        self._measure_panel.set_spectral(model.is_hyperspectral)

    def _navigate_back(self) -> None:
        if not self._history:
            return
        self._preview = None
        self._process.set_preview_mode(False)
        self._update_model(self._history.pop(), push_history=False)

    def _refresh_navigation(self) -> None:
        has_history = bool(self._history)
        self._back_btn.setVisible(has_history)
        if has_history:
            self._back_btn.setText(f"← Back to {self._history[-1].title}")

    # -- view switching -------------------------------------------------------

    def _show_channel_view(self) -> None:
        """Show the active measurement's own per-channel view (image, spectrum,
        or - a genuine third state, never an overload of ``is_spectral`` - the
        linked band-map + spectrum view for a hyperspectral measurement)."""
        self._refresh_view_controls()
        if self._model.is_hyperspectral:
            self._show_hyperspectral()
        elif self._model.is_spectral:
            self._show_spectrum()
        else:
            self._show_single()

    def _refresh_view_controls(self) -> None:
        """Enable/disable the image-only (comparison/contact-sheet) toolbar buttons."""
        image_only = not (self._model.is_spectral or self._model.is_hyperspectral)
        for button in self._image_only_buttons:
            button.setEnabled(image_only)

    def _show_single(self) -> None:
        self._experiment_compare = None  # any single view leaves cross-measurement compare
        self._stack.setCurrentWidget(self._image)
        self._refresh_channel()

    def _show_spectrum(self) -> None:
        """The point-spectroscopy analogue of :meth:`_show_single` (Rule 4: no image-only
        affordance - comparison, contact sheet, Measure - applies to a dataset with no
        2-D spatial grid; see docs/point-spectrum-discovery.md)."""
        self._experiment_compare = None
        self._spectrum.set_position_range(self._model.spectrum_position_count())
        self._stack.setCurrentWidget(self._spectrum)
        self._refresh_spectrum()

    def _on_spectrum_position_changed(self, _index: int) -> None:
        self._refresh_spectrum()

    def _on_spectrum_fit_requested(self, lo: float, hi: float) -> None:
        """Fit a Lorentzian + linear baseline within the widget's chosen window
        (docs/phase6-spectral-lineshape-analysis.md sec 3.3-3.4). A user-invoked,
        read-only analysis - it never mutates the dataset or touches provenance."""
        position = self._spectrum.position()
        try:
            result = self._model.fit_spectrum_lineshape((lo, hi), position_index=position)
        except ValueError as exc:
            QtWidgets.QMessageBox.information(self, "Fit failed", str(exc))
            return
        self._spectrum.show_fit(result)
        curve_label = self._model.spectrum_curve(position_index=position).label
        self._active_lineshape_fit = (self._model.title, curve_label, result)

    def _show_hyperspectral(self) -> None:
        """The hyperspectral analogue of :meth:`_show_single`/:meth:`_show_spectrum`:
        a linked band-map + spectrum view, never the plain 2-D image path (which
        would try to render the whole (y, x, wavenumber) cube as one image)."""
        self._experiment_compare = None
        self._hyperspectral.set_wavenumber_range(self._model.wavenumber_axis().size)
        self._stack.setCurrentWidget(self._hyperspectral)
        self._refresh_hyperspectral()

    def _on_hyperspectral_wavenumber_changed(self, _index: int) -> None:
        self._refresh_hyperspectral()

    def _on_hyperspectral_pixel_clicked(self, x_nm: float, y_nm: float) -> None:
        self._show_hyperspectral_pixel_spectrum(x_nm, y_nm)

    def _on_hyperspectral_cursor_moved(self, x_nm: float, y_nm: float, in_bounds: bool) -> None:
        if not in_bounds:
            return
        self._show_hyperspectral_pixel_spectrum(x_nm, y_nm, readout=True)

    def _show_hyperspectral_pixel_spectrum(
        self, x_nm: float, y_nm: float, *, readout: bool = False
    ) -> None:
        iy, ix, in_bounds = self._model.nearest_pixel(x_nm, y_nm)
        if not in_bounds:
            return
        curve = self._model.pixel_spectrum(x_index=ix, y_index=iy)
        self._hyperspectral.spectrum_view.show_curve(curve)
        if readout:
            self._hyperspectral.spectrum_view.set_readout(
                f"pixel ({ix}, {iy})      {curve.label}"
            )

    def _refresh_hyperspectral(self) -> None:
        self._browser.set_representations(
            self._model.representations(), self._model.current_representation
        )
        index = self._hyperspectral.wavenumber_index()
        render = self._model.band_map(index)
        self._hyperspectral.band_view.show_render(render)
        wn = self._model.wavenumber_axis()
        wn_text = f"{wn[index]:.1f} cm^-1" if index < wn.size else ""
        self._hyperspectral.set_wavenumber_readout(wn_text)
        state = self._channel_state(render.channel)
        self._active.setText(
            f"Showing   {render.title}   at {wn_text}      state: {state}"
        )
        self._diagnostics.set_histogram(
            self._model.band_map_histogram(index), render.vmin, render.vmax, render.title
        )

    def _show_comparison(self, preset: str) -> None:
        self._experiment_compare = None  # a within-measurement preset, not a cross-measurement view
        self._comparison_preset = preset
        specs = self._model.comparison_layout(preset)
        self._comparison.set_panes(specs, self._model.render_spec)
        self._stack.setCurrentWidget(self._comparison)
        self._active.setText("Comparing:   " + "      |      ".join(s.title for s in specs))

    def _show_contact(self) -> None:
        self._experiment_compare = None
        specs = self._model.harmonic_panes()
        self._contact.set_panes(specs, self._model.render_spec)
        self._stack.setCurrentWidget(self._contact)
        self._active.setText(f"Contact sheet  -  {len(specs)} optical harmonics")

    # -- processing (generic: any registered operation, no per-op wiring) ------

    def _on_operation_selected(self, step_id: str) -> None:
        """Show the selected operation or recipe (Phase 4A) in the workspace."""
        if step_id.startswith(_RECIPE_STEP_PREFIX):
            self._present_recipe(step_id[len(_RECIPE_STEP_PREFIX) :])
            return
        self._present_operation(step_id)

    def _present_recipe(self, name: str) -> None:
        """Render a saved recipe's ordered steps, ready to Preview or Delete."""
        recipe = self._recipes.get(name)
        if recipe is None:
            return
        self._process.show_recipe(name, self._model.recipe_steps(recipe), recipe.created_at)

    def _present_operation(self, step_id: str) -> None:
        """Render an operation in the workspace with its project-wide input candidates."""
        option = self._model.operation_option(step_id)
        self._process.show_operation(option, self._build_input_candidates(option))

    def _build_input_candidates(
        self, option: OperationOption
    ) -> dict[str, list[InputCandidate]]:
        """Candidate datasets for each non-primary input slot (project datasets but the active).

        Also rebuilds ``_input_candidate_map`` so a chosen key resolves back to a
        Dataset at Preview time. The same pool is offered to every extra slot.
        """
        self._input_candidate_map = {}
        if not option.inputs:
            return {}
        candidates: list[InputCandidate] = []
        index = 0
        for session in self._sessions:
            for model in [*session.history, session.model]:
                if model.dataset is self._model.dataset:
                    continue  # the active dataset is the "primary" input
                key = str(index)
                self._input_candidate_map[key] = model.dataset
                candidates.append(InputCandidate(key=key, label=f"{session.title} / {model.title}"))
                index += 1
        return {slot.name: candidates for slot in option.inputs}

    def _resolve_inputs(self) -> dict[str, Dataset] | None:
        """Map the workspace's chosen input keys back to Datasets (extra slots only).

        Returns ``None`` for a single-input operation. Raises
        :class:`~snomniman.core.exceptions.ProcessingError` if a slot was left
        unfilled (surfaced by the caller's preview-failure handling).
        """
        keys = self._process.current_input_keys()
        if not keys:
            return None
        inputs: dict[str, Dataset] = {}
        for slot, key in keys.items():
            dataset = self._input_candidate_map.get(key)
            if dataset is None:
                raise ProcessingError(f"no dataset chosen for input {slot!r}")
            inputs[slot] = dataset
        return inputs

    def _on_recommendation_preview(self, step_id: str, params: dict[str, Any]) -> None:
        """A suggested next step (from the AI Scientist) opens, pre-configured, in the Workspace.

        This is the whole point of building the Workspace first: an AI recommendation
        needs no special execution path - it selects a registered operation, fills its
        parameters, and runs the same generic preview every operation uses.
        """
        self._inspect_tabs.setCurrentWidget(self._process)
        self._process.highlight_operation(step_id)
        self._present_operation(step_id)
        self._process.apply_params(params)
        self._on_preview_requested(step_id, params)

    def _on_operation_learn_more(self, step_id: str) -> None:
        """Open the Knowledge Center article for an operation (from Workspace or AI)."""
        article = article_for_operation(step_id)
        if article is None:
            return
        self._inspect_tabs.setCurrentWidget(self._knowledge)
        self._knowledge.show_article(article.article_id)

    def _on_operation_manual(self, step_id: str) -> None:
        """Open the Manual page for an operation (from Workspace or AI)."""
        page = page_for_operation(step_id)
        if page is None:
            return
        self._inspect_tabs.setCurrentWidget(self._manual)
        self._manual.show_page(page.page_id)

    def _on_open_manual_page(self, page_id: str) -> None:
        """Open a Manual page by id (a Knowledge article's 'How to use this' link)."""
        self._inspect_tabs.setCurrentWidget(self._manual)
        self._manual.show_page(page_id)

    def _on_open_knowledge_article(self, article_id: str) -> None:
        """Open a Knowledge article by id (a Manual page's 'See also' link)."""
        self._inspect_tabs.setCurrentWidget(self._knowledge)
        self._knowledge.show_article(article_id)

    def _open_manual(self) -> None:
        """Help > Manual (F1): the global, always-available entry point."""
        self._inspect_tabs.setCurrentWidget(self._manual)
        self._manual.focus_search()

    def _on_preview_requested(self, step_id: str, params: dict[str, Any]) -> None:
        """Run the operation on a copy and show a before/after preview.

        The model does the science (build the step, apply it, diff the result); the
        window only lays the panes out and reveals the summary. Nothing is
        committed - the derived dataset rides on the preview until Accept.
        """
        is_recipe = step_id.startswith(_RECIPE_STEP_PREFIX)
        try:
            if is_recipe:
                recipe = self._recipes[step_id[len(_RECIPE_STEP_PREFIX) :]]
                preview = self._model.preview_recipe(recipe)
            else:
                inputs = self._resolve_inputs()
                preview = self._model.preview_operation(step_id, params, inputs)
        except (ProcessingError, DatasetError) as exc:
            QtWidgets.QMessageBox.warning(self, "Preview failed", str(exc))
            return

        self._preview = preview
        header = preview.title if is_recipe else self._operation_title(step_id)
        self._active.setText(f"Preview: {header} — Accept to commit, Cancel to discard")
        if preview.panes:
            # Image-shaped preview (incl. a hyperspectral band-0 representative
            # slice) - the existing comparison surface, unchanged.
            specs = [pane.spec for pane in preview.panes]
            renders: dict[PaneSpec, RenderData] = {
                pane.spec: pane.render for pane in preview.panes
            }
            self._comparison.set_panes(specs, renders.__getitem__)
            self._stack.setCurrentWidget(self._comparison)
        elif preview.spectral_panes:
            # Curve-shaped preview (a SPECTRUM/LINE_SCAN focus channel, or the
            # freshly-FFT'd output of an operation like spectrum.fft_interferogram)
            # - reuses the existing page-3 spectrum viewer's multi-curve overlay,
            # no new preview surface needed.
            curves = {p.label: p.curve for p in preview.spectral_panes}
            self._spectrum.show_curves(curves)
            self._stack.setCurrentWidget(self._spectrum)
        # Neither: an honest decline (e.g. no 2-D/curve view for this focus
        # channel yet) - the change summary in the Workspace still explains what
        # would happen; nothing crashes.
        self._process.show_preview(preview)
        self._process.set_preview_mode(True)

    def _on_preview_accepted(self) -> None:
        if self._preview is None:
            return
        new_model = ExplorerModel(self._preview.dataset, title=self._preview.title)
        self._preview = None
        self._process.set_preview_mode(False)
        self._update_model(new_model)

    def _on_preview_cancelled(self) -> None:
        self._preview = None
        self._process.set_preview_mode(False)
        self._show_channel_view()  # returns to whichever view the active model needs

    def _operation_title(self, step_id: str) -> str:
        return self._model.operation_option(step_id).title

    # -- project session: new / open / save -----------------------------------

    def _new_project(self) -> None:
        """Start a fresh project from a newly chosen measurement (replaces the current)."""
        self._open_measurement()

    def _close_project(self) -> None:
        """Close the whole project and start fresh from a newly chosen measurement.

        A project always holds at least one measurement, so (like New Project) this
        prompts for one; cancelling keeps the current project untouched.
        """
        self._open_measurement()

    def _open_measurement(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Open neaSNOM measurement directory"
        )
        if not path:
            return
        try:
            model = ExplorerModel.open_measurement(path)
        except ReaderError as exc:
            QtWidgets.QMessageBox.critical(self, "Could not open measurement", str(exc))
            return
        self._project_path = None
        self.load_explorer_model(model)

    def _add_measurement(self) -> None:
        """Open a measurement and append it to the current project (does not replace)."""
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Add neaSNOM measurement directory"
        )
        if not path:
            return
        try:
            model = ExplorerModel.open_measurement(path)
        except ReaderError as exc:
            QtWidgets.QMessageBox.critical(self, "Could not open measurement", str(exc))
            return
        self.add_measurement_model(model)

    def _rename_measurement(self, index: int) -> None:
        """Prompt for and apply a new display name for the measurement at ``index``."""
        if not 0 <= index < len(self._sessions):
            return
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Rename measurement", "Name:", text=self._sessions[index].title
        )
        if ok and name:
            self.rename_measurement(index, name)

    def _close_active_measurement(self) -> None:
        """File-menu handler: close the currently active measurement."""
        self.close_measurement(self._active_index)

    def _open_project(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Open SNOMNIMAN project")
        if not path:
            return
        try:
            project = load_project(path)
        except ReaderError as exc:
            QtWidgets.QMessageBox.critical(self, "Could not open project", str(exc))
            return
        self.load_project_object(project)
        self._project_path = Path(path)

    def _save_project(self) -> None:
        if self._project_path is None:
            self._save_project_as()
        else:
            self._write_project(self._project_path)

    def _save_project_as(self) -> None:
        default = f"{self._project_title}.snomproj"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save project as", default, "SNOMNIMAN project (*.snomproj)"
        )
        if not path:
            return
        bundle = Path(path)
        if bundle.suffix != ".snomproj":
            bundle = bundle.with_suffix(".snomproj")
        self._write_project(bundle)

    def _write_project(self, path: Path) -> None:
        try:
            save_project(self.current_project(), path, overwrite=True)
        except (OSError, FileExistsError) as exc:
            QtWidgets.QMessageBox.warning(self, "Save failed", str(exc))
            return
        self._project_path = path
        QtWidgets.QMessageBox.information(self, "Project saved", f"Saved project:\n{path}")

    # -- processing recipes (Phase 4A: create/load/delete a saved recipe) -----

    def _save_recipe_as(self) -> None:
        """Prompt for a name and a file, then capture + save the active history."""
        name, ok = QtWidgets.QInputDialog.getText(self, "Save as recipe", "Recipe name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save recipe", f"{name}{RECIPE_SUFFIX}", f"SNOMNIMAN Recipe (*{RECIPE_SUFFIX})"
        )
        if not path:
            return
        bundle = Path(path)
        if bundle.suffix != RECIPE_SUFFIX:
            bundle = bundle.with_suffix(RECIPE_SUFFIX)
        self._write_recipe(name, bundle)

    def _write_recipe(self, name: str, path: Path) -> None:
        """Capture the active measurement's history as *name* and save it to *path*."""
        try:
            recipe = self._model.capture_recipe(name)
        except ProcessingError as exc:
            QtWidgets.QMessageBox.warning(self, "Cannot save recipe", str(exc))
            return
        try:
            save_recipe(recipe, path, overwrite=True)
        except OSError as exc:
            QtWidgets.QMessageBox.warning(self, "Cannot save recipe", str(exc))
            return
        self._recipes[recipe.name] = recipe
        self._recipe_paths[recipe.name] = path
        self._refresh_recipes()

    def _load_recipe_dialog(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load recipe", "", f"SNOMNIMAN Recipe (*{RECIPE_SUFFIX})"
        )
        if not path:
            return
        self._read_recipe(Path(path))

    def _read_recipe(self, path: Path) -> None:
        try:
            recipe = load_recipe(path)
        except ReaderError as exc:
            QtWidgets.QMessageBox.warning(self, "Cannot load recipe", str(exc))
            return
        self._recipes[recipe.name] = recipe
        self._recipe_paths[recipe.name] = path
        self._refresh_recipes()

    def _delete_recipe_dialog(self, name: str) -> None:
        reply = QtWidgets.QMessageBox.question(
            self,
            "Delete recipe",
            f"Delete the recipe '{name}'? This also removes its saved file, if any.",
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        self._remove_recipe(name)

    def _remove_recipe(self, name: str) -> None:
        path = self._recipe_paths.pop(name, None)
        if path is not None:
            delete_recipe(path)
        self._recipes.pop(name, None)
        self._refresh_recipes()

    def _refresh_recipes(self) -> None:
        self._process.set_recipes(sorted(self._recipes))

    # -- batch processing (Phase 4B: replay one recipe across many measurements) --

    def _on_batch_requested(self) -> None:
        """Dialog-driven: choose scope + recipe, confirm, run with a progress dialog."""
        if not self._recipes:
            QtWidgets.QMessageBox.information(
                self,
                "No recipes available",
                "Save a recipe from a measurement's processing history first "
                "(Process tab -> Save current history as recipe...).",
            )
            return

        selected = self._manager.selected_rows()
        indices = list(range(len(self._sessions)))
        if selected:
            scope, ok = QtWidgets.QInputDialog.getItem(
                self,
                "Batch scope",
                "Run the recipe on:",
                [f"All measurements ({len(self._sessions)})", f"Selected ({len(selected)})"],
                editable=False,
            )
            if not ok:
                return
            if scope.startswith("Selected"):
                indices = selected

        recipe_name, ok = QtWidgets.QInputDialog.getItem(
            self, "Choose a recipe", "Recipe:", sorted(self._recipes), editable=False
        )
        if not ok:
            return
        recipe = self._recipes[recipe_name]

        reply = QtWidgets.QMessageBox.question(
            self,
            "Run batch",
            f"Replay recipe '{recipe.name}' on {len(indices)} measurement(s)?\n"
            "Any measurement it does not apply to will be skipped, explained, and "
            "the rest will continue.",
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        progress = QtWidgets.QProgressDialog(
            "Starting batch...", "Cancel", 0, len(indices), self
        )
        progress.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        progress.setWindowTitle("Batch processing")
        progress.setMinimumDuration(0)

        def on_progress(i: int, total: int, outcome: BatchOutcome) -> None:
            progress.setValue(i)
            progress.setLabelText(f"[{outcome.status}] {outcome.title}  ({i}/{total})")
            QtWidgets.QApplication.processEvents()

        result = self._run_batch(
            recipe, indices, on_progress=on_progress, should_stop=progress.wasCanceled
        )
        progress.setValue(len(result.outcomes))
        progress.close()

        self._show_batch_result(result, recipe)
        summary = (
            f"Batch '{recipe.name}': {len(result.succeeded)} succeeded, "
            f"{len(result.skipped)} skipped, {len(result.failed)} failed "
            f"of {result.requested} requested ({result.elapsed_seconds:.1f}s)."
        )
        if result.stopped_early:
            summary += " Stopped early by request."
        QtWidgets.QMessageBox.information(self, "Batch complete", summary)

    def _run_batch(
        self,
        recipe: Recipe,
        indices: Sequence[int],
        *,
        on_progress: Callable[[int, int, BatchOutcome], None] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> BatchResult:
        """Replay *recipe* on the sessions at *indices*; commit each success in place.

        Mirrors accepting a manual Preview for every successful measurement: the
        updated session's prior model moves to its history, and its new active
        model wraps the recipe's derived dataset - without going through the
        Preview/Accept UI (batch calls :func:`snomniman.batch.run_batch`, which
        replays via the unchanged ``apply_recipe`` directly, skipping the per-
        measurement before/after rendering a UI Preview needs but a batch does not).
        The currently displayed measurement, if included, is refreshed once at the
        end - never per measurement, so watching a long batch run stays cheap.
        """
        measurements = [self._measurement_of(self._sessions[i]) for i in indices]
        result = run_batch(recipe, measurements, on_progress=on_progress, should_stop=should_stop)
        touched_active = False
        for i, outcome in zip(indices, result.outcomes, strict=False):
            if outcome.measurement is None:
                continue
            session = self._sessions[i]
            session.history.append(session.model)
            session.model = ExplorerModel(
                outcome.measurement.current, title=f"{session.title} -> recipe '{recipe.name}'"
            )
            if i == self._active_index:
                touched_active = True
        if touched_active:
            self._load()
            self._refresh_navigation()
        self._refresh_manager()
        return result

    def _show_batch_result(self, result: BatchResult, recipe: Recipe) -> None:
        """Surface a completed batch run in the Experiment tab (no new report artifact)."""
        table = self._experiment.batch_result_table(result, recipe)
        self._experiment_panel.set_batch_result(table)
        self._inspect_tabs.setCurrentWidget(self._experiment_panel)
        self._batch_runs.append((recipe, result))  # remembered for Phase 4C reports

    # -- scientific reporting (Phase 4C: deterministic documents over the project) --

    def _on_generate_experiment_report(self) -> None:
        choice = self._prompt_report_path(f"{self._project_title} - experiment report")
        if choice is None:
            return
        path, fmt = choice
        self._write_report(self._build_report_model().experiment_report(), path, fmt)

    def _on_generate_publication_package(self) -> None:
        choice = self._prompt_report_path(f"{self._project_title} - publication package")
        if choice is None:
            return
        path, fmt = choice
        self._write_report(self._build_report_model().publication_package(), path, fmt)

    def _on_generate_reproducibility_report(self) -> None:
        default = f"{self._sessions[self._active_index].title} - reproducibility report"
        choice = self._prompt_report_path(default)
        if choice is None:
            return
        path, fmt = choice
        report = self._build_report_model().reproducibility_report(self._active_index)
        self._write_report(report, path, fmt)

    def _prompt_report_path(self, default_name: str) -> tuple[Path, str] | None:
        """Ask where to save a report; the chosen extension selects the format."""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save report", f"{default_name}.md", "Markdown (*.md);;HTML (*.html)"
        )
        if not path:
            return None
        target = Path(path)
        if target.suffix.lower() == ".html":
            return target, REPORT_FORMAT_HTML
        if target.suffix.lower() != ".md":
            target = target.with_suffix(".md")
        return target, REPORT_FORMAT_MARKDOWN

    def _build_report_model(self) -> ReportModel:
        """Compose a `ReportModel` from exactly what this session already holds."""
        self._capture_active_session()
        return ReportModel(
            self._sessions,
            self._project_title,
            recipes=self._recipes,
            batch_runs=self._batch_runs,
            exported_figures=self._exported_figures,
            experiment_stats=self._experiment_stats,
            active_lineshape_fit=self._active_lineshape_fit,
        )

    def _write_report(self, report: Report, path: Path, fmt: str) -> None:
        try:
            written = export_report(report, path, fmt)
        except OSError as exc:
            QtWidgets.QMessageBox.warning(self, "Cannot save report", str(exc))
            return
        QtWidgets.QMessageBox.information(self, "Report saved", f"Saved report:\n{written}")

    def current_project(self) -> Project:
        """Bundle every measurement (each with its history + view + overlays) for saving."""
        self._capture_active_session()
        measurements = tuple(self._measurement_of(s) for s in self._sessions)
        return Project(
            title=self._project_title,
            measurements=measurements,
            current_index=self._active_index,
            session={"next_measurement_seq": self._next_seq},
        )

    def _measurement_of(self, session: MeasurementSession) -> Measurement:
        """Build the immutable :class:`Measurement` snapshot of one working session."""
        models = [*session.history, session.model]
        doc: dict[str, Any] = {
            "titles": [m.title for m in models],
            "view": session.view_state,
            "measurements": session.measure_records,
        }
        return measurement_from_history(
            [m.dataset for m in models],
            title=session.title,
            measurement_id=session.measurement_id,
            current_index=len(session.history),
            session=doc,
        )

    def _capture_active_session(self) -> None:
        """Snapshot the live widget state (view + overlays) into the active session.

        The active session's view/overlays live in the widgets until captured; the
        inactive sessions already hold the state captured when they were last left.
        """
        s = self._active_session
        s.view_state = self._view_state()
        s.measure_records = self._measure.to_records()

    # -- multi-measurement management (switch / add / rename / close) ----------

    def switch_to(self, index: int) -> None:
        """Make measurement ``index`` active, preserving both sessions (no disk reload).

        The outgoing session's live view + overlays are captured first; the incoming
        session's captured state is restored into the single set of widgets.
        """
        if not 0 <= index < len(self._sessions) or index == self._active_index:
            return
        self._capture_active_session()
        self._active_index = index
        self._bind_active_session()

    def add_measurement_model(self, model: ExplorerModel) -> None:
        """Append a measurement to the project and switch to it (the dialog seam).

        Public so tests can add a measurement without a file dialog or disk access.
        """
        self._capture_active_session()
        self._sessions.append(
            MeasurementSession(
                model=model, measurement_id=self._new_measurement_id(), title=model.title
            )
        )
        self._active_index = len(self._sessions) - 1
        self._bind_active_session()

    def rename_measurement(self, index: int, name: str) -> None:
        """Set a measurement's display name (the seam ``_rename_measurement`` calls)."""
        if not 0 <= index < len(self._sessions) or not name:
            return
        self._sessions[index].title = name
        # For a single-measurement project, the project name follows the measurement.
        if len(self._sessions) == 1:
            self._project_title = name
        self._refresh_manager()

    def close_measurement(self, index: int) -> None:
        """Close the measurement at ``index``.

        Closing the active measurement binds a neighbour into the widgets; closing
        an inactive one leaves the active view untouched. A project keeps at least
        one measurement, so closing the last one starts a fresh project instead.
        """
        if not 0 <= index < len(self._sessions):
            return
        if len(self._sessions) == 1:
            self._close_project()
            return
        closing_active = index == self._active_index
        del self._sessions[index]
        if index < self._active_index:
            self._active_index -= 1
        elif closing_active:
            self._active_index = min(self._active_index, len(self._sessions) - 1)
        if closing_active:
            self._bind_active_session()
        else:
            self._refresh_manager()

    def _refresh_manager(self) -> None:
        """Refresh the experiment browser + the window title for the open measurements.

        With a single measurement the window title is left exactly as the single-
        measurement Explorer sets it, so the app feels unchanged; the "m/n" hint
        appears only once a project holds more than one measurement.
        """
        self._experiment.set_sessions(self._sessions)
        self._manager.set_rows(self._experiment.browser_rows(), self._active_index)
        n = len(self._sessions)
        if n > 1:
            self.setWindowTitle(
                f"{self._active_session.title} - Measurement {self._active_index + 1}/{n}"
                " - SNOMNIMAN Measurement Explorer"
            )

    # -- experiment analysis (Phase 2B, read-only: aggregates, never derives) --

    def compare_measurements(self, indices: list[int]) -> None:
        """Show the selected measurements side by side (shared channel, synced view).

        Reuses the existing comparison viewer: each pane is rendered by its own
        measurement's model, so no second comparison system is introduced. Nothing
        is created or modified - this is a read-only view across measurements.
        """
        chosen = [i for i in indices if 0 <= i < len(self._sessions)]
        if len(chosen) < 2:
            return
        # Cross-measurement comparison reuses the image-only ComparisonView (each pane
        # is rendered through a per-measurement ``render_spec``); a point-spectroscopy
        # or hyperspectral measurement has no such rendering yet, so both are excluded
        # here rather than left to crash when a shared channel name happens to line up.
        image_only = [
            i for i in chosen
            if not self._sessions[i].model.is_spectral
            and not self._sessions[i].model.is_hyperspectral
        ]
        if len(image_only) < 2:
            QtWidgets.QMessageBox.information(
                self,
                "Compare measurements",
                "Point-spectroscopy and hyperspectral measurements cannot be compared "
                "in this view yet; select two or more image measurements.",
            )
            return
        chosen = image_only
        self._experiment.set_sessions(self._sessions)
        shared = self._experiment.shared_channels(chosen)
        if not shared:
            QtWidgets.QMessageBox.information(
                self,
                "Compare measurements",
                "The selected measurements share no common channel to compare.",
            )
            return
        # Anchor the comparison on the first selected measurement: it becomes active,
        # so the channel browser drives the *shared* channel/representation consistently.
        if self._active_index != chosen[0]:
            self._capture_active_session()
            self._active_index = chosen[0]
            self._bind_active_session()  # binds widgets to the anchor (resets compare mode)
        current = self._model.current_channel
        self._experiment_compare = tuple(chosen)
        self._experiment_compare_channel = current if current in shared else shared[0]
        self._show_experiment_comparison()

    def _show_experiment_comparison(self) -> None:
        """Render the active cross-measurement comparison into the shared viewer."""
        if self._experiment_compare is None:
            return
        panes = self._experiment.comparison_panes(
            list(self._experiment_compare),
            self._experiment_compare_channel,
            self._model.current_representation,
        )
        specs = [p.spec for p in panes]
        renders = {p.spec: p.render for p in panes}
        self._comparison.set_panes(specs, renders.__getitem__)
        self._stack.setCurrentWidget(self._comparison)
        self._active.setText(
            "Comparing measurements:   " + "      |      ".join(s.title for s in specs)
        )

    def _on_inspect_tab_changed(self, _index: int) -> None:
        """Populate the experiment diagnostics lazily, only when its tab is opened."""
        if self._inspect_tabs.currentWidget() is self._experiment_panel:
            self._refresh_experiment_diagnostics()

    def _refresh_experiment_diagnostics(self) -> None:
        self._experiment.set_sessions(self._sessions)
        self._experiment_panel.set_diagnostics(self._experiment.diagnostics_table())

    def _compare_overlay(self) -> None:
        """Evaluate the active measurement's overlay across every measurement (Part 5).

        The same nm geometry and the active channel/representation are measured on
        each measurement via the existing measurement engine; whether the region is
        scientifically meaningful across these scans is the researcher's call.
        """
        geometry = self._measure.active_geometry()
        if geometry is None:
            QtWidgets.QMessageBox.information(
                self,
                "Cross-measurement statistics",
                "Place a line / rectangle / polygon on the active measurement (Measure tab) first.",
            )
            return
        kind, geom = geometry
        channel = self._model.current_channel
        representation = self._model.current_representation
        indices = list(range(len(self._sessions)))
        self._experiment.set_sessions(self._sessions)
        if kind == "line":
            p0, p1 = geom["points"]
            table = self._experiment.compare_profile(
                indices,
                (float(p0[0]), float(p0[1])),
                (float(p1[0]), float(p1[1])),
                channel,
                representation,
            )
        elif kind == "rectangle":
            x, y = geom["pos"]
            w, h = geom["size"]
            table = self._experiment.compare_region(
                indices,
                "rectangle",
                (float(x), float(y), float(x) + float(w), float(y) + float(h)),
                channel,
                representation,
            )
        else:  # polygon
            vertices = [(float(px), float(py)) for px, py in geom["points"]]
            table = self._experiment.compare_region(
                indices, "polygon", vertices, channel, representation
            )
        self._experiment_stats = table
        self._experiment_panel.set_statistics(table)

    def _export_experiment_stats(self) -> None:
        if self._experiment_stats is None:
            QtWidgets.QMessageBox.information(
                self,
                "Export comparison",
                "Compare an overlay across measurements first, then export it.",
            )
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export cross-measurement comparison",
            f"{self._project_title}_comparison.csv",
            "CSV (*.csv)",
        )
        if not path:
            return
        text = experiment_table_to_csv(self._experiment_stats, self._experiment_export_context())
        Path(path).write_text(text, encoding="utf-8")

    def _copy_experiment_stats(self) -> None:
        if self._experiment_stats is None:
            return
        text = experiment_table_to_csv(
            self._experiment_stats, self._experiment_export_context(), delimiter="\t"
        )
        QtWidgets.QApplication.clipboard().setText(text)

    def _experiment_export_context(self) -> ExperimentExportContext:
        return ExperimentExportContext(
            project=self._project_title,
            measurement_count=len(self._sessions),
            conventions=self._model.conventions_summary(),
            snomniman_version=current_software().get("snomniman", ""),
            created_at=datetime.now(UTC).isoformat(),
        )

    def load_explorer_model(self, model: ExplorerModel) -> None:
        """Reset the window to a single fresh measurement (New / Open Measurement)."""
        self._next_seq = 1
        self._sessions = [
            MeasurementSession(
                model=model, measurement_id=self._new_measurement_id(), title=model.title
            )
        ]
        self._active_index = 0
        self._project_title = model.title
        self._preview = None
        self._comparison_preset = None
        self._process.set_preview_mode(False)
        self._bind_active_session()

    def load_project_object(self, project: Project) -> None:
        """Rebuild the window from a saved :class:`Project` (every measurement + session)."""
        self._sessions = [self._session_of(m) for m in project.measurements]
        self._active_index = project.current_index
        self._project_title = project.title
        self._next_seq = _safe_int(
            project.session.get("next_measurement_seq"), len(self._sessions) + 1
        )
        self._preview = None
        self._comparison_preset = None
        self._process.set_preview_mode(False)
        self._bind_active_session()

    def _session_of(self, measurement: Measurement) -> MeasurementSession:
        """Rebuild a working session from an immutable :class:`Measurement` snapshot."""
        doc = dict(measurement.session)
        titles = doc.get("titles")
        models: list[ExplorerModel] = []
        for index, dataset in enumerate(measurement.datasets):
            title = titles[index] if isinstance(titles, list) and index < len(titles) else None
            models.append(ExplorerModel(dataset, title=title if isinstance(title, str) else None))
        view = doc.get("view")
        records = doc.get("measurements")
        return MeasurementSession(
            model=models[measurement.current_index],
            measurement_id=measurement.measurement_id,
            title=measurement.title,
            history=models[: measurement.current_index],
            measure_records=list(records) if isinstance(records, list) else [],
            view_state=dict(view) if isinstance(view, dict) else {},
        )

    def _bind_active_session(self) -> None:
        """Bind the single set of widgets to the active session and restore its view.

        Used after the active measurement changes (load, switch): the widgets are
        repainted from the active session's model and its captured view + overlays
        are restored, all without re-reading anything from disk.
        """
        s = self._active_session
        self._comparison_preset = None
        self._preview = None
        self._process.set_preview_mode(False)
        self._bind_measure(s.model)
        self._refresh_navigation()
        self._load()
        self._restore_view_and_measurements(s)
        self._refresh_manager()

    def _view_state(self) -> dict[str, Any]:
        current = self._stack.currentWidget()
        mode = "single"
        if current is self._comparison:
            mode = "comparison"
        elif current is self._contact:
            mode = "contact"
        elif current is self._spectrum:
            mode = "spectrum"
        elif current is self._hyperspectral:
            mode = "hyperspectral"
        state: dict[str, Any] = {
            "channel": self._model.current_channel,
            "representation": self._model.current_representation,
            "mode": mode,
            "preset": self._comparison_preset,
        }
        if mode == "hyperspectral":
            # The spectrum is a first-class object: the band a researcher was
            # looking at survives save/reopen, exactly like channel/representation.
            state["wavenumber_index"] = self._hyperspectral.wavenumber_index()
        return state

    def _restore_view_and_measurements(self, s: MeasurementSession) -> None:
        """Restore the active view (channel / representation / mode) and overlays."""
        view = s.view_state or {}
        channel = view.get("channel")
        if isinstance(channel, str) and channel in self._model.dataset.channel_names:
            self._model.set_channel(channel)
            representation = view.get("representation")
            if isinstance(representation, str) and representation in self._model.representations():
                self._model.set_representation(representation)
            self._browser.select(channel)
            if self._model.is_hyperspectral:
                self._refresh_hyperspectral()
            elif self._model.is_spectral:
                self._refresh_spectrum()
            else:
                self._refresh_channel()
        records = s.measure_records
        has_measurements = bool(records)
        if has_measurements:
            self._measure.load_records(records)
        # Measurements and multi-pane comparison/contact views are image-only; a
        # spectral or hyperspectral active measurement always restores into its
        # own channel view.
        mode = view.get("mode", "single")
        preset = view.get("preset")
        if self._model.is_hyperspectral:
            self._show_channel_view()  # sets the wavenumber range + shows band 0
            wavenumber_index = view.get("wavenumber_index")
            if isinstance(wavenumber_index, int):
                self._hyperspectral.set_wavenumber_index(wavenumber_index)
                self._refresh_hyperspectral()
        elif self._model.is_spectral:
            self._show_channel_view()
        elif not has_measurements and mode == "comparison" and isinstance(preset, str):
            self._show_comparison(preset)
        elif not has_measurements and mode == "contact":
            self._show_contact()
        else:
            self._show_single()

    # -- data export (processed dataset / channel / measurement) --------------

    def _export_data_zarr(self) -> None:
        """Export the current (processed) dataset as a loss-less canonical Zarr store."""
        default = f"{self._model.title}.zarr"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export processed data (Zarr)", default, "Zarr store (*.zarr)"
        )
        if not path:
            return
        store_path = Path(path)
        if store_path.suffix != ".zarr":
            store_path = store_path.with_suffix(".zarr")
        try:
            written = write_zarr(self._model.dataset, store_path, overwrite=True)
        except OSError as exc:
            QtWidgets.QMessageBox.warning(self, "Export failed", str(exc))
            return
        QtWidgets.QMessageBox.information(
            self,
            "Data exported",
            f"Saved the processed dataset (full provenance) to:\n{written}",
        )

    def _export_channel_gsf(self) -> None:
        """Export the channel/representation on screen as a Gwyddion Simple Field grid.

        For a hyperspectral measurement, exports the *currently displayed band* -
        one wavenumber slice is an ordinary 2-D grid, so this reuses the unmodified
        image exporter via ``ExplorerModel.band_dataset`` rather than a new format.
        """
        if self._model.is_spectral:
            QtWidgets.QMessageBox.information(
                self, "Not available",
                "GSF export is a 2-D spatial grid format; it is not available for a "
                "point-spectroscopy measurement. Use Export -> Processed Data (Zarr) instead.",
            )
            return
        channel = self._model.current_channel
        representation = self._model.current_representation
        if self._model.is_hyperspectral:
            index = self._hyperspectral.wavenumber_index()
            dataset = self._model.band_dataset(index)
            wn = self._model.wavenumber_axis()[index]
            default = f"{self._model.title}_{channel}_{representation}_{wn:.0f}cm-1.gsf"
        else:
            dataset = self._model.dataset
            default = f"{self._model.title}_{channel}_{representation}.gsf"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export channel (GSF)", default, "Gwyddion Simple Field (*.gsf)"
        )
        if not path:
            return
        try:
            gsf_path, provenance_path = export_channel_gsf(
                dataset, channel, path, representation=representation
            )
        except (OSError, DatasetError, ProcessingError) as exc:
            QtWidgets.QMessageBox.warning(self, "Export failed", str(exc))
            return
        QtWidgets.QMessageBox.information(
            self,
            "Channel exported",
            f"Saved {channel} ({representation}):\n{gsf_path}\n\n"
            f"with provenance:\n{provenance_path.name}",
        )

    def _export_measurement_csv(self) -> None:
        """Export the active measurement's numbers as CSV (delegates to the Measure panel)."""
        if self._model.is_spectral:
            QtWidgets.QMessageBox.information(
                self, "Not available",
                "Line/ROI measurements are not yet available for a point-spectroscopy "
                "measurement (no 2-D spatial grid to measure across).",
            )
            return
        self._inspect_tabs.setCurrentWidget(self._measure_panel)
        self._measure_panel.export_active_csv()

    # -- publication export ---------------------------------------------------

    def _figure_inputs(self) -> tuple[str, list[tuple[PaneSpec, tuple[float, float]]], list[Any]]:
        """Gather (kind, panels-with-levels, overlays) for the current view."""
        if self._experiment_compare is not None:
            # Cross-measurement compare is not a single-dataset figure source (each
            # pane is a different measurement); export the active measurement's
            # current channel instead rather than render every pane from one model.
            spec = PaneSpec(self._model.current_channel, self._model.current_representation)
            return "single", [(spec, self._image.levels)], []
        current = self._stack.currentWidget()
        if current is self._comparison and self._comparison.specs:
            panels = [
                (spec, pane.levels)
                for spec, pane in zip(self._comparison.specs, self._comparison.panes, strict=True)
            ]
            return "comparison", panels, []
        if current is self._contact:
            panels = []
            for spec in self._model.harmonic_panes():
                rd = self._model.render_spec(spec)
                panels.append((spec, (rd.vmin, rd.vmax)))
            return "harmonic_series", panels, []
        # single view: the current channel, plus any measurement overlays
        overlays = self._measure.overlay_specs()
        kind = "measurement" if overlays else "single"
        current_spec = PaneSpec(self._model.current_channel, self._model.current_representation)
        return kind, [(current_spec, self._image.levels)], overlays

    def _export_figure(self) -> None:
        if self._model.is_spectral or self._model.is_hyperspectral:
            QtWidgets.QMessageBox.information(
                self, "Not available",
                "Publication figure export is not yet available for a point-spectroscopy "
                "or hyperspectral measurement. Use Export -> Processed Data (Zarr) or "
                "Export -> Channel (GSF) instead.",
            )
            return
        kind, panels, overlays = self._figure_inputs()
        spec = self._model.figure_spec(panels, overlays, kind=kind, title=self._model.title)
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export figure",
            f"{self._model.title}.pdf",
            "PDF (*.pdf);;PNG (*.png);;SVG (*.svg)",
        )
        if not path:
            return
        figure_path, provenance_path = viz.export(spec, self._model.dataset, path)
        self._exported_figures.append((figure_path, provenance_path))  # for Phase 4C reports
        QtWidgets.QMessageBox.information(
            self,
            "Figure exported",
            f"Saved publication figure:\n{figure_path}\n\n"
            f"with provenance:\n{provenance_path.name}",
        )

    def _refresh_channel(self) -> None:
        self._browser.set_representations(
            self._model.representations(), self._model.current_representation
        )
        self._refresh_image()

    def _refresh_spectrum(self) -> None:
        self._browser.set_representations(
            self._model.representations(), self._model.current_representation
        )
        position = self._spectrum.position()
        curve = self._model.spectrum_curve(position_index=position)
        self._spectrum.show_curve(curve)  # also clears any fit overlay - mirror that here
        self._active_lineshape_fit = None
        state = self._channel_state(curve.channel)
        position_note = (
            f"      position {position + 1}/{self._model.spectrum_position_count()}"
            if self._model.spectrum_position_count() is not None
            else ""
        )
        self._active.setText(f"Showing   {curve.label}      state: {state}{position_note}")
        self._diagnostics.set_histogram(
            self._model.spectrum_histogram(position_index=position),
            float(curve.values.min()) if curve.values.size else 0.0,
            float(curve.values.max()) if curve.values.size else 0.0,
            curve.label,
        )

    def _refresh_image(self) -> None:
        render = self._model.render()
        self._image.show_render(render)
        # The colorbar now carries the value scale, so the caption stays minimal:
        # what channel/representation is shown and its processing state.
        state = self._channel_state(render.channel)
        self._active.setText(f"Showing   {render.title}      state: {state}")
        # Measurements survive channel changes: recompute them for the new channel.
        self._measure.refresh()
        # The Diagnostics distribution follows the channel/representation on screen.
        self._diagnostics.set_histogram(
            self._model.channel_histogram(), render.vmin, render.vmax, render.title
        )

    def _on_cursor_moved(self, x_nm: float, y_nm: float, in_bounds: bool) -> None:
        if not in_bounds:
            self._image.set_readout("")
            return
        readout = self._model.cursor_readout(x_nm, y_nm)
        if not readout.in_bounds:
            self._image.set_readout("")
            return
        values = "      ".join(f"{v.label}: {v.value} {v.unit}" for v in readout.values)
        self._image.set_readout(
            f"x = {readout.x_nm:.0f} nm     y = {readout.y_nm:.0f} nm        {values}"
        )

    def _on_comparison_cursor(self, x_nm: float, y_nm: float, in_bounds: bool) -> None:
        if in_bounds and self._experiment_compare is not None:
            readout = self._experiment.comparison_readout(
                list(self._experiment_compare),
                self._experiment_compare_channel,
                self._model.current_representation,
                x_nm,
                y_nm,
            )
        elif in_bounds:
            readout = self._model.values_at(self._comparison.specs, x_nm, y_nm)
        else:
            readout = None
        if readout is None or not readout.in_bounds:
            self._comparison.set_readout("")
            self._comparison.set_crosshair(0.0, 0.0, False)
            return
        values = "      ".join(f"{v.label}: {v.value} {v.unit}" for v in readout.values)
        self._comparison.set_readout(
            f"x = {readout.x_nm:.0f} nm     y = {readout.y_nm:.0f} nm        {values}"
        )
        self._comparison.set_crosshair(x_nm, y_nm, True)

    def _channel_state(self, channel: str) -> str:
        try:
            return self._model.dataset.metadata.channel(channel).state
        except KeyError:
            return "raw"


def _safe_int(value: Any, default: int) -> int:
    """Coerce a manifest value to int, falling back to ``default`` (tolerate junk)."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _facts_line(identity: MeasurementIdentity) -> str:
    parts: list[str] = [f"{identity.kind}", "raw measurement" if identity.is_raw else "derived"]
    if identity.pixels is not None:
        parts.append(f"{identity.pixels[0]} x {identity.pixels[1]} px")
    if identity.field_nm is not None:
        parts.append(f"{identity.field_nm[0] / 1000:g} x {identity.field_nm[1] / 1000:g} µm")
    if identity.wavenumber_cm1 is not None:
        parts.append(f"{identity.wavenumber_cm1:g} cm^-1")
    if identity.detection:
        parts.append(identity.detection)
    if identity.source_type:
        parts.append(identity.source_type)
    if identity.datetime:
        parts.append(identity.datetime)
    if identity.vendor:
        parts.append(identity.vendor)
    return "      ".join(parts)


__all__ = ["MeasurementExplorerWindow"]
